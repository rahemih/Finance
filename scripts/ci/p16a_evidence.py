from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.pretrade_firewall.signal_freshness import (
    PreTradeFreshnessPolicy,
    PreTradeFreshnessRequest,
    evaluate_signal_freshness,
)
from packages.signal_intelligence.signal_output_contract import AnalyticalSignalOutput


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/risk/pretrade-signal-freshness-policy.json"


def fixture_signal() -> AnalyticalSignalOutput:
    return AnalyticalSignalOutput(
        candidate_id="candidate-ci",
        asset_id="BTC-USD",
        strategy_id="trend",
        timeframe="1h",
        regime_label="TREND",
        as_of_time_ns=1_000,
        action="LONG",
        action_reason_codes=("ANALYTICAL_CHAIN_CLEAR",),
        fusion_id="fusion-ci",
        qualification_id="qualification-ci",
        tp_stop_prediction_id="tpstop-ci",
        explanation_id="explanation-ci",
        challenge_id="challenge-ci",
        empirical_probability_bps=6500,
        overall_uncertainty_bps=1000,
        tp_first_probability_bps=6000,
        stop_first_probability_bps=2500,
        neither_probability_bps=1500,
        entry_low_scaled=100_000,
        entry_high_scaled=101_000,
        invalidation_price_scaled=98_000,
        candidate_stop_scaled=99_000,
        candidate_target_scaled=104_000,
        price_scale=100,
        geometry_version_sha256="a" * 64,
        evidence_freshness_exclusions=(),
        reasons_for=("support",),
        reasons_against=(),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    policy = PreTradeFreshnessPolicy(
        policy_version="p16a-ci-v1",
        max_signal_age_ns=500,
        max_price_deviation_bps=100,
    )
    signal = fixture_signal()
    eligible = evaluate_signal_freshness(
        policy=policy,
        request=PreTradeFreshnessRequest(
            "eligible",
            signal,
            100_500,
            100,
            1_400,
        ),
    )
    veto = evaluate_signal_freshness(
        policy=policy,
        request=PreTradeFreshnessRequest(
            "veto",
            signal,
            102_011,
            100,
            1_400,
        ),
    )
    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P16A_SIGNAL_AGE_PRICE_DEVIATION_EVIDENCE",
        "task_id": "FIN-P16-WA-001",
        "fixture_only": True,
        "policy_sha256": hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest(),
        "eligible": {
            "decision_id": eligible.decision_id,
            "status": eligible.status,
            "signal_age_ns": eligible.signal_age_ns,
            "price_deviation_bps": eligible.price_deviation_bps,
        },
        "veto": {
            "decision_id": veto.decision_id,
            "status": veto.status,
            "reason_codes": list(veto.reason_codes),
            "price_deviation_bps": veto.price_deviation_bps,
        },
        "g8_authority": False,
        "execution_authority": False,
        "live_trading": "DISABLED",
        "auto_trading": "DISABLED",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"P16A_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
