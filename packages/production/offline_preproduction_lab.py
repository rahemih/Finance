"""P24-WO synthetic-only failure and kill-switch reference drills.

No network, secrets, real order submission, broker SDK or real-money budgets.
This lab does not certify the production pre-Live kill switch.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from html import escape
import hashlib
import json
from pathlib import Path
from typing import cast


class OfflineLabError(ValueError):
    """Fail-closed simulation policy or event violation."""


EXPECTED_POLICY: dict[str, object] = {
    "schema_version": "1.0",
    "kind": "P24_WO_OFFLINE_PREPRODUCTION_LAB",
    "task_id": "FIN-P24-WO-001",
    "claim_scope": "SYNTHETIC_REHEARSAL_ONLY",
    "markets": ["FOREX", "CRYPTO"],
    "environment": "SIMULATED",
    "network_mode": "DISABLED",
    "credential_mode": "NONE",
    "external_order_submission": False,
    "live_execution_authority": False,
    "allowed_event_kinds": [
        "TICK", "BROKER_DISCONNECT", "ACK_UNKNOWN",
        "PARTIAL_FILL_MISMATCH", "RISK_VETO", "KILL_SWITCH",
        "RESET_REQUEST", "MARGIN_ALERT",
    ],
    "kill_scopes": ["STRATEGY", "ASSET", "MARKET", "BROKER", "GLOBAL"],
    "max_tick_age_ms": 1500,
    "max_event_sequence": 100000,
    "risk_budget_real": None,
    "production_provider_selected": False,
    "production_venue_selected": False,
    "production_broker_certified": False,
    "pre_live_kill_switch_certified": False,
    "first_live_owner_approval": "NOT_GRANTED",
    "p24_b": "BLOCKED_HUMAN_AND_PRODUCTION_PREREQUISITES",
    "g13": "NOT_STARTED",
    "live_trading": "DISABLED",
    "auto_trading": "DISABLED",
}
VALID_MARKETS = ("FOREX", "CRYPTO")
VALID_KINDS = (
    "TICK", "BROKER_DISCONNECT", "ACK_UNKNOWN",
    "PARTIAL_FILL_MISMATCH", "RISK_VETO", "KILL_SWITCH",
    "RESET_REQUEST", "MARGIN_ALERT",
)
VALID_SCOPES = ("STRATEGY", "ASSET", "MARKET", "BROKER", "GLOBAL")


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


@dataclass(frozen=True, slots=True)
class SyntheticEvent:
    scenario: str
    event_id: str
    sequence: int
    market: str
    kind: str
    age_ms: int = 0
    connected: bool = True
    risk_veto: bool = False
    reconciliation_ok: bool = True
    kill_scope: str = "NONE"
    environment: str = "SIMULATED"
    network_mode: str = "DISABLED"
    credential_mode: str = "NONE"
    external_order_submission: bool = False
    live_execution_authority: bool = False


@dataclass(frozen=True, slots=True)
class AuditDecision:
    event_id: str
    scenario: str
    market: str
    kind: str
    status: str
    reason: str
    state: str
    audit_hash: str
    external_order_authority: bool = False
    real_money_authority: bool = False

    def payload(self) -> dict[str, object]:
        return asdict(self)


class OfflinePreproductionLab:
    def __init__(self, policy_id: str) -> None:
        if policy_id != digest(EXPECTED_POLICY):
            raise OfflineLabError("unverified synthetic policy identity")
        self.policy_id = policy_id
        self.state = "ACTIVE_SIMULATION_ONLY"
        self.last_sequence = 0
        self.seen: set[str] = set()
        self.chain = "0" * 64
        self.decisions: list[AuditDecision] = []

    @classmethod
    def from_path(cls, path: Path) -> "OfflinePreproductionLab":
        try:
            parsed: object = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise OfflineLabError("invalid offline policy") from exc
        if canonical_bytes(parsed) != canonical_bytes(EXPECTED_POLICY):
            raise OfflineLabError("policy drift or unsafe escalation")
        return cls(digest(parsed))

    def accept(self, event: SyntheticEvent) -> AuditDecision:
        self._validate(event)
        if event.event_id in self.seen or event.sequence <= self.last_sequence:
            raise OfflineLabError("duplicate/replayed/out-of-order event refused")
        gap = event.sequence != self.last_sequence + 1
        self.seen.add(event.event_id)
        self.last_sequence = event.sequence

        reason = "OBSERVED_SYNTHETIC_ONLY"
        if self.state != "ACTIVE_SIMULATION_ONLY":
            reason = "LATCHED_STOP_REQUIRES_INDEPENDENT_RESET"
        elif event.risk_veto or event.kind == "RISK_VETO":
            self.state = "HALTED"
            reason = "A5_RISK_VETO"
        elif event.kind in ("KILL_SWITCH", "MARGIN_ALERT"):
            self.state = "HALTED"
            reason = "KILL_SWITCH_LATCHED" if event.kind == "KILL_SWITCH" else "MARGIN_SAFETY_HALT"
        elif gap:
            self.state = "SAFE_MODE"
            reason = "SEQUENCE_GAP"
        elif not event.connected or event.kind == "BROKER_DISCONNECT":
            self.state = "SAFE_MODE"
            reason = "BROKER_DISCONNECTED"
        elif event.kind == "TICK" and event.age_ms > 1500:
            self.state = "SAFE_MODE"
            reason = "STALE_MARKET_DATA"
        elif event.kind in ("ACK_UNKNOWN", "PARTIAL_FILL_MISMATCH") or not event.reconciliation_ok:
            self.state = "WAIT_RECONCILIATION"
            reason = "UNKNOWN_ORDER_OR_RECONCILIATION"
        elif event.kind == "RESET_REQUEST":
            reason = "NO_SELF_APPROVAL_OR_RESET_AUTHORITY"

        if self.state == "ACTIVE_SIMULATION_ONLY":
            status = "REFERENCE_OBSERVATION_ONLY"
        else:
            status = "FAIL_CLOSED_NO_ORDER"
        payload: dict[str, object] = {
            "policy_id": self.policy_id,
            "previous_chain": self.chain,
            "event": asdict(event),
            "status": status,
            "reason": reason,
            "state": self.state,
            "external_order_authority": False,
            "real_money_authority": False,
        }
        self.chain = digest(payload)
        decision = AuditDecision(
            event_id=event.event_id,
            scenario=event.scenario,
            market=event.market,
            kind=event.kind,
            status=status,
            reason=reason,
            state=self.state,
            audit_hash=self.chain,
        )
        self.decisions.append(decision)
        return decision

    @staticmethod
    def _validate(event: SyntheticEvent) -> None:
        text_values = (
            event.scenario, event.event_id, event.market, event.kind,
            event.kill_scope, event.environment, event.network_mode, event.credential_mode,
        )
        if any(type(value) is not str for value in text_values):
            raise OfflineLabError("text fields must be strings")
        if not event.scenario.strip() or not event.event_id.strip():
            raise OfflineLabError("scenario and event ID required")
        if event.event_id != event.event_id.strip() or event.scenario != event.scenario.strip():
            raise OfflineLabError("noncanonical identity")
        if event.market not in VALID_MARKETS or event.kind not in VALID_KINDS:
            raise OfflineLabError("unknown market or event kind")
        if type(event.sequence) is not int or type(event.age_ms) is not int:
            raise OfflineLabError("integer event geometry required")
        if event.sequence < 1 or event.sequence > 100000 or event.age_ms < 0:
            raise OfflineLabError("invalid sequence or age")
        for value in (
            event.connected, event.risk_veto, event.reconciliation_ok,
            event.external_order_submission, event.live_execution_authority,
        ):
            if type(value) is not bool:
                raise OfflineLabError("Boolean field type spoofing")
        if event.environment != "SIMULATED" or event.network_mode != "DISABLED":
            raise OfflineLabError("network/real environment prohibited")
        if event.credential_mode != "NONE" or event.external_order_submission or event.live_execution_authority:
            raise OfflineLabError("credentials and all external order authority prohibited")
        if event.kind == "KILL_SWITCH":
            if event.kill_scope not in VALID_SCOPES:
                raise OfflineLabError("unknown kill scope")
        elif event.kill_scope != "NONE":
            raise OfflineLabError("kill scope not allowed for this event")

    def snapshot(self) -> dict[str, object]:
        decisions = [decision.payload() for decision in self.decisions]
        payload: dict[str, object] = {
            "schema_version": "1.0",
            "task_id": "FIN-P24-WO-001",
            "claim_scope": "SYNTHETIC_REHEARSAL_ONLY",
            "policy_id": self.policy_id,
            "final_chain": self.chain,
            "final_state": self.state,
            "event_count": len(decisions),
            "fail_closed_count": sum(d.status == "FAIL_CLOSED_NO_ORDER" for d in self.decisions),
            "decisions": decisions,
            "safety": {
                "network_mode": "DISABLED",
                "credential_mode": "NONE",
                "external_orders": False,
                "live_trading": "DISABLED",
                "auto_trading": "DISABLED",
                "production_pre_live_kill_switch_certified": False,
                "p24_b": "BLOCKED_HUMAN_AND_PRODUCTION_PREREQUISITES",
                "g13": "NOT_STARTED",
            },
        }
        return {**payload, "snapshot_id": digest(payload)}


def reference_scenarios() -> tuple[tuple[str, tuple[SyntheticEvent, ...]], ...]:
    """Only synthetic reference event tapes; no broker data or financial return."""
    def e(s: str, n: int, kind: str, market: str = "FOREX", **changes: object) -> SyntheticEvent:
        from dataclasses import replace
        return replace(SyntheticEvent(s, f"{s}-{n}", n, market, kind), **changes)
    return (
        ("baseline_fx", (e("baseline_fx", 1, "TICK"), e("baseline_fx", 2, "TICK"))),
        ("baseline_spot", (e("baseline_spot", 1, "TICK", "CRYPTO"),)),
        ("stale_fx", (e("stale_fx", 1, "TICK", age_ms=1501), e("stale_fx", 2, "TICK"))),
        ("feed_disconnected", (e("feed_disconnected", 1, "BROKER_DISCONNECT"), e("feed_disconnected", 2, "TICK"))),
        ("link_flag_down", (e("link_flag_down", 1, "TICK", connected=False),)),
        ("ack_ambiguous", (e("ack_ambiguous", 1, "ACK_UNKNOWN"), e("ack_ambiguous", 2, "TICK"))),
        ("fill_mismatch", (e("fill_mismatch", 1, "PARTIAL_FILL_MISMATCH", "CRYPTO"),)),
        ("recon_flag_false", (e("recon_flag_false", 1, "TICK", reconciliation_ok=False),)),
        ("risk_veto_fx", (e("risk_veto_fx", 1, "RISK_VETO"), e("risk_veto_fx", 2, "TICK"))),
        ("risk_veto_spot", (e("risk_veto_spot", 1, "TICK", "CRYPTO", risk_veto=True),)),
        ("kill_strategy", (e("kill_strategy", 1, "KILL_SWITCH", kill_scope="STRATEGY"),)),
        ("kill_broker", (e("kill_broker", 1, "KILL_SWITCH", kill_scope="BROKER"),)),
        ("kill_global", (e("kill_global", 1, "KILL_SWITCH", kill_scope="GLOBAL"), e("kill_global", 2, "RESET_REQUEST"))),
        ("margin_alert", (e("margin_alert", 1, "MARGIN_ALERT"),)),
        ("sequence_gap", (e("sequence_gap", 1, "TICK"), e("sequence_gap", 3, "TICK"))),
        ("reset_unprivileged", (e("reset_unprivileged", 1, "RESET_REQUEST"),)),
    )


def run_reference_suite(policy_path: Path) -> dict[str, object]:
    policy = OfflinePreproductionLab.from_path(policy_path)
    traces: list[dict[str, object]] = []
    for name, events in reference_scenarios():
        lab = OfflinePreproductionLab(policy.policy_id)
        for event in events:
            lab.accept(event)
        traces.append({"scenario": name, "snapshot": lab.snapshot()})
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "task_id": "FIN-P24-WO-001",
        "claim_scope": "SYNTHETIC_REHEARSAL_ONLY",
        "policy_id": policy.policy_id,
        "scenario_count": len(traces),
        "event_count": sum(len(events) for _, events in reference_scenarios()),
        "scenarios": traces,
        "broker_demo_events_observed": 0,
        "live_events_observed": 0,
        "real_pnl_measured": False,
        "pre_live_kill_switch_certified": False,
        "owner_live_gate": "NOT_GRANTED",
        "p24_b": "BLOCKED",
        "g13": "NOT_STARTED",
        "live_trading": "DISABLED",
        "auto_trading": "DISABLED",
    }
    return {**payload, "evidence_id": digest(payload)}


def render_html(report: dict[str, object]) -> str:
    scenarios_obj = report.get("scenarios")
    if not isinstance(scenarios_obj, list):
        raise OfflineLabError("invalid report data")
    scenarios = cast(list[object], scenarios_obj)
    rows: list[str] = []
    for scenario in scenarios:
        if not isinstance(scenario, dict):
            raise OfflineLabError("invalid report entry")
        item = cast(dict[str, object], scenario)
        name = item.get("scenario")
        snapshot = item.get("snapshot")
        if not isinstance(name, str) or not isinstance(snapshot, dict):
            raise OfflineLabError("invalid report entry fields")
        snap = cast(dict[str, object], snapshot)
        state, count, digest_value = snap.get("final_state"), snap.get("event_count"), snap.get("snapshot_id")
        if not isinstance(state, str) or type(count) is not int or not isinstance(digest_value, str):
            raise OfflineLabError("invalid report data types")
        rows.append(f"<tr><td>{escape(name)}</td><td>{escape(state)}</td><td>{count}</td><td><code>{escape(digest_value[:16])}</code></td></tr>")
    title = "NEXUS QUANT — P24 OFFLINE REFERENCE DRILL"
    return (
        "<!doctype html><html lang='en'><head><meta charset='UTF-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{title}</title>"
        "<style>body{font:15px system-ui,sans-serif;max-width:1024px;margin:auto;padding:30px;"
        "background:#0a1222;color:#e2e8f0}h1{font-size:25px}p{line-height:1.6}"
        "table{border-collapse:collapse;width:100%}th,td{border-bottom:1px solid #384459;padding:12px;text-align:left}"
        "th{background:#18263c}code{font-family:monospace}strong{color:#f6c667}</style></head><body>"
        f"<h1>{title}</h1>"
        "<p><strong>SIMULATED ONLY — NOT A DEMO-BROKER CERTIFICATION; NO REAL PERFORMANCE.</strong></p>"
        "<p>Network DISABLED · Credentials NONE · External orders FALSE · Live/Auto DISABLED.</p>"
        "<p>Pre-first-Live requirements remain unsatisfied; P24-B BLOCKED; G13 NOT_STARTED.</p>"
        f"<p>Scenarios: {len(rows)} · Real broker demo events: 0 · Real P&amp;L: not measured</p>"
        "<table><thead><tr><th>Scenario</th><th>Final safety state</th><th>Events</th>"
        "<th>Snapshot digest (prefix)</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table><p>Evidence ID: <code>"
        + escape(str(report.get("evidence_id", "")))
        + "</code></p></body></html>\n"
    )
