"""Page-aware, provenance-preserving text chunker."""
from __future__ import annotations

import json
import re
from pathlib import Path

from .env import ROOT

def _split_long(text: str, limit: int) -> list[str]:
    words = text.split()
    pieces, current = [], []
    length = 0
    for word in words:
        added = len(word) + (1 if current else 0)
        if current and length + added > limit:
            pieces.append(" ".join(current))
            current, length = [], 0
        current.append(word)
        length += len(word) + (1 if len(current) > 1 else 0)
    if current:
        pieces.append(" ".join(current))
    return pieces

def _page_chunks(text: str, target: int, overlap: int) -> list[str]:
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines() if line.strip()]
    units=[]
    for line in lines:
        units.extend(_split_long(line, target) if len(line)>target else [line])
    result=[]
    current=""
    for unit in units:
        joined=f"{current}\n{unit}" if current else unit
        if current and len(joined)>target:
            result.append(current)
            tail=current[-overlap:].split()
            current=(" ".join(tail)+"\n"+unit).strip() if tail else unit
            if len(current)>target:
                current=unit
        else:
            current=joined
    if current.strip(): result.append(current.strip())
    return result

def create_chunks(*, target_characters: int=1400, overlap_characters: int=180) -> tuple[list[dict],list[dict]]:
    if target_characters<300 or overlap_characters<0 or overlap_characters>=target_characters:
        raise ValueError("Chunk size must be >=300 and overlap must be smaller than chunk size")
    import csv
    metadata_path=ROOT/"data/metadata/article_metadata.csv"
    with metadata_path.open(encoding="utf-8-sig",newline="") as f:
        articles={r["article_id"]:r for r in csv.DictReader(f)}
    manifest_path=ROOT/"data/processed/quality/processing_manifest.csv"
    with manifest_path.open(encoding="utf-8-sig",newline="") as f:
        processed=list(csv.DictReader(f))
    chunks=[]; excluded=[]
    for doc in processed:
        if not doc["processing_status"].startswith("complete"):
            continue
        article=articles[doc["article_id"]]
        json_path=ROOT/Path(doc["page_records_path"])
        with json_path.open(encoding="utf-8") as f:
            pages=[json.loads(line) for line in f if line.strip()]
        for page in pages:
            if page["quality_status"]!="text_extracted":
                excluded.append({"article_id":page["article_id"],"source_filename":page["source_filename"],"physical_page":page["physical_page"],"printed_page":page.get("printed_page"),"reason":"Page has a visual-review flag; excluded from text chunks"})
                continue
            for page_part, text in enumerate(_page_chunks(page["cleaned_text"],target_characters,overlap_characters),start=1):
                printed=page.get("printed_page")
                page_component=str(printed) if printed else f"PDF{page['physical_page']}"
                chunk_id=f"{page['article_id']}-P{page_component}-C{page_part:02d}"
                chunks.append({
                    "chunk_id":chunk_id,"article_id":page["article_id"],"journal":page["journal"],
                    "title":article["title"],"authors":article.get("authors", ""),
                    "section":article["section"],"content_role":article["content_role"],
                    "year":int(article["year"]),"month":int(article["month"]),
                    "volume":int(article["volume"]),"issue_number":int(article["issue_number"]),
                    "issue_id":article["issue_id"],"page_start":printed or "",
                    "page_end":printed or "","physical_page":page["physical_page"],
                    "page_role":page["page_role"],"source_filename":page["source_filename"],
                    "source_sha256":page["source_sha256"],"source_url":article["publisher_issue_url"],
                    "text":text,"chunk_char_count":len(text),"page_chunk_index":page_part,
                })
    return chunks,excluded

def write_chunks(chunks: list[dict], excluded: list[dict], out_dir: Path|None=None) -> tuple[Path,Path]:
    out_dir=out_dir or ROOT/"data/processed/chunks"
    out_dir.mkdir(parents=True,exist_ok=True)
    chunk_path=out_dir/"chunks.jsonl"
    exclusion_path=out_dir/"chunk_exclusions.jsonl"
    with chunk_path.open("w",encoding="utf-8",newline="\n") as f:
        for item in chunks: f.write(json.dumps(item,ensure_ascii=False)+"\n")
    with exclusion_path.open("w",encoding="utf-8",newline="\n") as f:
        for item in excluded: f.write(json.dumps(item,ensure_ascii=False)+"\n")
    return chunk_path,exclusion_path
