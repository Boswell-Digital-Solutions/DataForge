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
from app.api import search_router, admin_router, auth_router, projects_router, runs_router, vibeforge_router, learning_router, teams_router
from app.api.routes.events_router import router as events_router
from app.api.diligence_router import router as diligence_router, ui_router as diligence_ui_router
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
from app.security_config import configure_security_headers
from app.logging_config import initialize_logging, get_logger, log_security_event

# Load environment variables
load_dotenv()

# Initialize structured logging with JSON format
logger = initialize_logging(
    log_level=LOG_LEVEL,
    log_dir="logs",
    json_format=True
)
main_logger = get_logger(__name__)

# Lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for application startup and shutdown.
    Creates database tables on startup.
    """
    # Startup: Validate configuration
    main_logger.info("🚀 Starting DataForge...")

    try:
        validate_config()
        main_logger.info("✅ Configuration validated")
    except ValueError as e:
        main_logger.error(f"❌ Configuration error: {e}")
        main_logger.error("Please check your .env file and ensure all required variables are set")
        log_security_event(
            main_logger,
            "STARTUP_FAILURE",
            f"Configuration validation failed: {e}"
        )
        sys.exit(1)

    # Check embedding provider
    provider, api_key = get_embedding_provider()
    if provider:
        main_logger.info(f"✅ Using {provider} for embeddings")
    else:
        main_logger.warning("⚠️  No embedding provider configured")

    # Enable pgvector extension
    main_logger.info("📦 Enabling pgvector extension...")
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
        main_logger.info("✅ pgvector extension enabled")
    except Exception as e:
        main_logger.error(f"❌ Failed to enable pgvector extension: {e}")
        log_security_event(
            main_logger,
            "EXTENSION_INIT_FAILURE",
            f"Failed to enable pgvector extension: {e}"
        )
        sys.exit(1)

    # Create database tables
    main_logger.info("📊 Creating database tables...")
    try:
        Base.metadata.create_all(bind=engine)
        main_logger.info("✅ Database tables created")
    except Exception as e:
        main_logger.error(f"❌ Failed to create database tables: {e}")
        log_security_event(
            main_logger,
            "DATABASE_INIT_FAILURE",
            f"Failed to create database tables: {e}"
        )
        sys.exit(1)

    yield

    # Shutdown
    main_logger.info("👋 Shutting down DataForge...")

# Initialize FastAPI application
app = FastAPI(
    title="DataForge",
    description="Knowledge Base Management System with Semantic Search",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure security headers middleware (must be added before CORS)
main_logger.info("Adding security headers middleware...")
configure_security_headers(app)

# Configure CORS
main_logger.info(f"Configuring CORS with origins: {ALLOWED_ORIGINS}")
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
app.include_router(projects_router.router)  # AuthorForge projects API
app.include_router(diligence_router)  # Due Diligence API
app.include_router(diligence_ui_router)  # Due Diligence UI
app.include_router(runs_router.router)  # VibeForge runs & analytics
app.include_router(vibeforge_router.router)  # VibeForge learning layer
app.include_router(learning_router.router)  # Multi-AI planning learning layer
app.include_router(teams_router.router)  # Team & Organization Learning (Phase 4.1)
app.include_router(events_router)  # BuildGuard Events API (GRR Phase D)

# ============================================
# Health Check & Info Endpoints
# ============================================

@app.get("/", tags=["info"], response_class=HTMLResponse)
async def root(request: Request):
    """Home page with links to main features"""
    if templates is None:
        return HTMLResponse(
            content="""
            <html>
                <head><title>DataForge</title></head>
                <body>
                    <h1>DataForge</h1>
                    <p>Knowledge Base Management System with Semantic Search</p>
                    <ul>
                        <li><a href="/diligence/dashboard">📊 Due Diligence Dashboard</a></li>
                        <li><a href="/admin">🔧 Admin Panel</a></li>
                        <li><a href="/docs">📚 API Documentation</a></li>
                    </ul>
                </body>
            </html>
            """,
            status_code=200
        )
    
    return templates.TemplateResponse("home.html", {"request": request})

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


@app.get("/health/render", tags=["info"])
async def render_health_check():
    """
    Render deployment health check.
    Simple status check for service and Redis connectivity.
    """
    result = {"service": "ok"}

    # Check Redis
    try:
        from app.utils.redis_utils import get_redis_client
        redis = await get_redis_client()
        if redis:
            await redis.ping()
            result["redis"] = "ok"
        else:
            result["redis"] = "not_configured"
    except Exception:
        result["redis"] = "error"

    return result


# ============================================
# Admin UI
# ============================================

@app.get("/admin", response_class=HTMLResponse, tags=["ui"])
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
    port = int(os.getenv("PORT", "8788"))

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
