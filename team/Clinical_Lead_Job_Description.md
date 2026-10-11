# Clinical Lead (Pediatrics and Evidence Quality)

## Part-time Clinical Adviser - Medical Journal Literature Assistant POC

### 1. Role at a glance

| Item | Description |
|---|---|
| Working title | Clinical Lead (Pediatrics and Evidence Quality) |
| Engagement | Paid, part-time adviser or consultant for the POC; scope and fee agreed before work begins |
| Project | Reusable AI literature-discovery assistant, initially configured for one issue of *Indian Pediatrics* |
| Initial corpus | January 2025, Volume 62, Issue 1; limited set of locally processed article PDFs |
| Main purpose | Define and independently review clinical relevance, answer grounding, citations, safety boundaries, and demonstration claims |
| Reports to | Product Owner / Project Lead |
| Coding requirement | None |

### 2. About the project

The project is a proof of concept for helping pediatricians, residents, researchers, educators, and students find and inspect articles in a journal archive. It combines metadata, local lexical and semantic retrieval, source passages, and optional AI-generated summaries that cite retrieved passages.

The intended POC is a **journal literature-discovery and summarization tool**. It is not intended to diagnose a child, recommend tests or treatment, calculate a dose, triage a patient, or replace clinical judgment. It currently covers one journal issue and has not been clinically validated.

### 3. Why this role is important

The developer can implement indexing, retrieval, interfaces, and automated checks, but should not be the sole judge of whether a medical statement is accurate, appropriately qualified, or safe to show. A pediatrician should help set the clinical evaluation criteria, independently review representative results, and explain the limits in language that journal editors and clinicians recognize.

For this POC, the pediatrician can initially serve as a paid adviser rather than a full-time employee or formal Medical Director. Their appointment does not by itself establish regulatory compliance, publication rights, or clinical validation.

### 4. Responsibilities

#### 4.1 Define intended use and clinical boundaries

- Review the product's intended users, tasks, and explicit non-goals.
- Help define examples of permitted literature-search questions versus patient-specific requests that must be refused or redirected.
- Review the visible safety language so that it is accurate, understandable, and not falsely reassuring.
- Identify clinically foreseeable misuse, including treating a paper summary as an individualized recommendation.
- Advise when a proposed feature changes the intended use enough to require a new safety and regulatory assessment.

#### 4.2 Review the corpus and medical metadata

- Check that article title, type/category, author, publication date, volume, issue, and page information are represented correctly for reviewed examples.
- Confirm that article types are not conflated: for example, original research, systematic review, guideline synopsis, commentary, correspondence, case report, and secondary-source clipping.
- Identify when a result is from a commentary or secondary source rather than primary clinical evidence.
- Review extracted passages for clinically meaningful missing context, broken tables, negation errors, unit errors, and article/page mismatches.
- Flag content that should not be used as clinical evidence or should be visibly labeled with its editorial role.

#### 4.3 Build and approve the clinical evaluation set

- Review the existing Golden Test Set and confirm whether each expected article is genuinely relevant to its question.
- Add realistic, neutral questions across topics and article types, including author/issue lookup, comparisons, temporal questions, ambiguous queries, and questions outside the corpus.
- Create a reference record for each question: intended relevant article(s), passage/page supporting the answer, essential facts, and acceptable uncertainty.
- Include negative cases where the issue has no answer, conflicting evidence, insufficient detail, or only commentary/secondary-source material.
- Keep patient-specific prompts synthetic and non-identifiable; do not use real patient details in demo or evaluation prompts.

#### 4.4 Review generated answers and citation grounding

For a representative sample of outputs, independently assess:

- **Factual accuracy:** Does the summary accurately state the passage's findings?
- **Support:** Does each claim have a cited passage that actually supports it?
- **Completeness:** Has an important qualification, comparator, outcome, or limitation been omitted?
- **Study interpretation:** Are design, population, intervention/exposure, comparator, and outcome described correctly?
- **Evidence type:** Does the answer distinguish a trial, observational study, review, guideline, commentary, or case report?
- **Uncertainty:** Are limitations, conflicting findings, and insufficient evidence stated honestly?
- **Citation integrity:** Does each source label resolve to the correct article and page, and is the cited text relevant to the claim?
- **Clinical safety:** Has the response drifted into patient-specific diagnosis, treatment, dosing, or reassurance?
- **Misleading tone:** Does fluent wording make a preliminary or weak finding sound established or universal?

The adviser should record the exact answer, source ID/page, review decision, and a short rationale. A citation that exists is not automatically evidence that a claim is supported.

#### 4.5 Set severity and escalation rules

Work with the Product Owner to agree a simple defect scale. For example:

| Severity | Example | Suggested action |
|---|---|---|
| Critical | Patient-specific treatment or dose advice; dangerous reversal of a finding; fabricated clinical result | Block the demo/release path until fixed and retested |
| Major | Unsupported or materially incorrect claim; citation points to unrelated evidence; study design is misrepresented | Fix and rerun affected evaluation cases before demonstrating the affected workflow |
| Moderate | Important limitation or context omitted; article type/page metadata misleading | Correct, document, and retest the affected behavior |
| Minor | Wording, formatting, or non-clinical display issue without misleading meaning | Log and prioritize with the Product Owner |

The pediatrician should have authority to recommend pausing a clinical-content demonstration when a critical or major issue is found. The Product Owner remains responsible for implementation and project decisions and must document how high-severity issues are resolved.

#### 4.6 Review the demonstration and communicate with editors

- Review the demonstration questions, selected results, and spoken claims before an editor walkthrough.
- Help present the product in journal and clinical-research language: corpus scope, evidence types, provenance, retrieval, summaries, citation checks, limitations, and human review.
- Explain what the prototype does and does not demonstrate without implying endorsement by the journal or medical institution.
- Help prepare questions for editors about article categories, archive structure, reader workflows, corrections/updates, metadata, and editorial expectations.
- Route permission, licensing, confidentiality, and publication-rights questions to the journal/publisher and appropriate legal or institutional contact; do not decide rights alone.
- Disclose professional, financial, institutional, and editorial conflicts of interest.

#### 4.7 Support retesting and ongoing quality review

- Review high-severity defects after fixes and confirm that the original failure case has been rerun.
- Advise which evaluation cases should be repeated when the corpus, PDF extraction, metadata, retrieval settings, prompt, or model changes.
- Help define a periodic review plan before any expansion beyond the POC issue.
- Identify clinical/editorial changes that could make older article content misleading without publication-date context.

### 5. Expected deliverables

The initial engagement should produce the following project records:

1. **Clinical Intended-Use and Boundary Note** - intended users, supported literature tasks, prohibited patient-specific use, and escalation wording.
2. **Corpus Review Log** - reviewed article metadata, article-type concerns, extraction/page issues, and items to exclude or label.
3. **Clinician-Reviewed Golden Test Set** - questions, expected article IDs/pages, answer-essential facts, negative cases, and reviewer rationale.
4. **Answer and Citation Evaluation Rubric** - scoring definitions for accuracy, grounding, citation, evidence-type interpretation, uncertainty, and safety.
5. **Clinical Evaluation Report** - per-question outcomes, severity-ranked defects, counts/denominators, examples, and limitations.
6. **Retest and Closure Record** - defects fixed, cases rerun, residual risks, and unresolved items.
7. **Editor Demonstration Review** - approved talking points, demo cases to avoid, and disclosures about scope and limitations.
8. **Clinical Adviser Sign-off or Non-sign-off Memo** - a clear statement of what was reviewed, the review sample, findings, and what remains outside the review.

The adviser must not be asked to sign a blanket statement that the product is “clinically validated” based on a one-issue POC or a small set of questions.

### 6. Suggested initial work plan

The exact time commitment depends on availability and the volume of outputs. A practical starting engagement is a short, paid evaluation sprint over approximately 4-6 weeks, with a planning assumption of 2-4 hours per week plus review workshops. Confirm the actual effort with the candidate before agreeing to the scope.

| Milestone | Adviser activity | Output |
|---|---|---|
| 1. Orientation | Review intended use, current UI, corpus scope, existing Step 6 results, and data flow | Boundary comments and initial risk list |
| 2. Corpus/context review | Inspect representative article types and selected extracted passages/pages | Corpus review log |
| 3. Evaluation design | Review and expand questions; write expected sources and answer-essential facts | Clinician-reviewed Golden Test Set and rubric |
| 4. Output review | Independently rate the selected generated answers and safety cases | Question-level clinical evaluation log |
| 5. Defect review | Discuss severity, fixes, and retesting evidence | Retest and closure record |
| 6. Demo preparation | Review the script, output examples, wording, and editor questions | Demonstration review and sign-off/non-sign-off memo |

### 7. Candidate qualifications

#### Required

- Recognized medical qualification and postgraduate specialty training in Pediatrics (or an equivalent pediatric specialist qualification applicable to the candidate's jurisdiction).
- Meaningful clinical experience caring for children; for this project, several years of post-specialty experience is preferred.
- Ability to read pediatric clinical research critically and explain findings in plain language.
- Familiarity with common study designs and limitations, including randomized trials, observational studies, systematic reviews, guidelines, and case reports.
- Willingness to record uncertainty, disagree with the product team, and identify unsafe or unsupported claims.
- Strong written and verbal communication with clinicians, researchers, and journal editors.
- Willingness to disclose conflicts of interest and respect confidentiality and source-use restrictions.

#### Strongly preferred

- Experience as a journal peer reviewer, associate editor, editorial-board member, or author of pediatric research.
- Training or practical experience in evidence-based medicine, epidemiology, biostatistics, systematic reviews, or clinical research methods.
- Experience teaching residents, medical students, or researchers how to interpret evidence.
- Familiarity with Indian pediatric practice, research settings, and the local relevance of pediatric literature.
- Prior involvement in digital health, clinical informatics, AI evaluation, or responsible innovation (helpful but not required; coding is not required).

### 8. Independence, conflicts, and working relationship

- Engage the adviser under a written scope, fee, confidentiality terms, conflict disclosure, and attribution agreement.
- Pay for review time; do not rely on informal unpaid sign-off for a high-stakes evaluation role.
- Agree whether their name and qualifications may appear in a pitch, slide, or report. Do not imply journal, hospital, university, or professional-body endorsement without written permission.
- Keep reviewer decisions and changes auditable. Preserve disagreements rather than editing them out.
- The adviser reviews clinical content and evidence quality; the developer owns engineering and operational controls; the Product Owner owns scope and business decisions; the publisher/editor/legal adviser determines source permissions and editorial approval.

### 9. Success measures for the engagement

- Each reviewed question has an expected source and documented review outcome.
- Every generated claim selected for review is checked against its cited passage, not only its citation syntax.
- Critical and major errors are either fixed and retested or explicitly block the relevant demonstration claim.
- Negative and patient-specific scenarios are evaluated and handled conservatively.
- The editor walkthrough clearly states corpus scope, source provenance, external data flow, known limitations, and the review status.
- No one presents this limited POC as clinical validation, treatment advice, complete archive coverage, or journal endorsement.

### 10. Important boundaries of the role

This adviser does not, solely by accepting this role:

- Certify the product as clinically validated or safe for patient care.
- Provide legal advice or confirm copyright, licensing, or publisher reuse rights.
- Decide whether the final product is a regulated medical device or determine its regulatory pathway.
- Guarantee that an LLM will not make errors or replace independent evaluation.
- Approve deployment, security, API key management, privacy compliance, or commercial claims without the relevant expertise and evidence.

If the intended use later moves from journal discovery toward diagnosis, patient-specific treatment recommendations, triage, or decision support, pause feature expansion and obtain a separate regulatory and clinical-safety assessment for the relevant market. In India, CDSCO publishes guidance relating to medical-device software; whether a particular product falls within a regulated category depends on the actual intended use and applicable rules and should be reviewed with qualified regulatory counsel.

### 11. Suggested interview questions

1. How would you decide whether a generated summary accurately represents a clinical study?
2. How would you evaluate whether each citation truly supports the sentence that cites it?
3. What kinds of pediatric literature questions should this POC refuse to answer?
4. How would you distinguish an original study from a commentary or guideline synopsis in a user-facing summary?
5. If the answer is plausible but the article passage does not support it, how would you document and prioritize the issue?
6. What would you need to see before allowing a controlled demonstration to journal editors?
7. How would you explain the system's limitations to editors without either overselling it or dismissing its potential?
8. What conflicts, affiliations, or source permissions should be disclosed before joining this project?
