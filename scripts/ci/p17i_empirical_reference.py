#!/usr/bin/env python3
from __future__ import annotations

import argparse
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
import hashlib
import json
from pathlib import Path

from quant.backtesting.empirical_quant_gate import (
    EmpiricalMeasurement,
    EmpiricalWorkstreamEvidence,
    MetricSchema,
    certify_empirical_g9,
)
from quant.backtesting.model_registry import ModelVersion, build_model_registry
from quant.backtesting.strategy_registry import StrategyVersion, build_strategy_registry

ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "research/reference-data/btc-usd-daily-2026-09-yahoo.json"
POLICY_PATH = ROOT / "config/quant/empirical-quant-gate-policy.json"


def digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json_decimal(path: Path) -> dict[str, object]:
    value = json.loads(
        path.read_text(encoding="utf-8"),
        parse_float=Decimal,
        parse_int=Decimal,
    )
    if not isinstance(value, dict):
        raise RuntimeError(f"object required: {path}")
    return value


def integer_bps(value: Decimal, *, rounding: str = "floor") -> int:
    mode = ROUND_FLOOR if rounding == "floor" else ROUND_CEILING
    return int(value.to_integral_value(rounding=mode))


def build_evidence() -> dict[str, object]:
    data = load_json_decimal(DATA_PATH)
    policy = load_json_decimal(POLICY_PATH)
    if data.get("fixture_only") is not False:
        raise RuntimeError("empirical reference dataset must explicitly be non-fixture")

    rows_raw = data.get("rows")
    if not isinstance(rows_raw, list) or len(rows_raw) < 8:
        raise RuntimeError("empirical reference dataset requires at least eight observations")

    rows: list[dict[str, object]] = []
    for raw in rows_raw:
        if not isinstance(raw, dict):
            raise RuntimeError("reference row must be an object")
        rows.append(raw)

    dates = [str(row["date"]) for row in rows]
    if dates != sorted(dates) or len(set(dates)) != len(dates):
        raise RuntimeError("reference rows must be unique and chronological")

    oos_start_index = 3
    oos = rows[oos_start_index:]
    first_close = Decimal(oos[0]["close"])
    last_close = Decimal(oos[-1]["close"])
    gross_return_bps = integer_bps((last_close / first_close - Decimal(1)) * Decimal(10_000))

    peak = first_close
    max_drawdown = Decimal(0)
    for row in oos:
        close = Decimal(row["close"])
        if close > peak:
            peak = close
        drawdown = (Decimal(1) - close / peak) * Decimal(10_000)
        if drawdown > max_drawdown:
            max_drawdown = drawdown
    max_drawdown_bps = integer_bps(max_drawdown, rounding="ceil")

    roundtrip_cost_bps = int(Decimal(policy["governed_roundtrip_cost_bps"]))
    stress_cost_bps = int(Decimal(policy["robustness_stress_cost_bps"]))
    reference_notional = Decimal(policy["reference_notional_usd"])
    net_return_bps = gross_return_bps - roundtrip_cost_bps
    stressed_net_return_bps = gross_return_bps - stress_cost_bps

    max_capacity_ppm = 0
    for row in oos:
        volume = Decimal(row["quote_volume"])
        if volume <= 0:
            raise RuntimeError("quote volume must be positive")
        ppm = integer_bps(reference_notional / volume * Decimal(1_000_000), rounding="ceil")
        max_capacity_ppm = max(max_capacity_ppm, ppm)

    dataset_sha = file_sha(DATA_PATH)
    policy_sha = file_sha(POLICY_PATH)
    code_sha = file_sha(Path(__file__))
    source = data.get("source")
    if not isinstance(source, dict):
        raise RuntimeError("source metadata required")
    source_provenance_sha = digest(source)

    a_payload = {
        "kind": "EMPIRICAL_BACKTEST_REFERENCE",
        "dataset_sha256": dataset_sha,
        "oos_start_date": dates[oos_start_index],
        "oos_end_date": dates[-1],
        "gross_return_bps": gross_return_bps,
        "net_return_bps": net_return_bps,
    }
    b_payload = {
        "kind": "EMPIRICAL_EXECUTION_REALISM_REFERENCE",
        "dataset_sha256": dataset_sha,
        "threshold_policy_sha256": policy_sha,
        "governed_roundtrip_cost_bps": roundtrip_cost_bps,
    }
    c_payload = {
        "kind": "EMPIRICAL_INFORMATION_HYGIENE_REFERENCE",
        "dataset_sha256": dataset_sha,
        "source_provenance_sha256": source_provenance_sha,
        "chronological_unique_rows": True,
        "fixture_only": False,
    }
    d_payload = {
        "kind": "EMPIRICAL_OOS_REFERENCE",
        "dataset_sha256": dataset_sha,
        "selection_before_oos": True,
        "oos_start_index": oos_start_index,
        "oos_start_date": dates[oos_start_index],
        "oos_end_date": dates[-1],
    }
    e_payload = {
        "kind": "EMPIRICAL_ROBUSTNESS_REFERENCE",
        "dataset_sha256": dataset_sha,
        "gross_return_bps": gross_return_bps,
        "stress_cost_bps": stress_cost_bps,
        "stressed_net_return_bps": stressed_net_return_bps,
    }
    f_payload = {
        "kind": "EMPIRICAL_CAPACITY_REFERENCE",
        "dataset_sha256": dataset_sha,
        "reference_notional_usd": str(reference_notional),
        "max_notional_to_daily_quote_volume_ppm": max_capacity_ppm,
    }

    walk_id = digest(d_payload)
    robustness_id = digest(e_payload)
    capacity_id = digest(f_payload)
    strategy_definition = digest(
        {
            "strategy": "REFERENCE_BUY_FIRST_OOS_CLOSE_SELL_LAST_OOS_CLOSE",
            "oos_start_index": oos_start_index,
            "dataset_sha256": dataset_sha,
        }
    )
    strategy = StrategyVersion(
        strategy_id="reference-btc-usd-buy-hold",
        version="1.0.0",
        lifecycle_state="VALIDATED",
        definition_sha256=strategy_definition,
        code_sha256=code_sha,
        config_sha256=policy_sha,
        universe_id="BTC-USD",
        timeframe_id="1d",
        walk_forward_certificate_sha256=walk_id,
        robustness_certificate_sha256=robustness_id,
        capacity_certificate_sha256=capacity_id,
    )
    strategy_registry = build_strategy_registry((strategy,))

    model_artifact_sha = digest(
        {
            "kind": "REFERENCE_NON_ML_BASELINE",
            "strategy_record_id": strategy.record_id,
            "dataset_sha256": dataset_sha,
        }
    )
    model = ModelVersion(
        model_id="reference-rule-baseline",
        version="1.0.0",
        lifecycle_state="VALIDATED",
        model_artifact_sha256=model_artifact_sha,
        code_sha256=code_sha,
        config_sha256=policy_sha,
        feature_schema_sha256=digest({"schema": "OHLCV_DAILY_V1"}),
        training_dataset_sha256=dataset_sha,
        strategy_record_sha256=strategy.record_id,
        walk_forward_certificate_sha256=walk_id,
        robustness_certificate_sha256=robustness_id,
    )
    model_registry = build_model_registry((model,))

    g_payload = {
        "kind": "EMPIRICAL_STRATEGY_REGISTRY_REFERENCE",
        "strategy_record_id": strategy.record_id,
        "strategy_registry_id": strategy_registry.registry_id,
    }
    h_payload = {
        "kind": "EMPIRICAL_MODEL_REGISTRY_REFERENCE",
        "model_record_id": model.record_id,
        "model_registry_id": model_registry.registry_id,
    }

    payloads = (a_payload, b_payload, c_payload, d_payload, e_payload, f_payload, g_payload, h_payload)
    workstreams = tuple(
        EmpiricalWorkstreamEvidence(
            workstream=f"P17-{letter}",
            evidence_sha256=digest(payload),
            provenance_sha256=digest(
                {
                    "workstream": f"P17-{letter}",
                    "dataset_sha256": dataset_sha,
                    "threshold_policy_sha256": policy_sha,
                    "source_provenance_sha256": source_provenance_sha,
                    "payload_sha256": digest(payload),
                }
            ),
        )
        for letter, payload in zip("ABCDEFGH", payloads, strict=True)
    )

    metrics_raw = policy.get("legacy_metrics")
    if not isinstance(metrics_raw, list):
        raise RuntimeError("legacy empirical compatibility metrics must be a list")
    metric_schemas = tuple(
        MetricSchema(
            category=str(row["category"]),
            metric_id=str(row["metric_id"]),
            version="1.0",
            unit=str(row["unit"]),
            comparator=str(row["comparator"]),
            threshold_value=int(Decimal(row["threshold_value"])),
        )
        for row in metrics_raw
        if isinstance(row, dict)
    )

    measured = {
        "OOS_EDGE": net_return_bps,
        "RISK": max_drawdown_bps,
        "ROBUSTNESS": stressed_net_return_bps,
        "CAPACITY": max_capacity_ppm,
        "EXECUTION_REALISM": roundtrip_cost_bps,
    }
    evidence_by_category = {
        "OOS_EDGE": digest(a_payload),
        "RISK": digest({"dataset_sha256": dataset_sha, "max_drawdown_bps": max_drawdown_bps}),
        "ROBUSTNESS": digest(e_payload),
        "CAPACITY": digest(f_payload),
        "EXECUTION_REALISM": digest(b_payload),
    }
    measurements = tuple(
        EmpiricalMeasurement(
            category=schema.category,
            metric_schema_id=schema.schema_id,
            measured_value=measured[schema.category],
            evidence_sha256=evidence_by_category[schema.category],
            dataset_sha256=dataset_sha,
        )
        for schema in metric_schemas
    )

    gate = certify_empirical_g9(
        dataset_sha256=dataset_sha,
        threshold_policy_sha256=policy_sha,
        strategy_registry_id=strategy_registry.registry_id,
        model_registry_id=model_registry.registry_id,
        workstream_evidence=workstreams,
        metric_schemas=metric_schemas,
        measurements=measurements,
    )

    return {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P17_EMPIRICAL_G9_REFERENCE_EVIDENCE",
        "task_id": "FIN-P17-WI-001-R01",
        "source": source,
        "fixture_only": False,
        "empirical_reference": True,
        "legacy_reference_only": True,
        "authoritative_g9": False,
        "dataset_sha256": dataset_sha,
        "threshold_policy_sha256": policy_sha,
        "strategy_record_id": strategy.record_id,
        "strategy_registry_id": strategy_registry.registry_id,
        "model_record_id": model.record_id,
        "model_registry_id": model_registry.registry_id,
        "gate_name": gate.gate_name,
        "gate_state": gate.state,
        "gate_certificate_id": gate.certificate_id,
        "oos_window": {"start": dates[oos_start_index], "end": dates[-1]},
        "measurements": {
            "OOS_EDGE": net_return_bps,
            "RISK": max_drawdown_bps,
            "ROBUSTNESS": stressed_net_return_bps,
            "CAPACITY": max_capacity_ppm,
            "EXECUTION_REALISM": roundtrip_cost_bps,
        },
        "workstream_evidence": [item.payload() for item in gate.workstream_evidence],
        "metric_schemas": [item.payload() for item in gate.metric_schemas],
        "profitability_guarantee": False,
        "production_scale_validation": False,
        "execution_authority": False,
        "automatic_live_promotion": False,
        "p19_started": False,
        "live_trading": "DISABLED",
        "auto_trading": "DISABLED",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = build_evidence()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"P17_EMPIRICAL_G9_REFERENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
