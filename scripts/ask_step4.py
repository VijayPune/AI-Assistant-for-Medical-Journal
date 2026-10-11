"""Search the local corpus; provider-backed answering is enabled only by explicit opt-in."""
import argparse, sys, tomllib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"src"))
from journal_assistant.rag.store import SQLiteHybridStore
from journal_assistant.rag.retrieval import search
from journal_assistant.rag.answering import answer_question, is_patient_specific, PATIENT_BOUNDARY
from journal_assistant.rag.env import external_text_processing_allowed
from journal_assistant.rag.providers.fastembed_provider import FastEmbedProvider
from journal_assistant.rag.providers.groq_provider import GroqProvider
from journal_assistant.rag.providers.base import ProviderNotReady

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("question"); p.add_argument("--author"); p.add_argument("--year",type=int); p.add_argument("--volume",type=int); p.add_argument("--issue",type=int); args=p.parse_args()
    filters={k:v for k,v in {"author":args.author,"year":args.year,"volume":args.volume,"issue_number":args.issue}.items() if v is not None}
    cfg=tomllib.loads((ROOT/"config/rag.toml").read_text(encoding="utf-8")); store=SQLiteHybridStore()
    if is_patient_specific(args.question):
        print(PATIENT_BOUNDARY)
        store.close()
        return 0
    provider=None
    counts=store.counts()
    if external_text_processing_allowed():
        try: provider=GroqProvider(answer_model=cfg["generation"]["model"])
        except ProviderNotReady: pass
    query_vector=None
    if counts["vectors"]==counts["chunks"] and counts["chunks"]:
        emb_cfg=cfg["embedding"]
        embedder=FastEmbedProvider(model_name=emb_cfg["model"],cache_directory=ROOT/emb_cfg["cache_directory"])
        query_vector=embedder.embed_query(args.question)
    evidence=search(store,args.question,embedding=query_vector,top_k=int(cfg["retrieval"]["top_k"]),filters=filters,allowed_roles=set(cfg["retrieval"]["default_allowed_roles"]),minimum_semantic_similarity=cfg["retrieval"].get("minimum_semantic_similarity"))
    result=answer_question(args.question,evidence,provider)
    print(result.answer)
    for item in result.evidence:
        author=f" | {item['authors']}" if item.get("authors") else ""
        print(f"\n[{item['source_label']}] {item['title']}{author} ({item['year']}), {item['section']}, journal page {item['page_start'] or 'unmapped'}; PDF page {item['physical_page']}\n{item['source_url']}")
    store.close(); return 0
if __name__=="__main__": raise SystemExit(main())
