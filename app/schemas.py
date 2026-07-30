from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class CaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_name: str
    age: int
    medicare_plan: str
    equipment: str
    pcp_name: str
    pcp_clinic: str
    pcp_phone: str
    status: str
    billing_code: str | None
    order_billing_code: str | None = None
    coverage_json: str | None
    selected_supplier_name: str | None
    delivery_eta: str | None
    patient_owes_share: float


class FollowUpOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: int
    party: str
    purpose: str
    supplier_name: str | None
    run_at: datetime
    completed: bool
    attempt: int
    notes: str | None


class CallLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: int
    followup_id: int | None
    party: str
    to_phone: str
    prompt_name: str
    outcome_json: str
    success: bool
    transcript_summary: str | None
    created_at: datetime


class DemoStartResponse(BaseModel):
    case: CaseOut
    message: str


class TickResponse(BaseModel):
    case: CaseOut
    processed: int
    details: list[dict[str, Any]]
