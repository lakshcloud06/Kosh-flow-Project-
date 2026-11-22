
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

logger = logging.getLogger("koshflow.database")

DATABASE_URL = (
    f"mysql+pymysql://{settings.DB_USER}:{settings.DB_PASSWORD}"
    f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args={
        "connect_timeout": 10,
        "ssl": {}
    }
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def init_db():
    if not settings.DB_HOST or settings.DB_HOST == "localhost":
        raise RuntimeError("Aiven DB_HOST is missing or incorrectly configured.")
    import app.models
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created or verified successfully.")


def get_db():
    if not settings.DB_HOST or settings.DB_HOST == "localhost":
        raise RuntimeError("Aiven DB_HOST is missing or incorrectly configured.")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
