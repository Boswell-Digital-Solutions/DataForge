"""
AuthorForge - AI-Powered Writing Assistant for Fantasy, Sci-Fi, and Christian Fiction

FastAPI application entry point.
"""
import logging
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from app.config import (
    validate_config,
    get_config_info,
    ALLOWED_ORIGINS,
    CORS_ALLOW_METHODS,
    CORS_ALLOW_HEADERS,
    LOG_LEVEL,
    HOST,
    PORT
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


# Lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for application startup and shutdown.
    """
    # Startup: Validate configuration
    logger.info("🚀 Starting AuthorForge...")

    try:
        validate_config()
        logger.info("✅ Configuration validated")
    except ValueError as e:
        logger.error(f"❌ Configuration error: {e}")
        logger.error("Please check your .env file and ensure all required variables are set")
        sys.exit(1)

    config = get_config_info()
    logger.info(f"✅ DataForge URL: {config['dataforge_url']}")
    logger.info(f"✅ Anthropic API configured: {config['anthropic_configured']}")

    yield

    # Shutdown
    logger.info("👋 Shutting down AuthorForge...")


# Initialize FastAPI application
app = FastAPI(
    title="AuthorForge",
    description="AI-Powered Writing Assistant for Fantasy, Sci-Fi, and Christian Fiction",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
logger.info(f"Configuring CORS with origins: {ALLOWED_ORIGINS}")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=CORS_ALLOW_METHODS,
    allow_headers=CORS_ALLOW_HEADERS,
)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    config = get_config_info()
    return {
        "status": "ok",
        "service": "authorforge",
        "version": "1.0.0",
        "config": config
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "AuthorForge API - AI-Powered Writing Assistant",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "supported_genres": ["fantasy", "scifi", "christian_fiction", "general"]
    }


# Import and register routers
from app.api import research_router, smithy_router

app.include_router(research_router)
app.include_router(smithy_router)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if LOG_LEVEL == "DEBUG" else "An error occurred"
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)
