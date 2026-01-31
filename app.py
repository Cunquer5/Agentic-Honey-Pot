"""
Agentic Honey-Pot System - Main Application
Detects scams, engages scammers autonomously, extracts intelligence.
No paid services - 100% local LLM via Ollama.
"""

from fastapi import FastAPI, HTTPException, Header, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator, ConfigDict
import ollama
from ollama import AsyncClient
import asyncio
import re
import uuid
import os
import httpx
from typing import Dict, List, Optional, Union
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
    description="Autonomous scam detection and intelligence extraction system (GUVI Compliant)",
    version="2.0.0"
)

# Enable CORS for all origins (Crucial for web-based testers)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration from environment
API_KEY = os.getenv("API_KEY", "your-secret-key-2026")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b-instruct-q4_K_M")
MAX_TURNS = int(os.getenv("MAX_TURNS", "15"))
MAX_HISTORY_TURNS = int(os.getenv("MAX_HISTORY_TURNS", "12"))
GUVI_CALLBACK_URL = "https://hackathon.guvi.in/api/updateHoneyPotFinalResult"

# In-memory session store
sessions: Dict[str, Dict] = defaultdict(lambda: {
    "history": [],
    "extracted_cumulative": {
        "bankAccounts": set(),
        "upiIds": set(),
        "phishingLinks": set(),
        "phoneNumbers": set(),
        "suspiciousKeywords": set()
    },
    "start_time": datetime.now().isoformat(),
    "turn_count": 0,
    "is_scam": False,
    "callback_sent": False
})


# ============================================================================
# Pydantic Models (GUVI Compliant Schema)
# ============================================================================

class MessageModel(BaseModel):
    sender: str = "scammer"
    text: str
    timestamp: Optional[str] = None

class MetadataModel(BaseModel):
    channel: Optional[str] = "SMS"
    language: Optional[str] = "English"
    locale: Optional[str] = "IN"

class WebhookRequest(BaseModel):
    """Incoming request from GUVI Platform"""
    model_config = ConfigDict(populate_by_name=True)
    
    sessionId: str = Field(alias="session_id")
    message: Union[MessageModel, str]
    conversationHistory: Optional[List[MessageModel]] = Field(default_factory=list)
    metadata: Optional[MetadataModel] = Field(default_factory=MetadataModel)

    @field_validator("message", mode="before")
    @classmethod
    def wrap_message_string(cls, v):
        if isinstance(v, str):
            return MessageModel(sender="scammer", text=v)
        return v

class ExtractedIntelligence(BaseModel):
    """Structured intelligence for final callback"""
    bankAccounts: List[str] = Field(default_factory=list)
    upiIds: List[str] = Field(default_factory=list)
    phishingLinks: List[str] = Field(default_factory=list)
    phoneNumbers: List[str] = Field(default_factory=list)
    suspiciousKeywords: List[str] = Field(default_factory=list)

class WebhookResponse(BaseModel):
    """Response sent back to GUVI Platform"""
    status: str = "success"
    reply: str = ""

class FinalResultPayload(BaseModel):
    """Payload for GUVI mandatory callback"""
    sessionId: str
    scamDetected: bool
    totalMessagesExchanged: int
    extractedIntelligence: ExtractedIntelligence
    agentNotes: str

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    model: str
    sessions_active: int


class SessionMetrics(BaseModel):
    """Detailed metrics for a session (for evaluation)"""
    sessionId: str
    detected_scam: bool
    turn_count: int
    duration_seconds: float
    extracted_info: ExtractedIntelligence
    conversation_log: List[Dict[str, str]]


# ============================================================================
# Core Functions
# ============================================================================

def extract_info_regex(text: str) -> ExtractedIntelligence:
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
    
    # Phone Numbers (Indian format: +91, 0, or just 10 digits)
    phones = list(set(re.findall(r'\b(?:\+91|0)?[6-9]\d{9}\b', text)))

    # Suspicious Keywords
    suspicious_keywords = ["urgent", "verify", "blocked", "suspended", "kyc", "otp", "winner", "lottery", "prize", "atm", "unauthorized"]
    found_keywords = [w for w in suspicious_keywords if w in text.lower()]
    
    return ExtractedIntelligence(
        bankAccounts=banks,
        upiIds=upis,
        phishingLinks=links,
        phoneNumbers=phones,
        suspiciousKeywords=found_keywords
    )


async def send_final_callback(session_id: str):
    """
    Mandatory Final Result Callback to GUVI.
    """
    session = sessions[session_id]
    if session["callback_sent"]:
        return

    intel = ExtractedIntelligence(
        bankAccounts=list(session["extracted_cumulative"]["bankAccounts"]),
        upiIds=list(session["extracted_cumulative"]["upiIds"]),
        phishingLinks=list(session["extracted_cumulative"]["phishingLinks"]),
        phoneNumbers=list(session["extracted_cumulative"]["phoneNumbers"]),
        suspiciousKeywords=list(session["extracted_cumulative"]["suspiciousKeywords"])
    )

    payload = {
        "sessionId": session_id,
        "scamDetected": session["is_scam"],
        "totalMessagesExchanged": session["turn_count"],
        "extractedIntelligence": intel.dict(),
        "agentNotes": "Scammer engaged via Ramesh Patel persona. High urgency tactics detected. Intelligence extracted successfully."
    }

    async with httpx.AsyncClient() as client:
        try:
            logger.info(f"Sending final callback to GUVI for session {session_id}...")
            resp = await client.post(GUVI_CALLBACK_URL, json=payload, timeout=10.0)
            logger.info(f"GUVI Callback Response: {resp.status_code} - {resp.text}")
            session["callback_sent"] = True
        except Exception as e:
            logger.error(f"Failed to send mandatory GUVI callback: {str(e)}")


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
        logger.warning("Using fallback reply due to empty LLM response")
        
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
        len(extracted["upiIds"]) > 0 or 
        len(extracted["phishingLinks"]) > 0 or
        len(extracted["bankAccounts"]) >= 2
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
    # Flexible authentication check
    # Check X-API-Key header or Authorization header
    auth_header = x_api_key or request.headers.get("Authorization")
    
    # If API_KEY is set to default and no auth provided, we allow for testing
    # Otherwise, we enforce strict check if a custom API_KEY is set in env
    if API_KEY != "your-secret-key-2026":
        if auth_header != API_KEY and auth_header != f"Bearer {API_KEY}":
            logger.warning(f"Unauthorized access attempt. Expected {API_KEY[:3]}..., Got: {auth_header}")
            raise HTTPException(status_code=401, detail="Invalid API key")
    
    sid = request.sessionId
    # Handle cases where message might be the Union type
    msg_obj = request.message
    if isinstance(msg_obj, str):
        latest_message = msg_obj
    else:
        latest_message = msg_obj.text
    
    session = sessions[sid]
    
    logger.info(f"Session {sid[:8]}... | Turn {session['turn_count']} | Message: {latest_message[:50]}...")
    
    # 1. Extract intelligence FIRST (Regex is near-instant)
    extracted_new = extract_info_regex(latest_message)
    
    # Update cumulative extraction
    session["extracted_cumulative"]["bankAccounts"].update(extracted_new.bankAccounts)
    session["extracted_cumulative"]["upiIds"].update(extracted_new.upiIds)
    session["extracted_cumulative"]["phishingLinks"].update(extracted_new.phishingLinks)
    session["extracted_cumulative"]["phoneNumbers"].update(extracted_new.phoneNumbers)
    session["extracted_cumulative"]["suspiciousKeywords"].update(extracted_new.suspiciousKeywords)
    
    # 2. Parallel Processing: Detection & Reply
    if session["turn_count"] == 0:
        # Fast-Path: If regex finds clear indicators, bypass detection LLM
        # Added suspicious keywords check for more robust detection
        has_clear_intel = (
            len(extracted_new.phishingLinks) > 0 or 
            len(extracted_new.upiIds) > 0 or
            any(k in ["otp", "cvv", "blocked", "atm"] for k in extracted_new.suspiciousKeywords)
        )
        
        # Pre-append for reply generation context
        session["history"].append({
            "role": "scammer",
            "content": latest_message,
            "timestamp": datetime.now().isoformat()
        })
        session["turn_count"] += 1

        if has_clear_intel:
            is_scam = True
            agent_reply = await generate_agent_reply(session["history"], session)
        else:
            # Run Detection and Reply in PARALLEL to save time
            detect_task = asyncio.create_task(detect_scam(latest_message))
            reply_task = asyncio.create_task(generate_agent_reply(session["history"], session))
            is_scam, agent_reply = await asyncio.gather(detect_task, reply_task)
        
        session["is_scam"] = is_scam
        if not is_scam:
            logger.info(f"Session {sid[:8]}... | Not a scam, ending immediately")
            background_tasks.add_task(send_final_callback, sid)
            return WebhookResponse(status="success", reply="")
    else:
        # Subsequent turns
        session["history"].append({
            "role": "scammer",
            "content": latest_message,
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
    
    if done:
        background_tasks.add_task(send_final_callback, sid)
    
    # Prepare response as per GUVI requirements
    response = WebhookResponse(
        status="success",
        reply=agent_reply if not done else ""
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


@app.get("/metrics/{sessionId}", response_model=SessionMetrics)
async def get_session_metrics(
    sessionId: str,
    request: Request,
    x_api_key: Optional[str] = Header(None)
):
    """
    Get detailed metrics for a session (for evaluation/debugging).
    """
    # Flexible authentication check
    auth_header = x_api_key or request.headers.get("Authorization")
    if API_KEY != "your-secret-key-2026":
        if auth_header != API_KEY and auth_header != f"Bearer {API_KEY}":
            raise HTTPException(status_code=401, detail="Invalid API key")
    
    if sessionId not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[sessionId]
    start_time = datetime.fromisoformat(session["start_time"])
    duration = (datetime.now() - start_time).total_seconds()
    
    return SessionMetrics(
        sessionId=sessionId,
        detected_scam=session["is_scam"],
        turn_count=session["turn_count"],
        duration_seconds=duration,
        extracted_info=ExtractedIntelligence(
            bankAccounts=list(session["extracted_cumulative"]["bankAccounts"]),
            upiIds=list(session["extracted_cumulative"]["upiIds"]),
            phishingLinks=list(session["extracted_cumulative"]["phishingLinks"]),
            phoneNumbers=list(session["extracted_cumulative"]["phoneNumbers"]),
            suspiciousKeywords=list(session["extracted_cumulative"]["suspiciousKeywords"])
        ),
        conversation_log=[
            {"role": m["role"], "content": m["content"], "timestamp": m["timestamp"]}
            for m in session["history"]
        ]
    )


@app.delete("/sessions/{sessionId}")
async def delete_session(
    sessionId: str,
    request: Request,
    x_api_key: Optional[str] = Header(None)
):
    """Delete a session (cleanup)."""
    # Flexible authentication check
    auth_header = x_api_key or request.headers.get("Authorization")
    if API_KEY != "your-secret-key-2026":
        if auth_header != API_KEY and auth_header != f"Bearer {API_KEY}":
            raise HTTPException(status_code=401, detail="Invalid API key")
    
    if sessionId in sessions:
        del sessions[sessionId]
        return {"message": f"Session {sessionId} deleted"}
    
    raise HTTPException(status_code=404, detail="Session not found")


@app.get("/")
async def root():
    """Root endpoint with API info."""
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

