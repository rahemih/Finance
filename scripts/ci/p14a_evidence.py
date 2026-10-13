from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.signal_intelligence.evidence_contract import (
    EvidenceBundle,
    EvidenceContractPolicy,
    SignalEvidence,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/signal-intelligence/evidence-contract-policy.json"


def item(
    *,
    phase: str,
    family: str,
    evidence_family: str,
    group: str,
    direction: int,
    index: int,
    hard_veto: bool = False,
    veto_codes: tuple[str, ...] = (),
) -> SignalEvidence:
    return SignalEvidence(
        source_phase=phase,
        source_family=family,
        evidence_family=evidence_family,
        independence_group=group,
        subject_id="BTC-USD",
        timeframe="1h",
        regime_label="TRENDING",
        direction=direction,
        strength_bps=6000 + index * 100,
        quality_bps=7000 + index * 100,
        sample_count=100 + index * 10,
        event_time_ns=900 + index,
        as_of_time_ns=1000,
        valid_until_ns=1200,
        source_record_id=f"p14a-source-{index}",
        provenance_sha256=f"{index + 1:x}" * 64,
        invalidation="upstream evidence invalidated or superseded",
        hard_veto=hard_veto,
        veto_codes=veto_codes,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    policy = EvidenceContractPolicy.from_path(POLICY_PATH)
    records = (
        item(phase="P08", family="TECHNICAL", evidence_family="TREND", group="TECH_TREND", direction=1, index=0),
        item(phase="P09", family="ORDER_FLOW_LIQUIDITY", evidence_family="CVD", group="FLOW_DELTA", direction=1, index=1),
        item(phase="P10", family="FUNDAMENTAL_MACRO", evidence_family="MACRO", group="MACRO_GROWTH", direction=1, index=2),
        item(phase="P11", family="NEWS_SENTIMENT", evidence_family="NEWS", group="NEWS_CONFIRMED", direction=0, index=3),
        item(phase="P12", family="MARKET_MEMORY", evidence_family="ANALOG", group="MEMORY_ANALOG", direction=1, index=4),
        item(
            phase="P13",
            family="TIMING_OPPORTUNITY",
            evidence_family="NO_TRADE",
            group="TIMING_VETO",
            direction=0,
            index=5,
            hard_veto=True,
            veto_codes=("P13_NO_TRADE",),
        ),
    )
    bundle = EvidenceBundle.build(
        policy=policy,
        subject_id="BTC-USD",
        as_of_time_ns=1000,
        evidence=records,
    )
    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P14A_EVIDENCE_CONTRACT_EVIDENCE",
        "task_id": "FIN-P14-WA-001",
        "policy_sha256": hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest(),
        "bundle_id": bundle.bundle_id,
        "subject_id": bundle.subject_id,
        "source_phases": list(bundle.source_phases),
        "independence_groups": list(bundle.independence_groups),
        "evidence_ids": [record.evidence_id for record in bundle.evidence],
        "hard_veto": bundle.hard_veto,
        "veto_codes": list(bundle.veto_codes),
        "expired_evidence_ids": list(bundle.expired_evidence_ids),
        "weighted_fusion": None,
        "empirical_probability": None,
        "llm_probability_authority": False,
        "live_trading": policy.live_trading,
        "auto_trading": policy.auto_trading,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"P14A_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
