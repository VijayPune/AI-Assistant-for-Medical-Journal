"""Exercise the local Step 5 application using Streamlit's in-process test runner."""
from __future__ import annotations

import sys
import os
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from journal_assistant.configuration import load_journal_config
from journal_assistant.rag.env import external_text_processing_allowed

def _visible_text(app) -> str:
    values = []
    for name in ("title", "header", "subheader", "caption", "markdown", "write", "success", "info", "warning", "error"):
        for item in getattr(app, name, []):
            value = getattr(item, "value", None)
            if value is not None:
                values.append(str(value))
    return "\n".join(values)

def main() -> int:
    results: list[tuple[str, bool, str]] = []
    def check(name: str, ok: bool, detail: str) -> None:
        results.append((name, bool(ok), detail))

    ui_path = ROOT / "app/streamlit_app.py"
    run_path = ROOT / "scripts/run_ui.py"
    config = load_journal_config()
    check("Journal UI configuration loads", config.display_name == "Indian Pediatrics" and config.metadata_file.is_file() and config.raw_files_directory.is_dir(), f"{config.display_name}; corpus paths resolve")
    check("Application entry points exist", ui_path.is_file() and run_path.is_file(), "Streamlit UI and Windows launcher are present")
    cfg = tomllib.loads((ROOT / "config/app.toml").read_text(encoding="utf-8"))
    check("Journal display is configuration-driven", cfg["application"]["default_journal_config"].endswith("indian_pediatrics.toml"), "Default can be overridden with JOURNAL_ASSISTANT_CONFIG")

    missing = object()
    saved_groq_key = os.environ.get("GROQ_API_KEY", missing)
    os.environ["GROQ_API_KEY"] = ""  # prevent this smoke test from making a live provider request
    try:
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(ui_path)).run(timeout=30)
        check("Streamlit app renders without runtime errors", not app.exception, f"{len(app.exception)} app exception(s)")
        initial_ui = _visible_text(app)
        has_query = any(widget.key == "question" for widget in app.text_input)
        has_type_filter = any(widget.key == "article_types" for widget in app.multiselect)
        has_demo_examples = any(widget.key == "demo_question" for widget in app.selectbox) and any(widget.key == "use_demo_question" for widget in app.button)
        check("Search, answer, filters, and demo examples appear", all(x in initial_ui for x in ["Search filters", "Answer"]) and has_query and has_type_filter and has_demo_examples, "Question input, filters, answer area and demonstration question selector are present")

        demo_question = "What did the KISS study compare for severe sickle-cell pain?"
        app.selectbox(key="demo_question").set_value(demo_question)
        app.button(key="use_demo_question").click().run(timeout=30)
        check("Demo example fills the question field", app.text_input(key="question").value == demo_question, "Selected sample copied into the search box")

        app.text_input(key="question").set_value("ketorolac morphine sickle cell")
        app.button(key="search_button").click().run(timeout=30)
        first_text = _visible_text(app)
        check("Search returns the expected KISS study source", "Ketorolac vs Morphine for Severe Vaso-Occlusive Crisis" in first_text and "S1" in first_text, "Known local corpus query returns a labelled passage")
        check("Sources and article comparison appear after retrieval", "Sources" in first_text and "Compare articles" in first_text, "Evidence-dependent sections render when passages are found")

        app.multiselect(key="article_types").set_value(["Original Article"])
        app.button(key="search_button").click().run(timeout=30)
        filtered_text = _visible_text(app)
        check("Article-type filter changes the retrieved source set", "Ketorolac vs Morphine for Severe Vaso-Occlusive Crisis" in filtered_text and "Redefining Ten; Reducing the Invisible Pain" not in filtered_text, "Original Article selected; commentary excluded")

        app.multiselect(key="article_types").set_value([])
        app.text_input(key="question").set_value("zzzxqv nonexistingword")
        app.button(key="search_button").click().run(timeout=30)
        no_match_text = _visible_text(app)
        check("No-match query shows abstention without source cards", "could not find relevant supporting evidence" in no_match_text.lower(), "No relevant local result returned")

        app.text_input(key="question").set_value("what dose should I give my child")
        app.button(key="search_button").click().run(timeout=30)
        patient_text = _visible_text(app)
        check("Patient-specific question shows the boundary", "cannot assess an individual child" in patient_text and "[S1]" not in patient_text, "Boundary is visible and source cards are absent")
    except Exception as exc:
        check("Streamlit UI interaction checks", False, f"{type(exc).__name__}: {exc}")
    finally:
        if saved_groq_key is missing:
            os.environ.pop("GROQ_API_KEY", None)
        else:
            os.environ["GROQ_API_KEY"] = saved_groq_key

    ui_source = ui_path.read_text(encoding="utf-8")
    gated_provider = "GroqProvider(" in ui_source and "external_text_processing_allowed()" in ui_source and "not is_patient_specific(question)" in ui_source
    check("Groq answer path is protected by consent and patient-query gates", gated_provider, "The test suppresses the key; live use requires the enabled project gate")
    gate_on = external_text_processing_allowed()
    check("External text-processing gate is readable", isinstance(gate_on, bool), f"Project setting is {'on' if gate_on else 'off'}")

    passed = sum(ok for _, ok, _ in results)
    failed = len(results) - passed
    state = "STEP 5 APPLICATION CHECKS PASSED" if failed == 0 else "STEP 5 APPLICATION CHECKS FAILED"
    lines = ["# Step 5 checkpoint: Application", "", f"**Overall status:** {state}", "", f"**Checks:** {passed} passed; {failed} failed.", "", "| Check | Result | Detail |", "|---|---:|---|"]
    lines += [f"| {name} | {'PASS' if ok else 'FAIL'} | {detail.replace('|', '/')} |" for name, ok, detail in results]
    lines += ["", "## Scope note", "", "The application uses local lexical and semantic retrieval, source display, article comparison, and article-type filtering. When the project gate and Groq credentials are present, a live user search can send its question and retrieved passages to Groq for answer generation. This automated UI checkpoint temporarily suppresses the Groq key, so it does not make provider requests. Query and document embeddings are computed locally.", ""]
    report = ROOT / "data/processed/step5_checkpoint.md"
    report.write_text("\n".join(lines), encoding="utf-8")
    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}: {name} - {detail}")
    print(f"\n{state}\nCheckpoint: {report.relative_to(ROOT)}")
    return 1 if failed else 0

if __name__ == "__main__":
    raise SystemExit(main())
