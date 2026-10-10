from __future__ import annotations

import json
from pathlib import Path
import unittest

from packages.technical_intelligence.technical_validation_gate import (
    GateOutcome,
    TechnicalValidationGateEvaluator,
    TechnicalValidationGatePolicy,
)

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = (
    ROOT
    / "config/technical-intelligence/technical-validation-gate-policy.json"
)


def policy() -> TechnicalValidationGatePolicy:
    return TechnicalValidationGatePolicy.from_path(POLICY_PATH)


def canonical_documents() -> dict[str, bytes]:
    return {
        item.document: (ROOT / item.document).read_bytes()
        for item in policy().required_workstreams
    }


def mutate_document(
    documents: dict[str, bytes],
    task_id: str,
    key: str,
    value: object,
) -> dict[str, bytes]:
    result = dict(documents)
    item = next(
        candidate
        for candidate in policy().required_workstreams
        if candidate.task_id == task_id
    )
    document = json.loads(result[item.document].decode("utf-8"))
    assert isinstance(document, dict)
    document[key] = value
    result[item.document] = (
        json.dumps(
            document,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")
    return result


class P08IPolicyTests(unittest.TestCase):
    def test_policy_requires_exactly_p08_a_through_h(self) -> None:
        value = policy()
        self.assertEqual(value.gate_id, "G6_TECHNICAL_VALIDATED")
        self.assertTrue(value.fail_closed)
        self.assertEqual(
            {item.task_id for item in value.required_workstreams},
            {
                "FIN-P08-WA-001",
                "FIN-P08-WB-001",
                "FIN-P08-WC-001",
                "FIN-P08-WD-001",
                "FIN-P08-WE-001",
                "FIN-P08-WF-001",
                "FIN-P08-WG-001",
                "FIN-P08-WH-001",
            },
        )
        self.assertEqual(value.production_fusion_threshold_owner, "P14")
        self.assertFalse(value.direct_trade_output_allowed)
        self.assertFalse(value.network_required)
        self.assertFalse(value.credentials_required)


class P08IGateTests(unittest.TestCase):
    def test_canonical_p08_a_through_h_pass(self) -> None:
        report = TechnicalValidationGateEvaluator(policy()).evaluate(
            canonical_documents()
        )
        self.assertIs(report.outcome, GateOutcome.PASS)
        self.assertEqual(len(report.certified_task_ids), 8)
        self.assertEqual(report.issues, ())
        self.assertEqual(
            report.next_phase_state,
            "NOT_STARTED_OWNER_PHASE_AUTHORIZATION_REQUIRED",
        )
        self.assertEqual(report.live_trading, "DISABLED")
        self.assertEqual(report.auto_trading, "DISABLED")

    def test_input_order_does_not_change_gate_fingerprint(self) -> None:
        documents = canonical_documents()
        reversed_documents = dict(reversed(tuple(documents.items())))
        evaluator = TechnicalValidationGateEvaluator(policy())
        first = evaluator.evaluate(documents)
        second = evaluator.evaluate(reversed_documents)
        self.assertEqual(first.outcome, second.outcome)
        self.assertEqual(first.fingerprint, second.fingerprint)

    def test_missing_workstream_fails_closed(self) -> None:
        documents = canonical_documents()
        documents.pop(next(iter(documents)))
        report = TechnicalValidationGateEvaluator(policy()).evaluate(
            documents
        )
        self.assertIs(report.outcome, GateOutcome.FAIL)
        self.assertTrue(
            any(
                issue.code == "DOCUMENT_SET_MISMATCH"
                for issue in report.issues
            )
        )

    def test_non_canonical_state_or_lock_fails(self) -> None:
        documents = canonical_documents()
        for key, value, code in (
            ("state", "IMPLEMENTATION_ACTIVE", "STATE_NOT_CANONICAL"),
            ("lock", "LOCKED", "LOCK_NOT_RELEASED"),
        ):
            report = TechnicalValidationGateEvaluator(policy()).evaluate(
                mutate_document(
                    documents,
                    "FIN-P08-WB-001",
                    key,
                    value,
                )
            )
            self.assertIs(report.outcome, GateOutcome.FAIL)
            self.assertTrue(
                any(issue.code == code for issue in report.issues)
            )

    def test_safety_drift_fails(self) -> None:
        documents = canonical_documents()
        mutations = (
            ("live_trading", "ENABLED", "LIVE_TRADING_NOT_DISABLED"),
            ("auto_trading", "ENABLED", "AUTO_TRADING_NOT_DISABLED"),
            ("country_assumption", "DE", "COUNTRY_ASSUMPTION_CHANGED"),
            (
                "direct_trade_output_allowed",
                True,
                "DIRECT_TRADE_OUTPUT_NOT_FORBIDDEN",
            ),
        )
        for key, value, code in mutations:
            report = TechnicalValidationGateEvaluator(policy()).evaluate(
                mutate_document(
                    documents,
                    "FIN-P08-WC-001",
                    key,
                    value,
                )
            )
            self.assertIs(report.outcome, GateOutcome.FAIL)
            self.assertTrue(
                any(issue.code == code for issue in report.issues)
            )

    def test_p08a_point_in_time_and_trusted_data_are_mandatory(self) -> None:
        documents = canonical_documents()
        for key, code in (
            ("point_in_time_required", "POINT_IN_TIME_NOT_REQUIRED"),
            ("trusted_data_required", "TRUSTED_DATA_NOT_REQUIRED"),
        ):
            report = TechnicalValidationGateEvaluator(policy()).evaluate(
                mutate_document(
                    documents,
                    "FIN-P08-WA-001",
                    key,
                    False,
                )
            )
            self.assertIs(report.outcome, GateOutcome.FAIL)
            self.assertTrue(
                any(issue.code == code for issue in report.issues)
            )

    def test_p08f_breakout_leakage_and_double_counting_fail(self) -> None:
        documents = canonical_documents()
        report = TechnicalValidationGateEvaluator(policy()).evaluate(
            mutate_document(
                documents,
                "FIN-P08-WF-001",
                "current_bar_in_reference_channel",
                True,
            )
        )
        self.assertIs(report.outcome, GateOutcome.FAIL)
        self.assertTrue(
            any(
                issue.code == "BREAKOUT_REFERENCE_LEAKAGE"
                for issue in report.issues
            )
        )

        report = TechnicalValidationGateEvaluator(policy()).evaluate(
            mutate_document(
                documents,
                "FIN-P08-WF-001",
                "expansion_vote_semantics",
                "SECOND_INDEPENDENT_VOTE",
            )
        )
        self.assertIs(report.outcome, GateOutcome.FAIL)
        self.assertTrue(
            any(
                issue.code == "BREAKOUT_EXPANSION_DOUBLE_COUNT_RISK"
                for issue in report.issues
            )
        )

    def test_p08g_timeframes_must_remain_related(self) -> None:
        report = TechnicalValidationGateEvaluator(policy()).evaluate(
            mutate_document(
                canonical_documents(),
                "FIN-P08-WG-001",
                "cross_timeframe_independence_status",
                "INDEPENDENT",
            )
        )
        self.assertIs(report.outcome, GateOutcome.FAIL)
        self.assertTrue(
            any(
                issue.code == "MULTI_TIMEFRAME_DOUBLE_COUNT_RISK"
                for issue in report.issues
            )
        )

    def test_p08h_cluster_and_threshold_authority_are_mandatory(self) -> None:
        documents = canonical_documents()
        mutations = (
            ("cluster_vote_cap", 2, "CLUSTER_VOTE_CAP_INVALID"),
            (
                "numeric_dependence_decision_semantics",
                "THRESHOLD_CLASSIFIED",
                "NUMERIC_DEPENDENCE_OVERCLAIM",
            ),
            (
                "numeric_dependence_threshold",
                "0.7",
                "UNCALIBRATED_CORRELATION_THRESHOLD",
            ),
            (
                "production_fusion_threshold_owner",
                "P08",
                "FUSION_THRESHOLD_AUTHORITY_DRIFT",
            ),
            (
                "unregistered_direct_dependency_semantics",
                "INDEPENDENT",
                "UNREGISTERED_DEPENDENCY_OVERCLAIM",
            ),
        )
        for key, value, code in mutations:
            report = TechnicalValidationGateEvaluator(policy()).evaluate(
                mutate_document(
                    documents,
                    "FIN-P08-WH-001",
                    key,
                    value,
                )
            )
            self.assertIs(report.outcome, GateOutcome.FAIL)
            self.assertTrue(
                any(issue.code == code for issue in report.issues)
            )

    def test_malformed_closure_evidence_fails(self) -> None:
        documents = canonical_documents()
        item = next(
            candidate
            for candidate in policy().required_workstreams
            if candidate.task_id == "FIN-P08-WD-001"
        )
        document = json.loads(
            documents[item.document].decode("utf-8")
        )
        assert isinstance(document, dict)
        closure = document["closure_evidence"]
        assert isinstance(closure, dict)
        closure["post_merge_artifact_sha256"] = "bad"
        documents[item.document] = (
            json.dumps(
                document,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            )
            + "\n"
        ).encode("utf-8")
        report = TechnicalValidationGateEvaluator(policy()).evaluate(
            documents
        )
        self.assertIs(report.outcome, GateOutcome.FAIL)
        self.assertTrue(
            any(
                issue.code == "CLOSURE_EVIDENCE_INVALID"
                for issue in report.issues
            )
        )

    def test_gate_does_not_import_execution_or_network_clients(self) -> None:
        source = (
            ROOT
            / "packages/technical_intelligence/technical_validation_gate.py"
        ).read_text(encoding="utf-8").lower()
        for forbidden in (
            "adapters.execution",
            "packages.execution",
            "requests",
            "httpx",
            "websocket",
            "boto3",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
