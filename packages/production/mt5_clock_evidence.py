"""P24 Demo clock provenance: pure parser, NO broker access or time correction.

Parses only redacted, fixed-field output of P24ReadOnlyClockProbe.mq5.
Every result is an *unverified observation* and cannot enable live trading.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Final

PREFIX: Final[str] = "P24_CLOCK_V1"
KEYS: Final[tuple[str, ...]] = (
    "sample", "symbol", "tick_s", "tick_ms", "gmt_s", "local_s",
    "gmt_offset_s", "server_last_s", "server_est_s", "status",
)
INT_KEYS: Final[frozenset[str]] = frozenset(KEYS) - {"symbol", "status"}
SYMBOL_PATTERN: Final[re.Pattern[str]] = re.compile(r"[A-Za-z0-9._-]{1,20}\Z")
INTEGER_PATTERN: Final[re.Pattern[str]] = re.compile(r"-?[0-9]{1,15}\Z")


class ClockEvidenceError(ValueError):
    """Refuse noncanonical/prohibited clock evidence, no partial acceptance."""


@dataclass(frozen=True, slots=True)
class ClockSample:
    sample: int
    symbol: str
    tick_s: int
    tick_ms: int
    gmt_s: int
    local_s: int
    gmt_offset_s: int
    server_last_s: int
    server_est_s: int
    status: str


def parse_probe_line(line: str) -> ClockSample:
    if not isinstance(line, str) or not line.startswith(PREFIX + "|"):
        raise ClockEvidenceError("missing canonical clock prefix")
    if len(line) > 512 or "\n" in line or "\r" in line or "\t" in line:
        raise ClockEvidenceError("line too long or contains control characters")
    pieces = line.split("|")
    if len(pieces) != 11 or pieces[0] != PREFIX:
        raise ClockEvidenceError("exact ten-field schema required")
    fields: dict[str, str] = {}
    for piece in pieces[1:]:
        if piece.count("=") != 1:
            raise ClockEvidenceError("noncanonical key/value")
        key, val = piece.split("=", 1)
        if key not in KEYS or key in fields or not val:
            raise ClockEvidenceError("unknown/duplicate/empty field")
        fields[key] = val
    if tuple(fields) != KEYS:
        raise ClockEvidenceError("unexpected field order or omission")
    if fields["status"] != "OK" or SYMBOL_PATTERN.fullmatch(fields["symbol"]) is None:
        raise ClockEvidenceError("invalid status or symbol")
    parsed: dict[str, int] = {}
    for name in INT_KEYS:
        val = fields[name]
        if INTEGER_PATTERN.fullmatch(val) is None or (
            val.startswith("0") and len(val) > 1
        ) or val == "-0":
            raise ClockEvidenceError("invalid integer")
        parsed[name] = int(val)
    if not 1 <= parsed["sample"] <= 3:
        raise ClockEvidenceError("sample out of range")
    times = [parsed[k] for k in ("tick_s", "gmt_s", "local_s", "server_last_s", "server_est_s")]
    if any(not 1_500_000_000 <= n < 4_102_444_800 for n in times):
        raise ClockEvidenceError("timestamp not in plausible safety window")
    if not 1_500_000_000_000 <= parsed["tick_ms"] < 4_102_444_800_000:
        raise ClockEvidenceError("tick milliseconds implausible")
    if not -64_800 <= parsed["gmt_offset_s"] <= 64_800:
        raise ClockEvidenceError("GMT offset implausible")
    return ClockSample(
        parsed["sample"], fields["symbol"], parsed["tick_s"], parsed["tick_ms"],
        parsed["gmt_s"], parsed["local_s"], parsed["gmt_offset_s"],
        parsed["server_last_s"], parsed["server_est_s"], fields["status"],
    )


def canonical_hash(value: dict[str, object]) -> str:
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def review_probe_lines(lines: list[str], *, tier: str) -> dict[str, object]:
    """Review S1 pasted numeric-only probe logs; NEVER certify broker time."""
    if tier not in ("FOREX", "CRYPTO") or not 1 <= len(lines) <= 3:
        raise ClockEvidenceError("fixed tier and 1-3 samples required")
    samples = [parse_probe_line(x) for x in lines]
    if any(x.sample != i + 1 for i, x in enumerate(samples)):
        raise ClockEvidenceError("nonsequential or duplicate sample counter")
    if len({x.symbol for x in samples}) != 1:
        raise ClockEvidenceError("mixed symbols or terminals prohibited")
    if any(a.tick_ms > b.tick_ms for a, b in zip(samples, samples[1:])):
        raise ClockEvidenceError("raw tick regressed")
    observations: list[dict[str, object]] = []
    for x in samples:
        tick_delta_ms = x.tick_ms - 1000 * x.gmt_s
        # MQL5 read calls are not atomic; this is a sanity check, not UTC attestation.
        gmt_local_consistent = abs(x.gmt_s - (x.local_s + x.gmt_offset_s)) <= 5
        tick_fields_consistent = (x.tick_ms // 1000 == x.tick_s)
        observations.append({
            "sample": x.sample,
            "tick_minus_host_gmt_ms": tick_delta_ms,
            "estimated_server_minus_host_gmt_s": x.server_est_s - x.gmt_s,
            "last_marketwatch_quote_minus_host_gmt_s": x.server_last_s - x.gmt_s,
            "host_gmt_offset_s": x.gmt_offset_s,
            "host_gmt_local_consistent": gmt_local_consistent,
            "tick_seconds_milliseconds_consistent": tick_fields_consistent,
            "sanity": "INCONSISTENT" if not (gmt_local_consistent and tick_fields_consistent) else "RAW_VALUES_ONLY",
        })
    payload: dict[str, object] = {
        "schema": "P24_CLOCK_REVIEW_V1",
        "tier": tier,
        "symbol": samples[0].symbol,
        "samples": observations,
        "clock_provenance": "BROKER_NOT_ATTESTED",
        "machine_ntp_independently_verified": False,
        "read_only_mt5_compilation_and_execution_in_ci": "NOT_RUN",
        "broker_sanctioned_order_tests": "NOT_RUN",
        "operational_reconnect_drill": "NOT_RUN",
        "source_time_correction_applied": False,
        "data_freshness_certified": False,
        "live_execution_authorized": False,
        "pre_first_live_satisfied": 0,
        "p24_b": "BLOCKED_HUMAN_AND_PRODUCTION_PREREQUISITES",
        "g13": "NOT_STARTED",
        "live_trading": "DISABLED",
        "auto_trading": "DISABLED",
        "assessment": "UNVERIFIED_FAIL_CLOSED",
    }
    return {**payload, "evidence_sha256": canonical_hash(payload)}
