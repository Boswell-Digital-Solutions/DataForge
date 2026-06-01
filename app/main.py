"""
DataForge - Knowledge Base Management System with Semantic Search

FastAPI application entry point.
"""
import os
import logging
import sys
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler as fastapi_request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

from app.database import engine
from app.api import search_router, admin_router, auth_router, projects_router, runs_router, vibeforge_router, learning_router, teams_router
from app.api.authorforge_v2_router import router as authorforge_v2_router
from app.api.routes.events_router import router as events_router
from app.api.diligence_router import router as diligence_router, ui_router as diligence_ui_router
from app.api.admin_keys_router import router as admin_keys_router, auth_info_router, rotation_router  # ForgeCommand Key Rotation
from app.api.secrets_router import router as secrets_router  # LLM Provider Secrets (synced from Forge_Command)
from app.api.tarcie_router import router as tarcie_router  # Tarcie friction capture ingest
from app.api.fpvs_router import router as fpvs_router  # FPVS Phase 1 endpoints
from app.api.forge_run_router import router as forge_run_router  # ForgeAgents run persistence (Phase 2)
from app.api.agents_registry_router import router as agents_registry_router  # ForgeAgents agent persistence
from app.api.bugcheck_router import router as bugcheck_router  # BugCheck Agent persistence
from app.api.experience_router import router as experience_router  # Agentic Reasoning: Experience Store
from app.api.runtime_promotion_candidate_router import router as runtime_promotion_candidate_router
from app.api.runtime_promotion_router import router as runtime_promotion_router  # Runtime promotion receipt ingest
from app.api.smithy_portfolio_router import router as smithy_portfolio_router  # Smithy Portfolio
from app.api.smithy_planning_router import router as smithy_planning_router  # Smithy Planning Sessions
from app.api.neuroforge_router import router as neuroforge_router  # NeuroForge inference logging
from app.api.multi_provider_router import router as multi_provider_router  # Multi-Provider Pipeline (catalog, pricing, costs, batch)
from app.api.rate_limits_router import router as rate_limits_router  # Global rate limiting (XAI/MAID cross-run)
from app.api.sentinel_router import router as sentinel_router  # Sentinel Agent (sweeps, healing events)
from app.api.compression_router import router as compression_router  # Dictionary Compression (Phase 2)
from app.api.press_router import router as press_router  # PressForge: journalist outreach (AuthorForge module)
from app.api.private_source_router import router as private_source_router  # PSIM: private source profiles
from app.api.policy_envelope_router import router as policy_envelope_router  # Deterministic LLM policy envelopes + ledgers
from app.api.proving_slice_router import router as proving_slice_router  # Proving-slice artifact intake + receipt
from app.api.llm_intel_source_trust_router import router as llm_intel_source_trust_router  # LLM provider intelligence source trust
from app.api.llm_intel_pending_records_router import router as llm_intel_pending_records_router  # LLM provider intelligence pending records
from app.api.llm_intel_promotion_application_router import router as llm_intel_promotion_application_router  # LLM provider intelligence promotion application
from app.middleware.correlation import CorrelationIDMiddleware
from app.middleware.request_timeout import RequestTimeoutMiddleware
try:
    from forge_compression import PayloadSizeCollector, ZstdDictionaryMiddleware, DictionaryStore
    _HAS_COMPRESSION = True
except ImportError:
    _HAS_COMPRESSION = False
from app.config import (
    validate_config,
    get_embedding_provider,
    ALLOWED_ORIGINS,
    CORS_ALLOW_METHODS,
    CORS_ALLOW_HEADERS,
    LOG_LEVEL,
    HOST,
    PORT,
    COMPRESSION_ENABLED,
    FORGECOMMAND_COMPRESSION_URL,
    COMPRESSION_MIN_SIZE,
    COMPRESSION_POLL_INTERVAL,
    REQUEST_TIMEOUT_SECONDS,
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
    Validates runtime config and initializes required extensions.
    """
    # Startup: Validate configuration
    main_logger.info("🚀 Starting DataForge...")
    app.state.pgvector_startup_ok = None
    app.state.pgvector_startup_error = None

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

    skip_startup_db_init = os.getenv("DATAFORGE_SKIP_STARTUP_DB_INIT", "").lower() in {"1", "true", "yes"}

    # Enable pgvector extension (retry on transient connection failures)
    if skip_startup_db_init:
        main_logger.info("⏭️  Skipping pgvector startup init due to DATAFORGE_SKIP_STARTUP_DB_INIT")
    else:
        main_logger.info("📦 Enabling pgvector extension...")
        import time as _time
        _pgvector_ok = False
        for _attempt in range(1, 4):
            try:
                from sqlalchemy import text
                with engine.connect() as conn:
                    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                    conn.commit()
                main_logger.info("✅ pgvector extension enabled")
                _pgvector_ok = True
                break
            except Exception as e:
                main_logger.warning(
                    f"⚠️  pgvector init attempt {_attempt}/3 failed: {e}"
                )
                if _attempt < 3:
                    _delay = 5 * _attempt  # 5s, 10s
                    main_logger.info(f"   Retrying in {_delay}s...")
                    _time.sleep(_delay)
        if not _pgvector_ok:
            startup_error = "Failed to enable pgvector extension after 3 retries"
            app.state.pgvector_startup_ok = False
            app.state.pgvector_startup_error = startup_error
            main_logger.error("❌ Failed to enable pgvector after 3 attempts")
            log_security_event(
                main_logger,
                "EXTENSION_INIT_FAILURE",
                startup_error
            )
            main_logger.warning(
                "⚠️  Continuing startup without pgvector. /ready will report the dependency failure until the database recovers."
            )
        else:
            app.state.pgvector_startup_ok = True

    # Database migrations run in Render build phase for free-tier deploys.
    # Keep app startup focused on serving traffic quickly.
    main_logger.info("📊 Database migrations are managed outside app startup")

    yield

    # Shutdown
    main_logger.info("👋 Shutting down DataForge...")

# Initialize FastAPI application
# Disable interactive API docs (Swagger/ReDoc/OpenAPI) in production so the
# full API surface of this data gateway is not publicly browsable.
_is_production = os.getenv("ENVIRONMENT", "development").lower() == "production"
app = FastAPI(
    title="DataForge",
    description="Knowledge Base Management System with Semantic Search",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None if _is_production else "/docs",
    redoc_url=None if _is_production else "/redoc",
    openapi_url=None if _is_production else "/openapi.json",
)


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    """Preserve legacy 404 semantics for invalid project path IDs."""
    if request.url.path.startswith("/api/projects/"):
        for error in exc.errors():
            if error.get("loc") == ("path", "project_id"):
                return JSONResponse(status_code=404, content={"detail": "Project not found"})
    return await fastapi_request_validation_exception_handler(request, exc)

# Configure security headers middleware (must be added before CORS)
main_logger.info("Adding security headers middleware...")
configure_security_headers(app)

# Add request timeout middleware before correlation tracing so completion logs
# still emit around a timed-out request instead of disappearing mid-flight.
main_logger.info("Adding request timeout middleware...")
app.add_middleware(
    RequestTimeoutMiddleware,
    timeout_seconds=REQUEST_TIMEOUT_SECONDS,
)

# Add correlation ID middleware (FPVS Phase 1)
main_logger.info("Adding correlation ID middleware...")
app.add_middleware(CorrelationIDMiddleware)

# Payload size collection + Zstd dictionary compression (local-only; requires forge-compression)
if _HAS_COMPRESSION:
    main_logger.info("Adding payload size collector middleware...")
    app.add_middleware(PayloadSizeCollector, service_name="dataforge")

    if COMPRESSION_ENABLED:
        main_logger.info("Adding Zstd dictionary compression middleware...")
        _dict_store = DictionaryStore(
            forgecommand_url=FORGECOMMAND_COMPRESSION_URL,
            poll_interval=COMPRESSION_POLL_INTERVAL,
        )
        _dict_store.start()
        app.add_middleware(
            ZstdDictionaryMiddleware,
            service_name="dataforge",
            dictionary_store=_dict_store,
            enabled_routes=[
                "/api/v1/search",
                "/api/v1/bugcheck",
                "/api/v1/experience",
            ],
            min_size=COMPRESSION_MIN_SIZE,
        )
else:
    main_logger.warning("forge_compression not installed — compression middleware disabled (local-only feature)")

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
app.include_router(auth_router.legacy_router)
app.include_router(projects_router.router)  # AuthorForge projects API
app.include_router(diligence_router)  # Due Diligence API
app.include_router(diligence_ui_router)  # Due Diligence UI
app.include_router(runtime_promotion_router)  # Runtime promotion receipt ingest
app.include_router(runtime_promotion_candidate_router)  # Runtime promotion candidate management (Phase 3)
app.include_router(runs_router.router)  # VibeForge runs & analytics
app.include_router(vibeforge_router.router)  # VibeForge learning layer
app.include_router(learning_router.router)  # Multi-AI planning learning layer
app.include_router(teams_router.router)  # Team & Organization Learning (Phase 4.1)
app.include_router(events_router)  # BuildGuard Events API (GRR Phase D)
app.include_router(admin_keys_router)  # API Key Management (ForgeCommand Key Rotation)
app.include_router(rotation_router)  # Admin Token Rotation (72-hour auto-rotation)
app.include_router(secrets_router)  # LLM Provider Secrets (synced from Forge_Command)
app.include_router(tarcie_router)  # Tarcie friction capture ingest
app.include_router(forge_run_router)  # ForgeAgents run persistence (Phase 2)
app.include_router(agents_registry_router)  # ForgeAgents agent registry persistence
app.include_router(bugcheck_router)  # BugCheck Agent persistence (runs, findings, enrichments)
app.include_router(smithy_portfolio_router)  # Smithy Portfolio & Competency module
app.include_router(smithy_planning_router)  # Smithy Planning Sessions persistence
app.include_router(authorforge_v2_router)  # AuthorForge V2: chapters, scenes, graph, maps, covers
app.include_router(neuroforge_router)  # NeuroForge inference logging & transparency
app.include_router(experience_router)  # Agentic Reasoning: Experience Store (search, index, get)
app.include_router(multi_provider_router)  # Multi-Provider Pipeline: model catalog, pricing, costs, batch
app.include_router(rate_limits_router)  # Global rate limiting: XAI/MAID cross-run enforcement
app.include_router(sentinel_router)  # Sentinel Agent: health sweeps, healing events
app.include_router(compression_router)  # Dictionary Compression: CRUD for Zstd dictionaries
app.include_router(press_router)  # PressForge: journalist outreach module
app.include_router(private_source_router)  # PSIM: private source profile CRUD
app.include_router(policy_envelope_router)  # Deterministic LLM policy envelopes + run ledgers
app.include_router(proving_slice_router)  # Proving-slice artifact intake + receipt emission
app.include_router(llm_intel_source_trust_router)  # LLM provider intelligence approved source registry
app.include_router(llm_intel_pending_records_router)  # LLM provider intelligence pending record storage
app.include_router(llm_intel_promotion_application_router)  # LLM provider intelligence DataForge promotion application

# ============================================
# Health Check & Info Endpoints
# ============================================

@app.get("/", tags=["info"])
async def root(request: Request):
    """Service info endpoint with optional HTML home page for browsers."""
    info = {
        "name": "DataForge",
        "version": app.version,
        "description": app.description,
        "endpoints": ["/health", "/docs", "/admin-ui", "/diligence/dashboard"],
    }

    accept = request.headers.get("accept", "")
    wants_html = "text/html" in accept
    if not wants_html:
        return info

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
    Lightweight liveness endpoint.

    This route intentionally avoids database, Redis, filesystem, and external
    dependency access so Render health checks only verify that the process and
    event loop are alive.
    """
    return {
        "status": "ok",
        "service": "DataForge",
        "version": "1.0.0",
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


@app.get("/ready", tags=["info"])
async def readiness_check():
    """
    Readiness check endpoint for ecosystem verification.

    Returns structured dependency health following the Forge verification contract.
    Used by Forge Command to verify service readiness with dependency details.
    """
    from sqlalchemy import text

    dependencies = []
    overall_status = "ok"

    # Check PostgreSQL (critical dependency)
    postgres_dep = {
        "name": "postgres",
        "status": "ok",
        "critical": True,
        "latency_ms": 0,
        "message": None,
        "error_class": None
    }
    def _check_postgres() -> int:
        from app.database import SessionLocal

        start = time.perf_counter()
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        return int((time.perf_counter() - start) * 1000)

    try:
        from starlette.concurrency import run_in_threadpool

        postgres_dep["latency_ms"] = await run_in_threadpool(_check_postgres)
    except Exception as e:
        postgres_dep["status"] = "down"
        postgres_dep["message"] = str(e)
        postgres_dep["error_class"] = "tcp_failed" if "connect" in str(e).lower() else "unknown"
        overall_status = "down"  # Critical dependency failed
        logger.error(f"Readiness check - PostgreSQL failed: {e}")
    dependencies.append(postgres_dep)

    # Check Redis (non-critical dependency)
    redis_dep = {
        "name": "redis",
        "status": "ok",
        "critical": False,
        "latency_ms": 0,
        "message": None,
        "error_class": None
    }
    try:
        from app.utils.redis_utils import get_redis_client
        start = time.perf_counter()
        redis = await get_redis_client()
        if redis:
            await redis.ping()
            redis_dep["latency_ms"] = int((time.perf_counter() - start) * 1000)
        else:
            # Surface the configured endpoint (password stripped) so readiness is
            # self-diagnosing: shows whether the process actually got REDIS_URL
            # (cloud host) or fell back to localhost (env not reaching the container).
            from app.config import REDIS_URL as _ru
            _endpoint = _ru.split("@")[-1] if _ru else "(unset)"
            redis_dep["status"] = "down"
            redis_dep["message"] = f"Redis client unavailable (configured endpoint: {_endpoint})"
            redis_dep["error_class"] = "dependency_failed"
            if overall_status == "ok":
                overall_status = "degraded"
    except Exception as e:
        redis_dep["status"] = "down"
        redis_dep["message"] = str(e)
        redis_dep["error_class"] = "tcp_failed" if "connect" in str(e).lower() else "timeout" if "timeout" in str(e).lower() else "unknown"
        if overall_status == "ok":
            overall_status = "degraded"
        logger.warning(f"Readiness check - Redis failed: {e}")
    dependencies.append(redis_dep)

    from fastapi.responses import JSONResponse
    status_code = 200 if overall_status == "ok" else 503 if overall_status == "down" else 200

    return JSONResponse(
        content={
            "status": overall_status,
            "dependencies": dependencies
        },
        status_code=status_code
    )


app.include_router(auth_info_router)  # /auth/whoami and secondary /health info
app.include_router(fpvs_router, tags=["FPVS"])  # FPVS Phase 1: /health, /ready, /version


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

    host = os.getenv("HOST", "127.0.0.1")
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
