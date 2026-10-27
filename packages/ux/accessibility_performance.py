from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import cast


class AccessibilityPerformanceError(ValueError):
    """P23-G reference frontend-hardening invariant failure."""


EXPECTED_PROFILE_IDS = ("mobile", "tablet", "desktop", "wide")
EXPECTED_PROFILE_WIDTHS = (360, 768, 1024, 1440)
EXPECTED_SCREEN_IDS = (
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


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _object(value: object, *, field: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise AccessibilityPerformanceError(f"{field} must be an object")
    raw = cast(dict[object, object], value)
    result: dict[str, object] = {}
    for key, item in raw.items():
        if not isinstance(key, str):
            raise AccessibilityPerformanceError(f"{field} keys must be strings")
        result[key] = item
    return result


def _list(value: object, *, field: str) -> list[object]:
    if not isinstance(value, list):
        raise AccessibilityPerformanceError(f"{field} must be a list")
    return cast(list[object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AccessibilityPerformanceError(f"{field} must be non-empty text")
    return value


def _number(value: object, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AccessibilityPerformanceError(f"{field} must be numeric")
    return float(value)


@dataclass(frozen=True, slots=True)
class FrontendHardeningPolicy:
    profile_ids: tuple[str, ...]
    profile_widths: tuple[int, ...]
    screen_ids: tuple[str, ...]
    accessibility: dict[str, object]
    performance: dict[str, object]
    safety: dict[str, object]

    @classmethod
    def from_paths(
        cls,
        policy_path: Path,
        design_system_path: Path,
        operational_screens_path: Path,
    ) -> "FrontendHardeningPolicy":
        try:
            raw_value: object = json.loads(policy_path.read_text(encoding="utf-8"))
            design_value: object = json.loads(design_system_path.read_text(encoding="utf-8"))
            screens_value: object = json.loads(
                operational_screens_path.read_text(encoding="utf-8")
            )
        except Exception as exc:
            raise AccessibilityPerformanceError(f"invalid P23-G JSON: {exc}") from exc

        raw = _object(raw_value, field="root")
        design = _object(design_value, field="design_system")
        screens = _object(screens_value, field="operational_screens")

        expected_static: dict[str, object] = {
            "schema_version": "1.0",
            "kind": "NEXUS_QUANT_P23G_ACCESSIBILITY_RESPONSIVE_PERFORMANCE",
            "task_id": "FIN-P23-WG-001",
            "phase": "P23",
            "workstream": "P23-G",
            "claim_scope": "REFERENCE_FRONTEND_VALIDATION",
        }
        for key, expected in expected_static.items():
            if raw.get(key) != expected:
                raise AccessibilityPerformanceError(f"P23-G policy mismatch: {key}")

        upstream = _object(raw.get("upstream"), field="upstream")
        if upstream != {
            "design_system": "config/ux/design-system.json",
            "operational_screens": "config/ux/operational-screens.json",
            "frontend_baseline": "docs/03-research/FRONTEND-EXCELLENCE-BASELINE.md",
        }:
            raise AccessibilityPerformanceError("upstream binding drift")

        accessibility = _object(raw.get("accessibility"), field="accessibility")
        expected_accessibility: dict[str, object] = {
            "standard": "WCAG_2_2_AA",
            "minimum_normal_text_contrast": 4.5,
            "minimum_large_text_contrast": 3.0,
            "minimum_touch_target_px": 44,
            "visible_focus_required": True,
            "reduced_motion_required": True,
            "color_only_state_forbidden": True,
            "keyboard_operability_required": True,
            "semantic_labels_required": True,
            "critical_table_chart_alternative_required": True,
        }
        if accessibility != expected_accessibility:
            raise AccessibilityPerformanceError("accessibility contract drift")

        design_access = _object(design.get("accessibility"), field="design.accessibility")
        for key in (
            "minimum_normal_text_contrast",
            "minimum_large_text_contrast",
            "minimum_touch_target_px",
            "visible_focus_required",
            "reduced_motion_required",
            "color_only_state_forbidden",
        ):
            if design_access.get(key) != accessibility.get(key):
                raise AccessibilityPerformanceError(f"P23-B accessibility mismatch: {key}")

        responsive = _object(raw.get("responsive"), field="responsive")
        profiles_raw = _list(responsive.get("profiles"), field="responsive.profiles")
        profile_ids: list[str] = []
        profile_widths: list[int] = []
        for index, profile_value in enumerate(profiles_raw):
            profile = _object(profile_value, field=f"responsive.profiles[{index}]")
            profile_ids.append(_text(profile.get("id"), field=f"profiles[{index}].id"))
            width = profile.get("width_px")
            if isinstance(width, bool) or not isinstance(width, int):
                raise AccessibilityPerformanceError("profile width must be integer")
            profile_widths.append(width)
        if tuple(profile_ids) != EXPECTED_PROFILE_IDS:
            raise AccessibilityPerformanceError("responsive profile order/coverage drift")
        if tuple(profile_widths) != EXPECTED_PROFILE_WIDTHS:
            raise AccessibilityPerformanceError("responsive profile width drift")

        for flag in (
            "critical_content_clipping_forbidden",
            "dense_table_horizontal_scroll_explicit",
            "rtl_shell_preserved",
            "ltr_financial_islands_preserved",
        ):
            if responsive.get(flag) is not True:
                raise AccessibilityPerformanceError(f"responsive requirement weakened: {flag}")

        screen_values = _list(screens.get("screens"), field="operational_screens.screens")
        screen_ids: list[str] = []
        for index, value in enumerate(screen_values):
            screen = _object(value, field=f"screens[{index}]")
            screen_ids.append(_text(screen.get("id"), field=f"screens[{index}].id"))
        if tuple(screen_ids) != EXPECTED_SCREEN_IDS:
            raise AccessibilityPerformanceError("canonical screen coverage drift")
        if responsive.get("canonical_screen_count") != len(EXPECTED_SCREEN_IDS):
            raise AccessibilityPerformanceError("canonical screen count drift")

        directionality = _object(screens.get("directionality"), field="screens.directionality")
        if directionality.get("shell") != "RTL" or directionality.get("financial_islands") != "LTR":
            raise AccessibilityPerformanceError("directionality upstream drift")

        performance = _object(raw.get("performance"), field="performance")
        if performance.get("measurement_scope") != "REFERENCE_BUDGET_ONLY":
            raise AccessibilityPerformanceError("performance scope drift")
        if _number(performance.get("lcp_ms_max"), field="performance.lcp_ms_max") != 2500.0:
            raise AccessibilityPerformanceError("LCP reference budget drift")
        if _number(performance.get("inp_ms_max"), field="performance.inp_ms_max") != 200.0:
            raise AccessibilityPerformanceError("INP reference budget drift")
        if _number(performance.get("cls_max"), field="performance.cls_max") != 0.1:
            raise AccessibilityPerformanceError("CLS reference budget drift")
        if performance.get("regression_budget_required") is not True:
            raise AccessibilityPerformanceError("performance regression budget required")
        if performance.get("production_certification") is not False:
            raise AccessibilityPerformanceError("production performance certification forbidden")
        if performance.get("real_user_monitoring_certification") is not False:
            raise AccessibilityPerformanceError("RUM certification forbidden")

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
            raise AccessibilityPerformanceError("P23-G safety boundary drift")

        return cls(
            profile_ids=tuple(profile_ids),
            profile_widths=tuple(profile_widths),
            screen_ids=tuple(screen_ids),
            accessibility=accessibility,
            performance=performance,
            safety=safety,
        )

    @property
    def policy_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()

    def payload(self) -> dict[str, object]:
        return {
            "profile_ids": list(self.profile_ids),
            "profile_widths": list(self.profile_widths),
            "screen_ids": list(self.screen_ids),
            "accessibility": self.accessibility,
            "performance": self.performance,
            "safety": self.safety,
        }
