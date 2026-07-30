import json

from fastapi.testclient import TestClient

from app.db import Base, engine, init_db
from app.main import app
from app.services.voice import reset_demo_queue


def setup_module():
    Base.metadata.drop_all(bind=engine)
    init_db()


def test_demo_e2e_ten_outcomes():
    reset_demo_queue()
    Base.metadata.drop_all(bind=engine)
    init_db()
    client = TestClient(app)

    start = client.post("/demo/start")
    assert start.status_code == 200
    case_id = start.json()["case"]["id"]

    outcomes = []
    for _ in range(25):
        tick = client.post(f"/cases/{case_id}/tick")
        assert tick.status_code == 200
        body = tick.json()
        for d in body["details"]:
            outcomes.append(d["outcome"])
        if body["case"]["status"] == "completed":
            break

    expected = [
        "request_fell_in_hole",
        "written_order_received",  # K0002
        "written_order_received",  # K0001
        "patient_unreachable",
        "cannot_serve",
        "accepted_delivery",
        "delivery_silent",
        "accepted_delivery",
        "delivery_confirmed",
        "paid",
    ]
    assert outcomes == expected

    calls = client.get(f"/cases/{case_id}/calls").json()
    assert len(calls) == 10
    # Second written_order should be success path; first wrong code still logged
    codes = []
    for call in calls:
        payload = json.loads(call["outcome_json"])
        if payload["outcome"] == "written_order_received":
            codes.append(payload["details"].get("order_billing_code"))
    assert codes == ["K0002", "K0001"]

    case = client.get(f"/cases/{case_id}").json()
    assert case["status"] == "completed"
    assert case["billing_code"] == "K0001"
    assert case["selected_supplier_name"] is not None
