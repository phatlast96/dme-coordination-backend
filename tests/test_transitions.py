from datetime import datetime

from app.models import Case, ScheduledFollowUp, Supplier, SupplierContact
from app.services.coordination import schedule_followup, start_case
from app.services.transitions import Action, apply_call_outcome, resolve_action
from app.services.voice import VoiceCallResult, reset_demo_queue
from app.jobs.process_followups import process_due_followups


def _seed_minimal(session):
    reset_demo_queue()
    case = start_case(session, use_live_coverage_fetch=False)
    return case


def test_hole_retries_same(session):
    case = _seed_minimal(session)
    fu = session.query(ScheduledFollowUp).filter_by(completed=False).one()
    result = VoiceCallResult(success=False, outcome="request_fell_in_hole", details={})
    apply_call_outcome(session, case, fu, result, to_phone="x", prompt_name="pcp")
    session.commit()
    nxt = session.query(ScheduledFollowUp).filter_by(completed=False).one()
    assert nxt.party == "pcp"
    assert nxt.purpose == "chase_order"


def test_wrong_code_blocks_suppliers(session):
    case = _seed_minimal(session)
    fu = session.query(ScheduledFollowUp).filter_by(completed=False).one()
    result = VoiceCallResult(
        success=True,
        outcome="written_order_received",
        details={"order_billing_code": "K0002"},
    )
    action, logged = resolve_action(
        ("pcp", "chase_order", "written_order_received"), case, fu, result
    )
    assert action == Action.RETRY_PCP
    assert logged.outcome == "billing_mismatch"
    assert logged.success is False
    assert logged.details["expected"] == "K0001"
    assert logged.details["actual"] == "K0002"
    apply_call_outcome(session, case, fu, result, to_phone="x", prompt_name="pcp")
    session.commit()
    assert case.status == "awaiting_pcp_order"
    assert session.query(ScheduledFollowUp).filter_by(party="supplier", completed=False).count() == 0
    from app.models import CallLog
    import json

    call = session.query(CallLog).one()
    payload = json.loads(call.outcome_json)
    assert payload["outcome"] == "billing_mismatch"
    assert call.success is False


def test_good_code_opens_suppliers_and_patient(session):
    case = _seed_minimal(session)
    fu = session.query(ScheduledFollowUp).filter_by(completed=False).one()
    result = VoiceCallResult(
        success=True,
        outcome="written_order_received",
        details={"order_billing_code": "K0001"},
    )
    apply_call_outcome(session, case, fu, result, to_phone="x", prompt_name="pcp")
    session.commit()
    assert case.status == "supplier_outreach"
    parties = [
        f.party
        for f in session.query(ScheduledFollowUp)
        .filter_by(completed=False)
        .order_by(ScheduledFollowUp.id)
        .all()
    ]
    assert parties == ["patient", "supplier"]


def test_cannot_serve_next_supplier(session):
    case = _seed_minimal(session)
    # open suppliers manually
    fu = session.query(ScheduledFollowUp).filter_by(completed=False).one()
    apply_call_outcome(
        session,
        case,
        fu,
        VoiceCallResult(
            success=True,
            outcome="written_order_received",
            details={"order_billing_code": "K0001"},
        ),
        to_phone="x",
        prompt_name="pcp",
    )
    session.commit()
    # complete patient first
    patient_fu = (
        session.query(ScheduledFollowUp)
        .filter_by(party="patient", completed=False)
        .one()
    )
    apply_call_outcome(
        session,
        case,
        patient_fu,
        VoiceCallResult(success=False, outcome="patient_unreachable", details={}),
        to_phone="x",
        prompt_name="patient",
    )
    supplier_fu = (
        session.query(ScheduledFollowUp)
        .filter_by(party="supplier", completed=False)
        .one()
    )
    first = supplier_fu.supplier_name
    apply_call_outcome(
        session,
        case,
        supplier_fu,
        VoiceCallResult(success=False, outcome="cannot_serve", details={}),
        to_phone="x",
        prompt_name="supplier",
    )
    session.commit()
    nxt = session.query(ScheduledFollowUp).filter_by(party="supplier", completed=False).one()
    assert nxt.supplier_name != first


def test_delivery_silent_does_not_open_medicare(session):
    case = _seed_minimal(session)
    # Fast-forward via scripted process
    reset_demo_queue(
        [
            {"outcome": "written_order_received", "details": {"order_billing_code": "K0001"}},
            {"outcome": "patient_unreachable", "details": {}},
            {"outcome": "accepted_delivery", "details": {"eta": "soon"}},
            {"outcome": "delivery_silent", "details": {}},
        ]
    )
    # clear initial followup and use only our queue by processing
    session.query(ScheduledFollowUp).delete()
    schedule_followup(session, case.id, "pcp", "chase_order", delay_seconds=0)
    session.commit()

    for _ in range(4):
        process_due_followups(session, case_id=case.id)
    session.refresh(case)
    assert session.query(ScheduledFollowUp).filter_by(party="medicare").count() == 0
    assert case.status in {"supplier_outreach", "stalled"}


def test_full_demo_reaches_completed(session):
    case = _seed_minimal(session)
    for _ in range(20):
        details = process_due_followups(session, case_id=case.id)
        session.refresh(case)
        if case.status == "completed" or not details:
            break
    assert case.status == "completed"
