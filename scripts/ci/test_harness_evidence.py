#!/usr/bin/env python3
"""Generate deterministic P04-E test-harness evidence without timestamps."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from tests.harness import ReplayTape


ROOT = Path(__file__).resolve().parents[2]
REPLAY = ROOT / "tests/fixtures/foundation/replay-basic.json"
PROVIDER = ROOT / "tests/fixtures/foundation/provider-unknown.json"
HARNESS = ROOT / "tests/harness/core.py"
TESTS = ROOT / "tests/foundation/test_harness.py"
DOC = ROOT / "docs/06-engineering/TEST-HARNESS.md"
MANIFEST = ROOT / "docs/06-engineering/test-harness.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(output: Path) -> None:
    tape = ReplayTape.from_fixture(REPLAY)
    inputs = [REPLAY, PROVIDER, HARNESS, TESTS, DOC, MANIFEST]
    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_TEST_HARNESS_EVIDENCE",
        "replay": {
            "event_count": len(tape.normalized_events()),
            "normalized_sha256": tape.digest(),
        },
        "inputs": [
            {"path": str(path.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(path)}
            for path in sorted(inputs)
        ],
        "safety": {
            "network_provider_calls": "NONE",
            "canary": "DISABLED",
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"TEST_HARNESS_EVIDENCE=PASS output={output}")
    print(f"REPLAY_SHA256={payload['replay']['normalized_sha256']}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
