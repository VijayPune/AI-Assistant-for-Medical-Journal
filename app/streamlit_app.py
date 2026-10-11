"""Reusable local Streamlit interface for the journal assistant POC."""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from journal_assistant.configuration import load_journal_config
from journal_assistant.rag.answering import answer_question, is_patient_specific
from journal_assistant.rag.env import external_text_processing_allowed
from journal_assistant.rag.providers.fastembed_provider import FastEmbedProvider
from journal_assistant.rag.providers.groq_provider import GroqProvider
from journal_assistant.rag.providers.base import ProviderNotReady
from journal_assistant.rag.retrieval import search
from journal_assistant.rag.store import SQLiteHybridStore

st.set_page_config(page_title="Journal Literature Assistant", page_icon="📚", layout="wide")

@st.cache_data
def load_metadata(metadata_file: str) -> list[dict]:
    path = Path(metadata_file)
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))

@st.cache_resource
def load_embedder(model_name: str, cache_directory: str) -> FastEmbedProvider:
    return FastEmbedProvider(model_name=model_name, cache_directory=Path(cache_directory))

def _group_by_article(evidence: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for item in evidence:
        grouped[item["article_id"]].append(item)
    return grouped

def _source_card(item: dict, raw_files_directory: Path) -> None:
    page = item.get("page_start") or "unmapped"
    authors = item.get("authors") or "Author not verified in metadata"
    st.markdown(f"**[{item['source_label']}] {item['title']}**")
    st.caption(f"{authors} · {item['year']} · {item['section']} · Vol. {item['volume']}, Issue {item['issue_number']} · journal page {page} · PDF page {item['physical_page']}")
    st.write(item["text"])
    left, right = st.columns([1, 1])
    with left:
        if item.get("source_url", "").startswith("https://"):
            st.link_button("Open publisher issue", item["source_url"], key=f"issue-{item['chunk_id']}")
    source_path = raw_files_directory / item["source_filename"]
    if source_path.is_file():
        with right:
            st.download_button("Download source PDF", source_path.read_bytes(), file_name=source_path.name,
                               mime="application/pdf", key=f"pdf-{item['chunk_id']}")
    st.caption(f"Source file: {item['source_filename']} · SHA-256: {item['source_sha256'][:16]}…")

def main() -> None:
    journal = load_journal_config()
    records = load_metadata(str(journal.metadata_file))
    sections = sorted({row["section"] for row in records if row.get("section")})
    years = sorted({int(row["year"]) for row in records if row.get("year", "").isdigit()})

    st.title(f"{journal.display_name} Literature Assistant")
    st.subheader("Journal evidence discovery · proof of concept")
    st.caption(journal.corpus_title)
    st.warning("Research literature discovery only. This POC does not provide diagnosis or treatment advice.")
    with st.expander("How this prototype handles evidence"):
        st.write("Search ranks passages from the configured journal issue. Generated summaries cite retrieved source labels and should be checked against the article. This prototype is not a substitute for clinical judgment.")

    db_path = ROOT / "data/indexes/journal_assistant.sqlite3"
    if not db_path.is_file():
        st.error("The local search index is not built yet. From the Project folder, run the Step 4 chunk and index commands shown in README.md.")
        st.stop()

    with st.sidebar:
        st.header("Search filters")
        selected_types = st.multiselect("Article type / section", sections, key="article_types")
        selected_year = st.selectbox("Publication year", ["Any"] + [str(x) for x in years], key="year_filter")
        author_filter = st.text_input("Author contains", key="author_filter", placeholder="e.g., Radhakrishnan")
        top_k = st.slider("Evidence passages", min_value=1, max_value=10, value=6, key="top_k")
        st.divider()
        st.caption("Search mode: local hybrid lexical + semantic retrieval")
        st.caption("Embeddings: local BGE model")
        st.caption("Answer synthesis: Groq when evidence is found and consent is enabled")
        st.caption(f"External answer processing: {'enabled' if external_text_processing_allowed() else 'off'}")

    demo_path = ROOT / "evaluation/demo_questions.json"
    examples = []
    if demo_path.is_file():
        demo_data = json.loads(demo_path.read_text(encoding="utf-8"))
        if demo_data.get("journal_id") == journal.journal_id:
            examples = [entry["question"] for entry in demo_data.get("questions", [])]
    if examples:
        selected_example = st.selectbox("Try a demonstration question", ["Choose an example"] + examples, key="demo_question")
        if st.button("Use selected example", key="use_demo_question") and selected_example != "Choose an example":
            st.session_state["question"] = selected_example

    question = st.text_input("What topic or question would you like to search?", key="question",
                             placeholder="For example: ketorolac morphine sickle cell")
    if external_text_processing_allowed():
        st.info("External answers are enabled: pressing Search sends your question and retrieved passages to Groq. Query embeddings are generated locally.")
    else:
        st.caption("External answer processing is off. Search and query embeddings stay local; no Groq answer will be requested.")
    search_clicked = st.button("Search journal", type="primary", key="search_button")

    if search_clicked:
        if not question.strip():
            st.session_state["step5_evidence"] = []
            st.session_state["step5_answer"] = "Enter a topic or question to search the corpus."
            st.session_state["step5_status"] = "empty_query"
        else:
            filters: dict = {}
            if selected_types:
                filters["section"] = selected_types
            if selected_year != "Any":
                filters["year"] = int(selected_year)
            if author_filter.strip():
                filters["author"] = author_filter.strip()
            try:
                store = SQLiteHybridStore(db_path)
                try:
                    cfg_path = ROOT / "config/rag.toml"
                    import tomllib
                    rag_cfg = tomllib.loads(cfg_path.read_text(encoding="utf-8"))
                    counts = store.counts()
                    query_vector = None
                    if counts["chunks"] and counts["vectors"] == counts["chunks"]:
                        embedding_cfg = rag_cfg["embedding"]
                        embedder = load_embedder(embedding_cfg["model"], str(ROOT / embedding_cfg["cache_directory"]))
                        query_vector = embedder.embed_query(question)
                    evidence = search(store, question, embedding=query_vector, top_k=top_k, filters=filters,
                                      allowed_roles=set(rag_cfg["retrieval"]["default_allowed_roles"]),
                                      minimum_semantic_similarity=rag_cfg["retrieval"].get("minimum_semantic_similarity"))
                finally:
                    store.close()
                provider = None
                if evidence and external_text_processing_allowed() and not is_patient_specific(question):
                    try:
                        provider = GroqProvider(answer_model=rag_cfg["generation"]["model"])
                    except ProviderNotReady:
                        provider = None
                try:
                    result = answer_question(question, evidence, provider=provider)
                except Exception as exc:
                    result = answer_question(question, evidence, provider=None)
                    result.answer = "Local search succeeded, but Groq answer generation could not be completed. Review the retrieved source passages."
                    result.status = "generation_error"
                st.session_state["step5_evidence"] = result.evidence
                st.session_state["step5_answer"] = result.answer
                st.session_state["step5_status"] = result.status
            except Exception as exc:
                st.session_state["step5_evidence"] = []
                st.session_state["step5_answer"] = f"Local search could not be completed: {exc}"
                st.session_state["step5_status"] = "search_error"

    evidence = st.session_state.get("step5_evidence", [])
    answer = st.session_state.get("step5_answer")
    status = st.session_state.get("step5_status")

    st.header("Answer")
    if answer:
        if status == "answered":
            st.success(answer)
        elif status == "no_evidence":
            st.info(answer)
        elif status == "patient_specific_boundary":
            st.warning(answer)
        elif status == "generation_not_configured":
            st.info("Search matches were found. " + answer)
        else:
            st.info(answer)
    else:
        st.caption("Enter a query and select Search journal. Retrieved passages stay linked to their journal sources; answer synthesis uses the setting shown above.")

    if evidence:
        grouped = _group_by_article(evidence)
        st.header("Sources")
        st.caption(f"{len(evidence)} passages from {len(grouped)} article(s). Each passage links to its article and source page.")
        for item in evidence:
            with st.expander(f"[{item['source_label']}] {item['title']} · {item['section']} · page {item.get('page_start') or 'unmapped'}"):
                _source_card(item, journal.raw_files_directory)

        st.header("Compare articles")
        article_titles = {aid: passages[0]["title"] for aid, passages in grouped.items()}
        selected_articles = st.multiselect("Choose two or more retrieved articles", list(article_titles),
            format_func=lambda aid: article_titles[aid], max_selections=3, key="compare_articles")
        if len(selected_articles) >= 2:
            columns = st.columns(min(len(selected_articles), 3))
            for index, article_id in enumerate(selected_articles[:3]):
                with columns[index]:
                    passages = grouped[article_id]
                    first = passages[0]
                    st.markdown(f"#### {first['title']}")
                    st.caption(f"{first['section']} · {first['year']} · {first.get('authors') or 'author not verified'}")
                    st.caption(f"Article ID: {article_id}")
                    for passage in passages:
                        st.markdown(f"**[{passage['source_label']}] page {passage.get('page_start') or passage['physical_page']}**")
                        st.write(passage["text"])
        elif selected_articles:
            st.caption("Select at least two retrieved articles to compare their metadata and supporting passages side by side.")
    elif status in {"no_evidence", "patient_specific_boundary"}:
        st.header("Sources")
        st.caption("No source passages are shown for this result.")

    with st.expander("About this proof of concept"):
        st.write("The current corpus and index are configured for one journal issue. Document and query embeddings run locally. When external processing is enabled, the question and selected text passages are sent to Groq for answer generation; source PDFs remain on this computer. Results are research literature, not personalized medical advice.")
        st.caption(f"Corpus access review status in journal configuration: {journal.access_review_status}. This POC is for a controlled demonstration; do not redistribute source PDFs.")

if __name__ == "__main__":
    main()
