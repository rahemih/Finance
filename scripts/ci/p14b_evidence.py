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
from packages.signal_intelligence.weighted_fusion import (
    WeightedFusionPolicy,
    fuse_evidence,
)


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_POLICY_PATH = ROOT / "config/signal-intelligence/evidence-contract-policy.json"
FUSION_POLICY_PATH = ROOT / "config/signal-intelligence/weighted-evidence-fusion-policy.json"


def item(
    *,
    phase: str,
    source_family: str,
    evidence_family: str,
    group: str,
    direction: int,
    strength: int,
    quality: int,
    index: int,
    valid_until_ns: int = 1200,
    hard_veto: bool = False,
    veto_codes: tuple[str, ...] = (),
) -> SignalEvidence:
    return SignalEvidence(
        source_phase=phase,
        source_family=source_family,
        evidence_family=evidence_family,
        independence_group=group,
        subject_id="BTC-USD",
        timeframe="1h",
        regime_label="TRENDING",
        direction=direction,
        strength_bps=strength,
        quality_bps=quality,
        sample_count=100 + index * 10,
        event_time_ns=900,
        as_of_time_ns=1000,
        valid_until_ns=valid_until_ns,
        source_record_id=f"p14b-{index}",
        provenance_sha256=f"{index + 1:x}" * 64,
        invalidation="source invalidated",
        hard_veto=hard_veto,
        veto_codes=veto_codes,
    )


def bundle(policy: EvidenceContractPolicy, records: tuple[SignalEvidence, ...]) -> EvidenceBundle:
    return EvidenceBundle.build(policy=policy, subject_id="BTC-USD", as_of_time_ns=1000, evidence=records)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    evidence_policy = EvidenceContractPolicy.from_path(EVIDENCE_POLICY_PATH)
    fusion_policy = WeightedFusionPolicy.from_path(FUSION_POLICY_PATH)
    records = (
        item(phase="P08", source_family="TECHNICAL", evidence_family="TREND", group="TECH_TREND", direction=1, strength=8000, quality=9000, index=0),
        item(phase="P08", source_family="TECHNICAL", evidence_family="MOMENTUM", group="TECH_TREND", direction=1, strength=4000, quality=5000, index=1),
        item(phase="P09", source_family="ORDER_FLOW_LIQUIDITY", evidence_family="CVD", group="FLOW_DELTA", direction=1, strength=7000, quality=8000, index=2),
        item(phase="P10", source_family="FUNDAMENTAL_MACRO", evidence_family="MACRO", group="MACRO_GROWTH", direction=-1, strength=5000, quality=8000, index=3),
        item(phase="P11", source_family="NEWS_SENTIMENT", evidence_family="NEWS", group="NEWS_EXPIRED", direction=1, strength=9000, quality=9000, index=4, valid_until_ns=950),
    )
    fused = fuse_evidence(bundle=bundle(evidence_policy, records), policy=fusion_policy)
    veto = item(
        phase="P13",
        source_family="TIMING_OPPORTUNITY",
        evidence_family="NO_TRADE",
        group="TIMING_VETO",
        direction=0,
        strength=0,
        quality=10000,
        index=5,
        hard_veto=True,
        veto_codes=("P13_NO_TRADE",),
    )
    blocked = fuse_evidence(bundle=bundle(evidence_policy, records + (veto,)), policy=fusion_policy)

    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P14B_WEIGHTED_EVIDENCE_FUSION",
        "task_id": "FIN-P14-WB-001",
        "evidence_policy_sha256": hashlib.sha256(EVIDENCE_POLICY_PATH.read_bytes()).hexdigest(),
        "fusion_policy_sha256": hashlib.sha256(FUSION_POLICY_PATH.read_bytes()).hexdigest(),
        "fused": fused.payload() | {"fusion_id": fused.fusion_id},
        "blocked": blocked.payload() | {"fusion_id": blocked.fusion_id},
        "empirical_probability": None,
        "llm_weighting_authority": False,
        "live_trading": fusion_policy.live_trading,
        "auto_trading": fusion_policy.auto_trading,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"P14B_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
