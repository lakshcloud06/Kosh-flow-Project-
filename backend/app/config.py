import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from backend/.env or local .env
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

class Settings:
    """Application configuration loaded from backend/.env."""
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_NAME: str = os.getenv("DB_NAME", "koshflow")
    JWT_SECRET: str = os.getenv("JWT_SECRET", "koshflow_secret_key_atm_cash_demand_forecasting_2026")
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))
    ALGORITHM: str = "HS256"

# Global settings instance
settings = Settings()
print("========== DATABASE CONFIG CHECK ==========")
print("DB_HOST:", settings.DB_HOST)
print("DB_PORT:", settings.DB_PORT)
print("DB_USER:", settings.DB_USER)
print("DB_NAME:", settings.DB_NAME)
print("===========================================")