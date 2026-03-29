"""
Database setup for SENTINEL.
Uses SQLite with SQLAlchemy ORM. The database file is created automatically.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings

# Create the SQLAlchemy engine
# connect_args is only needed for SQLite to allow multi-threaded access
engine_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    engine_args["connect_args"] = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    **engine_args,
    echo=settings.DEBUG,
)


# Create a session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all SQLAlchemy models
Base = declarative_base()


def get_db():
    """
    Dependency function for FastAPI routes.
    Usage in a route: db: Session = Depends(get_db)
    This gives you a database session that auto-closes when the request ends.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
