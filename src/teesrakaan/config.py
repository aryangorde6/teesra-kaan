"""Paths and settings. Settings come from the environment, with .env as a fallback."""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def load_dotenv(path: Path | None = None) -> None:
    """Load KEY=VALUE lines from .env without overriding variables already set."""
    path = path or REPO_ROOT / ".env"
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def env_float(name: str, default: float | None = None) -> float | None:
    raw = env(name)
    return default if not raw else float(raw)


def data_dir() -> Path:
    path = Path(env("TEESRAKAAN_DATA") or REPO_ROOT / "data")
    path.mkdir(parents=True, exist_ok=True)
    return path


def paid_calls_allowed() -> bool:
    return env("TEESRAKAAN_ALLOW_PAID") == "1"


def api_key() -> str:
    load_dotenv()
    key = env("MODEL_API_KEY")
    if not key:
        raise RuntimeError("Set MODEL_API_KEY in .env to use the Meta Model API.")
    return key
