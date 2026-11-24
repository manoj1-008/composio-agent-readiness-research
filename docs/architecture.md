# System Architecture

## Modular Pipeline Overview

```text
App Registry (config/apps.json)
      │
      ▼
Documentation Discovery Agent (src/discovery.py)
  ├─ Async HTTP crawler (httpx + BeautifulSoup4, bounded semaphore)
  ├─ Pluggable SearchProvider interface
  └─ ComposioMcpProvider (v3 Sessions API `composio>=0.34.0` + `composio-gemini`)
      │
      ▼
Research Agent (src/research_agent.py)
  ├─ Live mode: `google-genai` Pydantic structured output synthesis
  └─ Replay mode: Deterministic ingestion from verified primary-source dataset
      │
      ▼  [SQLite Checkpoint: pass1_researched]
Evidence Evaluator (src/evidence.py) — Pass 2
  ├─ Enforces >= 2 usable primary sources per app
  ├─ Rejects bare homepages as sole authentication evidence
  ├─ Verifies Composio toolkit URLs and official MCP citations
  └─ Computes deterministic 0..1 evidence score & routes flags to Human Review Queue
      │
      ▼  [SQLite Checkpoint: pass2_evidence_checked]
Verification Agent (src/verification.py) — Pass 3 & Pass 4
  ├─ Pass 3: Cross-checks commercial vs. technical contradictions
  └─ Pass 4: Computes field-level accuracy across 20 stratified human-audited apps
      │
      ▼  [SQLite Checkpoint: pass3_verified]
Analytics Engine (src/analytics.py)
  └─ Pandas aggregations, 2x2 Opportunity Matrix scores, strategic buckets & 5 executive insights
      │
      ▼
Report Generator (src/reporting.py)
  └─ Jinja2 self-contained HTML case study (`reports/index.html`) with Chart.js + interactive 100-app explorer
```
