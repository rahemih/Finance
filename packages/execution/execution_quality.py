from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import string
from typing import Mapping, cast


class ExecutionQualityError(ValueError):
    """P20-H deterministic reference execution-quality invariant failure."""


PPM = 1_000_000


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ExecutionQualityError(f"{field} must be non-empty text")
    return value.strip()


def _sha256_hex(value: object, *, field: str) -> str:
    text = _text(value, field=field).lower()
    if len(text) != 64 or any(ch not in string.hexdigits for ch in text):
        raise ExecutionQualityError(f"{field} must be a sha256 hex digest")
    return text


def _non_negative_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ExecutionQualityError(f"{field} must be a non-negative integer")
    return value


def _positive_int(value: object, *, field: str) -> int:
    value = _non_negative_int(value, field=field)
    if value == 0:
        raise ExecutionQualityError(f"{field} must be positive")
    return value


def _ratio_ppm(numerator: int, denominator: int) -> int:
    _positive_int(denominator, field="ratio denominator")
    sign = -1 if numerator < 0 else 1
    return sign * ((abs(numerator) * PPM) // denominator)


def _nearest_rank(values: list[int], percentile: int) -> int:
    if not values:
        raise ExecutionQualityError("percentile requires at least one value")
    if percentile <= 0 or percentile > 100:
        raise ExecutionQualityError("percentile must be in 1..100")
    ordered = sorted(values)
    rank = (percentile * len(ordered) + 99) // 100
    return ordered[rank - 1]


@dataclass(frozen=True, slots=True)
class ExecutionQualityPolicy:
    markets: tuple[str, ...]
    quality_bands: tuple[str, ...]
    ack_latency_p95_max_ns: int
    terminal_latency_p95_max_ns: int
    adverse_slippage_p95_max_ppm: int
    min_fill_ratio_ppm: int
    degraded_trigger_percent: int
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "ExecutionQualityPolicy":
        try:
            raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ExecutionQualityError(f"invalid P20-H policy JSON: {exc}") from exc
        if not isinstance(raw_value, Mapping):
            raise ExecutionQualityError("P20-H policy root must be an object")
        raw = cast(Mapping[str, object], raw_value)
        expected: dict[str, object] = {
            "schema_version": "1.0",
            "kind": "NEXUS_QUANT_P20H_EXECUTION_QUALITY_POLICY",
            "task_id": "FIN-P20-WH-001",
            "mode": "DETERMINISTIC_REFERENCE_EXECUTION_QUALITY",
            "source_mode": "EXPLICIT_REFERENCE_SANDBOX_EXECUTION_ONLY",
            "required_reconciliation_verdict": "MATCHED",
            "latency_unit": "NS",
            "ratio_unit": "PPM",
            "real_venue_query": False,
            "production_execution_certification": False,
            "broker_certification": False,
            "automatic_oms_mutation": False,
            "external_order_mutation": False,
            "external_order_submission": False,
            "credential_mode": "NONE",
            "network_mode": "DISABLED",
            "live_execution_authority": False,
            "g11_execution_validated": False,
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        }
        for key, expected_value in expected.items():
            if raw.get(key) != expected_value:
                raise ExecutionQualityError(f"P20-H policy mismatch: {key}")
        markets_value = raw.get("markets")
        bands_value = raw.get("quality_bands")
        thresholds_value = raw.get("thresholds")
        if not isinstance(markets_value, list) or not isinstance(bands_value, list):
            raise ExecutionQualityError("markets/quality_bands must be lists")
        if not isinstance(thresholds_value, Mapping):
            raise ExecutionQualityError("thresholds must be an object")
        markets = tuple(_text(v, field="markets") for v in cast(list[object], markets_value))
        bands = tuple(_text(v, field="quality_bands") for v in cast(list[object], bands_value))
        if markets != ("CRYPTO", "FOREX"):
            raise ExecutionQualityError("invalid P20-H market taxonomy")
        if bands != ("WITHIN_REFERENCE_BUDGET", "DEGRADED_REFERENCE", "REFERENCE_FAIL"):
            raise ExecutionQualityError("invalid P20-H quality-band taxonomy")
        thresholds = cast(Mapping[str, object], thresholds_value)
        ack = _positive_int(thresholds.get("ack_latency_p95_max_ns"), field="ack_latency_p95_max_ns")
        terminal = _positive_int(thresholds.get("terminal_latency_p95_max_ns"), field="terminal_latency_p95_max_ns")
        slippage = _non_negative_int(thresholds.get("adverse_slippage_p95_max_ppm"), field="adverse_slippage_p95_max_ppm")
        fill = _positive_int(thresholds.get("min_fill_ratio_ppm"), field="min_fill_ratio_ppm")
        degraded = _positive_int(thresholds.get("degraded_trigger_percent"), field="degraded_trigger_percent")
        if fill > PPM:
            raise ExecutionQualityError("min_fill_ratio_ppm cannot exceed 1,000,000")
        if degraded >= 100:
            raise ExecutionQualityError("degraded_trigger_percent must be below 100")
        return cls(markets, bands, ack, terminal, slippage, fill, degraded, "DISABLED", "DISABLED")

    @property
    def policy_id(self) -> str:
        payload: dict[str, object] = {
            "markets": list(self.markets),
            "quality_bands": list(self.quality_bands),
            "ack_latency_p95_max_ns": self.ack_latency_p95_max_ns,
            "terminal_latency_p95_max_ns": self.terminal_latency_p95_max_ns,
            "adverse_slippage_p95_max_ppm": self.adverse_slippage_p95_max_ppm,
            "min_fill_ratio_ppm": self.min_fill_ratio_ppm,
            "degraded_trigger_percent": self.degraded_trigger_percent,
            "source_mode": "EXPLICIT_REFERENCE_SANDBOX_EXECUTION_ONLY",
            "required_reconciliation_verdict": "MATCHED",
            "network_mode": "DISABLED",
            "production_execution_certification": False,
            "live_execution_authority": False,
            "live_trading": self.live_trading,
            "auto_trading": self.auto_trading,
        }
        return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


@dataclass(frozen=True, slots=True)
class ExecutionQualityObservation:
    market: str
    order_id: str
    client_order_id: str
    reconciliation_report_id: str
    reconciliation_verdict: str
    side: str
    order_type: str
    terminal_status: str
    ordered_quantity_scaled: int
    filled_quantity_scaled: int
    quantity_scale: int
    arrival_price_scaled: int
    average_fill_price_scaled: int | None
    price_scale: int
    submit_time_ns: int
    ack_time_ns: int
    first_fill_time_ns: int | None
    terminal_time_ns: int
    source_ref: str

    def validate(self, policy: ExecutionQualityPolicy) -> None:
        if self.market not in policy.markets:
            raise ExecutionQualityError("market outside P20-H policy")
        _text(self.order_id, field="order_id")
        _text(self.client_order_id, field="client_order_id")
        _sha256_hex(self.reconciliation_report_id, field="reconciliation_report_id")
        if self.reconciliation_verdict != "MATCHED":
            raise ExecutionQualityError("P20-H accepts MATCHED P20-G reconciliation only")
        if self.side not in ("BUY", "SELL"):
            raise ExecutionQualityError("unsupported side")
        if self.order_type not in ("MARKET", "LIMIT", "STOP"):
            raise ExecutionQualityError("unsupported order type")
        if self.terminal_status not in ("FILLED", "PARTIALLY_FILLED", "CANCELED", "REJECTED", "EXPIRED"):
            raise ExecutionQualityError("unsupported terminal_status")
        _positive_int(self.ordered_quantity_scaled, field="ordered_quantity_scaled")
        _non_negative_int(self.filled_quantity_scaled, field="filled_quantity_scaled")
        _positive_int(self.quantity_scale, field="quantity_scale")
        if self.filled_quantity_scaled > self.ordered_quantity_scaled:
            raise ExecutionQualityError("filled quantity exceeds ordered quantity")
        _positive_int(self.arrival_price_scaled, field="arrival_price_scaled")
        _positive_int(self.price_scale, field="price_scale")
        if self.filled_quantity_scaled > 0:
            _positive_int(self.average_fill_price_scaled, field="average_fill_price_scaled")
            if self.first_fill_time_ns is None:
                raise ExecutionQualityError("filled sample requires first_fill_time_ns")
        else:
            if self.average_fill_price_scaled is not None or self.first_fill_time_ns is not None:
                raise ExecutionQualityError("unfilled sample cannot carry fill price/time")
        submit = _non_negative_int(self.submit_time_ns, field="submit_time_ns")
        ack = _non_negative_int(self.ack_time_ns, field="ack_time_ns")
        terminal = _non_negative_int(self.terminal_time_ns, field="terminal_time_ns")
        if ack < submit:
            raise ExecutionQualityError("ack_time_ns cannot precede submit_time_ns")
        if self.first_fill_time_ns is not None:
            first_fill = _non_negative_int(self.first_fill_time_ns, field="first_fill_time_ns")
            if first_fill < ack:
                raise ExecutionQualityError("first_fill_time_ns cannot precede ack_time_ns")
            if terminal < first_fill:
                raise ExecutionQualityError("terminal_time_ns cannot precede first fill")
        elif terminal < ack:
            raise ExecutionQualityError("terminal_time_ns cannot precede ack_time_ns")
        _text(self.source_ref, field="source_ref")

    def payload(self) -> dict[str, object]:
        return {
            "market": self.market,
            "order_id": self.order_id,
            "client_order_id": self.client_order_id,
            "reconciliation_report_id": self.reconciliation_report_id,
            "reconciliation_verdict": self.reconciliation_verdict,
            "side": self.side,
            "order_type": self.order_type,
            "terminal_status": self.terminal_status,
            "ordered_quantity_scaled": self.ordered_quantity_scaled,
            "filled_quantity_scaled": self.filled_quantity_scaled,
            "quantity_scale": self.quantity_scale,
            "arrival_price_scaled": self.arrival_price_scaled,
            "average_fill_price_scaled": self.average_fill_price_scaled,
            "price_scale": self.price_scale,
            "submit_time_ns": self.submit_time_ns,
            "ack_time_ns": self.ack_time_ns,
            "first_fill_time_ns": self.first_fill_time_ns,
            "terminal_time_ns": self.terminal_time_ns,
            "source_ref": self.source_ref,
        }

    @property
    def observation_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class ExecutionQualityMetric:
    policy_id: str
    observation_id: str
    market: str
    order_id: str
    client_order_id: str
    ack_latency_ns: int
    first_fill_latency_ns: int | None
    terminal_latency_ns: int
    fill_ratio_ppm: int
    adverse_slippage_ppm: int | None
    reference_only: bool = True
    real_venue_observation: bool = False
    production_execution_certification: bool = False
    live_execution_authority: bool = False

    def payload(self) -> dict[str, object]:
        return {
            "policy_id": self.policy_id,
            "observation_id": self.observation_id,
            "market": self.market,
            "order_id": self.order_id,
            "client_order_id": self.client_order_id,
            "ack_latency_ns": self.ack_latency_ns,
            "first_fill_latency_ns": self.first_fill_latency_ns,
            "terminal_latency_ns": self.terminal_latency_ns,
            "fill_ratio_ppm": self.fill_ratio_ppm,
            "adverse_slippage_ppm": self.adverse_slippage_ppm,
            "reference_only": self.reference_only,
            "real_venue_observation": self.real_venue_observation,
            "production_execution_certification": self.production_execution_certification,
            "live_execution_authority": self.live_execution_authority,
        }

    @property
    def metric_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


class ExecutionQualityLedger:
    def __init__(self, policy: ExecutionQualityPolicy) -> None:
        self._policy = policy
        self._metrics: dict[str, ExecutionQualityMetric] = {}
        self._order_observation: dict[tuple[str, str], str] = {}

    def add(self, observation: ExecutionQualityObservation) -> ExecutionQualityMetric:
        observation.validate(self._policy)
        order_key = (observation.market, observation.order_id)
        existing_observation_id = self._order_observation.get(order_key)
        if existing_observation_id is not None and existing_observation_id != observation.observation_id:
            raise ExecutionQualityError("conflicting execution-quality sample for market/order")
        existing = self._metrics.get(observation.observation_id)
        if existing is not None:
            return existing
        ack_latency = observation.ack_time_ns - observation.submit_time_ns
        terminal_latency = observation.terminal_time_ns - observation.submit_time_ns
        first_fill_latency = (
            None
            if observation.first_fill_time_ns is None
            else observation.first_fill_time_ns - observation.submit_time_ns
        )
        fill_ratio = _ratio_ppm(observation.filled_quantity_scaled, observation.ordered_quantity_scaled)
        slippage: int | None = None
        if observation.average_fill_price_scaled is not None:
            price_delta = (
                observation.average_fill_price_scaled - observation.arrival_price_scaled
                if observation.side == "BUY"
                else observation.arrival_price_scaled - observation.average_fill_price_scaled
            )
            slippage = _ratio_ppm(price_delta, observation.arrival_price_scaled)
        metric = ExecutionQualityMetric(
            policy_id=self._policy.policy_id,
            observation_id=observation.observation_id,
            market=observation.market,
            order_id=observation.order_id,
            client_order_id=observation.client_order_id,
            ack_latency_ns=ack_latency,
            first_fill_latency_ns=first_fill_latency,
            terminal_latency_ns=terminal_latency,
            fill_ratio_ppm=fill_ratio,
            adverse_slippage_ppm=slippage,
        )
        self._metrics[observation.observation_id] = metric
        self._order_observation[order_key] = observation.observation_id
        return metric

    def _quality_band(self, *, ack_p95: int, terminal_p95: int, slippage_p95: int | None, min_fill: int) -> str:
        hard_fail = (
            ack_p95 > self._policy.ack_latency_p95_max_ns
            or terminal_p95 > self._policy.terminal_latency_p95_max_ns
            or min_fill < self._policy.min_fill_ratio_ppm
            or (slippage_p95 is not None and slippage_p95 > self._policy.adverse_slippage_p95_max_ppm)
        )
        if hard_fail:
            return "REFERENCE_FAIL"
        pct = self._policy.degraded_trigger_percent
        degraded = (
            ack_p95 * 100 >= self._policy.ack_latency_p95_max_ns * pct
            or terminal_p95 * 100 >= self._policy.terminal_latency_p95_max_ns * pct
            or min_fill * 100 <= self._policy.min_fill_ratio_ppm * (200 - pct)
            or (
                slippage_p95 is not None
                and self._policy.adverse_slippage_p95_max_ppm > 0
                and slippage_p95 * 100 >= self._policy.adverse_slippage_p95_max_ppm * pct
            )
        )
        return "DEGRADED_REFERENCE" if degraded else "WITHIN_REFERENCE_BUDGET"

    def summary(self) -> dict[str, object]:
        if not self._metrics:
            raise ExecutionQualityError("execution-quality summary requires at least one sample")
        metrics = [self._metrics[key] for key in sorted(self._metrics)]
        ack = [m.ack_latency_ns for m in metrics]
        terminal = [m.terminal_latency_ns for m in metrics]
        fill = [m.fill_ratio_ppm for m in metrics]
        slip = [m.adverse_slippage_ppm for m in metrics if m.adverse_slippage_ppm is not None]
        slip_values = cast(list[int], slip)
        ack_p95 = _nearest_rank(ack, 95)
        terminal_p95 = _nearest_rank(terminal, 95)
        slippage_p95 = _nearest_rank(slip_values, 95) if slip_values else None
        min_fill = min(fill)
        payload: dict[str, object] = {
            "schema_version": "1.0",
            "kind": "NEXUS_QUANT_P20H_EXECUTION_QUALITY_SUMMARY",
            "task_id": "FIN-P20-WH-001",
            "policy_id": self._policy.policy_id,
            "sample_count": len(metrics),
            "filled_sample_count": len(slip_values),
            "ack_latency_ns": {"p50": _nearest_rank(ack, 50), "p95": ack_p95, "max": max(ack)},
            "terminal_latency_ns": {"p50": _nearest_rank(terminal, 50), "p95": terminal_p95, "max": max(terminal)},
            "adverse_slippage_ppm": (
                None
                if not slip_values
                else {"p50": _nearest_rank(slip_values, 50), "p95": slippage_p95, "max": max(slip_values)}
            ),
            "fill_ratio_ppm": {"min": min_fill, "p50": _nearest_rank(fill, 50)},
            "quality_band": self._quality_band(
                ack_p95=ack_p95,
                terminal_p95=terminal_p95,
                slippage_p95=slippage_p95,
                min_fill=min_fill,
            ),
            "samples": [
                {**metric.payload(), "metric_id": metric.metric_id}
                for metric in metrics
            ],
            "authority": {
                "source_mode": "EXPLICIT_REFERENCE_SANDBOX_EXECUTION_ONLY",
                "required_reconciliation_verdict": "MATCHED",
                "reference_only": True,
                "real_venue_query": False,
                "production_execution_certification": False,
                "broker_certification": False,
                "automatic_oms_mutation": False,
                "external_order_mutation": False,
                "external_order_submission": False,
                "credential_mode": "NONE",
                "network_mode": "DISABLED",
                "g11_execution_validated": False,
                "simulation_gate_owner": "P20-I",
                "position_management_owner": "P21",
                "live_execution_authority": False,
                "live_trading": self._policy.live_trading,
                "auto_trading": self._policy.auto_trading,
            },
        }
        result = dict(payload)
        result["summary_id"] = hashlib.sha256(_canonical_bytes(payload)).hexdigest()
        return result
