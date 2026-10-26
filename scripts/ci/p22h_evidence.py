from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.operations.incident_postmortem import (
    IncidentPostmortemPolicy,
    build_corrective_action,
    build_incident_event,
    build_incident_record,
    build_postmortem,
)


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    policy_path = Path("config/operations/incident-postmortem-policy.json")
    policy = IncidentPostmortemPolicy.from_path(policy_path)
    corr = "0123456789abcdef0123456789abcdef"

    detected = build_incident_event(
        policy,
        event_code="DETECTED",
        occurred_at_ns=100,
        summary="Reference incident detected from deterministic operational evidence.",
        evidence_refs=("a" * 64,),
        correlation_id=corr,
    )
    contained = build_incident_event(
        policy,
        event_code="CONTAINED",
        occurred_at_ns=200,
        summary="Reference incident containment recorded.",
        evidence_refs=("b" * 64,),
        correlation_id=corr,
    )
    recovered = build_incident_event(
        policy,
        event_code="RECOVERED",
        occurred_at_ns=300,
        summary="Reference recovery validation recorded.",
        evidence_refs=("c" * 64,),
        correlation_id=corr,
    )
    incident = build_incident_record(
        policy,
        severity="SEV2",
        state="RECOVERED",
        opened_at_ns=100,
        contained_at_ns=200,
        recovered_at_ns=300,
        closed_at_ns=None,
        impact_scopes=("OPERATIONS", "DATA"),
        timeline=(detected, contained, recovered),
        correlation_id=corr,
    )
    action = build_corrective_action(
        policy,
        action_code="ADD_RECOVERY_ASSERTION",
        owner_role="OPERATIONS_OWNER",
        priority="P1",
        verification_required=True,
        evidence_refs=("d" * 64,),
    )
    postmortem = build_postmortem(
        policy,
        incident=incident,
        root_cause_code="UPSTREAM_TIMEOUT",
        root_cause_summary="Reference root cause supported by deterministic evidence.",
        contributing_factors=("RETRY_PRESSURE", "STALE_DEPENDENCY"),
        evidence_refs=("a" * 64, "b" * 64, "c" * 64),
        corrective_actions=(action,),
        created_at_ns=400,
    )

    if incident.state != "RECOVERED":
        raise SystemExit("P22-H reference incident must be recovered")
    if not postmortem.complete:
        raise SystemExit("P22-H postmortem must be complete")
    if postmortem.execution_authority or postmortem.runtime_state_mutation:
        raise SystemExit("P22-H postmortem unexpectedly gained runtime authority")
    if action.execution_authority or action.automatic_remediation:
        raise SystemExit("P22-H corrective action unexpectedly gained remediation authority")

    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P22H_INCIDENT_POSTMORTEM_EVIDENCE",
        "task_id": "FIN-P22-WH-001",
        "state": "REFERENCE_INCIDENT_POSTMORTEM_VALIDATED_PASS",
        "policy_id": policy.policy_id,
        "policy_sha256": hashlib.sha256(policy_path.read_bytes()).hexdigest(),
        "incident": {"incident_id": incident.incident_id, **incident.payload()},
        "postmortem": {"postmortem_id": postmortem.postmortem_id, **postmortem.payload()},
        "claim_scope": "DETERMINISTIC_REFERENCE_INCIDENT_POSTMORTEM",
        "safety": {
            "corrective_action_execution_authority": False,
            "automatic_remediation": False,
            "person_name_fields_allowed": False,
            "pii_fields_allowed": False,
            "network_mode": "DISABLED",
            "credential_mode": "NONE",
            "runtime_state_mutation": False,
            "external_order_authority": False,
            "live_execution_authority": False,
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        },
        "next": "P22-I_NOT_STARTED",
    }
    payload["evidence_id"] = hashlib.sha256(_canonical(payload)).hexdigest()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(_canonical(payload) + b"\n")
    print(f"P22H_EVIDENCE=PASS evidence_id={payload['evidence_id']} output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
