"""Structured Research Agent powered by Google GenAI (`google-genai`) or deterministic replay.

Hard guardrails:
- Live synthesis NEVER runs on an empty or zero-verified evidence bundle
  (`EmptyEvidenceBundleError` is raised).
- Replay mode is explicitly labeled `deterministic_dataset_replay` and never
  represented as fresh live crawling.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, Optional

from src.discovery import DiscoveryBundle
from src.schemas import AppRegistryEntry, ResearchedAppRecord


class EmptyEvidenceBundleError(ValueError):
    """Raised when live LLM synthesis is attempted without verified retrieved evidence."""


class GeminiResearchProvider:
    """Wraps `google-genai` structured Pydantic synthesis when GEMINI_API_KEY is configured."""

    def __init__(self, model: str = "gemini-2.5-flash", api_key: Optional[str] = None) -> None:
        self.model = model
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.available = False
        self._client = None
        if self.api_key:
            try:
                from google import genai  # type: ignore

                self._client = genai.Client(api_key=self.api_key)
                self.available = True
            except ImportError:
                self.available = False

    def synthesize(self, app: AppRegistryEntry, bundle: DiscoveryBundle) -> ResearchedAppRecord:
        verified_pages = [
            (url, page)
            for url, page in bundle.fetched_pages.items()
            if page.get("status") == "verified" and page.get("text", "").strip()
        ]
        if not verified_pages:
            raise EmptyEvidenceBundleError(
                f"Refusing to run Gemini synthesis for #{app.id} {app.name}: "
                f"evidence bundle has 0 verified pages (candidate_urls={len(bundle.candidate_urls)})."
            )

        if not self.available or self._client is None:
            raise RuntimeError(
                "Gemini live synthesis requires `google-genai` package and GEMINI_API_KEY."
            )
        from google.genai import types  # type: ignore

        context_snippets = "\n\n".join(
            f"URL: {url}\nTITLE: {p['title']}\nEXCERPT: {p['text'][:2000]}"
            for url, p in verified_pages
        )
        prompt = (
            f"Synthesize a strictly grounded integration-readiness record for #{app.id} {app.name} "
            f"(Category: {app.category}). Use ONLY the retrieved evidence below. Never fabricate URLs. "
            f"If evidence does not confirm a field, mark it 'Unclear / not verified' or 'Unknown / needs verification'.\n\n"
            f"{context_snippets}"
        )
        response = self._client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ResearchedAppRecord,
                temperature=0.1,
            ),
        )
        return ResearchedAppRecord(**json.loads(response.text))


class ResearchAgent:
    """Executes Pass 1 extraction in either live mode or deterministic dataset replay mode."""

    def __init__(
        self,
        replay_dataset_path: Optional[str | Path] = None,
        gemini_provider: Optional[GeminiResearchProvider] = None,
    ) -> None:
        self.gemini_provider = gemini_provider or GeminiResearchProvider()
        self._replay_index: Dict[int, dict] = {}
        if replay_dataset_path and Path(replay_dataset_path).exists():
            raw = json.loads(Path(replay_dataset_path).read_text(encoding="utf-8"))
            items = raw["apps"] if isinstance(raw, dict) and "apps" in raw else raw
            for item in items:
                self._replay_index[int(item["id"])] = item

    def research_app(
        self, app: AppRegistryEntry, bundle: Optional[DiscoveryBundle] = None, mode: str = "replay"
    ) -> ResearchedAppRecord:
        if mode == "live":
            if bundle is None or bundle.verified_page_count == 0:
                raise EmptyEvidenceBundleError(
                    f"Live research aborted for #{app.id} {app.name}: discovery returned 0 verified pages."
                )
            return self.gemini_provider.synthesize(app, bundle)

        if app.id in self._replay_index:
            return ResearchedAppRecord(**self._replay_index[app.id])
        raise KeyError(
            f"Deterministic replay record missing for app id={app.id} ({app.name})."
        )
