from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = DATA_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(
    dotenv_path=os.getenv("RAG_ENV_FILE", r"D:\secrets\.env"),
    override=True,
)


def configure_logging(log_file: str | None = None) -> logging.Logger:
    '''Configure logging for the application.'''
    logger = logging.getLogger("rag_project")
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    file_handler = RotatingFileHandler(
        LOGS_DIR / (log_file or os.getenv("LOG_FILE", "rag_project.log")),
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    logger.propagate = False
    return logger


logger = configure_logging()


def get_env(name: str, default: str | None = None) -> str | None:
    '''Get an environment variable value, returning a default if not found.'''
    return os.getenv(name, default)
