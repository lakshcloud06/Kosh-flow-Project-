import logging
from pathlib import Path
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

logger = logging.getLogger("koshflow.database")

# Build MySQL URL using credentials configured in backend/.env
encoded_password = quote_plus(settings.DB_PASSWORD)
mysql_url = (
    f"mysql+pymysql://{settings.DB_USER}:{encoded_password}@"
    f"{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}?charset=utf8mb4"
)

# Connect to MySQL, with graceful fallback to persistent local SQLite if MySQL credentials are not yet configured
try:
    # First attempt to ensure the database exists if connected as root/admin
    server_url = (
        f"mysql+pymysql://{settings.DB_USER}:{encoded_password}@"
        f"{settings.DB_HOST}:{settings.DB_PORT}/?charset=utf8mb4"
    )
    temp_engine = create_engine(server_url, pool_pre_ping=True, connect_args={"connect_timeout": 2})
    with temp_engine.connect() as conn:
        conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{settings.DB_NAME}` DEFAULT CHARACTER SET utf8mb4;"))
        conn.commit()
    temp_engine.dispose()

    engine = create_engine(mysql_url, pool_pre_ping=True, pool_recycle=3600, connect_args={"connect_timeout": 2})
    with engine.connect() as test_conn:
        test_conn.execute(text("SELECT 1"))
    logger.info("Successfully connected to MySQL database: %s", settings.DB_NAME)
except Exception as e:
    # Deterministic absolute path to koshflow.db in backend folder
    sqlite_path = Path(__file__).resolve().parent.parent / "koshflow.db"
    logger.warning("Could not connect to MySQL (%s). Using fallback SQLite database: %s", e, sqlite_path)
    engine = create_engine(f"sqlite:///{sqlite_path.as_posix()}", connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def init_db():
    """Create all database tables automatically on startup."""
    import app.models  # Ensure models are loaded
    Base.metadata.create_all(bind=engine)

def get_db():
    """Dependency that yields a database session and closes it after request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Auto-create tables on import
try:
    init_db()
except Exception:
    pass
