"""
SENTINEL App Configuration.
All settings for the application with environment variable support.
"""

import os
import secrets
from dotenv import load_dotenv

# Load environment variables from .env file (if it exists)
# This is safe for production because system environment variables take precedence.
load_dotenv()


class Settings:
    """Application settings. Deployment-ready with environment variable support."""

    APP_NAME: str = "SENTINEL Medical Portal API"
    APP_VERSION: str = "0.2.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

    # Database: Use DATABASE_URL from environment (Supabase), fallback to SQLite
    # Note: SQLAlchemy requires postgresql:// instead of postgres://
    raw_db_url = os.getenv("DATABASE_URL", "sqlite:///./sentinel.db")
    if raw_db_url.startswith("postgres://"):
        DATABASE_URL: str = raw_db_url.replace("postgres://", "postgresql://", 1)
    else:
        DATABASE_URL: str = raw_db_url

    # JWT Authentication
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_MINUTES: int = int(os.getenv("JWT_EXPIRY_MINUTES", "10080"))  # 7 days

    # Google SSO
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173") 
    BACKEND_URL: str = os.getenv("BACKEND_URL", "http://localhost:8000")


    # Email Verification
    REQUIRE_VERIFICATION: bool = os.getenv("REQUIRE_VERIFICATION", "True").lower() == "true"
    VERIFICATION_CODE_EXPIRY_MINUTES: int = 15

    # SMTP (optional — falls back to console logging if not set)
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASS: str = os.getenv("SMTP_PASS", "")
    SMTP_FROM: str = os.getenv("SMTP_FROM", "noreply@sentinel.dev")

    # CORS: Allow everything during deployment or restrict if needed
    # CORS: Dynamically allow local origins + your configured frontend origin.
    _cors_env = os.getenv("CORS_ORIGINS", "")
    CORS_ORIGINS: list[str] = _cors_env.split(",") if _cors_env else []
    
    # Always ensure local dev origins and your specific frontend URL are included.
    _required_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
    if os.getenv("FRONTEND_URL"):
        _required_origins.append(os.getenv("FRONTEND_URL"))

    for _o in _required_origins:
        if _o and _o not in CORS_ORIGINS:
            CORS_ORIGINS.append(_o)
    
    # If no origins specified at all, default to "*" (though allow_credentials will require specific)
    if not CORS_ORIGINS:
        CORS_ORIGINS = ["*"]

    # File uploads: where uploaded lab reports are saved
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "data/uploads")

    # Feature toggles
    USE_LIVE_OCR: bool = os.getenv("USE_LIVE_OCR", "False").lower() == "true"
    ENABLE_TELEGRAM: bool = os.getenv("ENABLE_TELEGRAM", "False").lower() == "true"


settings = Settings()
