from __future__ import annotations

from pathlib import Path
import unittest

from packages.operations.backup import BackupPolicy, build_backup_manifest
from packages.operations.disaster_recovery import DisasterRecoveryPolicy, build_disaster_recovery_plan
from packages.operations.restore_drill import RestoreDrillPolicy, run_restore_drill


BACKUP_POLICY = Path("config/operations/backup-policy.json")
DRILL_POLICY = Path("config/operations/restore-drill-policy.json")
DR_POLICY = Path("config/operations/disaster-recovery-policy.json")
SOURCE = "a" * 64
CONTENT = "b" * 64
INCIDENT = "c" * 64


class DisasterRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.backup_policy = BackupPolicy.from_path(BACKUP_POLICY)
        self.drill_policy = RestoreDrillPolicy.from_path(DRILL_POLICY)
        self.policy = DisasterRecoveryPolicy.from_path(DR_POLICY)

    def manifest(self, *, dr_class: str = "DR0", recovery_domain: str = "SITE_B_LOGICAL"):
        return build_backup_manifest(
            self.backup_policy,
            dr_class=dr_class,  # type: ignore[arg-type]
            source_ref=SOURCE,
            source_content_sha256=CONTENT,
            source_version=1,
            created_at_ns=1_000_000_000,
            source_size_bytes=4096,
            rights_status="ALLOWED" if dr_class != "DR3" else "DERIVED_ONLY",
            contains_raw_licensed_content=False,
            primary_failure_domain="SITE_A_LOGICAL",
            recovery_failure_domain=recovery_domain,
        )

    def drill(self, manifest, *, kind: str | None = None, reconciliation: bool = True):
        drill_kind = kind or ("REBUILD" if manifest.dr_class == "DR3" else "RESTORE")
        return run_restore_drill(
            self.drill_policy,
            manifest=manifest,
            drill_kind=drill_kind,  # type: ignore[arg-type]
            incident_at_ns=31_000_000_000,
            restore_started_at_ns=32_000_000_000,
            validation_completed_at_ns=131_000_000_000,
            restored_content_sha256=CONTENT,
            quarantine_passed=True,
            reconciliation_passed=reconciliation,
        )

    def plan(
        self,
        manifest,
        drill,
        *,
        state: str = "EMERGENCY",
        authorized: bool = True,
        recovery_domain: str | None = None,
    ):
        return build_disaster_recovery_plan(
            self.policy,
            incident_id=INCIDENT,
            system_state=state,  # type: ignore[arg-type]
            manifest=manifest,
            drill=drill,
            declared_at_ns=200_000_000_000,
            recovery_failure_domain=recovery_domain or manifest.recovery_failure_domain,
            owner_recovery_authorized=authorized,
        )

    def test_emergency_dr0_with_trusted_drill_and_owner_authorization_is_ready(self) -> None:
        manifest = self.manifest()
        plan = self.plan(manifest, self.drill(manifest))
        self.assertEqual(plan.status, "REFERENCE_RECOVERY_READY")
        self.assertEqual(plan.recovery_mode, "RESTORE")
        self.assertIn("RECONCILE_EXECUTION_AUTHORITY_REFERENCE", plan.reference_steps)
        self.assertFalse(plan.execution_authority)
        self.assertFalse(plan.production_recovery_certified)

    def test_halted_state_is_eligible(self) -> None:
        manifest = self.manifest(dr_class="DR1")
        plan = self.plan(manifest, self.drill(manifest), state="HALTED")
        self.assertEqual(plan.status, "REFERENCE_RECOVERY_READY")

    def test_non_disaster_state_is_blocked(self) -> None:
        manifest = self.manifest()
        plan = self.plan(manifest, self.drill(manifest), state="SAFE_MODE")
        self.assertEqual(plan.status, "BLOCKED")
        self.assertEqual(plan.reason_code, "SYSTEM_STATE_NOT_DISASTER_ELIGIBLE")

    def test_owner_authorization_is_required(self) -> None:
        manifest = self.manifest()
        plan = self.plan(manifest, self.drill(manifest), authorized=False)
        self.assertEqual(plan.status, "AWAITING_OWNER_AUTHORIZATION")
        self.assertEqual(plan.reason_code, "OWNER_RECOVERY_AUTHORIZATION_REQUIRED")
        self.assertNotIn("REFERENCE_RECOVERY_READY", plan.reference_steps)

    def test_backup_drill_lineage_mismatch_is_blocked(self) -> None:
        manifest = self.manifest()
        other = self.manifest(dr_class="DR1")
        plan = self.plan(manifest, self.drill(other))
        self.assertEqual(plan.status, "BLOCKED")
        self.assertEqual(plan.reason_code, "BACKUP_DRILL_LINEAGE_MISMATCH")

    def test_untrusted_failed_drill_is_blocked(self) -> None:
        manifest = self.manifest()
        failed = run_restore_drill(
            self.drill_policy,
            manifest=manifest,
            drill_kind="RESTORE",
            incident_at_ns=31_000_000_000,
            restore_started_at_ns=32_000_000_000,
            validation_completed_at_ns=131_000_000_000,
            restored_content_sha256="d" * 64,
            quarantine_passed=True,
            reconciliation_passed=True,
        )
        plan = self.plan(manifest, failed)
        self.assertEqual(plan.status, "BLOCKED")
        self.assertEqual(plan.reason_code, "RESTORE_DRILL_NOT_TRUSTED_PASS")

    def test_recovery_domain_lineage_mismatch_is_blocked(self) -> None:
        manifest = self.manifest()
        plan = self.plan(manifest, self.drill(manifest), recovery_domain="SITE_C_LOGICAL")
        self.assertEqual(plan.status, "BLOCKED")
        self.assertEqual(plan.reason_code, "RECOVERY_DOMAIN_LINEAGE_MISMATCH")

    def test_dr3_preserves_rebuild_semantics(self) -> None:
        manifest = self.manifest(dr_class="DR3", recovery_domain="SITE_A_LOGICAL")
        drill = self.drill(manifest)
        plan = self.plan(manifest, drill)
        self.assertEqual(plan.status, "REFERENCE_RECOVERY_READY")
        self.assertEqual(plan.recovery_mode, "REBUILD")
        self.assertNotIn("RECONCILE_EXECUTION_AUTHORITY_REFERENCE", plan.reference_steps)

    def test_plan_identity_is_deterministic(self) -> None:
        manifest = self.manifest()
        drill = self.drill(manifest)
        first = self.plan(manifest, drill)
        second = self.plan(manifest, drill)
        self.assertEqual(first.plan_id, second.plan_id)

    def test_plan_never_grants_runtime_authority(self) -> None:
        manifest = self.manifest()
        plan = self.plan(manifest, self.drill(manifest))
        self.assertFalse(plan.execution_authority)
        self.assertFalse(plan.real_failover_execution)
        self.assertFalse(plan.dns_mutation)
        self.assertFalse(plan.network_mutation)
        self.assertFalse(plan.storage_mutation)
        self.assertFalse(plan.automatic_state_mutation)
        self.assertFalse(plan.external_order_authority)
        self.assertFalse(plan.production_recovery_certified)
        policy = DR_POLICY.read_text(encoding="utf-8")
        self.assertIn('"execution_mode": "REFERENCE_PLAN_ONLY"', policy)
        self.assertIn('"real_failover_execution": false', policy)
        self.assertIn('"dns_mutation": false', policy)
        self.assertIn('"network_mutation": false', policy)
        self.assertIn('"storage_mutation": false', policy)
        self.assertIn('"credential_mode": "NONE"', policy)
        self.assertIn('"live_trading": "DISABLED"', policy)
        self.assertIn('"auto_trading": "DISABLED"', policy)


if __name__ == "__main__":
    unittest.main()
