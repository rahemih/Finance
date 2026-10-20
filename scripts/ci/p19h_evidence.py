#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Mapping, cast

from packages.shadow.shadow_validation_gate import (
    ReproducibilityGateSummary,
    ShadowGateWorkstreamRecord,
    ShadowValidationGatePolicy,
    certify_g10_shadow_validated,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/shadow/shadow-validation-gate-policy.json"
MANIFEST_PATHS = {
    "P19-A": ROOT / "docs/14-shadow/p19-a-shadow-decisioning.json",
    "P19-B": ROOT / "docs/14-shadow/p19-b-data-replay.json",
    "P19-C": ROOT / "docs/14-shadow/p19-c-decision-replay.json",
    "P19-D": ROOT / "docs/14-shadow/p19-d-incident-replay.json",
    "P19-E": ROOT / "docs/14-shadow/p19-e-digital-twin-fill-slippage.json",
    "P19-F": ROOT / "docs/14-shadow/p19-f-paper-live-drift-metrics.json",
    "P19-G": ROOT / "docs/14-shadow/p19-g-deterministic-reproducibility.json",
}
EXPECTED_EVIDENCE_KINDS = {
    "P19-A": "NEXUS_QUANT_P19A_SHADOW_DECISION_EVIDENCE",
    "P19-B": "NEXUS_QUANT_P19B_DATA_REPLAY_EVIDENCE",
    "P19-C": "NEXUS_QUANT_P19C_DECISION_REPLAY_EVIDENCE",
    "P19-D": "NEXUS_QUANT_P19D_INCIDENT_REPLAY_EVIDENCE",
    "P19-E": "NEXUS_QUANT_P19E_DIGITAL_TWIN_FILL_EVIDENCE",
    "P19-F": "NEXUS_QUANT_P19F_EXECUTION_DRIFT_EVIDENCE",
    "P19-G": "NEXUS_QUANT_P19G_DETERMINISTIC_REPRODUCIBILITY_EVIDENCE",
}


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"object required: {path}")
    return value


def mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise RuntimeError(f"{field} must be object")
    return cast(Mapping[str, object], value)


def text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"{field} must be non-empty text")
    return value.strip()


def require_false(value: Mapping[str, object], field: str, *, owner: str) -> None:
    if field in value and value.get(field) is not False:
        raise RuntimeError(f"{owner}.{field} must be false")


def verify_safety(value: Mapping[str, object], *, owner: str) -> None:
    for field in (
        "g10_authority",
        "production_readiness_authority",
        "production_readiness",
        "execution_authority",
        "order_routing_authority",
        "broker_exchange_routing",
        "p20_started",
        "automatic_p20_activation",
        "live_execution_validated",
        "broker_certification_validated",
        "profitability_guarantee",
    ):
        require_false(value, field, owner=owner)
    if "live_trading" in value and value.get("live_trading") != "DISABLED":
        raise RuntimeError(f"{owner}.live_trading must remain DISABLED")
    if "auto_trading" in value and value.get("auto_trading") != "DISABLED":
        raise RuntimeError(f"{owner}.auto_trading must remain DISABLED")


def main() -> int:
    parser = argparse.ArgumentParser()
    for suffix in ("a","b","c","d","e","f","g"):
        parser.add_argument(f"--p19{suffix}", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    evidence_paths = {
        "P19-A": args.p19a,
        "P19-B": args.p19b,
        "P19-C": args.p19c,
        "P19-D": args.p19d,
        "P19-E": args.p19e,
        "P19-F": args.p19f,
        "P19-G": args.p19g,
    }
    evidence = {ws: load(path) for ws, path in evidence_paths.items()}
    manifests = {ws: load(path) for ws, path in MANIFEST_PATHS.items()}

    for workstream in (
        "P19-A","P19-B","P19-C","P19-D","P19-E","P19-F","P19-G"
    ):
        item = evidence[workstream]
        manifest = manifests[workstream]
        if item.get("kind") != EXPECTED_EVIDENCE_KINDS[workstream]:
            raise RuntimeError(f"{workstream} evidence kind mismatch")
        if item.get("phase") != "P19" or item.get("workstream") != workstream:
            raise RuntimeError(f"{workstream} evidence phase/workstream mismatch")
        if manifest.get("state") != "CANONICAL_COMPLETE":
            raise RuntimeError(f"{workstream} manifest must be CANONICAL_COMPLETE")
        if manifest.get("lock") != "RELEASED":
            raise RuntimeError(f"{workstream} manifest lock must be RELEASED")
        verify_safety(item, owner=f"{workstream}.evidence")
        verify_safety(manifest, owner=f"{workstream}.manifest")

    g = evidence["P19-G"]
    if g.get("coverage_state") != "P19_A_TO_F_COMPLETE":
        raise RuntimeError("P19-G coverage state mismatch")
    if g.get("evidence_pair_match") != "BYTE_IDENTICAL":
        raise RuntimeError("P19-G evidence pair match must be BYTE_IDENTICAL")
    if g.get("cross_workstream_lineage") != "VERIFIED":
        raise RuntimeError("P19-G cross-workstream lineage must be VERIFIED")
    if g.get("claim_scope") != "REFERENCE_REPRODUCIBILITY_ONLY":
        raise RuntimeError("P19-G claim scope drift")
    if g.get("live_empirical_status") != "UNAVAILABLE_PRE_P20_H":
        raise RuntimeError("P19-G Live empirical status drift")
    if g.get("live_drift_validated") is not False:
        raise RuntimeError("P19-G cannot validate Live drift")

    evidence_hashes = mapping(
        g.get("workstream_evidence_sha256"),
        field="P19-G.workstream_evidence_sha256",
    )
    manifest_hashes = mapping(
        g.get("workstream_manifest_sha256"),
        field="P19-G.workstream_manifest_sha256",
    )
    for workstream in ("P19-A","P19-B","P19-C","P19-D","P19-E","P19-F"):
        if evidence_hashes.get(workstream) != file_sha(evidence_paths[workstream]):
            raise RuntimeError(f"{workstream} same-run evidence identity mismatch")
        if manifest_hashes.get(workstream) != file_sha(MANIFEST_PATHS[workstream]):
            raise RuntimeError(f"{workstream} canonical manifest identity mismatch")

    f = evidence["P19-F"]
    if f.get("claim_scope") != "REFERENCE_ONLY":
        raise RuntimeError("P19-F claim scope must remain REFERENCE_ONLY")
    if f.get("live_empirical_status") != "UNAVAILABLE_PRE_P20_H":
        raise RuntimeError("P19-F Live empirical status drift")
    if f.get("live_drift_validated") is not False:
        raise RuntimeError("P19-F cannot validate Live drift")

    policy = ShadowValidationGatePolicy.from_path(POLICY_PATH)
    records: list[ShadowGateWorkstreamRecord] = []
    for workstream in policy.required_workstreams:
        item = evidence[workstream]
        manifest = manifests[workstream]
        claim_scope: str | None = None
        live_status: str | None = None
        live_validated: bool | None = None
        if workstream == "P19-F":
            claim_scope = text(item.get("claim_scope"), field="P19-F.claim_scope")
            live_status = text(
                item.get("live_empirical_status"),
                field="P19-F.live_empirical_status",
            )
            live_validated = cast(bool, item.get("live_drift_validated"))
        elif workstream == "P19-G":
            claim_scope = text(item.get("claim_scope"), field="P19-G.claim_scope")
            live_status = text(
                item.get("live_empirical_status"),
                field="P19-G.live_empirical_status",
            )
            live_validated = cast(bool, item.get("live_drift_validated"))

        records.append(
            ShadowGateWorkstreamRecord(
                workstream=workstream,
                evidence_kind=text(item.get("kind"), field=f"{workstream}.kind"),
                evidence_sha256=file_sha(evidence_paths[workstream]),
                manifest_kind=text(
                    manifest.get("kind"),
                    field=f"{workstream}.manifest.kind",
                ),
                manifest_sha256=file_sha(MANIFEST_PATHS[workstream]),
                manifest_state=text(
                    manifest.get("state"),
                    field=f"{workstream}.manifest.state",
                ),
                lock_state=text(
                    manifest.get("lock"),
                    field=f"{workstream}.manifest.lock",
                ),
                claim_scope=claim_scope,
                live_empirical_status=live_status,
                live_drift_validated=live_validated,
            )
        )

    reproducibility = ReproducibilityGateSummary(
        reproducibility_certificate_id=text(
            g.get("reproducibility_certificate_id"),
            field="P19-G.reproducibility_certificate_id",
        ),
        coverage_state=text(g.get("coverage_state"), field="coverage_state"),
        evidence_pair_match=text(
            g.get("evidence_pair_match"),
            field="evidence_pair_match",
        ),
        cross_workstream_lineage=text(
            g.get("cross_workstream_lineage"),
            field="cross_workstream_lineage",
        ),
        claim_scope=text(g.get("claim_scope"), field="claim_scope"),
        live_empirical_status=text(
            g.get("live_empirical_status"),
            field="live_empirical_status",
        ),
        live_drift_validated=cast(bool, g.get("live_drift_validated")),
    )

    gate = certify_g10_shadow_validated(
        policy=policy,
        workstream_records=records,
        reproducibility=reproducibility,
    )
    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P19H_G10_SHADOW_VALIDATION_EVIDENCE",
        "task_id": "FIN-P19-WH-001",
        "phase": "P19",
        "workstream": "P19-H",
        "gate_name": gate.gate_name,
        "state": gate.state,
        "gate_id": gate.gate_id,
        "gate_claim_scope": gate.gate_claim_scope,
        "policy_sha256": file_sha(POLICY_PATH),
        "policy_id": gate.policy_id,
        "workstream_coverage": list(gate.workstream_coverage),
        "workstream_record_ids": list(gate.workstream_record_ids),
        "workstream_evidence_sha256": {
            ws: file_sha(evidence_paths[ws]) for ws in gate.workstream_coverage
        },
        "workstream_manifest_sha256": {
            ws: file_sha(MANIFEST_PATHS[ws]) for ws in gate.workstream_coverage
        },
        "reproducibility_certificate_id": gate.reproducibility_certificate_id,
        "live_empirical_status": "UNAVAILABLE_PRE_P20_H",
        "live_drift_validated": False,
        "live_execution_validated": False,
        "broker_certification_validated": False,
        "production_readiness": False,
        "profitability_guarantee": False,
        "next_phase": gate.next_phase,
        "next_phase_state": gate.next_phase_state,
        "automatic_p20_activation": False,
        "execution_authority": False,
        "order_routing_authority": False,
        "broker_exchange_routing": False,
        "p20_started": False,
        "live_trading": "DISABLED",
        "auto_trading": "DISABLED",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"P19H_G10_SHADOW_VALIDATION=PASS "
        f"gate_id={gate.gate_id} output={args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
