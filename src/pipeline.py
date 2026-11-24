"""End-to-End Reproducible Research Pipeline with SQLite Checkpointing, Retrieval Logs & JSONL Evidence.

Execution Modes:
- `--mode replay`: Deterministic dataset replay over `data/researched_apps.json`
  (explicitly labeled `deterministic_dataset_replay` — NOT fresh web crawling).
- `--mode live`: Live web search (`Serper`/`Google CSE`/`DuckDuckGo`) + async HTTP
  official-docs crawling + `google-genai` Pydantic synthesis (aborts on empty evidence).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import yaml

from src.analytics import AnalyticsEngine
from src.discovery import (
    ComposioMcpProvider,
    DocumentationDiscoveryAgent,
    RetrievalLogEntry,
    build_default_search_provider,
)
from src.evidence import EvidenceEvaluator
from src.registry import AppRegistry
from src.reporting import ReportGenerator
from src.research_agent import ResearchAgent
from src.schemas import ResearchedAppRecord, model_to_dict, model_to_json
from src.verification import VerificationAgent


class CheckpointStore:
    """SQLite-backed checkpoint store enabling resumable execution across 100 apps."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS app_checkpoints (
                    app_id INTEGER PRIMARY KEY,
                    app_name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    pass_stage TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def reset(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM app_checkpoints")
            conn.commit()

    def save(self, record: ResearchedAppRecord, pass_stage: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO app_checkpoints (app_id, app_name, category, pass_stage, payload_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(app_id) DO UPDATE SET
                    pass_stage = excluded.pass_stage,
                    payload_json = excluded.payload_json,
                    updated_at = excluded.updated_at
                """,
                (record.id, record.name, record.category, pass_stage, model_to_json(record), now),
            )
            conn.commit()

    def load_all(self) -> List[ResearchedAppRecord]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT payload_json FROM app_checkpoints ORDER BY app_id ASC"
            ).fetchall()
        return [ResearchedAppRecord(**json.loads(r[0])) for r in rows]


async def run_pipeline(
    config_path: str = "config/research_config.yaml",
    mode: str = "replay",
    limit: Optional[int] = None,
    category: Optional[str] = None,
    reset_checkpoints: bool = False,
    regenerate_report_only: bool = False,
) -> dict:
    cfg = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    pipe_cfg = cfg["pipeline"]

    registry = AppRegistry("config/apps.json")
    composio_provider = ComposioMcpProvider()
    if mode == "live" and composio_provider.sdk_initialized:
        composio_provider.test_tool_invocation()

    checkpoints = CheckpointStore(pipe_cfg["checkpoint_db"])
    if reset_checkpoints:
        checkpoints.reset()

    apps_json_path = Path(pipe_cfg["output_apps_json"])
    evidence_jsonl_path = Path(pipe_cfg["evidence_log"])
    replay_log_path = Path(pipe_cfg.get("replay_log", "data/replay_log.jsonl"))
    http_retrieval_log_path = Path(pipe_cfg.get("http_retrieval_log", "data/http_retrieval_log.jsonl"))
    audit_sample_path = Path(pipe_cfg["audit_sample_json"])
    findings_json_path = Path(pipe_cfg["findings_json"])
    report_html_path = Path(pipe_cfg["report_html"])

    if regenerate_report_only:
        records = [ResearchedAppRecord(**item) for item in json.loads(apps_json_path.read_text(encoding="utf-8"))]
        findings = json.loads(findings_json_path.read_text(encoding="utf-8"))
        audit_data = json.loads(audit_sample_path.read_text(encoding="utf-8"))
        ReportGenerator().generate(records, findings, audit_data, report_html_path)
        return {"status": "report_regenerated", "apps": len(records), "report": str(report_html_path)}

    execution_label = "live_web_research" if mode == "live" else "deterministic_dataset_replay"
    target_apps = registry.sample(limit=limit, category=category)
    search_provider = build_default_search_provider()
    discovery = DocumentationDiscoveryAgent(
        timeout_seconds=pipe_cfg["http_timeout_seconds"],
        concurrency_limit=pipe_cfg["concurrency_limit"],
        search_provider=search_provider,
    )
    researcher = ResearchAgent(replay_dataset_path=apps_json_path)
    evaluator = EvidenceEvaluator()
    verifier = VerificationAgent()

    pass1_records: List[ResearchedAppRecord] = []
    retrieval_logs: List[RetrievalLogEntry] = []
    cached = {r.id: r for r in checkpoints.load_all()}

    for app in target_apps:
        if app.id in cached and not reset_checkpoints:
            pass1_records.append(cached[app.id])
            continue
        if mode == "live":
            bundle = await discovery.discover(app)
            retrieval_logs.extend(bundle.retrieval_logs)
            rec = researcher.research_app(app, bundle=bundle, mode="live")
        else:
            rec = researcher.research_app(app, bundle=None, mode="replay")
            for ev in rec.evidence:
                retrieval_logs.append(
                    RetrievalLogEntry(
                        app_id=rec.id,
                        app_name=rec.name,
                        mode=execution_label,
                        url=ev.url,
                        status=ev.source_status.value,
                        http_status=None,
                        title=ev.title,
                        retrieved_at=ev.retrieved_at,
                        note="Replayed from verified primary-source dataset (no live HTTP fetch in replay mode)",
                    )
                )
        checkpoints.save(rec, pass_stage="pass1_researched")
        pass1_records.append(rec)

    pass2_records, _ = evaluator.evaluate_batch(pass1_records)
    for rec in pass2_records:
        checkpoints.save(rec, pass_stage="pass2_evidence_checked")

    final_records, warnings = verifier.run_pass3(pass2_records)
    for rec in final_records:
        checkpoints.save(rec, pass_stage="pass3_verified")

    # Strictly separate deterministic replay logs from actual live HTTP retrieval logs
    active_log_path = http_retrieval_log_path if mode == "live" else replay_log_path
    active_log_path.parent.mkdir(parents=True, exist_ok=True)
    with active_log_path.open("w", encoding="utf-8") as fh:
        for entry in retrieval_logs:
            row = entry.to_dict()
            row["log_type"] = "live_http_retrieval" if mode == "live" else "deterministic_replay"
            row["http_executed"] = (mode == "live")
            fh.write(json.dumps(row) + "\n")

    if limit is None and category is None:
        apps_json_path.parent.mkdir(parents=True, exist_ok=True)
        apps_json_path.write_text(
            json.dumps([model_to_dict(r) for r in final_records], indent=2),
            encoding="utf-8",
        )
        with evidence_jsonl_path.open("w", encoding="utf-8") as fh:
            for rec in final_records:
                for ev in rec.evidence:
                    row = model_to_dict(ev)
                    row["app_id"] = rec.id
                    row["app_name"] = rec.name
                    row["category"] = rec.category
                    fh.write(json.dumps(row) + "\n")

    audit_data = {}
    accuracy_metrics = None
    if audit_sample_path.exists():
        audit_data = json.loads(audit_sample_path.read_text(encoding="utf-8"))
        audit_entries = verifier.load_audit_sample(audit_sample_path)
        meta = audit_data.get("audit_summary", {})
        accuracy_metrics = verifier.compute_accuracy_metrics(
            all_records=final_records,
            audit_entries=audit_entries,
            false_positives=int(meta.get("false_positives", 0)),
            false_negatives=int(meta.get("false_negatives", 0)),
        )

    engine = AnalyticsEngine(final_records)
    findings = engine.save_findings(findings_json_path, accuracy=accuracy_metrics)
    findings["execution_metadata"] = {
        "pipeline_mode": execution_label,
        "search_provider_configured": search_provider.provider_name,
        "replay_log_entries": len(retrieval_logs) if mode != "live" else 0,
        "live_http_retrieval_entries": len(retrieval_logs) if mode == "live" else 0,
        "active_log_file": str(active_log_path),
        "composio_provider": composio_provider.status(),
    }
    findings_json_path.write_text(json.dumps(findings, indent=2), encoding="utf-8")

    ReportGenerator().generate(final_records, findings, audit_data, report_html_path)

    return {
        "status": "completed",
        "execution_mode": execution_label,
        "apps_processed": len(final_records),
        "retrieval_log_entries": len(retrieval_logs),
        "pass3_warnings": len(warnings),
        "needs_human_review": sum(1 for r in final_records if r.verification_status == "Needs human review"),
        "composio_provider": composio_provider.status(),
        "report": str(report_html_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Composio 100-App Agent-Readiness Research Pipeline")
    parser.add_argument("--config", default="config/research_config.yaml")
    parser.add_argument("--mode", choices=["replay", "live"], default="replay")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--category", type=str, default=None)
    parser.add_argument("--reset-checkpoints", action="store_true")
    parser.add_argument("--regenerate-report-only", action="store_true")
    args = parser.parse_args()

    result = asyncio.run(
        run_pipeline(
            config_path=args.config,
            mode=args.mode,
            limit=args.limit,
            category=args.category,
            reset_checkpoints=args.reset_checkpoints,
            regenerate_report_only=args.regenerate_report_only,
        )
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
