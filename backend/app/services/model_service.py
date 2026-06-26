"""
Model service — singleton that loads/holds the trained ensemble and preprocessing artifacts.
"""
import logging
import os
from typing import Optional

import joblib
import numpy as np

from app.core.config import get_settings
from app.ml.ensemble import MuleShieldEnsemble

logger = logging.getLogger(__name__)
settings = get_settings()

_ensemble: Optional[MuleShieldEnsemble] = None
_preprocessing_stats: Optional[dict] = None
_scaler = None
_shap_explainer = None


def get_ensemble() -> Optional[MuleShieldEnsemble]:
    return _ensemble


def get_scaler():
    return _scaler


def get_preprocessing_stats() -> Optional[dict]:
    return _preprocessing_stats


def get_shap_explainer():
    return _shap_explainer


def _init_shap_explainer():
    global _shap_explainer
    if _ensemble is None:
        return
    xgb_model = _ensemble.models.get("xgboost")
    if xgb_model is None:
        return
    try:
        import shap
        _shap_explainer = shap.TreeExplainer(xgb_model)
        logger.info("SHAP TreeExplainer created and cached.")
    except Exception as e:
        logger.warning(f"SHAP TreeExplainer creation failed: {e}")


def load_artifacts() -> bool:
    """
    Load trained model artifacts from disk.
    Returns True if all essential models are loaded, False otherwise.
    """
    global _ensemble, _preprocessing_stats, _scaler
    artifacts_dir = settings.MODEL_ARTIFACTS_DIR

    scaler_path = os.path.join(artifacts_dir, "scaler.pkl")
    stats_path = os.path.join(artifacts_dir, "preprocessing_stats.pkl")
    meta_path = os.path.join(artifacts_dir, "ensemble_meta.pkl")

    if not os.path.exists(meta_path):
        logger.warning(f"No trained model found at {artifacts_dir}. API will start without scoring capability.")
        return False

    try:
        _ensemble = MuleShieldEnsemble.load(artifacts_dir)
        logger.info(f"Ensemble loaded with {len(_ensemble.models)} models: {list(_ensemble.models.keys())}")
    except Exception as e:
        logger.error(f"Failed to load ensemble: {e}")
        return False

    if os.path.exists(scaler_path):
        _scaler = joblib.load(scaler_path)
        logger.info("Scaler loaded.")
    else:
        logger.warning("Scaler not found — feature normalization will be skipped.")

    if os.path.exists(stats_path):
        _preprocessing_stats = joblib.load(stats_path)
        logger.info(f"Preprocessing stats loaded. Features: {_preprocessing_stats.get('n_features')}")

    _init_shap_explainer()
    return True


def preprocess_features(feature_vector: list) -> np.ndarray:
    """
    Apply the same preprocessing (imputation + scaling) used during training.
    """
    x = np.array(feature_vector, dtype=float)
    stats = _preprocessing_stats

    if stats and "train_medians" in stats:
        medians = np.array(stats["train_medians"])
        n = min(len(x), len(medians))
        x[:n] = np.where(np.isnan(x[:n]), medians[:n], x[:n])

    x = np.where(np.isnan(x), 0.0, x)

    if _scaler is not None:
        expected = len(_scaler.mean_) if hasattr(_scaler, 'mean_') else len(x)
        if len(x) >= expected:
            return _scaler.transform(x[:expected].reshape(1, -1))[0]
        padded = np.zeros(expected)
        padded[:len(x)] = x
        return _scaler.transform(padded.reshape(1, -1))[0]

    return x
