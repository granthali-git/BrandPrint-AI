"""API routes package."""
from app.routes.auth import router as auth_router
from app.routes.guidelines import router as guidelines_router
from app.routes.reviews import router as reviews_router
from app.routes.dashboard import router as dashboard_router

__all__ = ["auth_router", "guidelines_router", "reviews_router", "dashboard_router"]



