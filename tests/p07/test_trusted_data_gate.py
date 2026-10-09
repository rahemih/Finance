from __future__ import annotations

import json
from pathlib import Path
import unittest

from packages.data_quality import (
    GateOutcome,
    TrustedDataGateEvaluator,
    TrustedDataGatePolicy,
)

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/data-quality/trusted-data-gate-policy.json"


def policy() -> TrustedDataGatePolicy:
    return TrustedDataGatePolicy.from_path(POLICY)


def documents() -> dict[str, bytes]:
    value = policy()
    return {
        item.document: (ROOT / item.document).read_bytes()
        for item in value.required_workstreams
    }


def mutate(path: str, docs: dict[str, bytes], field_path: tuple[str, ...], value: object) -> None:
    raw = json.loads(docs[path].decode("utf-8"))
    target = raw
    for part in field_path[:-1]:
        target = target[part]
    target[field_path[-1]] = value
    docs[path] = (json.dumps(raw, indent=2, sort_keys=True) + "\n").encode("utf-8")


class TrustedDataGateTests(unittest.TestCase):
    def test_canonical_p07_a_through_g_pass(self):
        result = TrustedDataGateEvaluator(policy()).evaluate(documents())
        self.assertTrue(result.is_pass)
        self.assertEqual(result.outcome, GateOutcome.PASS)
        self.assertEqual(len(result.certified_task_ids), 7)
        self.assertEqual(result.live_trading, "DISABLED")
        self.assertEqual(result.auto_trading, "DISABLED")
        self.assertEqual(result.next_phase, "P08")
        self.assertEqual(result.next_phase_state, "NOT_STARTED_OWNER_PHASE_AUTHORIZATION_REQUIRED")

    def test_missing_required_workstream_fails_closed(self):
        docs = documents()
        docs.pop("docs/07-data/p07-a-schema-validators.json")
        result = TrustedDataGateEvaluator(policy()).evaluate(docs)
        self.assertFalse(result.is_pass)
        self.assertIn("MISSING_DOCUMENT", {issue.code for issue in result.issues})

    def test_non_canonical_state_fails_closed(self):
        docs = documents()
        path = "docs/07-data/p07-b-completeness-duplicates.json"
        mutate(path, docs, ("state",), "IN_PROGRESS")
        result = TrustedDataGateEvaluator(policy()).evaluate(docs)
        self.assertIn("NON_CANONICAL_STATE", {issue.code for issue in result.issues})

    def test_non_released_lock_fails_closed(self):
        docs = documents()
        path = "docs/07-data/p07-c-staleness-outlier-sequence.json"
        mutate(path, docs, ("closure", "lock"), "ACQUIRED")
        result = TrustedDataGateEvaluator(policy()).evaluate(docs)
        self.assertIn("LOCK_NOT_RELEASED", {issue.code for issue in result.issues})

    def test_malformed_closure_evidence_fails_closed(self):
        docs = documents()
        path = "docs/07-data/p07-d-cross-provider-comparison.json"
        mutate(path, docs, ("closure", "post_merge_artifact_digest"), "bad")
        result = TrustedDataGateEvaluator(policy()).evaluate(docs)
        self.assertIn("INVALID_ARTIFACT_EVIDENCE", {issue.code for issue in result.issues})

    def test_enabled_trading_fails_closed(self):
        docs = documents()
        path = "docs/07-data/p07-a-schema-validators.json"
        mutate(path, docs, ("live_trading",), "ENABLED")
        result = TrustedDataGateEvaluator(policy()).evaluate(docs)
        self.assertIn("LIVE_TRADING_SAFETY_VIOLATION", {issue.code for issue in result.issues})

    def test_country_assumption_fails_closed(self):
        docs = documents()
        path = "docs/07-data/p07-b-completeness-duplicates.json"
        mutate(path, docs, ("country_assumption",), "SOME_COUNTRY")
        result = TrustedDataGateEvaluator(policy()).evaluate(docs)
        self.assertIn("COUNTRY_ASSUMPTION_VIOLATION", {issue.code for issue in result.issues})

    def test_feature_quality_adapter_invariant_fails_closed(self):
        docs = documents()
        path = "docs/07-data/p07-e-provenance-confidence.json"
        mutate(path, docs, ("feature_quality_adapter",), False)
        result = TrustedDataGateEvaluator(policy()).evaluate(docs)
        self.assertIn("FEATURE_QUALITY_ADAPTER_VIOLATION", {issue.code for issue in result.issues})

    def test_non_accepted_downstream_invariant_fails_closed(self):
        docs = documents()
        path = "docs/07-data/p07-f-quarantine-fail-closed-routing.json"
        mutate(path, docs, ("non_accepted_downstream_allowed",), True)
        result = TrustedDataGateEvaluator(policy()).evaluate(docs)
        self.assertIn("FAIL_CLOSED_ROUTING_VIOLATION", {issue.code for issue in result.issues})

    def test_no_data_must_remain_blocking(self):
        docs = documents()
        path = "docs/07-data/p07-g-quality-dashboards-slos.json"
        mutate(path, docs, ("no_data_blocking",), False)
        result = TrustedDataGateEvaluator(policy()).evaluate(docs)
        self.assertIn("NO_DATA_BLOCKING_VIOLATION", {issue.code for issue in result.issues})

    def test_malformed_json_yields_fail_not_crash(self):
        docs = documents()
        docs["docs/07-data/p07-a-schema-validators.json"] = b"{bad"
        result = TrustedDataGateEvaluator(policy()).evaluate(docs)
        self.assertIn("MALFORMED_DOCUMENT", {issue.code for issue in result.issues})

    def test_unexpected_document_fails_closed(self):
        docs = documents()
        docs["docs/07-data/unexpected.json"] = b"{}"
        result = TrustedDataGateEvaluator(policy()).evaluate(docs)
        self.assertIn("UNEXPECTED_DOCUMENT", {issue.code for issue in result.issues})

    def test_input_order_does_not_change_gate_fingerprint(self):
        docs = documents()
        first = TrustedDataGateEvaluator(policy()).evaluate(docs)
        second = TrustedDataGateEvaluator(policy()).evaluate(
            dict(reversed(list(docs.items())))
        )
        self.assertEqual(first.fingerprint, second.fingerprint)
        self.assertEqual(first.document_sha256s, second.document_sha256s)


if __name__ == "__main__":
    unittest.main()
