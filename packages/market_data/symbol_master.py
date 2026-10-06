from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import json
from pathlib import Path
from typing import Mapping, Sequence, cast

from packages.contracts.market_data import ProviderMarketEnvelope


class SymbolMasterError(ValueError):
    """Symbol Master configuration or provider identity is invalid."""


class InstrumentRole(StrEnum):
    TRADABLE_RESEARCH_CANDIDATE = "TRADABLE_RESEARCH_CANDIDATE"
    CONTEXT_ONLY = "CONTEXT_ONLY"


class AliasMode(StrEnum):
    EXACT = "EXACT"
    DYNAMIC_MAPPED_CONTRACT = "DYNAMIC_MAPPED_CONTRACT"


@dataclass(frozen=True, slots=True)
class CanonicalInstrument:
    canonical_id: str
    asset_class: str
    role: InstrumentRole


@dataclass(frozen=True, slots=True)
class ProviderAlias:
    mode: AliasMode
    provider: str
    exchange: str
    instrument_class: str
    code: str | None = None
    subscription_symbol: str | None = None

    def key(self) -> tuple[str, str, str, str, str]:
        return (
            self.mode.value,
            self.provider,
            self.exchange,
            self.instrument_class,
            self.code or self.subscription_symbol or "",
        )


@dataclass(frozen=True, slots=True)
class SymbolRecord:
    instrument: CanonicalInstrument
    aliases: tuple[ProviderAlias, ...]


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SymbolMasterError(f"{field} must be a non-empty string")
    return value.strip()


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise SymbolMasterError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _sequence(value: object, *, field: str) -> Sequence[object]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise SymbolMasterError(f"{field} must be an array")
    return cast(Sequence[object], value)


def metadata_mapping(metadata: tuple[tuple[str, str], ...]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in metadata:
        if key in out:
            raise SymbolMasterError(f"duplicate metadata key: {key}")
        out[key] = value
    return out


class SymbolMaster:
    def __init__(self, records: Sequence[SymbolRecord]) -> None:
        if not records:
            raise SymbolMasterError("at least one canonical instrument is required")

        by_id: dict[str, SymbolRecord] = {}
        alias_owners: dict[tuple[str, str, str, str, str], str] = {}
        for record in records:
            cid = record.instrument.canonical_id
            if cid in by_id:
                raise SymbolMasterError(f"duplicate canonical_id: {cid}")
            if not record.aliases:
                raise SymbolMasterError(f"canonical instrument has no aliases: {cid}")
            by_id[cid] = record
            for alias in record.aliases:
                key = alias.key()
                previous = alias_owners.get(key)
                if previous is not None:
                    raise SymbolMasterError(
                        f"duplicate provider alias key={key} owners={previous},{cid}"
                    )
                alias_owners[key] = cid

        self._records = tuple(records)
        self._by_id = by_id

    @classmethod
    def from_path(cls, path: Path) -> "SymbolMaster":
        try:
            raw_value: object = json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception as exc:
            raise SymbolMasterError(f"invalid Symbol Master JSON: {exc}") from exc
        raw = _mapping(raw_value, field="root")
        if raw.get("schema_version") != "1.0":
            raise SymbolMasterError("unsupported Symbol Master schema_version")

        instruments = _sequence(raw.get("instruments"), field="instruments")
        records: list[SymbolRecord] = []
        for index, item in enumerate(instruments):
            row = _mapping(item, field=f"instruments[{index}]")
            canonical_id = _text(row.get("canonical_id"), field=f"instruments[{index}].canonical_id")
            asset_class = _text(row.get("asset_class"), field=f"instruments[{index}].asset_class")
            role_text = _text(row.get("role"), field=f"instruments[{index}].role")
            try:
                role = InstrumentRole(role_text)
            except ValueError:
                raise SymbolMasterError(f"unsupported instrument role: {role_text}") from None

            aliases_raw = _sequence(row.get("aliases"), field=f"instruments[{index}].aliases")
            aliases: list[ProviderAlias] = []
            for alias_index, alias_item in enumerate(aliases_raw):
                alias_row = _mapping(
                    alias_item,
                    field=f"instruments[{index}].aliases[{alias_index}]",
                )
                mode_text = _text(
                    alias_row.get("mode"),
                    field=f"instruments[{index}].aliases[{alias_index}].mode",
                )
                try:
                    mode = AliasMode(mode_text)
                except ValueError:
                    raise SymbolMasterError(f"unsupported alias mode: {mode_text}") from None

                provider = _text(alias_row.get("provider"), field="alias.provider")
                exchange = _text(alias_row.get("exchange"), field="alias.exchange")
                instrument_class = _text(
                    alias_row.get("instrument_class"),
                    field="alias.instrument_class",
                )

                if mode is AliasMode.EXACT:
                    code = _text(alias_row.get("code"), field="alias.code")
                    aliases.append(
                        ProviderAlias(
                            mode=mode,
                            provider=provider,
                            exchange=exchange,
                            instrument_class=instrument_class,
                            code=code,
                        )
                    )
                else:
                    subscription_symbol = _text(
                        alias_row.get("subscription_symbol"),
                        field="alias.subscription_symbol",
                    )
                    mapped_source = _text(
                        alias_row.get("mapped_code_source"),
                        field="alias.mapped_code_source",
                    )
                    if mapped_source != "envelope.instrument.code":
                        raise SymbolMasterError(
                            "dynamic mapped alias must use envelope.instrument.code"
                        )
                    required = _sequence(
                        alias_row.get("required_metadata"),
                        field="alias.required_metadata",
                    )
                    required_text = tuple(_text(x, field="required_metadata[]") for x in required)
                    if required_text != (
                        "canonical_id",
                        "subscription_symbol",
                        "mapped_symbol",
                    ):
                        raise SymbolMasterError(
                            "dynamic mapped alias requires canonical_id, subscription_symbol, mapped_symbol metadata"
                        )
                    aliases.append(
                        ProviderAlias(
                            mode=mode,
                            provider=provider,
                            exchange=exchange,
                            instrument_class=instrument_class,
                            subscription_symbol=subscription_symbol,
                        )
                    )

            records.append(
                SymbolRecord(
                    instrument=CanonicalInstrument(
                        canonical_id=canonical_id,
                        asset_class=asset_class,
                        role=role,
                    ),
                    aliases=tuple(aliases),
                )
            )
        return cls(records)

    def get(self, canonical_id: str) -> CanonicalInstrument:
        record = self._by_id.get(canonical_id)
        if record is None:
            raise SymbolMasterError(f"unknown canonical_id: {canonical_id}")
        return record.instrument

    def resolve(self, envelope: ProviderMarketEnvelope) -> CanonicalInstrument:
        metadata = metadata_mapping(envelope.metadata)
        claimed = metadata.get("canonical_id")

        if claimed is not None:
            record = self._by_id.get(claimed)
            if record is None:
                raise SymbolMasterError(f"unknown canonical_id in provider metadata: {claimed}")
            if not any(self._matches(alias, envelope, metadata) for alias in record.aliases):
                raise SymbolMasterError(
                    f"provider identity does not match claimed canonical_id: {claimed}"
                )
            return record.instrument

        matches: list[CanonicalInstrument] = []
        for record in self._records:
            for alias in record.aliases:
                if alias.mode is AliasMode.EXACT and self._matches(alias, envelope, metadata):
                    matches.append(record.instrument)
                    break

        if len(matches) != 1:
            raise SymbolMasterError(
                f"provider identity resolved to {len(matches)} canonical instruments"
            )
        return matches[0]

    @staticmethod
    def _matches(
        alias: ProviderAlias,
        envelope: ProviderMarketEnvelope,
        metadata: Mapping[str, str],
    ) -> bool:
        instrument = envelope.instrument
        if (
            instrument.provider != alias.provider
            or instrument.exchange != alias.exchange
            or instrument.instrument_class != alias.instrument_class
        ):
            return False

        if alias.mode is AliasMode.EXACT:
            return instrument.code == alias.code

        if metadata.get("subscription_symbol") != alias.subscription_symbol:
            return False
        mapped = metadata.get("mapped_symbol")
        if mapped is None or mapped != instrument.code:
            return False
        return True
