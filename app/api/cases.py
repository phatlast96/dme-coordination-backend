from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_session
from app.jobs.process_followups import process_due_followups
from app.models import CallLog, Case, ScheduledFollowUp
from app.schemas import CallLogOut, CaseOut, DemoStartResponse, FollowUpOut, TickResponse
from app.services.coordination import start_case

router = APIRouter()


@router.post("/demo/start", response_model=DemoStartResponse)
def demo_start(session: Session = Depends(get_session)):
    case = start_case(session, use_live_coverage_fetch=False)
    return DemoStartResponse(
        case=CaseOut.model_validate(case),
        message="Case started: coverage loaded, PCP follow-up scheduled.",
    )


@router.get("/cases/{case_id}", response_model=CaseOut)
def get_case(case_id: int, session: Session = Depends(get_session)):
    case = session.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return CaseOut.model_validate(case)


@router.get("/cases/{case_id}/followups", response_model=list[FollowUpOut])
def list_followups(case_id: int, session: Session = Depends(get_session)):
    if not session.get(Case, case_id):
        raise HTTPException(status_code=404, detail="Case not found")
    rows = (
        session.query(ScheduledFollowUp)
        .filter(ScheduledFollowUp.case_id == case_id)
        .order_by(ScheduledFollowUp.id.asc())
        .all()
    )
    return [FollowUpOut.model_validate(r) for r in rows]


@router.get("/cases/{case_id}/calls", response_model=list[CallLogOut])
def list_calls(case_id: int, session: Session = Depends(get_session)):
    if not session.get(Case, case_id):
        raise HTTPException(status_code=404, detail="Case not found")
    rows = (
        session.query(CallLog)
        .filter(CallLog.case_id == case_id)
        .order_by(CallLog.id.asc())
        .all()
    )
    return [CallLogOut.model_validate(r) for r in rows]


@router.post("/cases/{case_id}/tick", response_model=TickResponse)
def tick_case(case_id: int, session: Session = Depends(get_session)):
    case = session.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    details = process_due_followups(session, case_id=case_id)
    session.refresh(case)
    return TickResponse(
        case=CaseOut.model_validate(case),
        processed=len(details),
        details=details,
    )
