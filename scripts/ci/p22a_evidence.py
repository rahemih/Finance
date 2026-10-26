from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.operations.observability import ObservabilityPolicy, build_log, build_metric, build_trace


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    policy_path = Path("config/operations/observability-policy.json")
    policy = ObservabilityPolicy.from_path(policy_path)
    correlation = "0123456789abcdef0123456789abcdef"
    trace_id = "abcdef0123456789abcdef0123456789"
    span_id = "0123456789abcdef"

    metric = build_metric(
        policy,
        name="nexus_quant.operations.reference_latency",
        metric_kind="HISTOGRAM",
        value="7.250",
        unit="ms",
        observed_at_ns=1_000_000_000,
        correlation_id=correlation,
        attributes={"component": "operations", "phase": "P22", "workstream": "P22-A"},
    )
    trace = build_trace(
        policy,
        trace_id=trace_id,
        span_id=span_id,
        parent_span_id=None,
        operation="reference-observability-validation",
        status="OK",
        started_at_ns=1_000_000_000,
        ended_at_ns=1_000_007_250,
        correlation_id=correlation,
        attributes={"component": "operations", "phase": "P22", "workstream": "P22-A"},
    )
    log = build_log(
        policy,
        level="INFO",
        message="reference observability validation complete",
        observed_at_ns=1_000_007_250,
        correlation_id=correlation,
        trace_id=trace_id,
        span_id=span_id,
        attributes={"component": "operations", "outcome": "PASS", "workstream": "P22-A"},
    )

    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P22A_OBSERVABILITY_EVIDENCE",
        "task_id": "FIN-P22-WA-001",
        "state": "REFERENCE_OBSERVABILITY_VALIDATED_PASS",
        "policy_id": policy.policy_id,
        "policy_sha256": hashlib.sha256(policy_path.read_bytes()).hexdigest(),
        "metric": {"record_id": metric.record_id, **metric.payload()},
        "log": {"record_id": log.record_id, **log.payload()},
        "trace": {"record_id": trace.record_id, **trace.payload()},
        "safety": {
            "network_mode": "DISABLED",
            "credential_mode": "NONE",
            "vendor_export": False,
            "automatic_system_state_mutation": False,
            "automatic_risk_policy_relaxation": False,
            "live_execution_authority": False,
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        },
        "next": "P22-B_NOT_STARTED",
    }
    payload["evidence_id"] = hashlib.sha256(_canonical(payload)).hexdigest()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(_canonical(payload) + b"\n")
    print(f"P22A_EVIDENCE=PASS evidence_id={payload['evidence_id']} output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
