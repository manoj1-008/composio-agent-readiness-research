"""Strict Pydantic schemas for the 100-App Agent-Readiness Research Pipeline.

Compatible with both Pydantic v1 (1.10.x) and Pydantic v2 (2.x) with zero
deprecated `Field(regex=...)` usage.
"""
from __future__ import annotations

import json
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


def model_to_dict(model: BaseModel) -> Dict[str, Any]:
    """Version-safe Pydantic v1/v2 serialization to dict."""
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")  # type: ignore[attr-defined]
    return json.loads(model.json())


def model_to_json(model: BaseModel, indent: Optional[int] = None) -> str:
    """Version-safe Pydantic v1/v2 serialization to JSON string."""
    return json.dumps(model_to_dict(model), indent=indent)


def model_copy_deep(model: BaseModel) -> Any:
    """Version-safe Pydantic v1/v2 deep copy."""
    if hasattr(model, "model_copy"):
        return model.model_copy(deep=True)  # type: ignore[attr-defined]
    return model.copy(deep=True)


class AuthMethod(str, Enum):
    OAUTH_2 = "OAuth 2.0"
    API_KEY = "API key"
    PAT = "Personal access token"
    BASIC = "Basic authentication"
    JWT_SERVICE_ACCOUNT = "JWT / service account"
    OTHER_CUSTOM = "Other / custom authentication"
    NONE_LOCAL = "None (local CLI / no auth)"
    UNKNOWN = "Unknown / needs verification"


class CredentialAcquisition(str, Enum):
    FREE_SELF_SERVICE = "Free self-service"
    FREE_TRIAL = "Free trial"
    PAID_PLAN = "Paid-plan required"
    ADMIN_APPROVAL = "Admin approval required"
    PARTNER_SALES = "Partner / contact-sales gated"
    ENTERPRISE_ONLY = "Enterprise-only"
    UNCLEAR = "Unclear / not verified"


class ApiAvailability(str, Enum):
    REST = "REST"
    GRAPHQL = "GraphQL"
    BOTH = "Both"
    SDK_ONLY = "SDK-only"
    NO_PUBLIC_API = "No documented public API"


class ApiBreadth(str, Enum):
    SMALL = "Small"
    MEDIUM = "Medium"
    LARGE = "Large"
    NONE = "None / N/A"


class McpStatus(str, Enum):
    OFFICIAL = "Official"
    VENDOR_SUPPORTED = "Vendor-supported"
    COMMUNITY = "Community-maintained"
    COMPOSIO = "Composio integration"
    NOT_FOUND = "Not found"


class BuildabilityVerdict(str, Enum):
    READY = "Ready to build"
    LIMITATIONS = "Buildable with limitations"
    PARTNER_ENTERPRISE = "Partner / enterprise dependent"
    NOT_PRACTICAL = "Not currently practical"


class SourceType(str, Enum):
    OFFICIAL_DOCS = "official_docs"
    AUTH_DOCS = "auth_docs"
    PRICING = "pricing"
    GITHUB = "github"
    MCP_REGISTRY = "mcp_registry"
    ARTICLE = "article"


class SourceStatus(str, Enum):
    VERIFIED = "verified"
    PARTIAL = "partial"
    INACCESSIBLE = "inaccessible"


class ConfidenceLevel(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class AuditVerdict(str, Enum):
    CORRECT = "Correct"
    PARTIALLY_CORRECT = "Partially correct"
    INCORRECT = "Incorrect"
    UNRESOLVED = "Unresolved"


class EvidenceRecord(BaseModel):
    url: str = Field(..., min_length=8)
    title: str = Field(..., min_length=1)
    source_type: SourceType
    claims_supported: List[str] = Field(default_factory=list)
    retrieved_at: str = Field(..., description="ISO date YYYY-MM-DD")
    source_status: SourceStatus = SourceStatus.VERIFIED

    @validator("url")
    def validate_url(cls, value: str) -> str:
        if not (value.startswith("https://") or value.startswith("http://")):
            raise ValueError(f"Evidence URL must be http(s): {value}")
        return value


class AppRegistryEntry(BaseModel):
    id: int = Field(..., ge=1, le=100)
    name: str = Field(..., min_length=1)
    category: str = Field(..., min_length=1)
    seed_docs_url: Optional[str] = None


class ResearchedAppRecord(BaseModel):
    id: int = Field(..., ge=1, le=100)
    name: str
    category: str
    one_line_description: str
    developer_docs_url: str
    auth_methods: List[AuthMethod] = Field(..., min_items=1)
    credential_acquisition: CredentialAcquisition
    api_availability: ApiAvailability
    api_breadth: ApiBreadth
    api_breadth_basis: str
    mcp_status: McpStatus
    mcp_details: str
    composio_integration: bool
    buildability: BuildabilityVerdict
    primary_blocker: str
    commercial_considerations: str
    confidence: ConfidenceLevel
    verification_status: str
    last_researched: str
    evidence: List[EvidenceRecord] = Field(default_factory=list)
    evidence_score: Optional[float] = None
    review_flags: List[str] = Field(default_factory=list)

    @validator("developer_docs_url")
    def validate_docs_url(cls, value: str) -> str:
        if value != "None / No public developer portal" and not (
            value.startswith("https://") or value.startswith("http://")
        ):
            raise ValueError(f"Invalid developer_docs_url: {value}")
        return value


class AuditFieldResult(BaseModel):
    field_name: str
    original_value: str
    post_validation_value: str
    audited_value: str
    pass1_verdict: AuditVerdict
    pass2_verdict: AuditVerdict
    final_verdict: AuditVerdict
    note: str


class AuditSampleEntry(BaseModel):
    app_id: int
    app_name: str
    category: str
    official_docs_checked: List[str]
    overall_verdict: AuditVerdict
    field_results: List[AuditFieldResult]
    discrepancy_summary: str
    final_corrected_conclusion: str


class StageAccuracyBreakdown(BaseModel):
    stage: str
    total_evaluated_fields: int
    correct: int
    partially_correct: int
    incorrect: int
    unresolved: int
    accuracy_pct: float


class AccuracyMetrics(BaseModel):
    total_apps_in_scope: int
    apps_researched: int
    evidence_coverage_pct: float
    unknown_unresolved_rate_pct: float
    audited_sample_size: int
    evaluated_fields_per_app: int
    total_evaluated_fields: int
    first_pass: StageAccuracyBreakdown
    post_validation: StageAccuracyBreakdown
    final_audited: StageAccuracyBreakdown
    false_positives: int
    false_negatives: int
    evaluation_denominator_definition: str
    field_error_breakdown_pass1: Dict[str, int]
    field_error_breakdown_final: Dict[str, int]
