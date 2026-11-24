# Research & Verification Methodology

## 1. Source Priority Hierarchy
1. Official developer documentation (`official_docs`)
2. Official authentication & OAuth guides (`auth_docs`)
3. Official pricing, sandbox, and plan-gating docs (`pricing`)
4. Official GitHub repositories (`github`)
5. Official MCP registries & Composio toolkit directory (`mcp_registry`)
6. Reputable technical articles only when primary docs are insufficient (`article`)

## 2. Separating Technical Buildability from Commercial Accessibility
- **API availability** (`REST`, `GraphQL`, `Both`, `SDK-only`, `No documented public API`) and **API breadth** (`Small`, `Medium`, `Large`, `None / N/A`) measure the technical surface.
- **Credential acquisition** (`Free self-service`, `Free trial`, `Paid-plan required`, `Admin approval required`, `Partner / contact-sales gated`, `Enterprise-only`, `Unclear / not verified`) measures commercial and operational onboarding friction.
- **Buildability** synthesizes both dimensions without conflating public docs with free access.

## 3. Field-Level Accuracy Formula (Pass 4)
- **Stratified Sample**: 20 applications (2 per category across all 10 categories).
- **Evaluated Fields (7 per app)**: `auth_methods`, `credential_acquisition`, `api_availability`, `api_breadth`, `mcp_status`, `composio_integration`, `buildability`.
- **Denominator**: `20 × 7 = 140` evaluated fields.
- **Formula**: `Accuracy = Correct evaluated fields / Total evaluated fields`.
- **Strict Rule**: Fields labeled `Unknown / needs verification` or `Unclear / not verified` are **never** counted as correct.
