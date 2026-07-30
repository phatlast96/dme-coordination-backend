from app.config import INTAKE_PATH, SUPPLIERS_PATH
from app.models import Case, Supplier
from app.services.seed import seed_intake_case, seed_suppliers


def test_seed_suppliers_and_intake(session):
    count = seed_suppliers(session, SUPPLIERS_PATH)
    case = seed_intake_case(session, INTAKE_PATH)
    session.commit()

    assert count == 12
    assert session.query(Supplier).count() == 12
    assert case.patient_name == "Eleanor Martinez"
    assert case.pcp_phone == "(312) 555-0198"
    assert session.query(Case).count() == 1


def test_seed_suppliers_idempotent(session):
    seed_suppliers(session, SUPPLIERS_PATH)
    seed_suppliers(session, SUPPLIERS_PATH)
    session.commit()
    assert session.query(Supplier).count() == 12
