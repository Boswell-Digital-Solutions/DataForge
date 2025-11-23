"""
VibeForge Automation API
Standalone FastAPI app for VibeForge automation endpoints (stack profiles, languages).
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import sys
import os

# Add current directory to path to resolve imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from neuroforge_backend.routers.stack_profiles import router as stack_profiles_router
from neuroforge_backend.routers.languages import router as languages_router
from neuroforge_backend.services.stack_loader import load_stack_profiles_from_json
from neuroforge_backend.routers.stack_profiles import load_stack_profiles

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="VibeForge Automation API",
    description="Stack profiles and language selector APIs for VibeForge",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(stack_profiles_router, tags=["Stack Profiles"])
app.include_router(languages_router, tags=["Languages"])


@app.on_event("startup")
async def startup_event():
    """Load stack profiles on startup."""
    logger.info("Loading stack profiles...")
    try:
        profiles = load_stack_profiles_from_json()
        load_stack_profiles(profiles)
        logger.info(f"Loaded {len(profiles)} stack profiles")
    except Exception as e:
        logger.error(f"Failed to load stack profiles: {e}")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "VibeForge Automation API",
        "endpoints": {
            "stacks": "/api/v1/stacks",
            "languages": "/api/v1/languages"
        }
    }


@app.get("/")
async def root():
    """Root endpoint with service info."""
    return {
        "service": "VibeForge Automation API",
        "version": "1.0.0",
        "description": "Stack profiles and language selector APIs",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
