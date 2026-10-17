from __future__ import annotations

from dataclasses import replace
import unittest

from quant.backtesting.quant_gate import (
    BenchmarkCriterion,
    QuantGateError,
    WorkstreamEvidence,
    certify_g9_quant_validated,
)


def workstreams() -> tuple[WorkstreamEvidence,...]:
    return tuple(
        WorkstreamEvidence(f"P17-{letter}", f"{i:x}".rjust(64,"0"))
        for i,letter in enumerate("ABCDEFGH", start=1)
    )


def criteria() -> tuple[BenchmarkCriterion,...]:
    return (
        BenchmarkCriterion("OOS_EDGE","oos-edge",110,100,"GE","a"*64),
        BenchmarkCriterion("RISK","max-risk",80,100,"LE","b"*64),
        BenchmarkCriterion("ROBUSTNESS","robustness",105,100,"GE","c"*64),
        BenchmarkCriterion("CAPACITY","capacity",120,100,"GE","d"*64),
        BenchmarkCriterion("EXECUTION_REALISM","execution-cost",90,100,"LE","e"*64),
    )


class QuantGateTests(unittest.TestCase):
    def test_complete_evidence_passes_g9(self) -> None:
        gate=certify_g9_quant_validated(
            workstream_evidence=workstreams(),
            benchmark_criteria=criteria(),
            strategy_registry_sha256="f"*64,
            model_registry_sha256="1"*64,
        )
        self.assertEqual(gate.gate_name,"G9_QUANT_VALIDATED")
        self.assertEqual(gate.state,"PASS")
        self.assertEqual(gate.next_phase,"P18")
        self.assertEqual(gate.next_phase_state,"NOT_STARTED_OWNER_PHASE_AUTHORIZATION_REQUIRED")
        self.assertFalse(gate.automatic_p18_promotion)
        self.assertFalse(gate.execution_authority)

    def test_missing_workstream_fails_closed(self) -> None:
        with self.assertRaises(QuantGateError):
            certify_g9_quant_validated(
                workstream_evidence=workstreams()[:-1],
                benchmark_criteria=criteria(),
                strategy_registry_sha256="f"*64,
                model_registry_sha256="1"*64,
            )

    def test_duplicate_workstream_fails_closed(self) -> None:
        rows=list(workstreams())
        rows[-1]=replace(rows[-1],workstream="P17-G",evidence_sha256="9"*64)
        with self.assertRaises(QuantGateError):
            certify_g9_quant_validated(workstream_evidence=rows,benchmark_criteria=criteria(),strategy_registry_sha256="f"*64,model_registry_sha256="1"*64)

    def test_failing_ge_criterion_fails_closed(self) -> None:
        rows=list(criteria())
        rows[0]=replace(rows[0],measured_value=99)
        with self.assertRaises(QuantGateError):
            certify_g9_quant_validated(workstream_evidence=workstreams(),benchmark_criteria=rows,strategy_registry_sha256="f"*64,model_registry_sha256="1"*64)

    def test_failing_le_criterion_fails_closed(self) -> None:
        rows=list(criteria())
        rows[1]=replace(rows[1],measured_value=101)
        with self.assertRaises(QuantGateError):
            certify_g9_quant_validated(workstream_evidence=workstreams(),benchmark_criteria=rows,strategy_registry_sha256="f"*64,model_registry_sha256="1"*64)

    def test_duplicate_category_fails_closed(self) -> None:
        rows=list(criteria())
        rows[-1]=replace(rows[-1],category="CAPACITY",evidence_sha256="9"*64)
        with self.assertRaises(QuantGateError):
            certify_g9_quant_validated(workstream_evidence=workstreams(),benchmark_criteria=rows,strategy_registry_sha256="f"*64,model_registry_sha256="1"*64)

    def test_invalid_hash_fails_closed(self) -> None:
        with self.assertRaises(QuantGateError):
            certify_g9_quant_validated(workstream_evidence=workstreams(),benchmark_criteria=criteria(),strategy_registry_sha256="bad",model_registry_sha256="1"*64)

    def test_order_independent_identity(self) -> None:
        left=certify_g9_quant_validated(workstream_evidence=workstreams(),benchmark_criteria=criteria(),strategy_registry_sha256="f"*64,model_registry_sha256="1"*64)
        right=certify_g9_quant_validated(workstream_evidence=tuple(reversed(workstreams())),benchmark_criteria=tuple(reversed(criteria())),strategy_registry_sha256="f"*64,model_registry_sha256="1"*64)
        self.assertEqual(left.gate_id,right.gate_id)


if __name__=="__main__":
    unittest.main()
