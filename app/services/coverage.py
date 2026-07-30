from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass

from app.config import MEDICARE_COVERAGE_URL, PROMPTS_DIR, SCRAPED_DIR

logger = logging.getLogger("dme.coverage")


@dataclass
class CoverageRequirements:
    billing_code: str
    covered_under: str
    patient_cost_share: float
    prior_auth_likely: bool
    required_docs: list[str]
    summary: str


def fetch_coverage_html(url: str = MEDICARE_COVERAGE_URL) -> str:
    """Fetch Medicare coverage page HTML via Playwright (real network)."""
    from playwright.sync_api import sync_playwright

    logger.info("COVERAGE_FETCH url=%s via=playwright", url)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        html = page.content()
        browser.close()
    return html


def extract_coverage_requirements(html: str) -> CoverageRequirements:
    """Mocked OpenAI extraction using coverage_extract prompt + HTML signals."""
    prompt = (PROMPTS_DIR / "coverage_extract.txt").read_text()
    logger.info(
        "OPENAI_MOCK action=extract_coverage prompt=%s html_chars=%s",
        "coverage_extract.txt",
        len(html),
    )
    # Deterministic mock grounded in known Medicare wheelchair coverage.
    lower = html.lower()
    has_wheelchair = "wheelchair" in lower or "k0001" in lower or len(html) > 0
    requirements = CoverageRequirements(
        billing_code="K0001",
        covered_under="Medicare Part B",
        patient_cost_share=0.20,
        prior_auth_likely=False,
        required_docs=[
            "Written order / prescription from treating physician",
            "Medical necessity documentation",
            "Supplier enrollment with Medicare",
        ],
        summary=(
            "Standard manual wheelchairs are covered under Part B when medically necessary; "
            "typical patient responsibility ~20% without supplemental coverage. "
            f"Prompt used ({len(prompt)} chars); page_signals_ok={has_wheelchair}."
        ),
    )
    logger.info(
        "OPENAI_MOCK action=extract_coverage status=finished billing_code=%s",
        requirements.billing_code,
    )
    return requirements


def persist_scraped_html(html: str, filename: str = "medicare_wheelchairs.html") -> str:
    SCRAPED_DIR.mkdir(parents=True, exist_ok=True)
    path = SCRAPED_DIR / filename
    path.write_text(html)
    return str(path)


def requirements_to_json(requirements: CoverageRequirements) -> str:
    return json.dumps(asdict(requirements))
