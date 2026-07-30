# DME Coordination Backend

FastAPI demo that automates Durable Medical Equipment (DME) coordination for Eleanor Martinez:

**intake → coverage research → PCP order chase → supplier outreach → Medicare payment**

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

## Run the API

```bash
uvicorn app.main:app --reload
```

Background APScheduler polls due follow-ups every 2s. For a deterministic demo, use `/tick`.

## Demo

```bash
# Start Eleanor's case (seeds JSON → SQLite, scrapes coverage fixture, schedules PCP call)
curl -s -X POST http://127.0.0.1:8000/demo/start | python3 -m json.tool

# Advance due follow-ups one batch at a time (repeat until status=completed)
curl -s -X POST http://127.0.0.1:8000/cases/1/tick | python3 -m json.tool

curl -s http://127.0.0.1:8000/cases/1 | python3 -m json.tool
curl -s http://127.0.0.1:8000/cases/1/calls | python3 -m json.tool
curl -s http://127.0.0.1:8000/cases/1/followups | python3 -m json.tool
```

Watch the server logs for `CALL_START`, `TWILIO_MOCK`, `OPENAI_VOICE`, `CALL_RESULT status=SUCCESS|FAILURE`, and `TRANSITION ... action=...`.

The same lines are written to `logs/dme.log` (rotated). Tail with:

```bash
tail -f logs/dme.log
```

## Tests

```bash
pytest -v
```

## Pipeline wiring

1. `POST /demo/start` seeds intake + suppliers JSON into SQLAlchemy, runs coverage extract (`K0001`), inserts first PCP follow-up (`completed=false`).
2. Scheduler or `/tick` loads due `scheduled_followups`.
3. Mock Twilio + OpenAI voice call (real prompts under `prompts/`; scripted outcomes).
4. `apply_call_outcome` maps `(party, purpose, outcome)` → `Action` and enqueues the next follow-up.
5. Phases: PCP (order + billing match) → suppliers (outreach + delivery confirm) → Medicare claim. Patient ping is non-blocking.

## What's mocked

| System | Behavior |
|--------|----------|
| OpenAI voice | Scripted 10-step demo queue; prompts are loaded and logged |
| OpenAI coverage extract | Deterministic `K0001` / Part B / 20% from HTML |
| Twilio | Dial logged only (`TWILIO_MOCK`) |
| Playwright | Used for live fetch when enabled; demo/start uses HTML fixture |

Runtime source of truth after seed is SQLite (`data/dme.db`), not the JSON files.
