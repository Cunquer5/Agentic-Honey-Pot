"""
Data Models Module
Contains all Pydantic models for request/response validation.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict, AliasChoices


class MessageModel(BaseModel):
    """Message model for chat conversations."""
    model_config = ConfigDict(extra='ignore')
    
    sender: str = "scammer"
    text: str = ""
    timestamp: Optional[str] = None


class MetadataModel(BaseModel):
    """Metadata for incoming requests."""
    model_config = ConfigDict(extra='ignore')
    
    channel: Optional[str] = "SMS"
    language: Optional[str] = "English"
    locale: Optional[str] = "IN"


class WebhookRequest(BaseModel):
    """Incoming request from GUVI Platform - Hyper-Resilient Schema."""
    model_config = ConfigDict(populate_by_name=True, extra='ignore')
    
    sessionId: str = Field(default="", validation_alias=AliasChoices("sessionId", "session_id"))
    message: Any = None
    conversationHistory: Optional[List[Any]] = Field(default_factory=list)
    metadata: Optional[Any] = None

    @field_validator("sessionId", mode="before")
    @classmethod
    def ensure_sid_string(cls, v):
        return str(v) if v is not None else ""

    @field_validator("message", mode="before")
    @classmethod
    def wrap_message_string(cls, v):
        if isinstance(v, str):
            return MessageModel(sender="scammer", text=v)
        return v


class ExtractedIntelligence(BaseModel):
    """Structured intelligence for final callback."""
    bankAccounts: List[str] = Field(default_factory=list)
    upiIds: List[str] = Field(default_factory=list)
    phishingLinks: List[str] = Field(default_factory=list)
    phoneNumbers: List[str] = Field(default_factory=list)
    suspiciousKeywords: List[str] = Field(default_factory=list)


class WebhookResponse(BaseModel):
    """Response sent back to GUVI Platform."""
    status: str = "success"
    reply: str = ""


class FinalResultPayload(BaseModel):
    """Payload for GUVI mandatory callback."""
    sessionId: str
    scamDetected: bool
    totalMessagesExchanged: int
    extractedIntelligence: ExtractedIntelligence
    agentNotes: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    model: str
    sessions_active: int


class SessionMetrics(BaseModel):
    """Detailed metrics for a session (for evaluation)."""
    sessionId: str
    detected_scam: bool
    turn_count: int
    duration_seconds: float
    extracted_info: ExtractedIntelligence
    conversation_log: List[Dict[str, str]]


class SessionData(BaseModel):
    """Session data structure for internal use."""
    history: List[Dict[str, str]] = Field(default_factory=list)
    extracted_cumulative: Dict[str, set] = Field(default_factory=lambda: {
        "bankAccounts": set(),
        "upiIds": set(),
        "phishingLinks": set(),
        "phoneNumbers": set(),
        "suspiciousKeywords": set()
    })
    start_time: str = Field(default_factory=lambda: datetime.now().isoformat())
    turn_count: int = 0
    is_scam: bool = False
    callback_sent: bool = False
