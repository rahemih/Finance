from __future__ import annotations

import hashlib
from pathlib import Path
import unittest

from packages.fundamental_intelligence.crypto_onchain_context import (
    ChainBlockAnchor,
    CryptoOnchainContextError,
    CryptoOnchainPoint,
    CryptoOnchainPolicy,
    CryptoOnchainStore,
    assert_no_crypto_onchain_trade_authority_fields,
    validate_anchor,
    validate_point,
)

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/fundamental-intelligence/crypto-onchain-context-policy.json"


def policy() -> CryptoOnchainPolicy:
    return CryptoOnchainPolicy.from_path(POLICY_PATH)


def anchor(
    *,
    block: int,
    block_hash: str,
    timestamp: int,
    observed: int,
    finality: str = "FINALIZED",
) -> ChainBlockAnchor:
    return ChainBlockAnchor(
        chain_id="1",
        block_number=block,
        block_hash=block_hash,
        block_timestamp_ns=timestamp,
        observed_at_ns=observed,
        finality_state=finality,
        source_id="BLOCKSCOUT",
    )


def point(
    *,
    series: str,
    subject_kind: str,
    subject_id: str,
    metric: str,
    value: str,
    unit: str,
    block_anchor: ChainBlockAnchor,
) -> CryptoOnchainPoint:
    digest = hashlib.sha256(
        f"{series}:{subject_kind}:{subject_id}:{metric}:{value}:{unit}:{block_anchor.anchor_id}".encode()
    ).hexdigest()
    return CryptoOnchainPoint(
        series_id=series,
        subject_kind=subject_kind,
        subject_id=subject_id,
        metric_kind=metric,
        value_text=value,
        unit=unit,
        anchor=block_anchor,
        source_snapshot_sha256=digest,
    )


A_HASH = "0x" + "a" * 64
B_HASH = "0x" + "b" * 64
C_HASH = "0x" + "c" * 64


class CryptoOnchainContextTests(unittest.TestCase):
    def test_anchor_and_metric_guards(self) -> None:
        p = policy()
        good_anchor = anchor(block=100, block_hash=A_HASH, timestamp=100, observed=105)
        self.assertEqual(validate_anchor(good_anchor, policy=p), good_anchor)
        good = point(
            series="ETH:USDC:HOLDERS",
            subject_kind="TOKEN",
            subject_id="1:0xA0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
            metric="TOKEN_HOLDER_COUNT",
            value="1000",
            unit="COUNT",
            block_anchor=good_anchor,
        )
        self.assertEqual(validate_point(good, policy=p), good)

        with self.assertRaises(CryptoOnchainContextError):
            validate_anchor(
                anchor(block=100, block_hash=A_HASH.upper(), timestamp=100, observed=105),
                policy=p,
            )
        bad = point(
            series="ETH:BAD",
            subject_kind="NETWORK",
            subject_id="1",
            metric="TOKEN_HOLDER_COUNT",
            value="1000",
            unit="COUNT",
            block_anchor=good_anchor,
        )
        with self.assertRaises(CryptoOnchainContextError):
            validate_point(bad, policy=p)

    def test_latest_as_of_is_point_in_time(self) -> None:
        p = policy()
        first = point(
            series="ETH:USDC:SUPPLY",
            subject_kind="TOKEN",
            subject_id="1:USDC",
            metric="TOKEN_TOTAL_SUPPLY",
            value="1000000",
            unit="RAW_BASE_UNITS",
            block_anchor=anchor(block=100, block_hash=A_HASH, timestamp=100, observed=110),
        )
        later = point(
            series="ETH:USDC:SUPPLY",
            subject_kind="TOKEN",
            subject_id="1:USDC",
            metric="TOKEN_TOTAL_SUPPLY",
            value="1100000",
            unit="RAW_BASE_UNITS",
            block_anchor=anchor(block=101, block_hash=B_HASH, timestamp=120, observed=130),
        )
        store = CryptoOnchainStore((first, later), policy=p)
        self.assertIsNone(store.resolve_latest_as_of(series_id=first.series_id, decision_time_ns=105))
        at_first = store.resolve_latest_as_of(series_id=first.series_id, decision_time_ns=115)
        at_later = store.resolve_latest_as_of(series_id=first.series_id, decision_time_ns=140)
        self.assertEqual(at_first, first)
        self.assertEqual(at_later, later)

    def test_reorg_preserves_prior_chain_view(self) -> None:
        p = policy()
        before = point(
            series="ETH:NETWORK:TX_COUNT",
            subject_kind="NETWORK",
            subject_id="1",
            metric="NETWORK_TRANSACTION_COUNT",
            value="200",
            unit="COUNT",
            block_anchor=anchor(block=200, block_hash=A_HASH, timestamp=200, observed=210, finality="PROVISIONAL"),
        )
        after = point(
            series="ETH:NETWORK:TX_COUNT",
            subject_kind="NETWORK",
            subject_id="1",
            metric="NETWORK_TRANSACTION_COUNT",
            value="198",
            unit="COUNT",
            block_anchor=anchor(block=200, block_hash=C_HASH, timestamp=200, observed=230, finality="FINALIZED"),
        )
        store = CryptoOnchainStore((before, after), policy=p)
        views = store.chain_views_for_block(series_id=before.series_id, block_number=200)
        self.assertEqual(len(views), 2)
        self.assertEqual(
            store.resolve_latest_as_of(series_id=before.series_id, decision_time_ns=220),
            before,
        )
        self.assertEqual(
            store.resolve_latest_as_of(series_id=before.series_id, decision_time_ns=240),
            after,
        )

    def test_unverified_exchange_label_not_in_contract(self) -> None:
        assert_no_crypto_onchain_trade_authority_fields()
        p = policy()
        self.assertFalse(p.unverified_exchange_wallet_labels_allowed)
        self.assertEqual(p.production_source_mapping, "NOT_SELECTED")
        self.assertEqual(p.independent_validation, "DIRECT_NODE_OR_SECOND_INDEXER_TBD")


if __name__ == "__main__":
    unittest.main()
