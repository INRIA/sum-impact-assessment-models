"""
Database connection and session management.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from contextlib import contextmanager
from typing import Generator
from ..config.settings import settings

# Create SQLAlchemy engine
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # Verify connections before using them
    pool_recycle=3600,   # Recycle connections after 1 hour
    echo=settings.DEBUG  # Log SQL queries in debug mode
)

# Create session factory
print("Creating SessionLocal with database URL:", settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for ORM models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get database session.
    Use with FastAPI Depends().
    
    Yields:
        Database session that automatically closes after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.
    Use in non-FastAPI contexts.
    
    Example:
        with get_db_session() as db:
            # Use db session here
            pass
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
