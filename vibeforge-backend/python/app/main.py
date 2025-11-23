"""Main FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from app.routers import vibeforge, dataforge, neuroforge, adaptive
from app.middleware.wizard_logging import WizardLoggingMiddleware

# Create FastAPI app
app = FastAPI(
    title="VibeForge Backend",
    description="Professional prompt workbench backend with Rust performance layer",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Wizard logging middleware (Phase 3.2)
app.add_middleware(WizardLoggingMiddleware)

# Include routers
app.include_router(vibeforge.router)
app.include_router(dataforge.router)
app.include_router(neuroforge.router)
app.include_router(adaptive.router)  # Phase 3.2 - Adaptive recommendations


@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "vibeforge-backend"}


@app.get("/", tags=["System"])
async def root():
    """Root endpoint with API info."""
    return {
        "name": "VibeForge Backend",
        "version": "0.1.0",
        "docs": "/docs",
        "openapi": "/openapi.json",
    }


def custom_openapi():
    """Custom OpenAPI schema."""
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="VibeForge Backend",
        version="0.1.0",
        description="FastAPI + Rust backend for VibeForge prompt workbench",
        routes=app.routes,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
