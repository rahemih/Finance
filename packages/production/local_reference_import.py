"""P24-WS offline CSV import for synthetic or UNATTESTED owner-supplied research.

No licensed-provider claims, real feed, network, credentials, signals or orders.
The reference CSV schema is intentionally narrower than raw broker statements.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from html import escape
import hashlib
import io
import json
from pathlib import Path
from typing import cast


class LocalImportError(ValueError):
    """Reject malformed CSV, unsupported provenance or unsafe authority."""


EXPECTED_POLICY: dict[str, object] = {
    "schema_version": "1.0",
    "task_id": "FIN-P24-WS-001",
    "kind": "P24_LOCAL_REFERENCE_CSV_OFFLINE_QUARANTINE",
    "claim_scope": "FILE_SCHEMA_AND_SYNTHETIC_REFERENCE_ONLY",
    "network_mode": "DISABLED",
    "credential_mode": "NONE",
    "data_license_status": "UNVERIFIED",
    "supports_owner_supplied_unattested": True,
    "accepts_real_source_as_certified": False,
    "provider_candidates": {
        "FX_REFERENCE_CANDIDATE": {"market": "FOREX", "pair": "EURUSD", "role": "REFERENCE_ONLY"},
        "CRYPTO_REFERENCE_CANDIDATE": {"market": "CRYPTO", "pair": "BTCUSDT", "role": "REFERENCE_ONLY"},
        "USDTIRT_REFERENCE_CANDIDATE": {"market": "CRYPTO", "pair": "USDTIRT", "role": "CONVERSION_REFERENCE_ONLY"},
    },
    "csv_columns": ["event_time_ms", "bid", "ask"],
    "max_records": 1000,
    "max_file_bytes": 100000,
    "max_age_ms": 2000,
    "required_rights_claim": "UNVERIFIED",
    "real_market_rights_verified": False,
    "independent_source_attested": False,
    "external_order_authority": False,
    "trading_signal_authority": False,
    "first_live_owner_approval": "NOT_GRANTED",
    "pre_first_live_satisfied": 0,
    "p24_b": "BLOCKED_HUMAN_AND_PRODUCTION_PREREQUISITES",
    "g13": "NOT_STARTED",
    "live_trading": "DISABLED",
    "auto_trading": "DISABLED",
}
SOURCE_MAP: dict[str, tuple[str, str, str]] = {
    "FX_REFERENCE_CANDIDATE": ("FOREX", "EURUSD", "REFERENCE_ONLY"),
    "CRYPTO_REFERENCE_CANDIDATE": ("CRYPTO", "BTCUSDT", "REFERENCE_ONLY"),
    "USDTIRT_REFERENCE_CANDIDATE": ("CRYPTO", "USDTIRT", "CONVERSION_REFERENCE_ONLY"),
}
COLUMNS = ("event_time_ms", "bid", "ask")


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


@dataclass(frozen=True, slots=True)
class ImportContext:
    source_id: str
    market: str
    pair: str
    role: str
    source_mode: str = "SYNTHETIC_FIXTURE"
    cadence: str = "RECENT_REFERENCE"
    rights_status: str = "UNVERIFIED"
    environment: str = "OFFLINE"
    network_mode: str = "DISABLED"
    credential_mode: str = "NONE"
    signal_authority: bool = False
    order_authority: bool = False

    def validate(self) -> None:
        for value in (self.source_id, self.market, self.pair, self.role,
                      self.source_mode, self.cadence, self.rights_status,
                      self.environment, self.network_mode, self.credential_mode):
            if type(value) is not str:
                raise LocalImportError("context must contain exact strings")
        if self.source_id not in SOURCE_MAP:
            raise LocalImportError("source not in research candidate allowlist")
        if (self.market, self.pair, self.role) != SOURCE_MAP[self.source_id]:
            raise LocalImportError("market, quote currency or source role mismatch")
        if self.source_mode not in ("SYNTHETIC_FIXTURE", "OWNER_SUPPLIED_UNATTESTED"):
            raise LocalImportError("unverified real feed cannot claim certification")
        if self.cadence not in ("RECENT_REFERENCE", "HISTORICAL_RESEARCH"):
            raise LocalImportError("unapproved data cadence")
        if (self.rights_status != "UNVERIFIED" or self.environment != "OFFLINE"
                or self.network_mode != "DISABLED" or self.credential_mode != "NONE"):
            raise LocalImportError("rights, environment or credential escalation")
        if type(self.signal_authority) is not bool or type(self.order_authority) is not bool:
            raise LocalImportError("authority flags must be exact booleans")
        if self.signal_authority or self.order_authority:
            raise LocalImportError("signals and orders always disabled")


def _price(value: str) -> Decimal:
    if not value or value != value.strip() or len(value) > 60:
        raise LocalImportError("invalid decimal field")
    try:
        result = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise LocalImportError("non-numeric quote") from exc
    if not result.is_finite() or result <= 0:
        raise LocalImportError("quote must be positive and finite")
    return result


def _timestamp(value: str) -> int:
    if not value or not value.isascii() or not value.isdecimal() or len(value) > 18:
        raise LocalImportError("noncanonical integer timestamp")
    stamp = int(value)
    if stamp < 1:
        raise LocalImportError("invalid event timestamp")
    return stamp


class LocalReferenceImport:
    def __init__(self, policy_path: Path) -> None:
        try:
            raw: object = json.loads(policy_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise LocalImportError("invalid offline import policy") from exc
        if canonical(raw) != canonical(EXPECTED_POLICY):
            raise LocalImportError("policy drift or forbidden authority")
        self.policy_id = sha(raw)

    def parse(self, raw: bytes, context: ImportContext, *, now_ms: int) -> dict[str, object]:
        if self.policy_id != sha(EXPECTED_POLICY):
            raise LocalImportError("runtime reference-policy identity changed")
        if not isinstance(context, ImportContext):
            raise LocalImportError("typed source context required")
        context.validate()
        if type(now_ms) is not int or now_ms < 1:
            raise LocalImportError("invalid evaluation clock")
        if type(raw) is not bytes or len(raw) > 100000 or not raw:
            raise LocalImportError("CSV must be bounded nonempty bytes")
        if b"\x00" in raw:
            raise LocalImportError("binary content not permitted")
        try:
            decoded = raw.decode("utf-8")
        except UnicodeError as exc:
            raise LocalImportError("CSV must be valid UTF-8") from exc
        if decoded.startswith("\ufeff"):
            raise LocalImportError("hidden BOM header not permitted")
        reader = csv.DictReader(io.StringIO(decoded, newline=""), strict=True)
        if reader.fieldnames != list(COLUMNS):
            raise LocalImportError("exact CSV fields required, no account or secret data")
        samples: list[dict[str, object]] = []
        previous = 0
        try:
            for row in reader:
                if len(samples) >= 1000:
                    raise LocalImportError("too many CSV observations")
                if set(row) != set(COLUMNS) or any(v is None for v in row.values()):
                    raise LocalImportError("extra, missing or malformed CSV columns")
                item = cast(dict[str, str], row)
                t = _timestamp(item["event_time_ms"])
                bid, ask = _price(item["bid"]), _price(item["ask"])
                if ask < bid:
                    raise LocalImportError("crossed bid ask values")
                if t <= previous or t > now_ms:
                    raise LocalImportError("timestamps must be increasing and not future")
                if context.cadence == "RECENT_REFERENCE" and now_ms - t > 2000:
                    raise LocalImportError("stale current-reference data")
                previous = t
                samples.append({
                    "event_time_ms": t,
                    "bid": str(bid),
                    "ask": str(ask),
                    "mid": str((bid + ask) / 2),
                })
        except csv.Error as exc:
            raise LocalImportError("invalid CSV quoting") from exc
        if not samples:
            raise LocalImportError("at least one valid observation required")
        payload: dict[str, object] = {
            "schema_version": "1.0",
            "task_id": "FIN-P24-WS-001",
            "policy_id": self.policy_id,
            "claim_scope": "FILE_SCHEMA_AND_SYNTHETIC_REFERENCE_ONLY",
            "raw_sha256": hashlib.sha256(raw).hexdigest(),
            "context": {
                "source_id": context.source_id,
                "market": context.market,
                "pair": context.pair,
                "role": context.role,
                "source_mode": context.source_mode,
                "cadence": context.cadence,
                "rights_status": "UNVERIFIED",
            },
            "sample_count": len(samples),
            "samples": samples,
            "source_licensed": False,
            "origin_independent_attested": False,
            "broker_quote_certified": False,
            "downstream_signal_allowed": False,
            "tradeable_price": False,
            "result": (
                "SYNTHETIC_REFERENCE_ONLY"
                if context.source_mode == "SYNTHETIC_FIXTURE"
                else "QUARANTINED_UNATTESTED_SOURCE"
            ),
            "external_order_authority": False,
            "pre_first_live_satisfied": 0,
            "p24_b": "BLOCKED_HUMAN_AND_PRODUCTION_PREREQUISITES",
            "g13": "NOT_STARTED",
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        }
        return {**payload, "evidence_id": sha(payload)}


def render_html(report: dict[str, object]) -> str:
    rows_obj = report.get("samples")
    if not isinstance(rows_obj, list):
        raise LocalImportError("invalid evidence samples")
    rows: list[str] = []
    for obj in cast(list[object], rows_obj):
        if not isinstance(obj, dict):
            raise LocalImportError("invalid evidence sample")
        item = cast(dict[str, object], obj)
        rows.append("<tr>" + "".join(
            f"<td>{escape(str(item.get(key, '')))}</td>"
            for key in ("event_time_ms", "bid", "ask", "mid")
        ) + "</tr>")
    return (
        "<!doctype html><html lang='fa' dir='rtl'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>واردسازی تحقیقاتی آفلاین — NEXUS QUANT</title>"
        "<style>body{font:15px system-ui;background:#0f1c31;color:#f0f4ff;"
        "max-width:1024px;margin:24px auto;padding:24px}table{width:100%;"
        "border-collapse:collapse;direction:ltr}th,td{border-bottom:1px solid #48566b;"
        "padding:12px;text-align:left}strong{color:#ffcf75}</style>"
        "</head><body><h1>آزمایش واردسازی داده بازار — Finance</h1>"
        "<p><strong>فقط تحقیق آفلاین؛ حقوق داده و منشأ مستقل تأیید نشده‌اند. "
        "هیچ سیگنال یا سفارش واقعی مجاز نیست.</strong></p>"
        f"<p>نتیجه: {escape(str(report.get('result','')))}"
        f" · منبع: {escape(str(cast(dict[str, object], report.get('context', {})).get('source_id','')))}</p>"
        "<table><thead><tr><th>زمان میلی‌ثانیه</th><th>Bid</th><th>Ask</th><th>Mid</th></tr></thead><tbody>"
        + "".join(rows) + "</tbody></table>"
        f"<p>شناسه: {escape(str(report.get('evidence_id','')))}</p>"
        "<p>G13 شروع‌نشده؛ Live/Auto غیرفعال.</p></body></html>\n"
    )
