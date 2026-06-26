"""
MuleShield AI Ensemble Model.
Combines XGBoost, LightGBM, CatBoost, Isolation Forest, Autoencoder, and GNN
with configurable weights to produce a 0–1000 risk score.
"""
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Tuple

import numpy as np
import joblib

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=6)

# Default ensemble weights (must sum to 1.0)
DEFAULT_WEIGHTS = {
    "xgboost": 0.30,
    "lightgbm": 0.25,
    "catboost": 0.15,
    "isolation_forest": 0.15,
    "autoencoder": 0.10,
    "gnn": 0.05,  # Reduced since GNN requires graph data; remaining 0.10 distributed
}


class AutoencoderModel:
    """Simple PyTorch autoencoder for anomaly detection via reconstruction error."""

    def __init__(self, input_dim: int, hidden_dim: int = 64):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.model = None
        self._build()

    def _build(self):
        try:
            import torch
            import torch.nn as nn

            class _AE(nn.Module):
                def __init__(self, in_dim, h_dim):
                    super().__init__()
                    self.encoder = nn.Sequential(
                        nn.Linear(in_dim, h_dim * 2),
                        nn.ReLU(),
                        nn.Linear(h_dim * 2, h_dim),
                        nn.ReLU(),
                    )
                    self.decoder = nn.Sequential(
                        nn.Linear(h_dim, h_dim * 2),
                        nn.ReLU(),
                        nn.Linear(h_dim * 2, in_dim),
                    )

                def forward(self, x):
                    z = self.encoder(x)
                    return self.decoder(z)

            self.torch = torch
            self.nn = nn
            self.model = _AE(self.input_dim, self.hidden_dim)
        except ImportError:
            logger.warning("PyTorch not available — autoencoder will return zeros.")
            self.model = None

    def fit(self, X: np.ndarray, epochs: int = 20, batch_size: int = 256, lr: float = 1e-3):
        if self.model is None:
            return self
        import torch
        optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)
        criterion = torch.nn.MSELoss()
        X_tensor = torch.FloatTensor(X)
        self.model.train()
        dataset = torch.utils.data.TensorDataset(X_tensor)
        loader = torch.utils.data.DataLoader(dataset, batch_size=batch_size, shuffle=True)
        for epoch in range(epochs):
            total_loss = 0.0
            for (batch,) in loader:
                optimizer.zero_grad()
                recon = self.model(batch)
                loss = criterion(recon, batch)
                loss.backward()
                optimizer.step()
                total_loss += loss.item()
            if (epoch + 1) % 5 == 0:
                logger.debug(f"AE Epoch {epoch+1}/{epochs} loss: {total_loss/len(loader):.6f}")
        self.model.eval()
        # Compute reconstruction error threshold (95th percentile on training)
        with torch.no_grad():
            recon = self.model(X_tensor)
            errors = ((X_tensor - recon) ** 2).mean(dim=1).numpy()
        self._threshold = float(np.percentile(errors, 95))
        self._max_error = float(errors.max()) + 1e-9
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Return anomaly probability in [0, 1] based on reconstruction error."""
        if self.model is None:
            return np.zeros(len(X))
        import torch
        self.model.eval()
        with torch.no_grad():
            X_tensor = torch.FloatTensor(X)
            recon = self.model(X_tensor)
            errors = ((X_tensor - recon) ** 2).mean(dim=1).numpy()
        # Normalize to [0, 1]
        probs = np.clip(errors / self._max_error, 0.0, 1.0)
        return probs


class MuleShieldEnsemble:
    """Weighted ensemble of fraud detection models."""

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or DEFAULT_WEIGHTS
        self._normalize_weights()
        self.models: Dict = {}
        self.feature_names: List[str] = []
        self.is_fitted = False
        self.model_version: Optional[str] = None

    def _normalize_weights(self):
        """Ensure weights sum to 1.0."""
        total = sum(self.weights.values())
        if abs(total - 1.0) > 1e-6:
            self.weights = {k: v / total for k, v in self.weights.items()}

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_test: np.ndarray,
        y_test: np.ndarray,
        feature_names: Optional[List[str]] = None,
    ) -> Dict:
        """Train all ensemble components in parallel. Returns metrics dict."""
        self.feature_names = feature_names or [f"F{i}" for i in range(X_train.shape[1])]
        metrics = {}
        scale_pos_weight = float(np.sum(y_train == 0)) / max(float(np.sum(y_train == 1)), 1)

        def _train_xgboost():
            import xgboost as xgb
            model = xgb.XGBClassifier(
                n_estimators=300, max_depth=6, learning_rate=0.05,
                subsample=0.8, colsample_bytree=0.8,
                scale_pos_weight=scale_pos_weight,
                use_label_encoder=False, eval_metric="auc",
                random_state=42, n_jobs=-1, verbosity=0,
            )
            model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)
            return "xgboost", model

        def _train_lightgbm():
            import lightgbm as lgb
            model = lgb.LGBMClassifier(
                n_estimators=300, learning_rate=0.05, num_leaves=63,
                subsample=0.8, colsample_bytree=0.8,
                class_weight="balanced", random_state=42, n_jobs=-1, verbose=-1,
            )
            model.fit(X_train, y_train, eval_set=[(X_test, y_test)])
            return "lightgbm", model

        def _train_catboost():
            from catboost import CatBoostClassifier
            model = CatBoostClassifier(
                iterations=300, learning_rate=0.05, depth=6,
                class_weights=[1, int(scale_pos_weight)],
                random_seed=42, verbose=0,
            )
            model.fit(X_train, y_train, eval_set=(X_test, y_test), plot=False)
            return "catboost", model

        def _train_isolation_forest():
            from sklearn.ensemble import IsolationForest
            contamination = float(np.mean(y_train == 1))
            contamination = max(0.01, min(contamination, 0.5))
            model = IsolationForest(n_estimators=200, contamination=contamination, random_state=42, n_jobs=-1)
            model.fit(X_train)
            return "isolation_forest", model

        def _train_autoencoder():
            ae = AutoencoderModel(input_dim=X_train.shape[1], hidden_dim=128)
            ae.fit(X_train[y_train == 0], epochs=20)
            return "autoencoder", ae

        trainers = [_train_xgboost, _train_lightgbm, _train_catboost, _train_isolation_forest, _train_autoencoder]
        with ThreadPoolExecutor(max_workers=len(trainers)) as executor:
            futures = [executor.submit(fn) for fn in trainers]
            for future in futures:
                try:
                    name, model = future.result()
                    self.models[name] = model
                    metrics[name] = "trained"
                    logger.info(f"{name} trained successfully.")
                except Exception as e:
                    logger.error(f"Training failed: {e}")
                    metrics["training_error"] = str(e)

        metrics["gnn"] = "skipped (requires graph topology)"
        self.is_fitted = True
        return metrics

    def _isolation_forest_prob(self, X: np.ndarray) -> np.ndarray:
        """Convert Isolation Forest scores to [0, 1] anomaly probabilities."""
        if_model = self.models.get("isolation_forest")
        if if_model is None:
            return np.zeros(len(X))
        # scores are negative: lower = more anomalous
        scores = if_model.score_samples(X)
        # Normalize: most negative → 1 (anomaly), least negative → 0 (normal)
        min_s, max_s = scores.min(), scores.max()
        if max_s == min_s:
            return np.zeros(len(X))
        probs = 1.0 - (scores - min_s) / (max_s - min_s)
        return np.clip(probs, 0.0, 1.0)

    def predict_proba_single(self, x: np.ndarray) -> Tuple[float, Dict[str, float]]:
        """
        Predict fraud probability for a single feature vector.
        Runs ensemble models in parallel via ThreadPoolExecutor.
        Returns (ensemble_prob, per_model_probs).
        Idempotent: same input → same output.
        """
        X = x.reshape(1, -1)
        component_probs: Dict[str, float] = {}

        def _predict(name: str) -> Tuple[str, float]:
            model = self.models.get(name)
            if model is None:
                return name, -1.0
            if name in ("xgboost", "lightgbm", "catboost"):
                return name, float(model.predict_proba(X)[0, 1])
            elif name == "isolation_forest":
                return name, float(self._isolation_forest_prob(X)[0])
            elif name == "autoencoder":
                return name, float(model.predict_proba(X)[0])
            elif name == "gnn":
                return name, 0.5
            return name, -1.0

        tasks = [name for name in self.weights if self.models.get(name) is not None]
        if not tasks:
            return 0.0, {}

        futures = {_executor.submit(_predict, name): name for name in tasks}
        weighted_sum = 0.0
        active_weight = 0.0
        for future in futures:
            try:
                name, prob = future.result()
                if prob >= 0.0:
                    component_probs[name] = prob
                    weighted_sum += self.weights[name] * prob
                    active_weight += self.weights[name]
            except Exception as e:
                name = futures[future]
                logger.warning(f"Model {name} prediction failed: {e}")

        ensemble_prob = weighted_sum / active_weight if active_weight > 0 else 0.0
        return float(np.clip(ensemble_prob, 0.0, 1.0)), component_probs

    def predict_proba_batch(self, X: np.ndarray) -> np.ndarray:
        """Batch prediction — uses vectorized model predictions where possible."""
        n = len(X)
        weighted_sum = np.zeros(n, dtype=float)
        active_weight = 0.0

        for name, weight in self.weights.items():
            model = self.models.get(name)
            if model is None:
                continue
            try:
                if name in ("xgboost", "lightgbm", "catboost"):
                    probs = model.predict_proba(X)[:, 1]
                elif name == "isolation_forest":
                    probs = self._isolation_forest_prob(X)
                elif name == "autoencoder":
                    probs = model.predict_proba(X)
                elif name == "gnn":
                    probs = np.full(n, 0.5, dtype=float)
                else:
                    continue
                weighted_sum += weight * probs
                active_weight += weight
            except Exception as e:
                logger.warning(f"Model {name} batch prediction failed: {e}")

        ensemble_probs = weighted_sum / active_weight if active_weight > 0 else np.zeros(n)
        return np.clip(ensemble_probs, 0.0, 1.0)

    def save(self, artifacts_dir: str):
        """Persist all trained models to disk."""
        os.makedirs(artifacts_dir, exist_ok=True)
        for name, model in self.models.items():
            path = os.path.join(artifacts_dir, f"{name}.pkl")
            joblib.dump(model, path)
        joblib.dump({"weights": self.weights, "feature_names": self.feature_names, "version": self.model_version}, os.path.join(artifacts_dir, "ensemble_meta.pkl"))
        logger.info(f"Ensemble saved to {artifacts_dir}")

    @classmethod
    def load(cls, artifacts_dir: str) -> "MuleShieldEnsemble":
        """Load a previously saved ensemble from disk."""
        meta_path = os.path.join(artifacts_dir, "ensemble_meta.pkl")
        if not os.path.exists(meta_path):
            raise FileNotFoundError(f"Ensemble metadata not found at {meta_path}")
        meta = joblib.load(meta_path)
        ensemble = cls(weights=meta["weights"])
        ensemble.feature_names = meta.get("feature_names", [])
        ensemble.model_version = meta.get("version")

        model_names = ["xgboost", "lightgbm", "catboost", "isolation_forest", "autoencoder"]
        for name in model_names:
            path = os.path.join(artifacts_dir, f"{name}.pkl")
            if os.path.exists(path):
                ensemble.models[name] = joblib.load(path)
                logger.info(f"Loaded model: {name}")
            else:
                logger.warning(f"Model artifact not found: {path}")

        ensemble.is_fitted = bool(ensemble.models)
        return ensemble
