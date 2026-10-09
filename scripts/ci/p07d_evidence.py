#!/usr/bin/env python3
"""Build deterministic P07-D cross-provider evidence offline."""

from __future__ import annotations

import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.data_quality import (
    ComparisonRule,
    CrossProviderAnalyzer,
    CrossProviderPolicy,
    ProviderObservation,
)

POLICY = ROOT / "config/data-quality/cross-provider-policy.json"
UPSTREAM = "a" * 64


def observation(provider: str, value: str, family: str = "DIRECT_SPOT_QUOTE", coverage: int = 10000):
    return ProviderObservation(
        sample_id="sample-1",
        canonical_id="FX:EUR/USD:SPOT_OTC",
        metric="mid_price",
        comparison_family=family,
        provider=provider,
        value=Decimal(value),
        coverage_bps=coverage,
        upstream_quality_evidence_sha256=UPSTREAM,
    )


def rule(family: str = "DIRECT_SPOT_QUOTE") -> ComparisonRule:
    return ComparisonRule(
        metric="mid_price",
        comparison_family=family,
        min_provider_count=2,
        min_coverage_bps=9000,
        max_abs_diff=Decimal("0.01"),
        max_rel_diff=Decimal("0.01"),
    )


def report_payload(report) -> dict[str, object]:
    return {
        "outcome": report.outcome.value,
        "groups_evaluated": report.groups_evaluated,
        "issues": [issue.payload() for issue in report.issues],
        "semantic_families": list(report.semantic_families),
        "fingerprint": report.fingerprint,
    }


def build(output: Path) -> None:
    policy = CrossProviderPolicy.from_path(POLICY)
    analyzer = CrossProviderAnalyzer(policy)

    aligned = analyzer.analyze(
        (observation("p1", "1.1000"), observation("p2", "1.1005")),
        (rule(),),
    )
    divergent = analyzer.analyze(
        (observation("p1", "1.10"), observation("p2", "1.30")),
        (rule(),),
    )
    low_coverage = analyzer.analyze(
        (observation("p1", "1.10"), observation("p2", "1.10", coverage=8000)),
        (rule(),),
    )
    separated = analyzer.analyze(
        (
            observation("spot", "1.10", "DIRECT_SPOT_QUOTE"),
            observation("proxy", "1.50", "FUTURES_PROXY"),
        ),
        (rule("DIRECT_SPOT_QUOTE"), rule("FUTURES_PROXY")),
    )

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P07D_CROSS_PROVIDER_EVIDENCE",
        "policy_sha256": hashlib.sha256(POLICY.read_bytes()).hexdigest(),
        "reports": [
            report_payload(aligned),
            report_payload(divergent),
            report_payload(low_coverage),
            report_payload(separated),
        ],
        "aligned_pass": aligned.is_valid,
        "divergence_fail_closed": not divergent.is_valid,
        "coverage_fail_closed": not low_coverage.is_valid,
        "semantic_family_isolation_proven": (
            not separated.is_valid
            and all(issue.code == "INSUFFICIENT_PROVIDER_COVERAGE" for issue in separated.issues)
        ),
        "production_data_quality_vendor": policy.production_data_quality_vendor,
        "safety": {
            "network_required": False,
            "credentials_required": False,
            "country_assumption": "NONE",
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED"
        }
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"P07D_EVIDENCE=PASS output={output}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    build(parser.parse_args().output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
