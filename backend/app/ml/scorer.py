"""
Risk scoring logic: converts ensemble probability → Risk_Score (0–1000) and Risk_Band.
Also handles detection pattern classification and SHAP explainability.
"""
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

RISK_BANDS = [
    (0, 199, "MINIMAL"),
    (200, 399, "LOW"),
    (400, 599, "MEDIUM"),
    (600, 799, "HIGH"),
    (800, 1000, "CRITICAL"),
]

DETECTION_PATTERNS = [
    "Smurfing",
    "Structuring",
    "Rapid_Fund_Movement",
    "Round_Tripping",
    "Layering",
    "Cash_In_Cash_Out",
    "Dormant_Activation",
    "Account_Takeover",
    "Synthetic_Identity",
    "Multi_Account_Abuse",
    "Cross_Channel_Laundering",
]

PATTERN_SCORE_RANGES = {
    "Smurfing": (500, 750),
    "Structuring": (500, 700),
    "Rapid_Fund_Movement": (600, 800),
    "Round_Tripping": (600, 800),
    "Layering": (700, 900),
    "Cash_In_Cash_Out": (550, 700),
    "Dormant_Activation": (400, 600),
    "Account_Takeover": (700, 900),
    "Synthetic_Identity": (800, 1000),
    "Multi_Account_Abuse": (600, 800),
    "Cross_Channel_Laundering": (800, 1000),
}


@dataclass
class SHAPFeature:
    name: str
    shap_value: float
    direction: str  # "positive" or "negative"


@dataclass
class DetectionPatternResult:
    pattern: str
    confidence: float


@dataclass
class ScoreResult:
    account_id: str
    risk_score: int
    risk_band: str
    ensemble_probability: float
    component_probs: Dict[str, float] = field(default_factory=dict)
    top_patterns: List[DetectionPatternResult] = field(default_factory=list)
    shap_features: List[SHAPFeature] = field(default_factory=list)
    narrative: str = ""
    auto_freeze_eligible: bool = False
    shap_available: bool = True
    str_draft: Optional[Dict] = None
    model_version: Optional[str] = None


def probability_to_score(prob: float) -> int:
    """Convert ensemble probability [0,1] to Risk_Score [0,1000]."""
    return int(round(float(np.clip(prob, 0.0, 1.0)) * 1000))


def score_to_band(score: int) -> str:
    """Map Risk_Score to Risk_Band."""
    for low, high, band in RISK_BANDS:
        if low <= score <= high:
            return band
    return "CRITICAL"


def compute_shap_values(
    ensemble,
    x: np.ndarray,
    feature_names: List[str],
    top_k: int = 10,
    explainer=None,
) -> Tuple[List[SHAPFeature], bool]:
    """Compute SHAP attributions for the primary model (XGBoost)."""
    try:
        import shap
        if explainer is None:
            xgb_model = ensemble.models.get("xgboost")
            if xgb_model is None:
                return [], False
            explainer = shap.TreeExplainer(xgb_model)
        shap_vals = explainer.shap_values(x.reshape(1, -1))
        # For binary classification, shap_values may be a list [neg, pos]
        if isinstance(shap_vals, list):
            shap_array = shap_vals[1][0]
        else:
            shap_array = shap_vals[0]
        indices = np.argsort(np.abs(shap_array))[::-1][:top_k]
        features = []
        for i in indices:
            name = feature_names[i] if i < len(feature_names) else f"F{i}"
            val = float(shap_array[i])
            features.append(SHAPFeature(
                name=name,
                shap_value=round(val, 4),
                direction="positive" if val > 0 else "negative",
            ))
        return features, True
    except Exception as e:
        logger.warning(f"SHAP computation failed: {e}")
        return [], False


def classify_detection_patterns(
    risk_score: int,
    shap_features: List[SHAPFeature],
    component_probs: Dict[str, float],
) -> List[DetectionPatternResult]:
    """
    Classify fraud typologies using rule-based heuristics on SHAP values and score.
    Returns top-3 patterns ranked by confidence.
    """
    results: Dict[str, float] = {}

    # Heuristic: score falls within pattern's typical range → baseline confidence
    for pattern, (lo, hi) in PATTERN_SCORE_RANGES.items():
        if lo <= risk_score <= hi:
            range_width = hi - lo
            score_pos = (risk_score - lo) / range_width
            # Peak confidence at center of range
            results[pattern] = 0.3 + 0.4 * (1.0 - 2.0 * abs(score_pos - 0.5))

    # Boost based on SHAP feature names (heuristic pattern matching)
    shap_names = {f.name.lower() for f in shap_features[:5]}
    boosters = {
        "Smurfing": {"upi", "split", "count", "frequency"},
        "Structuring": {"amount", "threshold", "deposit", "cash"},
        "Rapid_Fund_Movement": {"debit", "credit", "velocity", "time"},
        "Round_Tripping": {"cycle", "hop", "return", "graph"},
        "Layering": {"hop", "chain", "network", "layer"},
        "Cash_In_Cash_Out": {"atm", "cash", "withdrawal", "branch"},
        "Dormant_Activation": {"dormant", "inactive", "days"},
        "Account_Takeover": {"device", "login", "password", "reset"},
        "Synthetic_Identity": {"kyc", "identity", "synthetic"},
        "Multi_Account_Abuse": {"multi", "account", "shared"},
        "Cross_Channel_Laundering": {"channel", "upi", "neft", "imps"},
    }
    for pattern, keywords in boosters.items():
        overlap = len(keywords & shap_names)
        if overlap > 0:
            results[pattern] = results.get(pattern, 0.1) + 0.15 * overlap

    # Sort and return top 3
    sorted_patterns = sorted(results.items(), key=lambda x: x[1], reverse=True)
    top_3 = sorted_patterns[:3]

    if not top_3 or top_3[0][1] < 0.20:
        return [DetectionPatternResult(pattern="UNKNOWN", confidence=0.0)]

    return [
        DetectionPatternResult(pattern=p, confidence=round(min(c, 1.0), 3))
        for p, c in top_3
    ]


def generate_narrative(
    account_id: str,
    risk_score: int,
    risk_band: str,
    top_patterns: List[DetectionPatternResult],
    shap_features: List[SHAPFeature],
) -> str:
    """Generate a plain-English explanation paragraph from SHAP attributions."""
    top_features = [f.name for f in shap_features[:3]] if shap_features else ["unknown features"]
    top_pattern = top_patterns[0].pattern if top_patterns else "UNKNOWN"
    top_confidence = top_patterns[0].confidence if top_patterns else 0.0

    action_text = {
        "MINIMAL": "No immediate action required. Continue routine monitoring.",
        "LOW": "Enhanced monitoring recommended.",
        "MEDIUM": "Alert raised for analyst review within 4 hours.",
        "HIGH": "Soft freeze recommended. Senior analyst notified.",
        "CRITICAL": "Hard freeze applied. AML team notified. STR draft generated.",
    }.get(risk_band, "Review required.")

    return (
        f"Account {account_id} received a Risk Score of {risk_score}/1000 (Band: {risk_band}). "
        f"The primary fraud pattern identified is {top_pattern} "
        f"(confidence: {top_confidence:.0%}). "
        f"Key risk drivers include: {', '.join(top_features)}. "
        f"{action_text}"
    )


def generate_str_draft(
    account_id: str,
    risk_score: int,
    risk_band: str,
    top_patterns: List[DetectionPatternResult],
    shap_features: List[SHAPFeature],
    model_version: Optional[str] = None,
) -> Dict:
    """Generate a pre-filled goAML STR draft for HIGH/CRITICAL accounts."""
    from datetime import datetime, timezone
    return {
        "str_type": "goAML",
        "schema_version": "2.0",
        "subject": {
            "account_id": account_id,
            "risk_score": risk_score,
            "risk_band": risk_band,
        },
        "suspicion_reason": {
            "primary_pattern": top_patterns[0].pattern if top_patterns else "UNKNOWN",
            "confidence": top_patterns[0].confidence if top_patterns else 0.0,
            "top_shap_features": [
                {"name": f.name, "contribution": f.shap_value}
                for f in shap_features[:3]
            ],
        },
        "narrative": generate_narrative(account_id, risk_score, risk_band, top_patterns, shap_features),
        "model_version": model_version,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "draft",
    }
