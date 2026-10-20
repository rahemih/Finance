#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Mapping, cast

from packages.shadow.reproducibility import (
    ReproducibilityCertificate,
    ReproducibilityPolicy,
    WorkstreamReproducibilityRecord,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/shadow/deterministic-reproducibility-policy.json"

MANIFEST_PATHS = {
    "P19-A": ROOT / "docs/14-shadow/p19-a-shadow-decisioning.json",
    "P19-B": ROOT / "docs/14-shadow/p19-b-data-replay.json",
    "P19-C": ROOT / "docs/14-shadow/p19-c-decision-replay.json",
    "P19-D": ROOT / "docs/14-shadow/p19-d-incident-replay.json",
    "P19-E": ROOT / "docs/14-shadow/p19-e-digital-twin-fill-slippage.json",
    "P19-F": ROOT / "docs/14-shadow/p19-f-paper-live-drift-metrics.json",
}
EXPECTED_EVIDENCE_KINDS = {
    "P19-A": "NEXUS_QUANT_P19A_SHADOW_DECISION_EVIDENCE",
    "P19-B": "NEXUS_QUANT_P19B_DATA_REPLAY_EVIDENCE",
    "P19-C": "NEXUS_QUANT_P19C_DECISION_REPLAY_EVIDENCE",
    "P19-D": "NEXUS_QUANT_P19D_INCIDENT_REPLAY_EVIDENCE",
    "P19-E": "NEXUS_QUANT_P19E_DIGITAL_TWIN_FILL_EVIDENCE",
    "P19-F": "NEXUS_QUANT_P19F_EXECUTION_DRIFT_EVIDENCE",
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
    if value.get(field) is not False:
        raise RuntimeError(f"{owner}.{field} must be false")


def verify_safety(value: Mapping[str, object], *, owner: str) -> None:
    for field in (
        "execution_authority",
        "order_routing_authority",
        "broker_exchange_routing",
        "p20_started",
    ):
        require_false(value, field, owner=owner)
    if value.get("live_trading") != "DISABLED":
        raise RuntimeError(f"{owner}.live_trading must remain DISABLED")
    if value.get("auto_trading") != "DISABLED":
        raise RuntimeError(f"{owner}.auto_trading must remain DISABLED")
    for optional in (
        "decision_authority",
        "fill_authority",
        "external_order_submission",
        "automatic_live_promotion",
        "g10_authority",
        "production_readiness_authority",
        "production_fill_accuracy_claim",
        "broker_truth",
    ):
        if optional in value and value.get(optional) is not False:
            raise RuntimeError(f"{owner}.{optional} must be false")


def exact_pair(left: Path, right: Path, *, workstream: str) -> dict[str, object]:
    left_bytes = left.read_bytes()
    right_bytes = right.read_bytes()
    if left_bytes != right_bytes:
        raise RuntimeError(f"{workstream} evidence pair is not byte-identical")
    evidence = load(left)
    if evidence.get("kind") != EXPECTED_EVIDENCE_KINDS[workstream]:
        raise RuntimeError(f"{workstream} evidence kind mismatch")
    if evidence.get("phase") != "P19" or evidence.get("workstream") != workstream:
        raise RuntimeError(f"{workstream} evidence phase/workstream mismatch")
    verify_safety(evidence, owner=f"{workstream}.evidence")
    return evidence


def same_sha(evidence: Mapping[str, object], field: str, path: Path, *, owner: str) -> None:
    expected = file_sha(path)
    if evidence.get(field) != expected:
        raise RuntimeError(f"{owner}.{field} lineage mismatch")


def main() -> int:
    parser = argparse.ArgumentParser()
    for suffix in ("a", "b", "c", "d", "e", "f"):
        parser.add_argument(f"--p19{suffix}-a", type=Path, required=True)
        parser.add_argument(f"--p19{suffix}-b", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    arg_pairs = {
        "P19-A": (args.p19a_a, args.p19a_b),
        "P19-B": (args.p19b_a, args.p19b_b),
        "P19-C": (args.p19c_a, args.p19c_b),
        "P19-D": (args.p19d_a, args.p19d_b),
        "P19-E": (args.p19e_a, args.p19e_b),
        "P19-F": (args.p19f_a, args.p19f_b),
    }
    evidence: dict[str, dict[str, object]] = {
        workstream: exact_pair(left, right, workstream=workstream)
        for workstream, (left, right) in arg_pairs.items()
    }

    a_path = arg_pairs["P19-A"][0]
    b_path = arg_pairs["P19-B"][0]
    c_path = arg_pairs["P19-C"][0]
    d_path = arg_pairs["P19-D"][0]
    e_path = arg_pairs["P19-E"][0]

    c = evidence["P19-C"]
    same_sha(c, "p19a_same_run_evidence_sha256", a_path, owner="P19-C")
    same_sha(c, "p19b_same_run_evidence_sha256", b_path, owner="P19-C")

    d = evidence["P19-D"]
    same_sha(d, "p19b_same_run_evidence_sha256", b_path, owner="P19-D")
    same_sha(d, "p19c_same_run_evidence_sha256", c_path, owner="P19-D")

    e = evidence["P19-E"]
    same_sha(e, "p19a_same_run_evidence_sha256", a_path, owner="P19-E")
    same_sha(e, "p19b_same_run_evidence_sha256", b_path, owner="P19-E")
    same_sha(e, "p19c_same_run_evidence_sha256", c_path, owner="P19-E")
    same_sha(e, "p19d_same_run_evidence_sha256", d_path, owner="P19-E")

    f = evidence["P19-F"]
    same_sha(f, "p19e_same_run_evidence_sha256", e_path, owner="P19-F")
    if f.get("claim_scope") != "REFERENCE_ONLY":
        raise RuntimeError("P19-F claim_scope must remain REFERENCE_ONLY")
    if f.get("live_empirical_status") != "UNAVAILABLE_PRE_P20_H":
        raise RuntimeError("P19-F Live empirical status drift")
    if f.get("live_drift_validated") is not False:
        raise RuntimeError("P19-F reference evidence cannot validate Live drift")

    manifest_refs = {
        "P19-B": ("p19a_manifest_sha256", "P19-A"),
        "P19-C": ("p19a_manifest_sha256", "P19-A"),
        "P19-C:B": ("p19b_manifest_sha256", "P19-B"),
        "P19-D": ("p19b_manifest_sha256", "P19-B"),
        "P19-D:C": ("p19c_manifest_sha256", "P19-C"),
        "P19-E": ("p19d_manifest_sha256", "P19-D"),
        "P19-F": ("p19e_manifest_sha256", "P19-E"),
    }
    for key, (field, upstream) in manifest_refs.items():
        owner = key.split(":", 1)[0]
        if evidence[owner].get(field) != file_sha(MANIFEST_PATHS[upstream]):
            raise RuntimeError(f"{owner}.{field} canonical manifest lineage mismatch")

    policy = ReproducibilityPolicy.from_path(POLICY_PATH)
    records: list[WorkstreamReproducibilityRecord] = []
    manifest_hashes: dict[str, str] = {}
    evidence_hashes: dict[str, str] = {}
    package_hashes: dict[str, str] = {}
    workstream_policy_hashes: dict[str, str] = {}

    for workstream in policy.required_workstreams:
        manifest_path = MANIFEST_PATHS[workstream]
        manifest = load(manifest_path)
        if manifest.get("state") != "CANONICAL_COMPLETE":
            raise RuntimeError(f"{workstream} manifest is not CANONICAL_COMPLETE")
        if manifest.get("lock") != "RELEASED":
            raise RuntimeError(f"{workstream} manifest lock is not RELEASED")
        verify_safety(manifest, owner=f"{workstream}.manifest")

        package_path = ROOT / text(manifest.get("package"), field=f"{workstream}.package")
        policy_path = ROOT / text(manifest.get("policy"), field=f"{workstream}.policy")
        if not package_path.is_file() or not policy_path.is_file():
            raise RuntimeError(f"{workstream} package/policy path missing")

        manifest_hashes[workstream] = file_sha(manifest_path)
        evidence_hashes[workstream] = file_sha(arg_pairs[workstream][0])
        package_hashes[workstream] = file_sha(package_path)
        workstream_policy_hashes[workstream] = file_sha(policy_path)

        records.append(
            WorkstreamReproducibilityRecord(
                workstream=workstream,
                evidence_kind=text(evidence[workstream].get("kind"), field="kind"),
                evidence_sha256=evidence_hashes[workstream],
                manifest_kind=text(manifest.get("kind"), field="manifest.kind"),
                manifest_sha256=manifest_hashes[workstream],
                package_sha256=package_hashes[workstream],
                policy_sha256=workstream_policy_hashes[workstream],
                manifest_state=text(manifest.get("state"), field="manifest.state"),
                lock_state=text(manifest.get("lock"), field="manifest.lock"),
                claim_scope=(
                    text(f.get("claim_scope"), field="P19-F.claim_scope")
                    if workstream == "P19-F"
                    else None
                ),
                live_empirical_status=(
                    text(
                        f.get("live_empirical_status"),
                        field="P19-F.live_empirical_status",
                    )
                    if workstream == "P19-F"
                    else None
                ),
                live_drift_validated=(
                    cast(bool, f.get("live_drift_validated"))
                    if workstream == "P19-F"
                    else None
                ),
            )
        )

    certificate = ReproducibilityCertificate.build(records=records, policy=policy)
    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P19G_DETERMINISTIC_REPRODUCIBILITY_EVIDENCE",
        "task_id": "FIN-P19-WG-001",
        "phase": "P19",
        "workstream": "P19-G",
        "state": "IN_PROGRESS_IMPLEMENTATION_EVIDENCE",
        "policy_sha256": file_sha(POLICY_PATH),
        "policy_id": policy.policy_id,
        "workstream_evidence_sha256": evidence_hashes,
        "workstream_manifest_sha256": manifest_hashes,
        "workstream_package_sha256": package_hashes,
        "workstream_policy_sha256": workstream_policy_hashes,
        "evidence_pair_match": "BYTE_IDENTICAL",
        "cross_workstream_lineage": "VERIFIED",
        "coverage_state": certificate.coverage_state,
        "record_ids": list(certificate.record_ids),
        "reproducibility_certificate_id": certificate.certificate_id,
        "claim_scope": certificate.claim_scope,
        "live_empirical_status": certificate.live_empirical_status,
        "live_drift_validated": certificate.live_drift_validated,
        "g10_authority": False,
        "production_readiness_authority": False,
        "execution_authority": False,
        "order_routing_authority": False,
        "broker_exchange_routing": False,
        "p19_active_workstream": "P19-G",
        "p20_started": False,
        "live_trading": "DISABLED",
        "auto_trading": "DISABLED",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"P19G_REPRODUCIBILITY_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
