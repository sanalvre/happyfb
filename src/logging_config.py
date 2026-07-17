import logging
import os
import sys
from pathlib import Path

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
LOG_DIR = Path(os.environ.get("LOG_DIR", "state/logs"))


def setup_logging(run_id: str | None = None) -> logging.Logger:
    """Configure logging with console + file output.

    Console gets human-readable messages.
    File gets timestamped, structured lines for debugging.
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    log_file = LOG_DIR / "pipeline.log"

    root = logging.getLogger("pipeline")
    root.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    if root.handlers:
        return root

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("%(message)s"))

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_fmt = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
    file_handler.setFormatter(logging.Formatter(file_fmt, datefmt="%Y-%m-%d %H:%M:%S"))

    root.addHandler(console)
    root.addHandler(file_handler)

    if run_id:
        root.info(f"--- Run {run_id} started ---")

    return root


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"pipeline.{name}")
