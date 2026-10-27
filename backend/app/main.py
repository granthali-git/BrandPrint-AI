"""FastAPI Main Application entry point for BrandPrint AI."""
import os
from datetime import datetime, timezone
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import engine, Base
from app.routes.auth import router as auth_router
from app.routes.guidelines import router as guidelines_router
from app.routes.reviews import router as reviews_router
from app.routes.dashboard import router as dashboard_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("brandprint.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for application startup and shutdown."""
    logger.info("Initializing BrandPrint AI Backend...")
    # Attempt table creation if running with local or accessible database (skip during tests)
    if not os.environ.get("TESTING") and not os.environ.get("PYTEST_CURRENT_TEST"):
        try:
            Base.metadata.create_all(bind=engine)
            with engine.connect() as conn:
                try:
                    from sqlalchemy import text
                    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS full_name VARCHAR(255);"))
                    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS company VARCHAR(255);"))
                    conn.execute(text("ALTER TABLE findings ADD COLUMN IF NOT EXISTS is_visual BOOLEAN DEFAULT FALSE;"))
                    conn.execute(text("ALTER TABLE findings ADD COLUMN IF NOT EXISTS visual_element VARCHAR(255);"))
                    conn.execute(text("ALTER TABLE findings ADD COLUMN IF NOT EXISTS observed_evidence TEXT;"))
                    conn.execute(text("ALTER TABLE content_submissions ADD COLUMN IF NOT EXISTS image_preview_url TEXT;"))
                    conn.execute(text("ALTER TABLE content_submissions ADD COLUMN IF NOT EXISTS visual_analysis_status VARCHAR(50);"))
                    conn.execute(text("ALTER TABLE content_submissions ADD COLUMN IF NOT EXISTS visual_analysis_message TEXT;"))
                    conn.commit()
                except Exception:
                    pass
            logger.info("Database schema verified/initialized successfully.")
        except Exception as e:
            logger.warning(
                f"Note: Could not run metadata create_all against database URL ({e}). "
                "Ensure Supabase database is active and reachable."
            )
    yield
    logger.info("Shutting down BrandPrint AI Backend...")


app = FastAPI(
    title="BrandPrint AI API",
    description="Intelligent Brand Consistency & Guideline Verification Engine",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Comprehensive CORS setup: Local development + Vercel / Cloud deployments
origins = [
    "*",
    "https://brand-print-ai.vercel.app",
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:5175",
    "http://localhost:3000",
]
if settings.FRONTEND_URL and settings.FRONTEND_URL not in origins:
    origins.append(settings.FRONTEND_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"^https:\/\/.*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers - support both /api and direct prefix
app.include_router(auth_router, prefix="/api")
app.include_router(auth_router)
app.include_router(guidelines_router, prefix="/api")
app.include_router(guidelines_router)
app.include_router(reviews_router, prefix="/api")
app.include_router(reviews_router)
app.include_router(dashboard_router, prefix="/api")
app.include_router(dashboard_router)

# Direct alias for /check-contradictions
from typing import Optional
from fastapi import Query, Body, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.guideline import ContradictionCheckRequest
from app.routes.guidelines import check_contradictions as route_check_contradictions

@app.post("/api/check-contradictions", tags=["Guidelines"])
@app.post("/check-contradictions", tags=["Guidelines"])
def check_contradictions_direct(
    brand_id: int = Query(1),
    payload: Optional[ContradictionCheckRequest] = Body(None),
    as_list: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return route_check_contradictions(brand_id=brand_id, payload=payload, as_list=as_list, current_user=current_user, db=db)





@app.get("/api/system-status", tags=["System"], summary="System status endpoint")
@app.get("/api/ping", tags=["System"], summary="Ping endpoint")
def system_status():
    return {"status": "healthy", "service": "brandprint-core"}


@app.get(
    "/health",
    tags=["System"],
    summary="Health check endpoint",
    description="Returns the current operational status of the BrandPrint AI backend."
)
def health_check():
    """System health check endpoint."""
    return {
        "status": "healthy",
        "port": int(os.environ.get("PORT", 8000)),
        "service": "BrandPrint AI Backend",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database_configured": bool(settings.SUPABASE_DB_URL),
        "cors_origins": origins
    }


@app.get(
    "/",
    tags=["System"],
    summary="Root welcome endpoint"
)
def root():
    """Welcome endpoint providing quick links to documentation."""
    return {
        "message": "Welcome to BrandPrint AI API",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
