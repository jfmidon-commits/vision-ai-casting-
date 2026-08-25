from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.database import init_db
from app.utils.logger import get_logger
from app.routers import (
    auth_router, profiles_router, photoshoots_router,
    photos_router, analyses_router, reports_router,
    uploads_router, ai_router, commands_router,
    approvals_router, career_memory_router
)
from app.routers.websocket import router as websocket_router

logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up Vision AI Casting API...")
    await init_db()
    logger.info("Database initialized")
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
