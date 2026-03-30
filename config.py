"""
Configuration Management Module
Handles all environment variables and application settings.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Settings:
    """Application settings and configuration."""
    
    # API Configuration
    API_KEY: str = os.getenv("API_KEY", "your-secret-key-2026")
    
    # Ollama Configuration
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2:1b-instruct-q4_K_M")
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "localhost")
    OLLAMA_PORT: int = int(os.getenv("OLLAMA_PORT", "11434"))
    
    # Conversation Limits
    MAX_TURNS: int = int(os.getenv("MAX_TURNS", "15"))
    MAX_HISTORY_TURNS: int = int(os.getenv("MAX_HISTORY_TURNS", "12"))
    
    # External Services
    GUVI_CALLBACK_URL: str = "https://hackathon.guvi.in/api/updateHoneyPotFinalResult"
    
    # Server Configuration
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "7860"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Request Timeout
    REQUEST_TIMEOUT: float = float(os.getenv("REQUEST_TIMEOUT", "10.0"))
    
    @property
    def ollama_url(self) -> str:
        """Construct Ollama URL from host and port."""
        if "://" not in self.OLLAMA_HOST:
            return f"http://{self.OLLAMA_HOST}:{self.OLLAMA_PORT}"
        return self.OLLAMA_HOST
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return not self.DEBUG and self.API_KEY != "your-secret-key-2026"


# Global settings instance
settings = Settings()
