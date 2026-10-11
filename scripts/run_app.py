"""Run a startup smoke check from a source checkout without installation."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from journal_assistant.startup import startup_message  # noqa: E402


def main() -> int:
    print(startup_message())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
