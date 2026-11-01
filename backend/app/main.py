from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app.routers import (
    auth_router,
    dashboard_router,
    forecast_router,
    plan_router,
    model_router,
    alerts_router,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager creating database tables on startup."""
    init_db()
    yield

# Initialize FastAPI application
app = FastAPI(
    title="Koshflow Backend API",
    description="ATM Cash Demand Predictor and Smart Replenishment System",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for frontend applications
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://localhost:80",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router.router)
app.include_router(dashboard_router.router)
app.include_router(forecast_router.router)
app.include_router(plan_router.router)
app.include_router(model_router.router)
app.include_router(alerts_router.router)

@app.get("/")
def root():
    """Health check endpoint confirming API service status."""
    return {
        "status": "online",
        "service": "Koshflow - ATM Cash Demand Predictor",
        "version": "1.0.0"
    }

@app.get("/health")
def health():
    """Service health verification."""
    return {"status": "healthy"}
