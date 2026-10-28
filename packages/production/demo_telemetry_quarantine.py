"""Offline, explicitly unverified, privacy-safe synthetic/demo telemetry reader.

No MT5 login, account IDs, authentication, APIs, orders or networks are used.
An accepted file is NOT broker-attested and NOT production certification.
"""
from __future__ import annotations

from datetime import datetime
from html import escape
import hashlib
import json
from pathlib import Path
import re
from typing import cast


class DemoQuarantineError(ValueError):
    """Fail-closed rejected telemetry or policy."""


EXPECTED_POLICY: dict[str, object] = {
    "schema_version": "1.0",
    "kind": "P24_WP_OFFLINE_DEMO_TELEMETRY_POLICY",
    "task_id": "FIN-P24-WP-001",
    "claim_scope": "SCHEMA_AND_REFERENCE_METRICS_ONLY",
    "source_kinds": ["SYNTHETIC_FIXTURE", "USER_SUPPLIED_SANITIZED_DEMO"],
    "platforms": ["FIBO_MT5_DEMO", "FIBO_CTRADER_DEMO", "TABDEAL_SPOT_MOCK"],
    "currency_units": ["USD_CENTS", "EUR_CENTS", "TOMAN"],
    "max_quote_age_ms": 1500,
    "max_observations": 10000,
    "source_account_attested": False,
    "production_broker_certified": False,
    "network_mode": "DISABLED",
    "credential_mode": "NONE",
    "external_order_submission": False,
    "live_execution_authority": False,
    "real_capital_risk_budget": None,
    "pre_first_live_satisfied": 0,
    "first_live_owner_approval": "NOT_GRANTED",
    "p24_b": "BLOCKED",
    "g13": "NOT_STARTED",
    "live_trading": "DISABLED",
    "auto_trading": "DISABLED",
}
ROOT_KEYS = frozenset({
    "schema_version", "trace_id", "source_kind", "platform",
    "environment", "currency_unit", "observations",
})
OBS_KEYS = frozenset({
    "observed_at_utc", "balance_minor", "equity_minor", "external_flow_minor",
    "open_pnl_minor", "quote_age_ms", "connected",
    "trades_closed_count", "rejected_orders_count",
})
TRACE = re.compile(r"TRACE-[0-9a-f]{16}\Z")
TIME = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\Z")


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _mapping(value: object, fields: frozenset[str]) -> dict[str, object]:
    if not isinstance(value, dict):
        raise DemoQuarantineError("object required")
    checked = cast(dict[object, object], value)
    if any(type(key) is not str for key in checked):
        raise DemoQuarantineError("invalid or potentially private field names")
    key_names: set[str] = {str(key) for key in checked}
    if key_names != set(fields):
        raise DemoQuarantineError("unknown or missing fields, potentially private data")
    return cast(dict[str, object], value)


def _typed_int(value: object, field: str, *, allow_negative: bool = False) -> int:
    if type(value) is not int:
        raise DemoQuarantineError(f"{field} must be integer")
    parsed = value
    if not allow_negative and parsed < 0:
        raise DemoQuarantineError(f"{field} must be nonnegative")
    return parsed


def _typed_str(value: object, field: str) -> str:
    if type(value) is not str or not value:
        raise DemoQuarantineError(f"{field} must be text")
    return value


class OfflineDemoTelemetry:
    def __init__(self, policy_path: Path) -> None:
        try:
            obj: object = json.loads(policy_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise DemoQuarantineError("missing or invalid immutable policy") from exc
        if canonical_bytes(obj) != canonical_bytes(EXPECTED_POLICY):
            raise DemoQuarantineError("policy drift or authority escalation")
        self.policy_id = sha(obj)

    def evaluate(self, source: object) -> dict[str, object]:
        data = _mapping(source, ROOT_KEYS)
        if data["schema_version"] != "1.0" or data["environment"] != "DEMO":
            raise DemoQuarantineError("only DEMO report schema permitted")
        trace = _typed_str(data["trace_id"], "trace_id")
        if TRACE.fullmatch(trace) is None:
            raise DemoQuarantineError("nonsecret random trace identity required")
        origin = _typed_str(data["source_kind"], "source_kind")
        platform = _typed_str(data["platform"], "platform")
        unit = _typed_str(data["currency_unit"], "currency_unit")
        if origin not in ("SYNTHETIC_FIXTURE", "USER_SUPPLIED_SANITIZED_DEMO"):
            raise DemoQuarantineError("unsupported provenance")
        if platform not in ("FIBO_MT5_DEMO", "FIBO_CTRADER_DEMO", "TABDEAL_SPOT_MOCK"):
            raise DemoQuarantineError("unsupported platform")
        if platform == "TABDEAL_SPOT_MOCK" and origin != "SYNTHETIC_FIXTURE":
            raise DemoQuarantineError("no verified Tabdeal live demo or sandbox")
        if unit not in ("USD_CENTS", "EUR_CENTS", "TOMAN"):
            raise DemoQuarantineError("unapproved account unit")
        samples_obj = data["observations"]
        if not isinstance(samples_obj, list):
            raise DemoQuarantineError("observations must be a list")
        samples = cast(list[object], samples_obj)
        if not 2 <= len(samples) <= 10000:
            raise DemoQuarantineError("insufficient or excessive samples")
        previous_time: datetime | None = None
        previous_trades = 0
        previous_rejects = 0
        initial_balance: int | None = None
        previous_peak = 0
        max_drawdown_bps = 0
        stale_count = 0
        disconnected_count = 0
        final_equity = 0
        final_external_flow = 0
        final_balance = 0
        rows: list[dict[str, object]] = []
        for pos, item in enumerate(samples):
            sample = _mapping(item, OBS_KEYS)
            stamp = _typed_str(sample["observed_at_utc"], "observed_at_utc")
            if TIME.fullmatch(stamp) is None:
                raise DemoQuarantineError("must use explicit UTC timestamp")
            try:
                moment = datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ")
            except ValueError as exc:
                raise DemoQuarantineError("invalid timestamp") from exc
            if previous_time is not None and moment <= previous_time:
                raise DemoQuarantineError("timestamps cannot replay or regress")
            previous_time = moment
            balance = _typed_int(sample["balance_minor"], "balance_minor")
            equity = _typed_int(sample["equity_minor"], "equity_minor")
            flow = _typed_int(sample["external_flow_minor"], "external_flow_minor", allow_negative=True)
            floating = _typed_int(sample["open_pnl_minor"], "open_pnl_minor", allow_negative=True)
            age = _typed_int(sample["quote_age_ms"], "quote_age_ms")
            trades = _typed_int(sample["trades_closed_count"], "trades_closed_count")
            rejects = _typed_int(sample["rejected_orders_count"], "rejected_orders_count")
            if type(sample["connected"]) is not bool:
                raise DemoQuarantineError("connected must be Boolean")
            connected = sample["connected"]
            if equity <= 0 or balance <= 0 or equity != balance + floating:
                raise DemoQuarantineError("nonpositive or inconsistent broker equity")
            if trades < previous_trades or rejects < previous_rejects:
                raise DemoQuarantineError("counter replay/regression")
            previous_trades, previous_rejects = trades, rejects
            if pos == 0:
                if flow != 0:
                    raise DemoQuarantineError("starting flow must equal zero")
                initial_balance = balance
            previous_peak = max(previous_peak, equity)
            drawdown_bps = (previous_peak - equity) * 10000 // previous_peak
            max_drawdown_bps = max(max_drawdown_bps, drawdown_bps)
            stale_count += int(age > 1500)
            disconnected_count += int(not connected)
            final_equity, final_external_flow, final_balance = equity, flow, balance
            rows.append({
                "observed_at_utc": stamp,
                "equity_minor": equity,
                "drawdown_bps": drawdown_bps,
                "quote_age_ms": age,
                "connected": connected,
            })
        if initial_balance is None:
            raise DemoQuarantineError("initial balance required")
        payload: dict[str, object] = {
            "schema_version": "1.0",
            "task_id": "FIN-P24-WP-001",
            "claim_scope": "SCHEMA_AND_REFERENCE_METRICS_ONLY",
            "policy_id": self.policy_id,
            "source_sha256": sha(data),
            "trace_id": trace,
            "source_kind": origin,
            "platform": platform,
            "currency_unit": unit,
            "number_of_samples": len(samples),
            "first_balance_minor": initial_balance,
            "final_balance_minor": final_balance,
            "final_equity_minor": final_equity,
            "external_flow_minor": final_external_flow,
            "net_pnl_minor_adjusted_for_flows": final_equity - initial_balance - final_external_flow,
            "max_drawdown_bps": max_drawdown_bps,
            "stale_quote_observations": stale_count,
            "disconnected_observations": disconnected_count,
            "closed_trades_user_reported": previous_trades,
            "rejected_orders_user_reported": previous_rejects,
            "observations": rows,
            "broker_source_attested": False,
            "broker_execution_certified": False,
            "real_profitability_validated": False,
            "live_execution_authority": False,
            "network_mode": "DISABLED",
            "pre_first_live_satisfied": 0,
            "first_live_owner_approval": "NOT_GRANTED",
            "p24_b": "BLOCKED",
            "g13": "NOT_STARTED",
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        }
        return {**payload, "report_id": sha(payload)}


def render_html(report: dict[str, object]) -> str:
    rows_obj = report.get("observations")
    if not isinstance(rows_obj, list):
        raise DemoQuarantineError("missing dashboard observations")
    rows: list[str] = []
    for raw in cast(list[object], rows_obj):
        if not isinstance(raw, dict):
            raise DemoQuarantineError("invalid dashboard row")
        item = cast(dict[str, object], raw)
        stamp = item.get("observed_at_utc")
        equity = item.get("equity_minor")
        dd = item.get("drawdown_bps")
        if type(stamp) is not str or type(equity) is not int or type(dd) is not int:
            raise DemoQuarantineError("invalid dashboard types")
        rows.append(
            f"<tr><td>{escape(stamp)}</td>"
            f"<td>{equity}</td><td>{dd}</td></tr>"
        )
    heading = "NEXUS QUANT — DEMO TELEMETRY (UNATTESTED)"
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{heading}</title>"
        "<style>body{font:15px system-ui;background:#0d1729;color:#dce7f5;max-width:950px;"
        "margin:24px auto;padding:20px}h1{font-size:24px}strong{color:#ffce70}"
        "table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid #31445d;"
        "padding:12px;text-align:left}th{background:#1a2d46}</style></head><body>"
        f"<h1>{heading}</h1>"
        "<p><strong>UNVERIFIED SANITIZED SOURCE. NO ACCOUNT ATTESTATION, NO DEMO PROFIT CERTIFICATION, NO LIVE AUTHORITY.</strong></p>"
        "<p>All metrics reflect the declared input, which may be a synthetic fixture."
        " This is not a broker statement or real investment result.</p>"
        f"<p>Platform: {escape(str(report.get('platform','')))} · "
        f"Provenance: {escape(str(report.get('source_kind','')))} · "
        f"Unit: {escape(str(report.get('currency_unit','')))}</p>"
        f"<p>Flow-adjusted net P&amp;L: {escape(str(report.get('net_pnl_minor_adjusted_for_flows', '')))} "
        f"· Maximum drawdown (bps): {escape(str(report.get('max_drawdown_bps', '')))}</p>"
        "<table><thead><tr><th>Observed UTC</th><th>Equity (minor units)</th><th>Drawdown bps</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
        f"<p>Report digest: {escape(str(report.get('report_id','')))}</p></body></html>\n"
    )
