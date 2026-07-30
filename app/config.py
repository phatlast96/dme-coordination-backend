import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
PROMPTS_DIR = ROOT / "prompts"
DB_PATH = DATA_DIR / "dme.db"
DB_URL = f"sqlite:///{DB_PATH}"
FOLLOWUP_POLL_SECONDS = 2
DEMO_FOLLOWUP_DELAY_SECONDS = 1
MEDICARE_COVERAGE_URL = "https://www.medicare.gov/coverage/wheelchairs-scooters"
INTAKE_PATH = DATA_DIR / "intake" / "eleanor_martinez.json"
SUPPLIERS_PATH = DATA_DIR / "suppliers" / "chicago_dme_suppliers.json"
SCRAPED_DIR = DATA_DIR / "scraped"
LOG_DIR = ROOT / "logs"
LOG_FILE = LOG_DIR / "dme.log"
# Disable background scheduler during pytest (ticks are explicit).
ENABLE_SCHEDULER = os.getenv("DME_ENABLE_SCHEDULER", "1") not in {"0", "false", "False"}
