from app.jobs.process_followups import process_due_followups
from app.models import ScheduledFollowUp
from app.services.coordination import start_case
from app.services.voice import reset_demo_queue


def test_process_due_completes_and_may_enqueue_next(session):
    reset_demo_queue()
    case = start_case(session, use_live_coverage_fetch=False)
    before = session.query(ScheduledFollowUp).filter_by(completed=False).count()
    assert before == 1
    details = process_due_followups(session, case_id=case.id)
    assert len(details) == 1
    assert details[0]["outcome"] == "request_fell_in_hole"
    incomplete = session.query(ScheduledFollowUp).filter_by(completed=False).all()
    assert len(incomplete) == 1
    assert incomplete[0].party == "pcp"
