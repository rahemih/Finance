from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import unicodedata
from typing import Mapping, cast

from .ingestion import RawNewsItem


class EntityMappingError(ValueError):
    pass


def _norm(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


@dataclass(frozen=True, slots=True)
class EntityAsset:
    entity_id: str
    canonical_name: str
    symbol: str
    asset_class: str
    venue_scope: str
    aliases: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EntityRegistry:
    entities: tuple[EntityAsset, ...]
    confidence_states: tuple[str, ...]
    canonical_tests_network_required: bool
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "EntityRegistry":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw_value, Mapping):
            raise EntityMappingError("registry root must be an object")
        raw = cast(Mapping[str, object], raw_value)
        if raw.get("schema_version") != "1.0":
            raise EntityMappingError("unsupported registry schema_version")
        entities_value = raw.get("entities")
        states_value = raw.get("confidence_states")
        if not isinstance(entities_value, list) or not entities_value:
            raise EntityMappingError("entities must be non-empty list")
        if not isinstance(states_value, list) or not states_value:
            raise EntityMappingError("confidence_states must be non-empty list")

        entities: list[EntityAsset] = []
        alias_owners: dict[str, str] = {}
        for item_value in cast(list[object], entities_value):
            if not isinstance(item_value, Mapping):
                raise EntityMappingError("entity must be object")
            item = cast(Mapping[str, object], item_value)
            aliases_value = item.get("aliases")
            if not isinstance(aliases_value, list) or not aliases_value:
                raise EntityMappingError("aliases must be non-empty list")
            entity_id = str(item.get("entity_id", "")).strip()
            canonical_name = str(item.get("canonical_name", "")).strip()
            symbol = str(item.get("symbol", "")).strip().upper()
            asset_class = str(item.get("asset_class", "")).strip().upper()
            venue_scope = str(item.get("venue_scope", "")).strip().upper()
            if not all((entity_id, canonical_name, symbol, asset_class, venue_scope)):
                raise EntityMappingError("entity missing required field")
            aliases = tuple(_norm(str(x)) for x in cast(list[object], aliases_value))
            if any(not a for a in aliases) or len(set(aliases)) != len(aliases):
                raise EntityMappingError("aliases must be unique non-empty values")
            for alias in aliases:
                owner = alias_owners.get(alias)
                if owner is not None and owner != entity_id:
                    raise EntityMappingError(f"ambiguous alias in registry: {alias}")
                alias_owners[alias] = entity_id
            entities.append(EntityAsset(entity_id, canonical_name, symbol, asset_class, venue_scope, aliases))

        states = tuple(str(x) for x in cast(list[object], states_value))
        network = raw.get("canonical_tests_network_required")
        live = raw.get("live_trading")
        auto = raw.get("auto_trading")
        if network is not False or live != "DISABLED" or auto != "DISABLED":
            raise EntityMappingError("registry violates safety constraints")
        return cls(tuple(entities), states, False, "DISABLED", "DISABLED")


@dataclass(frozen=True, slots=True)
class EntityMatch:
    entity_id: str
    symbol: str
    asset_class: str
    venue_scope: str
    confidence: str
    matched_term: str


@dataclass(frozen=True, slots=True)
class MappingResult:
    news_content_id: str
    matches: tuple[EntityMatch, ...]
    state: str


def _contains_term(text: str, term: str) -> bool:
    pattern = r"(?<!\w)" + re.escape(term) + r"(?!\w)"
    return re.search(pattern, text, flags=re.UNICODE) is not None


def map_news_item(item: RawNewsItem, *, registry: EntityRegistry) -> MappingResult:
    text = _norm(f"{item.normalized_title} {item.normalized_body}")
    matches: list[EntityMatch] = []
    for entity in registry.entities:
        found: list[tuple[str, str]] = []
        for term in (_norm(entity.canonical_name), entity.symbol.casefold()):
            if term and _contains_term(text, term):
                found.append((term, "EXACT"))
        for alias in entity.aliases:
            if _contains_term(text, alias):
                found.append((alias, "ALIAS"))
        if not found:
            continue
        found.sort(key=lambda x: (0 if x[1] == "EXACT" else 1, -len(x[0]), x[0]))
        term, confidence = found[0]
        matches.append(EntityMatch(entity.entity_id, entity.symbol, entity.asset_class, entity.venue_scope, confidence, term))

    by_term: dict[str, set[str]] = {}
    for match in matches:
        by_term.setdefault(match.matched_term, set()).add(match.entity_id)
    if any(len(owners) > 1 for owners in by_term.values()):
        raise EntityMappingError("ambiguous mapping term")

    matches.sort(key=lambda m: (m.entity_id, m.confidence, m.matched_term))
    return MappingResult(item.content_id, tuple(matches), "NONE" if not matches else "MAPPED")
