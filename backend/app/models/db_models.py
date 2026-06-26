"""SQLAlchemy ORM models."""
import hashlib
import json
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, JSON

from app.core.database import Base


class ScoreRecord(Base):
    __tablename__ = "score_records"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(String(64), index=True, nullable=False)
    risk_score = Column(Integer, nullable=False)
    risk_band = Column(String(16), nullable=False)
    ensemble_probability = Column(Float, nullable=False)
    detection_patterns = Column(JSON, nullable=True)
    shap_features = Column(JSON, nullable=True)
    narrative = Column(Text, nullable=True)
    auto_freeze_eligible = Column(Boolean, default=False)
    model_version = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class AccountAction(Base):
    __tablename__ = "account_actions"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(String(64), index=True, nullable=False)
    action_type = Column(String(32), nullable=False)  # soft_freeze, hard_freeze, unfreeze, fund_trace
    status = Column(String(16), nullable=False)  # active, removed
    analyst_id = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    account_id = Column(String(64), nullable=True, index=True)
    user_id = Column(String(64), nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    model_version = Column(String(64), nullable=True)
    risk_score = Column(Integer, nullable=True)
    details = Column(JSON, nullable=True)
    record_hash = Column(String(64), nullable=True)  # SHA-256 chain hash
    prev_hash = Column(String(64), nullable=True)

    def compute_hash(self) -> str:
        """Compute SHA-256 hash of this record for audit chain."""
        payload = json.dumps({
            "id": self.id,
            "event_type": self.event_type,
            "account_id": self.account_id,
            "user_id": self.user_id,
            "timestamp": str(self.timestamp),
            "model_version": self.model_version,
            "risk_score": self.risk_score,
            "prev_hash": self.prev_hash,
        }, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()
