"""Create page-aware chunks from the Step 3 cleaned page records."""
from __future__ import annotations

import tomllib
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from journal_assistant.rag.chunking import create_chunks,write_chunks

def main():
    with (ROOT/"config/rag.toml").open("rb") as f: config=tomllib.load(f)
    settings=config["chunking"]
    chunks,excluded=create_chunks(target_characters=int(settings["target_characters"]),overlap_characters=int(settings["overlap_characters"]))
    chunk_path,exclude_path=write_chunks(chunks,excluded)
    print(f"Created {len(chunks)} chunks from processed pages; excluded {len(excluded)} flagged pages.")
    print("Chunk file:",chunk_path.relative_to(ROOT))
    print("Exclusion log:",exclude_path.relative_to(ROOT))
    return 0

if __name__=="__main__": raise SystemExit(main())
