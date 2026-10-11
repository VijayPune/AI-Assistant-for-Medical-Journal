"""Evaluate the POC on its versioned Golden Test Set; --live-answers sends passages to Groq."""
from __future__ import annotations
import argparse, csv, json, sys, tomllib
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from journal_assistant.rag.answering import answer_question, is_patient_specific
from journal_assistant.rag.env import external_text_processing_allowed
from journal_assistant.rag.providers.fastembed_provider import FastEmbedProvider
from journal_assistant.rag.providers.groq_provider import GroqProvider
from journal_assistant.rag.retrieval import search
from journal_assistant.rag.store import SQLiteHybridStore

def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live-answers",action="store_true",help="Send eligible questions and retrieved passages to the configured answer provider.")
    args=parser.parse_args()
    if args.live_answers and not external_text_processing_allowed():
        parser.error("Live answers require JOURNAL_ASSISTANT_ALLOW_EXTERNAL_TEXT_PROCESSING=true in the local .env file.")
    gold=json.loads((ROOT/"evaluation/golden_test_set.json").read_text(encoding="utf-8"))
    cfg=tomllib.loads((ROOT/"config/rag.toml").read_text(encoding="utf-8"))
    settings=cfg["embedding"]
    embedder=FastEmbedProvider(model_name=settings["model"],cache_directory=ROOT/settings["cache_directory"])
    store=SQLiteHybridStore(); roles=set(cfg["retrieval"]["default_allowed_roles"])
    results=[]; ranked=[]; live_rows=[]
    try:
        for item in gold["questions"]:
            query=item["question"]
            patient=item["kind"]=="patient_specific"
            evidence=[] if patient else search(store,query,embedding=embedder.embed_query(query),top_k=int(cfg["retrieval"]["top_k"]),allowed_roles=roles,minimum_semantic_similarity=cfg["retrieval"].get("minimum_semantic_similarity"))
            ids=[]
            for e in evidence:
                if e["article_id"] not in ids: ids.append(e["article_id"])
            expected=set(item["relevant_article_ids"])
            hit=bool(expected.intersection(ids))
            rr=next((1/(rank+1) for rank,article in enumerate(ids) if article in expected),0.0) if expected else 0.0
            if item["kind"]=="topic": ranked.append((hit,rr))
            checks=[]
            if patient:
                boundary=answer_question(query,evidence).status=="patient_specific_boundary"
                checks.append(boundary)
            elif item["kind"]=="topic":
                checks.append(hit)
            generated_status="NOT_RUN"
            if args.live_answers and item["id"] in {"G01","G11"} and evidence:
                try:
                    answer=answer_question(query,evidence,GroqProvider(answer_model=cfg["generation"]["model"]))
                    generated_status=answer.status
                    live_rows.append({"id":item["id"],"question":query,"status":answer.status,"answer":answer.answer,"retrieved_article_ids":";".join(ids),"human_review":"PENDING"})
                except Exception as exc:
                    generated_status=f"provider_error:{type(exc).__name__}"
                    live_rows.append({"id":item["id"],"question":query,"status":generated_status,"answer":"Generation call failed; no answer shown.","retrieved_article_ids":";".join(ids),"human_review":"PENDING"})
            if item["kind"]=="no_evidence" and args.live_answers:
                checks.append(generated_status=="no_evidence_from_generation")
            results.append({"id":item["id"],"kind":item["kind"],"hit_at_6":hit,"reciprocal_rank":rr,"expected_article_ids":sorted(expected),"retrieved_article_ids":ids,"generation_status":generated_status,"status":"PASS" if all(checks) else "REVIEW/FAIL"})
    finally:
        store.close()
    topics=ranked
    hit_rate=sum(x[0] for x in topics)/len(topics) if topics else 0.0
    mrr=sum(x[1] for x in topics)/len(topics) if topics else 0.0
    threshold=gold["retrieval_targets"]
    retrieval_pass=hit_rate>=threshold["minimum_hit_at_6"] and mrr>=threshold["minimum_mrr_at_6"]
    safety_kinds={"patient_specific","no_evidence"} if args.live_answers else {"patient_specific"}
    safe=all(x["status"]=="PASS" for x in results if x["kind"] in safety_kinds)
    generated={x["id"]:x["status"] for x in live_rows}
    automated_answer_pass=(generated.get("G01")=="answered" and generated.get("G11")=="no_evidence_from_generation") if args.live_answers else False
    out=ROOT/"evaluation/results"; out.mkdir(parents=True,exist_ok=True)
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    payload={"evaluation_version":gold["version"],"run_utc":stamp,"corpus":"January 2025, Volume 62, Issue 1","retrieval":{"topic_question_count":len(topics),"hit_at_6":round(hit_rate,4),"mrr_at_6":round(mrr,4),"target_hit_at_6":threshold["minimum_hit_at_6"],"target_mrr_at_6":threshold["minimum_mrr_at_6"],"target_pass":retrieval_pass},"safety_cases_pass":safe,"live_answers_requested":args.live_answers,"live_answers_citation_and_abstention_pass":automated_answer_pass,"live_answer_statuses":generated,"per_question":results,"limitations":["Article-level retrieval relevance is a preliminary label and should be confirmed by a pediatric literature reviewer.","Automated citation-ID checks do not establish that a cited passage substantively supports a claim.","This one-issue proof of concept is not clinically validated."]}
    report=out/"step6_evaluation.json"; report.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    if live_rows:
        review=out/"step6_answer_review.csv"
        with review.open("w",newline="",encoding="utf-8-sig") as f:
            writer=csv.DictWriter(f,fieldnames=list(live_rows[0])); writer.writeheader(); writer.writerows(live_rows)
    md=["# Step 6 checkpoint: Validation","",f"**Run (UTC):** {stamp}","",f"**Retrieval:** Hit@6 {hit_rate:.1%} (target {threshold['minimum_hit_at_6']:.0%}); MRR@6 {mrr:.3f} (target {threshold['minimum_mrr_at_6']:.2f}); {'PASS' if retrieval_pass else 'FAIL'}.",f"**Patient-specific boundary:** {'PASS' if any(x['id']=='G12' and x['status']=='PASS' for x in results) else 'FAIL'}.",f"**Out-of-corpus no-answer generation:** {generated.get('G11','NOT RUN')}.",f"**Live answer citation/abstention check:** {'PASS' if automated_answer_pass else ('NOT RUN' if not args.live_answers else 'FAIL/REVIEW')}.","","## Golden Test Set results","","| ID | Type | Expected article | Retrieved article(s) | Hit@6 | Result |","|---|---|---|---|---:|---|"]
    for row in results:
        md.append(f"| {row['id']} | {row['kind']} | {', '.join(row['expected_article_ids']) or 'none'} | {', '.join(row['retrieved_article_ids']) or 'none'} | {'yes' if row['hit_at_6'] else 'no'} | {row['status']} |")
    md += ["","## Human review still required","","Use `evaluation/results/step6_answer_review.csv` to review generated answers. For each response, verify factual correctness against the cited passage, study-design interpretation, completeness, and absence of unsupported clinical advice. Citation IDs being syntactically valid is not proof of entailment.","","## Interpretation and limits","","A small single-issue dataset tests this implementation path; it cannot establish clinical safety or performance on other journals. Human review is required before closing answer correctness and grounding. Article-level expected-relevance labels must also be reviewed. The corpus remains limited to the January 2025 issue.","","## Re-run","","`python scripts\\evaluate_step6.py` runs local retrieval and patient-boundary checks only. `python scripts\\evaluate_step6.py --live-answers` additionally tests one grounded topic answer and one no-answer question, sending their questions and retrieved passages to Groq; external processing must be enabled. Results are written under `evaluation/results/`.",""]
    checkpoint=ROOT/"data/processed/step6_checkpoint.md"; checkpoint.parent.mkdir(parents=True,exist_ok=True); checkpoint.write_text("\n".join(md),encoding="utf-8")
    print(f"Hit@6={hit_rate:.3f} (target {threshold['minimum_hit_at_6']:.2f}); MRR@6={mrr:.3f} (target {threshold['minimum_mrr_at_6']:.2f}); retrieval={'PASS' if retrieval_pass else 'FAIL'}")
    print(f"Patient/no-evidence safety cases={'PASS' if safe else 'FAIL/REVIEW'}; live answer citations={'PASS' if automated_answer_pass else ('NOT RUN' if not args.live_answers else 'FAIL/REVIEW')}")
    print(f"Detailed results: {report}\nCheckpoint: {checkpoint}")
    return 0 if retrieval_pass and safe else 1

if __name__=="__main__": raise SystemExit(main())
