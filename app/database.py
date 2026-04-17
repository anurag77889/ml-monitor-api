from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

# For SQLite, check_same_thread=False is required
# because FastAPI handles requests in threads
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=settings.DEBUG,  # Logs SQL queries in debug mode
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


class Base(DeclarativeBase):
    """All ORM models will inherit from this."""
    pass


def get_db():
    """
    Dependency that provides a DB session per request
    and always closes it when done — even on errors.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
