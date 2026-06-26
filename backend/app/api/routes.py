"""
MuleShield AI API routes.
All endpoints under /api/v1/
"""
import json
import logging
from datetime import datetime, timezone
from typing import Optional

import numpy as np
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.schemas import (
    ActionRequest, ActionResponse, AlertItem, AlertsResponse,
    AuditLogItem, AuditLogResponse, HealthResponse, RegulatorSummary,
    ScoreRequest, ScoreResponse, SHAPFeatureResponse, DetectionPatternResponse,
)
from app.core.config import get_settings
from app.core.database import get_db
from app.ml import scorer as sc
from app.models.db_models import AccountAction, AuditLog, ScoreRecord
from app.services import audit_service, model_service, prevention_service

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter()

# ── Redis-backed cache (falls back to in-process dict) ─────────────────────────
_score_cache: dict = {}
_redis_client = None

try:
    import redis as _redis
    _redis_client = _redis.from_url(settings.REDIS_URL, socket_connect_timeout=1, socket_timeout=1)
    _redis_client.ping()
    logger.info("Redis cache connected.")
except Exception:
    _redis_client = None
    logger.info("Redis unavailable — using in-process cache.")


def _cache_key(account_id: str) -> str:
    return f"ms:score:{account_id}"


def _get_cached(account_id: str) -> Optional[ScoreResponse]:
    if _redis_client:
        try:
            data = _redis_client.get(_cache_key(account_id))
            if data:
                import pickle
                return pickle.loads(data)
        except Exception:
            pass
    if account_id in _score_cache:
        resp, ts = _score_cache[account_id]
        age = (datetime.now(timezone.utc) - ts).total_seconds()
        if age <= settings.SCORE_CACHE_TTL:
            return resp
    return None


def _set_cache(account_id: str, resp: ScoreResponse):
    if _redis_client:
        try:
            import pickle
            _redis_client.setex(_cache_key(account_id), settings.SCORE_CACHE_TTL, pickle.dumps(resp))
            return
        except Exception:
            pass
    _score_cache[account_id] = (resp, datetime.now(timezone.utc))


# ── Health ─────────────────────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse, tags=["System"])
def health_check():
    """Returns service health and model status."""
    ensemble = model_service.get_ensemble()
    loaded = ensemble is not None and ensemble.is_fitted
    count = len(ensemble.models) if loaded else 0
    return HealthResponse(
        status="ok",
        models_loaded=loaded,
        model_count=count,
        version=settings.APP_VERSION,
    )


# ── Score ──────────────────────────────────────────────────────────────────────

@router.post("/score", response_model=ScoreResponse, tags=["Scoring"])
def score_account(request: ScoreRequest, db: Session = Depends(get_db)):
    """
    Submit an account feature vector for fraud risk scoring.
    Returns Risk_Score (0–1000), Risk_Band, detection patterns, SHAP features, and narrative.
    """
    account_id = request.account_id

    # Cache check (60-second TTL)
    cached = _get_cached(account_id)
    if cached:
        cached.cached = True
        return cached

    ensemble = model_service.get_ensemble()
    if ensemble is None or not ensemble.is_fitted:
        raise HTTPException(
            status_code=503,
            detail="Model not loaded. Run the training pipeline first."
        )

    # Preprocess features
    x = model_service.preprocess_features(request.features)

    # Ensemble prediction
    prob, component_probs = ensemble.predict_proba_single(x)
    risk_score = sc.probability_to_score(prob)
    risk_band = sc.score_to_band(risk_score)

    # SHAP (uses cached TreeExplainer)
    feature_names = ensemble.feature_names or [f"F{i}" for i in range(len(x))]
    shap_explainer = model_service.get_shap_explainer()
    shap_features_raw, shap_ok = sc.compute_shap_values(ensemble, x, feature_names, explainer=shap_explainer)

    # Detection patterns
    top_patterns = sc.classify_detection_patterns(risk_score, shap_features_raw, component_probs)

    # Narrative
    narrative = sc.generate_narrative(account_id, risk_score, risk_band, top_patterns, shap_features_raw)

    # STR draft for HIGH/CRITICAL
    str_draft = None
    if risk_band in ("HIGH", "CRITICAL"):
        str_draft = sc.generate_str_draft(
            account_id, risk_score, risk_band,
            top_patterns, shap_features_raw, ensemble.model_version
        )

    auto_freeze = risk_band == "CRITICAL"

    response = ScoreResponse(
        account_id=account_id,
        risk_score=risk_score,
        risk_band=risk_band,
        ensemble_probability=round(prob, 4),
        component_probs=component_probs,
        top_patterns=[DetectionPatternResponse(pattern=p.pattern, confidence=p.confidence) for p in top_patterns],
        shap_features=[SHAPFeatureResponse(name=f.name, shap_value=f.shap_value, direction=f.direction) for f in shap_features_raw],
        narrative=narrative,
        auto_freeze_eligible=auto_freeze,
        shap_available=shap_ok,
        str_draft=str_draft,
        model_version=ensemble.model_version,
        cached=False,
    )

    # Persist score record
    db_record = ScoreRecord(
        account_id=account_id,
        risk_score=risk_score,
        risk_band=risk_band,
        ensemble_probability=prob,
        detection_patterns=[{"pattern": p.pattern, "confidence": p.confidence} for p in top_patterns],
        shap_features=[{"name": f.name, "shap_value": f.shap_value, "direction": f.direction} for f in shap_features_raw],
        narrative=narrative,
        auto_freeze_eligible=auto_freeze,
        model_version=ensemble.model_version,
    )
    db.add(db_record)
    db.commit()

    # Audit
    audit_service.write_audit_event(
        db,
        event_type="score_computed",
        account_id=account_id,
        risk_score=risk_score,
        model_version=ensemble.model_version,
        details={"risk_band": risk_band, "auto_freeze_eligible": auto_freeze},
    )

    # Auto-freeze for CRITICAL (if kill switch is off)
    if auto_freeze and not prevention_service.is_kill_switch_active():
        prevention_service.apply_action(db, account_id, "hard_freeze", analyst_id="system", model_version=ensemble.model_version)
        audit_service.write_audit_event(
            db, event_type="str_generated",
            account_id=account_id, risk_score=risk_score,
            details={"str_type": "goAML"},
        )

    _set_cache(account_id, response)
    return response


# ── Alerts ─────────────────────────────────────────────────────────────────────

@router.get("/alerts", response_model=AlertsResponse, tags=["Alerts"])
def get_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    risk_band: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Return paginated fraud alerts (Risk_Band ≥ MEDIUM), sorted by score descending."""
    query = db.query(ScoreRecord).filter(
        ScoreRecord.risk_band.in_(["MEDIUM", "HIGH", "CRITICAL"])
    )
    if risk_band:
        query = query.filter(ScoreRecord.risk_band == risk_band.upper())
    query = query.order_by(ScoreRecord.risk_score.desc())

    total = query.count()
    records = query.offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for r in records:
        top_pattern = None
        if r.detection_patterns:
            try:
                patterns = r.detection_patterns
                top_pattern = patterns[0]["pattern"] if patterns else None
            except Exception:
                pass
        items.append(AlertItem(
            account_id=r.account_id,
            risk_score=r.risk_score,
            risk_band=r.risk_band,
            top_pattern=top_pattern,
            auto_freeze_eligible=r.auto_freeze_eligible or False,
            scored_at=r.created_at,
        ))

    return AlertsResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total,
    )


# ── Actions ────────────────────────────────────────────────────────────────────

@router.post("/action", response_model=ActionResponse, tags=["Prevention"])
def apply_action(request: ActionRequest, db: Session = Depends(get_db)):
    """Apply a freeze/unfreeze/fund_trace action to an account."""
    result = prevention_service.apply_action(
        db,
        account_id=request.account_id,
        action_type=request.action_type,
        analyst_id=request.analyst_id,
    )
    return ActionResponse(**result)


@router.post("/kill-switch", tags=["Prevention"])
def activate_kill_switch(user_id: str = Query(...), db: Session = Depends(get_db)):
    """Activate the system-wide kill switch to stop all automated freeze actions."""
    return prevention_service.activate_kill_switch(db, user_id)


# ── Regulator ─────────────────────────────────────────────────────────────────

@router.get("/regulator/summary", response_model=RegulatorSummary, tags=["Regulator"])
def regulator_summary(
    x_regulator_token: Optional[str] = Header(None, alias="X-Regulator-Token"),
    db: Session = Depends(get_db),
):
    """Read-only regulatory metrics endpoint. Requires X-Regulator-Token header."""
    if x_regulator_token != settings.REGULATOR_TOKEN:
        raise HTTPException(status_code=401, detail={"error": "unauthorized"})

    all_bands = ["MINIMAL", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
    band_counts = dict(
        db.query(ScoreRecord.risk_band, func.count(ScoreRecord.id))
        .group_by(ScoreRecord.risk_band)
        .all()
    )
    by_band = {band: band_counts.get(band, 0) for band in all_bands}
    total_scored = sum(by_band.values())

    total_freezes = db.query(AccountAction).filter(
        AccountAction.action_type.in_(["soft_freeze", "hard_freeze"]),
        AccountAction.status == "active",
    ).count()

    total_strs = db.query(AuditLog).filter(AuditLog.event_type == "str_generated").count()

    return RegulatorSummary(
        total_accounts_scored=total_scored,
        by_risk_band=by_band,
        total_freeze_actions=total_freezes,
        total_strs_generated=total_strs,
        last_model_auc_roc=None,  # populated post-training
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


# ── Audit Log ─────────────────────────────────────────────────────────────────

@router.get("/audit", response_model=AuditLogResponse, tags=["Audit"])
def get_audit_log(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    event_type: Optional[str] = Query(None),
    account_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Paginated audit log with optional filters."""
    query = db.query(AuditLog)
    if event_type:
        query = query.filter(AuditLog.event_type == event_type)
    if account_id:
        query = query.filter(AuditLog.account_id == account_id)
    query = query.order_by(AuditLog.timestamp.desc())

    total = query.count()
    records = query.offset((page - 1) * page_size).limit(page_size).all()

    items = [
        AuditLogItem(
            id=r.id,
            event_type=r.event_type,
            account_id=r.account_id,
            user_id=r.user_id,
            timestamp=r.timestamp,
            risk_score=r.risk_score,
            record_hash=r.record_hash,
        )
        for r in records
    ]
    return AuditLogResponse(items=items, total=total, page=page, page_size=page_size)
