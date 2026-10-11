"""Create the Step 2 catalogue and file manifest from the Jan 2025 POC set.

This records bibliographic and acquisition status only; PDF text extraction and
indexing belong to later roadmap steps.
"""
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "data" / "metadata"
RAW = Path("data/raw/2025_Jan")
ISSUE_URL = "https://indianpediatrics.net/articles.php?issue=766"

# Titles and issue sections are catalogued from the publisher's issue contents.
# Unknown author/DOI fields are intentionally blank rather than guessed.
items = [
    ("001", "For Children, With Colleagues, Towards a Healthier Country", "President's Page", "9", "9", "9.pdf", "present", "clinical_context", "Vasant Khalatkar"),
    ("002", "Redefining Ten; Reducing the Invisible Pain of Sickle Cell Disease", "Invited Commentary", "11", "12", "11.pdf", "present", "clinical_context", "Nita Radhakrishnan"),
    ("003", "NRP Training for Parents – Is it Desirable?", "Invited Commentary", "13", "14", "13.pdf", "present", "clinical_context", "S Sitaraman"),
    ("004", "Ketorolac vs Morphine for Severe Vaso-Occlusive Crisis in Sickle Cell Disease: An Open-Label Randomized Controlled Trial (KISS Study)", "Original Article", "15", "19", "15.pdf", "present", "clinical_evidence", ""),
    ("005", "Feasibility of Implementing Resuscitation Training for Parents of At-risk Infants at Discharge (FIRST AID)", "Original Article", "21", "26", "21.pdf", "present", "clinical_evidence", ""),
    ("006", "Telemedicine in Pediatric Diabetes Care: The Way Forward?", "Original Article", "27", "30", "27.pdf", "present", "clinical_evidence", ""),
    ("007", "Re-evaluating Presumptive Treatment with Doxycycline/Azithromycin in Children With Acute Febrile Illness in a Scrub Typhus Endemic Region: A Cross-Sectional Study", "Original Article", "31", "36", "31.pdf", "present", "clinical_evidence", ""),
    ("008", "Association of Specific Dietary Fatty Acids with Asthma in Urban School Children and Adolescents: Inferences from a Cross-Sectional Multicentric Study From India", "Original Article", "37", "43", "37.pdf", "present", "clinical_evidence", ""),
    ("009", "Clinical and Laboratory Characteristics and Comorbidities in Asthma Endotypes in Children", "Original Article", "44", "48", "44.pdf", "present", "clinical_evidence", ""),
    ("010", "Serosurvey For Measles, Mumps and Rubella in Children and Adolescents with Chronic Kidney Disease", "Original Article", "49", "52", "49.pdf", "present", "clinical_evidence", ""),
    ("011", "Feed Intolerance With Short Term Use of Commercial Pasteurized Donor Human Milk Versus Preterm Formula in Addition to Mother's Milk: A Retrospective Analytical Study", "Research Letter", "53", "55", "53.pdf", "present", "clinical_evidence", ""),
    ("012", "Efficacy and Safety of Intravenous Immunoglobulin (IVIg) in Acute Viral Myocarditis in Children: A Systematic Review of Randomized Controlled Trials", "Systematic Review", "56", "62", "56.pdf", "present", "clinical_evidence", "PDF also contains unpaginated supplementary material"),
    ("013", "Professional Identity Formation in Indian Undergraduate Medical Students", "Medical Education", "63", "70", "63.pdf", "present", "nonclinical_context", ""),
    ("014", "ESPGHAN Guideline Synopsis: Eosinophilic Esophagitis", "Update", "71", "74", "71.pdf", "present", "clinical_evidence", ""),
    ("015", "Malnutrition in India: Recovery Over Five Decades", "Reminiscences", "75", "77", "75.pdf", "present", "clinical_context", ""),
    ("016", "Acute Lymphoblastic Leukemia in Children with Thalassemia Exposed to Thalidomide", "Clinical Case Letters", "78", "80", "78.pdf", "present", "clinical_evidence", ""),
    ("017", "Concerns Regarding the Study Design in Assessing Autonomic Dysfunction in Nutcracker Syndrome", "Correspondence", "81", "81", "", "scoped_out", "clinical_context", "PDF not supplied; intentionally excluded from this POC corpus by user decision"),
    ("018", "Glycerol-3-Phosphate Dehydrogenase 1 Deficiency: A Rare Cause of Fatty Liver Disease in Children", "Correspondence", "82", "82", "", "scoped_out", "clinical_context", "PDF not supplied; intentionally excluded from this POC corpus by user decision"),
    ("019", "Clippings: Neonatology – SimCapture app video performance assessment versus real-time instructor-based evaluation in neonatal resuscitation", "Clippings", "", "", "83.pdf", "present", "secondary_source", "Secondary summary; source citation must be retained and ranked below primary papers"),
]

article_fields = ["article_id", "title", "authors", "journal", "publication_date", "year", "month", "volume", "issue_number", "issue_id", "section", "page_start", "page_end", "doi", "publisher_issue_url", "local_filename", "acquisition_status", "content_role", "access_basis", "external_demo_permission", "notes"]
articles = []
for code, title, section, start, end, filename, status, role, notes in items:
    articles.append({
        "article_id": f"IP-2025-V62-I01-{code}", "title": title, "authors": {"001": "Vasant Khalatkar", "002": "Nita Radhakrishnan", "003": "S Sitaraman"}.get(code, ""),
        "journal": "Indian Pediatrics", "publication_date": "2025-01-15", "year": "2025", "month": "01", "volume": "62", "issue_number": "1", "issue_id": "766",
        "section": section, "page_start": start, "page_end": end, "doi": "", "publisher_issue_url": ISSUE_URL, "local_filename": filename,
        "acquisition_status": status, "content_role": role, "access_basis": "User-provided local copy for internal POC; user states they have access",
        "external_demo_permission": "pending_editor_confirmation", "notes": notes,
    })

file_fields = ["filename", "relative_path", "article_id", "content_role", "section_or_file_role", "pdf_bytes", "physical_pages", "text_extractable", "include_in_clinical_retrieval", "duplicate_or_exclusion_note", "access_basis"]
file_to_item = {it[5]: it for it in items if it[5]}
files = []
for pdf in sorted((ROOT / RAW).glob("*.pdf"), key=lambda p: p.name.lower()):
    it = file_to_item.get(pdf.name)
    if pdf.name == "14.pdf":
        aid, role, section, include, note = "IP-2025-V62-I01-003", "administrative_duplicate", "Duplicate commentary ending plus access notice", "no", "Do not ingest; duplicated ending from 13.pdf with administrative notice appended"
    elif pdf.name == "84.pdf":
        aid, role, section, include, note = "", "administrative_news", "News in Brief", "no", "Catalogue only; not clinical evidence"
    elif it:
        aid, role, section, include, note = f"IP-2025-V62-I01-{it[0]}", it[7], it[2], ("yes" if it[7] in {"clinical_evidence", "clinical_context"} else "limited" if it[7] == "secondary_source" else "no"), it[8]
    else:
        aid, role, section, include, note = "", "unclassified", "Unclassified file", "no", "Review classification before ingest"
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(pdf), strict=False)
        pages = len(reader.pages)
        extractable = "yes" if any((page.extract_text() or "").strip() for page in reader.pages) else "no"
    except Exception:
        pages, extractable = "", "not_checked"
    files.append({"filename": pdf.name, "relative_path": str(pdf.relative_to(ROOT)).replace("\\", "/"), "article_id": aid, "content_role": role, "section_or_file_role": section, "pdf_bytes": str(pdf.stat().st_size), "physical_pages": str(pages), "text_extractable": extractable, "include_in_clinical_retrieval": include, "duplicate_or_exclusion_note": note, "access_basis": "User-provided local copy for internal POC"})

META.mkdir(parents=True, exist_ok=True)
for name, fields, rows in (("article_metadata.csv", article_fields, articles), ("corpus_file_manifest.csv", file_fields, files)):
    with (META / name).open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
print(f"Wrote {len(articles)} catalogue records and {len(files)} supplied-file manifest rows to {META}")
