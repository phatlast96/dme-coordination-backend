import logging
import os
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler

from fastapi import FastAPI

from app.api.cases import router as cases_router
from app.config import LOG_DIR, LOG_FILE
from app.db import init_db
from app.scheduler.scheduler import start_scheduler, stop_scheduler


def _configure_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_format = "%(asctime)s %(levelname)s %(name)s %(message)s"
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    formatter = logging.Formatter(log_format)

    # Avoid duplicate file handlers on uvicorn --reload
    if not any(isinstance(h, RotatingFileHandler) for h in root.handlers):
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=2_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
        root.addHandler(file_handler)

    if not any(isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler) for h in root.handlers):
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        stream_handler.setLevel(logging.INFO)
        root.addHandler(stream_handler)


_configure_logging()


def _scheduler_enabled() -> bool:
    return os.getenv("DME_ENABLE_SCHEDULER", "1") not in {"0", "false", "False"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    enable_scheduler = _scheduler_enabled()
    if enable_scheduler:
        start_scheduler()
    try:
        yield
    finally:
        if enable_scheduler:
            stop_scheduler()


app = FastAPI(title="DME Coordination", lifespan=lifespan)
app.include_router(cases_router)


@app.get("/health")
def health():
    return {"status": "ok"}
