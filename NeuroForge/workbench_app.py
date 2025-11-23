"""
NeuroForge Workbench Application
Simplified FastAPI app for workbench routers only.
Uses DataForge for all persistence (stateless architecture).
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import logging

from config import config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import workbench routers
from neuroforge_backend.workbench import (
    prompt_router,
    chain_router,
    deployment_router,
    execution_router
)
from neuroforge_backend import auth_router

# Import VibeForge automation routers directly (bypass __init__.py)
import sys
import importlib.util

def load_router_module(module_path: str, module_name: str):
    """Load a router module directly without going through __init__.py"""
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

stack_profiles_module = load_router_module(
    "neuroforge_backend/routers/stack_profiles.py",
    "stack_profiles_router_module"
)
stack_profiles_router = stack_profiles_module.router

languages_module = load_router_module(
    "neuroforge_backend/routers/languages.py",
    "languages_router_module"
)
languages_router = languages_module.router

# Create rate limiter
limiter = Limiter(key_func=get_remote_address)

# Create FastAPI app
app = FastAPI(
    title="NeuroForge Workbench",
    description="Stateless compute layer for VibeForge - All data persisted in DataForge",
    version="1.0.0"
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(
    auth_router.router,
    tags=["authentication"]
)

app.include_router(
    prompt_router.router,
    prefix="/api/v1/workbench",
    tags=["prompts"]
)

app.include_router(
    chain_router.router,
    prefix="/api/v1/workbench",
    tags=["chains"]
)

app.include_router(
    deployment_router.router,
    prefix="/api/v1/workbench",
    tags=["deployments"]
)

app.include_router(
    execution_router.router,
    prefix="/api/v1",
    tags=["execution"]
)

# Include VibeForge automation routers
app.include_router(
    stack_profiles_router,
    tags=["Stack Profiles"]
)

app.include_router(
    languages_router,
    tags=["Languages"]
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "NeuroForge Workbench",
        "architecture": "stateless",
        "data_layer": "DataForge"
    }


@app.get("/")
async def root():
    """Root endpoint with service info."""
    return {
        "service": "NeuroForge Workbench",
        "version": "1.0.0",
        "architecture": "stateless",
        "description": "Stateless compute layer - all data persisted in DataForge",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "prompts": "/api/v1/workbench/prompts",
            "chains": "/api/v1/workbench/chains",
            "deployments": "/api/v1/workbench/prompts/{prompt_id}/deploy",
            "execution": "/api/v1/execute"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
