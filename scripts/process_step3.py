"""Extract page text for the selected POC PDFs without changing raw sources."""
from __future__ import annotations

import csv
import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import pypdf
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "2025_Jan"
META = ROOT / "data" / "metadata"
PROCESSED = ROOT / "data" / "processed"
EXTRACTED = PROCESSED / "extracted"
CLEANED = PROCESSED / "cleaned"
QUALITY = PROCESSED / "quality"
MIN_TEXT_CHARS = 200
EXCLUDED_ROLES = {"administrative_duplicate", "administrative_news"}

def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

def clean_page(text: str) -> str:
    """Normalize extraction noise conservatively; preserve line and paragraph order."""
    text = unicodedata.normalize("NFC", text or "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00ad", "")  # soft hyphen inserted by layout, not a visible word character
    text = text.replace("\ufeff", "").replace("\u200b", "")
    for ligature, expanded in {"\ufb00":"ff", "\ufb01":"fi", "\ufb02":"fl", "\ufb03":"ffi", "\ufb04":"ffl", "\ufb05":"st", "\ufb06":"st"}.items():
        text = text.replace(ligature, expanded)
    cleaned_lines = []
    for line in text.split("\n"):
        line = line.replace("\u00a0", " ").replace("\t", " ")
        line = re.sub(r"[ ]{2,}", " ", line).strip()
        cleaned_lines.append(line)
    text = "\n".join(cleaned_lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def get_printed_page(text: str, physical_page: int, start: str, end: str, page_count: int) -> tuple[str, str]:
    if start.isdigit() and end.isdigit():
        span = int(end) - int(start) + 1
        if physical_page <= span:
            return str(int(start) + physical_page - 1), "article"
        return "", "supplement_or_unpaginated"
    match = re.search(r"INDIAN\s+PEDIATRICS\s+(\d{1,4})\b", text[:500], re.IGNORECASE)
    if match:
        return match.group(1), "issue_content"
    return "", "unmapped_page"

def image_count(page) -> int:
    try:
        return len(page.images)
    except Exception:
        return 0

def main() -> int:
    EXTRACTED.mkdir(parents=True, exist_ok=True)
    CLEANED.mkdir(parents=True, exist_ok=True)
    QUALITY.mkdir(parents=True, exist_ok=True)
    articles = {r["article_id"]: r for r in load_csv(META / "article_metadata.csv")}
    files = load_csv(META / "corpus_file_manifest.csv")
    manifest_rows: list[dict[str, str]] = []
    page_rows: list[dict[str, str]] = []
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    for record in files:
        filename = record["filename"]
        source = ROOT / Path(record["relative_path"])
        article_id = record.get("article_id", "")
        role = record.get("content_role", "")
        excluded = role in EXCLUDED_ROLES or not article_id
        digest = sha256(source) if source.is_file() else ""
        row = {
            "filename": filename, "article_id": article_id, "content_role": role,
            "source_relative_path": record.get("relative_path", ""), "source_sha256": digest,
            "extractor": "pypdf", "extractor_version": pypdf.__version__,
            "processed_at_utc": now, "processing_status": "excluded" if excluded else "pending",
            "physical_pages": "", "pages_extracted": "", "total_clean_chars": "",
            "short_or_visual_pages": "", "replacement_chars": "",
            "first_page_title_token_overlap": "",
            "page_records_path": "", "clean_text_path": "", "notes": "",
        }
        if excluded:
            row["notes"] = "Excluded by Step 2 scope: " + record.get("section_or_file_role", role)
            manifest_rows.append(row)
            continue
        if not source.is_file():
            row["processing_status"] = "failed"
            row["notes"] = "Source file is missing"
            manifest_rows.append(row)
            continue
        article = articles.get(article_id)
        if not article:
            row["processing_status"] = "failed"
            row["notes"] = "Article ID not found in article catalogue"
            manifest_rows.append(row)
            continue

        try:
            reader = PdfReader(str(source), strict=False)
            if reader.is_encrypted:
                row["processing_status"] = "failed"
                row["notes"] = "Encrypted PDF is not processed"
                manifest_rows.append(row)
                continue
            physical_count = len(reader.pages)
            json_path = EXTRACTED / f"{article_id}.jsonl"
            text_path = CLEANED / f"{article_id}.txt"
            docs: list[dict] = []
            text_parts: list[str] = []
            total_chars = 0
            review_pages: list[str] = []
            replacement_count = 0
            for page_no, page in enumerate(reader.pages, start=1):
                raw_text = page.extract_text() or ""
                cleaned = clean_page(raw_text)
                printed, page_role = get_printed_page(raw_text, page_no, article.get("page_start", ""), article.get("page_end", ""), physical_count)
                chars = len(cleaned)
                replacement = raw_text.count("\ufffd")
                replacement_count += replacement
                embedded_images = image_count(page)
                if chars < MIN_TEXT_CHARS:
                    page_status = "visual_review_required" if embedded_images or page_role == "supplement_or_unpaginated" else "text_review_required"
                    review_pages.append(f"physical {page_no}" + (f" / printed {printed}" if printed else ""))
                else:
                    page_status = "text_extracted"
                page_record = {
                    "schema_version": "1.0", "article_id": article_id,
                    "journal": article["journal"], "title": article["title"],
                    "section": article["section"], "content_role": article["content_role"],
                    "issue_id": article["issue_id"], "year": int(article["year"]),
                    "volume": int(article["volume"]), "issue_number": int(article["issue_number"]),
                    "source_filename": filename, "source_relative_path": record["relative_path"],
                    "source_sha256": digest, "physical_page": page_no,
                    "printed_page": printed or None, "page_role": page_role,
                    "embedded_image_count": embedded_images, "raw_text": raw_text,
                    "cleaned_text": cleaned, "cleaned_char_count": chars,
                    "replacement_character_count": replacement, "quality_status": page_status,
                }
                docs.append(page_record)
                text_parts.append(f"\n\n=== ARTICLE {article_id} | SOURCE {filename} | PDF PAGE {page_no} | PRINTED PAGE {printed or 'not mapped'} | {page_role.upper()} ===\n\n{cleaned}")
                page_rows.append({
                    "article_id": article_id, "filename": filename, "physical_page": str(page_no),
                    "printed_page": printed, "page_role": page_role, "raw_chars": str(len(raw_text)),
                    "cleaned_chars": str(chars), "embedded_image_count": str(embedded_images),
                    "replacement_characters": str(replacement), "quality_status": page_status,
                })
                total_chars += chars
            with json_path.open("w", encoding="utf-8", newline="\n") as f:
                for page_record in docs:
                    f.write(json.dumps(page_record, ensure_ascii=False) + "\n")
            with text_path.open("w", encoding="utf-8", newline="\n") as f:
                f.write(f"ARTICLE_ID: {article_id}\nTITLE: {article['title']}\nSECTION: {article['section']}\nCONTENT_ROLE: {article['content_role']}\nSOURCE: {filename}\nSOURCE_SHA256: {digest}\nEXTRACTOR: pypdf {pypdf.__version__}\n")
                f.write("".join(text_parts).lstrip())
            row.update({
                "processing_status": "complete_with_review_flags" if review_pages or replacement_count else "complete",
                "physical_pages": str(physical_count), "pages_extracted": str(len(docs)),
                "total_clean_chars": str(total_chars), "short_or_visual_pages": "; ".join(review_pages),
                "replacement_chars": str(replacement_count),
                "first_page_title_token_overlap": str(round(len({t for t in re.findall(r'[a-z0-9]+', article['title'].casefold()) if len(t)>2} & {t for t in re.findall(r'[a-z0-9]+', docs[0]['raw_text'].casefold()) if len(t)>2}) / max(1, len({t for t in re.findall(r'[a-z0-9]+', article['title'].casefold()) if len(t)>2})), 3)),
                "page_records_path": json_path.relative_to(ROOT).as_posix(),
                "clean_text_path": text_path.relative_to(ROOT).as_posix(),
                "notes": "Review low-text pages; image-only figures/tables are not transcribed by text extraction." if review_pages else "",
            })
        except Exception as exc:
            row["processing_status"] = "failed"
            row["notes"] = f"{type(exc).__name__}: {exc}"
        manifest_rows.append(row)

    write_csv(QUALITY / "processing_manifest.csv", list(manifest_rows[0].keys()), manifest_rows)
    page_fields = list(page_rows[0].keys()) if page_rows else ["article_id","filename","physical_page","printed_page","page_role","raw_chars","cleaned_chars","embedded_image_count","replacement_characters","quality_status"]
    write_csv(QUALITY / "page_quality.csv", page_fields, page_rows)
    print(f"Processed {sum(r['processing_status'].startswith('complete') for r in manifest_rows)} article PDFs; excluded {sum(r['processing_status']=='excluded' for r in manifest_rows)}; failed {sum(r['processing_status']=='failed' for r in manifest_rows)}")
    print(f"Wrote {len(page_rows)} page records using pypdf {pypdf.__version__}")
    print(f"Outputs: {QUALITY.relative_to(ROOT)}")
    return 1 if any(r["processing_status"] == "failed" for r in manifest_rows) else 0

if __name__ == "__main__":
    raise SystemExit(main())
