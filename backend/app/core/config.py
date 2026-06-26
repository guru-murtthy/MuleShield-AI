"""Application configuration via environment variables."""
from functools import lru_cache
from typing import List, Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_NAME: str = "MuleShield AI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str = "changeme-use-strong-secret-in-production"

    # API
    API_V1_PREFIX: str = "/api/v1"
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:80"]

    # Redis / Feature Store
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL_SECONDS: int = 60

    # Database (SQLite by default for easy local dev)
    DATABASE_URL: str = "sqlite:///./muleshield.db"

    # MLflow
    MLFLOW_TRACKING_URI: str = "http://localhost:5000"
    MLFLOW_EXPERIMENT_NAME: str = "muleshield-ensemble"

    # Model artifacts
    MODEL_ARTIFACTS_DIR: str = "./artifacts"
    DATASET_PATH: str = "./data/DataSet.csv"

    # Ensemble weights
    XGBOOST_WEIGHT: float = 0.30
    LIGHTGBM_WEIGHT: float = 0.25
    CATBOOST_WEIGHT: float = 0.15
    ISOLATION_FOREST_WEIGHT: float = 0.15
    AUTOENCODER_WEIGHT: float = 0.10
    GNN_WEIGHT: float = 0.15

    # Risk thresholds
    SCORE_CACHE_TTL: int = 60  # seconds

    # Regulator auth token
    REGULATOR_TOKEN: str = "regulator-secret-token"

    # Kill switch
    KILL_SWITCH_ACTIVE: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()
