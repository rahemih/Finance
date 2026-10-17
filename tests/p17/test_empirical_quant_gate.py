from __future__ import annotations
import hashlib
import unittest
from dataclasses import replace
from quant.backtesting.empirical_quant_gate import (
    EmpiricalMeasurement,
    EmpiricalQuantGateError,
    EmpiricalWorkstreamEvidence,
    MetricSchema,
    certify_empirical_g9,
)

def h(v: str) -> str:
    return hashlib.sha256(v.encode()).hexdigest()

def ev() -> tuple[EmpiricalWorkstreamEvidence, ...]:
    return tuple(
        EmpiricalWorkstreamEvidence(f"P17-{letter}", h(f"e-{letter}"), h(f"p-{letter}"))
        for letter in "ABCDEFGH"
    )

def schemas() -> tuple[MetricSchema, ...]:
    return (
        MetricSchema("OOS_EDGE","TOTAL_NET_RETURN_BPS","1.0","BPS","GE",100),
        MetricSchema("RISK","MAX_DRAWDOWN_BPS","1.0","BPS","LE",700),
        MetricSchema("ROBUSTNESS","STRESSED_NET_RETURN_BPS","1.0","BPS","GE",50),
        MetricSchema("CAPACITY","MAX_NOTIONAL_TO_DAILY_QUOTE_VOLUME_PPM","1.0","PPM","LE",20),
        MetricSchema("EXECUTION_REALISM","GOVERNED_ROUNDTRIP_COST_BPS","1.0","BPS","LE",100),
    )

def ms(dataset: str) -> tuple[EmpiricalMeasurement, ...]:
    values={"OOS_EDGE":500,"RISK":400,"ROBUSTNESS":400,"CAPACITY":5,"EXECUTION_REALISM":50}
    return tuple(EmpiricalMeasurement(
        row.category,row.schema_id,values[row.category],h(f"m-{row.category}"),dataset
    ) for row in schemas())

def cert():
    dataset=h("dataset")
    return certify_empirical_g9(
        dataset_sha256=dataset,
        threshold_policy_sha256=h("policy"),
        strategy_registry_id=h("strategy"),
        model_registry_id=h("model"),
        workstream_evidence=ev(),
        metric_schemas=schemas(),
        measurements=ms(dataset),
    )

class EmpiricalGateTests(unittest.TestCase):
    def test_pass(self) -> None:
        result=cert()
        self.assertEqual(result.state,"PASS_EMPIRICAL_REFERENCE")
        self.assertFalse(result.fixture_only)
        self.assertFalse(result.profitability_guarantee)

    def test_fixture_fails(self) -> None:
        with self.assertRaises(EmpiricalQuantGateError):
            EmpiricalWorkstreamEvidence("P17-A",h("e"),h("p"),True)

    def test_placeholder_fails(self) -> None:
        dataset=h("dataset")
        with self.assertRaises(EmpiricalQuantGateError):
            certify_empirical_g9(
                dataset_sha256="a"*64,
                threshold_policy_sha256=h("policy"),
                strategy_registry_id=h("strategy"),
                model_registry_id=h("model"),
                workstream_evidence=ev(),
                metric_schemas=schemas(),
                measurements=ms(dataset),
            )

    def test_missing_workstream_fails(self) -> None:
        dataset=h("dataset")
        with self.assertRaises(EmpiricalQuantGateError):
            certify_empirical_g9(
                dataset_sha256=dataset,
                threshold_policy_sha256=h("policy"),
                strategy_registry_id=h("strategy"),
                model_registry_id=h("model"),
                workstream_evidence=ev()[:-1],
                metric_schemas=schemas(),
                measurements=ms(dataset),
            )

    def test_schema_mismatch_fails(self) -> None:
        dataset=h("dataset")
        rows=list(ms(dataset))
        rows[0]=replace(rows[0],metric_schema_id=h("wrong"))
        with self.assertRaises(EmpiricalQuantGateError):
            certify_empirical_g9(
                dataset_sha256=dataset,
                threshold_policy_sha256=h("policy"),
                strategy_registry_id=h("strategy"),
                model_registry_id=h("model"),
                workstream_evidence=ev(),
                metric_schemas=schemas(),
                measurements=rows,
            )

    def test_threshold_fails(self) -> None:
        dataset=h("dataset")
        rows=list(ms(dataset))
        rows[0]=replace(rows[0],measured_value=99)
        with self.assertRaises(EmpiricalQuantGateError):
            certify_empirical_g9(
                dataset_sha256=dataset,
                threshold_policy_sha256=h("policy"),
                strategy_registry_id=h("strategy"),
                model_registry_id=h("model"),
                workstream_evidence=ev(),
                metric_schemas=schemas(),
                measurements=rows,
            )

    def test_order_independent(self) -> None:
        left=cert()
        dataset=h("dataset")
        right=certify_empirical_g9(
            dataset_sha256=dataset,
            threshold_policy_sha256=h("policy"),
            strategy_registry_id=h("strategy"),
            model_registry_id=h("model"),
            workstream_evidence=tuple(reversed(ev())),
            metric_schemas=tuple(reversed(schemas())),
            measurements=tuple(reversed(ms(dataset))),
        )
        self.assertEqual(left.certificate_id,right.certificate_id)

if __name__=="__main__":
    unittest.main()
