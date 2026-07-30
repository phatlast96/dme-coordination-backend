import logging

from app.models import Case, ScheduledFollowUp
from app.services.voice import DEFAULT_DEMO_QUEUE, peek_demo_queue, place_call, reset_demo_queue


def _case():
    return Case(
        id=1,
        patient_name="Eleanor Martinez",
        age=72,
        medicare_plan="Original Medicare (Part B)",
        equipment="Standard manual wheelchair",
        pcp_name="Dr. Sarah Chen",
        pcp_clinic="Sunrise Family Medicine",
        pcp_phone="(312) 555-0198",
        status="awaiting_pcp_order",
        billing_code="K0001",
        patient_owes_share=0.20,
    )


def test_place_call_logs_and_advances_queue(caplog):
    reset_demo_queue()
    case = _case()
    followup = ScheduledFollowUp(
        id=1,
        case_id=1,
        party="pcp",
        purpose="chase_order",
        run_at=case.created_at if hasattr(case, "created_at") else None,
        attempt=1,
        completed=False,
    )
    # run_at required by model usage in place_call only for fields we set
    from datetime import datetime

    followup.run_at = datetime.utcnow()

    with caplog.at_level(logging.INFO, logger="dme.voice"):
        result = place_call(case, followup)

    assert result.outcome == "request_fell_in_hole"
    assert any("TWILIO_MOCK" in r.message for r in caplog.records)
    assert any("OPENAI_VOICE" in r.message for r in caplog.records)
    assert any("CALL_RESULT" in r.message for r in caplog.records)
    assert len(peek_demo_queue()) == len(DEFAULT_DEMO_QUEUE) - 1


def test_demo_queue_ten_steps():
    reset_demo_queue()
    assert len(DEFAULT_DEMO_QUEUE) == 10
    assert DEFAULT_DEMO_QUEUE[0]["outcome"] == "request_fell_in_hole"
    assert DEFAULT_DEMO_QUEUE[1]["details"]["order_billing_code"] == "K0002"
    assert DEFAULT_DEMO_QUEUE[6]["outcome"] == "delivery_silent"
    assert DEFAULT_DEMO_QUEUE[-1]["outcome"] == "paid"
