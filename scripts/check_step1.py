"""Verify the development foundation and run a local startup check."""

from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from journal_assistant.configuration import load_journal_config  # noqa: E402


def main() -> int:
    passed = 0
    failed = 0
    warnings: list[str] = []

    def report(label: str, ok: bool, detail: str = "") -> None:
        nonlocal passed, failed
        if ok:
            passed += 1
            print(f"[PASS] {label}" + (f" — {detail}" if detail else ""))
        else:
            failed += 1
            print(f"[FAIL] {label}" + (f" — {detail}" if detail else ""))

    report("Python version", sys.version_info >= (3, 11), sys.version.split()[0])

    venv_path = (ROOT / ".venv").resolve()
    active_venv = Path(sys.prefix).resolve() != Path(sys.base_prefix).resolve()
    in_project_venv = active_venv and Path(sys.prefix).resolve().is_relative_to(venv_path)
    report(
        "Project virtual environment",
        in_project_venv,
        "running inside Project/.venv" if in_project_venv else "activate .venv before running this check",
    )

    required_paths = [
        "config",
        "config/journals",
        "data/metadata",
        "data/raw",
        "data/processed",
        "data/indexes",
        "data/cache",
        "evaluation",
        "scripts",
        "src/journal_assistant",
        "tests",
    ]
    missing_paths = [item for item in required_paths if not (ROOT / item).is_dir()]
    report(
        "Reusable project folder structure",
        not missing_paths,
        "all required folders exist" if not missing_paths else "missing: " + ", ".join(missing_paths),
    )

    required_files = [
        ".gitignore",
        ".env.example",
        "README.md",
        "pyproject.toml",
        "requirements.txt",
        "config/app.toml",
        "config/journals/indian_pediatrics.toml",
        "config/journals/journal_template.toml.example",
        "scripts/run_app.py",
        "scripts/check_step1.py",
    ]
    missing_files = [item for item in required_files if not (ROOT / item).is_file()]
    report(
        "Foundation files",
        not missing_files,
        "all required files exist" if not missing_files else "missing: " + ", ".join(missing_files),
    )

    config_ok = False
    config_detail = ""
    try:
        journal = load_journal_config(ROOT / "config/journals/indian_pediatrics.toml")
        config_ok = journal.journal_id == "indian_pediatrics" and journal.issue_id == "766"
        config_detail = f"{journal.display_name}; {journal.corpus_title}"
        if journal.access_review_status.lower() not in {"approved", "confirmed", "authorized"}:
            warnings.append(
                "Full-text access status remains "
                f"'{journal.access_review_status}'. Step 2 records the user's stated basis for the supplied local POC files; "
                "confirm broader publisher/editor reuse terms before expanding or redistributing the corpus."
            )
    except Exception as exc:  # Report configuration issues as a failed readiness item.
        config_detail = str(exc)
    report("Journal configuration loads and validates", config_ok, config_detail)

    project_meta_ok = False
    try:
        with (ROOT / "pyproject.toml").open("rb") as stream:
            project_meta = tomllib.load(stream).get("project", {})
        project_meta_ok = (
            project_meta.get("name") == "medical-journal-assistant"
            and project_meta.get("requires-python") == ">=3.11"
        )
    except Exception:
        project_meta_ok = False
    report("Project metadata is valid TOML", project_meta_ok)

    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
    active_requirements = [line.strip() for line in requirements if line.strip() and not line.lstrip().startswith("#")]
    malformed_requirements = [line for line in active_requirements if "==" not in line]
    report(
        "Project dependencies are explicitly declared",
        not malformed_requirements,
        "all active requirements use explicit versions" if not malformed_requirements else "unpinned entries: " + ", ".join(malformed_requirements),
    )

    git = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )
    git_root_ok = git.returncode == 0 and Path(git.stdout.strip()).resolve() == ROOT.resolve()
    report("Git tracks this Project folder", git_root_ok, "repository initialized here" if git_root_ok else "Git repository not found at Project root")

    startup = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "run_app.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    startup_ok = startup.returncode == 0 and startup.stdout.strip().startswith("READY:")
    startup_detail = startup.stdout.strip() or startup.stderr.strip()
    report("Application startup smoke check", startup_ok, startup_detail)

    for warning in warnings:
        print(f"[WARN] {warning}")

    print(f"\nStep 1 readiness: {passed} passed, {failed} failed, {len(warnings)} warning(s).")
    if failed:
        print("Step 1 is not ready; fix the failed items before continuing.")
        return 1
    print("Step 1 foundation is ready. Review the access warning when expanding or reusing journal content.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
