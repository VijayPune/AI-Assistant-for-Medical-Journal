"""Load local environment values without printing secrets."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

def load_project_env() -> None:
    path = ROOT / ".env"
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if value.startswith(("'", '"')) and value.endswith(("'", '"')) and len(value) >= 2:
            value = value[1:-1]
        if key and key.replace("_", "").isalnum():
            os.environ.setdefault(key, value)

def external_text_processing_allowed() -> bool:
    load_project_env()
    return os.getenv("JOURNAL_ASSISTANT_ALLOW_EXTERNAL_TEXT_PROCESSING", "false").strip().lower() in {"1", "true", "yes"}
