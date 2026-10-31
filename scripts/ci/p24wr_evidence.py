#!/usr/bin/env python3
"""Repeatable P24-WR synthetic-only venue research evidence."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from packages.production.offline_venue_contract import (
    OfflineVenueError,
    OfflineVenueReference,
    SyntheticIntent,
    canonical_bytes,
)

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/production/offline-venue-reference-policy.json"


def sample(venue: str, market: str) -> SyntheticIntent:
    return SyntheticIntent(
        venue_id=venue,
        market=market,
        action="SUBMIT_MOCK",
        side="BUY",
        client_order_id=f"mock-{market.lower()}-001",
        quantity_scaled=100,
        quantity_step_scaled=10,
        price_scaled=5000,
        price_tick_scaled=5,
        feed_sequence=20,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    reference = OfflineVenueReference.from_path(POLICY)
    forex = reference.evaluate(sample("FIBO_CTRADER_DEMO_REFERENCE", "FOREX"))
    spot = reference.evaluate(sample("TABDEAL_SPOT_MOCK_REFERENCE", "CRYPTO"))

    veto_denied = False
    try:
        guarded = SyntheticIntent(
            venue_id="TABDEAL_SPOT_MOCK_REFERENCE",
            market="CRYPTO",
            action="CLOSE_LEVERAGE",
            side="SELL",
            client_order_id="leverage-must-deny",
            quantity_scaled=100,
            quantity_step_scaled=10,
            price_scaled=5000,
            price_tick_scaled=5,
            feed_sequence=20,
            leveraged=True,
        )
        reference.evaluate(guarded)
    except OfflineVenueError:
        veto_denied = True
    if not veto_denied:
        raise OfflineVenueError("leverage negative control unexpectedly accepted")

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "task_id": "FIN-P24-WR-001",
        "claim_scope": "RESEARCH_SIMULATOR_ONLY",
        "policy_id": reference.policy_id,
        "forex_decision_id": forex.decision_id,
        "crypto_spot_decision_id": spot.decision_id,
        "leverage_refused": veto_denied,
        "network_mode": "DISABLED",
        "external_orders": False,
        "live_trading": "DISABLED",
        "auto_trading": "DISABLED",
        "first_live_gate": "NOT_GRANTED",
        "g13": "NOT_STARTED",
        "production_venue_selection": False,
        "pre_first_live_satisfied": 0,
        "p24_b": "BLOCKED_HUMAN_AND_PRODUCTION_PREREQUISITES",
    }
    evidence_id = hashlib.sha256(canonical_bytes(payload)).hexdigest()
    dest = Path(args.output)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(canonical_bytes({**payload, "evidence_id": evidence_id}) + b"\n")
    print(f"P24_WR_OFFLINE_REFERENCE=PASS evidence_id={evidence_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
