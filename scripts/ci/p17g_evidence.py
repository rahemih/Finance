from __future__ import annotations

import argparse
import json
from pathlib import Path

from quant.backtesting.strategy_registry import StrategyVersion, build_strategy_registry


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    registry = build_strategy_registry([
        StrategyVersion(
            "fixture-strategy",
            "1.0.0",
            "VALIDATED",
            "a" * 64,
            "b" * 64,
            "c" * 64,
            "fixture-universe",
            "1h",
            "d" * 64,
            "e" * 64,
            "f" * 64,
        )
    ])
    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P17G_STRATEGY_REGISTRY_EVIDENCE",
        "task_id": "FIN-P17-WG-001",
        "fixture_only": True,
        "registry_id": registry.registry_id,
        "record_ids": [r.record_id for r in registry.records],
        "automatic_promotion": False,
        "profitability_authority": False,
        "g9_authority": False,
        "execution_authority": False,
        "live_trading": "DISABLED",
        "auto_trading": "DISABLED",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"P17G_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
