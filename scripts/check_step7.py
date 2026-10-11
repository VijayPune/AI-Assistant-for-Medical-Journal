"""Check that the Step 7 demonstration package is complete and report open gates."""
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def main() -> int:
    checks=[]
    def add(name,ok,detail): checks.append((name,bool(ok),detail))
    required={
        "demonstration question set":ROOT/"evaluation/demo_questions.json",
        "reproducible demonstration script":ROOT/"demo/Demonstration_Script.md",
        "Step 6 automated checkpoint":ROOT/"data/processed/step6_checkpoint.md",
        "Step 6 detailed evaluation":ROOT/"evaluation/results/step6_evaluation.json",
        "Step 6 answer-review file":ROOT/"evaluation/results/step6_answer_review.csv",
        "Step 7 manual PDF":ROOT/"manuals/Step7.pdf",
    }
    for name,path in required.items(): add(f"{name} exists",path.is_file(),str(path.relative_to(ROOT)))
    demo=json.loads(required["demonstration question set"].read_text(encoding="utf-8")) if required["demonstration question set"].is_file() else {}
    questions=demo.get("questions",[])
    add("Five to seven demo examples are catalogued",5<=len(questions)<=7,f"{len(questions)} example questions")
    add("Demo set covers grounded, no-evidence and patient-specific paths",any(q.get("expected_article_id") for q in questions) and any("decline" in q.get("purpose","") for q in questions) and any("boundary" in q.get("purpose","") for q in questions),"All three intended demonstration paths present")
    eval_path=required["Step 6 detailed evaluation"]
    evaluation=json.loads(eval_path.read_text(encoding="utf-8")) if eval_path.is_file() else {}
    add("Step 6 retrieval target met",evaluation.get("retrieval",{}).get("target_pass") is True,f"Hit@6={evaluation.get('retrieval',{}).get('hit_at_6','unknown')}; MRR={evaluation.get('retrieval',{}).get('mrr_at_6','unknown')}")
    add("Step 6 citation and abstention smoke checks passed",evaluation.get("live_answers_citation_and_abstention_pass") is True,str(evaluation.get("live_answer_statuses",{})))
    step5=ROOT/"data/processed/step5_checkpoint.md"
    step5_text=step5.read_text(encoding="utf-8") if step5.is_file() else ""
    add("Step 5 UI checkpoint passed", "STEP 5 APPLICATION CHECKS PASSED" in step5_text and "0 failed" in step5_text, "Latest Streamlit smoke-check checkpoint")
    manual=ROOT/"manuals/Step7.pdf"
    if manual.is_file():
        try:
            from pypdf import PdfReader
            pages=PdfReader(str(manual)).pages
            manual_ok=len(pages)>0 and all((page.extract_text() or "").strip() for page in pages)
            manual_detail=f"{len(pages)} pages; text present"
        except Exception as exc:
            manual_ok=False; manual_detail=f"PDF inspection failed: {type(exc).__name__}"
        add("Step 7 manual PDF is readable",manual_ok,manual_detail)
    else:
        add("Step 7 manual PDF is readable",False,"PDF missing")
    passed=sum(ok for _,ok,_ in checks); failed=len(checks)-passed
    access_status="unconfirmed"
    try:
        import tomllib
        cfg=tomllib.loads((ROOT/"config/journals/indian_pediatrics.toml").read_text(encoding="utf-8"))
        access_status=cfg.get("access",{}).get("review_status","unconfirmed")
    except Exception: pass
    review_file=ROOT/"evaluation/results/step6_answer_review.csv"
    human_pending="PENDING" in review_file.read_text(encoding="utf-8-sig") if review_file.is_file() else True
    demo_ready=failed==0
    status="DEMO PACKAGE READY WITH DISCLOSURES" if demo_ready else "DEMO PACKAGE INCOMPLETE"
    lines=["# Step 7 checkpoint: Demonstration","",f"**Status:** {status}",f"**Automated checks:** {passed} passed; {failed} failed.","","| Check | Result | Detail |","|---|---:|---|"]
    lines += [f"| {n} | {'PASS' if ok else 'FAIL'} | {d.replace('|','/')} |" for n,ok,d in checks]
    lines += ["","## Readiness decision","",f"The demonstration package is {'ready' if demo_ready else 'not ready'} for a controlled editor walkthrough, provided the disclosures in `demo/Demonstration_Script.md` are followed.","","- **Product/clinical-readiness decision:** NOT DECLARED. This POC is not clinically validated.",f"- **Expert review of generated claims and relevance labels:** {'PENDING' if human_pending else 'review file has no PENDING markers; verify recorded decisions'}.",f"- **Publisher full-text access/reuse confirmation:** {access_status} in journal configuration.","- **Corpus scope:** one issue, January 2025, Volume 62, Issue 1.","- **External processing:** when enabled, demo questions and retrieved passages are sent to Groq; source PDFs and embeddings stay local.","","A demo-package pass means the materials and automated checks are ready for a controlled demonstration. It does not grant rights to redistribute content, validate medical safety, or approve deployment.",""]
    checkpoint=ROOT/"data/processed/step7_checkpoint.md"; checkpoint.parent.mkdir(parents=True,exist_ok=True); checkpoint.write_text("\n".join(lines),encoding="utf-8")
    report=ROOT/"evaluation/results/step7_poc_test_report.md"; report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text("# Step 7 | POC Test Report\n\nThis report summarizes the automated readiness checks for the demonstration package. It is not a clinical-validation report.\n\n"+"\n".join(lines[2:]),encoding="utf-8")
    for n,ok,d in checks: print(f"{'PASS' if ok else 'FAIL'}: {n} - {d}")
    print(f"\n{status}\nCheckpoint: {checkpoint}\nTest report: {report}")
    return 0 if demo_ready else 1

if __name__=="__main__": raise SystemExit(main())
