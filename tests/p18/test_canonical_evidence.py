from __future__ import annotations

import hashlib
import unittest

from packages.learning.canonical_evidence import (
    CanonicalArtifact,
    CanonicalDemoLineage,
    CanonicalEvidenceStore,
    CanonicalLearningEvidenceError,
    CanonicalPromotionRequest,
    MetricDefinition,
    MetricPolicy,
    CanonicalEvaluation,
    RetrainingResourceBudget,
    RetrainingResourceUsage,
    enforce_retraining_budget,
    evaluate_canonical_promotion,
    verify_demo_lineage,
    verify_retraining_lineage,
)


def h(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def artifact(label: str, kind: str, state: str) -> CanonicalArtifact:
    return CanonicalArtifact(h(label), kind, state, h("prov-" + label))


class CanonicalEvidenceTests(unittest.TestCase):
    def test_demo_lineage_requires_resolved_upstream_artifacts(self) -> None:
        store = CanonicalEvidenceStore()
        records = (
            artifact("strategy", "STRATEGY_RECORD", "VALIDATED"),
            artifact("model", "MODEL_RECORD", "VALIDATED"),
            artifact("signal", "SIGNAL_DECISION", "PASS"),
            artifact("risk", "RISK_DECISION", "PASS"),
            artifact("firewall", "FIREWALL_DECISION", "PASS"),
        )
        for row in records:
            store.add(row)
        lineage = CanonicalDemoLineage(*(row.artifact_id for row in records))
        self.assertEqual(verify_demo_lineage(store, lineage), lineage.lineage_id)

    def test_unknown_or_wrong_kind_fails_closed(self) -> None:
        store = CanonicalEvidenceStore()
        store.add(artifact("strategy", "STRATEGY_RECORD", "VALIDATED"))
        store.add(artifact("model", "MODEL_RECORD", "VALIDATED"))
        store.add(artifact("signal", "SIGNAL_DECISION", "PASS"))
        store.add(artifact("risk", "RISK_DECISION", "PASS"))
        store.add(artifact("firewall", "AUDIT_BUNDLE", "COMPLETE"))
        lineage = CanonicalDemoLineage(
            h("strategy"), h("model"), h("signal"), h("risk"), h("firewall")
        )
        with self.assertRaises(CanonicalLearningEvidenceError):
            verify_demo_lineage(store, lineage)

    def test_metric_policy_requires_exact_metric_set(self) -> None:
        policy = MetricPolicy(
            (
                MetricDefinition("SHARPE", "1.0", "RATIO", "HIGHER_BETTER"),
                MetricDefinition("MAX_DRAWDOWN_BPS", "1.0", "BPS", "LOWER_BETTER"),
            ),
            "SHARPE",
        )
        row = CanonicalEvaluation.create(
            model_record_id=h("model"),
            dataset_id=h("dataset"),
            metric_policy=policy,
            metrics={"SHARPE": "1.25", "MAX_DRAWDOWN_BPS": "400"},
            evidence_sha256=h("evaluation"),
        )
        self.assertEqual(row.metric_policy_id, policy.policy_id)
        with self.assertRaises(CanonicalLearningEvidenceError):
            CanonicalEvaluation.create(
                model_record_id=h("model"),
                dataset_id=h("dataset"),
                metric_policy=policy,
                metrics={"SHARPE": "1.25"},
                evidence_sha256=h("evaluation"),
            )

    def test_retraining_lineage_and_resource_budget(self) -> None:
        store = CanonicalEvidenceStore()
        store.add(artifact("dataset", "DATASET", "READY"))
        store.add(artifact("experiment", "EXPERIMENT", "PASS"))
        store.add(artifact("model", "MODEL_RECORD", "VALIDATED"))
        lineage_id = verify_retraining_lineage(
            store,
            dataset_id=h("dataset"),
            experiment_id=h("experiment"),
            base_model_id=h("model"),
        )
        self.assertEqual(len(lineage_id), 64)
        budget = RetrainingResourceBudget(60, 512, 120, 2)
        evidence = enforce_retraining_budget(
            RetrainingResourceUsage(20, 256, 30, 1),
            budget,
        )
        self.assertEqual(len(evidence), 64)
        with self.assertRaises(CanonicalLearningEvidenceError):
            enforce_retraining_budget(
                RetrainingResourceUsage(20, 1024, 30, 1),
                budget,
            )

    def test_promotion_resolves_artifacts_not_caller_booleans(self) -> None:
        store = CanonicalEvidenceStore()
        rows = (
            artifact("candidate", "CANDIDATE_VALIDATION", "PASS"),
            artifact("comparison", "CHALLENGER_COMPARISON", "RECOMMENDED"),
            artifact("drift", "DRIFT_ASSESSMENT", "NORMAL"),
            artifact("risk-review", "RISK_REVIEW", "PASS"),
            artifact("audit", "AUDIT_BUNDLE", "COMPLETE"),
        )
        for row in rows:
            store.add(row)
        req = CanonicalPromotionRequest(
            "demo",
            "DEMO_CHAMPION",
            *(row.artifact_id for row in rows),
        )
        decision = evaluate_canonical_promotion(store, req)
        self.assertEqual(decision.status, "APPROVE_DEMO_CHAMPION_RECORD")
        self.assertFalse(decision.registry_mutation)
        self.assertFalse(decision.promotion_execution_authority)

    def test_failed_resolved_risk_blocks_demo_promotion(self) -> None:
        store = CanonicalEvidenceStore()
        rows = (
            artifact("candidate", "CANDIDATE_VALIDATION", "PASS"),
            artifact("comparison", "CHALLENGER_COMPARISON", "RECOMMENDED"),
            artifact("drift", "DRIFT_ASSESSMENT", "NORMAL"),
            artifact("risk-review", "RISK_REVIEW", "FAIL"),
            artifact("audit", "AUDIT_BUNDLE", "COMPLETE"),
        )
        for row in rows:
            store.add(row)
        req = CanonicalPromotionRequest(
            "demo",
            "DEMO_CHAMPION",
            *(row.artifact_id for row in rows),
        )
        with self.assertRaises(CanonicalLearningEvidenceError):
            evaluate_canonical_promotion(store, req)

    def test_live_always_requires_owner_gate(self) -> None:
        req = CanonicalPromotionRequest(
            "live",
            "LIVE",
            h("candidate"),
            h("comparison"),
            h("drift"),
            h("risk-review"),
            h("audit"),
        )
        decision = evaluate_canonical_promotion(CanonicalEvidenceStore(), req)
        self.assertEqual(decision.status, "OWNER_LIVE_GATE_REQUIRED")
        self.assertFalse(decision.automatic_live_promotion)


if __name__ == "__main__":
    unittest.main()
