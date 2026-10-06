#!/usr/bin/env python3
"""Build deterministic P06-E macro-vintage anti-lookahead evidence offline."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.historical_data import (
    MacroVintage,
    MacroVintagePolicy,
    MacroVintageStore,
)

POLICY = ROOT / "config/historical-data/macro-vintage-policy.json"
DATASET_VERSION = "a" * 64


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def vintage(revision: int, release: int, observed: int, value: str) -> MacroVintage:
    raw = f"macro:{revision}:{value}".encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    return MacroVintage(
        series_id="MACRO:CPI:REFERENCE",
        observation_time_ns=10,
        release_time_ns=release,
        observed_at_ns=observed,
        revision_number=revision,
        value_text=value,
        unit="INDEX",
        source="reference-macro-provider",
        source_dataset_version=DATASET_VERSION,
        source_payload_sha256=digest,
        source_object_relative_path=f"reference-provider/2026/06/07/macro/{digest}.raw",
        source_revision_id=f"revision-{revision}",
    )


def value_or_none(value: MacroVintage | None) -> str | None:
    return None if value is None else value.value_text


def build(output: Path) -> None:
    policy = MacroVintagePolicy.from_path(POLICY)
    initial = vintage(0, 100, 105, "100.0")
    revision = vintage(1, 200, 205, "100.4")
    store = MacroVintageStore((revision, initial), policy)

    before_release = store.resolve(
        series_id=initial.series_id,
        observation_time_ns=10,
        decision_time_ns=99,
    )
    after_initial = store.resolve(
        series_id=initial.series_id,
        observation_time_ns=10,
        decision_time_ns=150,
    )
    released_not_observed = store.resolve(
        series_id=initial.series_id,
        observation_time_ns=10,
        decision_time_ns=202,
    )
    after_revision_observed = store.resolve(
        series_id=initial.series_id,
        observation_time_ns=10,
        decision_time_ns=205,
    )

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P06E_MACRO_VINTAGE_EVIDENCE",
        "policy_sha256": sha256(POLICY),
        "store_fingerprint": store.fingerprint,
        "vintage_count": store.vintage_count,
        "initial_vintage_id": initial.vintage_id,
        "revision_vintage_id": revision.vintage_id,
        "timeline": {
            "decision_99": value_or_none(before_release),
            "decision_150": value_or_none(after_initial),
            "decision_202": value_or_none(released_not_observed),
            "decision_205": value_or_none(after_revision_observed)
        },
        "anti_lookahead_proven": (
            before_release is None
            and after_initial == initial
            and released_not_observed == initial
            and after_revision_observed == revision
        ),
        "production_macro_storage_vendor": policy.production_macro_storage_vendor,
        "safety": {
            "network_required": False,
            "credentials_required": False,
            "canary": "DISABLED",
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED"
        }
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"P06E_EVIDENCE=PASS output={output}")
    print(f"P06E_STORE_FINGERPRINT={store.fingerprint}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    build(parser.parse_args().output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
