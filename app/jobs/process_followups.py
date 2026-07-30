from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import CallLog, Case, ScheduledFollowUp
from app.services.transitions import apply_call_outcome
from app.services.voice import PROMPT_BY_PURPOSE, place_call

logger = logging.getLogger("dme.jobs")


def process_due_followups(
    session: Session | None = None,
    *,
    case_id: int | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    owns_session = session is None
    session = session or SessionLocal()
    details: list[dict[str, Any]] = []
    try:
        now = datetime.utcnow()
        query = session.query(ScheduledFollowUp).filter(
            ScheduledFollowUp.completed.is_(False),
            ScheduledFollowUp.run_at <= now,
        )
        if case_id is not None:
            query = query.filter(ScheduledFollowUp.case_id == case_id)
        due = query.order_by(ScheduledFollowUp.id.asc()).limit(limit).all()

        for followup in due:
            case = session.get(Case, followup.case_id)
            if case is None:
                followup.completed = True
                continue
            result = place_call(case, followup)
            prompt_name = PROMPT_BY_PURPOSE.get(followup.purpose, "unknown.txt")
            to_phone = case.pcp_phone if followup.party == "pcp" else (
                followup.supplier_name or followup.party
            )
            apply_call_outcome(
                session,
                case,
                followup,
                result,
                to_phone=to_phone,
                prompt_name=prompt_name,
            )
            # Prefer the persisted call-log outcome (e.g. billing_mismatch after voice success).
            last_log = (
                session.query(CallLog)
                .filter(CallLog.followup_id == followup.id)
                .order_by(CallLog.id.desc())
                .first()
            )
            logged_outcome = result.outcome
            if last_log:
                logged_outcome = json.loads(last_log.outcome_json).get("outcome", result.outcome)
            details.append(
                {
                    "followup_id": followup.id,
                    "party": followup.party,
                    "purpose": followup.purpose,
                    "outcome": logged_outcome,
                    "case_status": case.status,
                }
            )
        session.commit()
        return details
    except Exception:
        session.rollback()
        logger.exception("process_due_followups failed")
        raise
    finally:
        if owns_session:
            session.close()
