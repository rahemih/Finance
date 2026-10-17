#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from packages.learning.journal import (
    DecisionJournalEntry,
    DecisionOutcomeJournal,
    OutcomeJournalEntry,
)


def build_evidence() -> dict[str, object]:
    journal = DecisionOutcomeJournal()
    decision = DecisionJournalEntry(
        decision_id="ci-decision-1",
        session_spec_id="a" * 64,
        session_state_id="b" * 64,
        sequence=1,
        decision_time_ns=1000,
        asset_id="BTC-USD",
        quantity_delta="1",
        strategy_id="strategy-alpha",
        strategy_version="1.0.0",
        model_id="model-alpha",
        model_version="1.0.0",
        signal_id="signal-1",
        risk_decision_id="risk-1",
        firewall_decision_id="firewall-1",
        market_evidence_sha256="c" * 64,
    )
    decision_record_id = journal.append_decision(decision)
    outcome_record_id = journal.append_outcome(
        OutcomeJournalEntry(
            outcome_id="ci-outcome-1",
            decision_record_id=decision_record_id,
            observed_at_ns=3000,
            outcome_definition_id="return-bps",
            outcome_definition_version="1.0.0",
            outcome_value="125",
            outcome_evidence_sha256="d" * 64,
        )
    )

    early = journal.view_at(2000)
    late = journal.view_at(3000)
    if early.outcome_record_ids:
        raise RuntimeError("P18-B future outcome leaked into point-in-time view")
    if late.outcome_record_ids != (outcome_record_id,):
        raise RuntimeError("P18-B observable outcome missing from journal view")
    if late.training_authority or late.dataset_curation_authority:
        raise RuntimeError("P18-B must not grant P18-C training authority")
    if late.live_trading != "DISABLED" or late.auto_trading != "DISABLED":
        raise RuntimeError("P18-B trading authority boundary violated")

    return {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P18B_DECISION_OUTCOME_JOURNAL_EVIDENCE",
        "task_id": "FIN-P18-WB-001",
        "decision_record_id": decision_record_id,
        "outcome_record_id": outcome_record_id,
        "journal_root_id": journal.root_id,
        "early_view_root_id": early.journal_root_id,
        "late_view_root_id": late.journal_root_id,
        "early_visible_outcomes": list(early.outcome_record_ids),
        "late_visible_outcomes": list(late.outcome_record_ids),
        "dataset_curation_authority": late.dataset_curation_authority,
        "training_authority": late.training_authority,
        "broker_exchange_routing": late.broker_exchange_routing,
        "automatic_live_promotion": late.automatic_live_promotion,
        "live_trading": late.live_trading,
        "auto_trading": late.auto_trading,
        "p18_c_started": False,
        "p19_started": False,
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
    print(f"P18B_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
