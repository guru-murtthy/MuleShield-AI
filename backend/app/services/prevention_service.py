"""Prevention Engine — manages account freeze/unfreeze actions and kill switch."""
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.db_models import AccountAction
from app.services.audit_service import write_audit_event

logger = logging.getLogger(__name__)
settings = get_settings()

# In-memory kill switch state (persisted to audit log on activation)
_kill_switch_active = False


def is_kill_switch_active() -> bool:
    return _kill_switch_active or settings.KILL_SWITCH_ACTIVE


def activate_kill_switch(db: Session, user_id: str) -> dict:
    global _kill_switch_active
    _kill_switch_active = True
    write_audit_event(
        db,
        event_type="kill_switch_activated",
        user_id=user_id,
        metadata={"activated_at": datetime.now(timezone.utc).isoformat()},
    )
    logger.warning(f"KILL SWITCH ACTIVATED by user: {user_id}")
    return {"status": "kill_switch_activated", "activated_by": user_id}


def apply_action(
    db: Session,
    account_id: str,
    action_type: str,
    analyst_id: Optional[str] = "system",
    model_version: Optional[str] = None,
) -> dict:
    """
    Apply a freeze/unfreeze/fund_trace action to an account.
    action_type: soft_freeze | hard_freeze | unfreeze | fund_trace
    """
    if is_kill_switch_active() and action_type in ("soft_freeze", "hard_freeze"):
        logger.info(f"Kill switch active — blocking freeze action on {account_id}")
        return {
            "account_id": account_id,
            "action": action_type,
            "status": "blocked",
            "reason": "Kill switch is active. Automated freezes are disabled.",
        }

    # Check for duplicate hard_freeze
    if action_type == "hard_freeze":
        existing = (
            db.query(AccountAction)
            .filter(
                AccountAction.account_id == account_id,
                AccountAction.action_type == "hard_freeze",
                AccountAction.status == "active",
            )
            .first()
        )
        if existing:
            write_audit_event(
                db,
                event_type="freeze_applied",
                account_id=account_id,
                user_id=analyst_id,
                metadata={"action": action_type, "warning": "duplicate_action"},
            )
            return {
                "account_id": account_id,
                "action": action_type,
                "status": "no_change",
                "reason": "Account is already hard-frozen.",
            }

    # Record action
    db_action = AccountAction(
        account_id=account_id,
        action_type=action_type,
        status="removed" if action_type == "unfreeze" else "active",
        user_id=analyst_id,
    )
    db.add(db_action)
    db.commit()

    event_type = "freeze_removed" if action_type == "unfreeze" else "freeze_applied"
    write_audit_event(
        db,
        event_type=event_type,
        account_id=account_id,
        user_id=analyst_id,
        model_version=model_version,
        metadata={"action": action_type},
    )

    logger.info(f"Action {action_type} applied to account {account_id} by {analyst_id}")
    return {
        "account_id": account_id,
        "action": action_type,
        "status": "applied",
        "applied_at": datetime.now(timezone.utc).isoformat(),
    }
