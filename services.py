"""
Business Logic Services Module
Contains core services for LLM interaction, intelligence extraction, and session management.
"""

import asyncio
import re
import httpx
import logging
from datetime import datetime
from typing import Dict, List, Set, Optional

import ollama
from ollama import AsyncClient

from config import settings
from models import (
    ExtractedIntelligence, 
    SessionData, 
    FinalResultPayload
)

logger = logging.getLogger(__name__)


class IntelligenceService:
    """Service for extracting intelligence from text using regex patterns."""
    
    # Suspicious keywords for scam detection
    SUSPICIOUS_KEYWORDS = [
        "urgent", "verify", "blocked", "suspended", "kyc", "otp", 
        "winner", "lottery", "prize", "atm", "unauthorized"
    ]
    
    @staticmethod
    def extract_intelligence(text: str) -> ExtractedIntelligence:
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
        found_keywords = [w for w in IntelligenceService.SUSPICIOUS_KEYWORDS 
                          if w in text.lower()]
        
        return ExtractedIntelligence(
            bankAccounts=banks,
            upiIds=upis,
            phishingLinks=links,
            phoneNumbers=phones,
            suspiciousKeywords=found_keywords
        )


class LLMService:
    """Service for interacting with Ollama LLM."""
    
    def __init__(self):
        self.client = None
    
    async def _get_client(self) -> AsyncClient:
        """Get or create Ollama client."""
        if not self.client:
            self.client = AsyncClient(host=settings.ollama_url)
        return self.client
    
    async def generate_response(self, prompt: str, max_tokens: int = 300) -> str:
        """
        Call local Ollama LLM asynchronously with error handling.
        """
        try:
            logger.info(f"LLM call to {settings.ollama_url} | Model: {settings.OLLAMA_MODEL}")
            client = await self._get_client()
            
            response = await client.generate(
                model=settings.OLLAMA_MODEL,
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
    
    async def detect_scam(self, message: str) -> bool:
        """
        Binary scam detection on initial message using LLM.
        """
        prompt = f"Analyze if this message is a scam: \"{message}\"\nAnswer ONLY 'YES' or 'NO'."
        response = await self.generate_response(prompt, max_tokens=5)
        return "yes" in response.lower()
    
    async def generate_agent_reply(self, history: List[Dict[str, str]]) -> str:
        """
        Generate agent's next conversational response with fallbacks.
        """
        persona = ("You are Ramesh Patel, a 62-year-old retired man from Mumbai. "
                  "Reply in simple Hinglish (Hindi+English). Be confused but helpful. "
                  "Ask questions to get more info.")
        
        history_text = "\n".join([
            f"{'Scammer' if m['role'] == 'scammer' else 'Ramesh'}: {m['content']}" 
            for m in history[-3:]
        ])
        
        prompt = f"{persona}\n\nChat history:\n{history_text}\n\nYour reply as Ramesh:"
        
        reply = await self.generate_response(prompt, max_tokens=50)
        
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


class SessionService:
    """Service for managing conversation sessions."""
    
    def __init__(self):
        self.sessions: Dict[str, SessionData] = {}
    
    def get_session(self, session_id: str) -> SessionData:
        """Get or create a session."""
        if session_id not in self.sessions:
            self.sessions[session_id] = SessionData()
        return self.sessions[session_id]
    
    def update_session_with_message(self, session_id: str, message: str, role: str) -> SessionData:
        """Update session with new message and extract intelligence."""
        session = self.get_session(session_id)
        
        # Add message to history
        session.history.append({
            "role": role,
            "content": message,
            "timestamp": datetime.now().isoformat()
        })
        
        # Extract intelligence
        if role == "scammer":
            extracted = IntelligenceService.extract_intelligence(message)
            session.extracted_cumulative["bankAccounts"].update(extracted.bankAccounts)
            session.extracted_cumulative["upiIds"].update(extracted.upiIds)
            session.extracted_cumulative["phishingLinks"].update(extracted.phishingLinks)
            session.extracted_cumulative["phoneNumbers"].update(extracted.phoneNumbers)
            session.extracted_cumulative["suspiciousKeywords"].update(extracted.suspiciousKeywords)
        
        if role == "scammer":
            session.turn_count += 1
        
        return session
    
    def should_end_conversation(self, session_id: str, agent_reply: str) -> bool:
        """
        Determine if conversation should end based on heuristics.
        """
        session = self.get_session(session_id)
        
        # Max turns reached
        if session.turn_count >= settings.MAX_TURNS:
            logger.info(f"Ending: max turns ({settings.MAX_TURNS}) reached")
            return True
        
        # Got valuable intelligence
        extracted = session.extracted_cumulative
        has_good_intel = (
            len(extracted["upiIds"]) > 0 or 
            len(extracted["phishingLinks"]) > 0 or
            len(extracted["bankAccounts"]) >= 2
        )
        
        # Agent is wrapping up
        ending_phrases = ["thank you", "bye", "goodbye", "will check", "later", "thik hai"]
        agent_ending = any(phrase in agent_reply.lower() for phrase in ending_phrases)
        
        if has_good_intel and agent_ending and session.turn_count >= 5:
            logger.info("Ending: intelligence gathered + natural conclusion")
            return True
        
        return False
    
    def get_session_metrics(self, session_id: str) -> Optional[Dict]:
        """Get detailed metrics for a session."""
        if session_id not in self.sessions:
            return None
        
        session = self.sessions[session_id]
        start_time = datetime.fromisoformat(session.start_time)
        duration = (datetime.now() - start_time).total_seconds()
        
        return {
            "sessionId": session_id,
            "detected_scam": session.is_scam,
            "turn_count": session.turn_count,
            "duration_seconds": duration,
            "extracted_info": ExtractedIntelligence(
                bankAccounts=list(session.extracted_cumulative["bankAccounts"]),
                upiIds=list(session.extracted_cumulative["upiIds"]),
                phishingLinks=list(session.extracted_cumulative["phishingLinks"]),
                phoneNumbers=list(session.extracted_cumulative["phoneNumbers"]),
                suspiciousKeywords=list(session.extracted_cumulative["suspiciousKeywords"])
            ),
            "conversation_log": session.history
        }
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False


class CallbackService:
    """Service for handling external callbacks."""
    
    @staticmethod
    async def send_final_callback(session_id: str, session_data: SessionData):
        """
        Mandatory Final Result Callback to GUVI.
        """
        if session_data.callback_sent:
            return

        intel = ExtractedIntelligence(
            bankAccounts=list(session_data.extracted_cumulative["bankAccounts"]),
            upiIds=list(session_data.extracted_cumulative["upiIds"]),
            phishingLinks=list(session_data.extracted_cumulative["phishingLinks"]),
            phoneNumbers=list(session_data.extracted_cumulative["phoneNumbers"]),
            suspiciousKeywords=list(session_data.extracted_cumulative["suspiciousKeywords"])
        )

        payload = FinalResultPayload(
            sessionId=session_id,
            scamDetected=session_data.is_scam,
            totalMessagesExchanged=session_data.turn_count,
            extractedIntelligence=intel,
            agentNotes="Scammer engaged via Ramesh Patel persona. High urgency tactics detected. Intelligence extracted successfully."
        )

        async with httpx.AsyncClient() as client:
            try:
                logger.info(f"Sending final callback to GUVI for session {session_id}...")
                resp = await client.post(
                    settings.GUVI_CALLBACK_URL, 
                    json=payload.dict(), 
                    timeout=settings.REQUEST_TIMEOUT
                )
                logger.info(f"GUVI Callback Response: {resp.status_code} - {resp.text}")
                session_data.callback_sent = True
            except Exception as e:
                logger.error(f"Failed to send mandatory GUVI callback: {str(e)}")


# Global service instances
intelligence_service = IntelligenceService()
llm_service = LLMService()
session_service = SessionService()
callback_service = CallbackService()
