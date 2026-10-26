from __future__ import annotations

from pathlib import Path
import unittest

from packages.operations.backup import BackupPolicy, build_backup_manifest
from packages.operations.restore_drill import RestoreDrillError, RestoreDrillPolicy, run_restore_drill


BACKUP_POLICY = Path("config/operations/backup-policy.json")
DRILL_POLICY = Path("config/operations/restore-drill-policy.json")
SOURCE = "a" * 64
CONTENT = "b" * 64


class RestoreDrillTests(unittest.TestCase):
    def setUp(self) -> None:
        self.backup_policy = BackupPolicy.from_path(BACKUP_POLICY)
        self.policy = RestoreDrillPolicy.from_path(DRILL_POLICY)

    def manifest(self, **overrides: object):
        kwargs: dict[str, object] = {
            "dr_class": "DR0",
            "source_ref": SOURCE,
            "source_content_sha256": CONTENT,
            "source_version": 1,
            "created_at_ns": 1_000_000_000,
            "source_size_bytes": 4096,
            "rights_status": "ALLOWED",
            "contains_raw_licensed_content": False,
            "primary_failure_domain": "SITE_A_LOGICAL",
            "recovery_failure_domain": "SITE_B_LOGICAL",
        }
        kwargs.update(overrides)
        return build_backup_manifest(
            self.backup_policy,
            dr_class=kwargs["dr_class"],  # type: ignore[arg-type]
            source_ref=kwargs["source_ref"],  # type: ignore[arg-type]
            source_content_sha256=kwargs["source_content_sha256"],  # type: ignore[arg-type]
            source_version=kwargs["source_version"],  # type: ignore[arg-type]
            created_at_ns=kwargs["created_at_ns"],  # type: ignore[arg-type]
            source_size_bytes=kwargs["source_size_bytes"],  # type: ignore[arg-type]
            rights_status=kwargs["rights_status"],  # type: ignore[arg-type]
            contains_raw_licensed_content=kwargs["contains_raw_licensed_content"],  # type: ignore[arg-type]
            primary_failure_domain=kwargs["primary_failure_domain"],  # type: ignore[arg-type]
            recovery_failure_domain=kwargs["recovery_failure_domain"],  # type: ignore[arg-type]
        )

    def drill(self, manifest, **overrides: object):
        kwargs: dict[str, object] = {
            "drill_kind": "RESTORE",
            "incident_at_ns": 31_000_000_000,
            "restore_started_at_ns": 32_000_000_000,
            "validation_completed_at_ns": 131_000_000_000,
            "restored_content_sha256": CONTENT,
            "quarantine_passed": True,
            "reconciliation_passed": True,
        }
        kwargs.update(overrides)
        return run_restore_drill(
            self.policy,
            manifest=manifest,
            drill_kind=kwargs["drill_kind"],  # type: ignore[arg-type]
            incident_at_ns=kwargs["incident_at_ns"],  # type: ignore[arg-type]
            restore_started_at_ns=kwargs["restore_started_at_ns"],  # type: ignore[arg-type]
            validation_completed_at_ns=kwargs["validation_completed_at_ns"],  # type: ignore[arg-type]
            restored_content_sha256=kwargs["restored_content_sha256"],  # type: ignore[arg-type]
            quarantine_passed=kwargs["quarantine_passed"],  # type: ignore[arg-type]
            reconciliation_passed=kwargs["reconciliation_passed"],  # type: ignore[arg-type]
        )

    def test_dr0_reference_restore_passes_with_integrity_quarantine_reconciliation(self) -> None:
        result = self.drill(self.manifest())
        self.assertEqual(result.status, "PASS")
        self.assertEqual(result.measured_rpo_seconds, 30)
        self.assertEqual(result.measured_rto_seconds, 100)
        self.assertTrue(result.rpo_target_met)
        self.assertTrue(result.rto_target_met)
        self.assertTrue(result.integrity_match)
        self.assertTrue(result.quarantine_passed)
        self.assertTrue(result.reconciliation_passed)
        self.assertTrue(result.trusted_after_drill)

    def test_dr0_requires_reconciliation(self) -> None:
        result = self.drill(self.manifest(), reconciliation_passed=False)
        self.assertEqual(result.status, "FAIL")
        self.assertEqual(result.reason_code, "POST_RESTORE_RECONCILIATION_NOT_PASSED")
        self.assertFalse(result.trusted_after_drill)

    def test_integrity_mismatch_fails(self) -> None:
        result = self.drill(self.manifest(), restored_content_sha256="c" * 64)
        self.assertEqual(result.status, "FAIL")
        self.assertEqual(result.reason_code, "INTEGRITY_MISMATCH")

    def test_restore_quarantine_cannot_be_bypassed(self) -> None:
        result = self.drill(self.manifest(), quarantine_passed=False)
        self.assertEqual(result.status, "FAIL")
        self.assertEqual(result.reason_code, "RESTORE_QUARANTINE_NOT_PASSED")

    def test_reference_rpo_target_miss_fails(self) -> None:
        result = self.drill(
            self.manifest(),
            incident_at_ns=62_000_000_000,
            restore_started_at_ns=63_000_000_000,
            validation_completed_at_ns=100_000_000_000,
        )
        self.assertEqual(result.measured_rpo_seconds, 61)
        self.assertEqual(result.status, "FAIL")
        self.assertEqual(result.reason_code, "REFERENCE_RPO_TARGET_MISSED")

    def test_reference_rto_target_miss_fails(self) -> None:
        result = self.drill(
            self.manifest(),
            validation_completed_at_ns=3_632_000_000_000,
        )
        self.assertEqual(result.measured_rto_seconds, 3601)
        self.assertEqual(result.status, "FAIL")
        self.assertEqual(result.reason_code, "REFERENCE_RTO_TARGET_MISSED")

    def test_blocked_backup_manifest_is_not_drill_eligible(self) -> None:
        blocked = self.manifest(recovery_failure_domain="SITE_A_LOGICAL")
        result = self.drill(blocked)
        self.assertEqual(result.status, "BLOCKED")
        self.assertEqual(result.reason_code, "BACKUP_MANIFEST_BLOCKED")

    def test_dr3_requires_rebuild_semantics(self) -> None:
        manifest = self.manifest(
            dr_class="DR3",
            rights_status="DERIVED_ONLY",
            primary_failure_domain="SITE_A_LOGICAL",
            recovery_failure_domain="SITE_A_LOGICAL",
        )
        blocked = self.drill(manifest)
        self.assertEqual(blocked.status, "BLOCKED")
        self.assertEqual(blocked.reason_code, "REBUILD_ONLY_MANIFEST_REQUIRES_REBUILD_DRILL")

        rebuilt = self.drill(manifest, drill_kind="REBUILD")
        self.assertEqual(rebuilt.status, "PASS")
        self.assertIsNone(rebuilt.rpo_target_seconds)
        self.assertIsNone(rebuilt.rpo_target_met)

    def test_invalid_timing_fails_closed(self) -> None:
        manifest = self.manifest()
        with self.assertRaises(RestoreDrillError):
            self.drill(manifest, incident_at_ns=500_000_000)
        with self.assertRaises(RestoreDrillError):
            self.drill(manifest, restore_started_at_ns=30_000_000_000)
        with self.assertRaises(RestoreDrillError):
            self.drill(manifest, validation_completed_at_ns=31_000_000_000)

    def test_measurement_is_ceiling_seconds(self) -> None:
        manifest = self.manifest(created_at_ns=1_000_000_001)
        result = self.drill(
            manifest,
            incident_at_ns=31_000_000_000,
            restore_started_at_ns=31_000_000_001,
            validation_completed_at_ns=31_000_000_002,
        )
        self.assertEqual(result.measured_rpo_seconds, 30)
        self.assertEqual(result.measured_rto_seconds, 1)

    def test_result_is_deterministic(self) -> None:
        manifest = self.manifest()
        first = self.drill(manifest)
        second = self.drill(manifest)
        self.assertEqual(first.drill_id, second.drill_id)

    def test_reference_drill_never_claims_production_certification_or_mutation(self) -> None:
        result = self.drill(self.manifest())
        self.assertTrue(result.reference_measurement_only)
        self.assertFalse(result.production_rpo_rto_certified)
        self.assertFalse(result.real_restore_execution)
        self.assertFalse(result.network_access)
        self.assertFalse(result.credential_access)
        self.assertFalse(result.production_mutation)
        policy = DRILL_POLICY.read_text(encoding="utf-8")
        self.assertIn('"production_rpo_rto_certification": false', policy)
        self.assertIn('"real_restore_execution": false', policy)
        self.assertIn('"storage_write_authority": false', policy)
        self.assertIn('"network_mode": "DISABLED"', policy)
        self.assertIn('"credential_mode": "NONE"', policy)
        self.assertIn('"live_trading": "DISABLED"', policy)
        self.assertIn('"auto_trading": "DISABLED"', policy)


if __name__ == "__main__":
    unittest.main()
