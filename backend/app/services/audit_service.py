"""Audit logging service — append-only, SHA-256 chained records."""
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.db_models import AuditLog

logger = logging.getLogger(__name__)

_in_memory_prev_hash: str = "genesis"
_initialized: bool = False


def _ensure_init(db: Session):
    global _in_memory_prev_hash, _initialized
    if not _initialized:
        prev = db.query(AuditLog).order_by(AuditLog.id.desc()).first()
        if prev:
            _in_memory_prev_hash = prev.current_hash or "genesis"
        _initialized = True


def write_audit_event(
    db: Session,
    event_type: str,
    account_id: Optional[str] = None,
    user_id: Optional[str] = None,
    model_version: Optional[str] = None,
    risk_score: Optional[int] = None,
    metadata: Optional[dict] = None,
) -> AuditLog:
    """
    Append an audit record with SHA-256 hash chaining.
    Events: score_computed, freeze_applied, freeze_removed, str_generated,
            kill_switch_activated, model_retrained, user_login
    """
    global _in_memory_prev_hash
    _ensure_init(db)

    record = AuditLog(
        event_type=event_type,
        account_id=account_id,
        user_id=user_id,
        timestamp=datetime.now(timezone.utc),
        model_version=model_version,
        risk_score=risk_score,
        metadata=metadata or {},
        previous_hash=_in_memory_prev_hash,
    )
    db.add(record)
    db.flush()
    record.current_hash = record.compute_hash()
    _in_memory_prev_hash = record.current_hash
    db.commit()
    logger.debug(f"Audit event written: {event_type} | account={account_id}")
    return record
