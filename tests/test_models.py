from datetime import datetime, timedelta

from app.models import Case, ScheduledFollowUp, Supplier


def test_create_supplier_case_and_incomplete_followup(session):
    supplier = Supplier(
        supplier_name="Lakeshore Home Medical Equipment",
        phone="(312) 555-0142",
        address="1820 N Clark St, Chicago, IL 60614",
        medicare_enrolled=True,
    )
    case = Case(
        patient_name="Eleanor Martinez",
        age=72,
        medicare_plan="Original Medicare (Part B)",
        equipment="Standard manual wheelchair",
        pcp_name="Dr. Sarah Chen",
        pcp_clinic="Sunrise Family Medicine, Chicago IL",
        pcp_phone="(312) 555-0198",
        status="awaiting_pcp_order",
    )
    session.add_all([supplier, case])
    session.flush()

    followup = ScheduledFollowUp(
        case_id=case.id,
        party="pcp",
        purpose="chase_order",
        run_at=datetime.utcnow() - timedelta(seconds=1),
        completed=False,
        attempt=1,
    )
    session.add(followup)
    session.commit()

    incomplete = (
        session.query(ScheduledFollowUp)
        .filter(ScheduledFollowUp.completed.is_(False))
        .all()
    )
    assert len(incomplete) == 1
    assert incomplete[0].party == "pcp"
    assert session.query(Supplier).count() == 1
    assert session.query(Case).one().patient_name == "Eleanor Martinez"
