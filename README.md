# Medical Journal AI Assistant — Development Foundation

This folder is the application workspace. The first proof of concept is configured for the January 2025 issue of *Indian Pediatrics*. Shared application code is kept separate from journal-specific configuration so the same processing and retrieval workflow can support another journal when its editors authorize the work.

## Roadmap status

- Step 1 (Development Foundation): complete; see `manuals/Step1.pdf`.
- Step 2 (Define and Acquire the POC Corpus): complete; see `manuals/Step2.pdf` and `data/metadata/step2_checkpoint.md`.
- Step 3 (Data Processing): complete with one documented non-searchable figure limitation; see `manuals/Step3.pdf` and `data/processed/step3_quality_report.md`.
- Step 4 (Retrieval-Augmented Generation): local semantic embeddings and hybrid retrieval, with Groq answer generation gated by the local `.env` consent setting. See `manuals/Step4.pdf` and `data/processed/step4_checkpoint.md`.
- Step 5 (Application): Streamlit search interface with semantic/lexical retrieval, source display, passage comparison, article-type filters and gated Groq synthesis. See `manuals/Step5.pdf` and `data/processed/step5_checkpoint.md`.
- Step 6 (Validation): Golden Test Set, retrieval metrics, structured source-ID validation, patient-boundary and no-answer checks. See `manuals/Step6.pdf`, `evaluation/results/`, and `data/processed/step6_checkpoint.md`.
- Step 7 (Demonstration): seven curated examples, a reproducible editor walkthrough, interface polish, readiness checkpoint, and POC test report. See `manuals/Step7.pdf`, `demo/Demonstration_Script.md`, and `data/processed/step7_checkpoint.md`.

## Requirements

- Windows 10 or later
- Python 3.11 or later (Python 3.12 is the current development target)
- Git for Windows

Python 3.11 or later is required because the configuration files use the standard-library TOML reader. `pypdf` is pinned for Step 3 page-level PDF extraction; FastEmbed runs the embedding model locally; the OpenAI-compatible SDK connects to Groq for gated answer generation.

## Create or recreate the environment

Open PowerShell in this `Project` folder and run:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell does not recognize `py`, install Python 3.11 or later from the official Python distribution and select the option to add the Python launcher to Windows. The current Codex session created the environment using its bundled Python 3.12.14 runtime; that bundled runtime is specific to this computer and is not a project dependency.

## Run the Step 1 readiness check

With the project virtual environment activated:

```powershell
python scripts\check_step1.py
```

The check confirms the Python version and active virtual environment, required folders and files, configuration validity, Git repository, and successful application startup. It also reports the current article-indexing permission status. A pending permission status is recorded as a warning for the later corpus-acquisition step; it does not prevent Step 1 from passing.

## Start the foundation application

```powershell
python scripts\run_app.py
```

To select another journal configuration for local development, set `JOURNAL_ASSISTANT_CONFIG` to a TOML file path before running the application. Copy `config\journals\journal_template.toml.example`, replace its placeholders, and review source-access permissions before using any journal content.

## Folder guide

- `config\app.toml` — application-wide defaults.
- `config\journals\` — one configuration file per journal, plus a reusable template.
- `src\journal_assistant\` — shared application code.
- `data\` — metadata, raw source files, processed text, indexes, and cache; local article files are ignored by Git by default.
- `scripts\` — setup checks and local entry points.
- `tests\` and `evaluation\` — reserved for later implementation and evaluation steps.

## Content access and reuse

The presence of a public article URL does not by itself confirm permission to download or index its full text. Keep the access review status accurate in each journal configuration. Do not place credentials or API keys in source files or commit local article PDFs unless the project has an approved basis for doing so.

## Step 3 - extract and quality-check the POC corpus

Activate `.venv`, install the declared project dependencies, and run:

```powershell
python scripts\process_step3.py
python scripts\check_step3.py
```

The processor reads but does not modify `data/raw/`. It writes page-level JSONL with raw and normalized extracted text, article-level page-marked text, a processing manifest, and page-level QA results under `data/processed/`. The checker verifies file hashes, page coverage, provenance, outputs, and quality flags. A page consisting mainly of a figure or table may require visual review or OCR before chunking.

## Step 4 - chunk, index, and retrieve evidence

```powershell
python scripts\prepare_step4_chunks.py
python scripts\build_step4_index.py
python scripts\check_step4.py
python scripts\ask_step4.py "ketorolac morphine sickle cell"
```

The SQLite index and embeddings are local. The first `--with-embeddings` run downloads the configured FastEmbed model into `data/models/fastembed`; after that, document and query embeddings run on this computer. Groq is used only for answer generation. The project `.env` must contain `GROQ_API_KEY` and `JOURNAL_ASSISTANT_ALLOW_EXTERNAL_TEXT_PROCESSING=true` for questions and retrieved passages to be sent to Groq. `.env` is ignored by Git; never put a real key in `.env.example` or commit it. The checker does not make an answer-generation API call.

## Step 5 - use the local Streamlit application

```powershell
python scripts\check_step5.py
python scripts\run_ui.py
```

The interface supports hybrid retrieval, publisher/source provenance, side-by-side comparison of retrieved articles, article-type filters, and Groq answer synthesis when the explicit gate and key are available. The UI tells users when a search will send the question and retrieved passages to Groq. Patient-specific questions are stopped before any Groq request. Select a journal profile and its `[corpus]` metadata/source paths in `config\journals\` when preparing another journal.

## Step 6 - validate retrieval, answers, citations and safety

```powershell
python scripts\evaluate_step6.py
python scripts\evaluate_step6.py --live-answers
```

The first command runs local retrieval and patient-boundary checks. The second makes two live Groq requests (one grounded topic question and one out-of-corpus question); it requires the explicit external-processing setting and stores answer text in `evaluation\results\step6_answer_review.csv` for human review. The versioned test set is `evaluation\golden_test_set.json`. Results are recorded in `evaluation\results\step6_evaluation.json` and `data\processed\step6_checkpoint.md`. Automated citation checks confirm that source IDs exist in the retrieved evidence, not that the cited passages substantively prove the generated claims. A qualified human review is still required; this POC is not clinically validated.

## Step 7 - prepare a controlled demonstration

```powershell
python scripts\check_step7.py
python scripts\run_ui.py
```

The UI includes journal-specific example questions from `evaluation\demo_questions.json`. The reproducible 10-15 minute walkthrough is in `demo\Demonstration_Script.md`. The check writes `data\processed\step7_checkpoint.md` and `evaluation\results\step7_poc_test_report.md`. A pass means the materials are ready for a controlled editor walkthrough with disclosures. It does not declare clinical validation, confirm rights to redistribute article content, or approve deployment. Step 6 expert review and publisher access/reuse confirmation remain open.
