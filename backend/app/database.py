import logging
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

logger = logging.getLogger("koshflow.database")

# Build connection URL safely
mysql_url = URL.create(
    drivername="mysql+pymysql",
    username=settings.DB_USER,
    password=settings.DB_PASSWORD,
    host=settings.DB_HOST,
    port=int(settings.DB_PORT),
    database=settings.DB_NAME,
    query={"charset": "utf8mb4"}
)

# Connect directly to the existing Aiven database
engine = create_engine(
    mysql_url,
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args={
        "connect_timeout": 10,
        "ssl": {}
    }
)

# Verify the connection; fail visibly instead of silently using SQLite
with engine.connect() as conn:
    conn.exec_driver_sql("SELECT 1")

logger.info(
    "Successfully connected to MySQL database: %s",
    settings.DB_NAME
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def init_db():
    import app.models
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()