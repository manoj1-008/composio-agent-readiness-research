# Composio Agent-Readiness Research Pipeline (`composio-agent-readiness-research`)

A production-quality, multi-pass AI Product Operations research pipeline that audits **100 SaaS, developer, fintech, and AI-native applications** across **10 categories** to evaluate API maturity, authentication architecture, commercial credential friction, MCP ecosystem maturity, and Composio integration opportunities.

## Key Engineering Guarantees
- **Pydantic v1 & v2 Compatible**: Zero deprecated `Field(regex=...)` usage; uses strict `Enum` types and version-safe serialization helpers (`src/schemas.py`).
- **Explicit Execution Provenance**: `--mode replay` is explicitly labeled `deterministic_dataset_replay` (not fresh live crawling) and logs every replayed URL to `data/retrieval_log.jsonl`. `--mode live` connects real search providers (`SerperSearchProvider`, `GoogleCSESearchProvider`, `DuckDuckGoHtmlSearchProvider`) + official seed URLs from `config/apps.json` and raises `EmptyEvidenceBundleError` if zero verified pages are retrieved.
- **Honest Composio v3 Provider**: Targets `composio>=0.34.0` (Sessions API) + `composio-gemini`. Never reports a successful connection from SDK initialization alone; `execution_status` remains `"not_executed"` unless `test_tool_invocation()` succeeds on a live tool call.
- **Strictly Reconciled Field-Level Accuracy**: Pass 1, Post-Validation (Pass 2+3), and Final Audited (Pass 4) accuracies are computed directly from per-field `field_results` (`Correct` = 1, `Partially correct` = 0, `Incorrect` = 0, `Unresolved`/`Unknown` = 0).
- **100% Offline HTML Case Study**: `reports/index.html` uses zero external CDN scripts, CSS frameworks, or web fonts — all charts are inline SVG + vanilla JS.

## Repository Structure

```text
composio-agent-readiness-research/
├── README.md
├── LICENSE
├── .gitignore
├── .env.example
├── requirements.txt
├── config/
│   ├── apps.json               # Canonical 100-app registry (IDs 1..100 + official seed_docs_url)
│   └── research_config.yaml
├── src/
│   ├── schemas.py              # Pydantic v1/v2-safe models & enums
│   ├── registry.py             # Canonical 100-app loader
│   ├── discovery.py            # Real search providers, async crawler & Composio v3 provider
│   ├── research_agent.py       # google-genai structured synthesis + EmptyEvidenceBundleError guard
│   ├── evidence.py             # Pass 2 Evidence Evaluator (weak sources, MCP & Composio checks)
│   ├── verification.py         # Pass 3 Cross-Checker & strict Pass 1/2/4 accuracy engine
│   ├── analytics.py            # Pandas aggregations, Opportunity Matrix & executive insights
│   ├── reporting.py            # Jinja2 zero-CDN offline HTML case study generator
│   └── pipeline.py             # CLI orchestrator with SQLite checkpointing & retrieval logs
├── data/
│   ├── researched_apps.json    # Finalized 100-app dataset (461 primary evidence records)
│   ├── evidence.jsonl          # Line-delimited structured evidence audit trail
│   ├── retrieval_log.jsonl     # Per-run URL retrieval & provenance log
│   ├── audit_sample.json       # Stratified 20-app primary-doc audit (140 evaluated fields)
│   └── findings.json           # Programmatically computed analytics & reconciled accuracy metrics
├── reports/
│   └── index.html              # 100% offline interactive HTML case study
├── tests/
│   ├── test_schemas.py
│   ├── test_evidence.py
│   ├── test_accuracy.py
│   └── test_analytics.py
└── docs/
    ├── architecture.md
    └── methodology.md
```

## Quick Start

```bash
# 1. Setup (Python 3.11+)
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# 2. Deterministic Dataset Replay (validates all 100 apps, computes findings & rebuilds offline HTML)
python3 -m src.pipeline --mode replay --reset-checkpoints

# 3. Smaller Sample Run
python3 -m src.pipeline --mode replay --category "CRM and Sales" --limit 5

# 4. Live Web-Crawl + Gemini Structured Synthesis (requires GEMINI_API_KEY + internet access)
python3 -m src.pipeline --mode live --limit 5

# 5. Regenerate HTML Only
python3 -m src.pipeline --regenerate-report-only

# 6. Run Full Test Suite
python3 -m unittest discover -s tests -v
```

## Deployment
`reports/index.html` is completely self-contained (zero CDN dependencies). Push the repository to GitHub and enable GitHub Pages on `reports/index.html`, or deploy directly with `npx vercel reports/`.
