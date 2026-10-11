"""Safety boundaries and citation validation for generated answers."""
from __future__ import annotations

import re
import json
from dataclasses import dataclass
from typing import Protocol

class AnswerProvider(Protocol):
    def answer(self, question: str, evidence: list[dict], *, max_output_tokens: int = 1200) -> str: ...

NO_EVIDENCE = "I could not find relevant supporting evidence in the indexed journal corpus. Try a more specific topic, author, or issue filter."
PATIENT_BOUNDARY = "I can help summarize published journal literature, but I cannot assess an individual child or recommend diagnosis, treatment, or a dose. Please consult a qualified clinician for patient-specific decisions."
_PATIENT_QUERY = re.compile(r"\b(my (child|baby|patient)|my son|my daughter|what dose (should|can) i|should i (give|treat)|what should i give)\b", re.I)

def is_patient_specific(question: str) -> bool:
    return bool(_PATIENT_QUERY.search(question))

@dataclass
class AnswerResult:
    answer: str
    evidence: list[dict]
    status: str

def answer_question(question: str, evidence: list[dict], provider: AnswerProvider | None = None) -> AnswerResult:
    if is_patient_specific(question):
        return AnswerResult(PATIENT_BOUNDARY, [], "patient_specific_boundary")
    if not evidence:
        return AnswerResult(NO_EVIDENCE, [], "no_evidence")
    if provider is None:
        return AnswerResult("Relevant journal evidence was found, but answer generation is not configured. Review the cited source passages below.", evidence, "generation_not_configured")
    raw = provider.answer(question, evidence)
    allowed = {e["source_label"] for e in evidence}
    try:
        payload = json.loads(raw)
        claims = payload.get("claims")
        if payload.get("insufficient_evidence") is True and claims == []:
            return AnswerResult(NO_EVIDENCE, evidence, "no_evidence_from_generation")
        if not isinstance(claims, list) or not claims:
            raise ValueError("No grounded claims")
        rendered = []
        for claim in claims:
            text = claim.get("text", "").strip()
            ids = claim.get("source_ids", [])
            if not text or not ids or not set(ids).issubset(allowed):
                raise ValueError("Claim has no valid retrieved source IDs")
            rendered.append(f"{text} " + " ".join(f"[{source_id}]" for source_id in dict.fromkeys(ids)))
        return AnswerResult("\n\n".join(rendered), evidence, "answered")
    except (json.JSONDecodeError, AttributeError, TypeError, ValueError):
        return AnswerResult("I could not produce an answer with valid citations to the retrieved passages. Please inspect the source passages directly.", evidence, "citation_validation_failed")
