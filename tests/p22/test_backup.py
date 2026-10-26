from __future__ import annotations

from pathlib import Path
import unittest

from packages.operations.backup import BackupError, BackupPolicy, build_backup_manifest


POLICY = Path("config/operations/backup-policy.json")
SOURCE = "a" * 64
CONTENT = "b" * 64


class BackupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = BackupPolicy.from_path(POLICY)

    def build(self, **overrides: object):
        kwargs: dict[str, object] = {
            "dr_class": "DR1",
            "source_ref": SOURCE,
            "source_content_sha256": CONTENT,
            "source_version": 1,
            "created_at_ns": 1_000,
            "source_size_bytes": 4096,
            "rights_status": "ALLOWED",
            "contains_raw_licensed_content": False,
            "primary_failure_domain": "SITE_A_LOGICAL",
            "recovery_failure_domain": "SITE_B_LOGICAL",
        }
        kwargs.update(overrides)
        return build_backup_manifest(
            self.policy,
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

    def test_canonical_dr_targets_match_architecture(self) -> None:
        self.assertEqual(self.policy.dr_classes["DR0"].rpo_target_seconds, 60)
        self.assertEqual(self.policy.dr_classes["DR0"].provisional_rto_target_seconds, 3600)
        self.assertEqual(self.policy.dr_classes["DR1"].rpo_target_seconds, 900)
        self.assertEqual(self.policy.dr_classes["DR1"].provisional_rto_target_seconds, 14400)
        self.assertEqual(self.policy.dr_classes["DR2"].rpo_target_seconds, 86400)
        self.assertEqual(self.policy.dr_classes["DR2"].provisional_rto_target_seconds, 86400)
        self.assertIsNone(self.policy.dr_classes["DR3"].rpo_target_seconds)
        self.assertEqual(self.policy.dr_classes["DR3"].provisional_rto_target_seconds, 172800)

    def test_dr0_is_eligible_off_primary_and_requires_reconciliation(self) -> None:
        manifest = self.build(dr_class="DR0")
        self.assertEqual(manifest.status, "ELIGIBLE_REFERENCE_BACKUP")
        self.assertTrue(manifest.backup_required)
        self.assertTrue(manifest.reconciliation_after_restore_required)
        self.assertTrue(manifest.restore_quarantine_required)

    def test_same_failure_domain_does_not_count_as_dr(self) -> None:
        manifest = self.build(recovery_failure_domain="SITE_A_LOGICAL")
        self.assertEqual(manifest.status, "BLOCKED")
        self.assertEqual(manifest.reason_code, "SAME_FAILURE_DOMAIN_NOT_DR")

    def test_forbidden_and_unverified_retention_fail_closed(self) -> None:
        for rights in ("FORBIDDEN", "UNVERIFIED"):
            with self.subTest(rights=rights):
                manifest = self.build(rights_status=rights)
                self.assertEqual(manifest.status, "BLOCKED")
                self.assertEqual(manifest.reason_code, "RETENTION_RIGHTS_NOT_PERMITTED")

    def test_derived_only_rejects_raw_licensed_content(self) -> None:
        manifest = self.build(
            dr_class="DR2",
            rights_status="DERIVED_ONLY",
            contains_raw_licensed_content=True,
        )
        self.assertEqual(manifest.status, "BLOCKED")
        self.assertEqual(manifest.reason_code, "RAW_LICENSED_CONTENT_NOT_PERMITTED")

    def test_derived_only_accepts_nonraw_derived_content(self) -> None:
        manifest = self.build(
            dr_class="DR2",
            rights_status="DERIVED_ONLY",
            contains_raw_licensed_content=False,
        )
        self.assertEqual(manifest.status, "ELIGIBLE_REFERENCE_BACKUP")

    def test_dr3_is_rebuild_only_without_false_backup_claim(self) -> None:
        manifest = self.build(
            dr_class="DR3",
            primary_failure_domain="SITE_A_LOGICAL",
            recovery_failure_domain="SITE_A_LOGICAL",
        )
        self.assertEqual(manifest.status, "REBUILD_ONLY")
        self.assertFalse(manifest.backup_required)
        self.assertIsNone(manifest.rpo_target_seconds)

    def test_rpo_rto_are_targets_not_measured_claims(self) -> None:
        manifest = self.build(dr_class="DR2")
        self.assertFalse(manifest.measured_rpo_rto_validated)
        self.assertEqual(manifest.rpo_target_seconds, 86400)
        self.assertEqual(manifest.provisional_rto_target_seconds, 86400)

    def test_manifest_identity_is_deterministic(self) -> None:
        first = self.build()
        second = self.build()
        self.assertEqual(first.manifest_id, second.manifest_id)
        self.assertEqual(len(first.manifest_id), 64)

    def test_version_and_integrity_inputs_fail_closed(self) -> None:
        with self.assertRaises(BackupError):
            self.build(source_version=0)
        with self.assertRaises(BackupError):
            self.build(source_ref="bad")
        with self.assertRaises(BackupError):
            self.build(source_content_sha256="bad")

    def test_negative_time_and_size_fail_closed(self) -> None:
        with self.assertRaises(BackupError):
            self.build(created_at_ns=-1)
        with self.assertRaises(BackupError):
            self.build(source_size_bytes=-1)

    def test_reference_contract_has_zero_write_authority(self) -> None:
        manifest = self.build()
        self.assertFalse(manifest.backup_write_authority)
        self.assertFalse(manifest.network_write)
        self.assertFalse(manifest.production_mutation)
        content = POLICY.read_text(encoding="utf-8")
        self.assertIn('"production_storage_vendor": "NOT_SELECTED"', content)
        self.assertIn('"backup_write_authority": false', content)
        self.assertIn('"network_mode": "DISABLED"', content)
        self.assertIn('"credential_mode": "NONE"', content)
        self.assertIn('"live_execution_authority": false', content)
        self.assertIn('"live_trading": "DISABLED"', content)
        self.assertIn('"auto_trading": "DISABLED"', content)


if __name__ == "__main__":
    unittest.main()
