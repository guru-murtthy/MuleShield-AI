"""
MuleShield AI — FastAPI Application Entry Point
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, make_asgi_app

from app.api.routes import router
from app.core.config import get_settings
from app.core.database import Base, engine
from app.services.model_service import load_artifacts

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()

# Prometheus metrics
REQUEST_COUNT = Counter("muleshield_requests_total", "Total API requests", ["method", "endpoint"])
SCORE_LATENCY = Histogram("muleshield_score_latency_seconds", "Score endpoint latency")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("MuleShield AI starting up...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created.")
    loaded = load_artifacts()
    if loaded:
        logger.info("✓ ML models loaded and ready.")
    else:
        logger.warning("⚠ No trained models found. Run: python scripts/train.py --data <DataSet.csv>")
    yield
    # Shutdown
    logger.info("MuleShield AI shutting down.")


app = FastAPI(
    title="MuleShield AI",
    description=(
        "AI-powered mule account detection and fraud prevention for Public Sector Banks. "
        "Ensemble of XGBoost + LightGBM + CatBoost + Isolation Forest + Autoencoder "
        "producing a 0–1000 Risk Score."
    ),
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(router, prefix=settings.API_V1_PREFIX)

# Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


@app.get("/", tags=["Root"])
def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": f"{settings.API_V1_PREFIX}/health",
    }
