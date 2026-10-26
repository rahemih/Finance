from __future__ import annotations

from pathlib import Path
import unittest

from packages.operations.observability import (
    ObservabilityError,
    ObservabilityPolicy,
    build_log,
    build_metric,
    build_trace,
)


POLICY = Path("config/operations/observability-policy.json")
CORR = "0123456789abcdef0123456789abcdef"
TRACE = "abcdef0123456789abcdef0123456789"
SPAN = "0123456789abcdef"


class ObservabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = ObservabilityPolicy.from_path(POLICY)

    def test_reference_only_policy_is_stable(self) -> None:
        self.assertEqual(len(self.policy.policy_id), 64)
        self.assertEqual(self.policy.metric_prefix, "nexus_quant.")

    def test_metric_is_deterministic_and_namespaced(self) -> None:
        kwargs = dict(
            name="nexus_quant.execution.latency",
            metric_kind="histogram",
            value="12.500",
            unit="ms",
            observed_at_ns=10,
            correlation_id=CORR,
            attributes={"component": "execution", "phase": "P22"},
        )
        first = build_metric(self.policy, **kwargs)
        second = build_metric(self.policy, **kwargs)
        self.assertEqual(first.record_id, second.record_id)
        self.assertEqual(first.value, "12.5")
        self.assertEqual(first.attributes, (("component", "execution"), ("phase", "P22")))

    def test_metric_namespace_and_numeric_fail_closed(self) -> None:
        with self.assertRaises(ObservabilityError):
            build_metric(self.policy, name="latency", metric_kind="GAUGE", value=1, unit="ms", observed_at_ns=1, correlation_id=CORR)
        with self.assertRaises(ObservabilityError):
            build_metric(self.policy, name="nexus_quant.x", metric_kind="GAUGE", value=float("inf"), unit="1", observed_at_ns=1, correlation_id=CORR)

    def test_bounded_cardinality_rejects_unapproved_dimension(self) -> None:
        with self.assertRaises(ObservabilityError):
            build_metric(
                self.policy,
                name="nexus_quant.x",
                metric_kind="COUNTER",
                value=1,
                unit="1",
                observed_at_ns=1,
                correlation_id=CORR,
                attributes={"user_id": "high-cardinality"},
            )

    def test_secret_bearing_attributes_and_messages_fail_closed(self) -> None:
        with self.assertRaises(ObservabilityError):
            build_log(
                self.policy,
                level="INFO",
                message="safe",
                observed_at_ns=1,
                correlation_id=CORR,
                attributes={"api_key": "nope"},
            )
        with self.assertRaises(ObservabilityError):
            build_log(
                self.policy,
                level="INFO",
                message="Authorization: Bearer abc",
                observed_at_ns=1,
                correlation_id=CORR,
            )

    def test_log_trace_linkage_requires_pair(self) -> None:
        with self.assertRaises(ObservabilityError):
            build_log(
                self.policy,
                level="ERROR",
                message="failed safely",
                observed_at_ns=2,
                correlation_id=CORR,
                trace_id=TRACE,
            )
        record = build_log(
            self.policy,
            level="ERROR",
            message="failed safely",
            observed_at_ns=2,
            correlation_id=CORR,
            trace_id=TRACE,
            span_id=SPAN,
            attributes={"outcome": "SAFE_HOLD"},
        )
        self.assertEqual(record.trace_id, TRACE)
        self.assertEqual(record.span_id, SPAN)

    def test_trace_time_and_identity_fail_closed(self) -> None:
        with self.assertRaises(ObservabilityError):
            build_trace(
                self.policy,
                trace_id="bad",
                span_id=SPAN,
                parent_span_id=None,
                operation="reconcile",
                status="OK",
                started_at_ns=1,
                ended_at_ns=2,
                correlation_id=CORR,
            )
        with self.assertRaises(ObservabilityError):
            build_trace(
                self.policy,
                trace_id=TRACE,
                span_id=SPAN,
                parent_span_id=None,
                operation="reconcile",
                status="OK",
                started_at_ns=5,
                ended_at_ns=4,
                correlation_id=CORR,
            )

    def test_trace_is_deterministic(self) -> None:
        kwargs = dict(
            trace_id=TRACE,
            span_id=SPAN,
            parent_span_id=None,
            operation="position-reconciliation",
            status="OK",
            started_at_ns=100,
            ended_at_ns=125,
            correlation_id=CORR,
            attributes={"component": "position_management", "workstream": "P21-F"},
        )
        first = build_trace(self.policy, **kwargs)
        second = build_trace(self.policy, **kwargs)
        self.assertEqual(first.record_id, second.record_id)
        self.assertEqual(first.ended_at_ns - first.started_at_ns, 25)

    def test_no_runtime_authority_is_exposed(self) -> None:
        content = POLICY.read_text(encoding="utf-8")
        self.assertIn('"network_mode": "DISABLED"', content)
        self.assertIn('"credential_mode": "NONE"', content)
        self.assertIn('"vendor_export": false', content)
        self.assertIn('"automatic_system_state_mutation": false', content)
        self.assertIn('"automatic_risk_policy_relaxation": false', content)
        self.assertIn('"live_execution_authority": false', content)
        self.assertIn('"live_trading": "DISABLED"', content)
        self.assertIn('"auto_trading": "DISABLED"', content)


if __name__ == "__main__":
    unittest.main()
