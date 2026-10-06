#!/usr/bin/env python3
"""Persistent repository-native P05-A boundary revalidation."""

from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
P01_G = ROOT / "docs/03-research/P01-G-PROVIDER-BASELINE-DECISION.md"
P05A = ROOT / "docs/07-data/p05-a-crypto-realtime-adapter.json"
CONTRACT = ROOT / "packages/contracts/market_data.py"
ADAPTER = ROOT / "adapters/market_data/kaiko.py"


class RevalidationFailure(RuntimeError):
    pass


def fail(message: str) -> None:
    raise RevalidationFailure(message)


def main() -> int:
    try:
        p01 = P01_G.read_text(encoding="utf-8")
        if "Primary reference:\n- **Kaiko**" not in p01:
            fail("P01_G_KAIKO_PRIMARY_MISSING")
        if "Backup reference:\n- **CoinAPI**" not in p01:
            fail("P01_G_COINAPI_BACKUP_MISSING")

        manifest = json.loads(P05A.read_text(encoding="utf-8"))
        if manifest.get("state") != "P05-A_CANONICAL_COMPLETE":
            fail(f"P05A_STATE_INVALID state={manifest.get('state')}")
        provider = manifest.get("provider", {})
        if provider.get("name") != "Kaiko":
            fail("P05A_PROVIDER_INVALID")
        if provider.get("production_transport") != "NOT_SELECTED":
            fail("P05A_PRODUCTION_TRANSPORT_PREMATURE")
        if provider.get("live_connectivity") != "DISABLED_ENTITLEMENT_REQUIRED":
            fail("P05A_LIVE_CONNECTIVITY_INVALID")
        if manifest.get("canonical_ci_network_required") is not False:
            fail("P05A_CANONICAL_CI_NETWORK_MUST_BE_FALSE")

        neutral = CONTRACT.read_text(encoding="utf-8").lower()
        if "kaiko" in neutral:
            fail("PROVIDER_NEUTRAL_CONTRACT_LEAKS_KAIKO")
        adapter = ADAPTER.read_text(encoding="utf-8")
        for marker in (
            "HTTP_API_TESTING_ONLY",
            "secret://",
            "market_update_v1",
            "orderbookl2_v1",
        ):
            if marker not in adapter:
                fail(f"P05A_ADAPTER_MARKER_MISSING marker={marker}")

        safety = {
            "canary": manifest.get("canary"),
            "live_trading": manifest.get("live_trading"),
            "auto_trading": manifest.get("auto_trading"),
        }
        if safety != {
            "canary": "DISABLED",
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        }:
            fail(f"P05A_SAFETY_INVALID actual={safety}")

    except (OSError, json.JSONDecodeError, RevalidationFailure) as exc:
        print(f"P05A_REVALIDATION=FAIL error={exc}")
        return 1

    print("P05A_PROVIDER_BASELINE=PASS provider=Kaiko backup=CoinAPI")
    print("P05A_PROVIDER_NEUTRAL_BOUNDARY=PASS")
    print("P05A_CONNECTIVITY_SAFETY=PASS")
    print("P05A_REVALIDATION=PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
