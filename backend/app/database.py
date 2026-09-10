"""Local SQLite setup and request-scoped SQLAlchemy sessions.

The demo deliberately keeps this boundary small: callers receive a session from
``get_db`` and models share the declarative ``Base`` defined here.
"""

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


# Keep the database alongside the backend so local setup has no external service.
DATABASE_PATH = Path(__file__).resolve().parent.parent / "effigov.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """Yield one database session per request and close it even when it fails."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
