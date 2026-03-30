"""
API Routes Module
Contains all FastAPI route handlers.
"""

import asyncio
import logging
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Header, Request, BackgroundTasks
from fastapi.responses import JSONResponse, HTMLResponse

from config import settings
from models import (
    WebhookRequest, 
    WebhookResponse, 
    HealthResponse, 
    SessionMetrics
)
from services import (
    intelligence_service,
    llm_service, 
    session_service, 
    callback_service
)

logger = logging.getLogger(__name__)


def register_routes(app: FastAPI):
    """Register all API routes with the FastAPI app."""
    
    @app.post("/", response_model=WebhookResponse)
    @app.post("/webhook", response_model=WebhookResponse)
    async def handle_scam_webhook(
        request: WebhookRequest,
        background_tasks: BackgroundTasks,
        x_api_key: Optional[str] = Header(None)
    ):
        """
        Main webhook endpoint for scam conversation handling.
        Receives scammer message, returns agent reply.
        """
        # Authentication check
        auth_header = _get_auth_header(x_api_key, request.headers)
        if settings.is_production and not _is_valid_auth(auth_header):
            logger.warning(f"Unauthorized access attempt. Got: {auth_header}")
            raise HTTPException(status_code=401, detail="Invalid API key")
        
        # Extract message content
        session_id = request.sessionId
        latest_message = _extract_message_text(request.message)
        
        if not latest_message:
            logger.warning(f"Empty message received for session {session_id}")
            latest_message = "Hello"
        
        logger.info(f"Session {session_id[:8]}... | Processing message: {latest_message[:50]}...")
        
        # Get or create session
        session = session_service.get_session(session_id)
        
        # Update session with user message
        session_service.update_session_with_message(session_id, latest_message, "scammer")
        
        # Handle first turn differently
        if session.turn_count == 1:
            result = await _handle_first_turn(session_id, latest_message, background_tasks)
        else:
            result = await _handle_subsequent_turns(session_id, latest_message)
        
        # Update session with agent reply if exists
        if result.reply:
            session_service.update_session_with_message(session_id, result.reply, "agent")
        
        # Check if conversation should end
        if session_service.should_end_conversation(session_id, result.reply):
            background_tasks.add_task(callback_service.send_final_callback, session_id, session)
            result.reply = ""  # Don't reply if conversation is ending
        
        logger.info(f"Session {session_id[:8]}... | Reply: {result.reply[:50]}... | Done: {not bool(result.reply)}")
        return result
    
    @app.get("/health", response_model=HealthResponse)
    async def health_check():
        """Health check endpoint for monitoring."""
        return HealthResponse(
            status="ok",
            model=settings.OLLAMA_MODEL,
            sessions_active=len(session_service.sessions)
        )
    
    @app.get("/metrics/{sessionId}", response_model=SessionMetrics)
    async def get_session_metrics(
        sessionId: str,
        request: Request,
        x_api_key: Optional[str] = Header(None)
    ):
        """Get detailed metrics for a session (for evaluation/debugging)."""
        # Authentication check
        auth_header = _get_auth_header(x_api_key, request.headers)
        if settings.is_production and not _is_valid_auth(auth_header):
            raise HTTPException(status_code=401, detail="Invalid API key")
        
        metrics = session_service.get_session_metrics(sessionId)
        if not metrics:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return SessionMetrics(**metrics)
    
    @app.delete("/sessions/{sessionId}")
    async def delete_session(
        sessionId: str,
        request: Request,
        x_api_key: Optional[str] = Header(None)
    ):
        """Delete a session (cleanup)."""
        # Authentication check
        auth_header = _get_auth_header(x_api_key, request.headers)
        if settings.is_production and not _is_valid_auth(auth_header):
            raise HTTPException(status_code=401, detail="Invalid API key")
        
        if session_service.delete_session(sessionId):
            return {"message": f"Session {sessionId} deleted"}
        
        raise HTTPException(status_code=404, detail="Session not found")
    
    @app.get("/ping")
    async def ping():
        """Simple ping for connectivity check without auth/models."""
        return {"status": "alive", "timestamp": str(datetime.now())}
    
    @app.get("/api")
    async def api_info():
        """API info endpoint."""
        return {
            "name": "Agentic Honey-Pot API",
            "version": "2.0.0",
            "endpoints": {
                "POST /webhook": "Main scam handling endpoint (GUVI Compliant)",
                "GET /health": "Health check",
                "GET /metrics/{sessionId}": "Session metrics",
                "DELETE /sessions/{sessionId}": "Delete session"
            },
            "docs": "/docs"
        }
    
    @app.get("/")
    async def root():
        """Root endpoint with basic info."""
        return HTMLResponse("""
        <!DOCTYPE html>
        <html>
        <head><title>Agentic Honey-Pot API</title></head>
        <body>
            <h1>Agentic Honey-Pot API</h1>
            <p>If you see this, the server is working!</p>
            <a href="/web-ui">Go to Web UI</a>
        </body>
        </html>
        """)
    
    @app.get("/web-ui")
    async def web_ui():
        """Serve the web UI"""
        try:
            with open("templates/simple.html", "r", encoding="utf-8") as f:
                content = f.read()
            return HTMLResponse(content)
        except FileNotFoundError:
            return HTMLResponse("<h1>Template not found</h1>", status_code=404)


# Helper functions
def _get_auth_header(x_api_key: Optional[str], headers: dict) -> Optional[str]:
    """Extract authentication header from multiple possible sources."""
    return (
        x_api_key or 
        headers.get("Authorization") or 
        headers.get("apikey") or 
        headers.get("api-key")
    )


def _is_valid_auth(auth_header: Optional[str]) -> bool:
    """Validate authentication header."""
    if not auth_header:
        return False
    return auth_header == settings.API_KEY or auth_header == f"Bearer {settings.API_KEY}"


def _extract_message_text(message_obj) -> str:
    """Extract text from various message object formats."""
    if isinstance(message_obj, str):
        return message_obj
    elif isinstance(message_obj, dict):
        return (message_obj.get("text") or 
                message_obj.get("content") or 
                message_obj.get("message") or "")
    return ""


async def _handle_first_turn(session_id: str, message: str, background_tasks: BackgroundTasks) -> WebhookResponse:
    """Handle the first turn of conversation with scam detection."""
    session = session_service.get_session(session_id)
    
    # Fast-Path: If regex finds clear indicators, bypass detection LLM
    extracted = intelligence_service.extract_intelligence(message)
    has_clear_intel = (
        len(extracted.phishingLinks) > 0 or 
        len(extracted.upiIds) > 0 or
        any(k in ["otp", "cvv", "blocked", "atm"] for k in extracted.suspiciousKeywords)
    )
    
    if has_clear_intel:
        session.is_scam = True
        agent_reply = await llm_service.generate_agent_reply(session.history)
    else:
        # Run Detection and Reply in PARALLEL to save time
        detect_task = asyncio.create_task(llm_service.detect_scam(message))
        reply_task = asyncio.create_task(llm_service.generate_agent_reply(session.history))
        is_scam, agent_reply = await asyncio.gather(detect_task, reply_task)
        session.is_scam = is_scam
        
        if not is_scam:
            logger.info(f"Session {session_id[:8]}... | Not a scam, ending immediately")
            background_tasks.add_task(callback_service.send_final_callback, session_id, session)
            return WebhookResponse(status="success", reply="")
    
    return WebhookResponse(status="success", reply=agent_reply)


async def _handle_subsequent_turns(session_id: str, message: str) -> WebhookResponse:
    """Handle subsequent turns in conversation."""
    session = session_service.get_session(session_id)
    agent_reply = await llm_service.generate_agent_reply(session.history)
    return WebhookResponse(status="success", reply=agent_reply)
