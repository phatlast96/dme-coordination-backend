from __future__ import annotations

import logging
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from app.config import PROMPTS_DIR
from app.models import Case, ScheduledFollowUp

logger = logging.getLogger("dme.voice")

SUCCESS_OUTCOMES = {
    "written_order_received",
    "accepted_delivery",
    "delivery_confirmed",
    "patient_updated",
    "paid",
}

PROMPT_BY_PURPOSE = {
    "chase_order": "pcp_order_call.txt",
    "correct_billing": "pcp_order_call.txt",
    "outreach": "supplier_outreach_call.txt",
    "confirm_delivery": "supplier_delivery_confirm.txt",
    "claim_status": "medicare_claim_call.txt",
    "patient_status": "patient_update_call.txt",
}


@dataclass
class VoiceCallResult:
    success: bool
    outcome: str
    details: dict[str, Any] = field(default_factory=dict)


# Compact 10-step demo: each PDF failure once.
DEFAULT_DEMO_QUEUE: list[dict[str, Any]] = [
    {"outcome": "request_fell_in_hole", "details": {}},
    {
        "outcome": "written_order_received",
        "details": {
            "order_equipment": "Standard manual wheelchair",
            "order_billing_code": "K0002",
        },
    },
    {
        "outcome": "written_order_received",
        "details": {
            "order_equipment": "Standard manual wheelchair",
            "order_billing_code": "K0001",
        },
    },
    {"outcome": "patient_unreachable", "details": {}},
    {"outcome": "cannot_serve", "details": {"reason": "not taking new Medicare patients"}},
    {"outcome": "accepted_delivery", "details": {"eta": "3-5 business days"}},
    {"outcome": "delivery_silent", "details": {}},
    {"outcome": "accepted_delivery", "details": {"eta": "2-4 business days"}},
    {"outcome": "delivery_confirmed", "details": {"eta": "2-4 business days"}},
    {"outcome": "paid", "details": {}},
]

_queue: list[dict[str, Any]] = []


def reset_demo_queue(queue: list[dict[str, Any]] | None = None) -> None:
    global _queue
    _queue = deepcopy(queue if queue is not None else DEFAULT_DEMO_QUEUE)


def peek_demo_queue() -> list[dict[str, Any]]:
    return list(_queue)


def _load_prompt(prompt_name: str, context: dict[str, Any]) -> str:
    path = PROMPTS_DIR / prompt_name
    template = path.read_text() if path.exists() else prompt_name
    try:
        return template.format(**context)
    except KeyError:
        return template


def _phone_for(case: Case, followup: ScheduledFollowUp) -> str:
    if followup.party == "pcp":
        return case.pcp_phone
    if followup.party == "patient":
        return "patient-callback"
    if followup.party == "medicare":
        return "medicare-claims"
    return followup.supplier_name or "supplier"


def place_call(case: Case, followup: ScheduledFollowUp) -> VoiceCallResult:
    if not _queue:
        reset_demo_queue()

    prompt_name = PROMPT_BY_PURPOSE.get(followup.purpose, "unknown.txt")
    to_phone = _phone_for(case, followup)
    context = {
        "patient_name": case.patient_name,
        "age": case.age,
        "equipment": case.equipment,
        "billing_code": case.billing_code or "K0001",
        "pcp_name": case.pcp_name,
        "pcp_clinic": case.pcp_clinic,
        "pcp_phone": case.pcp_phone,
        "supplier_name": followup.supplier_name or case.selected_supplier_name or "",
        "supplier_phone": to_phone,
        "supplier_address": "",
        "status": case.status,
        "patient_owes_share": case.patient_owes_share,
    }
    prompt_text = _load_prompt(prompt_name, context)

    logger.info(
        "CALL_START case_id=%s party=%s purpose=%s to=%s prompt=%s attempt=%s",
        case.id,
        followup.party,
        followup.purpose,
        to_phone,
        prompt_name,
        followup.attempt,
    )
    logger.info("TWILIO_MOCK action=dial to=%s status=initiated", to_phone)
    logger.info("OPENAI_VOICE prompt=%s status=running chars=%s", prompt_name, len(prompt_text))

    step = _queue.pop(0)
    outcome = step["outcome"]
    details = dict(step.get("details") or {})
    success = outcome in SUCCESS_OUTCOMES
    status = "SUCCESS" if success else "FAILURE"

    logger.info(
        "OPENAI_VOICE prompt=%s status=finished outcome=%s",
        prompt_name,
        outcome,
    )
    logger.info(
        "CALL_RESULT status=%s case_id=%s party=%s outcome=%s success=%s",
        status,
        case.id,
        followup.party,
        outcome,
        success,
    )

    return VoiceCallResult(success=success, outcome=outcome, details=details)
