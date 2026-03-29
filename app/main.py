"""
SENTINEL Backend — Main Application Entrypoint.
Run with: python -m uvicorn app.main:app --reload --port 8000

JWT-based authentication. All data endpoints require Bearer token.
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.database import engine, Base, SessionLocal
from app.seed import seed_database

# ─── Import all models so SQLAlchemy knows about them ───
from app.models.user import User  # noqa: F401
from app.models.profile import PatientProfile  # noqa: F401
from app.models.report import LabReport  # noqa: F401
from app.models.trauma import TraumaPin  # noqa: F401
from app.models.share_key import ShareKey  # noqa: F401

from contextlib import asynccontextmanager

# ─── Startup: Create tables + seed data ───
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs once when the server starts and stops."""
    # Create all database tables (if they don't exist)
    Base.metadata.create_all(bind=engine)
    print("[STARTUP] Database tables created.")

    # Create uploads directory
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    # Seed with demo data
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()

    print(f"[STARTUP] {settings.APP_NAME} v{settings.APP_VERSION} is running.")
    print("[STARTUP] API docs at: http://localhost:8000/docs")
    yield

# ─── Create FastAPI App ───
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Bio-Digital Twin API — JWT-authenticated endpoints",
    lifespan=lifespan,
)

# ─── CORS ───
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Health Check ───
@app.get("/", tags=["Health"])
def health_check():
    """Root endpoint. Returns API status."""
    return {
        "status": "online",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }


# ─── Include Routers ───

# Auth (public endpoints: register, verify, login)
from app.api.routes.auth import router as auth_router
app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])

# Profile (onboarding + profile management)
from app.api.routes.profile import router as profile_router
app.include_router(profile_router, prefix="/api/profile", tags=["Profile"])

# Protected data endpoints
from app.api.routes.patient import router as patient_router
app.include_router(patient_router, prefix="/api/patients", tags=["Patients"])


from app.api.routes.reports import router as reports_router
app.include_router(reports_router, prefix="/api/reports", tags=["Lab Reports"])

from app.api.routes.trauma import router as trauma_router
app.include_router(trauma_router, prefix="/api/trauma", tags=["Trauma Vault"])

from app.api.routes.share import router as share_router
app.include_router(share_router, prefix="/api/share", tags=["Share Keys"])

from app.api.routes.timeline import router as timeline_router
app.include_router(timeline_router, prefix="/api/timeline", tags=["Timeline"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
