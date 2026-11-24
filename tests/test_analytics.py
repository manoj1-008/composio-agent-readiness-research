"""Unit tests for Pandas Analytics Engine and programmatic findings consistency."""
import json
import unittest
from pathlib import Path

from src.analytics import AnalyticsEngine
from src.schemas import ResearchedAppRecord


class TestAnalyticsEngine(unittest.TestCase):
    def setUp(self):
        raw = json.loads(Path("data/researched_apps.json").read_text(encoding="utf-8"))
        self.records = [ResearchedAppRecord(**item) for item in raw]
        self.engine = AnalyticsEngine(self.records)
        self.findings = self.engine.compute_findings()

    def test_overview_counts_sum_to_100(self):
        self.assertEqual(self.findings["overview"]["apps_researched"], 100)
        bld = self.findings["distributions"]["buildability"]
        self.assertEqual(sum(bld.values()), 100)
        cred = self.findings["distributions"]["credential_acquisition"]
        self.assertEqual(sum(cred.values()), 100)

    def test_category_breakdown_covers_all_10_categories(self):
        cats = self.findings["category_breakdown"]
        self.assertEqual(len(cats), 10)
        for c in cats:
            self.assertEqual(
                c["ready_to_build"]
                + c["buildable_with_limitations"]
                + c["partner_enterprise"]
                + c["not_practical"],
                10,
            )

    def test_opportunity_matrix_has_100_points(self):
        pts = self.findings["opportunity_matrix"]
        self.assertEqual(len(pts), 100)
        for p in pts:
            self.assertGreaterEqual(p["accessibility_score"], 0)
            self.assertLessEqual(p["accessibility_score"], 100)
            self.assertGreaterEqual(p["api_maturity_score"], 0)
            self.assertLessEqual(p["api_maturity_score"], 100)

    def test_five_executive_insights_generated(self):
        self.assertEqual(len(self.findings["executive_insights"]), 5)


if __name__ == "__main__":
    unittest.main()
