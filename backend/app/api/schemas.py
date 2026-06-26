"""Pydantic request/response schemas."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ── Score ──────────────────────────────────────────────────────────────────────

class ScoreRequest(BaseModel):
    account_id: str = Field(..., description="Unique account identifier")
    features: List[float] = Field(..., description="Feature vector (F1–F3924)")

    model_config = {"json_schema_extra": {
        "example": {
            "account_id": "ACC-001234",
            "features": [0.0] * 50,
        }
    }}


class SHAPFeatureResponse(BaseModel):
    name: str
    shap_value: float
    direction: str  # "positive" | "negative"


class DetectionPatternResponse(BaseModel):
    pattern: str
    confidence: float


class ScoreResponse(BaseModel):
    account_id: str
    risk_score: int = Field(..., ge=0, le=1000)
    risk_band: str
    ensemble_probability: float
    component_probs: Dict[str, float] = {}
    top_patterns: List[DetectionPatternResponse] = []
    shap_features: List[SHAPFeatureResponse] = []
    narrative: str = ""
    auto_freeze_eligible: bool = False
    shap_available: bool = True
    str_draft: Optional[Dict[str, Any]] = None
    model_version: Optional[str] = None
    cached: bool = False


# ── Alerts ─────────────────────────────────────────────────────────────────────

class AlertItem(BaseModel):
    account_id: str
    risk_score: int
    risk_band: str
    top_pattern: Optional[str] = None
    auto_freeze_eligible: bool = False
    scored_at: Optional[datetime] = None


class AlertsResponse(BaseModel):
    items: List[AlertItem]
    total: int
    page: int
    page_size: int
    has_more: bool


# ── Actions ────────────────────────────────────────────────────────────────────

class ActionRequest(BaseModel):
    account_id: str
    action_type: str = Field(..., pattern="^(soft_freeze|hard_freeze|unfreeze|fund_trace)$")
    analyst_id: Optional[str] = "analyst@muleshield"

    model_config = {"json_schema_extra": {
        "example": {
            "account_id": "ACC-001234",
            "action_type": "soft_freeze",
            "analyst_id": "investigator1",
        }
    }}


class ActionResponse(BaseModel):
    account_id: str
    action: str
    status: str
    reason: Optional[str] = None
    applied_at: Optional[str] = None


# ── Health ─────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    models_loaded: bool
    model_count: int
    version: str


# ── Regulator ─────────────────────────────────────────────────────────────────

class RegulatorSummary(BaseModel):
    total_accounts_scored: int
    by_risk_band: Dict[str, int]
    total_freeze_actions: int
    total_strs_generated: int
    last_model_auc_roc: Optional[float] = None
    generated_at: str


# ── Audit ─────────────────────────────────────────────────────────────────────

class AuditLogItem(BaseModel):
    id: int
    event_type: str
    account_id: Optional[str]
    user_id: Optional[str]
    timestamp: datetime
    risk_score: Optional[int]
    record_hash: Optional[str]


class AuditLogResponse(BaseModel):
    items: List[AuditLogItem]
    total: int
    page: int
    page_size: int
