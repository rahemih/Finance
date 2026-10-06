from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from packages.contracts.market_data import (
    MarketEventKind,
    MarketPayload,
    ProviderContextEnvelope,
    ProviderEventEnvelope,
    ProviderMarketEnvelope,
    ProviderQuoteEnvelope,
    ProviderTimestamp,
)
from packages.market_data.symbol_master import (
    CanonicalInstrument,
    InstrumentRole,
    SymbolMaster,
    metadata_mapping,
)


class NormalizationError(ValueError):
    """Provider-neutral normalization input is invalid."""


class SourceEnvelopeKind(StrEnum):
    EVENT = "EVENT"
    QUOTE = "QUOTE"
    CONTEXT = "CONTEXT"


PRECISION_POLICY = "SOURCE_PRESERVED_NO_SYNTHETIC_PRECISION"


@dataclass(frozen=True, slots=True)
class CanonicalClock:
    provider_event_time: ProviderTimestamp | None
    exchange_time: ProviderTimestamp | None
    collection_time: ProviderTimestamp | None
    provider_receive_time: ProviderTimestamp | None
    local_receive_time_ns: int
    auxiliary_source_times: tuple[tuple[str, ProviderTimestamp], ...]
    event_to_local_delta_ns: int | None
    provider_receive_to_local_delta_ns: int | None
    precision_policy: str = PRECISION_POLICY

    def __post_init__(self) -> None:
        if (
            isinstance(self.local_receive_time_ns, bool)
            or not isinstance(self.local_receive_time_ns, int)
            or self.local_receive_time_ns < 0
        ):
            raise NormalizationError(
                "local_receive_time_ns must be a non-negative integer"
            )
        names = [name for name, _ in self.auxiliary_source_times]
        if len(names) != len(set(names)):
            raise NormalizationError("auxiliary source time names must be unique")
        for name, stamp in self.auxiliary_source_times:
            if not name:
                raise NormalizationError("auxiliary source time name must be non-empty")
            if stamp.epoch_ns < 0:
                raise NormalizationError(
                    f"auxiliary source time must be non-negative: {name}"
                )


@dataclass(frozen=True, slots=True)
class CanonicalMarketEvent:
    canonical_id: str
    asset_class: str
    instrument_role: InstrumentRole
    kind: MarketEventKind
    provider: str
    provider_exchange: str
    provider_instrument_class: str
    provider_symbol: str
    sequence_id: str
    source_envelope_kind: SourceEnvelopeKind
    clock: CanonicalClock
    payload: MarketPayload
    provenance: tuple[tuple[str, str], ...]


def _signed_delta(local_ns: int, source: ProviderTimestamp | None) -> int | None:
    if source is None:
        return None
    return local_ns - source.epoch_ns


def _clock_for(envelope: ProviderMarketEnvelope) -> tuple[CanonicalClock, SourceEnvelopeKind]:
    local_ns = envelope.received_at_ns
    if isinstance(local_ns, bool) or not isinstance(local_ns, int) or local_ns < 0:
        raise NormalizationError("received_at_ns must be a non-negative integer")

    if isinstance(envelope, ProviderEventEnvelope):
        event = envelope.ts_event
        return (
            CanonicalClock(
                provider_event_time=event,
                exchange_time=envelope.ts_exchange,
                collection_time=envelope.ts_collection,
                provider_receive_time=None,
                local_receive_time_ns=local_ns,
                auxiliary_source_times=(),
                event_to_local_delta_ns=_signed_delta(local_ns, event),
                provider_receive_to_local_delta_ns=None,
            ),
            SourceEnvelopeKind.EVENT,
        )

    if isinstance(envelope, ProviderQuoteEnvelope):
        event = envelope.provider_event_time
        return (
            CanonicalClock(
                provider_event_time=event,
                exchange_time=None,
                collection_time=None,
                provider_receive_time=None,
                local_receive_time_ns=local_ns,
                auxiliary_source_times=(
                    ("ask_time", envelope.payload.ask_time),
                    ("bid_time", envelope.payload.bid_time),
                ),
                event_to_local_delta_ns=_signed_delta(local_ns, event),
                provider_receive_to_local_delta_ns=None,
            ),
            SourceEnvelopeKind.QUOTE,
        )

    if isinstance(envelope, ProviderContextEnvelope):
        event = envelope.provider_event_time
        receive = envelope.provider_receive_time
        return (
            CanonicalClock(
                provider_event_time=event,
                exchange_time=None,
                collection_time=None,
                provider_receive_time=receive,
                local_receive_time_ns=local_ns,
                auxiliary_source_times=(),
                event_to_local_delta_ns=_signed_delta(local_ns, event),
                provider_receive_to_local_delta_ns=_signed_delta(local_ns, receive),
            ),
            SourceEnvelopeKind.CONTEXT,
        )

    raise NormalizationError(f"unsupported provider envelope type: {type(envelope).__name__}")


def _provenance(
    envelope: ProviderMarketEnvelope,
    instrument: CanonicalInstrument,
) -> tuple[tuple[str, str], ...]:
    values: dict[str, str] = {}
    for key, value in envelope.metadata:
        if key in values:
            raise NormalizationError(f"duplicate metadata key: {key}")
        values[key] = value

    values["canonical_id"] = instrument.canonical_id
    values["canonical_role"] = instrument.role.value
    values["provider"] = envelope.instrument.provider
    values["provider_exchange"] = envelope.instrument.exchange
    values["provider_instrument_class"] = envelope.instrument.instrument_class
    values["provider_symbol"] = envelope.instrument.code
    values["precision_policy"] = PRECISION_POLICY
    return tuple(sorted(values.items()))


class CanonicalNormalizer:
    def __init__(self, symbol_master: SymbolMaster) -> None:
        self._symbol_master = symbol_master

    def normalize(self, envelope: ProviderMarketEnvelope) -> CanonicalMarketEvent:
        if not envelope.sequence_id:
            raise NormalizationError("sequence_id must be non-empty")

        instrument = self._symbol_master.resolve(envelope)
        clock, source_kind = _clock_for(envelope)

        return CanonicalMarketEvent(
            canonical_id=instrument.canonical_id,
            asset_class=instrument.asset_class,
            instrument_role=instrument.role,
            kind=envelope.kind,
            provider=envelope.instrument.provider,
            provider_exchange=envelope.instrument.exchange,
            provider_instrument_class=envelope.instrument.instrument_class,
            provider_symbol=envelope.instrument.code,
            sequence_id=envelope.sequence_id,
            source_envelope_kind=source_kind,
            clock=clock,
            payload=envelope.payload,
            provenance=_provenance(envelope, instrument),
        )
