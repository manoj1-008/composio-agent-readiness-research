# Human Review & Verification Checklist

**Audit Date:** 2026-11-24  
**Scope:** 100 applications across 10 categories (20-app stratified primary-documentation audit + 100-app automated evidence integrity audit).

---

## 1. Completed Independent Primary-Documentation Audits (20 / 20 Stratified Apps)

Every app below was independently verified against its linked official developer, authentication, pricing, or MCP documentation.

- [x] **#9 Copper** (CRM and Sales) — Verified API Key & OAuth 2.0 on `developer.copper.com` and official Claude MCP beta at `copper.com/mcp`.
- [x] **#10 DealCloud** (CRM and Sales) — Verified enterprise Celeste license requirement and read-only MCP tools at `api.docs.dealcloud.com/mcp/tools`.
- [x] **#15 Pylon** (Support and Helpdesk) — Verified sales-assisted trials & no free plan on `usepylon.com/pylon-facts`; **corrected** `buildability` from `Buildable with limitations` to `Partner / enterprise dependent`.
- [x] **#17 Plain** (Support and Helpdesk) — Verified GraphQL-only full-parity API (`plain.com/docs/graphql/introduction`) and hosted OAuth MCP (`mcp.plain.com/mcp`).
- [x] **#24 Lark** (Communications and Messaging) — Verified `larksuite/lark-openapi-mcp`, tenant/user token model, and deprecated remote mode on `open.larksuite.com`.
- [x] **#25 Pumble** (Communications and Messaging) — Verified API Keys addon (`/api-keys generate`) and hosted MCP server on `pumble.com/help`.
- [x] **#31 Google Ads** (Marketing, Ads, Email and Social) — Verified GCP-project access levels (`Test`/`Explorer`/`Basic`/`Standard`) alongside developer token headers on `developers.google.com/google-ads/api/docs`; **refined** `auth_methods` & `primary_blocker`.
- [x] **#37 systeme.io** (Marketing, Ads, Email and Social) — Verified 3-key API cap and MCP keys on `help.systeme.io/article/2323` and `article/9489`.
- [x] **#49 Amazon Selling Partner** (Ecommerce) — Verified SP-API docs on `developer-docs.amazon.com/sp-api/`; **corrected** `mcp_status` to `Vendor-supported` (local sample), `composio_integration` to `false` (no dedicated toolkit page), and canonicalized URL.
- [x] **#50 Fanbasis** (Ecommerce) — Verified `commasdocs.com/` is the official single-page API Reference with `Authentication` & `API Key Scopes`; cleared Pass 2 root-URL heuristic false positive.
- [x] **#58 Sherlock** (Data, SEO and Scraping) — Verified `github.com/sherlock-project/sherlock` (v0.16.2, Python CLI/Docker, no hosted REST API) vs. commercial namesake `sherlockeye.io`; retained explicit `Unknown / needs verification` on `auth_methods`.
- [x] **#60 Clay** (Data, SEO and Scraping) — Verified 2026 Public API v0 (`api.clay.com/public/v0/me`, `clay-api-key`) and Routines/MCP on `developers.clay.com`.
- [x] **#67 Snowflake** (Developer, Infra and Data Platforms) — Verified key-pair JWT/OAuth/PAT auth and Snowflake-managed MCP server on `docs.snowflake.com`.
- [x] **#68 MongoDB Atlas** (Developer, Infra and Data Platforms) — Verified Atlas Data API EOL (September 30, 2025) on `mongodb.com/docs/api/doc/atlas-data-api-v1`.
- [x] **#78 Coda** (Productivity and Project Management) — Verified July 2026 rebrand to Superhuman Docs and OAuth/PAT MCP at `docs.superhuman.com/apis/mcp` on `help.superhuman.com`; upgraded confidence to `High`.
- [x] **#79 Smartsheet** (Productivity and Project Management) — Verified verbatim on `help.smartsheet.com/articles/529590` that free trials block API access token generation and Free plan ended Aug 2024.
- [x] **#84 Paygent Connect** (Finance and Fintech) — Verified `gopaygent.com/developers/docs` only publishes a Collect.js snippet with no public Connect API reference; retained `Low` confidence and explicit unresolved auth/credential fields.
- [x] **#87 Xero** (Finance and Fintech) — Verified exact March 2, 2026 commercial tier table ($0 Starter / $35 AUD Core / $245 AUD Plus / $1,445 AUD Advanced, $2.40 AUD/GB egress) on `developer.xero.com/pricing`.
- [x] **#91 NotebookLM** (AI, Research and Media-native) — Verified Pre-GA `v1alpha` Discovery Engine REST API for Gemini Notebook Enterprise on `docs.cloud.google.com`.
- [x] **#98 Mermaid CLI** (AI, Research and Media-native) — Verified local Node.js CLI (`mermaid-js/mermaid-cli`) with no auth; Pass 2 normalized empty `auth_methods` to `None (local CLI / no auth)`.

---

## 2. Completed Automated 100-App Integrity Checks

- [x] All 100 canonical apps (IDs `1..100`) present and validated against Pydantic v1/v2 schemas.
- [x] Zero unsupported `Official` / `Vendor-supported` MCP claims (`0 / 100` flagged).
- [x] Zero unsupported `composio_integration=true` claims (`0 / 100` flagged; all 79 verified via dedicated `composio.dev/toolkits/<slug>` URLs).
- [x] Confidence scores calibrated strictly against verified evidence depth (`87` High, `12` Medium, `1` Low).

---

## 3. Pending Human & Live-Environment Checks (Unverified)

- [ ] **Stakeholder scope confirmation for #58 Sherlock:** Confirm whether Composio's target is the MIT open-source `sherlock-project/sherlock` OSINT CLI or a commercial namesake (e.g., `sherlockeye.io`).
- [ ] **Vendor documentation request for #84 Paygent Connect:** Contact `gopaygent.com` to obtain private Connect API specifications, authentication flow, and sandbox/KYB terms.
- [ ] **Full primary-page browse for 10 Medium-confidence apps:** `#26 Discord`, `#27 Telegram`, `#33 LinkedIn Ads`, `#34 GoHighLevel`, `#35 Mailchimp`, `#36 Klaviyo`, `#38 Pinterest`, `#40 SendGrid`, `#51 DataForSEO`, and `#55 Apify` currently rely on 1 fully verified page + 3–4 partial snippet sources and were downgraded from `High` to `Medium` confidence pending full page-level verification.
- [ ] **Live 5-app HTTP crawl + Gemini synthesis run:** Pending execution outside the offline sandbox with `GEMINI_API_KEY` (and optional `SERPER_API_KEY`) to populate `data/http_retrieval_log.jsonl`.
- [ ] **Live Composio v3 toolkit tool invocation:** Pending execution outside the offline sandbox with `COMPOSIO_API_KEY` calling `ComposioMcpProvider.test_tool_invocation(tool_slug=...)` to verify an actual toolkit tool execution beyond session creation.
