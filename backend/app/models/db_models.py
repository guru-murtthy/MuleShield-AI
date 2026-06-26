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
    patterns = Column(JSON, nullable=True)  # top-3 Detection_Patterns
    shap_values = Column(JSON, nullable=True)  # top-10 SHAP attributions
    narrative = Column(Text, nullable=True)
    auto_freeze_eligible = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    model_version = Column(String(64), nullable=True)


class AccountAction(Base):
    __tablename__ = "account_actions"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(String(64), index=True, nullable=False)
    action_type = Column(String(32), nullable=False)  # soft_freeze, hard_freeze, unfreeze, fund_trace
    user_id = Column(String(64), nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    status = Column(String(16), nullable=False)  # applied, reversed


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    account_id = Column(String(64), nullable=True, index=True)
    user_id = Column(String(64), nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    model_version = Column(String(64), nullable=True)
    risk_score = Column(Integer, nullable=True)
    metadata = Column(JSON, nullable=True)
    previous_hash = Column(String(64), nullable=True)  # SHA-256 of previous record
    current_hash = Column(String(64), nullable=True)  # SHA-256(previous_hash || event_type || timestamp || account_id)

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
            "previous_hash": self.previous_hash,
        }, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()
