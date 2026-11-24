"""Pass 3 & Pass 4: Independent Verification Cross-Checker and Strict Accuracy Calculator.

Strict Field-Level Accuracy Rules:
- `Correct` counts as 1 correct.
- `Partially correct` counts as 0 correct (tracked separately; never rounded up).
- `Incorrect` counts as 0 correct.
- `Unresolved` (or any field whose value contains Unknown / Unclear) counts as 0 correct.
- Pass 1, Post-Validation (Pass 2+3), and Final Audited (Pass 4) accuracies are all
  computed directly from `field_results` with full mathematical reconciliation:
  correct + partially_correct + incorrect + unresolved == total_evaluated_fields.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

from src.schemas import (
    AccuracyMetrics,
    ApiAvailability,
    AuditSampleEntry,
    AuditVerdict,
    AuthMethod,
    BuildabilityVerdict,
    CredentialAcquisition,
    ResearchedAppRecord,
    StageAccuracyBreakdown,
    model_copy_deep,
)


EVALUATED_FIELDS = (
    "auth_methods",
    "credential_acquisition",
    "api_availability",
    "api_breadth",
    "mcp_status",
    "composio_integration",
    "buildability",
)


class VerificationAgent:
    """Cross-checks logical consistency across fields and computes strictly reconciled accuracy metrics."""

    def cross_check_record(self, record: ResearchedAppRecord) -> List[str]:
        warnings: List[str] = []

        if (
            record.credential_acquisition
            in (CredentialAcquisition.ENTERPRISE_ONLY, CredentialAcquisition.PARTNER_SALES)
            and record.buildability == BuildabilityVerdict.READY
        ):
            warnings.append(
                "contradiction: enterprise/partner-gated credentials marked 'Ready to build'"
            )

        if (
            record.api_availability == ApiAvailability.NO_PUBLIC_API
            and record.buildability == BuildabilityVerdict.READY
        ):
            warnings.append("contradiction: no public API marked 'Ready to build'")

        if (
            record.api_availability == ApiAvailability.NO_PUBLIC_API
            and record.api_breadth.value != "None / N/A"
        ):
            warnings.append("inconsistency: no public API should have api_breadth='None / N/A'")

        if not record.primary_blocker.strip():
            warnings.append("missing_primary_blocker_explanation")

        return warnings

    def run_pass3(
        self, records: List[ResearchedAppRecord]
    ) -> Tuple[List[ResearchedAppRecord], Dict[int, List[str]]]:
        updated: List[ResearchedAppRecord] = []
        warning_map: Dict[int, List[str]] = {}
        for rec in records:
            warnings = self.cross_check_record(rec)
            rec_copy: ResearchedAppRecord = model_copy_deep(rec)
            if warnings:
                warning_map[rec.id] = warnings
                for w in warnings:
                    if w not in rec_copy.review_flags:
                        rec_copy.review_flags.append(w)
                rec_copy.verification_status = "Needs human review"
            elif rec_copy.verification_status == "Initial pass verified" and not rec_copy.review_flags:
                rec_copy.verification_status = "Cross-checked"
            updated.append(rec_copy)
        return updated, warning_map

    @staticmethod
    def _classify_stage_verdict(verdict: AuditVerdict, value_str: str) -> AuditVerdict:
        """Enforce hard rule: Unknown / Unclear values can NEVER count as Correct."""
        lowered = value_str.lower()
        if "unknown" in lowered or "unclear" in lowered:
            return AuditVerdict.UNRESOLVED
        return verdict

    @classmethod
    def _compute_stage(
        cls,
        stage_name: str,
        audit_entries: List[AuditSampleEntry],
        verdict_attr: str,
        value_attr: str,
    ) -> Tuple[StageAccuracyBreakdown, Dict[str, int]]:
        correct = 0
        partially_correct = 0
        incorrect = 0
        unresolved = 0
        field_errors: Dict[str, int] = {f: 0 for f in EVALUATED_FIELDS}

        for entry in audit_entries:
            for fr in entry.field_results:
                raw_verdict: AuditVerdict = getattr(fr, verdict_attr)
                val_str: str = getattr(fr, value_attr)
                effective = cls._classify_stage_verdict(raw_verdict, val_str)

                if effective == AuditVerdict.CORRECT:
                    correct += 1
                elif effective == AuditVerdict.PARTIALLY_CORRECT:
                    partially_correct += 1
                    field_errors[fr.field_name] = field_errors.get(fr.field_name, 0) + 1
                elif effective == AuditVerdict.INCORRECT:
                    incorrect += 1
                    field_errors[fr.field_name] = field_errors.get(fr.field_name, 0) + 1
                else:
                    unresolved += 1
                    field_errors[fr.field_name] = field_errors.get(fr.field_name, 0) + 1

        total = correct + partially_correct + incorrect + unresolved
        expected_total = len(audit_entries) * len(EVALUATED_FIELDS)
        if total != expected_total:
            raise ValueError(
                f"Stage '{stage_name}' denominator mismatch: counted {total} fields vs expected {expected_total}"
            )

        accuracy_pct = round(100.0 * correct / max(total, 1), 1)
        return (
            StageAccuracyBreakdown(
                stage=stage_name,
                total_evaluated_fields=total,
                correct=correct,
                partially_correct=partially_correct,
                incorrect=incorrect,
                unresolved=unresolved,
                accuracy_pct=accuracy_pct,
            ),
            field_errors,
        )

    @classmethod
    def compute_accuracy_metrics(
        cls,
        all_records: List[ResearchedAppRecord],
        audit_entries: List[AuditSampleEntry],
        false_positives: int,
        false_negatives: int,
    ) -> AccuracyMetrics:
        total_apps = 100
        apps_researched = len(all_records)
        apps_with_evidence = sum(
            1 for r in all_records if any(e.source_status.value != "inaccessible" for e in r.evidence)
        )
        evidence_coverage_pct = round(100.0 * apps_with_evidence / max(apps_researched, 1), 1)

        unknown_field_count = 0
        total_all_fields = apps_researched * len(EVALUATED_FIELDS)
        for r in all_records:
            if AuthMethod.UNKNOWN in r.auth_methods:
                unknown_field_count += 1
            if r.credential_acquisition == CredentialAcquisition.UNCLEAR:
                unknown_field_count += 1
        unknown_rate_pct = round(100.0 * unknown_field_count / max(total_all_fields, 1), 2)

        sample_size = len(audit_entries)
        fields_per_app = len(EVALUATED_FIELDS)
        total_evaluated = sample_size * fields_per_app

        pass1, pass1_errors = cls._compute_stage(
            "first_pass", audit_entries, "pass1_verdict", "original_value"
        )
        post_val, _ = cls._compute_stage(
            "post_validation", audit_entries, "pass2_verdict", "post_validation_value"
        )
        final_aud, final_errors = cls._compute_stage(
            "final_audited", audit_entries, "final_verdict", "audited_value"
        )

        return AccuracyMetrics(
            total_apps_in_scope=total_apps,
            apps_researched=apps_researched,
            evidence_coverage_pct=evidence_coverage_pct,
            unknown_unresolved_rate_pct=unknown_rate_pct,
            audited_sample_size=sample_size,
            evaluated_fields_per_app=fields_per_app,
            total_evaluated_fields=total_evaluated,
            first_pass=pass1,
            post_validation=post_val,
            final_audited=final_aud,
            false_positives=false_positives,
            false_negatives=false_negatives,
            evaluation_denominator_definition=(
                f"{sample_size} stratified apps (2 per category across all 10 categories) x "
                f"{fields_per_app} core fields ({', '.join(EVALUATED_FIELDS)}) = {total_evaluated} evaluated fields. "
                "Strict rule: only 'Correct' counts toward accuracy; 'Partially correct', 'Incorrect', and "
                "'Unresolved'/'Unknown' fields count as 0 correct."
            ),
            field_error_breakdown_pass1=pass1_errors,
            field_error_breakdown_final=final_errors,
        )

    @staticmethod
    def load_audit_sample(path: str | Path) -> List[AuditSampleEntry]:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        entries = raw["entries"] if isinstance(raw, dict) and "entries" in raw else raw
        return [AuditSampleEntry(**item) for item in entries]
