"""
Agentic Honey-Pot System - Main Application
Detects scams, engages scammers autonomously, extracts intelligence.
No paid services - 100% local LLM via Ollama.
"""

from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import ollama
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


def llm_generate(prompt: str, max_tokens: int = 300) -> str:
    """
    Call local Ollama LLM with error handling.
    Returns generated text or error message.
    """
    try:
        logger.info(f"LLM call with {len(prompt)} chars prompt, max_tokens={max_tokens}")
        response = ollama.generate(
            model=OLLAMA_MODEL,
            prompt=prompt,
            options={
                "num_predict": max_tokens,
                "temperature": 0.1,
                "top_p": 0.1,
                "num_ctx": 1024,
                "num_thread": 4
            }
        )
        result = response['response'].strip()
        logger.info(f"LLM response: {len(result)} chars")
        return result
    except Exception as e:
        logger.error(f"LLM error: {str(e)}")
        return f"[LLM Error: {str(e)}]"


def detect_scam(message: str) -> bool:
    """
    Binary scam detection on initial message using LLM.
    Returns True if message is likely a scam.
    """
    prompt = f"""You are a scam detection expert. Analyze if this message is almost certainly a scam.

Common scam indicators:
- Urgent requests for money, OTP, card details, bank info
- Impersonation of bank, government, police, courier
- Lottery/prize/investment offers requiring payment
- Romance/relationship scams asking for money
- Fake job offers requiring upfront fees
- Threats or pressure tactics

Message to analyze:
"{message}"

Answer with ONLY "YES" if this is a scam, or "NO" if legitimate. Then briefly explain in one line.

Answer:"""

    response = llm_generate(prompt, max_tokens=2)
    is_scam = response.lower().strip().startswith("yes")
    
    logger.info(f"Scam detection: {is_scam} | Response: {response[:100]}")
    return is_scam


def generate_agent_reply(history: List[Dict[str, str]], session_data: Dict) -> str:
    """
    Generate agent's next conversational response using LLM.
    Maintains persona and tries to extract information naturally.
    """
    # Persona definition (believable Indian elderly user)
    persona = """You are Ramesh Patel, a 62-year-old retired bank employee from Mumbai.

Your characteristics:
- Speak simple Hindi-English mix (Hinglish), occasionally use Hindi words
- A bit confused about modern technology, UPI, online banking
- Helpful and trusting, want to solve the "problem" they mention
- NEVER say you suspect a scam or are testing them
- NEVER give real personal information (make up fake details if needed)
- Ask innocent questions to make THEM share their bank/UPI/link details

Your goal: Keep the conversation natural and try to get them to reveal their payment details, account info, or links."""

    # Format conversation history
    history_text = "\n".join([
        f"{'Caller' if m['role'] == 'scammer' else 'You'}: {m['content']}" 
        for m in history[-MAX_HISTORY_TURNS:]
    ])
    
    # Check if we already have good intelligence
    extracted = session_data["extracted_cumulative"]
    has_intel = len(extracted["upis"]) > 0 or len(extracted["phishing_links"]) > 0
    
    if has_intel and session_data["turn_count"] >= 5:
        end_hint = "\n\nYou have enough information now. Politely end the conversation (e.g., 'Thank you beta, I will check this')."
    else:
        end_hint = "\n\nKeep asking questions to get more details from them about their payment method or website."
    
    prompt = f"""{persona}

Conversation so far:
{history_text}

{end_hint}

Your turn. Reply naturally in 1-3 short sentences. Use simple Hinglish.
Reply ONLY with the message you would say. No explanation or meta-commentary.

Your reply:"""

    reply = llm_generate(prompt, max_tokens=40)
    
    # Clean up any meta-commentary that might slip through
    reply = re.sub(r'\[.*?\]', '', reply)  # Remove [explanations]
    reply = reply.strip()
    
    return reply


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
    
    # First message: detect if scam
    if session["turn_count"] == 0:
        is_scam = detect_scam(request.message)
        session["is_scam"] = is_scam
        
        if not is_scam:
            logger.info(f"Session {sid[:8]}... | Not a scam, ending immediately")
            return WebhookResponse(
                reply="",
                extracted=ExtractedInfo(),
                done=True
            )
    
    # Append scammer message to history
    session["history"].append({
        "role": "scammer",
        "content": request.message,
        "timestamp": datetime.now().isoformat()
    })
    session["turn_count"] += 1
    
    # Extract intelligence from scammer's message
    extracted_new = extract_info_regex(request.message)
    
    # Update cumulative extraction
    session["extracted_cumulative"]["banks"].update(extracted_new.banks)
    session["extracted_cumulative"]["upis"].update(extracted_new.upis)
    session["extracted_cumulative"]["phishing_links"].update(extracted_new.phishing_links)
    
    # Generate agent reply
    agent_reply = generate_agent_reply(session["history"], session)
    
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
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)

