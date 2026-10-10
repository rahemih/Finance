from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.fundamental_intelligence.crypto_onchain_context import (
    ChainBlockAnchor,
    CryptoOnchainPoint,
    CryptoOnchainPolicy,
    CryptoOnchainStore,
    assert_no_crypto_onchain_trade_authority_fields,
)

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/fundamental-intelligence/crypto-onchain-context-policy.json"
A_HASH = "0x" + "a" * 64
B_HASH = "0x" + "b" * 64
C_HASH = "0x" + "c" * 64


def anchor(block: int, block_hash: str, timestamp: int, observed: int, finality: str) -> ChainBlockAnchor:
    return ChainBlockAnchor("1", block, block_hash, timestamp, observed, finality, "BLOCKSCOUT")


def point(series: str, subject_kind: str, subject_id: str, metric: str, value: str, unit: str, block_anchor: ChainBlockAnchor) -> CryptoOnchainPoint:
    digest = hashlib.sha256(f"{series}:{subject_kind}:{subject_id}:{metric}:{value}:{unit}:{block_anchor.anchor_id}".encode()).hexdigest()
    return CryptoOnchainPoint(series, subject_kind, subject_id, metric, value, unit, block_anchor, digest)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    p = CryptoOnchainPolicy.from_path(POLICY_PATH)
    supply_100 = point("ETH:USDC:SUPPLY", "TOKEN", "1:USDC", "TOKEN_TOTAL_SUPPLY", "1000000", "RAW_BASE_UNITS", anchor(100, A_HASH, 100, 110, "FINALIZED"))
    supply_101 = point("ETH:USDC:SUPPLY", "TOKEN", "1:USDC", "TOKEN_TOTAL_SUPPLY", "1100000", "RAW_BASE_UNITS", anchor(101, B_HASH, 120, 130, "FINALIZED"))
    tx_before = point("ETH:NETWORK:TX_COUNT", "NETWORK", "1", "NETWORK_TRANSACTION_COUNT", "200", "COUNT", anchor(200, A_HASH, 200, 210, "PROVISIONAL"))
    tx_after = point("ETH:NETWORK:TX_COUNT", "NETWORK", "1", "NETWORK_TRANSACTION_COUNT", "198", "COUNT", anchor(200, C_HASH, 200, 230, "FINALIZED"))
    store = CryptoOnchainStore((supply_100, supply_101, tx_before, tx_after), policy=p)

    supply_before = store.resolve_latest_as_of(series_id="ETH:USDC:SUPPLY", decision_time_ns=115)
    supply_after = store.resolve_latest_as_of(series_id="ETH:USDC:SUPPLY", decision_time_ns=140)
    reorg_before = store.resolve_latest_as_of(series_id="ETH:NETWORK:TX_COUNT", decision_time_ns=220)
    reorg_after = store.resolve_latest_as_of(series_id="ETH:NETWORK:TX_COUNT", decision_time_ns=240)
    if None in (supply_before, supply_after, reorg_before, reorg_after):
        raise RuntimeError("P10-G evidence fixture failed")
    assert supply_before is not None and supply_after is not None
    assert reorg_before is not None and reorg_after is not None
    assert_no_crypto_onchain_trade_authority_fields()

    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P10G_CRYPTO_ONCHAIN_CONTEXT_EVIDENCE",
        "task_id": "FIN-P10-WG-001",
        "policy_sha256": hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest(),
        "store_fingerprint": store.fingerprint,
        "supplemental_source_id": p.supplemental_source_id,
        "independent_validation": p.independent_validation,
        "production_source_mapping": p.production_source_mapping,
        "ethereum_mainnet_chain_id": "1",
        "pre_later_block_supply_value": supply_before.value_text,
        "post_later_block_supply_value": supply_after.value_text,
        "pre_reorg_chain_view_hash": reorg_before.anchor.block_hash,
        "post_reorg_chain_view_hash": reorg_after.anchor.block_hash,
        "reorg_views_preserved": len(store.chain_views_for_block(series_id="ETH:NETWORK:TX_COUNT", block_number=200)),
        "unverified_exchange_wallet_labels_allowed": p.unverified_exchange_wallet_labels_allowed,
        "market_direction_interpretation_allowed": p.market_direction_interpretation_allowed,
        "causal_market_impact_claim_allowed": p.causal_market_impact_claim_allowed,
        "country_assumption": "NONE",
        "live_trading": p.live_trading,
        "auto_trading": p.auto_trading,
        "network_required": p.network_required,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"P10G_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
