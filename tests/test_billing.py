from app.services.billing import match_order_to_claim


def test_match_ok():
    result = match_order_to_claim("Standard manual wheelchair", "K0001")
    assert result.ok
    assert result.expected == "K0001"


def test_mismatch():
    result = match_order_to_claim("Standard manual wheelchair", "K0002")
    assert not result.ok
    assert result.reason == "billing_mismatch"
    assert result.expected == "K0001"
    assert result.actual == "K0002"


def test_unknown_equipment():
    result = match_order_to_claim("unknown device", "K0001")
    assert not result.ok
    assert result.reason == "unknown_equipment"
