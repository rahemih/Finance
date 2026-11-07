"""P24-C preparatory S0 ONLY: pure, deterministic semi-auto approval model.

No execution adapter, network, clock, credentials, broker or order API.
A positive fixture verdict NEVER confers real Demo or Live order authority.
"""
from __future__ import annotations

from dataclasses import dataclass, fields
from hashlib import sha256
import json
import re


@dataclass(frozen=True)
class SyntheticIntent:
    intent_id: str
    revision: int
    venue_tag: str
    strategy_tag: str
    symbol: str
    side: str
    quantity_units: int

    def digest(self) -> str:
        payload = {
            "intent_id": self.intent_id,
            "revision": self.revision,
            "venue_tag": self.venue_tag,
            "strategy_tag": self.strategy_tag,
            "symbol": self.symbol,
            "side": self.side,
            "quantity_units": self.quantity_units,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return sha256(canonical.encode("ascii")).hexdigest()


@dataclass(frozen=True)
class SyntheticApproval:
    owner_confirmed: bool = False  # Fixture, NEVER authenticated real Owner consent
    bound_intent_digest: str = ""
    bound_revision: int = 0
    acknowledgement_id: str = ""
    expires_at_tick: int = 0


@dataclass(frozen=True)
class SyntheticControls:
    p24_b_canonical_complete: bool = False
    first_live_owner_gate_granted: bool = False
    risk_budget_attested: bool = False
    provider_and_data_rights_attested: bool = False
    time_origin_attested: bool = False
    quote_freshness_attested: bool = False
    a5_independent_veto_passed: bool = False
    a8_security_passed: bool = False
    a10_evidence_verified: bool = False
    kill_switch_clear: bool = False
    ack_state_known: bool = False
    reconciliation_complete: bool = False


@dataclass(frozen=True)
class S0Verdict:
    state: str
    reasons: tuple[str, ...]
    external_order_authority: bool = False
    next_action: str = "NO_ORDER"
    operational_demo_certified: bool = False
    p24_c_stage_activated: bool = False
    live_trading_enabled: bool = False
    auto_trading_enabled: bool = False


def evaluate_s0(
    intent: SyntheticIntent,
    approval: SyntheticApproval,
    controls: SyntheticControls,
    *,
    now_tick: int,
    consumed_acknowledgements: frozenset[str] = frozenset(),
) -> S0Verdict:
    """Evaluate **synthetic** proposed human confirmation. No external side effects."""
    blockers: list[str] = []

    if not isinstance(intent, SyntheticIntent) or not isinstance(approval, SyntheticApproval) or not isinstance(controls, SyntheticControls):
        return S0Verdict("S0_BLOCKED", ("INVALID_SCHEMA",))
    if type(now_tick) is not int or now_tick < 0:
        blockers.append("INVALID_SYNTHETIC_TIME")
    if not isinstance(consumed_acknowledgements, frozenset) or any(type(x) is not str for x in consumed_acknowledgements):
        blockers.append("INVALID_REPLAY_REGISTER")
    if not isinstance(intent.intent_id, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,64}", intent.intent_id):
        blockers.append("INVALID_INTENT_ID")
    if type(intent.revision) is not int or intent.revision < 1:
        blockers.append("INVALID_REVISION")
    for name in ("venue_tag", "strategy_tag", "symbol"):
        value = getattr(intent, name)
        if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,32}", value):
            blockers.append("INVALID_" + name.upper())
    if intent.side not in ("BUY", "SELL") or type(intent.side) is not str:
        blockers.append("INVALID_SIDE")
    if type(intent.quantity_units) is not int or intent.quantity_units <= 0:
        blockers.append("INVALID_QUANTITY")
    for field in fields(controls):
        if type(getattr(controls, field.name)) is not bool:
            blockers.append("INVALID_FLAG_" + field.name.upper())
        elif not getattr(controls, field.name):
            blockers.append("MISSING_" + field.name.upper())
    if type(approval.owner_confirmed) is not bool or not approval.owner_confirmed:
        blockers.append("OWNER_FIXTURE_ACK_MISSING")
    if not isinstance(approval.acknowledgement_id, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,64}", approval.acknowledgement_id):
        blockers.append("INVALID_ACK_ID")
    elif isinstance(consumed_acknowledgements, frozenset) and approval.acknowledgement_id in consumed_acknowledgements:
        blockers.append("REPLAYED_ACK")
    if type(approval.bound_revision) is not int or approval.bound_revision != intent.revision:
        blockers.append("ACK_REVISION_MISMATCH")
    if type(approval.bound_intent_digest) is not str or approval.bound_intent_digest != intent.digest():
        blockers.append("ACK_INTENT_MISMATCH")
    if type(approval.expires_at_tick) is not int or (
        type(now_tick) is int and not (now_tick < approval.expires_at_tick <= now_tick + 60)
    ):
        blockers.append("ACK_EXPIRED_OR_UNBOUNDED")
    return S0Verdict(
        "S0_BLOCKED" if blockers else "S0_FIXTURE_ELIGIBLE",
        tuple(blockers),
    )
