from __future__ import annotations

from dataclasses import replace
import hashlib
from pathlib import Path
import unittest

from packages.historical_data.replay_snapshot import (
    ReplayDatasetRef,
    ReplaySnapshot,
    ReplaySnapshotPolicy,
)
from packages.shadow.data_replay import (
    DataReplayEngine,
    DataReplayPolicy,
    ReplayDataEvent,
)
from packages.shadow.decision_replay import (
    DecisionReplayCase,
    DecisionReplayEngine,
    DecisionReplayError,
    DecisionReplayPolicy,
)
from packages.shadow.shadow_decisioning import (
    ShadowDecisionInput,
    ShadowDecisionLedger,
    ShadowDecisionPolicy,
)


ROOT = Path(__file__).resolve().parents[2]
DATA_POLICY = DataReplayPolicy.from_path(ROOT / "config/shadow/data-replay-policy.json")
DECISION_POLICY = DecisionReplayPolicy.from_path(ROOT / "config/shadow/decision-replay-policy.json")
SHADOW_POLICY = ShadowDecisionPolicy.from_path(ROOT / "config/shadow/shadow-decisioning-policy.json")
SNAPSHOT_POLICY = ReplaySnapshotPolicy.from_path(
    ROOT / "config/historical-data/replay-snapshot-policy.json"
)


def h(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def snapshot() -> ReplaySnapshot:
    return ReplaySnapshot.build(
        replay_start_ns=1000,
        replay_end_ns=9000,
        snapshot_cutoff_ns=8000,
        clock_mode="CONTROLLED_SIMULATION_CLOCK",
        scope_ids=("BTC-USD",),
        dataset_refs=(
            ReplayDatasetRef(
                "btc-reference",
                h("dataset"),
                "1.0",
                1000,
                9000,
                h("membership"),
                "PUBLIC_REFERENCE",
            ),
        ),
        feature_refs=(),
        vintage_refs=(),
        quality_rule_versions=("p19c-test-v1",),
        config_sha256=h("config"),
        code_artifact_sha256=h("code"),
        rights_class="PUBLIC_REFERENCE",
        policy=SNAPSHOT_POLICY,
    )


def event(sequence: int) -> ReplayDataEvent:
    return ReplayDataEvent.create(
        sequence=sequence,
        event_time_ns=sequence * 1000,
        available_at_ns=sequence * 1000 + 100,
        dataset_name="btc-reference",
        dataset_version=h("dataset"),
        entity_id="BTC-USD",
        payload={"sequence": sequence, "close": 100 + sequence},
        source_evidence_sha256=h(f"source-{sequence}"),
    )


def shadow_input(observed: int, *, action: str = "LONG") -> ShadowDecisionInput:
    return ShadowDecisionInput(
        asset_id="BTC-USD",
        observed_at_ns=observed,
        market_available_at_ns=observed - 1,
        signal_id=h(f"signal-{observed}-{action}"),
        signal_as_of_ns=observed - 1,
        signal_action=action,
        empirical_probability_bps=7200 if action in {"LONG", "SHORT"} else None,
        overall_uncertainty_bps=800 if action in {"LONG", "SHORT"} else None,
        risk_validation_id=h("risk"),
        risk_status="PASS",
        risk_scale_bps=10_000,
        firewall_gate_id=h("firewall"),
        firewall_state="PASS",
        strategy_record_id=h("strategy"),
        model_record_id=h("model"),
        signal_evidence_sha256=h("signal-evidence"),
        risk_evidence_sha256=h("risk-evidence"),
        firewall_evidence_sha256=h("firewall-evidence"),
        quant_evidence_sha256=h("quant-evidence"),
        entry_low_scaled=99_500 if action in {"LONG", "SHORT"} else None,
        entry_high_scaled=100_500 if action in {"LONG", "SHORT"} else None,
        candidate_stop_scaled=(98_000 if action == "LONG" else 102_000) if action in {"LONG", "SHORT"} else None,
        candidate_target_scaled=(103_000 if action == "LONG" else 97_000) if action in {"LONG", "SHORT"} else None,
        price_scale=100 if action in {"LONG", "SHORT"} else None,
    )


def engine() -> tuple[DecisionReplayEngine, DataReplayEngine]:
    data = DataReplayEngine(
        snapshot=snapshot(),
        events=tuple(event(i) for i in range(1, 8)),
        policy=DATA_POLICY,
    )
    return (
        DecisionReplayEngine(
            data_replay=data,
            shadow_policy=SHADOW_POLICY,
            policy=DECISION_POLICY,
        ),
        data,
    )


def case_for(
    ledger: ShadowDecisionLedger,
    data: DataReplayEngine,
    *,
    name: str,
    observed: int,
    action: str = "LONG",
) -> DecisionReplayCase:
    value = shadow_input(observed, action=action)
    record = ledger.append(value)
    visible = data.replay_through(observed)
    return DecisionReplayCase(
        case_name=name,
        decision_time_ns=observed,
        required_event_ids=visible.event_ids,
        shadow_input=value,
        expected_input_id=value.input_id,
        expected_record_id=record.record_id,
        expected_disposition=record.disposition,
        expected_previous_record_id=record.previous_record_id,
    )


class DecisionReplayTests(unittest.TestCase):
    def test_exact_visible_prefix_reproduces_record(self) -> None:
        replay, data = engine()
        baseline = ShadowDecisionLedger(SHADOW_POLICY)
        case = case_for(baseline, data, name="one", observed=3001)
        result = replay.replay((case,))
        self.assertEqual(result.results[0].match_state, "EXACT_MATCH")
        self.assertEqual(result.results[0].replayed_record_id, case.expected_record_id)

    def test_multi_case_session_reproduces_previous_record_chain(self) -> None:
        replay, data = engine()
        baseline = ShadowDecisionLedger(SHADOW_POLICY)
        first = case_for(baseline, data, name="one", observed=3001)
        second = case_for(baseline, data, name="two", observed=5001, action="WAIT")
        result = replay.replay((first, second))
        self.assertEqual(len(result.results), 2)
        self.assertEqual(result.results[1].previous_record_id, first.expected_record_id)

    def test_missing_visible_event_fails_closed(self) -> None:
        replay, data = engine()
        baseline = ShadowDecisionLedger(SHADOW_POLICY)
        case = case_for(baseline, data, name="one", observed=3001)
        with self.assertRaises(DecisionReplayError):
            replay.replay((replace(case, required_event_ids=case.required_event_ids[:-1]),))

    def test_extra_visible_event_fails_closed(self) -> None:
        replay, data = engine()
        baseline = ShadowDecisionLedger(SHADOW_POLICY)
        case = case_for(baseline, data, name="one", observed=3001)
        with self.assertRaises(DecisionReplayError):
            replay.replay((replace(case, required_event_ids=case.required_event_ids + (h("extra"),)),))

    def test_event_order_mismatch_fails_closed(self) -> None:
        replay, data = engine()
        baseline = ShadowDecisionLedger(SHADOW_POLICY)
        case = case_for(baseline, data, name="one", observed=3001)
        with self.assertRaises(DecisionReplayError):
            replay.replay((replace(case, required_event_ids=tuple(reversed(case.required_event_ids))),))

    def test_expected_input_identity_drift_fails_closed(self) -> None:
        replay, data = engine()
        baseline = ShadowDecisionLedger(SHADOW_POLICY)
        case = case_for(baseline, data, name="one", observed=3001)
        with self.assertRaises(DecisionReplayError):
            replay.replay((replace(case, expected_input_id=h("wrong-input")),))

    def test_expected_record_identity_drift_fails_closed(self) -> None:
        replay, data = engine()
        baseline = ShadowDecisionLedger(SHADOW_POLICY)
        case = case_for(baseline, data, name="one", observed=3001)
        with self.assertRaises(DecisionReplayError):
            replay.replay((replace(case, expected_record_id=h("wrong-record")),))

    def test_expected_disposition_drift_fails_closed(self) -> None:
        replay, data = engine()
        baseline = ShadowDecisionLedger(SHADOW_POLICY)
        case = case_for(baseline, data, name="one", observed=3001)
        with self.assertRaises(DecisionReplayError):
            replay.replay((replace(case, expected_disposition="SHADOW_WAIT"),))

    def test_previous_record_chain_drift_fails_closed(self) -> None:
        replay, data = engine()
        baseline = ShadowDecisionLedger(SHADOW_POLICY)
        first = case_for(baseline, data, name="one", observed=3001)
        second = case_for(baseline, data, name="two", observed=5001, action="WAIT")
        with self.assertRaises(DecisionReplayError):
            replay.replay((first, replace(second, expected_previous_record_id=h("wrong-prev"))))

    def test_decision_times_must_increase(self) -> None:
        replay, data = engine()
        baseline = ShadowDecisionLedger(SHADOW_POLICY)
        first = case_for(baseline, data, name="one", observed=5001)
        second_value = shadow_input(4001, action="WAIT")
        second_record = ShadowDecisionLedger(SHADOW_POLICY).append(second_value)
        visible = data.replay_through(4001)
        second = DecisionReplayCase(
            case_name="two",
            decision_time_ns=4001,
            required_event_ids=visible.event_ids,
            shadow_input=second_value,
            expected_input_id=second_value.input_id,
            expected_record_id=second_record.record_id,
            expected_disposition=second_record.disposition,
            expected_previous_record_id=None,
        )
        with self.assertRaises(DecisionReplayError):
            replay.replay((first, second))

    def test_session_has_zero_execution_authority(self) -> None:
        replay, data = engine()
        baseline = ShadowDecisionLedger(SHADOW_POLICY)
        result = replay.replay((case_for(baseline, data, name="one", observed=3001),))
        self.assertFalse(result.fill_authority)
        self.assertFalse(result.execution_authority)
        self.assertFalse(result.order_routing_authority)
        self.assertFalse(result.p20_started)
        self.assertEqual(result.live_trading, "DISABLED")
        self.assertEqual(result.auto_trading, "DISABLED")


if __name__ == "__main__":
    unittest.main()
