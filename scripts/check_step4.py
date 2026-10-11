"""Check the local hybrid RAG index without making any answer-provider calls."""
from __future__ import annotations
import hashlib, json, os, sys, tomllib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from journal_assistant.rag.store import SQLiteHybridStore
from journal_assistant.rag.env import external_text_processing_allowed, load_project_env
from journal_assistant.rag.answering import answer_question
from journal_assistant.rag.providers.fastembed_provider import FastEmbedProvider
from journal_assistant.rag.retrieval import search

def main():
    checks=[]
    def record(name,ok,detail): checks.append((name,bool(ok),detail))
    cfg=tomllib.loads((ROOT/"config/rag.toml").read_text(encoding="utf-8"))
    chunk_file=ROOT/"data/processed/chunks/chunks.jsonl"; exclusion_file=ROOT/"data/processed/chunks/chunk_exclusions.jsonl"
    chunks=[json.loads(x) for x in chunk_file.read_text(encoding="utf-8").splitlines() if x.strip()] if chunk_file.exists() else []
    exclusions=[json.loads(x) for x in exclusion_file.read_text(encoding="utf-8").splitlines() if x.strip()] if exclusion_file.exists() else []
    ids=[x["chunk_id"] for x in chunks]
    record("Chunk output exists and is nonempty",bool(chunks),f"{len(chunks)} chunks")
    record("Chunk IDs are unique",len(ids)==len(set(ids)),f"{len(ids)-len(set(ids))} duplicate IDs")
    required={"article_id","title","authors","section","content_role","year","month","volume","issue_number","issue_id","physical_page","source_filename","source_sha256","source_url","text"}
    bad=[x["chunk_id"] for x in chunks if not required.issubset(x) or not x.get("text","").strip()]
    record("Chunk text and provenance complete",not bad,f"{len(bad)} malformed chunks")
    flagged=[e for e in exclusions if e.get("physical_page")==4 and e.get("source_filename")=="56.pdf"]
    record("Known visual-review page excluded and logged",bool(flagged),f"{len(exclusions)} page(s) excluded")
    store=SQLiteHybridStore()
    counts=store.counts(); record("SQLite index count matches chunks",counts["chunks"]==len(chunks),f"{counts['chunks']} rows")
    record("Vector count is truthful",counts["vectors"]==0 or counts["vectors"]==len(chunks),f"{counts['vectors']} stored vectors")
    vector_rows=store.db.execute("SELECT COUNT(DISTINCT embedding_dimensions) dimensions, COUNT(DISTINCT embedding_model) models FROM chunks WHERE embedding IS NOT NULL").fetchone()
    dims=int(vector_rows["dimensions"] or 0); models=int(vector_rows["models"] or 0)
    record("All semantic vectors use one model and dimension",counts["vectors"]==0 or (counts["vectors"]==len(chunks) and dims==1 and models==1),f"{dims} dimensions; {models} model identity")
    manifest_path=ROOT/"data/processed/embeddings/embedding_manifest.json"
    manifest=json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    manifest_ok=(manifest.get("provider")=="fastembed_local" and manifest.get("model")==cfg["embedding"]["model"] and manifest.get("chunk_count")==len(chunks) and manifest.get("vector_count")==counts["vectors"] and manifest.get("chunks_sha256")==hashlib.sha256((ROOT/"data/processed/chunks/chunks.jsonl").read_bytes()).hexdigest() and manifest.get("article_text_sent_to_remote_embedding_service") is False)
    record("Local embedding manifest matches the chunk corpus",bool(manifest_ok),"Model, vector count, corpus checksum and local-processing declaration verified" if manifest_ok else "Manifest missing or inconsistent")
    roles=set(cfg["retrieval"]["default_allowed_roles"])
    evidence=store.lexical_search("ketorolac morphine sickle cell",limit=10,allowed_roles=roles)
    expected="IP-2025-V62-I01-004"
    record("Known corpus query retrieves expected article",any(x["article_id"]==expected for x in evidence),f"{len(evidence)} result(s); expected article {'found' if any(x['article_id']==expected for x in evidence) else 'not found'}")
    semantic_ok=False
    if counts["vectors"]==len(chunks) and chunks:
        settings=cfg["embedding"]
        embedder=FastEmbedProvider(model_name=settings["model"],cache_directory=ROOT/settings["cache_directory"])
        query="What does the issue report about ketorolac compared with morphine for sickle-cell pain?"
        hybrid=search(store,query,embedding=embedder.embed_query(query),top_k=10,allowed_roles=roles,minimum_semantic_similarity=cfg["retrieval"].get("minimum_semantic_similarity"))
        semantic_ok=any(x["article_id"]==expected for x in hybrid)
    record("Local semantic and hybrid query retrieves expected article",semantic_ok,f"Expected article {'found' if semantic_ok else 'not found'} in semantic/hybrid results")
    class FakeProvider:
        def __init__(self,text): self.text=text
        def answer(self,*args,**kwargs): return self.text
    one_source=[dict(evidence[0],source_label="S1")] if evidence else []
    valid_citation=answer_question("Summarize the article",one_source,FakeProvider('{"insufficient_evidence":false,"claims":[{"text":"Supported statement.","source_ids":["S1"]}]}'))
    invalid_citation=answer_question("Summarize the article",one_source,FakeProvider('{"insufficient_evidence":false,"claims":[{"text":"Unsupported source.","source_ids":["S9"]}]}'))
    record("Citation validator accepts only retrieved source labels",bool(one_source) and valid_citation.status=="answered" and invalid_citation.status=="citation_validation_failed","Valid label accepted; invented label rejected")
    no_answer=answer_question("unmatched question",[],None)
    patient=answer_question("What dose should I give my child?",one_source,FakeProvider("Should not be called"))
    record("No-evidence and patient-boundary fallbacks work",no_answer.status=="no_evidence" and patient.status=="patient_specific_boundary" and not patient.evidence,"No-evidence abstains; patient-specific question returns no source cards")
    nonsense=store.lexical_search("zzzxqv nonexistingword",limit=5,allowed_roles=roles)
    record("No-match query produces empty evidence",not nonsense,f"{len(nonsense)} result(s)")
    filtered=store.lexical_search("ketorolac morphine sickle cell",limit=20,allowed_roles=roles,filters={"article_id":expected})
    record("Article metadata filter works",bool(filtered) and all(x["article_id"]==expected for x in filtered),f"{len(filtered)} filtered result(s)")
    role_test=store.lexical_search("ketorolac morphine sickle cell",limit=20,allowed_roles={"secondary_source"})
    record("Content-role filter excludes other article roles",all(x["content_role"]=="secondary_source" for x in role_test) and all(x["article_id"]!=expected for x in role_test),f"{len(role_test)} secondary-source result(s); original-article leakage={'yes' if any(x['article_id']==expected for x in role_test) else 'no'}")
    store.close()
    load_project_env(); key=bool(os.getenv("GROQ_API_KEY")); allow=external_text_processing_allowed()
    record("Groq answer-provider credentials configured",key,"Configured; secret not displayed" if key else "GROQ_API_KEY not configured")
    record("External text processing explicitly enabled",allow,"Enabled by explicit configuration" if allow else "Disabled (safe default)")
    vectors_ready=counts["vectors"]>0 and counts["vectors"]==counts["chunks"] and bool(manifest_ok)
    record("Semantic embeddings available locally",vectors_ready,f"{counts['vectors']} / {counts['chunks']} chunks have model vectors")
    record("Groq generation model configured",cfg["generation"]["provider"]=="groq" and bool(cfg["generation"]["model"]),f"{cfg['generation']['provider']}: {cfg['generation']['model']}")
    passed=sum(ok for _,ok,_ in checks)
    incomplete={"Groq answer-provider credentials configured","External text processing explicitly enabled","Semantic embeddings available locally","Groq generation model configured"}
    failures=[n for n,ok,_ in checks if not ok and n not in incomplete]
    provider_ready=key and allow and vectors_ready and cfg["generation"]["provider"]=="groq"
    state="RAG FOUNDATION READY FOR STEP 6 VALIDATION" if not failures and provider_ready else ("LOCAL CHECKS PASS; RAG SETUP INCOMPLETE" if not failures else "NOT READY")
    lines=["# Step 4 checkpoint: RAG", "",f"**Overall status:** {state}","",f"**Deterministic checks:** {sum(ok for n,ok,_ in checks if n not in incomplete)} passed; {len(failures)} failed.",f"**Provider/embedding setup:** {sum(ok for n,ok,_ in checks if n in incomplete)} of {len(incomplete)} configured.","", "| Check | Result | Detail |","|---|---:|---|"]
    lines += [f"| {n} | {'PASS' if ok else ('PENDING' if n in incomplete else 'FAIL')} | {d} |" for n,ok,d in checks]
    lines += ["", "## Interpretation", "", "Document and query embeddings are generated locally by FastEmbed; article text is not sent to a remote embedding service. When the external-processing switch is enabled, question text and retrieved passages are sent to Groq for answer generation. This checkpoint itself makes no Groq answer request. The Step 3 visual-review exception remains excluded from text evidence.",""]
    report=ROOT/"data/processed/step4_checkpoint.md"; report.parent.mkdir(parents=True,exist_ok=True); report.write_text("\n".join(lines),encoding="utf-8")
    for name,ok,detail in checks: print(f"{'PASS' if ok else ('PENDING' if name in incomplete else 'FAIL')}: {name} - {detail}")
    print(f"\n{state}\nCheckpoint: {report.relative_to(ROOT)}")
    return 1 if failures else 0
if __name__=="__main__": raise SystemExit(main())
