"""
Agentic Honey-Pot System - Main Application
Detects scams, engages scammers autonomously, extracts intelligence.
No paid services - 100% local LLM via Ollama.
"""

from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import ollama
from ollama import AsyncClient
import asyncio
import re
import uuid
import os
from typing import Dict, List, Optional
from collections import defaultdict
from datetime import datetime
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Agentic Honey-Pot API",
    description="Autonomous scam detection and intelligence extraction system",
    version="1.0.0"
)

# Configuration from environment
API_KEY = os.getenv("API_KEY", "your-secret-key-2026")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b-instruct-q4_K_M")
MAX_TURNS = int(os.getenv("MAX_TURNS", "15"))
MAX_HISTORY_TURNS = int(os.getenv("MAX_HISTORY_TURNS", "12"))

# In-memory session store (reset on restart - acceptable for hackathon)
sessions: Dict[str, Dict] = defaultdict(lambda: {
    "history": [],
    "extracted_cumulative": {"banks": set(), "upis": set(), "phishing_links": set()},
    "start_time": datetime.now().isoformat(),
    "turn_count": 0,
    "is_scam": False
})


# ============================================================================
# Pydantic Models (API Schema)
# ============================================================================

class WebhookRequest(BaseModel):
    """Incoming request from Mock Scammer API"""
    session_id: str = Field(..., description="Unique conversation session ID")
    message: str = Field(..., description="Latest scammer message")
    api_key: Optional[str] = Field(None, description="Optional API key in body")


class ExtractedInfo(BaseModel):
    """Structured intelligence extracted from conversation"""
    banks: List[str] = Field(default_factory=list, description="Bank account numbers, IFSC codes")
    upis: List[str] = Field(default_factory=list, description="UPI IDs (user@bank)")
    phishing_links: List[str] = Field(default_factory=list, description="Suspicious URLs")


class WebhookResponse(BaseModel):
    """Response sent back to Mock Scammer API"""
    reply: str = Field("", description="Agent's next message (empty = end conversation)")
    extracted: ExtractedInfo = Field(default_factory=ExtractedInfo, description="Intelligence extracted")
    done: bool = Field(False, description="True if conversation should end")


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    model: str
    sessions_active: int


class SessionMetrics(BaseModel):
    """Detailed metrics for a session (for evaluation)"""
    session_id: str
    detected_scam: bool
    turn_count: int
    duration_seconds: float
    extracted_info: ExtractedInfo
    conversation_log: List[Dict[str, str]]


# ============================================================================
# Core Functions
# ============================================================================

def extract_info_regex(text: str) -> ExtractedInfo:
    """
    Extract intelligence using regex patterns (primary method).
    Patterns tuned for Indian scam context.
    """
    # UPI IDs: user@bank (e.g., victim@oksbi, scammer@paytm)
    upis = list(set(re.findall(r'[\w\.-]+@[\w\.-]+', text)))
    
    # Bank identifiers:
    # - IFSC codes: 4 letters + 7 alphanumeric (e.g., SBIN0001234)
    # - Account numbers: 9-18 digits
    banks_ifsc = list(set(re.findall(r'\b[A-Z]{4}0[A-Z0-9]{6}\b', text.upper())))
    banks_acc = list(set(re.findall(r'\b\d{9,18}\b', text)))
    banks = banks_ifsc + banks_acc
    
    # Phishing links: http(s)://...
    links = list(set(re.findall(r'https?://[^\s<>"{}|\\^`\[\]]+', text)))
    
    return ExtractedInfo(banks=banks, upis=upis, phishing_links=links)


async def llm_generate(prompt: str, max_tokens: int = 300) -> str:
    """
    Call local Ollama LLM asynchronously with error handling.
    """
    try:
        # Better host detection for AsyncClient
        host = os.getenv("OLLAMA_HOST", "127.0.0.1")
        if "://" not in host:
            host = f"http://{host}:11434"
        
        logger.info(f"LLM call to {host} | Model: {OLLAMA_MODEL}")
        client = AsyncClient(host=host)
        
        response = await client.generate(
            model=OLLAMA_MODEL,
            prompt=prompt,
            options={
                "num_predict": max_tokens,
                "temperature": 0.7,
                "top_p": 0.9,
                "num_ctx": 2048,
                "num_thread": 4
            }
        )
        result = response.get('response', '').strip()
        logger.info(f"LLM generated {len(result)} chars")
        return result
    except Exception as e:
        logger.error(f"LLM error: {str(e)}")
        return ""


async def detect_scam(message: str) -> bool:
    """
    Binary scam detection on initial message using LLM.
    """
    prompt = f"Analyze if this message is a scam: \"{message}\"\nAnswer ONLY 'YES' or 'NO'."
    response = await llm_generate(prompt, max_tokens=5)
    return "yes" in response.lower()


async def generate_agent_reply(history: List[Dict[str, str]], session_data: Dict) -> str:
    """
    Generate agent's next conversational response with fallbacks.
    """
    persona = "You are Ramesh Patel, a 62-year-old retired man from Mumbai. Reply in simple Hinglish (Hindi+English). Be confused but helpful. Ask questions to get more info."
    
    history_text = "\n".join([
        f"{'Scammer' if m['role'] == 'scammer' else 'Ramesh'}: {m['content']}" 
        for m in history[-3:]
    ])
    
    prompt = f"{persona}\n\nChat history:\n{history_text}\n\nYour reply as Ramesh:"
    
    reply = await llm_generate(prompt, max_tokens=50)
    
    # FALLBACK: Ensure we ALWAYS have a reply if it's a scam
    if not reply or len(reply) < 5:
        fallbacks = [
            "Beta, mere phone pe kuch error aa raha hai. Kya karun?",
            "Arre, account block ho gaya? Main check karta hoon, thoda ruko.",
            "Yeh link open nahi ho raha, aap phir se bhej sakte ho?",
            "I am trying to pay but password bhool gaya. Kaise karun?"
        ]
        import random
        reply = random.choice(fallbacks)
        logger.warning(f"Using fallback reply for session {session_data.get('session_id', 'unknown')}")
        
    return reply.strip()


def should_end_conversation(session_data: Dict, agent_reply: str) -> bool:
    """
    Heuristic to determine if conversation should end.
    """
    # Max turns reached
    if session_data["turn_count"] >= MAX_TURNS:
        logger.info(f"Ending: max turns ({MAX_TURNS}) reached")
        return True
    
    # Got valuable intelligence
    extracted = session_data["extracted_cumulative"]
    has_good_intel = (
        len(extracted["upis"]) > 0 or 
        len(extracted["phishing_links"]) > 0 or
        len(extracted["banks"]) >= 2
    )
    
    # Agent is wrapping up
    ending_phrases = ["thank you", "bye", "goodbye", "will check", "later", "thik hai"]
    agent_ending = any(phrase in agent_reply.lower() for phrase in ending_phrases)
    
    if has_good_intel and agent_ending and session_data["turn_count"] >= 5:
        logger.info("Ending: intelligence gathered + natural conclusion")
        return True
    
    return False


# ============================================================================
# API Endpoints
# ============================================================================

@app.post("/webhook", response_model=WebhookResponse)
async def handle_scam_webhook(
    request: WebhookRequest,
    x_api_key: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None)
):
    """
    Main webhook endpoint for scam conversation handling.
    Receives scammer message, returns agent reply + extracted intelligence.
    """
    # API key authentication
    key = request.api_key or x_api_key or (
        authorization.split(" ")[1] if authorization and authorization.startswith("Bearer ") else None
    )
    
    if key != API_KEY:
        logger.warning(f"Unauthorized access attempt with key: {key}")
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    # Get or create session
    sid = request.session_id or str(uuid.uuid4())
    session = sessions[sid]
    
    logger.info(f"Session {sid[:8]}... | Turn {session['turn_count']} | Message: {request.message[:50]}...")
    
    # 1. Extract intelligence FIRST (Regex is near-instant)
    extracted_new = extract_info_regex(request.message)
    
    # Update cumulative extraction
    session["extracted_cumulative"]["banks"].update(extracted_new.banks)
    session["extracted_cumulative"]["upis"].update(extracted_new.upis)
    session["extracted_cumulative"]["phishing_links"].update(extracted_new.phishing_links)
    
    # 2. Parallel Processing: Detection & Reply
    if session["turn_count"] == 0:
        # Fast-Path: If regex finds clear indicators, bypass detection LLM
        has_clear_intel = len(extracted_new.phishing_links) > 0 or len(extracted_new.upis) > 0
        
        # Pre-append for reply generation context
        session["history"].append({
            "role": "scammer",
            "content": request.message,
            "timestamp": datetime.now().isoformat()
        })
        session["turn_count"] += 1

        if has_clear_intel:
            is_scam = True
            agent_reply = await generate_agent_reply(session["history"], session)
        else:
            # Run Detection and Reply in PARALLEL to save time
            detect_task = asyncio.create_task(detect_scam(request.message))
            reply_task = asyncio.create_task(generate_agent_reply(session["history"], session))
            is_scam, agent_reply = await asyncio.gather(detect_task, reply_task)
        
        session["is_scam"] = is_scam
        if not is_scam:
            logger.info(f"Session {sid[:8]}... | Not a scam, ending immediately")
            return WebhookResponse(reply="", extracted=ExtractedInfo(), done=True)
    else:
        # Subsequent turns
        session["history"].append({
            "role": "scammer",
            "content": request.message,
            "timestamp": datetime.now().isoformat()
        })
        session["turn_count"] += 1
        agent_reply = await generate_agent_reply(session["history"], session)
    
    # Append agent reply to history
    session["history"].append({
        "role": "agent",
        "content": agent_reply,
        "timestamp": datetime.now().isoformat()
    })
    
    # Decide if conversation should end
    done = should_end_conversation(session, agent_reply)
    
    # Prepare response
    response = WebhookResponse(
        reply=agent_reply if not done else "",
        extracted=ExtractedInfo(
            banks=list(session["extracted_cumulative"]["banks"]),
            upis=list(session["extracted_cumulative"]["upis"]),
            phishing_links=list(session["extracted_cumulative"]["phishing_links"])
        ),
        done=done
    )
    
    logger.info(f"Session {sid[:8]}... | Reply: {agent_reply[:50]}... | Done: {done}")
    
    return response


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for monitoring."""
    return HealthResponse(
        status="ok",
        model=OLLAMA_MODEL,
        sessions_active=len(sessions)
    )


@app.get("/metrics/{session_id}", response_model=SessionMetrics)
async def get_session_metrics(
    session_id: str,
    x_api_key: Optional[str] = Header(None)
):
    """
    Get detailed metrics for a session (for evaluation/debugging).
    """
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    start_time = datetime.fromisoformat(session["start_time"])
    duration = (datetime.now() - start_time).total_seconds()
    
    return SessionMetrics(
        session_id=session_id,
        detected_scam=session["is_scam"],
        turn_count=session["turn_count"],
        duration_seconds=duration,
        extracted_info=ExtractedInfo(
            banks=list(session["extracted_cumulative"]["banks"]),
            upis=list(session["extracted_cumulative"]["upis"]),
            phishing_links=list(session["extracted_cumulative"]["phishing_links"])
        ),
        conversation_log=[
            {"role": m["role"], "content": m["content"], "timestamp": m["timestamp"]}
            for m in session["history"]
        ]
    )


@app.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    x_api_key: Optional[str] = Header(None)
):
    """Delete a session (cleanup)."""
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    if session_id in sessions:
        del sessions[session_id]
        return {"message": f"Session {session_id} deleted"}
    
    raise HTTPException(status_code=404, detail="Session not found")


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "Agentic Honey-Pot API",
        "version": "1.0.0",
        "endpoints": {
            "POST /webhook": "Main scam handling endpoint",
            "GET /health": "Health check",
            "GET /metrics/{session_id}": "Session metrics",
            "DELETE /sessions/{session_id}": "Delete session"
        },
        "docs": "/docs"
    }


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all error handler for graceful degradation."""
    logger.error(f"Unhandled error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if os.getenv("DEBUG") else "An error occurred"
        }
    )


if __name__ == "__main__":
    import uvicorn
    # Hugging Face Spaces uses port 7860 by default
    port = int(os.getenv("PORT", "7860"))
    uvicorn.run(app, host="0.0.0.0", port=port)

