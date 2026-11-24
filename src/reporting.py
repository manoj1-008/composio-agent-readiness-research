"""100% Offline, Zero-CDN Editorial HTML Case Study Generator using Jinja2.

Renders `reports/index.html` with zero external script, stylesheet, or font CDN
dependencies so the deliverable works identically offline, via file://, or on
any static host. All charts (stacked bar, switchable distribution bar, and
100-app scatter matrix) are rendered cleanly via inline SVG + vanilla JS.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from jinja2 import BaseLoader, Environment

from src.schemas import ResearchedAppRecord, model_to_dict


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Beyond API Discovery: Mapping the Agent-Ready Software Ecosystem</title>
  <style>
    :root {
      --bg: #080A0F;
      --surface: #0F131C;
      --surface-2: #151B28;
      --surface-3: #1C2436;
      --border: rgba(255, 255, 255, 0.08);
      --border-strong: rgba(255, 255, 255, 0.16);
      --text: #F1F5F9;
      --text-2: #CBD5E1;
      --muted: #94A3B8;
      --dim: #64748B;
      --indigo: #6366F1;
      --indigo-soft: #A5B4FC;
      --emerald: #10B981;
      --emerald-soft: #34D399;
      --amber: #F59E0B;
      --amber-soft: #FBBF24;
      --purple: #8B5CF6;
      --purple-soft: #C4B5FD;
      --rose: #F43F5E;
      --rose-soft: #FB7185;
      --sky: #38BDF8;
      --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    html { scroll-behavior: smooth; background: var(--bg); color: var(--text); font-family: var(--font-sans); line-height: 1.5; }
    body {
      background: radial-gradient(1100px 540px at 85% -8%, rgba(99, 102, 241, 0.11), transparent 60%), var(--bg);
      -webkit-font-smoothing: antialiased;
    }
    a { color: var(--indigo-soft); text-decoration: none; }
    a:hover { text-decoration: underline; }
    .mono { font-family: var(--font-mono); }
    .container { max-width: 1240px; margin: 0 auto; padding: 0 20px; }

    /* Sticky Header */
    header {
      position: sticky; top: 0; z-index: 40;
      background: rgba(8, 10, 15, 0.88); backdrop-filter: blur(10px);
      border-bottom: 1px solid var(--border);
    }
    .nav-bar { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 12px 0; }
    .brand { display: flex; align-items: center; gap: 10px; }
    .brand-icon {
      width: 32px; height: 32px; border-radius: 8px;
      background: rgba(99, 102, 241, 0.15); border: 1px solid rgba(99, 102, 241, 0.35);
      display: flex; align-items: center; justify-content: center;
      color: var(--indigo-soft); font-weight: 700; font-size: 13px;
    }
    .brand-title { font-size: 14px; font-weight: 700; color: #fff; }
    .brand-sub { font-size: 11px; color: var(--muted); }
    .nav-links { display: flex; align-items: center; gap: 18px; font-size: 12px; font-weight: 500; }
    .nav-links a { color: var(--muted); }
    .nav-links a:hover { color: #fff; text-decoration: none; }
    .btn-primary {
      background: var(--indigo); color: #fff; font-size: 12px; font-weight: 600;
      padding: 7px 13px; border-radius: 8px; border: none; cursor: pointer; display: inline-block;
    }
    .btn-primary:hover { background: #4F46E5; text-decoration: none; }

    /* Sections & Panels */
    main { padding: 48px 0 88px; display: flex; flex-direction: column; gap: 68px; }
    .eyebrow { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.12em; color: var(--indigo-soft); }
    h1 { font-size: clamp(2rem, 4.4vw, 3.4rem); font-weight: 800; line-height: 1.08; letter-spacing: -0.025em; color: #fff; margin-top: 14px; }
    h2 { font-size: clamp(1.35rem, 2.3vw, 1.85rem); font-weight: 700; letter-spacing: -0.02em; color: #fff; margin-top: 6px; }
    h3 { font-size: 15px; font-weight: 700; color: #fff; }
    .lead { font-size: 17px; color: var(--text-2); max-width: 780px; margin-top: 14px; line-height: 1.6; }
    .subtext { font-size: 13px; color: var(--muted); margin-top: 6px; max-width: 780px; }

    .panel { background: var(--surface); border: 1px solid var(--border); border-radius: 14px; }
    .panel-2 { background: var(--surface-2); border: 1px solid var(--border); border-radius: 10px; }
    .p-4 { padding: 16px; }
    .p-5 { padding: 20px; }
    .p-6 { padding: 24px; }

    /* Grids */
    .grid { display: grid; gap: 16px; }
    .grid-6 { grid-template-columns: repeat(6, minmax(0, 1fr)); }
    .grid-4 { grid-template-columns: repeat(4, minmax(0, 1fr)); }
    .grid-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
    .grid-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .col-span-2 { grid-column: span 2; }

    /* Pills */
    .pill {
      display: inline-flex; align-items: center; gap: 6px;
      padding: 3px 9px; border-radius: 999px; font-size: 11px; font-weight: 600; white-space: nowrap;
    }
    .pill-ready { background: rgba(16, 185, 129, 0.14); color: var(--emerald-soft); border: 1px solid rgba(16, 185, 129, 0.28); }
    .pill-limit { background: rgba(245, 158, 11, 0.14); color: var(--amber-soft); border: 1px solid rgba(245, 158, 11, 0.28); }
    .pill-partner { background: rgba(139, 92, 246, 0.15); color: var(--purple-soft); border: 1px solid rgba(139, 92, 246, 0.30); }
    .pill-not { background: rgba(244, 63, 94, 0.14); color: var(--rose-soft); border: 1px solid rgba(244, 63, 94, 0.28); }
    .pill-neutral { background: rgba(148, 163, 184, 0.12); color: var(--text-2); border: 1px solid rgba(148, 163, 184, 0.22); }
    .pill-indigo { background: rgba(99, 102, 241, 0.16); color: var(--indigo-soft); border: 1px solid rgba(99, 102, 241, 0.35); }
    .pill-sky { background: rgba(56, 189, 248, 0.14); color: var(--sky); border: 1px solid rgba(56, 189, 248, 0.28); }

    /* KPI Cards */
    .kpi-label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted); font-weight: 600; }
    .kpi-value { font-size: 24px; font-weight: 800; color: #fff; margin-top: 6px; }
    .kpi-sub { font-size: 11px; color: var(--muted); margin-top: 4px; }

    /* Tables */
    .table-wrap { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; font-size: 12px; text-align: left; }
    thead { background: #0B0E16; color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; }
    th, td { padding: 11px 14px; border-bottom: 1px solid rgba(255, 255, 255, 0.05); vertical-align: top; }
    .num { text-align: right; font-variant-numeric: tabular-nums; }
    tbody tr.clickable { cursor: pointer; transition: background 0.12s ease; }
    tbody tr.clickable:hover { background: rgba(255, 255, 255, 0.03); }

    /* Controls */
    .filter-bar { display: grid; grid-template-columns: 2fr repeat(5, 1fr); gap: 10px; }
    input, select {
      width: 100%; background: #0B0E16; border: 1px solid var(--border-strong); color: var(--text);
      padding: 8px 10px; border-radius: 8px; font-size: 12px; font-family: inherit;
    }
    input:focus, select:focus { outline: none; border-color: var(--indigo); }
    .tab-group { display: inline-flex; background: #0B0E16; border: 1px solid var(--border); border-radius: 8px; padding: 3px; gap: 2px; }
    .tab-btn {
      background: transparent; color: var(--muted); border: none; padding: 5px 10px;
      font-size: 11px; font-weight: 600; border-radius: 6px; cursor: pointer;
    }
    .tab-btn.active { background: var(--indigo); color: #fff; }

    /* Provenance Banner */
    .banner {
      display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 12px;
      padding: 12px 16px; border-radius: 12px;
      background: rgba(245, 158, 11, 0.08); border: 1px solid rgba(245, 158, 11, 0.25);
      font-size: 12px; color: var(--text-2);
    }
    pre {
      background: #0B0E16; border: 1px solid var(--border); border-radius: 10px;
      padding: 14px; font-size: 11.5px; color: var(--indigo-soft); overflow-x: auto; line-height: 1.6;
    }
    .legend { display: flex; flex-wrap: wrap; gap: 14px; font-size: 11px; color: var(--muted); margin-top: 10px; }
    .legend-item { display: inline-flex; align-items: center; gap: 6px; }
    .swatch { width: 10px; height: 10px; border-radius: 3px; display: inline-block; }

    .tooltip-box {
      min-height: 44px; padding: 10px 14px; border-radius: 10px;
      background: #0B0E16; border: 1px solid var(--border-strong);
      font-size: 12px; color: var(--text-2); display: flex; align-items: center; justify-content: space-between; gap: 12px;
    }
    ul.bullets { padding-left: 18px; display: flex; flex-direction: column; gap: 8px; font-size: 13px; color: var(--text-2); }
    .tag-cloud { display: flex; flex-wrap: wrap; gap: 7px; margin-top: 10px; }
    .tag-chip { background: var(--surface-2); border: 1px solid var(--border); padding: 4px 9px; border-radius: 7px; font-size: 11.5px; color: var(--text-2); }
    footer { border-top: 1px solid var(--border); padding: 28px 0; text-align: center; font-size: 12px; color: var(--dim); }

    @media (max-width: 1024px) {
      .grid-6 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
      .grid-4, .grid-3, .grid-2 { grid-template-columns: 1fr; }
      .col-span-2 { grid-column: span 1; }
      .filter-bar { grid-template-columns: 1fr 1fr; }
      .nav-links { display: none; }
    }
    @media (max-width: 600px) {
      .grid-6 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .filter-bar { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <div class="container nav-bar">
      <div class="brand">
        <div class="brand-icon mono">C</div>
        <div>
          <div class="brand-title">Composio AI Product Ops</div>
          <div class="brand-sub mono">100-App Agent-Readiness Study &middot; Offline Self-Contained</div>
        </div>
      </div>
      <nav class="nav-links">
        <a href="#findings">Findings</a>
        <a href="#ecosystem">Ecosystem</a>
        <a href="#matrix">Matrix</a>
        <a href="#explorer">100-App Explorer</a>
        <a href="#architecture">Architecture</a>
        <a href="#verification">Verification</a>
        <a href="#recommendations">Roadmap</a>
        <a href="#reproducibility">Reproducibility</a>
      </nav>
      <a href="#explorer" class="btn-primary">Inspect 100 Apps</a>
    </div>
  </header>

  <main class="container">
    <!-- 1. HERO -->
    <section id="hero">
      <span class="pill pill-indigo mono">Executed {{ findings.generated_at }} &middot; 10 Categories &middot; Zero CDN Dependencies</span>
      <h1>Beyond API Discovery: Mapping the Agent-Ready Software Ecosystem</h1>
      <p class="lead">
        A 100-application research pipeline for identifying integration feasibility, developer access friction, and MCP opportunities — strictly separating technical API maturity from commercial credential accessibility.
      </p>

      <div class="banner" style="margin-top: 20px;">
        <div>
          <strong style="color: var(--amber-soft);">Execution Provenance:</strong>
          Pipeline mode: <span class="mono">{{ findings.execution_metadata.pipeline_mode }}</span> &middot;
          Composio live SDK: <span class="mono">{{ findings.execution_metadata.composio_provider.execution_status }}</span>
          ({{ findings.execution_metadata.composio_provider.reason }})
        </div>
        <div class="mono" style="font-size: 11px;">
          Confidence: {{ findings.overview.high_confidence_count }} High &middot; {{ findings.overview.medium_confidence_count }} Medium &middot; {{ findings.overview.low_confidence_count }} Low
        </div>
      </div>

      <div class="grid grid-6" style="margin-top: 18px;">
        <div class="panel p-4">
          <div class="kpi-label">Research Scope</div>
          <div class="kpi-value mono">{{ findings.overview.total_apps_in_scope }}</div>
          <div class="kpi-sub">10 categories &times; 10 apps</div>
        </div>
        <div class="panel p-4">
          <div class="kpi-label">Researched</div>
          <div class="kpi-value mono" style="color: var(--emerald-soft);">{{ findings.overview.apps_researched }}/100</div>
          <div class="kpi-sub">Zero dropped apps</div>
        </div>
        <div class="panel p-4">
          <div class="kpi-label">Evidence Coverage</div>
          <div class="kpi-value mono" style="color: var(--indigo-soft);">{{ findings.accuracy_metrics.evidence_coverage_pct }}%</div>
          <div class="kpi-sub">{{ findings.overview.total_evidence_records }} primary URLs</div>
        </div>
        <div class="panel p-4">
          <div class="kpi-label">MCP Ecosystem</div>
          <div class="kpi-value mono" style="color: var(--sky);">{{ findings.overview.official_mcp_count }} + {{ findings.overview.vendor_mcp_count }}</div>
          <div class="kpi-sub">Official + Vendor-supported</div>
        </div>
        <div class="panel p-4">
          <div class="kpi-label">Audited Accuracy</div>
          <div class="kpi-value mono" style="color: var(--amber-soft);">{{ findings.accuracy_metrics.final_audited.accuracy_pct }}%</div>
          <div class="kpi-sub">Pass 1: {{ findings.accuracy_metrics.first_pass.accuracy_pct }}% (n=140)</div>
        </div>
        <div class="panel p-4">
          <div class="kpi-label">Needs Review</div>
          <div class="kpi-value mono" style="color: var(--rose-soft);">{{ findings.overview.needs_human_review_count }}</div>
          <div class="kpi-sub">Unresolved / flagged</div>
        </div>
      </div>
    </section>

    <!-- 2. EXECUTIVE FINDINGS -->
    <section id="findings">
      <div class="eyebrow mono">01 / Executive Findings</div>
      <h2>Five Data-Backed Patterns Shaping Agent Integration Strategy</h2>
      <p class="subtext">All counts and percentages are computed programmatically by Pandas from <span class="mono">data/researched_apps.json</span>.</p>

      <div class="grid grid-3" style="margin-top: 20px;">
        {% for ins in findings.executive_insights %}
        <article class="panel p-5 {% if loop.index == 1 %}col-span-2{% endif %}" style="display:flex; flex-direction:column; justify-content:space-between; gap:14px;">
          <div>
            <div style="display:flex; align-items:center; justify-content:space-between; gap:8px; flex-wrap:wrap; margin-bottom:10px;">
              <span class="mono" style="font-size:11px; color:var(--muted); font-weight:600;">INSIGHT 0{{ loop.index }}</span>
              <span class="pill pill-indigo mono">{{ ins.metric }}</span>
            </div>
            <h3>{{ ins.title }}</h3>
            <p style="font-size:13px; color:var(--text-2); margin-top:8px;">{{ ins.summary }}</p>
          </div>
          <div style="padding-top:12px; border-top:1px solid var(--border);">
            <div style="font-size:11px; font-weight:700; text-transform:uppercase; color:var(--emerald-soft); margin-bottom:4px;">Composio Implication</div>
            <p style="font-size:12px; color:var(--muted);">{{ ins.business_implication }}</p>
          </div>
        </article>
        {% endfor %}
      </div>
    </section>

    <!-- 3. ECOSYSTEM MAP -->
    <section id="ecosystem">
      <div class="eyebrow mono">02 / Ecosystem Map</div>
      <h2>Category Readiness, Credential Access &amp; MCP Maturity</h2>

      <div class="grid grid-2" style="margin-top: 20px;">
        <div class="panel p-5">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
            <h3>Buildability by Category (n = 100)</h3>
            <span class="mono" style="font-size:11px; color:var(--muted);">10 apps / category</span>
          </div>
          <div id="categoryChartContainer"></div>
          <div class="legend">
            <span class="legend-item"><span class="swatch" style="background:var(--emerald);"></span>Ready to build</span>
            <span class="legend-item"><span class="swatch" style="background:var(--amber);"></span>Limitations</span>
            <span class="legend-item"><span class="swatch" style="background:var(--purple);"></span>Partner/Enterprise</span>
            <span class="legend-item"><span class="swatch" style="background:var(--rose);"></span>Not practical</span>
          </div>
        </div>

        <div class="panel p-5">
          <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:12px;">
            <h3>Ecosystem Distributions</h3>
            <div class="tab-group">
              <button type="button" id="btnChartAccess" class="tab-btn active">Credential Access</button>
              <button type="button" id="btnChartAuth" class="tab-btn">Auth Methods</button>
              <button type="button" id="btnChartMcp" class="tab-btn">MCP Status</button>
            </div>
          </div>
          <div id="distributionChartContainer"></div>
        </div>
      </div>

      <div class="panel" style="margin-top: 18px; overflow: hidden;">
        <div style="padding:14px 18px; border-bottom:1px solid var(--border); display:flex; justify-content:space-between; align-items:center;">
          <h3>Category-Level Quantitative Scorecard</h3>
          <span class="mono" style="font-size:11px; color:var(--muted);">Exact canonical order</span>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Category</th>
                <th class="num">Ready</th>
                <th class="num">Limitations</th>
                <th class="num">Partner/Ent</th>
                <th class="num">Not Practical</th>
                <th class="num">Free Self-Serve</th>
                <th class="num">OAuth 2.0</th>
                <th class="num">Official MCP</th>
                <th class="num">Vendor MCP</th>
                <th class="num">Composio</th>
              </tr>
            </thead>
            <tbody>
              {% for c in findings.category_breakdown %}
              <tr>
                <td style="font-weight:600; color:#fff;">{{ c.category }}</td>
                <td class="num mono" style="color:var(--emerald-soft); font-weight:700;">{{ c.ready_to_build }}</td>
                <td class="num mono" style="color:var(--amber-soft);">{{ c.buildable_with_limitations }}</td>
                <td class="num mono" style="color:var(--purple-soft);">{{ c.partner_enterprise }}</td>
                <td class="num mono" style="color:var(--rose-soft);">{{ c.not_practical }}</td>
                <td class="num mono">{{ c.free_self_service }}/10</td>
                <td class="num mono">{{ c.oauth_count }}/10</td>
                <td class="num mono" style="color:var(--sky);">{{ c.official_mcp }}/10</td>
                <td class="num mono">{{ c.vendor_mcp }}/10</td>
                <td class="num mono" style="color:var(--indigo-soft); font-weight:700;">{{ c.composio_integrated }}/10</td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- 4. INTEGRATION OPPORTUNITY MATRIX -->
    <section id="matrix">
      <div class="eyebrow mono">03 / Integration Opportunity Matrix</div>
      <h2>Developer Credential Accessibility vs. API &amp; MCP Maturity (All 100 Apps)</h2>

      <div class="panel p-5" style="margin-top: 18px; display:flex; flex-direction:column; gap:14px;">
        <div class="grid grid-4">
          <div class="panel-2 p-4" style="border-left: 3px solid var(--emerald);">
            <div style="font-size:12px; font-weight:700; color:var(--emerald-soft);">Top-Right: Quick Wins</div>
            <div style="font-size:11px; color:var(--muted); margin-top:3px;">High API maturity + Free/Trial self-service credentials.</div>
          </div>
          <div class="panel-2 p-4" style="border-left: 3px solid var(--amber);">
            <div style="font-size:12px; font-weight:700; color:var(--amber-soft);">Top-Left: Conditional / Partner</div>
            <div style="font-size:11px; color:var(--muted); margin-top:3px;">Rich APIs gated by paid plans, app review, KYB, or enterprise contracts.</div>
          </div>
          <div class="panel-2 p-4" style="border-left: 3px solid var(--sky);">
            <div style="font-size:12px; font-weight:700; color:var(--sky);">Bottom-Right: Narrow Self-Serve</div>
            <div style="font-size:11px; color:var(--muted); margin-top:3px;">Accessible credentials, narrow REST or CLI/SDK-only surface.</div>
          </div>
          <div class="panel-2 p-4" style="border-left: 3px solid var(--rose);">
            <div style="font-size:12px; font-weight:700; color:var(--rose-soft);">Bottom-Left: High Friction</div>
            <div style="font-size:11px; color:var(--muted); margin-top:3px;">Sparse/unclear API docs or enterprise-gated narrow surfaces.</div>
          </div>
        </div>

        <div id="matrixTooltip" class="tooltip-box">
          <span>Hover or click any point on the scatter plot below to inspect its exact accessibility &amp; API maturity profile.</span>
          <span class="mono" style="font-size:11px; color:var(--muted);">n = 100 plotted</span>
        </div>
        <div id="matrixChartContainer" style="overflow-x:auto;"></div>
      </div>
    </section>

    <!-- 5. INTERACTIVE 100-APP EXPLORER -->
    <section id="explorer">
      <div style="display:flex; flex-wrap:wrap; align-items:flex-end; justify-content:space-between; gap:10px;">
        <div>
          <div class="eyebrow mono">04 / Interactive 100-App Explorer</div>
          <h2>Inspect Every Application, Confidence Level &amp; Primary Evidence Trail</h2>
        </div>
        <div id="explorerCount" class="mono" style="font-size:12px; color:var(--muted);">Showing 100 of 100 applications</div>
      </div>

      <div class="panel p-4 filter-bar" style="margin-top: 16px;">
        <input id="filterSearch" type="text" placeholder="Search app name, blocker, MCP, docs..." />
        <select id="filterCategory">
          <option value="">All 10 Categories</option>
          {% for c in findings.category_breakdown %}
          <option value="{{ c.category }}">{{ c.category }}</option>
          {% endfor %}
        </select>
        <select id="filterBuildability">
          <option value="">All Buildability</option>
          <option value="Ready to build">Ready to build</option>
          <option value="Buildable with limitations">Buildable with limitations</option>
          <option value="Partner / enterprise dependent">Partner / enterprise dependent</option>
          <option value="Not currently practical">Not currently practical</option>
        </select>
        <select id="filterAuth">
          <option value="">All Auth Methods</option>
          <option value="OAuth 2.0">OAuth 2.0</option>
          <option value="API key">API key</option>
          <option value="Personal access token">Personal access token</option>
          <option value="Basic authentication">Basic authentication</option>
          <option value="JWT / service account">JWT / service account</option>
          <option value="Unknown / needs verification">Unknown / needs verification</option>
        </select>
        <select id="filterVerification">
          <option value="">All Verification States</option>
          <option value="Human audited">Human audited</option>
          <option value="Cross-checked">Cross-checked</option>
          <option value="Needs human review">Needs human review</option>
          <option value="Medium_or_Low">Medium / Low Confidence</option>
        </select>
        <select id="filterComposio">
          <option value="">Composio: All</option>
          <option value="yes">Verified Composio Toolkit</option>
          <option value="no">Not in Composio</option>
        </select>
      </div>

      <div class="panel" style="margin-top: 14px; overflow:hidden;">
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th style="width:48px;">#</th>
                <th>Application</th>
                <th>Auth &amp; Access</th>
                <th>API Surface</th>
                <th>MCP / Composio</th>
                <th>Buildability</th>
                <th>Verification</th>
                <th class="num">Evidence</th>
              </tr>
            </thead>
            <tbody id="explorerBody"></tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- 6. AGENT ARCHITECTURE -->
    <section id="architecture">
      <div class="eyebrow mono">05 / Agent Architecture</div>
      <h2>Modular Multi-Pass Pipeline &amp; Real Execution Trace</h2>

      <div class="panel p-5" style="margin-top: 18px; overflow-x:auto;">
        <svg viewBox="0 0 1120 140" style="width:100%; min-width:780px; height:auto;" role="img" aria-label="Agent pipeline architecture">
          <defs>
            <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M 0 1 L 10 5 L 0 9 z" fill="#6366F1"/>
            </marker>
          </defs>
          {% set stages = [
            ("1. Registry", "100 Canonical Apps", 10, "#94A3B8"),
            ("2. Discovery", "Search + HTTP Crawl", 150, "#38BDF8"),
            ("3. Research", "Pydantic / Gemini", 290, "#818CF8"),
            ("4. Evidence", "Primary URL Audit", 430, "#34D399"),
            ("5. Verify", "Cross-Check Rules", 570, "#FBBF24"),
            ("6. Human QA", "20-App Audit Queue", 710, "#F472B6"),
            ("7. Analytics", "Pandas Findings", 850, "#60A5FA"),
            ("8. Report", "Offline HTML", 990, "#A78BFA")
          ] %}
          {% for title, sub, x, stroke in stages %}
          <rect x="{{ x }}" y="24" width="118" height="74" rx="10" fill="#111622" stroke="{{ stroke }}" stroke-width="1.4" />
          <text x="{{ x + 59 }}" y="56" text-anchor="middle" fill="#F8FAFC" font-size="12" font-weight="700">{{ title }}</text>
          <text x="{{ x + 59 }}" y="76" text-anchor="middle" fill="#94A3B8" font-size="10" font-family="monospace">{{ sub }}</text>
          {% if not loop.last %}
          <line x1="{{ x + 118 }}" y1="61" x2="{{ x + 148 }}" y2="61" stroke="#6366F1" stroke-width="1.6" marker-end="url(#arrow)" />
          {% endif %}
          {% endfor %}
          <text x="560" y="124" text-anchor="middle" fill="#64748B" font-size="11" font-family="monospace">SQLite Checkpointing (data/checkpoints.sqlite) &middot; Retrieval Log (data/retrieval_log.jsonl) &middot; Empty-Evidence Guardrail</text>
        </svg>
      </div>

      <div class="panel p-5" style="margin-top: 16px;">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:14px;">
          <h3>Real Execution Trace: App #49 &mdash; Amazon Selling Partner (Ecommerce)</h3>
          <span class="pill pill-partner mono">Pass 1 Over-Claim Caught &amp; Corrected</span>
        </div>
        <div class="grid grid-4">
          <div class="panel-2 p-4">
            <div class="mono" style="font-size:11px; font-weight:700; color:var(--indigo-soft); margin-bottom:6px;">PASS 1 &middot; Research</div>
            <p style="font-size:12px; color:var(--text-2);">Discovered SP-API LWA OAuth 2.0 &amp; developer vetting, but over-claimed <span class="mono">mcp_status="Official"</span> (from local sample repo) and <span class="mono">composio_integration=true</span> (from generic category page).</p>
          </div>
          <div class="panel-2 p-4">
            <div class="mono" style="font-size:11px; font-weight:700; color:var(--emerald-soft); margin-bottom:6px;">PASS 2 &middot; Evidence Audit</div>
            <p style="font-size:12px; color:var(--text-2);">Dedicated-toolkit rule rejected <span class="mono">composio.dev/category/e-commerce</span> (missing <span class="mono">/toolkits/&lt;slug&gt;</span> path), flagging the record for review.</p>
          </div>
          <div class="panel-2 p-4">
            <div class="mono" style="font-size:11px; font-weight:700; color:var(--amber-soft); margin-bottom:6px;">PASS 3 &middot; Cross-Check</div>
            <p style="font-size:12px; color:var(--text-2);">Confirmed commercial gating (<span class="mono">Admin approval required</span> + <span class="mono">Partner / enterprise dependent</span>) separated from Large REST API docs.</p>
          </div>
          <div class="panel-2 p-4" style="border-color: rgba(139,92,246,0.35);">
            <div class="mono" style="font-size:11px; font-weight:700; color:var(--purple-soft); margin-bottom:6px;">PASS 4 &middot; Human Audit Fix</div>
            <p style="font-size:12px; color:var(--text-2);">Verified primary docs: reclassified MCP to <span class="mono">Vendor-supported</span>, set <span class="mono">composio_integration=false</span>, and fixed canonical URL to <span class="mono">developer-docs.amazon.com/sp-api/</span>.</p>
          </div>
        </div>
      </div>
    </section>

    <!-- 7. VERIFICATION & QUALITY -->
    <section id="verification">
      <div class="eyebrow mono">06 / Verification &amp; Quality</div>
      <h2>Strictly Reconciled Field-Level Accuracy (Computed Directly from Field Results)</h2>
      <p class="subtext">{{ findings.accuracy_metrics.evaluation_denominator_definition }}</p>

      <!-- Mathematical Reconciliation Table -->
      <div class="panel" style="margin-top: 18px; overflow:hidden;">
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Evaluation Stage</th>
                <th class="num">Correct (1 pt)</th>
                <th class="num">Partially Correct (0 pt)</th>
                <th class="num">Incorrect (0 pt)</th>
                <th class="num">Unresolved / Unknown (0 pt)</th>
                <th class="num">Denominator</th>
                <th class="num">Strict Accuracy</th>
              </tr>
            </thead>
            <tbody>
              {% for st in [findings.accuracy_metrics.first_pass, findings.accuracy_metrics.post_validation, findings.accuracy_metrics.final_audited] %}
              <tr>
                <td style="font-weight:700; color:#fff;">{{ st.stage | replace('_', ' ') | title }}</td>
                <td class="num mono" style="color:var(--emerald-soft); font-weight:700;">{{ st.correct }}</td>
                <td class="num mono" style="color:var(--amber-soft);">{{ st.partially_correct }}</td>
                <td class="num mono" style="color:var(--rose-soft);">{{ st.incorrect }}</td>
                <td class="num mono" style="color:var(--purple-soft);">{{ st.unresolved }}</td>
                <td class="num mono">{{ st.total_evaluated_fields }}</td>
                <td class="num mono" style="color:#fff; font-weight:800;">{{ st.accuracy_pct }}%</td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>

      <div class="grid grid-3" style="margin-top: 14px;">
        <div class="panel p-4">
          <div class="kpi-label">Unknown / Unresolved Rate (All 100 Apps)</div>
          <div class="kpi-value mono" style="color:var(--amber-soft);">{{ findings.accuracy_metrics.unknown_unresolved_rate_pct }}%</div>
          <div class="kpi-sub">3 unresolved fields across 700 total (Sherlock, Paygent Connect)</div>
        </div>
        <div class="panel p-4">
          <div class="kpi-label">False Positives Caught</div>
          <div class="kpi-value mono" style="color:var(--rose-soft);">{{ findings.accuracy_metrics.false_positives }}</div>
          <div class="kpi-sub">Pylon buildability, Amazon MCP &amp; Composio, Fanbasis heuristic</div>
        </div>
        <div class="panel p-4">
          <div class="kpi-label">False Negatives Caught</div>
          <div class="kpi-value mono" style="color:var(--rose-soft);">{{ findings.accuracy_metrics.false_negatives }}</div>
          <div class="kpi-sub">Amazon SP-API non-canonical TLD passed regex check</div>
        </div>
      </div>

      <!-- 20-App Audit Log -->
      <div class="panel" style="margin-top: 18px; overflow:hidden;">
        <div style="padding:14px 18px; border-bottom:1px solid var(--border); display:flex; justify-content:space-between; align-items:center;">
          <h3>Pass 4 Stratified Human Audit Log (20 Apps &times; 7 Fields = 140 Evaluated Fields)</h3>
          <span class="mono" style="font-size:11px; color:var(--muted);">2 apps per category</span>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>App</th>
                <th>Category</th>
                <th>Overall Verdict</th>
                <th>Discrepancy / Audit Finding</th>
                <th>Official Docs Checked</th>
              </tr>
            </thead>
            <tbody>
              {% for a in audit_data.entries %}
              <tr>
                <td style="font-weight:700; color:#fff; white-space:nowrap;">#{{ a.app_id }} {{ a.app_name }}</td>
                <td style="color:var(--muted); white-space:nowrap;">{{ a.category }}</td>
                <td style="white-space:nowrap;">
                  {% if a.overall_verdict == 'Correct' %}
                  <span class="pill pill-ready">Correct</span>
                  {% elif a.overall_verdict == 'Unresolved' %}
                  <span class="pill pill-not">Unresolved</span>
                  {% else %}
                  <span class="pill pill-limit">{{ a.overall_verdict }}</span>
                  {% endif %}
                </td>
                <td style="color:var(--text-2); max-width:440px;">{{ a.discrepancy_summary }}</td>
                <td>
                  {% for u in a.official_docs_checked[:2] %}
                  <div style="margin-bottom:3px;"><a href="{{ u }}" target="_blank" rel="noopener" class="mono" style="font-size:11px; word-break:break-all;">{{ u | replace('https://', '') | truncate(48) }}</a></div>
                  {% endfor %}
                </td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- 8. HUMAN IN THE LOOP -->
    <section id="hitl">
      <div class="eyebrow mono">07 / Human in the Loop</div>
      <h2>What Automated Well vs. Where Human Judgment Was Required</h2>
      <div class="grid grid-2" style="margin-top: 18px;">
        <div class="panel p-5">
          <h3 style="color:var(--emerald-soft); margin-bottom:10px;">Automated by the Pipeline</h3>
          <ul class="bullets">
            <li>Parallel primary-source discovery and structured logging of {{ findings.overview.total_evidence_records }} URLs across all 100 apps.</li>
            <li>Strict Pydantic enum validation that caught <strong style="color:#fff;">Mermaid CLI</strong>'s empty auth array in Pass 2.</li>
            <li>Evidence rules flagging generic Composio category pages (<strong style="color:#fff;">Amazon SP-API</strong>), third-party domains (<strong style="color:#fff;">Gladly</strong>'s removed G2 citation), and unsupported High confidence scores (10 apps downgraded to Medium).</li>
            <li>Programmatic Pandas aggregation and zero-CDN HTML report generation.</li>
          </ul>
        </div>
        <div class="panel p-5">
          <h3 style="color:var(--amber-soft); margin-bottom:10px;">Required Human Product Ops Judgment</h3>
          <ul class="bullets">
            <li><strong style="color:#fff;">Commercial vs. technical boundary:</strong> Reclassifying <strong style="color:#fff;">Pylon</strong> to Partner/enterprise-dependent after confirming sales-assisted trials.</li>
            <li><strong style="color:#fff;">MCP tier distinction:</strong> Separating GA Official MCP servers from Vendor-supported local/beta samples (<strong style="color:#fff;">Amazon SP-API</strong>, <strong style="color:#fff;">Twilio</strong>).</li>
            <li><strong style="color:#fff;">Ambiguous &amp; sparse products:</strong> Leaving <strong style="color:#fff;">Sherlock</strong> and <strong style="color:#fff;">Paygent Connect</strong> explicitly unresolved rather than guessing.</li>
            <li><strong style="color:#fff;">2026 platform transitions:</strong> Verifying <strong style="color:#fff;">Coda &rarr; Superhuman Docs</strong>, <strong style="color:#fff;">FanBasis &rarr; Commas</strong>, <strong style="color:#fff;">MongoDB Atlas Data API EOL</strong>, and <strong style="color:#fff;">Xero's March 2026</strong> egress tiers.</li>
          </ul>
        </div>
      </div>
    </section>

    <!-- 9. PRODUCT RECOMMENDATIONS -->
    <section id="recommendations">
      <div class="eyebrow mono">08 / Product Recommendations</div>
      <h2>Prioritized Integration Roadmap for Composio</h2>
      <div class="grid grid-2" style="margin-top: 18px;">
        <div class="panel p-5" style="border-top: 2px solid var(--emerald);">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <h3>1. White-Space Quick Wins (Build First)</h3>
            <span class="pill pill-ready mono">{{ findings.strategic_buckets.white_space_quick_wins | length }} apps</span>
          </div>
          <p class="subtext">Ready-to-build platforms with Medium/Large APIs and Free/Trial access lacking a dedicated Composio toolkit:</p>
          <div class="tag-cloud">
            {% for app in findings.strategic_buckets.white_space_quick_wins %}
            <span class="tag-chip"><strong style="color:var(--emerald-soft);">#{{ app.id }}</strong> {{ app.name }}</span>
            {% endfor %}
          </div>
        </div>

        <div class="panel p-5" style="border-top: 2px solid var(--amber);">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <h3>2. Conditional Wins (Managed Auth Moat)</h3>
            <span class="pill pill-limit mono">{{ findings.strategic_buckets.conditional_wins | length }} apps</span>
          </div>
          <p class="subtext">Strong APIs gated by paid plans, App Review, or read-only vendor MCPs where managed OAuth + write parity wins:</p>
          <div class="tag-cloud">
            {% for app in findings.strategic_buckets.conditional_wins[:14] %}
            <span class="tag-chip">{{ app.name }}</span>
            {% endfor %}
            {% if findings.strategic_buckets.conditional_wins | length > 14 %}
            <span class="tag-chip mono">+{{ (findings.strategic_buckets.conditional_wins | length) - 14 }} more</span>
            {% endif %}
          </div>
        </div>

        <div class="panel p-5" style="border-top: 2px solid var(--purple);">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <h3>3. Partnership &amp; Enterprise Outreach</h3>
            <span class="pill pill-partner mono">{{ findings.strategic_buckets.partnership_opportunities | length }} apps</span>
          </div>
          <p class="subtext">High-value B2B/Fintech/Enterprise systems requiring partner programs, KYB, or customer-provisioned tenants:</p>
          <div class="tag-cloud">
            {% for app in findings.strategic_buckets.partnership_opportunities %}
            <span class="tag-chip" style="color:var(--purple-soft);">{{ app.name }}</span>
            {% endfor %}
          </div>
        </div>

        <div class="panel p-5" style="border-top: 2px solid var(--rose);">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <h3>4. Difficult / Non-Standard Surfaces</h3>
            <span class="pill pill-not mono">{{ findings.strategic_buckets.difficult_integrations | length }} apps</span>
          </div>
          <p class="subtext">CLI-only tools, unofficial scraping libraries, or sparsely documented APIs requiring sandboxes or vendor clarification:</p>
          <div class="tag-cloud">
            {% for app in findings.strategic_buckets.difficult_integrations %}
            <span class="tag-chip" style="color:var(--rose-soft);">{{ app.name }} ({{ app.api_availability }})</span>
            {% endfor %}
          </div>
        </div>
      </div>
    </section>

    <!-- 10. REPRODUCIBILITY -->
    <section id="reproducibility">
      <div class="eyebrow mono">09 / Reproducibility &amp; Known Limitations</div>
      <h2>Executable Repository, CLI Commands &amp; Honest Disclosures</h2>
      <div class="grid grid-2" style="margin-top: 18px;">
        <div class="panel p-5">
          <h3 style="margin-bottom:10px;">Run Locally (Python 3.11+)</h3>
          <pre class="mono"># 1. Install dependencies
pip install -r requirements.txt

# 2. Deterministic dataset replay (validation + analytics + HTML)
python3 -m src.pipeline --mode replay --reset-checkpoints

# 3. Live web-crawl + Gemini synthesis (requires GEMINI_API_KEY + search/internet)
cp .env.example .env &amp;&amp; python3 -m src.pipeline --mode live --limit 5

# 4. Run full automated unit test suite
python3 -m unittest discover -s tests -v</pre>
        </div>
        <div class="panel p-5">
          <h3 style="margin-bottom:10px;">Honest Limitations &amp; Execution Status</h3>
          <ul class="bullets">
            <li><strong style="color:#fff;">Deterministic Replay vs. Live Crawl:</strong> Replay mode deterministically replays <span class="mono">data/researched_apps.json</span> and logs every source to <span class="mono">data/retrieval_log.jsonl</span>. Live mode uses real search providers (<span class="mono">Serper</span> / <span class="mono">Google CSE</span> / <span class="mono">DuckDuckGo</span>) + seed official URLs and aborts with <span class="mono">EmptyEvidenceBundleError</span> if zero pages are verified.</li>
            <li><strong style="color:#fff;">Composio SDK Status:</strong> Explicitly labeled <span class="mono">{{ findings.execution_metadata.composio_provider.execution_status }}</span> because no <span class="mono">COMPOSIO_API_KEY</span> or outbound VM network access was available to execute a live tool call.</li>
            <li><strong style="color:#fff;">Confidence Calibration:</strong> 10 apps with only 1 fully verified source were downgraded from High to Medium confidence; 2 apps (<span class="mono">Sherlock</span>, <span class="mono">Paygent Connect</span>) remain explicitly unresolved.</li>
          </ul>
        </div>
      </div>
    </section>
  </main>

  <footer class="mono">
    composio-agent-readiness-research &middot; Self-Contained Offline HTML Case Study &middot; Updated {{ findings.generated_at }}
  </footer>

  <script>
    const APPS = {{ apps_json | safe }};
    const FINDINGS = {{ findings_json | safe }};

    function escapeHtml(str) {
      return String(str == null ? '' : str).replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
    }

    // 1. Pure-SVG Category Buildability Stacked Bar Chart
    function renderCategoryChart() {
      const cats = FINDINGS.category_breakdown;
      const rowH = 30, labelW = 165, barW = 320, padTop = 10, padRight = 30;
      const height = padTop + cats.length * rowH + 10;
      const width = labelW + barW + padRight;
      const colors = { ready: '#10B981', limit: '#F59E0B', partner: '#8B5CF6', not: '#F43F5E' };

      const shortName = c => c
        .replace('Developer, Infra and Data Platforms', 'Dev, Infra & Data')
        .replace('Productivity and Project Management', 'Productivity & PM')
        .replace('Marketing, Ads, Email and Social', 'Marketing & Ads')
        .replace('Communications and Messaging', 'Comms & Messaging')
        .replace('AI, Research and Media-native', 'AI & Media-Native')
        .replace('Support and Helpdesk', 'Support & Helpdesk')
        .replace('Data, SEO and Scraping', 'Data, SEO & Scraping')
        .replace('Finance and Fintech', 'Finance & Fintech')
        .replace('CRM and Sales', 'CRM & Sales');

      let svg = `<svg viewBox="0 0 ${width} ${height}" style="width:100%;height:auto;" role="img" aria-label="Buildability by category">`;
      cats.forEach((c, i) => {
        const y = padTop + i * rowH;
        svg += `<text x="${labelW - 10}" y="${y + 15}" text-anchor="end" fill="#CBD5E1" font-size="11">${escapeHtml(shortName(c.category))}</text>`;
        let x = labelW;
        const segs = [
          [c.ready_to_build, colors.ready],
          [c.buildable_with_limitations, colors.limit],
          [c.partner_enterprise, colors.partner],
          [c.not_practical, colors.not]
        ];
        segs.forEach(([val, col]) => {
          if (val > 0) {
            const w = (val / 10) * barW;
            svg += `<rect x="${x}" y="${y + 3}" width="${Math.max(w - 1.5, 1)}" height="16" rx="3" fill="${col}"><title>${escapeHtml(c.category)}: ${val}/10</title></rect>`;
            if (w >= 20) {
              svg += `<text x="${x + w / 2}" y="${y + 15}" text-anchor="middle" fill="#080A0F" font-size="10" font-weight="700">${val}</text>`;
            }
            x += w;
          }
        });
      });
      svg += `</svg>`;
      document.getElementById('categoryChartContainer').innerHTML = svg;
    }

    // 2. Pure-SVG Switchable Distribution Bar Chart
    function renderDistChart(mode) {
      let sourceObj, color;
      if (mode === 'access') { sourceObj = FINDINGS.distributions.credential_acquisition; color = '#6366F1'; }
      else if (mode === 'auth') { sourceObj = FINDINGS.distributions.auth_methods; color = '#38BDF8'; }
      else { sourceObj = FINDINGS.distributions.mcp_status; color = '#10B981'; }

      const entries = Object.entries(sourceObj).sort((a, b) => b[1] - a[1]);
      const maxVal = Math.max(...entries.map(e => e[1]), 1);
      const rowH = 34, labelW = 190, barW = 285, padTop = 10, padRight = 40;
      const height = padTop + entries.length * rowH + 10;
      const width = labelW + barW + padRight;

      let svg = `<svg viewBox="0 0 ${width} ${height}" style="width:100%;height:auto;" role="img" aria-label="Distribution chart">`;
      entries.forEach(([label, val], i) => {
        const y = padTop + i * rowH;
        const w = (val / maxVal) * barW;
        svg += `<text x="${labelW - 10}" y="${y + 16}" text-anchor="end" fill="#CBD5E1" font-size="11">${escapeHtml(label)}</text>`;
        svg += `<rect x="${labelW}" y="${y + 4}" width="${barW}" height="16" rx="4" fill="rgba(255,255,255,0.04)" />`;
        svg += `<rect x="${labelW}" y="${y + 4}" width="${Math.max(w, 4)}" height="16" rx="4" fill="${color}" />`;
        svg += `<text x="${labelW + Math.max(w, 4) + 8}" y="${y + 16}" fill="#F1F5F9" font-size="11" font-family="monospace" font-weight="700">${val}</text>`;
      });
      svg += `</svg>`;
      document.getElementById('distributionChartContainer').innerHTML = svg;
    }

    // 3. Pure-SVG Integration Opportunity Matrix Scatter Plot (All 100 Apps)
    function renderMatrixChart() {
      const W = 920, H = 370, padL = 56, padR = 24, padT = 20, padB = 44;
      const plotW = W - padL - padR, plotH = H - padT - padB;
      const colors = {
        'Ready to build': '#10B981',
        'Buildable with limitations': '#F59E0B',
        'Partner / enterprise dependent': '#8B5CF6',
        'Not currently practical': '#F43F5E'
      };
      const sx = v => padL + (v / 100) * plotW;
      const sy = v => padT + plotH - (v / 100) * plotH;

      let svg = `<svg id="matrixSvg" viewBox="0 0 ${W} ${H}" style="width:100%;min-width:680px;height:auto;" role="img" aria-label="Opportunity matrix scatter plot">`;
      // Grid lines & quadrant dividers
      [0, 25, 50, 75, 100].forEach(t => {
        const gx = sx(t), gy = sy(t);
        const dash = t === 50 ? 'stroke-dasharray="4 4" stroke="rgba(255,255,255,0.22)"' : 'stroke="rgba(255,255,255,0.06)"';
        svg += `<line x1="${gx}" y1="${padT}" x2="${gx}" y2="${padT + plotH}" ${dash} />`;
        svg += `<line x1="${padL}" y1="${gy}" x2="${padL + plotW}" y2="${gy}" ${dash} />`;
        svg += `<text x="${gx}" y="${H - 22}" text-anchor="middle" fill="#64748B" font-size="10" font-family="monospace">${t}</text>`;
        svg += `<text x="${padL - 10}" y="${gy + 3}" text-anchor="end" fill="#64748B" font-size="10" font-family="monospace">${t}</text>`;
      });
      svg += `<text x="${padL + plotW / 2}" y="${H - 4}" text-anchor="middle" fill="#94A3B8" font-size="11">Developer Credential Accessibility (0 = Enterprise/Unclear, 100 = Free Self-Service)</text>`;
      svg += `<text x="14" y="${padT + plotH / 2}" text-anchor="middle" fill="#94A3B8" font-size="11" transform="rotate(-90 14 ${padT + plotH / 2})">API &amp; MCP Maturity</text>`;

      FINDINGS.opportunity_matrix.forEach(pt => {
        const cx = sx(pt.accessibility_score).toFixed(1);
        const cy = sy(pt.api_maturity_score).toFixed(1);
        const col = colors[pt.buildability] || '#94A3B8';
        svg += `<circle class="matrix-dot" data-app-id="${pt.id}" cx="${cx}" cy="${cy}" r="5.5" fill="${col}" fill-opacity="0.88" stroke="#080A0F" stroke-width="1.2" style="cursor:pointer;"><title>#${pt.id} ${escapeHtml(pt.name)} (${escapeHtml(pt.category)})</title></circle>`;
      });
      svg += `</svg>`;
      document.getElementById('matrixChartContainer').innerHTML = svg;

      const byId = {};
      FINDINGS.opportunity_matrix.forEach(p => { byId[p.id] = p; });
      const tooltip = document.getElementById('matrixTooltip');
      document.getElementById('matrixSvg').addEventListener('mouseover', e => {
        const dot = e.target.closest('.matrix-dot');
        if (!dot) return;
        const m = byId[Number(dot.getAttribute('data-app-id'))];
        if (!m) return;
        tooltip.innerHTML = `
          <span><strong style="color:#fff;">#${m.id} ${escapeHtml(m.name)}</strong> <span style="color:var(--muted);">(${escapeHtml(m.category)})</span> &middot; Access: <strong>${escapeHtml(m.credential_acquisition)}</strong> &middot; API: <strong>${escapeHtml(m.api_breadth)}</strong> &middot; MCP: <strong>${escapeHtml(m.mcp_status)}</strong></span>
          <span class="mono" style="font-size:11px; color:var(--indigo-soft);">Composio: ${m.composio_integration ? 'Yes' : 'No'} &middot; Conf: ${escapeHtml(m.confidence)}</span>
        `;
      });
    }

    // 4. Interactive 100-App Explorer
    const expandedIds = new Set();
    function pillClass(verdict) {
      if (verdict === 'Ready to build') return 'pill-ready';
      if (verdict === 'Buildable with limitations') return 'pill-limit';
      if (verdict === 'Partner / enterprise dependent') return 'pill-partner';
      return 'pill-not';
    }
    function verifPill(status, conf) {
      if (status === 'Needs human review' || conf === 'Low') return '<span class="pill pill-not">Needs Review</span>';
      if (status === 'Human audited') return '<span class="pill pill-ready">Human Audited</span>';
      if (conf === 'Medium') return '<span class="pill pill-limit">Partial / Med Conf</span>';
      return '<span class="pill pill-sky">Cross-Checked</span>';
    }

    function renderExplorer() {
      const q = document.getElementById('filterSearch').value.trim().toLowerCase();
      const cat = document.getElementById('filterCategory').value;
      const bld = document.getElementById('filterBuildability').value;
      const auth = document.getElementById('filterAuth').value;
      const verif = document.getElementById('filterVerification').value;
      const comp = document.getElementById('filterComposio').value;

      const filtered = APPS.filter(a => {
        if (cat && a.category !== cat) return false;
        if (bld && a.buildability !== bld) return false;
        if (auth && !a.auth_methods.includes(auth)) return false;
        if (verif === 'Medium_or_Low' && a.confidence === 'High') return false;
        if (verif && verif !== 'Medium_or_Low' && a.verification_status !== verif) return false;
        if (comp === 'yes' && !a.composio_integration) return false;
        if (comp === 'no' && a.composio_integration) return false;
        if (q) {
          const hay = `${a.id} ${a.name} ${a.category} ${a.one_line_description} ${a.primary_blocker} ${a.mcp_details}`.toLowerCase();
          if (!hay.includes(q)) return false;
        }
        return true;
      });

      document.getElementById('explorerCount').textContent = `Showing ${filtered.length} of ${APPS.length} applications`;
      const tbody = document.getElementById('explorerBody');
      if (filtered.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; padding:32px; color:var(--muted);">No applications match the active filters.</td></tr>';
        return;
      }

      const rows = [];
      filtered.forEach(a => {
        const isOpen = expandedIds.has(a.id);
        rows.push(`
          <tr class="clickable" data-toggle-id="${a.id}">
            <td class="mono" style="color:var(--muted);">${a.id}</td>
            <td>
              <div style="font-weight:700; color:#fff;">${escapeHtml(a.name)}</div>
              <div style="font-size:11px; color:var(--muted);">${escapeHtml(a.category)}</div>
            </td>
            <td>
              <div>${escapeHtml(a.auth_methods.slice(0,2).join(', '))}${a.auth_methods.length > 2 ? ' +' + (a.auth_methods.length - 2) : ''}</div>
              <div style="font-size:11px; color:var(--muted);">${escapeHtml(a.credential_acquisition)}</div>
            </td>
            <td>
              <span class="mono" style="color:#fff;">${escapeHtml(a.api_availability)}</span>
              <span style="color:var(--dim);">&middot;</span>
              <span>${escapeHtml(a.api_breadth)}</span>
            </td>
            <td>
              <div style="margin-bottom:4px;"><span class="pill pill-neutral">${escapeHtml(a.mcp_status)}</span></div>
              <div>${a.composio_integration ? '<span class="pill pill-indigo">Composio</span>' : '<span style="font-size:11px; color:var(--dim);">Not in Composio</span>'}</div>
            </td>
            <td><span class="pill ${pillClass(a.buildability)}">${escapeHtml(a.buildability)}</span></td>
            <td>
              ${verifPill(a.verification_status, a.confidence)}
              <div class="mono" style="font-size:10px; color:var(--muted); margin-top:4px;">Conf: ${escapeHtml(a.confidence)}</div>
            </td>
            <td class="num">
              <button type="button" class="mono" style="background:none; border:none; color:var(--indigo-soft); cursor:pointer; font-size:11px; font-weight:600;">${isOpen ? 'Hide' : 'Inspect'} (${a.evidence.length})</button>
            </td>
          </tr>
        `);

        if (isOpen) {
          const evLinks = a.evidence.map(e => `
            <li style="display:flex; justify-content:space-between; gap:8px; padding:6px 0; border-bottom:1px solid rgba(255,255,255,0.05);">
              <a href="${escapeHtml(e.url)}" target="_blank" rel="noopener" style="word-break:break-all;">${escapeHtml(e.title)}</a>
              <span class="mono" style="font-size:10px; color:var(--muted); white-space:nowrap;">${escapeHtml(e.source_type)} &middot; ${escapeHtml(e.source_status)}</span>
            </li>
          `).join('');
          const flagsHtml = (a.review_flags && a.review_flags.length)
            ? `<p style="font-size:11.5px; color:var(--rose-soft); margin-top:8px;"><strong>Review Flags:</strong> ${escapeHtml(a.review_flags.join(', '))}</p>`
            : '';
          rows.push(`
            <tr style="background:#0B0F18;">
              <td colspan="8" style="padding:18px 22px;">
                <div class="grid grid-3">
                  <div class="col-span-2" style="display:flex; flex-direction:column; gap:8px; font-size:12.5px; color:var(--text-2);">
                    <p><strong style="color:#fff;">Overview:</strong> ${escapeHtml(a.one_line_description)}</p>
                    <p><strong style="color:var(--amber-soft);">Primary Blocker:</strong> ${escapeHtml(a.primary_blocker)}</p>
                    <p><strong style="color:var(--sky);">API Breadth Basis:</strong> ${escapeHtml(a.api_breadth_basis)}</p>
                    <p><strong style="color:var(--indigo-soft);">MCP Details:</strong> ${escapeHtml(a.mcp_details)}</p>
                    <p><strong style="color:#fff;">Commercial Notes:</strong> ${escapeHtml(a.commercial_considerations)}</p>
                    ${flagsHtml}
                    <div class="mono" style="font-size:11px; color:var(--muted); margin-top:4px;">
                      Evidence Score: <strong style="color:#fff;">${a.evidence_score != null ? a.evidence_score : 'N/A'}</strong> &middot;
                      Status: <strong style="color:var(--emerald-soft);">${escapeHtml(a.verification_status)}</strong> &middot;
                      Researched: ${escapeHtml(a.last_researched)}
                    </div>
                  </div>
                  <div class="panel-2 p-4">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                      <strong style="font-size:12px; color:#fff;">Primary Evidence (${a.evidence.length})</strong>
                      <a href="${escapeHtml(a.developer_docs_url)}" target="_blank" rel="noopener" class="mono" style="font-size:11px;">Official Docs &rarr;</a>
                    </div>
                    <ul style="list-style:none; font-size:11px;">${evLinks}</ul>
                  </div>
                </div>
              </td>
            </tr>
          `);
        }
      });
      tbody.innerHTML = rows.join('');
    }

    // Event bindings
    renderCategoryChart();
    renderDistChart('access');
    renderMatrixChart();
    renderExplorer();

    const distButtons = { access: 'btnChartAccess', auth: 'btnChartAuth', mcp: 'btnChartMcp' };
    Object.entries(distButtons).forEach(([mode, id]) => {
      document.getElementById(id).addEventListener('click', () => {
        Object.values(distButtons).forEach(bid => document.getElementById(bid).classList.remove('active'));
        document.getElementById(id).classList.add('active');
        renderDistChart(mode);
      });
    });

    document.getElementById('explorerBody').addEventListener('click', e => {
      if (e.target.closest('a')) return;
      const row = e.target.closest('tr[data-toggle-id]');
      if (!row) return;
      const id = Number(row.getAttribute('data-toggle-id'));
      if (expandedIds.has(id)) expandedIds.delete(id); else expandedIds.add(id);
      renderExplorer();
    });

    ['filterSearch', 'filterCategory', 'filterBuildability', 'filterAuth', 'filterVerification', 'filterComposio'].forEach(id => {
      const el = document.getElementById(id);
      el.addEventListener(id === 'filterSearch' ? 'input' : 'change', renderExplorer);
    });
  </script>
</body>
</html>
"""


class ReportGenerator:
    """Renders the 100% offline self-contained HTML case study from finalized pipeline data."""

    def __init__(self) -> None:
        self.env = Environment(loader=BaseLoader(), autoescape=False)
        self.template = self.env.from_string(HTML_TEMPLATE)

    def generate(
        self,
        records: List[ResearchedAppRecord],
        findings: Dict[str, Any],
        audit_data: Dict[str, Any],
        output_path: str | Path,
    ) -> Path:
        apps_payload = [model_to_dict(r) for r in sorted(records, key=lambda x: x.id)]
        rendered = self.template.render(
            findings=findings,
            audit_data=audit_data,
            apps_json=json.dumps(apps_payload),
            findings_json=json.dumps(findings),
        )
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(rendered, encoding="utf-8")
        return out
