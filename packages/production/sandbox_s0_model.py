"""P24 S0: pure deterministic, broker-disconnected state-transition rehearsal.

Only synthetic order *descriptions* live here.  No exchange/MT5/S2 transport,
credentials, actual market data, real P&L, Live/Auto or production authority.
The original P24-WO fault/kill-switch laboratory remains the baseline.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Final

from packages.production.offline_preproduction_lab import canonical_bytes, digest


class S0Violation(ValueError):
    """Refuse malformed or escalated simulation inputs without I/O."""


ROUTES: Final[dict[str, tuple[str, str]]] = {
    "FOREX": ("FX-FIXTURE", "EURUSD"),
    "CRYPTO": ("CRYPTO-FIXTURE", "BTCUSD"),
}
KINDS: Final[frozenset[str]] = frozenset({
    "TICK", "INTENT", "ACK_UNKNOWN", "ACK", "PARTIAL_FILL",
    "REJECT", "CANCEL_REQUEST", "FILL", "RECONCILE",
    "DISCONNECT", "RECONNECT", "HALT", "AUDIT_FAIL",
    "SOURCE_EXPIRED", "RESET",
})
BLOCKED: Final[str] = "FAIL_CLOSED_NO_ORDER"


@dataclass(frozen=True, slots=True)
class S0Event:
    event_id: str
    sequence: int
    kind: str
    market: str = "FOREX"
    server: str = "FX-FIXTURE"
    symbol: str = "EURUSD"
    client_key: str = "fixture-key"
    units: int = 0
    timestamp_attested: bool = True  # Fixture assumption, NOT broker attestation.
    licensed: bool = True           # Synthetic flag, NOT a real data licence.
    fresh: bool = True
    connected: bool = True
    risk_approved: bool = True       # Fixture assumption, NOT independent A5 PASS.
    fixture_gate: bool = True        # NEVER production Owner Human Gate.
    kill_active: bool = False
    audit_ok: bool = True
    environment: str = "SIMULATED"
    network_mode: str = "DISABLED"
    credential_mode: str = "NONE"
    external_order_submission: bool = False


@dataclass(frozen=True, slots=True)
class S0Decision:
    event_id: str
    kind: str
    simulation_state: str
    fixture_order_state: str
    reason: str
    audit_hash: str
    state_hash: str
    external_order_authority: bool = False
    real_money_authority: bool = False


class S0Engine:
    """Test fixture reducer: every observable order is entirely synthetic."""

    def __init__(self) -> None:
        self.mode = "OBSERVATION"
        self.last_sequence = 0
        self.seen: set[str] = set()
        self.order_states: dict[str, str] = {}
        self.quantities: dict[str, int] = {}
        self.verified_fills: dict[str, int] = {}
        self.chain = "0" * 64
        self.decisions: list[S0Decision] = []

    def _state_digest(self) -> str:
        """Authenticate synthetic internal state after each accepted fixture event."""
        return digest({
            "mode": self.mode,
            "order_states": self.order_states,
            "quantities": self.quantities,
            "verified_fills": self.verified_fills,
            "last_sequence": self.last_sequence,
            "seen": sorted(self.seen),
        })

    @staticmethod
    def _validate(e: S0Event) -> None:
        text_fields = (e.event_id, e.kind, e.market, e.server, e.symbol,
                       e.client_key, e.environment, e.network_mode, e.credential_mode)
        if any(type(x) is not str or not x or x.strip() != x for x in text_fields):
            raise S0Violation("noncanonical event input")
        if e.kind not in KINDS or e.market not in ROUTES:
            raise S0Violation("unknown event kind or market")
        if (e.server, e.symbol) != ROUTES[e.market]:
            raise S0Violation("cross-market route or terminal identity mismatch")
        if type(e.sequence) is not int or not (1 <= e.sequence <= 100000):
            raise S0Violation("invalid sequence")
        if type(e.units) is not int or not (0 <= e.units <= 100000):
            raise S0Violation("invalid synthetic unit count")
        flags = (e.timestamp_attested, e.licensed, e.fresh, e.connected,
                 e.risk_approved, e.fixture_gate, e.kill_active, e.audit_ok,
                 e.external_order_submission)
        if any(type(v) is not bool for v in flags):
            raise S0Violation("Boolean input spoofing")
        if (e.environment != "SIMULATED" or e.network_mode != "DISABLED"
                or e.credential_mode != "NONE" or e.external_order_submission):
            raise S0Violation("external or credential authority forbidden")

    def apply(self, e: S0Event) -> S0Decision:
        self._validate(e)
        if self.decisions and (
            self.chain != self.decisions[-1].audit_hash
            or self._state_digest() != self.decisions[-1].state_hash
        ):
            raise S0Violation("hash chain or fixture state tampered")
        if e.event_id in self.seen or e.sequence <= self.last_sequence:
            raise S0Violation("replay or out-of-order refused")
        gap = e.sequence != self.last_sequence + 1
        self.seen.add(e.event_id)
        self.last_sequence = e.sequence
        reason = "SYNTHETIC_OBSERVATION"
        key = e.client_key
        state = self.order_states.get(key, "NONE")

        # Hard-stops cannot be undone by any synthetic ACK, tick or reset.
        if self.mode == "HALTED":
            reason = "HALT_LATCHED_NO_SELF_RESET"
        elif not e.audit_ok or e.kind == "AUDIT_FAIL":
            self.mode, reason = "HALTED", "AUDIT_INTEGRITY_FAIL"
        elif e.kill_active or e.kind == "HALT":
            self.mode, reason = "HALTED", "SYNTHETIC_KILL_SWITCH"
        elif not e.risk_approved:
            self.mode, reason = "HALTED", "SYNTHETIC_A5_VETO"
        elif gap:
            self.mode, reason = "SAFE_MODE", "EVENT_SEQUENCE_GAP"
        elif not e.licensed or e.kind == "SOURCE_EXPIRED":
            self.mode, reason = "SAFE_MODE", "SOURCE_RIGHTS_UNVERIFIED"
        elif not e.timestamp_attested:
            self.mode, reason = "SAFE_MODE", "UNVERIFIED_TIME"
        elif not e.fresh:
            self.mode, reason = "SAFE_MODE", "STALE_QUOTE"
        elif not e.connected or e.kind == "DISCONNECT":
            self.mode, reason = "SAFE_MODE", "SYNTHETIC_LINK_DOWN"
        elif not e.fixture_gate:
            self.mode, reason = "SAFE_MODE", "SYNTHETIC_GATE_MISSING"
        elif e.kind == "INTENT":
            if self.mode != "OBSERVATION":
                reason = "LATCHED_STOP_REFUSES_NEW_INTENT"
            elif state != "NONE":
                self.mode, reason = "SAFE_MODE", "DUPLICATE_CLIENT_KEY"
            elif e.units < 1:
                self.mode, reason = "SAFE_MODE", "INVALID_SYNTHETIC_QUANTITY"
            else:
                self.order_states[key] = "SIM_INTENT_PENDING"
                self.quantities[key] = e.units
                self.verified_fills[key] = 0
                reason = "INTERNAL_FIXTURE_INTENT_ONLY"
        elif e.kind == "ACK_UNKNOWN":
            self.mode = "WAIT_RECONCILIATION"
            self.order_states[key] = "UNKNOWN_OUTCOME"
            reason = "UNKNOWN_ACK_NO_RETRY"
        elif e.kind == "ACK":
            if state in ("SIM_INTENT_PENDING", "UNKNOWN_OUTCOME"):
                self.order_states[key] = "SIM_ACKED"
                reason = "LATE_OR_NORMAL_FIXTURE_ACK"
            else:
                self.mode, reason = "SAFE_MODE", "ACK_WITHOUT_PENDING_INTENT"
        elif e.kind == "PARTIAL_FILL":
            total = self.verified_fills.get(key, 0) + e.units
            if state not in ("SIM_ACKED", "PARTIAL") or e.units < 1 or total > self.quantities.get(key, 0):
                self.mode, reason = "WAIT_RECONCILIATION", "FILL_MISMATCH"
            else:
                self.verified_fills[key] = total
                self.order_states[key] = "PARTIAL"
                reason = "VERIFIED_FIXTURE_PARTIAL_ONLY"
        elif e.kind == "REJECT":
            if state == "PARTIAL":
                self.order_states[key] = "PARTIAL_REMAINDER_REJECTED"
                reason = "REJECT_REMAINDER_KEEP_VERIFIED_FILLS"
            else:
                self.order_states[key] = "SIM_REJECTED"
                reason = "TERMINAL_FIXTURE_REJECT"
        elif e.kind == "CANCEL_REQUEST":
            if state in ("SIM_ACKED", "PARTIAL"):
                self.order_states[key] = "CANCEL_PENDING"
                self.mode, reason = "WAIT_RECONCILIATION", "CANCEL_NOT_FINAL"
            else:
                self.mode, reason = "WAIT_RECONCILIATION", "CANCEL_OUTCOME_UNKNOWN"
        elif e.kind == "FILL":
            if state == "CANCEL_PENDING":
                self.order_states[key] = "UNKNOWN_OUTCOME"
                self.mode, reason = "WAIT_RECONCILIATION", "CANCEL_FILL_RACE"
            elif state in ("SIM_ACKED", "PARTIAL") and e.units > 0:
                total = self.verified_fills.get(key, 0) + e.units
                if total == self.quantities.get(key, 0):
                    self.verified_fills[key] = total
                    self.order_states[key] = "SIM_FILLED"
                    reason = "FIXTURE_FILL_ONLY"
                else:
                    self.mode, reason = "WAIT_RECONCILIATION", "FULL_FILL_MISMATCH"
            else:
                self.mode, reason = "WAIT_RECONCILIATION", "UNKNOWN_FILL"
        elif e.kind == "RECONCILE":
            if state in ("UNKNOWN_OUTCOME", "CANCEL_PENDING", "SIM_ACKED", "PARTIAL"):
                self.order_states[key] = "FIXTURE_RECONCILED"
                reason = "FIXTURE_RECONCILED_LATCH_RETAINED"
            else:
                reason = "NO_AUTHORITATIVE_REAL_RECONCILIATION"
        elif e.kind == "RECONNECT":
            reason = "SIMULATED_RECONNECT_NOT_OPERATIONAL"
        elif e.kind == "RESET":
            reason = "INDEPENDENT_RESET_NOT_IMPLEMENTED"

        status = ("SIMULATED_INTERNAL_ONLY" if self.mode == "OBSERVATION"
                  else BLOCKED)
        payload: dict[str, object] = {
            "previous_hash": self.chain,
            "event": asdict(e),
            "simulation_state": self.mode,
            "fixture_order_state": self.order_states.get(key, "NONE"),
            "verified_fixture_units": self.verified_fills.get(key, 0),
            "reason": reason,
            "status": status,
            "external_order_authority": False,
            "real_money_authority": False,
            "state_hash": self._state_digest(),
        }
        self.chain = digest(payload)
        decision = S0Decision(
            e.event_id, e.kind, self.mode, self.order_states.get(key, "NONE"),
            reason, self.chain, self._state_digest(),
        )
        self.decisions.append(decision)
        return decision

    def snapshot(self) -> dict[str, object]:
        rows = [asdict(d) for d in self.decisions]
        payload: dict[str, object] = {
            "schema_version": "1.0",
            "task_id": "FIN-P24-WO-001-R01",
            "claim_scope": "S0_DETERMINISTIC_FIXTURE_ONLY",
            "simulation_mode": self.mode,
            "fixture_orders": dict(sorted(self.order_states.items())),
            "fixture_fills": dict(sorted(self.verified_fills.items())),
            "events": rows,
            "last_audit_hash": self.chain,
            "actual_broker_orders": 0,
            "actual_broker_connections": 0,
            "real_pnl_measured": False,
            "production_broker_certified": False,
            "production_kill_switch_certified": False,
            "pre_first_live_satisfied": 0,
            "p24_b": "BLOCKED_HUMAN_AND_PRODUCTION_PREREQUISITES",
            "g13": "NOT_STARTED",
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        }
        return {**payload, "evidence_id": digest(payload)}


def s0_reference_evidence() -> dict[str, object]:
    """Stable controlled fixtures only; never claim real broker test coverage."""
    fx = S0Engine()
    fx.apply(S0Event("t1", 1, "TICK"))
    fx.apply(S0Event("t2", 2, "INTENT", units=10))
    fx.apply(S0Event("t3", 3, "ACK_UNKNOWN"))
    fx.apply(S0Event("t4", 4, "ACK"))
    fx.apply(S0Event("t5", 5, "RECONCILE"))
    crypto = S0Engine()
    crypto.apply(S0Event("c1", 1, "TICK", market="CRYPTO", server="CRYPTO-FIXTURE", symbol="BTCUSD"))
    crypto.apply(S0Event("c2", 2, "HALT", market="CRYPTO", server="CRYPTO-FIXTURE", symbol="BTCUSD"))
    report: dict[str, object] = {
        "schema_version": "1.0",
        "task_id": "FIN-P24-WO-001-R01",
        "claim_scope": "S0_DETERMINISTIC_FIXTURE_ONLY",
        "traces": [fx.snapshot(), crypto.snapshot()],
        "broker_order_tests": "NOT_RUN",
        "s2_scenarios": {"SC-22": "NOT_RUN", "SC-23": "NOT_RUN", "SC-24": "NOT_RUN"},
        "p24_b": "BLOCKED_HUMAN_AND_PRODUCTION_PREREQUISITES",
        "pre_first_live_satisfied": 0,
        "live_trading": "DISABLED",
        "auto_trading": "DISABLED",
    }
    # canonical_bytes comes from the unchanged original WO reference lab.
    if not canonical_bytes(report):
        raise S0Violation("empty deterministic report")
    return {**report, "evidence_id": digest(report)}
