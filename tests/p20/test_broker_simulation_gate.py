from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path
import unittest

from packages.execution.broker_simulation_gate import (
    BrokerSimulationEngine,
    BrokerSimulationGateError,
    BrokerSimulationPolicy,
    G11ExecutionValidationGate,
    SimulationScenario,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/execution/broker-simulation-g11-policy.json"


def manifest(workstream: str) -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "workstream": workstream,
        "state": "CANONICAL_COMPLETE",
        "safety": {
            "network_mode": "DISABLED",
            "live_execution_authority": False,
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        },
    }


def dependencies() -> dict[str, dict[str, object]]:
    return {f"P20-{letter}": manifest(f"P20-{letter}") for letter in "ABCDEFGH"}


def quality_summary() -> dict[str, object]:
    payload: dict[str, object] = {
        "quality_band": "WITHIN_REFERENCE_BUDGET",
        "authority": {
            "reference_only": True,
            "real_venue_query": False,
            "production_execution_certification": False,
            "broker_certification": False,
            "external_order_submission": False,
            "live_execution_authority": False,
            "g11_execution_validated": False,
        },
    }
    payload["summary_id"] = hashlib.sha256(repr(payload).encode()).hexdigest()
    return payload


class BrokerSimulationGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = BrokerSimulationPolicy.from_path(POLICY)

    def results(self):
        engine = BrokerSimulationEngine(self.policy)
        return tuple(
            engine.run(SimulationScenario(
                scenario_id=f"{market.lower()}-{scenario.lower()}",
                market=market,
                scenario_type=scenario,
            ))
            for market in self.policy.markets
            for scenario in self.policy.required_scenarios
        )

    def test_policy_is_reference_only(self) -> None:
        self.assertEqual(self.policy.gate_scope, "REFERENCE_SIMULATION_EXECUTION_VALIDATION")
        self.assertEqual(self.policy.live_trading, "DISABLED")
        self.assertEqual(self.policy.auto_trading, "DISABLED")

    def test_required_scenario_matrix_is_deterministic(self) -> None:
        first = self.results()
        second = self.results()
        self.assertEqual(first, second)
        self.assertEqual(len(first), 14)
        self.assertTrue(all(result.passed for result in first))

    def test_conflicting_scenario_identity_fails_closed(self) -> None:
        engine = BrokerSimulationEngine(self.policy)
        engine.run(SimulationScenario("same-id", "CRYPTO", "ACK_FILL"))
        with self.assertRaises(BrokerSimulationGateError):
            engine.run(SimulationScenario("same-id", "CRYPTO", "REJECT"))

    def test_missing_scenario_fails_gate(self) -> None:
        gate = G11ExecutionValidationGate(self.policy)
        with self.assertRaises(BrokerSimulationGateError):
            gate.evaluate(
                dependency_manifests=dependencies(),
                simulation_results=self.results()[:-1],
                execution_quality_summary=quality_summary(),
            )

    def test_noncanonical_dependency_fails_gate(self) -> None:
        deps = dependencies()
        deps["P20-G"]["state"] = "IN_PROGRESS"
        with self.assertRaises(BrokerSimulationGateError):
            G11ExecutionValidationGate(self.policy).evaluate(
                dependency_manifests=deps,
                simulation_results=self.results(),
                execution_quality_summary=quality_summary(),
            )

    def test_dependency_live_authority_fails_gate(self) -> None:
        deps = dependencies()
        safety = deps["P20-H"]["safety"]
        assert isinstance(safety, dict)
        safety["live_execution_authority"] = True
        with self.assertRaises(BrokerSimulationGateError):
            G11ExecutionValidationGate(self.policy).evaluate(
                dependency_manifests=deps,
                simulation_results=self.results(),
                execution_quality_summary=quality_summary(),
            )

    def test_degraded_quality_fails_gate(self) -> None:
        quality = quality_summary()
        quality["quality_band"] = "DEGRADED_REFERENCE"
        with self.assertRaises(BrokerSimulationGateError):
            G11ExecutionValidationGate(self.policy).evaluate(
                dependency_manifests=dependencies(),
                simulation_results=self.results(),
                execution_quality_summary=quality,
            )

    def test_forbidden_quality_authority_fails_gate(self) -> None:
        quality = quality_summary()
        authority = quality["authority"]
        assert isinstance(authority, dict)
        authority["real_venue_query"] = True
        with self.assertRaises(BrokerSimulationGateError):
            G11ExecutionValidationGate(self.policy).evaluate(
                dependency_manifests=dependencies(),
                simulation_results=self.results(),
                execution_quality_summary=quality,
            )

    def test_g11_pass_is_deterministic_and_non_live(self) -> None:
        gate = G11ExecutionValidationGate(self.policy)
        first = gate.evaluate(
            dependency_manifests=dependencies(),
            simulation_results=self.results(),
            execution_quality_summary=quality_summary(),
        )
        second = gate.evaluate(
            dependency_manifests=dependencies(),
            simulation_results=self.results(),
            execution_quality_summary=quality_summary(),
        )
        self.assertEqual(first, second)
        self.assertEqual(first["gate_status"], "PASS")
        self.assertEqual(first["gate_scope"], "REFERENCE_SIMULATION_EXECUTION_VALIDATION")
        authority = first["authority"]
        assert isinstance(authority, dict)
        self.assertTrue(authority["reference_simulation_validated"])
        self.assertFalse(authority["production_broker_certification"])
        self.assertFalse(authority["real_venue_query"])
        self.assertFalse(authority["live_execution_validated"])
        self.assertFalse(authority["live_execution_authority"])
        self.assertFalse(authority["p21_started"])


if __name__ == "__main__":
    unittest.main()
