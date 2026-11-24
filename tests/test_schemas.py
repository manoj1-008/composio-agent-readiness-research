"""Unit tests for canonical 100-app registry and Pydantic schemas."""
import json
import unittest
from pathlib import Path

from pydantic import ValidationError

from src.registry import AppRegistry
from src.schemas import ResearchedAppRecord


class TestSchemasAndRegistry(unittest.TestCase):
    def test_canonical_registry_has_100_apps_across_10_categories(self):
        registry = AppRegistry("config/apps.json")
        self.assertEqual(len(registry.all_apps()), 100)
        self.assertEqual(len(registry.categories()), 10)
        counts = registry.summary_counts()
        self.assertTrue(all(v == 10 for v in counts.values()))

    def test_all_100_researched_records_validate_against_schema(self):
        raw = json.loads(Path("data/researched_apps.json").read_text(encoding="utf-8"))
        self.assertEqual(len(raw), 100)
        records = [ResearchedAppRecord(**item) for item in raw]
        ids = [r.id for r in records]
        self.assertEqual(sorted(ids), list(range(1, 101)))

    def test_invalid_url_rejected_by_schema(self):
        raw = json.loads(Path("data/researched_apps.json").read_text(encoding="utf-8"))[0]
        raw["developer_docs_url"] = "not-a-valid-url"
        with self.assertRaises(ValidationError):
            ResearchedAppRecord(**raw)

    def test_empty_auth_methods_rejected_by_schema(self):
        raw = json.loads(Path("data/researched_apps.json").read_text(encoding="utf-8"))[0]
        raw["auth_methods"] = []
        with self.assertRaises(ValidationError):
            ResearchedAppRecord(**raw)


if __name__ == "__main__":
    unittest.main()
