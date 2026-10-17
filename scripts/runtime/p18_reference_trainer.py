#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    request = json.loads(args.request.read_text(encoding="utf-8"))
    if not isinstance(request, dict):
        raise RuntimeError("training request must be an object")
    request_id = digest(request)
    candidate_id = digest(
        {
            "kind": "P18_SANDBOX_REFERENCE_CANDIDATE",
            "request_id": request_id,
            "dataset_id": request["dataset_id"],
            "experiment_id": request["experiment_id"],
            "seed": request["seed"],
        }
    )
    artifact_id = digest(
        {
            "candidate_model_id": candidate_id,
            "trainer": "SANDBOX_REFERENCE_TRAINER_V1",
        }
    )
    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P18_SANDBOX_TRAINER_OUTPUT",
        "request_id": request_id,
        "candidate_model_id": candidate_id,
        "model_artifact_sha256": artifact_id,
        "metrics": {
            "loss": "0.04",
            "sharpe": "1.30",
            "max_drawdown_bps": "350"
        }
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
