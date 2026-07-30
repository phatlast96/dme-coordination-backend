from app.models import Case
from app.services.coverage import extract_coverage_requirements
from app.jobs.scrape_coverage import run_coverage_job


FIXTURE_HTML = """
<html><body>
<h1>Wheelchairs and scooters</h1>
<p>Medicare Part B covers standard manual wheelchairs. HCPCS K0001. Patient pays 20%.</p>
</body></html>
"""


def test_extract_coverage_requirements():
    req = extract_coverage_requirements(FIXTURE_HTML)
    assert req.billing_code == "K0001"
    assert req.covered_under == "Medicare Part B"
    assert req.patient_cost_share == 0.20


def test_run_coverage_job(session):
    case = Case(
        patient_name="Eleanor Martinez",
        age=72,
        medicare_plan="Original Medicare (Part B)",
        equipment="Standard manual wheelchair",
        pcp_name="Dr. Sarah Chen",
        pcp_clinic="Sunrise",
        pcp_phone="(312) 555-0198",
        status="intake_loaded",
    )
    session.add(case)
    session.flush()
    run_coverage_job(session, case, use_live_fetch=False)
    session.commit()
    assert case.billing_code == "K0001"
    assert case.status == "coverage_ready"
    assert case.coverage_json is not None
