from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
import hashlib
import json
import re
from typing import Sequence


class RobustnessError(ValueError):
    """P17-E Monte Carlo / stress / sensitivity invariant failure."""


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,191}$")\nMAX_MONTE_CARLO_OBSERVATIONS = 1_000_000


def _safe_id(value: str, *, field: str) -> str:
    parsed = value.strip()
    if _SAFE_ID.fullmatch(parsed) is None:
        raise RobustnessError(f"{field} contains unsafe characters")
    return parsed


def _sha(value: str, *, field: str) -> str:
    parsed = value.strip().lower()
    if _SHA256.fullmatch(parsed) is None:
        raise RobustnessError(f"{field} must be lowercase SHA-256")
    return parsed


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _validate_return_bps(value: int, *, field: str) -> int:
    if value <= -10_000:
        raise RobustnessError(f"{field} must be greater than -10000 bps")
    return value


def _terminal_and_drawdown_bps(returns_bps: Sequence[int]) -> tuple[int, int]:
    wealth = Decimal(1)
    peak = Decimal(1)
    worst_drawdown = Decimal(0)
    for item in returns_bps:
        if item <= -10_000:
            return -10_000, 10_000
        wealth *= (Decimal(10_000 + item) / Decimal(10_000))
        if wealth > peak:
            peak = wealth
        if peak > 0:
            drawdown = (peak - wealth) / peak * Decimal(10_000)
            if drawdown > worst_drawdown:
                worst_drawdown = drawdown
    terminal = (wealth - Decimal(1)) * Decimal(10_000)
    return (
        int(terminal.to_integral_value(rounding=ROUND_FLOOR)),
        int(worst_drawdown.to_integral_value(rounding=ROUND_CEILING)),
    )


def _sample_index(seed: str, *, path: int, block: int, population: int) -> int:
    material = f"{seed}:{path}:{block}".encode("utf-8")
    digest = hashlib.sha256(material).digest()
    return int.from_bytes(digest[:8], "big") % population


@dataclass(frozen=True, slots=True)
class MonteCarloSpec:
    seed_sha256: str
    path_count: int
    path_length: int
    block_size: int

    def __post_init__(self) -> None:
        _sha(self.seed_sha256, field="seed_sha256")
        if self.path_count <= 0:
            raise RobustnessError("path_count must be positive")
        if self.path_length <= 0:
            raise RobustnessError("path_length must be positive")
        if self.block_size <= 0:
            raise RobustnessError("block_size must be positive")

    def payload(self) -> dict[str, object]:
        return {
            "seed_sha256": self.seed_sha256,
            "path_count": self.path_count,
            "path_length": self.path_length,
            "block_size": self.block_size,
        }


@dataclass(frozen=True, slots=True)
class StressScenario:
    scenario_id: str
    loss_shock_bps: int
    cost_drag_bps: int

    def __post_init__(self) -> None:
        _safe_id(self.scenario_id, field="scenario_id")
        if self.loss_shock_bps < 0 or self.cost_drag_bps < 0:
            raise RobustnessError("stress shock/drag must be non-negative")

    def payload(self) -> dict[str, object]:
        return {
            "scenario_id": self.scenario_id,
            "loss_shock_bps": self.loss_shock_bps,
            "cost_drag_bps": self.cost_drag_bps,
        }


@dataclass(frozen=True, slots=True)
class SensitivityVariant:
    variant_id: str
    parameter_set_sha256: str
    metric_bps: int

    def __post_init__(self) -> None:
        _safe_id(self.variant_id, field="variant_id")
        _sha(self.parameter_set_sha256, field="parameter_set_sha256")

    def payload(self) -> dict[str, object]:
        return {
            "variant_id": self.variant_id,
            "parameter_set_sha256": self.parameter_set_sha256,
            "metric_bps": self.metric_bps,
        }


@dataclass(frozen=True, slots=True)
class StressDiagnostic:
    scenario_id: str
    terminal_return_bps: int
    max_drawdown_bps: int

    def payload(self) -> dict[str, object]:
        return {
            "scenario_id": self.scenario_id,
            "terminal_return_bps": self.terminal_return_bps,
            "max_drawdown_bps": self.max_drawdown_bps,
        }


@dataclass(frozen=True, slots=True)
class RobustnessCertificate:
    certificate_id: str
    status: str
    walk_forward_certificate_id: str
    monte_carlo_min_terminal_return_bps: int
    monte_carlo_p05_terminal_return_bps: int
    monte_carlo_median_terminal_return_bps: int
    monte_carlo_worst_max_drawdown_bps: int
    stress_diagnostics: tuple[StressDiagnostic, ...]
    sensitivity_min_metric_bps: int
    sensitivity_max_metric_bps: int
    sensitivity_dispersion_bps: int
    sensitivity_worst_degradation_bps: int
    profitability_claim_authority: bool = False
    candidate_selection_authority: bool = False
    g9_authority: bool = False
    execution_authority: bool = False
    order_routing_authority: bool = False
    live_trading: str = "DISABLED"
    auto_trading: str = "DISABLED"


def evaluate_robustness(
    *,
    walk_forward_certificate_id: str,
    oos_return_bps: Sequence[int],
    monte_carlo: MonteCarloSpec,
    baseline_metric_bps: int,
    stress_scenarios: Sequence[StressScenario],
    sensitivity_variants: Sequence[SensitivityVariant],
) -> RobustnessCertificate:
    walk_forward_id = _sha(
        walk_forward_certificate_id,
        field="walk_forward_certificate_id",
    )
    returns = tuple(
        _validate_return_bps(value, field="oos_return_bps")
        for value in oos_return_bps
    )
    if not returns:
        raise RobustnessError("oos_return_bps must be non-empty")
    if monte_carlo.block_size > len(returns):
        raise RobustnessError("block_size cannot exceed OOS return count")

    scenarios = tuple(
        sorted(stress_scenarios, key=lambda item: item.scenario_id)
    )
    if not scenarios:
        raise RobustnessError("at least one stress scenario is required")
    scenario_ids = tuple(item.scenario_id for item in scenarios)
    if len(scenario_ids) != len(set(scenario_ids)):
        raise RobustnessError("duplicate stress scenario_id")

    variants = tuple(
        sorted(sensitivity_variants, key=lambda item: item.variant_id)
    )
    if not variants:
        raise RobustnessError("at least one sensitivity variant is required")
    variant_ids = tuple(item.variant_id for item in variants)
    if len(variant_ids) != len(set(variant_ids)):
        raise RobustnessError("duplicate sensitivity variant_id")
    parameter_ids = tuple(item.parameter_set_sha256 for item in variants)
    if len(parameter_ids) != len(set(parameter_ids)):
        raise RobustnessError("duplicate sensitivity parameter_set_sha256")

    terminal_returns: list[int] = []
    drawdowns: list[int] = []
    for path_index in range(monte_carlo.path_count):
        path: list[int] = []
        block_index = 0
        while len(path) < monte_carlo.path_length:
            start = _sample_index(
                monte_carlo.seed_sha256,
                path=path_index,
                block=block_index,
                population=len(returns),
            )
            for offset in range(monte_carlo.block_size):
                path.append(returns[(start + offset) % len(returns)])
                if len(path) == monte_carlo.path_length:
                    break
            block_index += 1
        terminal, drawdown = _terminal_and_drawdown_bps(path)
        terminal_returns.append(terminal)
        drawdowns.append(drawdown)

    ordered_terminal = sorted(terminal_returns)
    p05_index = ((len(ordered_terminal) - 1) * 5) // 100
    median_index = (len(ordered_terminal) - 1) // 2

    stress_diagnostics: list[StressDiagnostic] = []
    for scenario in scenarios:
        stressed = tuple(
            item - scenario.loss_shock_bps - scenario.cost_drag_bps
            for item in returns
        )
        terminal, drawdown = _terminal_and_drawdown_bps(stressed)
        stress_diagnostics.append(
            StressDiagnostic(
                scenario_id=scenario.scenario_id,
                terminal_return_bps=terminal,
                max_drawdown_bps=drawdown,
            )
        )

    sensitivity_values = [item.metric_bps for item in variants]
    sensitivity_min = min(sensitivity_values)
    sensitivity_max = max(sensitivity_values)
    sensitivity_dispersion = sensitivity_max - sensitivity_min
    worst_degradation = max(0, baseline_metric_bps - sensitivity_min)

    body = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P17E_ROBUSTNESS_CERTIFICATE",
        "status": "ROBUSTNESS_EVALUATED",
        "walk_forward_certificate_id": walk_forward_id,
        "oos_return_bps": list(returns),
        "monte_carlo": monte_carlo.payload(),
        "monte_carlo_diagnostics": {
            "min_terminal_return_bps": min(ordered_terminal),
            "p05_terminal_return_bps": ordered_terminal[p05_index],
            "median_terminal_return_bps": ordered_terminal[median_index],
            "worst_max_drawdown_bps": max(drawdowns),
        },
        "stress_scenarios": [item.payload() for item in scenarios],
        "stress_diagnostics": [
            item.payload() for item in stress_diagnostics
        ],
        "baseline_metric_bps": baseline_metric_bps,
        "sensitivity_variants": [item.payload() for item in variants],
        "sensitivity_diagnostics": {
            "min_metric_bps": sensitivity_min,
            "max_metric_bps": sensitivity_max,
            "dispersion_bps": sensitivity_dispersion,
            "worst_degradation_bps": worst_degradation,
        },
        "profitability_claim_authority": False,
        "candidate_selection_authority": False,
        "g9_authority": False,
        "execution_authority": False,
        "order_routing_authority": False,
        "live_trading": "DISABLED",
        "auto_trading": "DISABLED",
    }
    return RobustnessCertificate(
        certificate_id=hashlib.sha256(_canonical_bytes(body)).hexdigest(),
        status="ROBUSTNESS_EVALUATED",
        walk_forward_certificate_id=walk_forward_id,
        monte_carlo_min_terminal_return_bps=min(ordered_terminal),
        monte_carlo_p05_terminal_return_bps=ordered_terminal[p05_index],
        monte_carlo_median_terminal_return_bps=ordered_terminal[median_index],
        monte_carlo_worst_max_drawdown_bps=max(drawdowns),
        stress_diagnostics=tuple(stress_diagnostics),
        sensitivity_min_metric_bps=sensitivity_min,
        sensitivity_max_metric_bps=sensitivity_max,
        sensitivity_dispersion_bps=sensitivity_dispersion,
        sensitivity_worst_degradation_bps=worst_degradation,
    )
