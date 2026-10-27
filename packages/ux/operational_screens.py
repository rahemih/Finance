from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import cast

from packages.ux.design_system import DesignSystem
from packages.ux.information_architecture import InformationArchitecture


class OperationalScreensError(ValueError):
    """P23-C operational-screen invariant failure."""


EXPECTED_SHELLS = ("default", "monitoring", "analysis")
EXPECTED_COMPONENT_FAMILIES = (
    "NexusAppShell",
    "MetricCard",
    "RiskBadge",
    "MarketStatusBadge",
    "EmptyState",
    "DegradedState",
    "StaleDataBanner",
)
EXPECTED_RESERVED_OWNERS = {
    "learning_mode": "P23-D",
    "team_collaboration": "P23-E",
    "notification_delivery": "P23-F",
    "accessibility_performance_hardening": "P23-G",
    "dangerous_action_security_ux": "P23-H",
}


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _object(value: object, *, field: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise OperationalScreensError(f"{field} must be an object")
    raw = cast(dict[object, object], value)
    result: dict[str, object] = {}
    for key, item in raw.items():
        if not isinstance(key, str):
            raise OperationalScreensError(f"{field} keys must be strings")
        result[key] = item
    return result


def _list(value: object, *, field: str) -> list[object]:
    if not isinstance(value, list):
        raise OperationalScreensError(f"{field} must be a list")
    return cast(list[object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise OperationalScreensError(f"{field} must be non-empty text")
    return value


@dataclass(frozen=True, slots=True)
class Screen:
    screen_id: str
    route: str
    label_fa: str
    shell: str
    critical: bool
    sections: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class OperationalScreens:
    screens: tuple[Screen, ...]
    critical_states: tuple[str, ...]
    allowed_component_families: tuple[str, ...]
    reserved_behavior_owners: dict[str, str]
    provenance: dict[str, bool]
    directionality: dict[str, object]
    safety: dict[str, object]
    architecture_id: str
    design_system_id: str

    @classmethod
    def from_paths(
        cls,
        policy_path: Path,
        information_architecture_path: Path,
        design_system_path: Path,
    ) -> "OperationalScreens":
        try:
            raw_value: object = json.loads(policy_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise OperationalScreensError(f"invalid P23-C JSON: {exc}") from exc
        raw = _object(raw_value, field="root")
        expected_static: dict[str, object] = {
            "schema_version": "1.0",
            "kind": "NEXUS_QUANT_P23C_OPERATIONAL_SCREENS",
            "task_id": "FIN-P23-WC-001",
            "phase": "P23",
            "workstream": "P23-C",
            "authority": "READ_ONLY_NAVIGATION",
        }
        for key, expected in expected_static.items():
            if raw.get(key) != expected:
                raise OperationalScreensError(f"P23-C policy mismatch: {key}")

        ia = InformationArchitecture.from_path(information_architecture_path)
        design = DesignSystem.from_path(design_system_path)

        upstream = _object(raw.get("upstream"), field="upstream")
        if upstream != {
            "information_architecture": "config/ux/information-architecture.json",
            "design_system": "config/ux/design-system.json",
        }:
            raise OperationalScreensError("upstream binding drift")

        reserved_raw = _object(
            raw.get("reserved_behavior_owners"), field="reserved_behavior_owners"
        )
        reserved = {key: _text(value, field=f"reserved.{key}") for key, value in reserved_raw.items()}
        if reserved != EXPECTED_RESERVED_OWNERS:
            raise OperationalScreensError("reserved downstream behavior ownership drift")

        screens_raw = _list(raw.get("screens"), field="screens")
        screens: list[Screen] = []
        if len(screens_raw) != len(ia.surfaces):
            raise OperationalScreensError("screen coverage must match canonical P23-A surfaces")
        for index, (screen_value, surface) in enumerate(
            zip(screens_raw, ia.surfaces, strict=True)
        ):
            item = _object(screen_value, field=f"screens[{index}]")
            critical = item.get("critical")
            if not isinstance(critical, bool):
                raise OperationalScreensError(f"screens[{index}].critical must be boolean")
            sections = tuple(
                _text(value, field=f"screens[{index}].sections[]")
                for value in _list(item.get("sections"), field=f"screens[{index}].sections")
            )
            if not sections or len(set(sections)) != len(sections):
                raise OperationalScreensError(f"screen {surface.surface_id} sections must be unique")
            screen = Screen(
                screen_id=_text(item.get("id"), field=f"screens[{index}].id"),
                route=_text(item.get("route"), field=f"screens[{index}].route"),
                label_fa=_text(item.get("label_fa"), field=f"screens[{index}].label_fa"),
                shell=_text(item.get("shell"), field=f"screens[{index}].shell"),
                critical=critical,
                sections=sections,
            )
            if (
                screen.screen_id != surface.surface_id
                or screen.route != surface.route
                or screen.label_fa != surface.label_fa
                or screen.critical != surface.critical
            ):
                raise OperationalScreensError(
                    f"screen {index} must exactly bind canonical P23-A surface"
                )
            if screen.shell not in EXPECTED_SHELLS:
                raise OperationalScreensError(f"unknown shell variant: {screen.shell}")
            screens.append(screen)

        states = tuple(
            _text(value, field="critical_states[]")
            for value in _list(raw.get("critical_states"), field="critical_states")
        )
        if states != ia.critical_surface_states:
            raise OperationalScreensError("critical state contract drift")

        provenance_raw = _object(raw.get("provenance"), field="provenance")
        provenance: dict[str, bool] = {}
        if set(provenance_raw) != set(ia.provenance_requirements):
            raise OperationalScreensError("provenance key coverage drift")
        for key, expected in ia.provenance_requirements.items():
            if provenance_raw.get(key) is not expected or expected is not True:
                raise OperationalScreensError(f"provenance requirement weakened: {key}")
            provenance[key] = True

        directionality = _object(raw.get("directionality"), field="directionality")
        if directionality != {
            "shell": "RTL",
            "financial_islands": "LTR",
            "bidi_isolation_required": True,
        }:
            raise OperationalScreensError("directionality contract drift")
        if design.shell_direction != "RTL" or design.financial_island_direction != "LTR":
            raise OperationalScreensError("P23-B directionality mismatch")

        component_families = tuple(
            _text(value, field="allowed_component_families[]")
            for value in _list(
                raw.get("allowed_component_families"),
                field="allowed_component_families",
            )
        )
        if component_families != EXPECTED_COMPONENT_FAMILIES:
            raise OperationalScreensError("component-family contract drift")

        figma = _object(raw.get("figma"), field="figma")
        if figma.get("file_key") != "5aVGC189GMrRDokrjBbI5P":
            raise OperationalScreensError("Figma file binding drift")
        if not _text(figma.get("node_id"), field="figma.node_id"):
            raise OperationalScreensError("Figma node binding required")

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
            raise OperationalScreensError("P23-C safety boundary drift")

        return cls(
            screens=tuple(screens),
            critical_states=states,
            allowed_component_families=component_families,
            reserved_behavior_owners=reserved,
            provenance=provenance,
            directionality=directionality,
            safety=safety,
            architecture_id=ia.architecture_id,
            design_system_id=design.design_system_id,
        )

    @property
    def operational_screens_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()

    def payload(self) -> dict[str, object]:
        return {
            "screens": [
                {
                    "id": item.screen_id,
                    "route": item.route,
                    "label_fa": item.label_fa,
                    "shell": item.shell,
                    "critical": item.critical,
                    "sections": list(item.sections),
                }
                for item in self.screens
            ],
            "critical_states": list(self.critical_states),
            "allowed_component_families": list(self.allowed_component_families),
            "reserved_behavior_owners": self.reserved_behavior_owners,
            "provenance": self.provenance,
            "directionality": self.directionality,
            "safety": self.safety,
            "architecture_id": self.architecture_id,
            "design_system_id": self.design_system_id,
        }
