from __future__ import annotations

import json
from pathlib import Path
import unittest

from packages.order_flow_liquidity.p09_validation import (
    P09ValidationEvaluator,
    P09ValidationPolicy,
)

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/order-flow-liquidity/p09-validation-policy.json"


def policy() -> P09ValidationPolicy:
    return P09ValidationPolicy.from_path(POLICY_PATH)


def canonical_documents(p: P09ValidationPolicy) -> dict[str, bytes]:
    return {
        item.document: (ROOT / item.document).read_bytes()
        for item in p.required_workstreams
    }


def mutate(
    documents: dict[str, bytes],
    path: str,
    mutate_fn: object,
) -> dict[str, bytes]:
    output = dict(documents)
    payload = json.loads(output[path].decode("utf-8"))
    assert isinstance(payload, dict)
    fn = mutate_fn
    assert callable(fn)
    fn(payload)
    output[path] = (
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")
    return output


class P09ValidationPolicyTests(unittest.TestCase):
    def test_policy_keeps_performance_ci_only_and_p10_gated(self) -> None:
        p = policy()
        self.assertEqual(p.performance_semantics, "CI_REGRESSION_BUDGET_NOT_PRODUCTION_SLO")
        self.assertEqual(p.p09_unit_suite_max_seconds, 60)
        self.assertFalse(p.network_required)
        self.assertFalse(p.production_slo_certified)
        self.assertFalse(p.profitability_certified)
        self.assertFalse(p.trade_success_probability_certified)
        self.assertFalse(p.production_execution_certified)
        self.assertFalse(p.production_provider_performance_certified)
        self.assertEqual(p.next_phase, "P10")
        self.assertEqual(p.next_phase_state, "OWNER_PHASE_AUTHORIZATION_REQUIRED")


class P09ValidationEvaluatorTests(unittest.TestCase):
    def test_canonical_p09_a_through_g_yields_pass(self) -> None:
        p = policy()
        report = P09ValidationEvaluator(p).evaluate(canonical_documents(p))
        self.assertEqual(report.outcome, "PASS")
        self.assertEqual(report.issues, ())
        self.assertEqual(
            report.certified_task_ids,
            tuple(item.task_id for item in p.required_workstreams),
        )
        self.assertEqual(report.live_trading, "DISABLED")
        self.assertEqual(report.auto_trading, "DISABLED")
        self.assertEqual(report.country_assumption, "NONE")
        self.assertEqual(report.next_phase_state, "OWNER_PHASE_AUTHORIZATION_REQUIRED")

    def test_input_order_does_not_change_fingerprint(self) -> None:
        p = policy()
        docs = canonical_documents(p)
        first = P09ValidationEvaluator(p).evaluate(docs)
        second = P09ValidationEvaluator(p).evaluate(dict(reversed(list(docs.items()))))
        self.assertEqual(first.outcome, "PASS")
        self.assertEqual(first.fingerprint, second.fingerprint)

    def test_missing_and_unexpected_documents_fail_closed(self) -> None:
        p = policy()
        docs = canonical_documents(p)
        missing = dict(docs)
        missing.pop(p.required_workstreams[0].document)
        report = P09ValidationEvaluator(p).evaluate(missing)
        self.assertEqual(report.outcome, "FAIL")
        self.assertIn("MISSING_DOCUMENT", {issue.code for issue in report.issues})

        unexpected = dict(docs)
        unexpected["unexpected.json"] = b"{}"
        report = P09ValidationEvaluator(p).evaluate(unexpected)
        self.assertEqual(report.outcome, "FAIL")
        self.assertIn("UNEXPECTED_DOCUMENT", {issue.code for issue in report.issues})

    def test_state_lock_safety_and_closure_evidence_fail_closed(self) -> None:
        p = policy()
        docs = canonical_documents(p)
        path = p.required_workstreams[0].document

        report = P09ValidationEvaluator(p).evaluate(
            mutate(docs, path, lambda x: x.__setitem__("state", "ACTIVE"))
        )
        self.assertEqual(report.outcome, "FAIL")

        report = P09ValidationEvaluator(p).evaluate(
            mutate(docs, path, lambda x: x.__setitem__("lock", "ACQUIRED"))
        )
        self.assertEqual(report.outcome, "FAIL")

        report = P09ValidationEvaluator(p).evaluate(
            mutate(docs, path, lambda x: x.__setitem__("live_trading", "ENABLED"))
        )
        self.assertEqual(report.outcome, "FAIL")

        report = P09ValidationEvaluator(p).evaluate(
            mutate(docs, path, lambda x: x.pop("canonical_closure"))
        )
        self.assertEqual(report.outcome, "FAIL")
        self.assertIn("MISSING_CLOSURE_EVIDENCE", {issue.code for issue in report.issues})

    def test_p09a_and_p09b_semantic_drift_fail_closed(self) -> None:
        p = policy()
        docs = canonical_documents(p)
        a = p.required_workstreams[0].document
        b = p.required_workstreams[1].document

        def break_a(payload: dict[str, object]) -> None:
            semantics = payload["spot_fx_volume_semantics"]
            assert isinstance(semantics, dict)
            semantics["consolidated_market_volume_claim_allowed"] = True

        report = P09ValidationEvaluator(p).evaluate(mutate(docs, a, break_a))
        self.assertEqual(report.outcome, "FAIL")
        self.assertIn("P09A_PROXY_BOUNDARY_DRIFT", {issue.code for issue in report.issues})

        report = P09ValidationEvaluator(p).evaluate(
            mutate(docs, b, lambda x: x.__setitem__("unknown_volume_enters_delta", True))
        )
        self.assertEqual(report.outcome, "FAIL")
        self.assertIn("P09B_FLOW_BOUNDARY_DRIFT", {issue.code for issue in report.issues})

    def test_p09c_d_e_semantic_drift_fail_closed(self) -> None:
        p = policy()
        docs = canonical_documents(p)
        c = p.required_workstreams[2].document
        d = p.required_workstreams[3].document
        e = p.required_workstreams[4].document

        report = P09ValidationEvaluator(p).evaluate(
            mutate(docs, c, lambda x: x.__setitem__("tick_volume_profile_allowed", True))
        )
        self.assertIn("P09C_PROFILE_BOUNDARY_DRIFT", {issue.code for issue in report.issues})

        report = P09ValidationEvaluator(p).evaluate(
            mutate(docs, d, lambda x: x.__setitem__("locked_or_crossed_book_allowed", True))
        )
        self.assertIn("P09D_BOOK_BOUNDARY_DRIFT", {issue.code for issue in report.issues})

        report = P09ValidationEvaluator(p).evaluate(
            mutate(docs, e, lambda x: x.__setitem__("fillability_claim_allowed", True))
        )
        self.assertIn("P09E_CAPACITY_BOUNDARY_DRIFT", {issue.code for issue in report.issues})

    def test_p09f_and_p09g_semantic_drift_fail_closed(self) -> None:
        p = policy()
        docs = canonical_documents(p)
        f = p.required_workstreams[5].document
        g = p.required_workstreams[6].document

        report = P09ValidationEvaluator(p).evaluate(
            mutate(docs, f, lambda x: x.__setitem__("crowding_score_allowed", True))
        )
        self.assertIn("P09F_CROWDING_BOUNDARY_DRIFT", {issue.code for issue in report.issues})

        report = P09ValidationEvaluator(p).evaluate(
            mutate(docs, g, lambda x: x.__setitem__("weighted_confidence_score_allowed", True))
        )
        self.assertIn("P09G_CONFIDENCE_BOUNDARY_DRIFT", {issue.code for issue in report.issues})


if __name__ == "__main__":
    unittest.main()
