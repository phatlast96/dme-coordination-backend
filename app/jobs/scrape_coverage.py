from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.models import Case
from app.services.coverage import (
    extract_coverage_requirements,
    fetch_coverage_html,
    persist_scraped_html,
    requirements_to_json,
)

logger = logging.getLogger("dme.coverage")


def run_coverage_job(session: Session, case: Case, *, use_live_fetch: bool = False) -> Case:
    """Scrape (or use fixture) and attach coverage requirements to the case."""
    if use_live_fetch:
        html = fetch_coverage_html()
        persist_scraped_html(html)
    else:
        html = (
            "<html><body><h1>Wheelchairs and scooters</h1>"
            "<p>Medicare Part B covers manual wheelchairs. Billing code K0001. "
            "You pay 20% of the Medicare-approved amount.</p></body></html>"
        )
        persist_scraped_html(html, filename="medicare_wheelchairs_fixture.html")

    requirements = extract_coverage_requirements(html)
    case.billing_code = requirements.billing_code
    case.coverage_json = requirements_to_json(requirements)
    case.patient_owes_share = requirements.patient_cost_share
    if case.status == "intake_loaded":
        case.status = "coverage_ready"
    session.add(case)
    session.flush()
    logger.info(
        "COVERAGE_READY case_id=%s billing_code=%s",
        case.id,
        case.billing_code,
    )
    return case
