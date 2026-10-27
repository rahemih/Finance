from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import cast


class DesignSystemError(ValueError):
    """P23-B design-system invariant failure."""


EXPECTED_TYPOGRAPHY = (12, 14, 16, 18, 20, 24, 30, 36)
EXPECTED_SPACING = (4, 8, 12, 16, 24, 32, 48, 64)
EXPECTED_RADII = (4, 8, 12, 16, 999)
EXPECTED_BREAKPOINTS = (640, 768, 1024, 1280, 1536)
EXPECTED_STATES = (
    "success",
    "warning",
    "critical",
    "stale",
    "degraded",
    "no_trade",
    "disconnected",
    "pending",
)
EXPECTED_TERMS = (
    "dashboard",
    "market",
    "opportunity",
    "trade",
    "portfolio",
    "demo",
    "research",
    "report",
    "system",
    "settings",
    "glossary",
    "long",
    "short",
    "wait",
    "no_trade",
)
EXPECTED_LTR_ISLANDS = (
    "ticker",
    "ohlc",
    "price",
    "quantity",
    "percentage",
    "order_id",
    "trade_id",
    "hash",
    "timestamp_iso",
    "version",
    "ip_address",
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
        raise DesignSystemError(f"{field} must be an object")
    raw = cast(dict[object, object], value)
    result: dict[str, object] = {}
    for key, item in raw.items():
        if not isinstance(key, str):
            raise DesignSystemError(f"{field} keys must be strings")
        result[key] = item
    return result


def _list(value: object, *, field: str) -> list[object]:
    if not isinstance(value, list):
        raise DesignSystemError(f"{field} must be a list")
    return cast(list[object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DesignSystemError(f"{field} must be non-empty text")
    return value


def _number_tuple(value: object, *, field: str) -> tuple[int, ...]:
    items = _list(value, field=field)
    result: list[int] = []
    for item in items:
        if not isinstance(item, int) or isinstance(item, bool):
            raise DesignSystemError(f"{field} must contain integers")
        result.append(item)
    return tuple(result)


def _hex_rgb(value: str) -> tuple[float, float, float]:
    if len(value) != 7 or not value.startswith("#"):
        raise DesignSystemError(f"invalid hex color: {value}")
    try:
        rgb = tuple(int(value[index:index + 2], 16) / 255.0 for index in (1, 3, 5))
    except ValueError as exc:
        raise DesignSystemError(f"invalid hex color: {value}") from exc
    return cast(tuple[float, float, float], rgb)


def _relative_luminance(value: str) -> float:
    channels: list[float] = []
    for channel in _hex_rgb(value):
        channels.append(
            channel / 12.92
            if channel <= 0.04045
            else ((channel + 0.055) / 1.055) ** 2.4
        )
    return (
        0.2126 * channels[0]
        + 0.7152 * channels[1]
        + 0.0722 * channels[2]
    )


def contrast_ratio(first: str, second: str) -> float:
    left = _relative_luminance(first)
    right = _relative_luminance(second)
    lighter = max(left, right)
    darker = min(left, right)
    return (lighter + 0.05) / (darker + 0.05)


@dataclass(frozen=True, slots=True)
class SemanticState:
    state_id: str
    label_fa: str
    icon: str
    light_foreground: str
    light_background: str
    dark_foreground: str
    dark_background: str


@dataclass(frozen=True, slots=True)
class DesignSystem:
    locale: str
    shell_direction: str
    financial_island_direction: str
    typography_px: tuple[int, ...]
    spacing_px: tuple[int, ...]
    radii_px: tuple[int, ...]
    breakpoints_px: tuple[int, ...]
    semantic_states: tuple[SemanticState, ...]
    terminology_ids: tuple[str, ...]
    ltr_islands: tuple[str, ...]
    raw: dict[str, object]

    @classmethod
    def from_path(cls, path: Path) -> "DesignSystem":
        try:
            raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise DesignSystemError(f"invalid P23-B JSON: {exc}") from exc
        raw = _object(raw_value, field="root")

        expected_static: dict[str, object] = {
            "schema_version": "1.0",
            "kind": "NEXUS_QUANT_P23B_DESIGN_SYSTEM",
            "task_id": "FIN-P23-WB-001",
            "locale": "fa-IR",
            "shell_direction": "RTL",
            "financial_island_direction": "LTR",
        }
        for key, expected in expected_static.items():
            if raw.get(key) != expected:
                raise DesignSystemError(f"P23-B policy mismatch: {key}")

        typography = _number_tuple(raw.get("typography_px"), field="typography_px")
        spacing = _number_tuple(raw.get("spacing_px"), field="spacing_px")
        radii = _number_tuple(raw.get("radii_px"), field="radii_px")
        breakpoints = _number_tuple(raw.get("breakpoints_px"), field="breakpoints_px")
        if typography != EXPECTED_TYPOGRAPHY:
            raise DesignSystemError("typography scale drift")
        if spacing != EXPECTED_SPACING:
            raise DesignSystemError("spacing scale drift")
        if radii != EXPECTED_RADII:
            raise DesignSystemError("radii scale drift")
        if breakpoints != EXPECTED_BREAKPOINTS:
            raise DesignSystemError("breakpoint scale drift")

        fonts = _object(raw.get("fonts"), field="fonts")
        if fonts != {
            "persian_ui": "Noto Sans Arabic",
            "latin_financial": "Noto Sans",
        }:
            raise DesignSystemError("font policy drift")

        themes = _object(raw.get("themes"), field="themes")
        for theme_id in ("light", "dark"):
            theme = _object(themes.get(theme_id), field=f"themes.{theme_id}")
            text_color = _text(theme.get("text"), field=f"themes.{theme_id}.text")
            background = _text(
                theme.get("background"),
                field=f"themes.{theme_id}.background",
            )
            if contrast_ratio(text_color, background) < 4.5:
                raise DesignSystemError(
                    f"{theme_id} body text contrast below WCAG AA"
                )
            muted = _text(
                theme.get("muted_text"),
                field=f"themes.{theme_id}.muted_text",
            )
            surface = _text(
                theme.get("surface"),
                field=f"themes.{theme_id}.surface",
            )
            if contrast_ratio(muted, surface) < 4.5:
                raise DesignSystemError(
                    f"{theme_id} muted text contrast below WCAG AA"
                )

        states_raw = _object(raw.get("semantic_states"), field="semantic_states")
        if tuple(states_raw) != EXPECTED_STATES:
            raise DesignSystemError("semantic state coverage/order drift")
        states: list[SemanticState] = []
        for state_id in EXPECTED_STATES:
            item = _object(states_raw[state_id], field=f"semantic_states.{state_id}")
            label = _text(item.get("label_fa"), field=f"{state_id}.label_fa")
            icon = _text(item.get("icon"), field=f"{state_id}.icon")
            light = _object(item.get("light"), field=f"{state_id}.light")
            dark = _object(item.get("dark"), field=f"{state_id}.dark")
            light_fg = _text(light.get("foreground"), field=f"{state_id}.light.foreground")
            light_bg = _text(light.get("background"), field=f"{state_id}.light.background")
            dark_fg = _text(dark.get("foreground"), field=f"{state_id}.dark.foreground")
            dark_bg = _text(dark.get("background"), field=f"{state_id}.dark.background")
            if contrast_ratio(light_fg, light_bg) < 4.5:
                raise DesignSystemError(f"{state_id} light contrast below WCAG AA")
            if contrast_ratio(dark_fg, dark_bg) < 4.5:
                raise DesignSystemError(f"{state_id} dark contrast below WCAG AA")
            states.append(
                SemanticState(
                    state_id=state_id,
                    label_fa=label,
                    icon=icon,
                    light_foreground=light_fg,
                    light_background=light_bg,
                    dark_foreground=dark_fg,
                    dark_background=dark_bg,
                )
            )

        directionality = _object(raw.get("directionality"), field="directionality")
        islands = tuple(
            _text(item, field="ltr_islands[]")
            for item in _list(
                directionality.get("ltr_islands"),
                field="directionality.ltr_islands",
            )
        )
        if islands != EXPECTED_LTR_ISLANDS:
            raise DesignSystemError("LTR financial island policy drift")
        if directionality.get("ltr_island_isolation_required") is not True:
            raise DesignSystemError("LTR islands must require bidi isolation")

        digit_policy = _object(raw.get("digit_policy"), field="digit_policy")
        latin_digits = tuple(
            _text(item, field="latin_digits[]")
            for item in _list(
                digit_policy.get("latin_digits"),
                field="digit_policy.latin_digits",
            )
        )
        required_latin = {
            "financial_values",
            "identifiers",
            "prices",
            "quantities",
            "percentages",
            "iso_timestamps",
            "versions",
        }
        if set(latin_digits) != required_latin:
            raise DesignSystemError("financial digit policy drift")

        terms_raw = _list(raw.get("terminology"), field="terminology")
        term_ids: list[str] = []
        for index, value in enumerate(terms_raw):
            item = _object(value, field=f"terminology[{index}]")
            term_id = _text(item.get("id"), field=f"terminology[{index}].id")
            _text(item.get("canonical"), field=f"terminology[{index}].canonical")
            fa = _text(item.get("fa"), field=f"terminology[{index}].fa")
            if term_id in {"long", "short", "wait", "no_trade"}:
                canonical = cast(str, item["canonical"])
                if canonical not in fa:
                    raise DesignSystemError(
                        f"financial direction identifier hidden: {term_id}"
                    )
            term_ids.append(term_id)
        if tuple(term_ids) != EXPECTED_TERMS:
            raise DesignSystemError("terminology coverage/order drift")

        accessibility = _object(raw.get("accessibility"), field="accessibility")
        if accessibility.get("minimum_normal_text_contrast") != 4.5:
            raise DesignSystemError("normal text contrast target drift")
        if accessibility.get("color_only_state_forbidden") is not True:
            raise DesignSystemError("color-only state must remain forbidden")
        if accessibility.get("visible_focus_required") is not True:
            raise DesignSystemError("visible focus must remain required")
        if accessibility.get("reduced_motion_required") is not True:
            raise DesignSystemError("reduced motion must remain required")
        if accessibility.get("minimum_touch_target_px") != 44:
            raise DesignSystemError("touch target policy drift")

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
            raise DesignSystemError("P23-B safety boundary drift")

        return cls(
            locale="fa-IR",
            shell_direction="RTL",
            financial_island_direction="LTR",
            typography_px=typography,
            spacing_px=spacing,
            radii_px=radii,
            breakpoints_px=breakpoints,
            semantic_states=tuple(states),
            terminology_ids=tuple(term_ids),
            ltr_islands=islands,
            raw=raw,
        )

    @property
    def design_system_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.raw)).hexdigest()
