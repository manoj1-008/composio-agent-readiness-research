"""Pass 2: Evidence Evaluator and Human Review Queue Router.

Audits each ResearchedAppRecord to verify that material claims (API availability,
authentication, credential acquisition, MCP status, Composio toolkit presence)
are backed by primary-source evidence rather than bare homepages, category pages,
or weak third-party articles.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple
from urllib.parse import urlparse

from src.schemas import (
    ApiAvailability,
    AuthMethod,
    ConfidenceLevel,
    CredentialAcquisition,
    McpStatus,
    ResearchedAppRecord,
    SourceStatus,
    SourceType,
    model_copy_deep,
)


WEAK_OR_THIRD_PARTY_DOMAINS = (
    "g2.com",
    "capterra.com",
    "trustradius.com",
    "zapier.com",
    "mcpservers.org",
    "smithery.ai",
    "clonepartner.com",
    "getfuzzy.ai",
    "scalekit.com",
)


@dataclass
class EvidenceEvaluation:
    app_id: int
    app_name: str
    score: float
    passed: bool
    flags: List[str]


class EvidenceEvaluator:
    """Enforces primary-source traceability and flags weak, unsupported, or conflicting records."""

    MATERIAL_CLAIMS = ("api_availability", "auth_methods", "credential_acquisition", "mcp_status")

    @staticmethod
    def is_bare_homepage(url: str) -> bool:
        parsed = urlparse(url)
        path = (parsed.path or "").strip("/")
        return path == "" and not parsed.query

    @staticmethod
    def is_weak_or_third_party(url: str) -> bool:
        host = urlparse(url).netloc.lower()
        return any(d in host for d in WEAK_OR_THIRD_PARTY_DOMAINS)

    @staticmethod
    def is_dedicated_composio_toolkit_url(url: str) -> bool:
        lowered = url.lower()
        return "composio.dev" in lowered and "/toolkits/" in lowered

    def evaluate(self, record: ResearchedAppRecord) -> EvidenceEvaluation:
        flags: List[str] = []
        verified_sources = [e for e in record.evidence if e.source_status == SourceStatus.VERIFIED]
        usable_sources = [e for e in record.evidence if e.source_status != SourceStatus.INACCESSIBLE]

        if len(usable_sources) < 2:
            flags.append("insufficient_evidence_count (<2 usable sources)")

        supported_claims = {
            claim for ev in usable_sources for claim in ev.claims_supported
        }

        # Flag any non-official / third-party aggregator sources
        third_party_urls = [ev.url for ev in usable_sources if self.is_weak_or_third_party(ev.url)]
        if third_party_urls:
            flags.append("contains_non_official_or_third_party_source")

        # Rule: Do not rely on bare homepages as sole auth evidence
        auth_evidence = [
            ev for ev in usable_sources
            if "auth_methods" in ev.claims_supported or ev.source_type == SourceType.AUTH_DOCS
        ]
        if (
            AuthMethod.UNKNOWN not in record.auth_methods
            and AuthMethod.NONE_LOCAL not in record.auth_methods
            and record.api_availability != ApiAvailability.NO_PUBLIC_API
        ):
            if not auth_evidence:
                flags.append("missing_auth_evidence")
            elif all(self.is_bare_homepage(ev.url) for ev in auth_evidence) and not any(
                "docs" in urlparse(ev.url).netloc.lower() for ev in auth_evidence
            ):
                flags.append("auth_supported_only_by_homepage")

        # Rule: Do not classify as free self-service without pricing/docs evidence
        if record.credential_acquisition == CredentialAcquisition.FREE_SELF_SERVICE:
            has_access_ev = any(
                "credential_acquisition" in ev.claims_supported
                or "commercial_considerations" in ev.claims_supported
                or ev.source_type in (SourceType.PRICING, SourceType.OFFICIAL_DOCS, SourceType.GITHUB)
                for ev in usable_sources
            )
            if not has_access_ev:
                flags.append("free_access_without_evidence")

        # Rule: Official / Vendor-supported MCP claims must be backed by primary official_docs or github URL
        if record.mcp_status in (McpStatus.OFFICIAL, McpStatus.VENDOR_SUPPORTED):
            has_primary_mcp_ev = any(
                ("mcp_status" in ev.claims_supported or "mcp_details" in ev.claims_supported)
                and ev.source_type in (SourceType.OFFICIAL_DOCS, SourceType.GITHUB)
                and not self.is_weak_or_third_party(ev.url)
                and "composio.dev" not in ev.url.lower()
                for ev in usable_sources
            )
            if not has_primary_mcp_ev:
                flags.append("official_mcp_without_primary_evidence")

        # Rule: Composio integration boolean must be backed by a dedicated /toolkits/<slug> URL
        if record.composio_integration:
            has_toolkit_url = any(
                self.is_dedicated_composio_toolkit_url(ev.url) for ev in usable_sources
            )
            if not has_toolkit_url:
                flags.append("composio_flag_missing_dedicated_toolkit_url")

        # Rule: High confidence requires >= 2 verified primary sources
        if record.confidence == ConfidenceLevel.HIGH and len(verified_sources) < 2:
            flags.append("high_confidence_with_insufficient_verified_sources")

        # Rule: Flag low confidence or explicit unknown statuses for human review
        if record.confidence == ConfidenceLevel.LOW:
            flags.append("low_confidence_record")
        if record.credential_acquisition == CredentialAcquisition.UNCLEAR:
            flags.append("unclear_credential_acquisition")
        if AuthMethod.UNKNOWN in record.auth_methods:
            flags.append("unknown_auth_method")

        claim_hits = sum(1 for c in self.MATERIAL_CLAIMS if c in supported_claims)
        claim_ratio = claim_hits / len(self.MATERIAL_CLAIMS)
        verified_ratio = len(verified_sources) / max(len(record.evidence), 1)
        severe_flags = [
            f for f in flags
            if f not in ("contains_non_official_or_third_party_source",)
        ]
        penalty = 0.12 * len(severe_flags)
        score = round(max(0.0, min(1.0, 0.65 * claim_ratio + 0.35 * verified_ratio - penalty)), 3)

        passed = len(severe_flags) == 0 and score >= 0.70
        return EvidenceEvaluation(
            app_id=record.id,
            app_name=record.name,
            score=score,
            passed=passed,
            flags=flags,
        )

    def evaluate_batch(
        self, records: List[ResearchedAppRecord]
    ) -> Tuple[List[ResearchedAppRecord], List[EvidenceEvaluation]]:
        updated: List[ResearchedAppRecord] = []
        evaluations: List[EvidenceEvaluation] = []
        for rec in records:
            ev = self.evaluate(rec)
            evaluations.append(ev)
            rec_copy: ResearchedAppRecord = model_copy_deep(rec)
            rec_copy.evidence_score = ev.score
            rec_copy.review_flags = ev.flags
            if not ev.passed and rec_copy.verification_status in ("Initial pass verified", "Cross-checked"):
                rec_copy.verification_status = "Needs human review"
            updated.append(rec_copy)
        return updated, evaluations
