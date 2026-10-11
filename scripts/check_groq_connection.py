"""Check Groq credentials and configured model without sending journal content."""
from __future__ import annotations
import sys, tomllib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from journal_assistant.rag.env import external_text_processing_allowed
from journal_assistant.rag.providers.groq_provider import GroqProvider
from journal_assistant.rag.providers.base import ProviderNotReady

def main() -> int:
    if not external_text_processing_allowed():
        print("NOT READY: external text-processing permission is off in .env")
        return 1
    cfg=tomllib.loads((ROOT/"config/rag.toml").read_text(encoding="utf-8"))
    try:
        provider=GroqProvider(answer_model=cfg["generation"]["model"])
        available=provider.client.models.list()
    except ProviderNotReady as exc:
        print(f"NOT READY: {exc}")
        return 1
    except Exception as exc:
        code=getattr(exc,"status_code",None)
        print(f"CONNECTION FAILED: {type(exc).__name__}"+(f" (HTTP {code})" if code else ""))
        return 1
    model=cfg["generation"]["model"]
    ok=any(item.id==model for item in available.data)
    print("Groq API key accepted; secret not displayed." if ok else "Groq API responded, but the configured model was not listed.")
    print(f"Configured model available: {model if ok else 'no'}")
    print("This check only requested the model list; no article text or question was sent.")
    return 0 if ok else 1

if __name__=="__main__": raise SystemExit(main())
