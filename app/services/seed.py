from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.models import Case, Supplier


def seed_suppliers(session: Session, path: Path) -> int:
    rows = json.loads(path.read_text())
    created = 0
    for row in rows:
        existing = (
            session.query(Supplier)
            .filter(Supplier.supplier_name == row["supplier_name"])
            .one_or_none()
        )
        if existing:
            existing.phone = row["phone"]
            existing.address = row["address"]
            existing.medicare_enrolled = True
        else:
            session.add(
                Supplier(
                    supplier_name=row["supplier_name"],
                    phone=row["phone"],
                    address=row["address"],
                    medicare_enrolled=True,
                )
            )
            created += 1
    session.flush()
    return created if created else len(rows)


def seed_intake_case(session: Session, path: Path) -> Case:
    data = json.loads(path.read_text())
    case = Case(
        patient_name=data["patient_name"],
        age=data["age"],
        medicare_plan=data["medicare_plan"],
        equipment=data["equipment"],
        pcp_name=data["pcp_name"],
        pcp_clinic=data["pcp_clinic"],
        pcp_phone=data["pcp_phone"],
        status_notes=data.get("status_notes"),
        status="intake_loaded",
        patient_owes_share=0.20,
    )
    session.add(case)
    session.flush()
    return case
