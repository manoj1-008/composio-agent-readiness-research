"""Unit tests for Pass 2 Evidence Evaluator, Pass 3 Verification, Empty Evidence Guard, and Composio Status."""
import json
import unittest
from pathlib import Path

from src.discovery import ComposioMcpProvider, DiscoveryBundle
from src.evidence import EvidenceEvaluator
from src.research_agent import EmptyEvidenceBundleError, GeminiResearchProvider, ResearchAgent
from src.schemas import (
    AppRegistryEntry,
    EvidenceRecord,
    McpStatus,
    ResearchedAppRecord,
    SourceStatus,
    SourceType,
    model_copy_deep,
)
from src.verification import VerificationAgent


class TestEvidenceAndVerification(unittest.TestCase):
    def setUp(self):
        raw = json.loads(Path("data/researched_apps.json").read_text(encoding="utf-8"))
        self.records = [ResearchedAppRecord(**item) for item in raw]
        self.evaluator = EvidenceEvaluator()
        self.verifier = VerificationAgent()

    def test_homepage_detector(self):
        self.assertTrue(self.evaluator.is_bare_homepage("https://example.com/"))
        self.assertTrue(self.evaluator.is_bare_homepage("https://example.com"))
        self.assertFalse(self.evaluator.is_bare_homepage("https://example.com/docs/auth"))

    def test_missing_evidence_flagged(self):
        rec = model_copy_deep(self.records[0])
        rec.evidence = []
        result = self.evaluator.evaluate(rec)
        self.assertFalse(result.passed)
        self.assertIn("insufficient_evidence_count (<2 usable sources)", result.flags)
        self.assertIn("missing_auth_evidence", result.flags)

    def test_false_official_mcp_claim_flagged(self):
        rec = model_copy_deep(self.records[0])
        rec.mcp_status = McpStatus.OFFICIAL
        rec.evidence = [
            EvidenceRecord(
                url="https://example.com/blog/mcp-review",
                title="Third party review",
                source_type=SourceType.ARTICLE,
                claims_supported=["mcp_status"],
                retrieved_at="2026-11-24",
                source_status=SourceStatus.VERIFIED,
            ),
            EvidenceRecord(
                url="https://developer.salesforce.com/docs/apis",
                title="API Docs",
                source_type=SourceType.OFFICIAL_DOCS,
                claims_supported=["api_availability", "auth_methods"],
                retrieved_at="2026-11-24",
                source_status=SourceStatus.VERIFIED,
            ),
        ]
        result = self.evaluator.evaluate(rec)
        self.assertFalse(result.passed)
        self.assertIn("official_mcp_without_primary_evidence", result.flags)

    def test_false_composio_category_url_flagged(self):
        rec = model_copy_deep(self.records[0])
        rec.composio_integration = True
        rec.evidence = [
            ev for ev in rec.evidence if "composio.dev" not in ev.url
        ] + [
            EvidenceRecord(
                url="https://composio.dev/category/e-commerce",
                title="Category listing",
                source_type=SourceType.MCP_REGISTRY,
                claims_supported=["composio_integration"],
                retrieved_at="2026-11-24",
                source_status=SourceStatus.VERIFIED,
            )
        ]
        result = self.evaluator.evaluate(rec)
        self.assertIn("composio_flag_missing_dedicated_toolkit_url", result.flags)

    def test_low_confidence_paygent_flagged(self):
        paygent = next(r for r in self.records if r.id == 84)
        result = self.evaluator.evaluate(paygent)
        self.assertFalse(result.passed)
        self.assertIn("low_confidence_record", result.flags)
        self.assertIn("unclear_credential_acquisition", result.flags)

    def test_pass3_detects_enterprise_ready_contradiction(self):
        dealcloud = model_copy_deep(next(r for r in self.records if r.id == 10))
        dealcloud.buildability = "Ready to build"  # type: ignore
        warnings = self.verifier.cross_check_record(dealcloud)
        self.assertTrue(any("contradiction" in w for w in warnings))

    def test_empty_evidence_bundle_rejected_by_live_synthesis(self):
        app = AppRegistryEntry(id=1, name="Salesforce", category="CRM and Sales")
        empty_bundle = DiscoveryBundle(app=app, candidate_urls=[], fetched_pages={}, mode="live")
        with self.assertRaises(EmptyEvidenceBundleError):
            GeminiResearchProvider(api_key="dummy").synthesize(app, empty_bundle)
        with self.assertRaises(EmptyEvidenceBundleError):
            ResearchAgent().research_app(app, bundle=empty_bundle, mode="live")

    def test_composio_provider_reports_not_executed_without_live_invocation(self):
        provider = ComposioMcpProvider(api_key=None)
        status = provider.status()
        self.assertEqual(status["execution_status"], "not_executed")
        self.assertFalse(status["live_tool_verified"])
        self.assertFalse(status["session_created"])
        self.assertFalse(status["toolkit_tool_invoked"])

        # Session creation alone MUST NOT count as a verified toolkit tool invocation
        class _SessionOnlyClient:
            def create(self, user_id):
                return type("S", (), {"mcp": type("M", (), {"url": "https://connect.composio.dev/mcp"})()})()

        session_only = ComposioMcpProvider(client=_SessionOnlyClient()).test_tool_invocation(user_id="u1")
        self.assertTrue(session_only["session_created"])
        self.assertFalse(session_only["toolkit_tool_invoked"])
        self.assertFalse(session_only["live_tool_verified"])
        self.assertEqual(session_only["execution_status"], "session_only_no_tool_invoked")

    def test_audit_sample_has_20_stratified_apps(self):
        entries = self.verifier.load_audit_sample("data/audit_sample.json")
        self.assertEqual(len(entries), 20)
        cats = {}
        for e in entries:
            cats[e.category] = cats.get(e.category, 0) + 1
        self.assertEqual(len(cats), 10)
        self.assertTrue(all(v == 2 for v in cats.values()))


if __name__ == "__main__":
    unittest.main()
