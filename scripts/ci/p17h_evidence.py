from __future__ import annotations

import argparse
import json
from pathlib import Path

from quant.backtesting.model_registry import ModelVersion, build_model_registry


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    registry = build_model_registry([
        ModelVersion(
            "fixture-model","1.0.0","VALIDATED",
            "a"*64,"b"*64,"c"*64,"d"*64,"e"*64,"f"*64,"1"*64,"2"*64
        )
    ])
    payload = {
        "schema_version":"1.0",
        "kind":"NEXUS_QUANT_P17H_MODEL_REGISTRY_EVIDENCE",
        "task_id":"FIN-P17-WH-001",
        "fixture_only":True,
        "registry_id":registry.registry_id,
        "record_ids":[r.record_id for r in registry.records],
        "automatic_retraining":False,
        "automatic_promotion":False,
        "profitability_authority":False,
        "g9_authority":False,
        "execution_authority":False,
        "live_trading":"DISABLED",
        "auto_trading":"DISABLED"
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(f"P17H_EVIDENCE=PASS output={args.output}")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
