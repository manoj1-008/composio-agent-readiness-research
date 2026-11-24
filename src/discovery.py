"""Documentation Discovery Agent, Real Search Providers, and Honest Composio v3 Abstraction.

- Provides concrete SearchProvider implementations (Serper API, Google Custom Search,
  and DuckDuckGo HTML fallback) wired into DocumentationDiscoveryAgent.
- Persists structured retrieval logs (`RetrievalLogEntry`) for every discovery attempt.
- Never reports a successful Composio connection based only on SDK initialization:
  `ComposioMcpProvider` marks `execution_status = "not_executed"` unless a live tool
  invocation (`test_tool_invocation`) executes and returns a verified payload.
"""
from __future__ import annotations

import asyncio
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, unquote, urlparse

import httpx
from bs4 import BeautifulSoup

from src.schemas import AppRegistryEntry, EvidenceRecord, SourceStatus, SourceType


@dataclass
class RetrievalLogEntry:
    app_id: int
    app_name: str
    mode: str
    url: str
    status: str
    http_status: Optional[int]
    title: str
    retrieved_at: str
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "app_id": self.app_id,
            "app_name": self.app_name,
            "mode": self.mode,
            "url": self.url,
            "status": self.status,
            "http_status": self.http_status,
            "title": self.title,
            "retrieved_at": self.retrieved_at,
            "note": self.note,
        }


@dataclass
class DiscoveryBundle:
    app: AppRegistryEntry
    candidate_urls: List[str] = field(default_factory=list)
    fetched_pages: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    evidence_stubs: List[EvidenceRecord] = field(default_factory=list)
    retrieval_logs: List[RetrievalLogEntry] = field(default_factory=list)
    mode: str = "live"

    @property
    def verified_page_count(self) -> int:
        return sum(1 for p in self.fetched_pages.values() if p.get("status") == "verified")


class SearchProvider:
    """Pluggable search provider interface."""

    provider_name: str = "abstract"

    async def search(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        raise NotImplementedError


class SerperSearchProvider(SearchProvider):
    """Real Serper.dev Google Search provider (requires SERPER_API_KEY)."""

    provider_name = "serper"

    def __init__(self, api_key: str, timeout_seconds: float = 15.0) -> None:
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    async def search(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            resp = await client.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": self.api_key, "Content-Type": "application/json"},
                json={"q": query, "num": num_results},
            )
            resp.raise_for_status()
            data = resp.json()
        return [
            {"url": item.get("link", ""), "title": item.get("title", ""), "snippet": item.get("snippet", "")}
            for item in data.get("organic", [])
            if item.get("link")
        ]


class GoogleCSESearchProvider(SearchProvider):
    """Real Google Custom Search JSON API provider (requires GOOGLE_CSE_API_KEY & GOOGLE_CSE_CX)."""

    provider_name = "google_cse"

    def __init__(self, api_key: str, cx: str, timeout_seconds: float = 15.0) -> None:
        self.api_key = api_key
        self.cx = cx
        self.timeout_seconds = timeout_seconds

    async def search(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            resp = await client.get(
                "https://www.googleapis.com/customsearch/v1",
                params={"key": self.api_key, "cx": self.cx, "q": query, "num": min(num_results, 10)},
            )
            resp.raise_for_status()
            data = resp.json()
        return [
            {"url": item.get("link", ""), "title": item.get("title", ""), "snippet": item.get("snippet", "")}
            for item in data.get("items", [])
            if item.get("link")
        ]


class DuckDuckGoHtmlSearchProvider(SearchProvider):
    """Keyless fallback search provider querying DuckDuckGo HTML endpoint."""

    provider_name = "duckduckgo_html"

    def __init__(self, timeout_seconds: float = 15.0) -> None:
        self.timeout_seconds = timeout_seconds

    async def search(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        async with httpx.AsyncClient(
            timeout=self.timeout_seconds,
            headers={"User-Agent": "ComposioResearchAgent/1.0"},
        ) as client:
            resp = await client.get("https://html.duckduckgo.com/html/", params={"q": query})
            resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        results: List[Dict[str, str]] = []
        for a in soup.select("a.result__a")[:num_results]:
            href = a.get("href", "")
            if "uddg=" in href:
                parsed = parse_qs(urlparse(href).query)
                href = unquote(parsed.get("uddg", [""])[0])
            if href.startswith("http"):
                results.append({"url": href, "title": a.get_text(" ", strip=True), "snippet": ""})
        return results


def build_default_search_provider() -> SearchProvider:
    """Selects the highest-priority configured SearchProvider from environment variables."""
    if os.getenv("SERPER_API_KEY"):
        return SerperSearchProvider(api_key=os.environ["SERPER_API_KEY"])
    if os.getenv("GOOGLE_CSE_API_KEY") and os.getenv("GOOGLE_CSE_CX"):
        return GoogleCSESearchProvider(
            api_key=os.environ["GOOGLE_CSE_API_KEY"],
            cx=os.environ["GOOGLE_CSE_CX"],
        )
    return DuckDuckGoHtmlSearchProvider()


class ComposioMcpProvider:
    """Honest provider abstraction for Composio v3 Python SDK (`composio>=0.34.0`) + `composio-gemini`.

    Strictly distinguishes three separate states:
    1. `sdk_initialized`: SDK client object constructed locally.
    2. `session_created`: A Composio v3 session was created (`client.create(user_id=...)`),
       which does NOT count as a verified toolkit tool invocation.
    3. `toolkit_tool_invoked`: An actual toolkit action (`client.tools.execute(slug=..., ...)`)
       executed and returned a successful result (`execution_status = "tool_invoked_success"`).
    """

    def __init__(self, api_key: Optional[str] = None, client: Any = None) -> None:
        self.api_key = api_key or os.getenv("COMPOSIO_API_KEY")
        self.sdk_initialized = False
        self.session_created = False
        self.toolkit_tool_invoked = False
        self.invoked_tool_slug: Optional[str] = None
        self.execution_status = "not_executed"
        self.last_invocation_result: Optional[str] = None
        self.unavailable_reason: Optional[str] = None
        self._client = client
        if self._client is not None:
            self.sdk_initialized = True
            self.unavailable_reason = "SDK client injected, but no toolkit tool invocation executed yet"
        else:
            self._init_client()

    def _init_client(self) -> None:
        if not self.api_key:
            self.unavailable_reason = "COMPOSIO_API_KEY not set in environment"
            return
        try:
            from composio import Composio  # type: ignore

            self._client = Composio(api_key=self.api_key)
            self.sdk_initialized = True
            self.unavailable_reason = "SDK initialized, but no live toolkit tool invocation executed yet"
        except ImportError:
            self.unavailable_reason = (
                "composio package not installed (install via: pip install composio composio-gemini)"
            )
        except Exception as exc:  # pragma: no cover
            self.unavailable_reason = f"Composio client init failed: {exc}"

    def test_tool_invocation(
        self,
        user_id: str = "research-agent",
        tool_slug: Optional[str] = None,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Distinguishes session creation from an actual successful toolkit tool invocation."""
        if not self.sdk_initialized or self._client is None:
            self.execution_status = "not_executed"
            return self.status()
        try:
            session = self._client.create(user_id=user_id)
            self.session_created = True
            mcp_url = getattr(getattr(session, "mcp", None), "url", None)
        except Exception as exc:
            self.session_created = False
            self.execution_status = "session_creation_failed"
            self.last_invocation_result = str(exc)
            self.unavailable_reason = f"Composio session creation failed: {exc}"
            return self.status()

        if not tool_slug:
            self.toolkit_tool_invoked = False
            self.execution_status = "session_only_no_tool_invoked"
            self.last_invocation_result = f"Session created (mcp_url={mcp_url or 'available'}); no toolkit tool executed"
            self.unavailable_reason = "Pass an explicit tool_slug to verify a real toolkit tool invocation"
            return self.status()

        try:
            result = self._client.tools.execute(
                slug=tool_slug,
                user_id=user_id,
                arguments=arguments or {},
            )
            self.toolkit_tool_invoked = True
            self.invoked_tool_slug = tool_slug
            self.execution_status = "tool_invoked_success"
            self.last_invocation_result = str(result)[:300]
            self.unavailable_reason = None
        except Exception as exc:
            self.toolkit_tool_invoked = False
            self.invoked_tool_slug = tool_slug
            self.execution_status = "tool_invocation_failed"
            self.last_invocation_result = str(exc)
            self.unavailable_reason = f"Toolkit tool '{tool_slug}' invocation failed: {exc}"
        return self.status()

    def status(self) -> Dict[str, Any]:
        return {
            "execution_status": self.execution_status,
            "sdk_initialized": self.sdk_initialized,
            "session_created": self.session_created,
            "toolkit_tool_invoked": self.toolkit_tool_invoked,
            "invoked_tool_slug": self.invoked_tool_slug,
            "live_tool_verified": self.execution_status == "tool_invoked_success",
            "sdk_target": "composio>=0.34.0 (v3 Sessions API) + composio-gemini",
            "mcp_gateway": "https://connect.composio.dev/mcp",
            "last_invocation_result": self.last_invocation_result,
            "reason": self.unavailable_reason,
        }


class DocumentationDiscoveryAgent:
    """Discovers and fetches official developer, auth, pricing, and MCP documentation."""

    def __init__(
        self,
        timeout_seconds: float = 20.0,
        concurrency_limit: int = 5,
        search_provider: Optional[SearchProvider] = None,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.semaphore = asyncio.Semaphore(concurrency_limit)
        self.search_provider = search_provider or build_default_search_provider()

    @staticmethod
    def build_discovery_queries(app: AppRegistryEntry) -> List[str]:
        return [
            f'"{app.name}" developer API documentation authentication',
            f'"{app.name}" API pricing plan restrictions developer sandbox',
            f'"{app.name}" official MCP server github',
            f'site:composio.dev/toolkits "{app.name}"',
        ]

    @staticmethod
    def classify_source_type(url: str) -> SourceType:
        lowered = url.lower()
        host = urlparse(lowered).netloc
        if "composio.dev" in host or "smithery.ai" in host or "mcpservers.org" in host:
            return SourceType.MCP_REGISTRY
        if "github.com" in host:
            return SourceType.GITHUB
        if any(tok in lowered for tok in ("auth", "oauth", "token", "api-key", "security", "credentials")):
            return SourceType.AUTH_DOCS
        if any(tok in lowered for tok in ("pricing", "plans", "billing", "limits", "free-tier")):
            return SourceType.PRICING
        if any(tok in lowered for tok in ("developer", "docs.", "/docs", "api-reference", "readme.io")):
            return SourceType.OFFICIAL_DOCS
        return SourceType.ARTICLE

    async def fetch_page(self, client: httpx.AsyncClient, url: str) -> Dict[str, Any]:
        async with self.semaphore:
            try:
                resp = await client.get(url, follow_redirects=True, timeout=self.timeout_seconds)
                if resp.status_code >= 400:
                    return {
                        "url": url,
                        "status": "inaccessible",
                        "http_status": resp.status_code,
                        "title": "",
                        "text": "",
                    }
                soup = BeautifulSoup(resp.text, "html.parser")
                title = (soup.title.string or "").strip() if soup.title else urlparse(url).netloc
                for tag in soup(["script", "style", "noscript"]):
                    tag.decompose()
                text = re.sub(r"\s+", " ", soup.get_text(" ")).strip()[:8000]
                return {
                    "url": url,
                    "status": "verified",
                    "http_status": resp.status_code,
                    "title": title,
                    "text": text,
                }
            except Exception as exc:
                return {
                    "url": url,
                    "status": "inaccessible",
                    "http_status": None,
                    "title": "",
                    "text": "",
                    "error": str(exc),
                }

    async def discover(self, app: AppRegistryEntry, seed_urls: Optional[List[str]] = None) -> DiscoveryBundle:
        candidates: List[str] = []
        if app.seed_docs_url:
            candidates.append(app.seed_docs_url)
        for u in seed_urls or []:
            if u and u not in candidates:
                candidates.append(u)

        bundle = DiscoveryBundle(app=app, candidate_urls=candidates, mode="live")
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        if self.search_provider is not None:
            for query in self.build_discovery_queries(app):
                try:
                    results = await self.search_provider.search(query, num_results=4)
                    for hit in results:
                        url = hit.get("url")
                        if url and url not in bundle.candidate_urls:
                            bundle.candidate_urls.append(url)
                except Exception as exc:
                    bundle.retrieval_logs.append(
                        RetrievalLogEntry(
                            app_id=app.id,
                            app_name=app.name,
                            mode="live",
                            url=f"search://{self.search_provider.provider_name}",
                            status="search_error",
                            http_status=None,
                            title=query,
                            retrieved_at=today,
                            note=str(exc),
                        )
                    )

        if bundle.candidate_urls:
            async with httpx.AsyncClient(headers={"User-Agent": "ComposioResearchAgent/1.0"}) as client:
                pages = await asyncio.gather(
                    *(self.fetch_page(client, url) for url in bundle.candidate_urls[:8])
                )
            for page in pages:
                bundle.fetched_pages[page["url"]] = page
                bundle.retrieval_logs.append(
                    RetrievalLogEntry(
                        app_id=app.id,
                        app_name=app.name,
                        mode="live",
                        url=page["url"],
                        status=page["status"],
                        http_status=page.get("http_status"),
                        title=page.get("title", ""),
                        retrieved_at=today,
                        note=page.get("error", ""),
                    )
                )
                bundle.evidence_stubs.append(
                    EvidenceRecord(
                        url=page["url"],
                        title=page["title"] or page["url"],
                        source_type=self.classify_source_type(page["url"]),
                        claims_supported=[],
                        retrieved_at=today,
                        source_status=(
                            SourceStatus.VERIFIED if page["status"] == "verified" else SourceStatus.INACCESSIBLE
                        ),
                    )
                )
        return bundle
