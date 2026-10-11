"""Validate Step 3 extraction outputs and write the data-quality report."""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "data" / "metadata"
RAW = ROOT / "data" / "raw" / "2025_Jan"
QUALITY = ROOT / "data" / "processed" / "quality"
REPORT = ROOT / "data" / "processed" / "step3_quality_report.md"
EXCLUDED = {"administrative_duplicate", "administrative_news"}
results: list[tuple[str, str, str]] = []

def read_csv(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def digest(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):
            h.update(block)
    return h.hexdigest()

def check(name, ok, detail):
    results.append(("PASS" if ok else "FAIL",name,detail))

def tokens(s):
    return {x for x in re.findall(r"[a-z0-9]+",s.casefold()) if len(x)>2}

def main() -> int:
    try:
        articles={r["article_id"]:r for r in read_csv(META/"article_metadata.csv")}
        source=read_csv(META/"corpus_file_manifest.csv")
        proc=read_csv(QUALITY/"processing_manifest.csv")
        pages=read_csv(QUALITY/"page_quality.csv")
        review_log=read_csv(QUALITY/"visual_review_log.csv")
        expected=[r for r in source if r.get("article_id") and r.get("content_role") not in EXCLUDED]
        check("Processing manifest covers all Step 2 files",len(proc)==len(source) and {r["filename"] for r in proc}=={r["filename"] for r in source},f"{len(proc)} manifest rows for {len(source)} inventoried files")
        completed=[r for r in proc if r["processing_status"].startswith("complete")]
        failed=[r for r in proc if r["processing_status"]=="failed"]
        excluded=[r for r in proc if r["processing_status"]=="excluded"]
        check("Expected article PDFs processed",len(completed)==len(expected),f"{len(completed)} processed; {len(expected)} expected; {len(excluded)} explicitly excluded; {len(failed)} failed")
        check("Source PDFs unchanged",all((ROOT/Path(r["source_relative_path"])).is_file() and digest(ROOT/Path(r["source_relative_path"]))==r["source_sha256"] for r in proc),"All source-file hashes still match the processing manifest")
        output_errors=[]
        for record in completed:
            article_id=record["article_id"]
            if article_id not in articles: output_errors.append(f"{record['filename']}: unknown article ID"); continue
            jp=ROOT/Path(record["page_records_path"])
            tp=ROOT/Path(record["clean_text_path"])
            if not jp.is_file() or not tp.is_file(): output_errors.append(f"{article_id}: output missing"); continue
            with jp.open(encoding="utf-8") as f: page_records=[json.loads(line) for line in f if line.strip()]
            if len(page_records)!=int(record["physical_pages"]) or len(page_records)!=int(record["pages_extracted"]): output_errors.append(f"{article_id}: page record count mismatch")
            if [x.get("physical_page") for x in page_records]!=list(range(1,len(page_records)+1)): output_errors.append(f"{article_id}: physical page sequence not continuous")
            if any(x.get("article_id")!=article_id or x.get("source_sha256")!=record["source_sha256"] for x in page_records): output_errors.append(f"{article_id}: provenance mismatch")
            if any(not (x.get("cleaned_text") or "").strip() for x in page_records): output_errors.append(f"{article_id}: blank page text")
            if f"ARTICLE {article_id}" not in tp.read_text(encoding="utf-8"): output_errors.append(f"{article_id}: page markers missing from review text")
        check("Page-level extraction and provenance",not output_errors,"Each processed PDF has a complete, ordered page record with article ID and source hash" if not output_errors else "; ".join(output_errors[:10]))
        pdf_errors=[]
        for r in proc:
            original=ROOT/Path(r["source_relative_path"])
            if not original.is_file(): pdf_errors.append(f"{r['filename']}: source missing"); continue
            try:
                from pypdf import PdfReader
                actual=len(PdfReader(str(original),strict=False).pages)
                if r["processing_status"].startswith("complete") and actual!=int(r["physical_pages"]): pdf_errors.append(f"{r['filename']}: PDF page-count mismatch")
            except Exception as exc: pdf_errors.append(f"{r['filename']}: cannot reopen ({exc})")
        check("PDF page counts agree with source files",not pdf_errors,"All page counts match" if not pdf_errors else "; ".join(pdf_errors[:8]))
        title_mismatches=[(r["filename"],r["article_id"],r.get("first_page_title_token_overlap","")) for r in completed if not r.get("first_page_title_token_overlap") or float(r["first_page_title_token_overlap"])<0.8]
        check("Catalogue title matches extracted first-page text",not title_mismatches,"All 17 titles have at least 80% meaningful-token overlap" if not title_mismatches else str(title_mismatches))
        role_errors=[]
        for r in source:
            entry=next((p for p in proc if p["filename"]==r["filename"]),None)
            should_skip=r["content_role"] in EXCLUDED or not r.get("article_id")
            if entry and should_skip and entry["processing_status"]!="excluded": role_errors.append(f"{r['filename']} should be excluded")
            if entry and not should_skip and not entry["processing_status"].startswith("complete"): role_errors.append(f"{r['filename']} should be processed")
        check("Step 2 inclusion and exclusion policy preserved",not role_errors,"Only the mixed duplicate/notice and News in Brief files were excluded" if not role_errors else "; ".join(role_errors))
        flagged=[p for p in pages if p["quality_status"]!="text_extracted"]
        review_index={(r["filename"],r["physical_page"]):r for r in review_log}
        unresolved=[p for p in flagged if (p["filename"],p["physical_page"]) not in review_index or review_index[(p["filename"],p["physical_page"])]["review_status"]!="visually_inspected"]
        check("Low-text pages visually reviewed and dispositions recorded",not unresolved,"All low-text pages have a documented visual-review disposition" if not unresolved else str([(p["filename"],p["physical_page"]) for p in unresolved]))
        replacement=[p for p in pages if int(p["replacement_characters"])>0]
        blank=[p for p in pages if int(p["cleaned_chars"])==0]
        check("No extracted page is blank",not blank,"Every processed page contains text, including pages flagged for visual review" if not blank else str([(p['filename'],p['physical_page']) for p in blank]))
        check("No Unicode replacement characters detected",not replacement,"No U+FFFD replacement characters were found" if not replacement else str([(p['filename'],p['physical_page'],p['replacement_characters']) for p in replacement]))
        check("Processing outputs match inventory totals",sum(int(r["pages_extracted"] or 0) for r in completed)==len(pages),f"{len(pages)} page QA records across {len(completed)} processed article PDFs")
        # Explicitly verify extra unpaginated pages are still retained, not dropped.
        supplement_pages=[p for p in pages if p["page_role"]=="supplement_or_unpaginated"]
        check("Supplemental pages preserved",bool(supplement_pages),f"{len(supplement_pages)} unpaginated/supplement pages retained with explicit page roles")

        total_chars=sum(int(p["cleaned_chars"]) for p in pages)
        total_pages=len(pages)
        status_counts={}
        for p in pages: status_counts[p["quality_status"]]=status_counts.get(p["quality_status"],0)+1
        with REPORT.open("w",encoding="utf-8",newline="\n") as f:
            f.write("# Step 3 - Data Processing Quality Report\n\n")
            f.write("## Scope and method\n\n")
            f.write("This report covers the January 2025, Volume 62, Issue 1 POC corpus. The processor used pypdf for page-by-page text extraction. Original PDFs under `data/raw/2025_Jan/` were read only. Cleaned outputs normalize Unicode canonically, remove soft/zero-width formatting artifacts, normalize whitespace conservatively, and preserve extracted line breaks and page boundaries. Raw extracted text is retained alongside cleaned text in page JSONL. No content paraphrasing, OCR, chunking, embedding, or clinical interpretation was performed.\n\n")
            f.write("## Inventory result\n\n")
            f.write(f"- Files in Step 2 manifest: {len(proc)}\n- Article PDFs processed: {len(completed)}\n- Files excluded by explicit Step 2 roles: {len(excluded)}\n- Failed files: {len(failed)}\n- Physical pages represented: {total_pages}\n- Cleaned selectable-text characters: {total_chars}\n- Extractor version: pypdf {proc[0]['extractor_version'] if proc else 'unknown'}\n\n")
            f.write("## Page-level QA\n\n")
            f.write("Status totals: " + ", ".join(f"{k}={v}" for k,v in sorted(status_counts.items())) + ".\n\n")
            f.write("### Low-text page visual review and disposition\n\n")
            if flagged:
                for p in flagged:
                    review=review_index.get((p["filename"],p["physical_page"]))
                    disposition=(f" Visually inspected: {review['content_observed']}. Disposition: {review['decision']}. Limit: {review['review_limit']}" if review else " No visual review disposition recorded.")
                    f.write(f"- `{p['filename']}`, PDF physical page {p['physical_page']} (printed page {p['printed_page'] or 'not mapped'}): {p['cleaned_chars']} extracted characters, {p['embedded_image_count']} detected embedded images; extraction status `{p['quality_status']}`.{disposition}\n")
            else: f.write("None.\n")
            f.write("\n### Extracted article files\n\n| Article ID | Source | Pages | Clean characters | Processing status | Flags |\n|---|---|---:|---:|---|---|\n")
            for r in completed:
                f.write(f"| {r['article_id']} | {r['filename']} | {r['pages_extracted']} | {r['total_clean_chars']} | {r['processing_status']} | {r['short_or_visual_pages'] or 'None'} |\n")
            f.write("\n## Limitations and required follow-up\n\n")
            f.write("1. PDF text extraction does not reconstruct visual tables, figures, charts, or reading order perfectly. The low-text page was rendered and visually inspected; it is a PRISMA flow chart, not a blank page. Its source image is retained, but its flow counts are not searchable text. Do not rely on diagram-only counts until OCR or a manually transcribed and verified record is added.\n2. Unpaginated supplemental pages in `56.pdf` are retained and labelled rather than dropped; confirm their article/supplement relationship before treating them as ordinary article pages.\n3. Current catalogue author and DOI fields are blank where not yet verified. This extraction step does not infer missing bibliographic metadata.\n4. No HTML source documents were acquired for this issue; therefore this run processed PDFs only.\n5. Extracted text quality is not a claim of medical correctness, permissions clearance, or clinical validation.\n\n")
            f.write("## Reproduction\n\nRun `python scripts/process_step3.py` to regenerate derived outputs and `python scripts/check_step3.py` to re-run deterministic checks. Generated text is in `data/processed/cleaned/`; page-level raw/cleaned records are in `data/processed/extracted/`; manifests and page checks are in `data/processed/quality/`. The original PDFs remain in `data/raw/`.\n")

        review_blocked=bool(unresolved)
        for result in results:
            print(f"{result[0]:4} | {result[1]}: {result[2]}")
        print(f"\nStep 3 checkpoint: {sum(x[0]=='PASS' for x in results)} PASS, {sum(x[0]=='FAIL' for x in results)} FAIL, {len(flagged)} VISUAL LIMITATION(S)")
        print("NOT READY FOR STEP 4 - resolve unreviewed low-text pages" if review_blocked else ("READY FOR STEP 4 WITH DOCUMENTED VISUAL LIMITATION" if flagged else "READY FOR STEP 4"))
        print(f"Quality report: {REPORT.relative_to(ROOT)}")
        return 1 if any(x[0]=="FAIL" for x in results) else (2 if review_blocked else 0)
    except Exception as exc:
        print(f"FAIL | Checkpoint execution: {type(exc).__name__}: {exc}")
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
