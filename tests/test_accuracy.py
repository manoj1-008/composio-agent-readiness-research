"""Unit tests for strict field-level accuracy calculations and mathematical reconciliation."""
import json
import unittest
from pathlib import Path

from src.schemas import AuditFieldResult, AuditSampleEntry, AuditVerdict, ResearchedAppRecord
from src.verification import EVALUATED_FIELDS, VerificationAgent


class TestAccuracyCalculations(unittest.TestCase):
    def setUp(self):
        raw = json.loads(Path("data/researched_apps.json").read_text(encoding="utf-8"))
        self.records = [ResearchedAppRecord(**item) for item in raw]
        self.audit_entries = VerificationAgent.load_audit_sample("data/audit_sample.json")

    def test_audit_sample_reconciles_mathematically_across_all_three_stages(self):
        metrics = VerificationAgent.compute_accuracy_metrics(
            all_records=self.records,
            audit_entries=self.audit_entries,
            false_positives=4,
            false_negatives=1,
        )
        self.assertEqual(metrics.total_evaluated_fields, 140)
        for stage in (metrics.first_pass, metrics.post_validation, metrics.final_audited):
            total = stage.correct + stage.partially_correct + stage.incorrect + stage.unresolved
            self.assertEqual(total, 140, f"Stage {stage.stage} failed reconciliation")
            expected_pct = round(100.0 * stage.correct / 140.0, 1)
            self.assertEqual(stage.accuracy_pct, expected_pct)

    def test_partially_correct_and_unknown_never_count_as_correct(self):
        # Synthetic 1-app sample (7 fields): 3 Correct, 2 Partially correct, 1 Incorrect, 1 Unknown-marked-Correct
        synthetic = [
            AuditSampleEntry(
                app_id=1,
                app_name="TestApp",
                category="CRM and Sales",
                official_docs_checked=["https://example.com/docs"],
                overall_verdict=AuditVerdict.PARTIALLY_CORRECT,
                discrepancy_summary="Synthetic test",
                final_corrected_conclusion="Synthetic test",
                field_results=[
                    AuditFieldResult(
                        field_name=EVALUATED_FIELDS[0],
                        original_value="OAuth 2.0",
                        post_validation_value="OAuth 2.0",
                        audited_value="OAuth 2.0",
                        pass1_verdict=AuditVerdict.CORRECT,
                        pass2_verdict=AuditVerdict.CORRECT,
                        final_verdict=AuditVerdict.CORRECT,
                        note="ok",
                    ),
                    AuditFieldResult(
                        field_name=EVALUATED_FIELDS[1],
                        original_value="Free self-service",
                        post_validation_value="Free self-service",
                        audited_value="Free self-service",
                        pass1_verdict=AuditVerdict.CORRECT,
                        pass2_verdict=AuditVerdict.CORRECT,
                        final_verdict=AuditVerdict.CORRECT,
                        note="ok",
                    ),
                    AuditFieldResult(
                        field_name=EVALUATED_FIELDS[2],
                        original_value="REST",
                        post_validation_value="REST",
                        audited_value="REST",
                        pass1_verdict=AuditVerdict.CORRECT,
                        pass2_verdict=AuditVerdict.CORRECT,
                        final_verdict=AuditVerdict.CORRECT,
                        note="ok",
                    ),
                    AuditFieldResult(
                        field_name=EVALUATED_FIELDS[3],
                        original_value="Large",
                        post_validation_value="Large",
                        audited_value="Medium",
                        pass1_verdict=AuditVerdict.PARTIALLY_CORRECT,
                        pass2_verdict=AuditVerdict.PARTIALLY_CORRECT,
                        final_verdict=AuditVerdict.PARTIALLY_CORRECT,
                        note="partial must count as 0",
                    ),
                    AuditFieldResult(
                        field_name=EVALUATED_FIELDS[4],
                        original_value="Official",
                        post_validation_value="Official",
                        audited_value="Vendor-supported",
                        pass1_verdict=AuditVerdict.PARTIALLY_CORRECT,
                        pass2_verdict=AuditVerdict.PARTIALLY_CORRECT,
                        final_verdict=AuditVerdict.PARTIALLY_CORRECT,
                        note="partial must count as 0",
                    ),
                    AuditFieldResult(
                        field_name=EVALUATED_FIELDS[5],
                        original_value="true",
                        post_validation_value="true",
                        audited_value="false",
                        pass1_verdict=AuditVerdict.INCORRECT,
                        pass2_verdict=AuditVerdict.INCORRECT,
                        final_verdict=AuditVerdict.INCORRECT,
                        note="incorrect must count as 0",
                    ),
                    AuditFieldResult(
                        field_name=EVALUATED_FIELDS[6],
                        original_value="Unknown / needs verification",
                        post_validation_value="Unknown / needs verification",
                        audited_value="Unknown / needs verification",
                        # Even if mistakenly tagged Correct, Unknown MUST be coerced to Unresolved!
                        pass1_verdict=AuditVerdict.CORRECT,
                        pass2_verdict=AuditVerdict.CORRECT,
                        final_verdict=AuditVerdict.CORRECT,
                        note="unknown must be coerced to unresolved",
                    ),
                ],
            )
        ]
        metrics = VerificationAgent.compute_accuracy_metrics(
            all_records=self.records,
            audit_entries=synthetic,
            false_positives=0,
            false_negatives=0,
        )
        self.assertEqual(metrics.final_audited.correct, 3)
        self.assertEqual(metrics.final_audited.partially_correct, 2)
        self.assertEqual(metrics.final_audited.incorrect, 1)
        self.assertEqual(metrics.final_audited.unresolved, 1)
        self.assertEqual(metrics.final_audited.accuracy_pct, round(300.0 / 7.0, 1))


if __name__ == "__main__":
    unittest.main()
