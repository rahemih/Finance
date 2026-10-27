from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import cast


class InformationArchitectureError(ValueError):
    """P23-A information-architecture invariant failure."""


EXPECTED_SURFACES = (
    "dashboard",
    "markets",
    "opportunities",
    "trades",
    "portfolio",
    "demo",
    "research",
    "reports",
    "system",
    "settings",
    "glossary",
)

EXPECTED_CRITICAL_STATES = (
    "LOADING",
    "EMPTY",
    "ERROR",
    "OFFLINE",
    "STALE",
    "DEGRADED",
)

EXPECTED_WORKFLOWS = (
    "monitor_market",
    "evaluate_opportunity",
    "review_trade_and_portfolio",
    "monitor_demo_learning",
    "investigate_system_state",
    "learn_explanation",
    "review_settings_and_security_context",
)


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _object(value: object, *, field: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise InformationArchitectureError(f"{field} must be an object")
    raw = cast(dict[object, object], value)
    result: dict[str, object] = {}
    for key, item in raw.items():
        if not isinstance(key, str):
            raise InformationArchitectureError(f"{field} keys must be strings")
        result[key] = item
    return result


def _list(value: object, *, field: str) -> list[object]:
    if not isinstance(value, list):
        raise InformationArchitectureError(f"{field} must be a list")
    return cast(list[object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InformationArchitectureError(f"{field} must be non-empty text")
    return value


@dataclass(frozen=True, slots=True)
class Surface:
    surface_id: str
    route: str
    label_fa: str
    critical: bool


@dataclass(frozen=True, slots=True)
class Workflow:
    workflow_id: str
    surfaces: tuple[str, ...]
    authority: str


@dataclass(frozen=True, slots=True)
class InformationArchitecture:
    locale: str
    direction: str
    financial_identifier_direction: str
    surfaces: tuple[Surface, ...]
    critical_surface_states: tuple[str, ...]
    workflows: tuple[Workflow, ...]
    provenance_requirements: dict[str, bool]
    safety: dict[str, object]

    @classmethod
    def from_path(cls, path: Path) -> "InformationArchitecture":
        try:
            raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise InformationArchitectureError(f"invalid P23-A JSON: {exc}") from exc
        raw = _object(raw_value, field="root")

        expected_static: dict[str, object] = {
            "schema_version": "1.0",
            "kind": "NEXUS_QUANT_P23A_INFORMATION_ARCHITECTURE",
            "task_id": "FIN-P23-WA-001",
            "phase": "P23",
            "workstream": "P23-A",
            "locale": "fa-IR",
            "direction": "RTL",
            "financial_identifier_direction": "LTR",
        }
        for key, expected in expected_static.items():
            if raw.get(key) != expected:
                raise InformationArchitectureError(f"P23-A policy mismatch: {key}")

        surfaces_raw = _list(raw.get("surfaces"), field="surfaces")
        surfaces: list[Surface] = []
        for index, value in enumerate(surfaces_raw):
            item = _object(value, field=f"surfaces[{index}]")
            critical = item.get("critical")
            if not isinstance(critical, bool):
                raise InformationArchitectureError(
                    f"surfaces[{index}].critical must be boolean"
                )
            surface = Surface(
                surface_id=_text(item.get("id"), field=f"surfaces[{index}].id"),
                route=_text(item.get("route"), field=f"surfaces[{index}].route"),
                label_fa=_text(
                    item.get("label_fa"), field=f"surfaces[{index}].label_fa"
                ),
                critical=critical,
            )
            surfaces.append(surface)

        surface_ids = tuple(item.surface_id for item in surfaces)
        if surface_ids != EXPECTED_SURFACES:
            raise InformationArchitectureError(
                "surfaces must exactly cover the canonical P23 core surfaces in order"
            )
        routes = tuple(item.route for item in surfaces)
        if len(set(routes)) != len(routes):
            raise InformationArchitectureError("surface routes must be unique")
        if any(
            not route.startswith("/")
            or route == "/"
            or ":" in route
            or "*" in route
            for route in routes
        ):
            raise InformationArchitectureError(
                "surface routes must be static absolute application routes"
            )

        states = tuple(
            _text(value, field="critical_surface_states[]")
            for value in _list(
                raw.get("critical_surface_states"),
                field="critical_surface_states",
            )
        )
        if states != EXPECTED_CRITICAL_STATES:
            raise InformationArchitectureError(
                "critical surface states must match the canonical fail-visible set"
            )

        workflows_raw = _list(raw.get("workflows"), field="workflows")
        workflows: list[Workflow] = []
        known = set(surface_ids)
        for index, value in enumerate(workflows_raw):
            item = _object(value, field=f"workflows[{index}]")
            workflow_id = _text(
                item.get("id"), field=f"workflows[{index}].id"
            )
            workflow_surfaces = tuple(
                _text(v, field=f"workflows[{index}].surfaces[]")
                for v in _list(
                    item.get("surfaces"),
                    field=f"workflows[{index}].surfaces",
                )
            )
            if len(workflow_surfaces) < 2:
                raise InformationArchitectureError(
                    f"workflow {workflow_id} must span at least two surfaces"
                )
            unknown = [value for value in workflow_surfaces if value not in known]
            if unknown:
                raise InformationArchitectureError(
                    f"workflow {workflow_id} references unknown surfaces: {unknown}"
                )
            if any(
                left == right
                for left, right in zip(
                    workflow_surfaces,
                    workflow_surfaces[1:],
                    strict=False,
                )
            ):
                raise InformationArchitectureError(
                    f"workflow {workflow_id} has adjacent duplicate surfaces"
                )
            authority = _text(
                item.get("authority"),
                field=f"workflows[{index}].authority",
            )
            if authority != "NAVIGATION_ONLY":
                raise InformationArchitectureError(
                    f"workflow {workflow_id} cannot grant action authority"
                )
            workflows.append(
                Workflow(
                    workflow_id=workflow_id,
                    surfaces=workflow_surfaces,
                    authority=authority,
                )
            )

        workflow_ids = tuple(item.workflow_id for item in workflows)
        if workflow_ids != EXPECTED_WORKFLOWS:
            raise InformationArchitectureError(
                "workflows must exactly cover the canonical P23-A flows in order"
            )

        provenance_raw = _object(
            raw.get("provenance_requirements"),
            field="provenance_requirements",
        )
        required_provenance = {
            "sensitive_analytics_show_source",
            "sensitive_analytics_show_timestamp",
            "realtime_surfaces_show_freshness",
            "system_state_visible_on_critical_surfaces",
        }
        if set(provenance_raw) != required_provenance:
            raise InformationArchitectureError(
                "provenance requirements do not match P23-A contract"
            )
        provenance: dict[str, bool] = {}
        for key in sorted(provenance_raw):
            value = provenance_raw[key]
            if value is not True:
                raise InformationArchitectureError(
                    f"provenance requirement must be true: {key}"
                )
            provenance[key] = True

        safety = _object(raw.get("safety"), field="safety")
        expected_safety: dict[str, object] = {
            "external_order_authority": False,
            "runtime_state_mutation": False,
            "remediation_authority": False,
            "credential_access": False,
            "production_activation": False,
            "p24_state": "NOT_STARTED",
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        }
        if safety != expected_safety:
            raise InformationArchitectureError("P23-A safety boundary drift")

        return cls(
            locale="fa-IR",
            direction="RTL",
            financial_identifier_direction="LTR",
            surfaces=tuple(surfaces),
            critical_surface_states=states,
            workflows=tuple(workflows),
            provenance_requirements=provenance,
            safety=safety,
        )

    @property
    def architecture_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()

    def payload(self) -> dict[str, object]:
        return {
            "locale": self.locale,
            "direction": self.direction,
            "financial_identifier_direction": self.financial_identifier_direction,
            "surfaces": [
                {
                    "id": item.surface_id,
                    "route": item.route,
                    "label_fa": item.label_fa,
                    "critical": item.critical,
                }
                for item in self.surfaces
            ],
            "critical_surface_states": list(self.critical_surface_states),
            "workflows": [
                {
                    "id": item.workflow_id,
                    "surfaces": list(item.surfaces),
                    "authority": item.authority,
                }
                for item in self.workflows
            ],
            "provenance_requirements": self.provenance_requirements,
            "safety": self.safety,
        }
