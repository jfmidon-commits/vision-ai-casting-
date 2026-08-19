from .auth import router as auth_router
from .profiles import router as profiles_router
from .photoshoots import router as photoshoots_router
from .photos import router as photos_router
from .analyses import router as analyses_router
from .reports import router as reports_router
from .evaluations import router as evaluations_router
from .uploads import router as uploads_router
from .ai import router as ai_router
from .commands import router as commands_router
from .approvals import router as approvals_router
from .career_memory import router as career_memory_router

__all__ = [
    "auth_router",
    "profiles_router",
    "photoshoots_router",
    "photos_router",
    "analyses_router",
    "reports_router",
    "evaluations_router",
    "uploads_router",
    "ai_router",
    "commands_router",
    "approvals_router",
    "career_memory_router",
]
