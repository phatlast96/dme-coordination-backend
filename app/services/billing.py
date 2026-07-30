from __future__ import annotations

from dataclasses import dataclass


EQUIPMENT_HCPCS = {
    "standard manual wheelchair": "K0001",
}


@dataclass(frozen=True)
class MatchResult:
    ok: bool
    expected: str
    actual: str
    reason: str


def match_order_to_claim(equipment: str, order_code: str) -> MatchResult:
    expected = EQUIPMENT_HCPCS.get(equipment.strip().lower(), "")
    actual = (order_code or "").strip().upper()
    if not expected:
        return MatchResult(
            ok=False,
            expected="",
            actual=actual,
            reason="unknown_equipment",
        )
    if actual != expected:
        return MatchResult(
            ok=False,
            expected=expected,
            actual=actual,
            reason="billing_mismatch",
        )
    return MatchResult(
        ok=True,
        expected=expected,
        actual=actual,
        reason="matched",
    )
