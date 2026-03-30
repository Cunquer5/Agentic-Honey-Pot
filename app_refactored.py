"""
Agentic Honey-Pot System - Refactored Main Application
Detects scams, engages scammers autonomously, extracts intelligence.
No paid services - 100% local LLM via Ollama.

Refactored for better maintainability, separation of concerns, and clean architecture.
"""

import logging
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from config import settings
from routes import register_routes

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    
    # Initialize FastAPI app
    app = FastAPI(
        title="Agentic Honey-Pot API",
        description="Autonomous scam detection and intelligence extraction system (GUVI Compliant)",
        version="2.0.0",
        redirect_slashes=False
    )
    
    # Add middleware
    setup_middleware(app)
    
    # Register routes
    register_routes(app)
    
    # Register error handlers
    setup_error_handlers(app)
    
    return app


def setup_middleware(app: FastAPI):
    """Setup application middleware."""
    
    # Global request logger middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        logger.info(f"Incoming request: {request.method} {request.url.path}")
        response = await call_next(request)
        logger.info(f"Response status: {response.status_code}")
        return response
    
    # Enable CORS for all origins (Crucial for web-based testers)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Mount static files
    app.mount("/static", StaticFiles(directory="static"), name="static")


def setup_error_handlers(app: FastAPI):
    """Setup global error handlers."""
    
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Catch-all error handler for graceful degradation."""
        logger.error(f"Unhandled error: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "detail": str(exc) if settings.DEBUG else "An error occurred"
            }
        )


# Create application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting server on {settings.HOST}:{settings.PORT}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    logger.info(f"Ollama model: {settings.OLLAMA_MODEL}")
    logger.info(f"Ollama URL: {settings.ollama_url}")
    
    uvicorn.run(
        app, 
        host=settings.HOST, 
        port=settings.PORT,
        reload=settings.DEBUG
    )
