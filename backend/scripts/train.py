#!/usr/bin/env python3
"""
MuleShield AI Training Pipeline
Usage: python scripts/train.py --data /path/to/DataSet.csv
"""
import argparse
import hashlib
import logging
import os
import sys
from datetime import datetime, timezone

# Allow running from scripts/ directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def compute_checksum(path: str) -> str:
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def main():
    parser = argparse.ArgumentParser(description="Train MuleShield AI ensemble models.")
    parser.add_argument("--data", default="./data/DataSet.csv", help="Path to DataSet.csv")
    parser.add_argument("--artifacts", default="./artifacts", help="Directory to save model artifacts")
    parser.add_argument("--missing-threshold", type=float, default=0.70)
    parser.add_argument("--test-size", type=float, default=0.20)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--mlflow-uri", default=None, help="MLflow tracking URI (optional)")
    args = parser.parse_args()

    # Check dataset existence
    if not os.path.exists(args.data):
        logger.warning(f"DataSet not found at: {args.data}. Skipping training.")
        sys.exit(0)

    checksum = compute_checksum(args.data)
    logger.info(f"Dataset: {args.data}")
    logger.info(f"SHA-256: {checksum}")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    # ── MLflow setup (optional) ────────────────────────────────────────────────
    mlflow_available = False
    run_id = None
    if args.mlflow_uri:
        try:
            import mlflow
            mlflow.set_tracking_uri(args.mlflow_uri)
            mlflow.set_experiment("muleshield-ensemble")
            mlflow.start_run(run_name=f"train_{timestamp}")
            mlflow.log_param("dataset_path", args.data)
            mlflow.log_param("dataset_checksum", checksum)
            mlflow.log_param("missing_threshold", args.missing_threshold)
            mlflow.log_param("test_size", args.test_size)
            mlflow.log_param("random_seed", args.seed)
            run_id = mlflow.active_run().info.run_id
            mlflow_available = True
            logger.info(f"MLflow run started: {run_id}")
        except Exception as e:
            logger.warning(f"MLflow not available: {e}. Training without experiment tracking.")

    # ── Preprocessing ──────────────────────────────────────────────────────────
    from app.ml.preprocessor import load_and_preprocess
    try:
        X_train, X_test, y_train, y_test, scaler, stats = load_and_preprocess(
            data_path=args.data,
            artifacts_dir=args.artifacts,
            missing_threshold=args.missing_threshold,
            test_size=args.test_size,
            random_seed=args.seed,
        )
    except Exception as e:
        logger.error(f"Preprocessing failed: {e}")
        sys.exit(1)

    logger.info(f"Training set: {X_train.shape[0]} rows, {X_train.shape[1]} features")
    logger.info(f"Test set: {X_test.shape[0]} rows")
    logger.info(f"Fraud rate (train): {y_train.mean():.4f}")

    # ── Ensemble Training ──────────────────────────────────────────────────────
    from app.ml.ensemble import MuleShieldEnsemble

    weights = {
        "xgboost": float(os.getenv("XGBOOST_WEIGHT", "0.30")),
        "lightgbm": float(os.getenv("LIGHTGBM_WEIGHT", "0.25")),
        "catboost": float(os.getenv("CATBOOST_WEIGHT", "0.15")),
        "isolation_forest": float(os.getenv("ISOLATION_FOREST_WEIGHT", "0.15")),
        "autoencoder": float(os.getenv("AUTOENCODER_WEIGHT", "0.10")),
        "gnn": float(os.getenv("GNN_WEIGHT", "0.05")),
    }
    logger.info(f"Ensemble weights: {weights}")

    ensemble = MuleShieldEnsemble(weights=weights)
    feature_names = stats.get("feature_columns", [f"F{i}" for i in range(X_train.shape[1])])
    train_metrics = ensemble.fit(X_train, y_train, X_test, y_test, feature_names=feature_names)
    logger.info(f"Training results: {train_metrics}")

    # ── Evaluation ─────────────────────────────────────────────────────────────
    eval_metrics = {}
    try:
        import numpy as np
        from sklearn.metrics import roc_auc_score, average_precision_score, f1_score, confusion_matrix

        y_proba = ensemble.predict_proba_batch(X_test)
        y_pred = (y_proba >= 0.5).astype(int)

        auc_roc = float(roc_auc_score(y_test, y_proba))
        auc_pr = float(average_precision_score(y_test, y_proba))
        f1 = float(f1_score(y_test, y_pred, zero_division=0))
        cm = confusion_matrix(y_test, y_pred).tolist()

        eval_metrics = {
            "auc_roc": round(auc_roc, 4),
            "auc_pr": round(auc_pr, 4),
            "f1_score": round(f1, 4),
            "confusion_matrix": cm,
        }
        logger.info(f"Evaluation metrics: {eval_metrics}")

        if auc_roc < 0.80:
            logger.warning(f"AUC-ROC {auc_roc:.4f} is below target of 0.80. Consider more training data or hyperparameter tuning.")
        else:
            logger.info(f"✓ AUC-ROC {auc_roc:.4f} meets target (≥ 0.80)")

        if mlflow_available:
            mlflow.log_metrics(eval_metrics)
    except Exception as e:
        logger.warning(f"Evaluation failed: {e}")

    # ── Save model artifacts ───────────────────────────────────────────────────
    ensemble.model_version = f"{timestamp}_{checksum[:8]}"
    ensemble.save(args.artifacts)

    # Save MLflow metrics to file for API to read
    import json
    metrics_path = os.path.join(args.artifacts, "eval_metrics.json")
    with open(metrics_path, "w") as f:
        json.dump({**eval_metrics, "model_version": ensemble.model_version, "trained_at": timestamp}, f, indent=2)
    logger.info(f"Metrics saved to {metrics_path}")

    if mlflow_available:
        mlflow.log_artifact(args.artifacts)
        mlflow.end_run()

    logger.info(f"✓ Training complete. Artifacts saved to: {args.artifacts}")
    logger.info(f"  Model version: {ensemble.model_version}")
    sys.exit(0)


if __name__ == "__main__":
    main()
