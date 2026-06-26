"""
Data preprocessing pipeline for MuleShield AI.
Handles DataSet.csv with 9,082 rows × 3,924 anonymized feature columns (F1–F3924).
"""
import hashlib
import logging
import os
from typing import Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import joblib

logger = logging.getLogger(__name__)

# Columns to always exclude from features
EXCLUDE_COLS = {"Unnamed: 0", ""}


def compute_dataset_checksum(path: str) -> str:
    """Compute SHA-256 checksum of the dataset file."""
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def infer_label_column(df: pd.DataFrame) -> Optional[str]:
    """
    Heuristically identify the label column.
    Looks for binary (0/1) integer columns with low cardinality near the end.
    Falls back to generating a synthetic label based on anomaly score if none found.
    """
    # Try common label column names first
    for candidate in ["label", "Label", "is_mule", "fraud", "target", "y"]:
        if candidate in df.columns:
            return candidate

    # Look for binary integer columns with ~1–15% positive rate (fraud is rare)
    for col in reversed(df.columns.tolist()):
        if df[col].dtype in [np.int64, np.int32, np.float64]:
            uniq = df[col].dropna().unique()
            if set(uniq).issubset({0, 1, 0.0, 1.0}):
                pos_rate = df[col].mean()
                if 0.001 <= pos_rate <= 0.20:
                    logger.info(f"Inferred label column: {col} (positive rate: {pos_rate:.3f})")
                    return col
    return None


def load_and_preprocess(
    data_path: str,
    artifacts_dir: str,
    missing_threshold: float = 0.70,
    test_size: float = 0.20,
    random_seed: int = 42,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, StandardScaler, dict]:
    """
    Load DataSet.csv, clean it, and return train/test splits.

    Returns:
        X_train, X_test, y_train, y_test, scaler, preprocessing_stats
    """
    logger.info(f"Loading dataset from: {data_path}")
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Dataset not found at: {data_path}")

    checksum = compute_dataset_checksum(data_path)
    logger.info(f"Dataset checksum (SHA-256): {checksum}")

    df = pd.read_csv(data_path, low_memory=False)
    logger.info(f"Loaded dataset shape: {df.shape}")

    # Drop unnamed index columns
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]

    # Identify label column
    label_col = infer_label_column(df)
    if label_col is None:
        logger.warning("No label column found — generating synthetic labels via IQR anomaly scoring.")
        label_col = "_synthetic_label"
        # Use numeric columns to build a simple anomaly proxy
        numeric = df.select_dtypes(include=[np.number])
        numeric = numeric.fillna(numeric.median())
        # Z-score based synthetic label: top 5% as "mule" (fraud=1)
        z_scores = np.abs((numeric - numeric.mean()) / (numeric.std() + 1e-9))
        anomaly_score = z_scores.mean(axis=1)
        threshold = anomaly_score.quantile(0.95)
        df[label_col] = (anomaly_score >= threshold).astype(int)
        logger.info(f"Synthetic label distribution: {df[label_col].value_counts().to_dict()}")

    # Separate features and labels
    y = df[label_col].fillna(0).astype(int).values
    feature_cols = [c for c in df.columns if c != label_col]

    # Keep only numeric columns for ML
    feature_df = df[feature_cols].select_dtypes(include=[np.number])
    logger.info(f"Numeric feature columns before filtering: {feature_df.shape[1]}")

    # Drop high-missing columns (> missing_threshold)
    missing_rates = feature_df.isnull().mean()
    low_missing_cols = missing_rates[missing_rates <= missing_threshold].index.tolist()
    feature_df = feature_df[low_missing_cols]
    logger.info(f"Columns after dropping >{missing_threshold*100:.0f}% missing: {feature_df.shape[1]}")

    # Drop constant columns
    non_constant = feature_df.std() > 0
    feature_df = feature_df.loc[:, non_constant]
    logger.info(f"Columns after dropping constants: {feature_df.shape[1]}")

    stats = {
        "n_rows": len(df),
        "n_features": feature_df.shape[1],
        "label_col": label_col,
        "dataset_checksum": checksum,
        "missing_threshold": missing_threshold,
        "feature_columns": feature_df.columns.tolist(),
        "positive_rate": float(y.mean()),
    }

    # Stratified train/test split
    X = feature_df.values
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, stratify=y, random_state=random_seed
    )

    # Impute with column median (computed on training split only)
    train_medians = np.nanmedian(X_train, axis=0)
    stats["train_medians"] = train_medians.tolist()

    X_train = np.where(np.isnan(X_train), train_medians, X_train)
    X_test = np.where(np.isnan(X_test), train_medians, X_test)

    # StandardScaler normalization
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test = scaler.transform(X_test)

    # Save artifacts
    os.makedirs(artifacts_dir, exist_ok=True)
    joblib.dump(scaler, os.path.join(artifacts_dir, "scaler.pkl"))
    joblib.dump(stats, os.path.join(artifacts_dir, "preprocessing_stats.pkl"))
    logger.info(f"Preprocessing artifacts saved to: {artifacts_dir}")

    logger.info(
        f"Split: train={X_train.shape[0]}, test={X_test.shape[0]}, "
        f"features={X_train.shape[1]}, fraud_rate={y.mean():.4f}"
    )
    return X_train, X_test, y_train, y_test, scaler, stats
