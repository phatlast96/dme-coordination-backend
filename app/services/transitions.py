from __future__ import annotations

import json
import logging
from enum import Enum
from typing import Any

from sqlalchemy.orm import Session

from app.models import Case, ScheduledFollowUp, Supplier, SupplierContact
from app.services.billing import match_order_to_claim
from app.services.coordination import get_or_create_contact, next_supplier, schedule_followup
from app.services.voice import VoiceCallResult

logger = logging.getLogger("dme.transitions")


class Action(str, Enum):
    RETRY_SAME = "retry_same"
    RETRY_PCP = "retry_pcp"
    NEXT_SUPPLIER = "next_supplier"
    CONFIRM_DELIVERY = "confirm_delivery"
    OPEN_SUPPLIERS = "open_suppliers"
    OPEN_MEDICARE = "open_medicare"
    COMPLETE = "complete"
    PATIENT_DONE = "patient_done"
    STALL = "stall"


TRANSITIONS: dict[tuple[str, str, str], Action | str] = {
    ("pcp", "chase_order", "request_fell_in_hole"): Action.RETRY_SAME,
    ("pcp", "chase_order", "no_answer"): Action.RETRY_SAME,
    ("pcp", "chase_order", "order_not_ready"): Action.RETRY_SAME,
    ("pcp", "chase_order", "call_failed"): Action.RETRY_SAME,
    ("pcp", "chase_order", "written_order_received"): "check_billing",
    ("pcp", "correct_billing", "request_fell_in_hole"): Action.RETRY_SAME,
    ("pcp", "correct_billing", "no_answer"): Action.RETRY_SAME,
    ("pcp", "correct_billing", "order_not_ready"): Action.RETRY_SAME,
    ("pcp", "correct_billing", "call_failed"): Action.RETRY_SAME,
    ("pcp", "correct_billing", "written_order_received"): "check_billing",
    ("supplier", "outreach", "cannot_serve"): Action.NEXT_SUPPLIER,
    ("supplier", "outreach", "out_of_stock"): Action.NEXT_SUPPLIER,
    ("supplier", "outreach", "not_taking_medicare"): Action.NEXT_SUPPLIER,
    ("supplier", "outreach", "outside_area"): Action.NEXT_SUPPLIER,
    ("supplier", "outreach", "no_answer"): Action.RETRY_SAME,
    ("supplier", "outreach", "call_failed"): Action.RETRY_SAME,
    ("supplier", "outreach", "accepted_delivery"): Action.CONFIRM_DELIVERY,
    ("supplier", "confirm_delivery", "delivery_silent"): Action.NEXT_SUPPLIER,
    ("supplier", "confirm_delivery", "delivery_confirmed"): Action.OPEN_MEDICARE,
    ("medicare", "claim_status", "claim_pending"): Action.RETRY_SAME,
    ("medicare", "claim_status", "call_failed"): Action.RETRY_SAME,
    ("medicare", "claim_status", "paid"): Action.COMPLETE,
    ("patient", "patient_status", "patient_unreachable"): Action.PATIENT_DONE,
    ("patient", "patient_status", "patient_updated"): Action.PATIENT_DONE,
}


def log_call_result(
    session: Session,
    case: Case,
    followup: ScheduledFollowUp,
    result: VoiceCallResult,
    to_phone: str,
    prompt_name: str,
) -> None:
    from app.models import CallLog

    session.add(
        CallLog(
            case_id=case.id,
            followup_id=followup.id,
            party=followup.party,
            to_phone=to_phone,
            prompt_name=prompt_name,
            outcome_json=json.dumps(
                {"outcome": result.outcome, "details": result.details, "success": result.success}
            ),
            success=result.success,
            transcript_summary=f"{followup.party}:{result.outcome}",
        )
    )


def resolve_action(
    key: tuple[str, str, str],
    case: Case,
    followup: ScheduledFollowUp,
    result: VoiceCallResult,
) -> Action:
    mapped = TRANSITIONS.get(key)
    if mapped == "check_billing":
        order_code = result.details.get("order_billing_code", "")
        match = match_order_to_claim(case.equipment, order_code)
        if not match.ok or not case.billing_code:
            logger.info(
                "CALL_RESULT status=FAILURE party=pcp outcome=billing_mismatch "
                "expected=%s actual=%s",
                match.expected,
                match.actual,
            )
            return Action.RETRY_PCP
        case.order_billing_code = match.actual
        return Action.OPEN_SUPPLIERS

    if mapped is None:
        logger.info("TRANSITION unknown key=%s defaulting=retry_same", key)
        return Action.RETRY_SAME

    action = mapped if isinstance(mapped, Action) else Action(mapped)

    # Supplier no_answer: retry once, then next supplier
    if (
        action == Action.RETRY_SAME
        and followup.party == "supplier"
        and followup.purpose == "outreach"
        and result.outcome in {"no_answer", "call_failed"}
        and followup.attempt >= 1
    ):
        # Demo script doesn't use no_answer; still honor 1 retry then next.
        if followup.attempt >= 2:
            return Action.NEXT_SUPPLIER
    return action


def apply_action(
    session: Session,
    case: Case,
    followup: ScheduledFollowUp,
    action: Action,
    result: VoiceCallResult,
) -> None:
    if action == Action.RETRY_SAME:
        schedule_followup(
            session,
            case.id,
            party=followup.party,
            purpose=followup.purpose,
            supplier_name=followup.supplier_name,
            attempt=followup.attempt + 1,
            notes=f"retry_after_{result.outcome}",
            delay_seconds=0,
        )
        return

    if action == Action.RETRY_PCP:
        case.status = "awaiting_pcp_order"
        schedule_followup(
            session,
            case.id,
            party="pcp",
            purpose="correct_billing",
            attempt=1,
            notes="billing_mismatch",
            delay_seconds=0,
        )
        return

    if action == Action.OPEN_SUPPLIERS:
        case.status = "supplier_outreach"
        supplier = next_supplier(session, case)
        if not supplier:
            case.status = "stalled"
            return
        contact = get_or_create_contact(session, case, supplier)
        contact.status = "attempted"
        contact.attempts += 1
        # Enqueue patient before supplier so the demo outcome queue stays aligned.
        schedule_followup(
            session,
            case.id,
            party="patient",
            purpose="patient_status",
            delay_seconds=0,
            notes="post_order_patient_ping",
        )
        schedule_followup(
            session,
            case.id,
            party="supplier",
            purpose="outreach",
            supplier_name=supplier.supplier_name,
            delay_seconds=0,
            notes="order_gate_passed",
        )
        return

    if action == Action.NEXT_SUPPLIER:
        if followup.supplier_name:
            contact = (
                session.query(SupplierContact)
                .filter(
                    SupplierContact.case_id == case.id,
                    SupplierContact.supplier_name == followup.supplier_name,
                )
                .one_or_none()
            )
            if contact:
                contact.status = "rejected"
                contact.last_outcome = result.outcome
        supplier = next_supplier(session, case)
        if not supplier:
            case.status = "stalled"
            return
        contact = get_or_create_contact(session, case, supplier)
        contact.status = "attempted"
        contact.attempts += 1
        case.status = "supplier_outreach"
        schedule_followup(
            session,
            case.id,
            party="supplier",
            purpose="outreach",
            supplier_name=supplier.supplier_name,
            delay_seconds=0,
            notes=f"after_{result.outcome}",
        )
        return

    if action == Action.CONFIRM_DELIVERY:
        enrolled = (
            session.query(Supplier)
            .filter(
                Supplier.supplier_name == followup.supplier_name,
                Supplier.medicare_enrolled.is_(True),
            )
            .one_or_none()
        )
        if not enrolled or not case.order_billing_code:
            logger.info(
                "TRANSITION skip confirm reason=not_enrolled_or_missing_code supplier=%s",
                followup.supplier_name,
            )
            apply_action(session, case, followup, Action.NEXT_SUPPLIER, result)
            return
        contact = (
            session.query(SupplierContact)
            .filter(
                SupplierContact.case_id == case.id,
                SupplierContact.supplier_name == followup.supplier_name,
            )
            .one_or_none()
        )
        if contact:
            contact.status = "attempted"
            contact.last_outcome = result.outcome
        case.selected_supplier_name = followup.supplier_name
        case.delivery_eta = result.details.get("eta")
        schedule_followup(
            session,
            case.id,
            party="supplier",
            purpose="confirm_delivery",
            supplier_name=followup.supplier_name,
            delay_seconds=0,
            notes="confirm_after_accept",
        )
        return

    if action == Action.OPEN_MEDICARE:
        contact = (
            session.query(SupplierContact)
            .filter(
                SupplierContact.case_id == case.id,
                SupplierContact.supplier_name == followup.supplier_name,
            )
            .one_or_none()
        )
        if contact:
            contact.status = "accepted"
            contact.last_outcome = result.outcome
        case.selected_supplier_name = followup.supplier_name
        case.delivery_eta = result.details.get("eta") or case.delivery_eta
        case.status = "medicare_followup"
        schedule_followup(
            session,
            case.id,
            party="medicare",
            purpose="claim_status",
            supplier_name=followup.supplier_name,
            delay_seconds=0,
            notes="delivery_confirmed",
        )
        return

    if action == Action.COMPLETE:
        case.status = "completed"
        return

    if action == Action.PATIENT_DONE:
        return

    if action == Action.STALL:
        case.status = "stalled"


def apply_call_outcome(
    session: Session,
    case: Case,
    followup: ScheduledFollowUp,
    result: VoiceCallResult,
    *,
    to_phone: str = "",
    prompt_name: str = "",
) -> Case:
    followup.completed = True
    if to_phone or prompt_name:
        log_call_result(session, case, followup, result, to_phone or "unknown", prompt_name or "unknown")

    key = (followup.party, followup.purpose, result.outcome)
    action = resolve_action(key, case, followup, result)
    apply_action(session, case, followup, action, result)
    logger.info(
        "TRANSITION party=%s purpose=%s outcome=%s action=%s case_status=%s",
        followup.party,
        followup.purpose,
        result.outcome,
        action.value,
        case.status,
    )
    session.add(case)
    session.add(followup)
    session.flush()
    return case
