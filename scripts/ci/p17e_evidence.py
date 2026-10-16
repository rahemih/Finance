from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from quant.backtesting.robustness import (
    MonteCarloSpec,
    SensitivityVariant,
    StressScenario,
    evaluate_robustness,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/quant/robustness-policy.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    result = evaluate_robustness(
        walk_forward_certificate_id="a" * 64,
        oos_return_bps=(100, -40, 70, -20, 55, 15, -35, 90),
        monte_carlo=MonteCarloSpec(
            seed_sha256="b" * 64,
            path_count=16,
            path_length=8,
            block_size=2,
        ),
        baseline_metric_bps=175,
        stress_scenarios=(
            StressScenario("cost-spike", 0, 25),
            StressScenario("market-shock", 100, 0),
        ),
        sensitivity_variants=(
            SensitivityVariant("base-near", "c" * 64, 180),
            SensitivityVariant("looser", "d" * 64, 120),
            SensitivityVariant("tighter", "e" * 64, 150),
        ),
    )
    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P17E_ROBUSTNESS_EVIDENCE",
        "task_id": "FIN-P17-WE-001",
        "fixture_only": True,
        "policy_sha256": hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest(),
        "certificate_id": result.certificate_id,
        "status": result.status,
        "monte_carlo": {
            "min_terminal_return_bps": result.monte_carlo_min_terminal_return_bps,
            "p05_terminal_return_bps": result.monte_carlo_p05_terminal_return_bps,
            "median_terminal_return_bps": result.monte_carlo_median_terminal_return_bps,
            "worst_max_drawdown_bps": result.monte_carlo_worst_max_drawdown_bps,
        },
        "stress": [item.payload() for item in result.stress_diagnostics],
        "sensitivity": {
            "min_metric_bps": result.sensitivity_min_metric_bps,
            "max_metric_bps": result.sensitivity_max_metric_bps,
            "dispersion_bps": result.sensitivity_dispersion_bps,
            "worst_degradation_bps": result.sensitivity_worst_degradation_bps,
        },
        "profitability_claim_authority": False,
        "candidate_selection_authority": False,
        "g9_authority": False,
        "execution_authority": False,
        "order_routing_authority": False,
        "live_trading": "DISABLED",
        "auto_trading": "DISABLED",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"P17E_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
