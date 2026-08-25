from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from app.config import settings
from app.database import init_db, AsyncSessionLocal
from app.utils.logger import get_logger
from app.routers import (
    auth_router, profiles_router, photoshoots_router,
    photos_router, analyses_router, reports_router,
    uploads_router, ai_router, commands_router,
    approvals_router, career_memory_router
)
from app.routers.websocket import router as websocket_router
from sqlalchemy import select, and_
from app.models import Analysis

logger = get_logger(__name__)

ORPHANED_ANALYSIS_THRESHOLD_MINUTES = 10


async def _recover_orphaned_analyses():
    """Marca análises órfãs (processing há mais de 10 min) como failed.

    Quando o processo é morto por OOM/restart, BackgroundTasks morrem
    silenciosamente, deixando análises presas em 'processing'. Esta função
    recupera essas análises no startup do novo processo."""
    try:
        async with AsyncSessionLocal() as db:
            cutoff = datetime.utcnow() - timedelta(minutes=ORPHANED_ANALYSIS_THRESHOLD_MINUTES)
            result = await db.execute(
                select(Analysis).where(
                    and_(
                        Analysis.status == "processing",
                        Analysis.created_at < cutoff,
                    )
                )
            )
            orphaned = result.scalars().all()
            if not orphaned:
                logger.info("No orphaned analyses found")
                return

            for analysis in orphaned:
                raw_results = (
                    dict(analysis.raw_results)
                    if isinstance(analysis.raw_results, dict)
                    else {}
                )
                raw_results["pipeline_error"] = {
                    "message": "Processo reiniciado (OOM/restart) durante análise. Tente novamente.",
                    "failed_at": datetime.utcnow().isoformat(),
                }
                analysis.raw_results = raw_results
                analysis.status = "failed"
                analysis.completed_at = datetime.utcnow()
                logger.warning(
                    "Recovered orphaned analysis %s (created at %s)",
                    analysis.id,
                    analysis.created_at,
                )

            await db.commit()
            logger.info("Recovered %d orphaned analyses", len(orphaned))
    except Exception:
        logger.exception("Failed to recover orphaned analyses")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up Vision AI Casting API...")
    await init_db()
    logger.info("Database initialized")
    await _recover_orphaned_analyses()
    yield
    logger.info("Shutting down...")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered casting analysis platform with Vision Core v0.1",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router)
app.include_router(profiles_router)
app.include_router(photoshoots_router)
app.include_router(photos_router)
app.include_router(analyses_router)
app.include_router(reports_router)
app.include_router(uploads_router)
app.include_router(ai_router)
app.include_router(commands_router)      # Vision Core - Commands
app.include_router(approvals_router)     # Vision Core - Approvals
app.include_router(career_memory_router)  # Vision Core - Career Memory / Talent Graph
app.include_router(websocket_router)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": settings.APP_VERSION}

@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
        "vision_core": "/api/v1/commands",
    }
