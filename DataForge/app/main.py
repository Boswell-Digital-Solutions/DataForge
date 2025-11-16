"""
DataForge - Knowledge Base Management System with Semantic Search

FastAPI application entry point.
"""
import os
import logging
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

from app.database import engine, Base
from app.api import search_router, admin_router, auth_router
from app.config import (
    validate_config,
    get_embedding_provider,
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
    Creates database tables on startup.
    """
    # Startup: Validate configuration
    logger.info("🚀 Starting DataForge...")

    try:
        validate_config()
        logger.info("✅ Configuration validated")
    except ValueError as e:
        logger.error(f"❌ Configuration error: {e}")
        logger.error("Please check your .env file and ensure all required variables are set")
        sys.exit(1)

    # Check embedding provider
    provider, api_key = get_embedding_provider()
    if provider:
        logger.info(f"✅ Using {provider} for embeddings")
    else:
        logger.warning("⚠️  No embedding provider configured")

    # Create database tables
    logger.info("📊 Creating database tables...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created")
    except Exception as e:
        logger.error(f"❌ Failed to create database tables: {e}")
        sys.exit(1)

    yield

    # Shutdown
    logger.info("👋 Shutting down DataForge...")

# Initialize FastAPI application
app = FastAPI(
    title="DataForge",
    description="Knowledge Base Management System with Semantic Search",
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

# Mount static files (if directory exists)
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup templates (if directory exists)
templates = None
if os.path.exists("templates"):
    templates = Jinja2Templates(directory="templates")

# Register routers
app.include_router(search_router.router)
app.include_router(admin_router.router)
app.include_router(auth_router.router)

# ============================================
# Health Check & Info Endpoints
# ============================================

@app.get("/", tags=["info"])
async def root():
    """Root endpoint with API information"""
    return {
        "name": "DataForge",
        "version": "1.0.0",
        "description": "Knowledge Base Management System with Semantic Search",
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "search": "/api/search",
            "admin": "/admin",
            "auth": "/auth/token",
            "admin_ui": "/admin-ui"
        }
    }

@app.get("/health", tags=["info"])
async def health_check():
    """
    Health check endpoint.

    Returns the health status of the application and database connectivity.
    """
    from sqlalchemy import text
    from app.database import SessionLocal

    # Check database connectivity
    db_status = "healthy"
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "service": "DataForge",
        "version": "1.0.0",
        "database": db_status
    }

# ============================================
# Admin UI
# ============================================

@app.get("/admin-ui", response_class=HTMLResponse, tags=["ui"])
async def admin_ui(request: Request):
    """
    Admin UI for managing the knowledge base.

    Provides a web interface for:
    - Creating and managing domains
    - Adding and editing documents
    - Managing tags
    - Viewing search statistics
    """
    if templates is None:
        return HTMLResponse(
            content="""
            <html>
                <head><title>DataForge Admin</title></head>
                <body>
                    <h1>DataForge Admin UI</h1>
                    <p>Admin UI template not found. Create templates/admin.html to enable the admin interface.</p>
                    <p>In the meantime, you can use the API documentation at <a href="/docs">/docs</a></p>
                </body>
            </html>
            """,
            status_code=200
        )

    return templates.TemplateResponse("admin.html", {"request": request})

# ============================================
# Application Entry Point
# ============================================

if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8001"))

    print(f"""
    ╔════════════════════════════════════════════╗
    ║          DataForge Starting...             ║
    ║  Knowledge Base Management System          ║
    ╚════════════════════════════════════════════╝

    📍 Server: http://{host}:{port}
    📚 API Docs: http://{host}:{port}/docs
    🔧 Admin UI: http://{host}:{port}/admin-ui
    ❤️  Health: http://{host}:{port}/health

    """)

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=True
    )
