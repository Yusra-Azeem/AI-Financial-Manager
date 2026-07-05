"""
database.py
Sets up the SQLAlchemy engine + session, pointed at Supabase Postgres (or local
sqlite if you set DATABASE_URL to a sqlite:/// path in .env for quick testing).
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from config import settings

connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency: yields a DB session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create tables. Call once on startup (fine for a hackathon; use Alembic later)."""
    import models  # noqa: F401  (ensures models are registered on Base before create_all)
    Base.metadata.create_all(bind=engine)
