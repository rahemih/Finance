from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Iterable

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_STATES = {"DRAFT", "RESEARCH", "VALIDATED", "RETIRED"}


class StrategyRegistryError(ValueError):
    """P17-G strategy registry invariant failure."""


def _sha(value: str, field: str) -> str:
    v = value.strip().lower()
    if _SHA256.fullmatch(v) is None:
        raise StrategyRegistryError(f"{field} must be lowercase SHA-256")
    return v


def _hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class StrategyVersion:
    strategy_id: str
    version: str
    lifecycle_state: str
    definition_sha256: str
    code_sha256: str
    config_sha256: str
    universe_id: str
    timeframe_id: str
    walk_forward_certificate_sha256: str | None = None
    robustness_certificate_sha256: str | None = None
    capacity_certificate_sha256: str | None = None

    def __post_init__(self) -> None:
        for field in ("strategy_id", "version", "universe_id", "timeframe_id"):
            if not str(getattr(self, field)).strip():
                raise StrategyRegistryError(f"{field} must be non-empty")
        if self.lifecycle_state not in _STATES:
            raise StrategyRegistryError("unsupported lifecycle_state")
        object.__setattr__(self, "definition_sha256", _sha(self.definition_sha256, "definition_sha256"))
        object.__setattr__(self, "code_sha256", _sha(self.code_sha256, "code_sha256"))
        object.__setattr__(self, "config_sha256", _sha(self.config_sha256, "config_sha256"))
        for field in (
            "walk_forward_certificate_sha256",
            "robustness_certificate_sha256",
            "capacity_certificate_sha256",
        ):
            value = getattr(self, field)
            if value is not None:
                object.__setattr__(self, field, _sha(value, field))
        if self.lifecycle_state == "VALIDATED":
            if any(
                getattr(self, field) is None
                for field in (
                    "walk_forward_certificate_sha256",
                    "robustness_certificate_sha256",
                    "capacity_certificate_sha256",
                )
            ):
                raise StrategyRegistryError("VALIDATED strategy requires P17-D/E/F certificate lineage")

    def payload(self) -> dict[str, object]:
        return {
            "strategy_id": self.strategy_id,
            "version": self.version,
            "lifecycle_state": self.lifecycle_state,
            "definition_sha256": self.definition_sha256,
            "code_sha256": self.code_sha256,
            "config_sha256": self.config_sha256,
            "universe_id": self.universe_id,
            "timeframe_id": self.timeframe_id,
            "walk_forward_certificate_sha256": self.walk_forward_certificate_sha256,
            "robustness_certificate_sha256": self.robustness_certificate_sha256,
            "capacity_certificate_sha256": self.capacity_certificate_sha256,
        }

    @property
    def record_id(self) -> str:
        return _hash(self.payload())


@dataclass(frozen=True, slots=True)
class StrategyRegistry:
    records: tuple[StrategyVersion, ...]
    registry_id: str
    profitability_authority: bool = False
    automatic_promotion: bool = False
    g9_authority: bool = False
    execution_authority: bool = False


def build_strategy_registry(records: Iterable[StrategyVersion]) -> StrategyRegistry:
    by_key: dict[tuple[str, str], StrategyVersion] = {}
    for record in records:
        key = (record.strategy_id, record.version)
        prior = by_key.get(key)
        if prior is not None and prior.record_id != record.record_id:
            raise StrategyRegistryError("strategy version is immutable and cannot diverge")
        by_key[key] = record
    ordered = tuple(sorted(by_key.values(), key=lambda r: (r.strategy_id, r.version)))
    payload = {
        "schema_version": "1.0",
        "records": [r.payload() for r in ordered],
        "profitability_authority": False,
        "automatic_promotion": False,
        "g9_authority": False,
        "execution_authority": False,
    }
    return StrategyRegistry(records=ordered, registry_id=_hash(payload))
