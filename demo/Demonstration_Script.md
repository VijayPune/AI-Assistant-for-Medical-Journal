# Step 7 | Demonstration Script

## Purpose and audience

This 10-15 minute walkthrough introduces the Indian Pediatrics literature-search proof of concept to journal editors. It demonstrates how a reader can search a limited issue, inspect source passages, and see when the assistant refuses to answer. It is a concept demonstration, not a clinical product launch or clinical validation.

## Before the meeting

1. Use the project folder `AI Asst for IP\Project` on the prepared development computer.
2. Confirm the January 2025, Volume 62, Issue 1 corpus is installed and the local index is current.
3. Run `python scripts\check_step7.py`; review the checkpoint and disclose any failed or pending item.
4. Use `python scripts\evaluate_step6.py` for local checks. Do not run `--live-answers` at the venue unless the external-processing notice is understood and the organizer has approved sending the questions and retrieved passages to Groq.
5. Ensure the screen displays the external answer processing notice. Keep `.env` private; never project or share it.
6. Use a clean browser window and close unrelated files and credentials.

## Opening statement

"This is a small proof of concept that helps find and inspect literature within one configured journal issue. It is not a diagnostic or treatment tool. The current dataset is January 2025, Volume 62, Issue 1. Search and embeddings run locally. If the visible external-processing setting is enabled, a question and the passages retrieved for it are sent to Groq to draft a cited literature summary."

## Walkthrough (seven examples)

| No. | Demonstration question | What to show |
|---|---|---|
| 1 | What did the KISS study compare for severe sickle-cell pain? | Select the example, search, read the cited short answer, expand [S1], and point to article title and page provenance. |
| 2 | What evidence is discussed about intravenous immunoglobulin for acute viral myocarditis in children? | Show retrieval of a systematic review and its article-type label. Inspect passages before making any claim about results. |
| 3 | What does the issue report about dietary fatty acids and asthma in Indian school children? | Show a topic search that does not require an exact article title. |
| 4 | What comparison was made between donor human milk and preterm formula for feed intolerance? | Show another original-research article and inspect its retrieved text. |
| 5 | What does the ESPGHAN guideline synopsis cover? | Show a guideline synopsis, then use the article-type filter and compare source metadata if helpful. |
| 6 | What evidence does this issue contain about pediatric brain tumors caused by moonlight exposure? | Show the assistant's no-evidence response despite broad candidate passages. Emphasize that it did not invent a finding. |
| 7 | What should I give my child for a fever tonight? | Show the patient-specific boundary. Do not invite anyone to enter a real patient case. |

## Closing statement

"The POC demonstrates a possible literature-discovery workflow. It currently covers one issue and a small set of processed article files. Automated checks measure retrieval and verify that displayed source IDs came from retrieved passages, but an expert still needs to review whether each claim is truly supported. Publisher permissions and reuse conditions must be confirmed before broader deployment or distribution."

## Troubleshooting

- If no source index is found, stop and rebuild it using the Step 4 commands in `README.md`.
- If the local search fails, use the Step 7 checkpoint and do not improvise a claim from a partial result.
- If Groq is unavailable or the consent switch is off, demonstrate local search and source cards; explain that generated summaries are disabled.
- If a citation is missing or an answer status is a safe failure, show the source passages directly and record the issue for the evaluation log.
- If a question returns unrelated sources, demonstrate the no-evidence case and record the retrieval weakness; do not change the question to force a favorable-looking result.

## Materials and boundaries

- Select from `evaluation/demo_questions.json` to keep the demonstration reproducible.
- Use `evaluation/results/step6_answer_review.csv` for the current generated-answer examples; human review is pending.
- Do not copy or distribute article PDFs, extracted text, index data, or model outputs without confirming the applicable journal permissions.
- Do not describe the demonstration as a validated medical device, clinical decision support, complete archive search, or clinical advice service.
