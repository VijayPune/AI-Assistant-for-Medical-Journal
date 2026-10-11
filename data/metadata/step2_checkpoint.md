# Step 2 — Define and Acquire the POC Corpus

## Purpose

This checkpoint records the scope and provenance of the January 2025 Indian Pediatrics issue selected for the proof of concept (Volume 62, Issue 1; publisher issue ID 766). It prepares an auditable catalogue and local-file manifest. It does not extract, clean, chunk, embed, or index article text; those activities belong to later roadmap steps.

## Corpus selection rules

1. Catalogue the issue's substantive editorial entries, including entries not yet supplied as PDFs.
2. Use stable article IDs so metadata, extracted text, chunks, citations, and evaluation records can be linked later.
3. Keep the publisher's section, issue date, volume, issue number, issue ID, pages, title, authors when verified, local filename, acquisition status, content role, and permission status as separate fields.
4. Prioritize primary clinical evidence for clinical retrieval. Keep clinical context available with its role labelled. Rank secondary Clippings below primary research and preserve their source citation.
5. Keep News in Brief, access notices, duplicate pages, and advertisements out of clinical evidence retrieval. News/notices may be catalogued for audit purposes.
6. Record access as user-provided local copies for an internal POC. This is not a publisher licence or permission to redistribute; external editor demonstrations and any later product use need confirmation.
7. Do not invent unknown authors or DOI values. Blank values are safer than unverified metadata.

## Acquired-file inventory

The manifest covers the 19 PDFs currently supplied in `data/raw/2025_Jan`. The local files were checked for nonzero size, PDF signature, physical pages, and extractable text. The file named `14.pdf` contains a repeated ending from the commentary in `13.pdf` and an access notice, so it is excluded from article text ingestion. `84.pdf` is News in Brief and is excluded from clinical retrieval. `83.pdf` is a secondary clipping and should carry reduced retrieval weight.

## Catalogue completeness and known gaps

The publisher issue contents list two Correspondence pieces on pages 81–82, but their PDFs are not in the supplied folder. At the user's direction, both remain in the article catalogue with `acquisition_status=scoped_out`; no replacement or inferred content is created and they are outside the accepted POC corpus. The selected issue also lists a Notice and advertisements, which are not clinical article records.

## Access and use status

The user has stated they have access to the local files and intends their use for an internal POC. The metadata therefore records that basis without claiming the files are public domain. Publisher/editor approval for external sharing, demonstrations, or product use remains to be confirmed. Do not distribute article PDFs as part of the application.

## Checkpoint command and acceptance

Run `python scripts/prepare_step2_metadata.py` to regenerate the catalogues from the supplied folder, then run `python scripts/check_step2.py`. The checker verifies expected issue records, unique IDs, required metadata, one-to-one folder/manifest coverage, file presence/signatures, recorded text availability, explicit exclusions, and the missing Correspondence entries.

**Step 2 is ready to hand off to Step 3 only when the checker reports `READY FOR STEP 3`.** The user has approved excluding the two absent Correspondence items from this POC corpus. The remaining permission warning is a record that external sharing or product use needs publisher/editor confirmation; it does not block internal POC preparation under the user's stated access and demonstration scope.
