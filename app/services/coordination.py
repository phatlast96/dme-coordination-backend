from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.config import DEMO_FOLLOWUP_DELAY_SECONDS, INTAKE_PATH, SUPPLIERS_PATH
from app.jobs.scrape_coverage import run_coverage_job
from app.models import Case, ScheduledFollowUp, Supplier, SupplierContact
from app.services.seed import seed_intake_case, seed_suppliers
from app.services.voice import reset_demo_queue

logger = logging.getLogger("dme.coordination")


def schedule_followup(
    session: Session,
    case_id: int,
    party: str,
    purpose: str,
    *,
    supplier_name: str | None = None,
    attempt: int = 1,
    notes: str | None = None,
    delay_seconds: int | None = None,
) -> ScheduledFollowUp:
    delay = DEMO_FOLLOWUP_DELAY_SECONDS if delay_seconds is None else delay_seconds
    followup = ScheduledFollowUp(
        case_id=case_id,
        party=party,
        purpose=purpose,
        supplier_name=supplier_name,
        run_at=datetime.utcnow() + timedelta(seconds=delay),
        completed=False,
        attempt=attempt,
        notes=notes,
    )
    session.add(followup)
    session.flush()
    logger.info(
        "FOLLOWUP_ENQUEUE case_id=%s party=%s purpose=%s supplier=%s "
        "run_at=%s completed=false attempt=%s reason=%s",
        case_id,
        party,
        purpose,
        supplier_name,
        followup.run_at.isoformat(),
        attempt,
        notes or purpose,
    )
    return followup


def next_supplier(session: Session, case: Case) -> Supplier | None:
    used = {
        c.supplier_name
        for c in session.query(SupplierContact)
        .filter(
            SupplierContact.case_id == case.id,
            SupplierContact.status.in_(["rejected", "accepted"]),
        )
        .all()
    }
    # Also skip suppliers with in-flight outreach/confirm (attempted but not terminal)
    in_flight = {
        c.supplier_name
        for c in session.query(SupplierContact)
        .filter(
            SupplierContact.case_id == case.id,
            SupplierContact.status == "attempted",
        )
        .all()
    }
    skip = used | in_flight
    suppliers = session.query(Supplier).order_by(Supplier.id.asc()).all()
    for supplier in suppliers:
        if supplier.supplier_name not in skip:
            return supplier
    return None


def get_or_create_contact(
    session: Session, case: Case, supplier: Supplier
) -> SupplierContact:
    contact = (
        session.query(SupplierContact)
        .filter(
            SupplierContact.case_id == case.id,
            SupplierContact.supplier_name == supplier.supplier_name,
        )
        .one_or_none()
    )
    if contact:
        return contact
    contact = SupplierContact(
        case_id=case.id,
        supplier_name=supplier.supplier_name,
        phone=supplier.phone,
        status="pending",
        attempts=0,
    )
    session.add(contact)
    session.flush()
    return contact


def start_case(session: Session, *, use_live_coverage_fetch: bool = False) -> Case:
    reset_demo_queue()
    seed_suppliers(session, SUPPLIERS_PATH)
    case = seed_intake_case(session, INTAKE_PATH)
    run_coverage_job(session, case, use_live_fetch=use_live_coverage_fetch)
    case.status = "awaiting_pcp_order"
    session.add(case)
    schedule_followup(
        session,
        case.id,
        party="pcp",
        purpose="chase_order",
        delay_seconds=0,
        notes="initial_pcp_chase",
    )
    session.commit()
    logger.info("CASE_STARTED case_id=%s status=%s", case.id, case.status)
    return case
