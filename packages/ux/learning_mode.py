from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import cast

from packages.ux.design_system import DesignSystem


class LearningModeError(ValueError):
    """P23-D Learning Mode / glossary invariant failure."""


EXPECTED_MODES = ("OFF", "GUIDED", "DETAILED")
EXPECTED_FIELDS = ("concept", "why_visible", "limitations", "source_context")


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _object(value: object, *, field: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise LearningModeError(f"{field} must be an object")
    raw = cast(dict[object, object], value)
    result: dict[str, object] = {}
    for key, item in raw.items():
        if not isinstance(key, str):
            raise LearningModeError(f"{field} keys must be strings")
        result[key] = item
    return result


def _list(value: object, *, field: str) -> list[object]:
    if not isinstance(value, list):
        raise LearningModeError(f"{field} must be a list")
    return cast(list[object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LearningModeError(f"{field} must be non-empty text")
    return value


@dataclass(frozen=True, slots=True)
class GlossaryEntry:
    term_id: str
    canonical: str
    fa: str
    definition_fa: str


@dataclass(frozen=True, slots=True)
class LearningMode:
    modes: tuple[str, ...]
    default_mode: str
    required_fields: tuple[str, ...]
    glossary_route: str
    entries: tuple[GlossaryEntry, ...]
    design_system_id: str
    safety: dict[str, object]

    @classmethod
    def from_paths(cls, policy_path: Path, design_system_path: Path) -> "LearningMode":
        try:
            raw_value: object = json.loads(policy_path.read_text(encoding="utf-8"))
            design_raw_value: object = json.loads(
                design_system_path.read_text(encoding="utf-8")
            )
        except Exception as exc:
            raise LearningModeError(f"invalid P23-D JSON: {exc}") from exc

        raw = _object(raw_value, field="root")
        design_raw = _object(design_raw_value, field="design_system")
        expected_static: dict[str, object] = {
            "schema_version": "1.0",
            "kind": "NEXUS_QUANT_P23D_LEARNING_MODE_GLOSSARY",
            "task_id": "FIN-P23-WD-001",
            "phase": "P23",
            "workstream": "P23-D",
            "locale": "fa-IR",
            "direction": "RTL",
            "canonical_identifier_direction": "LTR",
        }
        for key, expected in expected_static.items():
            if raw.get(key) != expected:
                raise LearningModeError(f"P23-D policy mismatch: {key}")

        design = DesignSystem.from_path(design_system_path)

        learning = _object(raw.get("learning_mode"), field="learning_mode")
        if learning.get("authority") != "EXPLANATION_ONLY":
            raise LearningModeError("Learning Mode authority drift")
        modes = tuple(
            _text(value, field="learning_mode.modes[]")
            for value in _list(learning.get("modes"), field="learning_mode.modes")
        )
        if modes != EXPECTED_MODES:
            raise LearningModeError("Learning Mode order/coverage drift")
        default_mode = _text(
            learning.get("default_mode"), field="learning_mode.default_mode"
        )
        if default_mode != "GUIDED":
            raise LearningModeError("default Learning Mode drift")
        fields = tuple(
            _text(value, field="learning_mode.required_fields[]")
            for value in _list(
                learning.get("required_fields"),
                field="learning_mode.required_fields",
            )
        )
        if fields != EXPECTED_FIELDS:
            raise LearningModeError("required explanation field drift")
        for flag in (
            "mutates_signal",
            "mutates_probability",
            "personalized_advice",
            "execution_action",
        ):
            if learning.get(flag) is not False:
                raise LearningModeError(f"forbidden Learning Mode authority: {flag}")

        glossary = _object(raw.get("glossary"), field="glossary")
        route = _text(glossary.get("route"), field="glossary.route")
        if route != "/glossary":
            raise LearningModeError("canonical glossary route drift")

        design_terms = _list(design_raw.get("terminology"), field="design.terminology")
        entries_raw = _list(glossary.get("entries"), field="glossary.entries")
        if len(entries_raw) != len(design_terms):
            raise LearningModeError("glossary coverage drift")

        entries: list[GlossaryEntry] = []
        for index, (entry_value, design_value) in enumerate(
            zip(entries_raw, design_terms, strict=True)
        ):
            entry = _object(entry_value, field=f"glossary.entries[{index}]")
            design_entry = _object(design_value, field=f"design.terminology[{index}]")
            term = GlossaryEntry(
                term_id=_text(entry.get("id"), field=f"glossary[{index}].id"),
                canonical=_text(
                    entry.get("canonical"), field=f"glossary[{index}].canonical"
                ),
                fa=_text(entry.get("fa"), field=f"glossary[{index}].fa"),
                definition_fa=_text(
                    entry.get("definition_fa"),
                    field=f"glossary[{index}].definition_fa",
                ),
            )
            if (
                term.term_id != design_entry.get("id")
                or term.canonical != design_entry.get("canonical")
                or term.fa != design_entry.get("fa")
            ):
                raise LearningModeError(
                    f"glossary term {index} must match P23-B terminology"
                )
            entries.append(term)

        if tuple(item.term_id for item in entries) != design.terminology_ids:
            raise LearningModeError("P23-B terminology order mismatch")

        provenance = _object(raw.get("provenance"), field="provenance")
        expected_provenance = {
            "source_context_required": True,
            "limitations_required": True,
            "canonical_identifier_required": True,
        }
        if provenance != expected_provenance:
            raise LearningModeError("Learning Mode provenance drift")

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
            raise LearningModeError("P23-D safety boundary drift")

        return cls(
            modes=modes,
            default_mode=default_mode,
            required_fields=fields,
            glossary_route=route,
            entries=tuple(entries),
            design_system_id=design.design_system_id,
            safety=safety,
        )

    @property
    def learning_mode_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()

    def payload(self) -> dict[str, object]:
        return {
            "modes": list(self.modes),
            "default_mode": self.default_mode,
            "required_fields": list(self.required_fields),
            "glossary_route": self.glossary_route,
            "entries": [
                {
                    "id": item.term_id,
                    "canonical": item.canonical,
                    "fa": item.fa,
                    "definition_fa": item.definition_fa,
                }
                for item in self.entries
            ],
            "design_system_id": self.design_system_id,
            "safety": self.safety,
        }
