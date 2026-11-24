"""Canonical 100-App Registry loader and category index."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from src.schemas import AppRegistryEntry


class AppRegistry:
    """Loads and validates the canonical 100-app dataset preserving exact IDs and names."""

    def __init__(self, config_path: str | Path = "config/apps.json") -> None:
        self.config_path = Path(config_path)
        self._apps: List[AppRegistryEntry] = []
        self._load()

    def _load(self) -> None:
        raw = json.loads(self.config_path.read_text(encoding="utf-8"))
        entries = [AppRegistryEntry(**item) for item in raw["apps"]]
        ids = [e.id for e in entries]
        if len(entries) != 100 or sorted(ids) != list(range(1, 101)):
            raise ValueError(
                f"Canonical registry must contain exactly 100 apps numbered 1..100; got {len(entries)}"
            )
        self._apps = sorted(entries, key=lambda e: e.id)

    def all_apps(self) -> List[AppRegistryEntry]:
        return list(self._apps)

    def get_by_id(self, app_id: int) -> Optional[AppRegistryEntry]:
        for app in self._apps:
            if app.id == app_id:
                return app
        return None

    def get_by_category(self, category: str) -> List[AppRegistryEntry]:
        return [app for app in self._apps if app.category == category]

    def categories(self) -> List[str]:
        seen: List[str] = []
        for app in self._apps:
            if app.category not in seen:
                seen.append(app.category)
        return seen

    def sample(self, limit: Optional[int] = None, category: Optional[str] = None) -> List[AppRegistryEntry]:
        items = self.get_by_category(category) if category else self.all_apps()
        return items[:limit] if limit is not None else items

    def summary_counts(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for app in self._apps:
            counts[app.category] = counts.get(app.category, 0) + 1
        return counts
