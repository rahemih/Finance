from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Mapping, cast


class BrokerSimulationGateError(ValueError):
    """P20-I deterministic reference broker-simulation / G11 invariant failure."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BrokerSimulationGateError(f"{field} must be non-empty text")
    return value.strip()


def _tuple_text(value: object, *, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise BrokerSimulationGateError(f"{field} must be a non-empty list")
    items = cast(list[object], value)
    parsed = tuple(_text(item, field=field) for item in items)
    if len(set(parsed)) != len(parsed):
        raise BrokerSimulationGateError(f"{field} cannot contain duplicates")
    return parsed


@dataclass(frozen=True, slots=True)
class BrokerSimulationPolicy:
    markets: tuple[str, ...]
    required_scenarios: tuple[str, ...]
    expected_controls: Mapping[str, str]
    dependency_workstreams: tuple[str, ...]
    required_quality_band: str
    gate_scope: str
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "BrokerSimulationPolicy":
        try:
            raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise BrokerSimulationGateError(f"invalid P20-I policy JSON: {exc}") from exc
        if not isinstance(raw_value, Mapping):
            raise BrokerSimulationGateError("P20-I policy root must be an object")
        raw = cast(Mapping[str, object], raw_value)
        expected: dict[str, object] = {
            "schema_version": "1.0",
            "kind": "NEXUS_QUANT_P20I_BROKER_SIMULATION_G11_POLICY",
            "task_id": "FIN-P20-WI-001",
            "mode": "DETERMINISTIC_REFERENCE_BROKER_SIMULATION_GATE",
            "gate": "G11_EXECUTION_VALIDATED",
            "gate_scope": "REFERENCE_SIMULATION_EXECUTION_VALIDATION",
            "required_dependency_state": "CANONICAL_COMPLETE",
            "required_quality_band": "WITHIN_REFERENCE_BUDGET",
            "source_mode": "DETERMINISTIC_REFERENCE_SIMULATION_ONLY",
            "production_broker_selection": "NOT_SELECTED",
            "production_broker_certification": False,
            "real_venue_query": False,
            "credential_mode": "NONE",
            "network_mode": "DISABLED",
            "external_order_submission": False,
            "external_order_mutation": False,
            "automatic_oms_mutation": False,
            "live_execution_validated": False,
            "live_execution_authority": False,
            "automatic_live_promotion": False,
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        }
        for key, value in expected.items():
            if raw.get(key) != value:
                raise BrokerSimulationGateError(f"P20-I policy mismatch: {key}")
        markets = _tuple_text(raw.get("markets"), field="markets")
        scenarios = _tuple_text(raw.get("required_scenarios"), field="required_scenarios")
        dependencies = _tuple_text(raw.get("required_dependency_workstreams"), field="required_dependency_workstreams")
        controls_value = raw.get("expected_controls")
        if not isinstance(controls_value, Mapping):
            raise BrokerSimulationGateError("expected_controls must be an object")
        controls_raw = cast(Mapping[str, object], controls_value)
        controls = {scenario: _text(controls_raw.get(scenario), field=f"expected_controls.{scenario}") for scenario in scenarios}
        if markets != ("CRYPTO", "FOREX"):
            raise BrokerSimulationGateError("invalid P20-I market taxonomy")
        required = (
            "ACK_FILL",
            "REJECT",
            "PARTIAL_FILL_CANCEL",
            "PRE_DISPATCH_TIMEOUT",
            "POST_DISPATCH_CRASH_AMBIGUITY",
            "DUPLICATE_REPLAY",
            "RECONCILIATION_MISMATCH",
        )
        if scenarios != required:
            raise BrokerSimulationGateError("invalid P20-I scenario taxonomy")
        if dependencies != ("P20-A","P20-B","P20-C","P20-D","P20-E","P20-F","P20-G","P20-H"):
            raise BrokerSimulationGateError("invalid P20-I dependency taxonomy")
        return cls(
            markets=markets,
            required_scenarios=scenarios,
            expected_controls=controls,
            dependency_workstreams=dependencies,
            required_quality_band="WITHIN_REFERENCE_BUDGET",
            gate_scope="REFERENCE_SIMULATION_EXECUTION_VALIDATION",
            live_trading="DISABLED",
            auto_trading="DISABLED",
        )

    @property
    def policy_id(self) -> str:
        return hashlib.sha256(_canonical_bytes({
            "markets": list(self.markets),
            "required_scenarios": list(self.required_scenarios),
            "expected_controls": dict(self.expected_controls),
            "dependency_workstreams": list(self.dependency_workstreams),
            "required_quality_band": self.required_quality_band,
            "gate_scope": self.gate_scope,
            "source_mode": "DETERMINISTIC_REFERENCE_SIMULATION_ONLY",
            "production_broker_certification": False,
            "real_venue_query": False,
            "network_mode": "DISABLED",
            "live_execution_validated": False,
            "live_execution_authority": False,
            "live_trading": self.live_trading,
            "auto_trading": self.auto_trading,
        })).hexdigest()


@dataclass(frozen=True, slots=True)
class SimulationScenario:
    scenario_id: str
    market: str
    scenario_type: str

    def validate(self, policy: BrokerSimulationPolicy) -> None:
        _text(self.scenario_id, field="scenario_id")
        if self.market not in policy.markets:
            raise BrokerSimulationGateError("scenario market outside P20-I policy")
        if self.scenario_type not in policy.required_scenarios:
            raise BrokerSimulationGateError("unsupported P20-I scenario type")


@dataclass(frozen=True, slots=True)
class SimulationResult:
    scenario_id: str
    market: str
    scenario_type: str
    control_outcome: str
    terminal_state: str
    passed: bool
    reference_only: bool = True
    real_venue_query: bool = False
    external_order_submission: bool = False
    live_execution_authority: bool = False

    def payload(self) -> dict[str, object]:
        return {
            "scenario_id": self.scenario_id,
            "market": self.market,
            "scenario_type": self.scenario_type,
            "control_outcome": self.control_outcome,
            "terminal_state": self.terminal_state,
            "passed": self.passed,
            "reference_only": self.reference_only,
            "real_venue_query": self.real_venue_query,
            "external_order_submission": self.external_order_submission,
            "live_execution_authority": self.live_execution_authority,
        }

    @property
    def result_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


class BrokerSimulationEngine:
    _TERMINAL: dict[str, str] = {
        "ACK_FILL": "FILLED",
        "REJECT": "REJECTED",
        "PARTIAL_FILL_CANCEL": "CANCELED",
        "PRE_DISPATCH_TIMEOUT": "RETRY_PLANNED",
        "POST_DISPATCH_CRASH_AMBIGUITY": "SAFE_HOLD",
        "DUPLICATE_REPLAY": "REPLAYED_EXISTING",
        "RECONCILIATION_MISMATCH": "RECONCILIATION_REQUIRED",
    }

    def __init__(self, policy: BrokerSimulationPolicy) -> None:
        self._policy = policy
        self._results: dict[str, SimulationResult] = {}

    def run(self, scenario: SimulationScenario) -> SimulationResult:
        scenario.validate(self._policy)
        expected = self._policy.expected_controls[scenario.scenario_type]
        result = SimulationResult(
            scenario_id=scenario.scenario_id,
            market=scenario.market,
            scenario_type=scenario.scenario_type,
            control_outcome=expected,
            terminal_state=self._TERMINAL[scenario.scenario_type],
            passed=True,
        )
        existing = self._results.get(scenario.scenario_id)
        if existing is not None and existing != result:
            raise BrokerSimulationGateError("scenario_id reused with conflicting simulation result")
        self._results[scenario.scenario_id] = result
        return result

    def snapshot(self) -> dict[str, object]:
        results = [self._results[key] for key in sorted(self._results)]
        payload: dict[str, object] = {
            "schema_version": "1.0",
            "kind": "NEXUS_QUANT_P20I_BROKER_SIMULATION_SNAPSHOT",
            "task_id": "FIN-P20-WI-001",
            "policy_id": self._policy.policy_id,
            "results": [{**result.payload(), "result_id": result.result_id} for result in results],
            "authority": {
                "source_mode": "DETERMINISTIC_REFERENCE_SIMULATION_ONLY",
                "production_broker_selection": "NOT_SELECTED",
                "production_broker_certification": False,
                "real_venue_query": False,
                "credential_mode": "NONE",
                "network_mode": "DISABLED",
                "external_order_submission": False,
                "external_order_mutation": False,
                "automatic_oms_mutation": False,
                "live_execution_validated": False,
                "live_execution_authority": False,
                "live_trading": self._policy.live_trading,
                "auto_trading": self._policy.auto_trading,
            },
        }
        return {**payload, "snapshot_id": hashlib.sha256(_canonical_bytes(payload)).hexdigest()}


class G11ExecutionValidationGate:
    def __init__(self, policy: BrokerSimulationPolicy) -> None:
        self._policy = policy

    def evaluate(
        self,
        *,
        dependency_manifests: Mapping[str, Mapping[str, object]],
        simulation_results: tuple[SimulationResult, ...],
        execution_quality_summary: Mapping[str, object],
    ) -> dict[str, object]:
        self._validate_dependencies(dependency_manifests)
        self._validate_scenarios(simulation_results)
        self._validate_quality(execution_quality_summary)
        dependency_ids = {
            workstream: hashlib.sha256(_canonical_bytes(dict(dependency_manifests[workstream]))).hexdigest()
            for workstream in self._policy.dependency_workstreams
        }
        scenario_ids = sorted(result.result_id for result in simulation_results)
        quality_id = _text(execution_quality_summary.get("summary_id"), field="execution_quality_summary.summary_id")
        payload: dict[str, object] = {
            "schema_version": "1.0",
            "kind": "NEXUS_QUANT_G11_EXECUTION_VALIDATION_GATE",
            "gate": "G11_EXECUTION_VALIDATED",
            "gate_status": "PASS",
            "gate_scope": self._policy.gate_scope,
            "policy_id": self._policy.policy_id,
            "dependency_manifest_ids": dependency_ids,
            "scenario_result_ids": scenario_ids,
            "execution_quality_summary_id": quality_id,
            "execution_quality_band": self._policy.required_quality_band,
            "authority": {
                "reference_simulation_validated": True,
                "production_broker_selection": "NOT_SELECTED",
                "production_broker_certification": False,
                "real_venue_query": False,
                "credential_mode": "NONE",
                "network_mode": "DISABLED",
                "external_order_submission": False,
                "external_order_mutation": False,
                "automatic_oms_mutation": False,
                "live_execution_validated": False,
                "live_execution_authority": False,
                "automatic_live_promotion": False,
                "p21_started": False,
                "live_trading": self._policy.live_trading,
                "auto_trading": self._policy.auto_trading,
            },
        }
        return {**payload, "gate_id": hashlib.sha256(_canonical_bytes(payload)).hexdigest()}

    def _validate_dependencies(self, manifests: Mapping[str, Mapping[str, object]]) -> None:
        if set(manifests) != set(self._policy.dependency_workstreams):
            raise BrokerSimulationGateError("G11 dependency manifest set is incomplete or unexpected")
        for workstream in self._policy.dependency_workstreams:
            manifest = manifests[workstream]
            if manifest.get("workstream") != workstream:
                raise BrokerSimulationGateError(f"{workstream} manifest workstream mismatch")
            if manifest.get("state") != "CANONICAL_COMPLETE":
                raise BrokerSimulationGateError(f"{workstream} is not CANONICAL_COMPLETE")
            safety_value = manifest.get("safety")
            if not isinstance(safety_value, Mapping):
                raise BrokerSimulationGateError(f"{workstream} safety block missing")
            safety = cast(Mapping[str, object], safety_value)
            if safety.get("network_mode") != "DISABLED":
                raise BrokerSimulationGateError(f"{workstream} network safety mismatch")
            if safety.get("live_execution_authority") is not False:
                raise BrokerSimulationGateError(f"{workstream} unexpectedly grants Live execution authority")
            if safety.get("live_trading") != "DISABLED" or safety.get("auto_trading") != "DISABLED":
                raise BrokerSimulationGateError(f"{workstream} Live/Auto safety mismatch")

    def _validate_scenarios(self, results: tuple[SimulationResult, ...]) -> None:
        required_pairs = {(market, scenario) for market in self._policy.markets for scenario in self._policy.required_scenarios}
        seen_pairs: set[tuple[str, str]] = set()
        seen_ids: set[str] = set()
        for result in results:
            pair = (result.market, result.scenario_type)
            if result.scenario_id in seen_ids:
                raise BrokerSimulationGateError("duplicate scenario_id in G11 result set")
            seen_ids.add(result.scenario_id)
            if pair in seen_pairs:
                raise BrokerSimulationGateError("duplicate market/scenario result in G11 result set")
            seen_pairs.add(pair)
            if pair not in required_pairs:
                raise BrokerSimulationGateError("unexpected G11 scenario result")
            if result.control_outcome != self._policy.expected_controls[result.scenario_type] or not result.passed:
                raise BrokerSimulationGateError("G11 scenario did not meet expected fail-closed control")
            if not result.reference_only or result.real_venue_query or result.external_order_submission or result.live_execution_authority:
                raise BrokerSimulationGateError("G11 scenario grants forbidden authority")
        if seen_pairs != required_pairs:
            raise BrokerSimulationGateError("G11 required scenario matrix is incomplete")

    def _validate_quality(self, summary: Mapping[str, object]) -> None:
        if summary.get("quality_band") != self._policy.required_quality_band:
            raise BrokerSimulationGateError("P20-H reference quality is not within required budget")
        authority_value = summary.get("authority")
        if not isinstance(authority_value, Mapping):
            raise BrokerSimulationGateError("P20-H quality authority block missing")
        authority = cast(Mapping[str, object], authority_value)
        required = {
            "reference_only": True,
            "real_venue_query": False,
            "production_execution_certification": False,
            "broker_certification": False,
            "external_order_submission": False,
            "live_execution_authority": False,
            "g11_execution_validated": False,
        }
        for key, value in required.items():
            if authority.get(key) != value:
                raise BrokerSimulationGateError(f"P20-H quality authority mismatch: {key}")
