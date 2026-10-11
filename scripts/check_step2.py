"""Checkpoint for Step 2: Define and Acquire the POC Corpus."""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "data" / "metadata"
RAW = ROOT / "data" / "raw" / "2025_Jan"

def read_csv(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

results: list[tuple[str, str, str]] = []
def check(name: str, ok: bool, detail: str):
    results.append(("PASS" if ok else "FAIL", name, detail))
def warn(name: str, detail: str):
    results.append(("WARN", name, detail))

try:
    article_path = META / "article_metadata.csv"
    manifest_path = META / "corpus_file_manifest.csv"
    articles = read_csv(article_path)
    manifest = read_csv(manifest_path)
    expected_article_cols = {"article_id", "title", "journal", "publication_date", "year", "month", "volume", "issue_number", "issue_id", "section", "acquisition_status", "content_role", "access_basis", "external_demo_permission"}
    expected_file_cols = {"filename", "relative_path", "content_role", "pdf_bytes", "physical_pages", "text_extractable", "include_in_clinical_retrieval"}
    check("Metadata files and required columns", expected_article_cols.issubset(articles[0].keys()) and expected_file_cols.issubset(manifest[0].keys()), "Both CSV catalogues exist with required fields")
    ids = [r["article_id"] for r in articles]
    check("Issue catalogue records", len(articles) == 19 and len(ids) == len(set(ids)), f"{len(articles)} records; {len(set(ids))} unique IDs (expected 19)")
    required = ("article_id", "title", "journal", "publication_date", "year", "month", "volume", "issue_number", "issue_id", "section", "acquisition_status", "content_role", "access_basis", "external_demo_permission")
    blank = [(r.get("article_id", "?"), c) for r in articles for c in required if not (r.get(c) or "").strip()]
    check("Required catalogue metadata populated", not blank, "No required fields are blank" if not blank else f"Missing values: {blank[:8]}")
    pdfs = sorted(p.name for p in RAW.glob("*.pdf"))
    names = [r["filename"] for r in manifest]
    check("Manifest matches supplied PDF folder", len(names) == len(set(names)) and sorted(names) == pdfs, f"Manifest {len(names)} files; folder {len(pdfs)} PDFs")
    invalid = []
    for r in manifest:
        path = ROOT / Path(r["relative_path"])
        if not path.is_file() or path.stat().st_size == 0:
            invalid.append(f"{r['filename']}: missing or empty")
        elif path.read_bytes()[:5] != b"%PDF-":
            invalid.append(f"{r['filename']}: PDF signature absent")
        if not r.get("article_id") and r.get("content_role") not in {"administrative_news", "administrative_duplicate", "unclassified"}:
            invalid.append(f"{r['filename']}: no article ID or explicit file role")
    check("Supplied files present and structurally recognizable", not invalid, "All manifest files exist and start with a PDF signature" if not invalid else "; ".join(invalid))
    badtext = [r["filename"] for r in manifest if r.get("text_extractable") != "yes"]
    check("Text availability recorded", not badtext, "Text extraction was confirmed for every PDF" if not badtext else f"No extractable text recorded: {badtext}")
    scoped_corr = [r for r in articles if r["section"] == "Correspondence" and r["acquisition_status"] == "scoped_out"]
    check("Out-of-scope issue entries explicitly tracked", len(scoped_corr) == 2, f"{len(scoped_corr)} Correspondence entries marked scoped_out (expected 2)")
    safe_exclusions = [r for r in manifest if r["filename"] == "84.pdf" and r["include_in_clinical_retrieval"] == "no" and r["content_role"] == "administrative_news"]
    safe_duplicate = [r for r in manifest if r["filename"] == "14.pdf" and r["include_in_clinical_retrieval"] == "no" and r["content_role"] == "administrative_duplicate"]
    check("Administrative/news material excluded", bool(safe_exclusions) and bool(safe_duplicate), "News item and mixed duplicate/notice file are catalogue-only")
    clipping = [r for r in manifest if r["filename"] == "83.pdf" and r["include_in_clinical_retrieval"] == "limited"]
    check("Secondary clipping has limited retrieval role", bool(clipping), "Clippings retained with reduced priority")
    warn("Reuse permissions for editor-facing demonstration", "User states local copies are accessible for internal POC; confirm publisher/editor permission before external redistribution or product demonstration")
    if len(scoped_corr) != 2:
        warn("Corpus completeness", "The two unavailable Correspondence items must be explicitly scoped out or acquired before Step 3")
except Exception as exc:
    check("Checkpoint execution", False, f"{type(exc).__name__}: {exc}")

for status, name, detail in results:
    print(f"{status:4} | {name}: {detail}")
passed = sum(s == "PASS" for s, _, _ in results)
failed = sum(s == "FAIL" for s, _, _ in results)
warnings = sum(s == "WARN" for s, _, _ in results)
print(f"\nStep 2 checkpoint: {passed} PASS, {failed} FAIL, {warnings} WARN")
incomplete = any(name == "Corpus completeness" for status, name, _ in results if status == "WARN")
print("READY FOR STEP 3" if failed == 0 and not incomplete else "NOT READY FOR STEP 3")
sys.exit(1 if failed else (2 if incomplete else 0))
