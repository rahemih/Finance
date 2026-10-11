from __future__ import annotations

import json
from pathlib import Path
import unittest

from packages.fundamental_intelligence.p10_validation import P10ValidationEvaluator, P10ValidationPolicy

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/fundamental-intelligence/p10-validation-policy.json"


def policy() -> P10ValidationPolicy:
    return P10ValidationPolicy.from_path(POLICY_PATH)


def canonical_documents(p: P10ValidationPolicy) -> dict[str, bytes]:
    return {item.document: (ROOT / item.document).read_bytes() for item in p.required_workstreams}


def mutate(documents: dict[str, bytes], path: str, field: str, value: object) -> dict[str, bytes]:
    output = dict(documents)
    payload = json.loads(output[path].decode("utf-8"))
    assert isinstance(payload, dict)
    payload[field] = value
    output[path] = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
    return output


class P10ValidationTests(unittest.TestCase):
    def test_policy_is_ci_only_and_p11_owner_gated(self) -> None:
        p = policy()
        self.assertEqual(p.performance_semantics, "CI_REGRESSION_BUDGET_NOT_PRODUCTION_SLO")
        self.assertEqual(p.p10_unit_suite_max_seconds, 60)
        self.assertFalse(p.network_required)
        self.assertFalse(p.production_slo_certified)
        self.assertFalse(p.production_provider_performance_certified)
        self.assertEqual(p.next_phase, "P11")
        self.assertEqual(p.next_phase_state, "OWNER_PHASE_AUTHORIZATION_REQUIRED")

    def test_canonical_p10_a_through_g_pass(self) -> None:
        p = policy()
        report = P10ValidationEvaluator(p).evaluate(canonical_documents(p))
        self.assertEqual(report.outcome, "PASS")
        self.assertEqual(report.issues, ())
        self.assertEqual(report.certified_task_ids, tuple(x.task_id for x in p.required_workstreams))

    def test_input_order_is_deterministic(self) -> None:
        p = policy()
        docs = canonical_documents(p)
        a = P10ValidationEvaluator(p).evaluate(docs)
        b = P10ValidationEvaluator(p).evaluate(dict(reversed(list(docs.items()))))
        self.assertEqual(a.fingerprint, b.fingerprint)

    def test_missing_or_unexpected_document_fails_closed(self) -> None:
        p = policy()
        docs = canonical_documents(p)
        missing = dict(docs)
        missing.pop(p.required_workstreams[0].document)
        self.assertEqual(P10ValidationEvaluator(p).evaluate(missing).outcome, "FAIL")
        unexpected = dict(docs)
        unexpected["unexpected.json"] = b"{}"
        self.assertEqual(P10ValidationEvaluator(p).evaluate(unexpected).outcome, "FAIL")

    def test_state_lock_and_safety_drift_fail_closed(self) -> None:
        p = policy()
        docs = canonical_documents(p)
        path = p.required_workstreams[-1].document
        for field, value in (
            ("state", "ACTIVE"),
            ("lock", "ACQUIRED"),
            ("live_trading", "ENABLED"),
            ("auto_trading", "ENABLED"),
            ("causal_market_impact_claim_allowed", True),
        ):
            with self.subTest(field=field):
                report = P10ValidationEvaluator(p).evaluate(mutate(docs, path, field, value))
                self.assertEqual(report.outcome, "FAIL")


if __name__ == "__main__":
    unittest.main()
