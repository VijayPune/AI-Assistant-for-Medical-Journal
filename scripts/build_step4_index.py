"""Build the local full-text index; embeddings are optional and externally gated."""
from __future__ import annotations
import argparse, hashlib, json, sys, tomllib
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from journal_assistant.rag.store import SQLiteHybridStore
from journal_assistant.rag.providers.fastembed_provider import FastEmbedProvider

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("--with-embeddings",action="store_true"); args=p.parse_args()
    cfg=tomllib.loads((ROOT/"config/rag.toml").read_text(encoding="utf-8"))
    chunk_path=ROOT/"data/processed/chunks/chunks.jsonl"
    chunks=[json.loads(line) for line in chunk_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    vectors=None; provider=None
    if args.with_embeddings:
        settings=cfg["embedding"]
        cache=ROOT/settings["cache_directory"]
        provider=FastEmbedProvider(model_name=settings["model"],cache_directory=cache)
        batch=int(settings["batch_size"]); vectors=[]
        for start in range(0,len(chunks),batch):
            vectors.extend(provider.embed_documents([x["text"] for x in chunks[start:start+batch]],batch_size=batch))
        if len(vectors)!=len(chunks) or (vectors and len({len(v) for v in vectors})!=1):
            raise RuntimeError("Embedding output count or dimensions do not match the chunk corpus; existing index was preserved.")
    store=SQLiteHybridStore()
    store.reset()
    store.upsert_chunks(chunks,vectors,embedding_model=provider.model_name if provider else None)
    counts=store.counts(); store.close()
    if provider:
        manifest={"provider":"fastembed_local","model":provider.model_name,"chunk_count":counts["chunks"],
                  "vector_count":counts["vectors"],"vector_dimensions":len(vectors[0]) if vectors else 0,
                  "chunks_sha256":hashlib.sha256(chunk_path.read_bytes()).hexdigest(),
                  "created_at_utc":datetime.now(timezone.utc).isoformat(),
                  "article_text_sent_to_remote_embedding_service":False}
        output=ROOT/"data/processed/embeddings/embedding_manifest.json"; output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    print(f"Indexed {counts['chunks']} chunks locally; {counts['vectors']} embeddings.")
    if provider: print(f"Embeddings created on this computer with {provider.model_name}; article text was not sent to a remote embedding API.")
    return 0
if __name__=="__main__": raise SystemExit(main())
