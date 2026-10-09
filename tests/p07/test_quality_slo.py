from __future__ import annotations

from pathlib import Path
import unittest

from packages.data_quality import (
    QualityRouteObservation,
    QualitySloError,
    QualitySloEvaluator,
    QualitySloPolicy,
    RouteDisposition,
    SloStatus,
)

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/data-quality/quality-slo-policy.json"


def evaluator() -> QualitySloEvaluator:
    return QualitySloEvaluator(QualitySloPolicy.from_path(POLICY))


def obs(index: int, disposition: RouteDisposition) -> QualityRouteObservation:
    return QualityRouteObservation(
        subject_id=f"subject-{index:03d}",
        disposition=disposition,
        decision_evidence_sha256=f"{index % 16:x}" * 64,
    )


class QualitySloPolicyTests(unittest.TestCase):
    def test_policy_is_offline_and_vendor_neutral(self):
        policy = QualitySloPolicy.from_path(POLICY)
        self.assertEqual(policy.production_observability_vendor, "NOT_SELECTED")
        self.assertEqual(policy.rate_scale_bps, 10000)
        self.assertEqual(policy.no_data_severity, SloStatus.CRITICAL)


class QualitySloEvaluationTests(unittest.TestCase):
    def test_healthy_sample_meets_all_slos(self):
        snapshot = evaluator().evaluate(
            tuple(obs(i, RouteDisposition.ACCEPTED_DOWNSTREAM) for i in range(20))
        )
        self.assertEqual(snapshot.trusted_route_bps, 10000)
        self.assertEqual(snapshot.quarantine_rate_bps, 0)
        self.assertEqual(snapshot.unknown_block_rate_bps, 0)
        self.assertEqual(snapshot.highest_severity, SloStatus.HEALTHY)
        self.assertFalse(snapshot.blocking)
        self.assertTrue(all(item.status is SloStatus.HEALTHY for item in snapshot.evaluations))

    def test_warning_band_is_deterministic(self):
        values = tuple(
            [obs(i, RouteDisposition.ACCEPTED_DOWNSTREAM) for i in range(18)]
            + [obs(18, RouteDisposition.QUARANTINED), obs(19, RouteDisposition.QUARANTINED)]
        )
        snapshot = evaluator().evaluate(values)
        self.assertEqual(snapshot.trusted_route_bps, 9000)
        self.assertEqual(snapshot.quarantine_rate_bps, 1000)
        self.assertEqual(snapshot.highest_severity, SloStatus.WARNING)
        self.assertFalse(snapshot.blocking)
        statuses = {item.slo_id: item.status for item in snapshot.evaluations}
        self.assertEqual(statuses["TRUSTED_ROUTE_RATE"], SloStatus.WARNING)
        self.assertEqual(statuses["QUARANTINE_RATE"], SloStatus.WARNING)

    def test_critical_band_is_blocking(self):
        values = tuple(
            [obs(i, RouteDisposition.ACCEPTED_DOWNSTREAM) for i in range(17)]
            + [
                obs(17, RouteDisposition.QUARANTINED),
                obs(18, RouteDisposition.QUARANTINED),
                obs(19, RouteDisposition.QUARANTINED),
            ]
        )
        snapshot = evaluator().evaluate(values)
        self.assertEqual(snapshot.trusted_route_bps, 8500)
        self.assertEqual(snapshot.quarantine_rate_bps, 1500)
        self.assertEqual(snapshot.highest_severity, SloStatus.CRITICAL)
        self.assertTrue(snapshot.blocking)

    def test_empty_window_is_blocking_no_data(self):
        snapshot = evaluator().evaluate(())
        self.assertEqual(snapshot.total_count, 0)
        self.assertEqual(snapshot.highest_severity, SloStatus.CRITICAL)
        self.assertTrue(snapshot.blocking)
        self.assertTrue(all(item.status is SloStatus.NO_DATA for item in snapshot.evaluations))
        self.assertIsNone(snapshot.trusted_route_bps)

    def test_unknown_block_rate_can_be_critical(self):
        values = tuple(
            [obs(i, RouteDisposition.ACCEPTED_DOWNSTREAM) for i in range(19)]
            + [obs(19, RouteDisposition.BLOCKED_UNKNOWN)]
        )
        snapshot = evaluator().evaluate(values)
        self.assertEqual(snapshot.unknown_block_rate_bps, 500)
        self.assertEqual(snapshot.highest_severity, SloStatus.WARNING)

        values2 = tuple(
            [obs(i, RouteDisposition.ACCEPTED_DOWNSTREAM) for i in range(18)]
            + [
                obs(18, RouteDisposition.BLOCKED_UNKNOWN),
                obs(19, RouteDisposition.BLOCKED_UNKNOWN),
            ]
        )
        snapshot2 = evaluator().evaluate(values2)
        self.assertEqual(snapshot2.unknown_block_rate_bps, 1000)
        self.assertEqual(snapshot2.highest_severity, SloStatus.CRITICAL)
        self.assertTrue(snapshot2.blocking)

    def test_duplicate_subject_observations_fail_closed(self):
        first = obs(1, RouteDisposition.ACCEPTED_DOWNSTREAM)
        duplicate = QualityRouteObservation(
            subject_id=first.subject_id,
            disposition=RouteDisposition.QUARANTINED,
            decision_evidence_sha256="f" * 64,
        )
        with self.assertRaises(QualitySloError):
            evaluator().evaluate((first, duplicate))

    def test_invalid_decision_evidence_digest_fails_closed(self):
        with self.assertRaises(QualitySloError):
            QualityRouteObservation(
                subject_id="subject-x",
                disposition=RouteDisposition.ACCEPTED_DOWNSTREAM,
                decision_evidence_sha256="bad",
            )

    def test_metric_arithmetic_uses_integer_basis_point_floor(self):
        snapshot = evaluator().evaluate(
            (
                obs(1, RouteDisposition.ACCEPTED_DOWNSTREAM),
                obs(2, RouteDisposition.ACCEPTED_DOWNSTREAM),
                obs(3, RouteDisposition.QUARANTINED),
            )
        )
        self.assertEqual(snapshot.trusted_route_bps, 6666)
        self.assertEqual(snapshot.quarantine_rate_bps, 3333)
        self.assertEqual(snapshot.unknown_block_rate_bps, 0)

    def test_input_order_does_not_change_snapshot_fingerprint(self):
        values = (
            obs(1, RouteDisposition.ACCEPTED_DOWNSTREAM),
            obs(2, RouteDisposition.QUARANTINED),
            obs(3, RouteDisposition.BLOCKED_UNKNOWN),
        )
        first = evaluator().evaluate(values)
        second = evaluator().evaluate(tuple(reversed(values)))
        self.assertEqual(first.fingerprint, second.fingerprint)
        self.assertEqual(first.evaluations, second.evaluations)
        self.assertEqual(first.decision_evidence_sha256s, second.decision_evidence_sha256s)


if __name__ == "__main__":
    unittest.main()
