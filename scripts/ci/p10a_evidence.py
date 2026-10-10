from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.fundamental_intelligence.source_registry import (
    OfficialSourcePolicy,
    OfficialSourceRegistry,
    build_offline_request_spec,
)

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/fundamental-intelligence/official-source-policy.json"
REGISTRY_PATH = ROOT / "config/fundamental-intelligence/official-source-registry.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    policy = OfficialSourcePolicy.from_path(POLICY_PATH)
    registry = OfficialSourceRegistry.from_path(REGISTRY_PATH, policy=policy)

    fred_spec = build_offline_request_spec(
        registry.get("FRED_ALFRED"),
        relative_path="series/observations",
        secret_handle="secret://fundamental/fred/api-key",
    )
    world_bank_spec = build_offline_request_spec(
        registry.get("WORLD_BANK"),
        relative_path="country/all/indicator/NY.GDP.MKTP.CD",
    )

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P10A_OFFICIAL_SOURCE_EVIDENCE",
        "task_id": "FIN-P10-WA-001",
        "policy_sha256": hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest(),
        "registry_sha256": hashlib.sha256(REGISTRY_PATH.read_bytes()).hexdigest(),
        "registry_id": registry.registry_id,
        "verified_on": registry.verified_on,
        "source_count": len(registry.sources),
        "source_ids": sorted(source.source_id for source in registry.sources),
        "revision_semantics": {
            source.source_id: source.revision_mode for source in sorted(registry.sources, key=lambda item: item.source_id)
        },
        "auth_semantics": {
            source.source_id: source.auth_mode for source in sorted(registry.sources, key=lambda item: item.source_id)
        },
        "transport_semantics": {
            source.source_id: source.transport_state for source in sorted(registry.sources, key=lambda item: item.source_id)
        },
        "sample_request_specs": [fred_spec.payload(), world_bank_spec.payload()],
        "production_source_selection": policy.production_source_selection,
        "canonical_tests_network_required": policy.canonical_tests_network_required,
        "country_assumption": "NONE",
        "live_trading": policy.live_trading,
        "auto_trading": policy.auto_trading,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"P10A_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
