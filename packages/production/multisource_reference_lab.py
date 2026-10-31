"""P24-WQ: deterministic, zero-network cross-venue market REFERENCE lab.

Only explicitly synthetic quotes; no Dukascopy, Binance or TradingView API is called.
P07's canonical CrossProviderAnalyzer is reused for aligned reference comparison.
No executable prices/orders, advice, DEMO success or real performance is claimed.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
from html import escape
import hashlib
import json
from pathlib import Path
from typing import cast

from packages.data_quality.cross_provider import (
    ComparisonRule,
    CrossProviderAnalyzer,
    CrossProviderPolicy,
    ProviderObservation,
)


class ReferenceLabError(ValueError):
    """Input or policy violates fail-closed synthetic-only reference boundary."""


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


ROLES: dict[str, tuple[str, str, str, str]] = {
    "DUKASCOPY_SIM": ("FOREX", "EURUSD", "DUKASCOPY", "REFERENCE"),
    "FX_INDEPENDENT_SIM": ("FOREX", "EURUSD", "INDEPENDENT_FX_ORIGIN", "REFERENCE"),
    "FIBO_SIM": ("FOREX", "EURUSD", "FIBO", "VENUE_MOCK"),
    "BINANCE_ARCHIVE_SIM": ("CRYPTO", "BTCUSDT", "BINANCE", "REFERENCE"),
    "CRYPTO_INDEPENDENT_SIM": ("CRYPTO", "BTCUSDT", "INDEPENDENT_CRYPTO_ORIGIN", "REFERENCE"),
    "USDTIRT_SIM": ("CRYPTO", "USDTIRT", "INDEPENDENT_FX_CONVERSION", "CONVERSION_MOCK"),
    "TABDEAL_SPOT_SIM": ("CRYPTO", "BTCIRT", "TABDEAL", "VENUE_MOCK"),
}
EXPECTED_POLICY: dict[str, object] = {
    "schema_version": "1.0",
    "task_id": "FIN-P24-WQ-001",
    "kind": "P24_WQ_SYNTHETIC_CROSS_VENUE_REFERENCE",
    "claim_scope": "SYNTHETIC_RESEARCH_ONLY",
    "network_mode": "DISABLED",
    "credentials_mode": "NONE",
    "license_mode": "SYNTHETIC_ONLY",
    "external_order_authority": False,
    "production_data_rights_verified": False,
    "tradingview_mode": "HUMAN_VISUAL_ONLY",
    "binance_authenticated_access": False,
    "markets": ["FOREX", "CRYPTO"],
    "max_age_ms": 2000,
    "max_alignment_ms": 500,
    "fx_max_drift_bps": 20,
    "crypto_max_drift_bps": 100,
    "venue_max_drift_bps": 200,
    "provider_roles": {
        code: {"market": values[0], "pair": values[1], "root": values[2], "role": values[3]}
        for code, values in ROLES.items()
    },
    "p24_b": "BLOCKED_HUMAN_AND_PRODUCTION_PREREQUISITES",
    "pre_first_live_satisfied": 0,
    "g13": "NOT_STARTED",
    "live_trading": "DISABLED",
    "auto_trading": "DISABLED",
}


@dataclass(frozen=True, slots=True)
class SyntheticQuote:
    provider: str
    market: str
    pair: str
    root: str
    role: str
    bid: Decimal
    ask: Decimal
    event_time_ms: int
    observed_time_ms: int
    lineage_sha256: str
    sample_id: str = "fixture-001"
    source_mode: str = "SYNTHETIC_ONLY"

    @property
    def mid(self) -> Decimal:
        return (self.bid + self.ask) / Decimal(2)

    def validate(self) -> None:
        if any(type(x) is not str for x in (
            self.provider, self.market, self.pair, self.root,
            self.role, self.lineage_sha256, self.sample_id, self.source_mode,
        )):
            raise ReferenceLabError("synthetic quote identity requires exact string types")
        if self.provider not in ROLES:
            raise ReferenceLabError("unapproved source adapter")
        if (self.market, self.pair, self.root, self.role) != ROLES[self.provider]:
            raise ReferenceLabError("provider market, pair, role or origin spoofing")
        if self.source_mode != "SYNTHETIC_ONLY" or self.sample_id != "fixture-001":
            raise ReferenceLabError("real data and unknown sample ID forbidden")
        if len(self.lineage_sha256) != 64 or any(c not in "0123456789abcdef" for c in self.lineage_sha256):
            raise ReferenceLabError("sha256 lineage required")
        if type(self.bid) is not Decimal or type(self.ask) is not Decimal:
            raise ReferenceLabError("bid/ask must be exact Decimal")
        if not self.bid.is_finite() or not self.ask.is_finite() or self.bid <= 0 or self.ask < self.bid:
            raise ReferenceLabError("nonpositive, nonfinite or crossed quote")
        if type(self.event_time_ms) is not int or type(self.observed_time_ms) is not int:
            raise ReferenceLabError("timestamps must be integer, not Boolean")
        if self.event_time_ms < 1 or self.observed_time_ms < self.event_time_ms:
            raise ReferenceLabError("invalid or future provider timestamp")


@dataclass(frozen=True, slots=True)
class Comparison:
    pair: str
    reference_mid: str
    destination_mid: str
    drift_bps: str
    limit_bps: int
    outcome: str
    note: str

    def payload(self) -> dict[str, object]:
        return asdict(self)


def _bps(reference: Decimal, dest: Decimal) -> Decimal:
    if reference <= 0:
        raise ReferenceLabError("invalid reference denominator")
    return abs(dest - reference) / reference * Decimal(10000)


def _compare(pair: str, ref: Decimal, dest: Decimal, limit: int, note: str) -> Comparison:
    bps = _bps(ref, dest)
    return Comparison(
        pair=pair, reference_mid=str(ref), destination_mid=str(dest),
        drift_bps=str(bps.quantize(Decimal("0.0001"))),
        limit_bps=limit,
        outcome="REFERENCE_ALIGNED" if bps <= Decimal(limit) else "QUARANTINED",
        note=note,
    )


class MultiSourceReferenceLab:
    def __init__(self, policy_path: Path, p07_policy_path: Path) -> None:
        try:
            raw: object = json.loads(policy_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ReferenceLabError("missing or invalid WQ policy") from exc
        if canonical(raw) != canonical(EXPECTED_POLICY):
            raise ReferenceLabError("noncanonical or unsafe WQ policy")
        self.policy_id = digest(raw)
        self.p07_policy = CrossProviderPolicy.from_path(p07_policy_path)
        if self.p07_policy.production_data_quality_vendor != "NOT_SELECTED":
            raise ReferenceLabError("unexpected production gate promotion")

    def evaluate(self, quotes: tuple[SyntheticQuote, ...], now_ms: int, *, risk_veto: bool = False) -> dict[str, object]:
        if self.policy_id != digest(EXPECTED_POLICY):
            raise ReferenceLabError("in-memory policy ID mutated")
        if type(now_ms) is not int or now_ms < 1 or type(risk_veto) is not bool:
            raise ReferenceLabError("invalid clock or risk veto type")
        if type(quotes) is not tuple or len(quotes) != len(ROLES):
            raise ReferenceLabError("exact seven synthetic source records required")
        sources: dict[str, SyntheticQuote] = {}
        for q in quotes:
            q.validate()
            if q.provider in sources:
                raise ReferenceLabError("duplicate source or missing independent record")
            sources[q.provider] = q
        if set(sources) != set(ROLES):
            raise ReferenceLabError("insufficient source diversity")
        issues: set[str] = set()
        times = [q.event_time_ms for q in sources.values()]
        if max(times) - min(times) > 500:
            issues.add("SOURCE_TIME_MISALIGNMENT")
        for q in sources.values():
            if now_ms < q.observed_time_ms or now_ms - q.event_time_ms > 2000:
                issues.add("STALE_OR_FUTURE_MARKET_REFERENCE")
            if q.observed_time_ms - q.event_time_ms > 2000:
                issues.add("COLLECTION_LATENCY_VIOLATION")
        # Different provider names do NOT prove independence. Bind to explicit roots.
        fx1, fx2 = sources["DUKASCOPY_SIM"], sources["FX_INDEPENDENT_SIM"]
        crypto1, crypto2 = sources["BINANCE_ARCHIVE_SIM"], sources["CRYPTO_INDEPENDENT_SIM"]
        for left, right in ((fx1, fx2), (crypto1, crypto2)):
            if left.root == right.root or left.lineage_sha256 == right.lineage_sha256:
                issues.add("CORRELATED_OR_REUSED_REFERENCE_LINEAGE")
        def obs(q: SyntheticQuote, canonical_id: str, family: str) -> ProviderObservation:
            return ProviderObservation(
                sample_id=q.sample_id, canonical_id=canonical_id, metric="mid_price",
                comparison_family=family, provider=q.provider, value=q.mid,
                coverage_bps=10000, upstream_quality_evidence_sha256=q.lineage_sha256,
            )
        analyzer = CrossProviderAnalyzer(self.p07_policy)
        fxcheck = analyzer.analyze(
            (obs(fx1, "FX:EUR/USD:SPOT_OTC", "FX_OTC_REF_MID"),
             obs(fx2, "FX:EUR/USD:SPOT_OTC", "FX_OTC_REF_MID")),
            (ComparisonRule(
                metric="mid_price", comparison_family="FX_OTC_REF_MID",
                min_provider_count=2, min_coverage_bps=9000,
                max_rel_diff=Decimal("0.0020"),
            ),),
        )
        cryptocheck = analyzer.analyze(
            (obs(crypto1, "CRYPTO:BTC/USDT:SPOT", "CRYPTO_SPOT_REF_MID"),
             obs(crypto2, "CRYPTO:BTC/USDT:SPOT", "CRYPTO_SPOT_REF_MID")),
            (ComparisonRule(
                metric="mid_price", comparison_family="CRYPTO_SPOT_REF_MID",
                min_provider_count=2, min_coverage_bps=9000,
                max_rel_diff=Decimal("0.0100"),
            ),),
        )
        if not fxcheck.is_valid or not cryptocheck.is_valid:
            issues.add("P07_INDEPENDENT_REFERENCE_DIVERGENCE")
        fx_ref = (fx1.mid + fx2.mid) / Decimal(2)
        btc_usdt_ref = (crypto1.mid + crypto2.mid) / Decimal(2)
        usdt_irt = sources["USDTIRT_SIM"].mid
        btc_irt_ref = btc_usdt_ref * usdt_irt
        comparisons = (
            _compare("EURUSD", fx_ref, sources["FIBO_SIM"].mid, 200,
                     "FIBO is a synthetic broker quote, never an executable price"),
            _compare("BTCIRT", btc_irt_ref, sources["TABDEAL_SPOT_SIM"].mid, 200,
                     "Synthetic BTCUSDT x USDTIRT; NOT venue-executable arbitrage"),
        )
        for c in comparisons:
            if c.outcome == "QUARANTINED":
                issues.add("DESTINATION_VENUE_REFERENCE_DRIFT")
        if risk_veto:
            issues.add("INDEPENDENT_A5_RISK_VETO")
        outcome = "QUARANTINED_NO_SIGNAL" if issues else "SYNTHETIC_CONSISTENCY_ONLY"
        payload: dict[str, object] = {
            "schema_version": "1.0", "task_id": "FIN-P24-WQ-001",
            "claim_scope": "SYNTHETIC_RESEARCH_ONLY",
            "policy_id": self.policy_id, "now_ms_fixture": now_ms,
            "outcome": outcome, "issues": sorted(issues),
            "p07_reference_ids": {"forex": fxcheck.fingerprint, "crypto": cryptocheck.fingerprint},
            "p07_reference_outcomes": {"forex": fxcheck.outcome.value, "crypto": cryptocheck.outcome.value},
            "source_count": len(sources),
            "source_ids": sorted(sources),
            "comparison": [c.payload() for c in comparisons],
            "tradingview_role": "HUMAN_VISUAL_ONLY",
            "binance_source_role": "SYNTHETIC_ARCHIVE_LABEL_NOT_API",
            "real_source_quotes_observed": 0,
            "actual_broker_fills": 0,
            "independent_source_rights_verified": False,
            "executability_certified": False,
            "order_authority": False,
            "risk_veto": risk_veto,
            "pre_first_live_satisfied": 0,
            "p24_b": "BLOCKED_HUMAN_AND_PRODUCTION_PREREQUISITES",
            "g13": "NOT_STARTED", "live_trading": "DISABLED", "auto_trading": "DISABLED",
        }
        return {**payload, "evidence_id": digest(payload)}


def render_html(result: dict[str, object]) -> str:
    rows_obj = result.get("comparison")
    if not isinstance(rows_obj, list):
        raise ReferenceLabError("comparison rows required")
    rows: list[str] = []
    for raw in cast(list[object], rows_obj):
        if not isinstance(raw, dict):
            raise ReferenceLabError("invalid report row")
        row = cast(dict[str, object], raw)
        tds = "".join(f"<td>{escape(str(row.get(key, '')))}</td>" for key in
                      ("pair", "reference_mid", "destination_mid", "drift_bps", "outcome"))
        rows.append(f"<tr>{tds}</tr>")
    issue_values = result.get("issues")
    if not isinstance(issue_values, list):
        raise ReferenceLabError("report issue list required")
    issue_text = ", ".join(str(x) for x in cast(list[object], issue_values)) or "None (synthetic only)"
    return (
        "<!doctype html><html lang='fa' dir='rtl'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>NEXUS QUANT — مقایسه چندمنبعی آزمایشی</title>"
        "<style>body{font-family:system-ui;margin:30px auto;max-width:1100px;padding:20px;"
        "background:#0d1727;color:#eef3ff}h1{font-size:26px}table{width:100%;border-collapse:collapse;"
        "direction:ltr}td,th{border-bottom:1px solid #496079;padding:12px;text-align:left}"
        "th{background:#18364c}strong{color:#ffd17c}code{font-family:monospace}</style>"
        "</head><body><h1>گزارش تطبیق منابع بازار — NEXUS QUANT</h1>"
        "<p><strong>فقط داده ساختگی؛ داده واقعی، مجوز تجاری یا نتیجه قابل معامله نیست.</strong></p>"
        "<p>Dukascopy و Binance فقط نام منبع آزمایشی‌اند. TradingView صرفاً برای بازبینی دستی است.</p>"
        f"<p>نتیجه: <code>{escape(str(result.get('outcome','')))}</code> · "
        f"خطا/هشدار: <code>{escape(issue_text)}</code></p>"
        "<table><thead><tr><th>دارایی</th><th>میانگین مرجع</th><th>قیمت مقصد ساختگی</th>"
        "<th>اختلاف (bps)</th><th>وضعیت</th></tr></thead><tbody>"
        + "".join(rows) + "</tbody></table>"
        f"<p>شناسه شواهد: <code>{escape(str(result.get('evidence_id','')))}</code></p>"
        "<p>معاملات واقعی: غیرفعال؛ G13: شروع‌نشده؛ PRE_FIRST_LIVE: ۰ از ۹.</p>"
        "</body></html>\n"
    )
