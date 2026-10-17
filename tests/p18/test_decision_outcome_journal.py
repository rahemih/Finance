from __future__ import annotations

from dataclasses import replace
import unittest

from packages.learning.journal import (
    DecisionJournalEntry,
    DecisionOutcomeJournal,
    DecisionOutcomeJournalError,
    OutcomeJournalEntry,
)


def decision(
    *,
    decision_id: str = "decision-1",
    sequence: int = 1,
    decision_time_ns: int = 1000,
) -> DecisionJournalEntry:
    return DecisionJournalEntry(
        decision_id=decision_id,
        session_spec_id="a" * 64,
        session_state_id="b" * 64,
        sequence=sequence,
        decision_time_ns=decision_time_ns,
        asset_id="BTC-USD",
        quantity_delta="1.25",
        strategy_id="strategy-alpha",
        strategy_version="1.0.0",
        model_id="model-alpha",
        model_version="2.0.0",
        signal_id="signal-1",
        risk_decision_id="risk-1",
        firewall_decision_id="firewall-1",
        market_evidence_sha256="c" * 64,
    )


def outcome(
    decision_record_id: str,
    *,
    outcome_id: str = "outcome-1",
    observed_at_ns: int = 3000,
    outcome_value: str = "125",
) -> OutcomeJournalEntry:
    return OutcomeJournalEntry(
        outcome_id=outcome_id,
        decision_record_id=decision_record_id,
        observed_at_ns=observed_at_ns,
        outcome_definition_id="return-bps",
        outcome_definition_version="1.0.0",
        outcome_value=outcome_value,
        outcome_evidence_sha256="d" * 64,
    )


class TestDecisionOutcomeJournal(unittest.TestCase):
    def test_deterministic_record_and_root_identity(self) -> None:
        first = DecisionOutcomeJournal()
        second = DecisionOutcomeJournal()
        first_decision = decision()
        second_decision = decision()

        first_id = first.append_decision(first_decision)
        second_id = second.append_decision(second_decision)
        self.assertEqual(first_id, second_id)

        first.append_outcome(outcome(first_id))
        second.append_outcome(outcome(second_id))
        self.assertEqual(first.root_id, second.root_id)
        self.assertEqual(
            first.view_at(4000).journal_root_id,
            second.view_at(4000).journal_root_id,
        )

    def test_duplicate_decision_identity_fails_closed(self) -> None:
        journal = DecisionOutcomeJournal()
        journal.append_decision(decision())
        with self.assertRaisesRegex(
            DecisionOutcomeJournalError,
            "duplicate or conflicting decision",
        ):
            journal.append_decision(
                replace(decision(), quantity_delta="2")
            )

    def test_unknown_outcome_fails_closed(self) -> None:
        journal = DecisionOutcomeJournal()
        with self.assertRaisesRegex(
            DecisionOutcomeJournalError,
            "unknown decision",
        ):
            journal.append_outcome(outcome("e" * 64))

    def test_outcome_before_decision_fails_closed(self) -> None:
        journal = DecisionOutcomeJournal()
        record_id = journal.append_decision(
            decision(decision_time_ns=2000)
        )
        with self.assertRaisesRegex(
            DecisionOutcomeJournalError,
            "before decision",
        ):
            journal.append_outcome(
                outcome(record_id, observed_at_ns=1999)
            )

    def test_future_outcome_is_hidden_from_point_in_time_view(self) -> None:
        journal = DecisionOutcomeJournal()
        record_id = journal.append_decision(decision())
        outcome_id = journal.append_outcome(
            outcome(record_id, observed_at_ns=3000)
        )

        early = journal.view_at(2000)
        late = journal.view_at(3000)
        self.assertEqual(early.decision_record_ids, (record_id,))
        self.assertEqual(early.outcome_record_ids, ())
        self.assertEqual(late.outcome_record_ids, (outcome_id,))

    def test_decision_lineage_is_preserved_exactly(self) -> None:
        entry = decision()
        payload = entry.payload()
        self.assertEqual(payload["session_spec_id"], "a" * 64)
        self.assertEqual(payload["session_state_id"], "b" * 64)
        self.assertEqual(payload["strategy_id"], "strategy-alpha")
        self.assertEqual(payload["strategy_version"], "1.0.0")
        self.assertEqual(payload["model_id"], "model-alpha")
        self.assertEqual(payload["model_version"], "2.0.0")
        self.assertEqual(payload["signal_id"], "signal-1")
        self.assertEqual(payload["risk_decision_id"], "risk-1")
        self.assertEqual(payload["firewall_decision_id"], "firewall-1")
        self.assertEqual(payload["market_evidence_sha256"], "c" * 64)

    def test_outcome_observed_time_cannot_decrease(self) -> None:
        journal = DecisionOutcomeJournal()
        first_id = journal.append_decision(decision())
        second_id = journal.append_decision(
            decision(
                decision_id="decision-2",
                sequence=2,
                decision_time_ns=1500,
            )
        )
        journal.append_outcome(
            outcome(first_id, outcome_id="outcome-1", observed_at_ns=4000)
        )
        with self.assertRaisesRegex(
            DecisionOutcomeJournalError,
            "observed time cannot decrease",
        ):
            journal.append_outcome(
                outcome(
                    second_id,
                    outcome_id="outcome-2",
                    observed_at_ns=3999,
                )
            )

    def test_safety_authority_remains_disabled(self) -> None:
        journal = DecisionOutcomeJournal()
        record_id = journal.append_decision(decision())
        journal.append_outcome(outcome(record_id))
        view = journal.view_at(5000)
        self.assertFalse(view.dataset_curation_authority)
        self.assertFalse(view.training_authority)
        self.assertFalse(view.broker_exchange_routing)
        self.assertFalse(view.automatic_live_promotion)
        self.assertEqual(view.live_trading, "DISABLED")
        self.assertEqual(view.auto_trading, "DISABLED")


if __name__ == "__main__":
    unittest.main()
