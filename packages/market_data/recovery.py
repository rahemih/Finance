from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import json
from pathlib import Path
from typing import Mapping, Sequence, cast

from packages.contracts.market_data import MarketEventKind, OrderBookPayload, OrderBookUpdateType
from packages.market_data.normalization import CanonicalMarketEvent


class RecoveryError(ValueError):
    """Provider-neutral recovery input or state is invalid."""


class RecoveryPending(RecoveryError):
    """Recovery cannot complete until required validation evidence arrives."""


class SequenceMode(StrEnum):
    LEXICOGRAPHIC = "LEXICOGRAPHIC"
    INTEGER = "INTEGER"


class RecoverySequenceDisposition(StrEnum):
    FIRST = "FIRST"
    ADVANCING = "ADVANCING"
    DUPLICATE = "DUPLICATE"
    OUT_OF_ORDER = "OUT_OF_ORDER"
    GAP = "GAP"


class RecoveryState(StrEnum):
    ACTIVE = "ACTIVE"
    DEGRADED = "DEGRADED"
    WAITING_RETRY = "WAITING_RETRY"
    RECONNECTING = "RECONNECTING"
    RECOVERY_VALIDATION = "RECOVERY_VALIDATION"
    CIRCUIT_OPEN = "CIRCUIT_OPEN"


class FailoverDisposition(StrEnum):
    PRIMARY_ACTIVE = "PRIMARY_ACTIVE"
    BACKUP_VALIDATION_REQUIRED = "BACKUP_VALIDATION_REQUIRED"
    FAIL_CLOSED = "FAIL_CLOSED"


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise RecoveryError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _sequence(value: object, *, field: str) -> Sequence[object]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise RecoveryError(f"{field} must be an array")
    return cast(Sequence[object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RecoveryError(f"{field} must be a non-empty string")
    return value.strip()


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise RecoveryError(f"{field} must be a positive integer")
    return value


def _bool(value: object, *, field: str) -> bool:
    if not isinstance(value, bool):
        raise RecoveryError(f"{field} must be a boolean")
    return value


def _now(value: int) -> int:
    if isinstance(value, bool) or value < 0:
        raise RecoveryError("now_ns must be a non-negative integer")
    return value


@dataclass(frozen=True, slots=True)
class RecoveryKey:
    provider: str
    canonical_id: str
    event_kind: MarketEventKind

    def __post_init__(self) -> None:
        if not self.provider.strip():
            raise RecoveryError("provider must be non-empty")
        if not self.canonical_id.strip():
            raise RecoveryError("canonical_id must be non-empty")


@dataclass(frozen=True, slots=True)
class ProviderRecoveryPolicy:
    provider: str
    sequence_mode: SequenceMode
    contiguous: bool
    snapshot_required_kinds: tuple[MarketEventKind, ...]
    backup_candidates: tuple[str, ...]
    backup_status: str

    def __post_init__(self) -> None:
        if not self.provider.strip():
            raise RecoveryError("provider policy name must be non-empty")
        if self.sequence_mode is SequenceMode.LEXICOGRAPHIC and self.contiguous:
            raise RecoveryError("lexicographic sequence cannot claim contiguity")
        if len(self.backup_candidates) != len(set(self.backup_candidates)):
            raise RecoveryError("backup candidates must be unique")


@dataclass(frozen=True, slots=True)
class RecoveryPolicy:
    max_attempts: int
    base_backoff_ns: int
    max_backoff_ns: int
    circuit_open_ns: int
    automatic_data_failover: bool
    providers: tuple[ProviderRecoveryPolicy, ...]

    def __post_init__(self) -> None:
        for field, value in (
            ("max_attempts", self.max_attempts),
            ("base_backoff_ns", self.base_backoff_ns),
            ("max_backoff_ns", self.max_backoff_ns),
            ("circuit_open_ns", self.circuit_open_ns),
        ):
            if isinstance(value, bool) or value <= 0:
                raise RecoveryError(f"{field} must be a positive integer")
        if self.base_backoff_ns > self.max_backoff_ns:
            raise RecoveryError("base_backoff_ns must be <= max_backoff_ns")
        names = [item.provider for item in self.providers]
        if len(names) != len(set(names)):
            raise RecoveryError("provider recovery policies must be unique")
        if self.automatic_data_failover:
            raise RecoveryError("automatic data failover is not authorized in P05-F")

    @classmethod
    def from_path(cls, path: Path) -> "RecoveryPolicy":
        try:
            raw_value: object = json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception as exc:
            raise RecoveryError(f"invalid recovery policy JSON: {exc}") from exc

        raw = _mapping(raw_value, field="root")
        if raw.get("schema_version") != "1.0":
            raise RecoveryError("unsupported recovery policy schema_version")

        retry = _mapping(raw.get("retry"), field="retry")
        providers_raw = _sequence(raw.get("providers"), field="providers")
        providers: list[ProviderRecoveryPolicy] = []
        for index, value in enumerate(providers_raw):
            item = _mapping(value, field=f"providers[{index}]")
            provider = _text(item.get("provider"), field=f"providers[{index}].provider")
            mode_text = _text(
                item.get("sequence_mode"),
                field=f"providers[{index}].sequence_mode",
            )
            try:
                mode = SequenceMode(mode_text)
            except ValueError:
                raise RecoveryError(f"unsupported sequence mode: {mode_text}") from None

            kinds_raw = _sequence(
                item.get("snapshot_required_kinds"),
                field=f"providers[{index}].snapshot_required_kinds",
            )
            kinds: list[MarketEventKind] = []
            for kind_value in kinds_raw:
                kind_text = _text(kind_value, field="snapshot_required_kinds[]")
                try:
                    kinds.append(MarketEventKind(kind_text))
                except ValueError:
                    raise RecoveryError(
                        f"unsupported snapshot-required event kind: {kind_text}"
                    ) from None

            backups_raw = _sequence(
                item.get("backup_candidates"),
                field=f"providers[{index}].backup_candidates",
            )
            backups = tuple(_text(value, field="backup_candidates[]") for value in backups_raw)
            providers.append(
                ProviderRecoveryPolicy(
                    provider=provider,
                    sequence_mode=mode,
                    contiguous=_bool(
                        item.get("contiguous"),
                        field=f"providers[{index}].contiguous",
                    ),
                    snapshot_required_kinds=tuple(kinds),
                    backup_candidates=backups,
                    backup_status=_text(
                        item.get("backup_status"),
                        field=f"providers[{index}].backup_status",
                    ),
                )
            )

        return cls(
            max_attempts=_positive_int(retry.get("max_attempts"), field="max_attempts"),
            base_backoff_ns=_positive_int(
                retry.get("base_backoff_ns"),
                field="base_backoff_ns",
            ),
            max_backoff_ns=_positive_int(
                retry.get("max_backoff_ns"),
                field="max_backoff_ns",
            ),
            circuit_open_ns=_positive_int(
                retry.get("circuit_open_ns"),
                field="circuit_open_ns",
            ),
            automatic_data_failover=_bool(
                raw.get("automatic_data_failover"),
                field="automatic_data_failover",
            ),
            providers=tuple(providers),
        )

    def provider(self, name: str) -> ProviderRecoveryPolicy:
        for item in self.providers:
            if item.provider == name:
                return item
        raise RecoveryError(f"unknown recovery provider: {name}")

    def backoff_ns(self, attempt: int) -> int:
        if isinstance(attempt, bool) or attempt <= 0:
            raise RecoveryError("attempt must be a positive integer")
        return min(self.base_backoff_ns * (2 ** (attempt - 1)), self.max_backoff_ns)


@dataclass(frozen=True, slots=True)
class SequenceObservation:
    key: RecoveryKey
    disposition: RecoverySequenceDisposition
    previous_sequence: str | None
    current_sequence: str
    expected_sequence: str | None
    accepted: bool


class SequenceTracker:
    def __init__(self, policy: RecoveryPolicy) -> None:
        self._policy = policy
        self._last: dict[RecoveryKey, str] = {}

    def reset(self, key: RecoveryKey) -> None:
        self._last.pop(key, None)

    @staticmethod
    def key_for(event: CanonicalMarketEvent) -> RecoveryKey:
        return RecoveryKey(
            provider=event.provider,
            canonical_id=event.canonical_id,
            event_kind=event.kind,
        )

    @staticmethod
    def _integer(value: str) -> int:
        if not value.isdigit():
            raise RecoveryError("integer sequence must contain only decimal digits")
        return int(value)

    def observe(self, event: CanonicalMarketEvent) -> SequenceObservation:
        key = self.key_for(event)
        provider_policy = self._policy.provider(key.provider)
        current = event.sequence_id
        if not current:
            raise RecoveryError("sequence_id must be non-empty")

        previous = self._last.get(key)
        if previous is None:
            self._last[key] = current
            return SequenceObservation(
                key=key,
                disposition=RecoverySequenceDisposition.FIRST,
                previous_sequence=None,
                current_sequence=current,
                expected_sequence=None,
                accepted=True,
            )

        if current == previous:
            return SequenceObservation(
                key=key,
                disposition=RecoverySequenceDisposition.DUPLICATE,
                previous_sequence=previous,
                current_sequence=current,
                expected_sequence=None,
                accepted=False,
            )

        expected: str | None = None
        if provider_policy.sequence_mode is SequenceMode.LEXICOGRAPHIC:
            if current < previous:
                disposition = RecoverySequenceDisposition.OUT_OF_ORDER
            else:
                disposition = RecoverySequenceDisposition.ADVANCING
        else:
            previous_number = self._integer(previous)
            current_number = self._integer(current)
            if current_number < previous_number:
                disposition = RecoverySequenceDisposition.OUT_OF_ORDER
            elif provider_policy.contiguous and current_number > previous_number + 1:
                disposition = RecoverySequenceDisposition.GAP
                expected = str(previous_number + 1)
            else:
                disposition = RecoverySequenceDisposition.ADVANCING

        accepted = disposition is RecoverySequenceDisposition.ADVANCING
        if accepted:
            self._last[key] = current

        return SequenceObservation(
            key=key,
            disposition=disposition,
            previous_sequence=previous,
            current_sequence=current,
            expected_sequence=expected,
            accepted=accepted,
        )


@dataclass(slots=True)
class _Runtime:
    state: RecoveryState = RecoveryState.ACTIVE
    attempts: int = 0
    next_retry_at_ns: int | None = None
    circuit_open_until_ns: int | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class RecoverySnapshot:
    key: RecoveryKey
    state: RecoveryState
    attempts: int
    next_retry_at_ns: int | None
    circuit_open_until_ns: int | None
    reason: str | None


class RecoveryCoordinator:
    def __init__(self, policy: RecoveryPolicy) -> None:
        self._policy = policy
        self._sequences = SequenceTracker(policy)
        self._runtime: dict[RecoveryKey, _Runtime] = {}

    @property
    def policy(self) -> RecoveryPolicy:
        return self._policy

    @staticmethod
    def key_for(event: CanonicalMarketEvent) -> RecoveryKey:
        return SequenceTracker.key_for(event)

    def _state(self, key: RecoveryKey) -> _Runtime:
        current = self._runtime.get(key)
        if current is None:
            current = _Runtime()
            self._runtime[key] = current
        return current

    def snapshot(self, key: RecoveryKey) -> RecoverySnapshot:
        current = self._state(key)
        return RecoverySnapshot(
            key=key,
            state=current.state,
            attempts=current.attempts,
            next_retry_at_ns=current.next_retry_at_ns,
            circuit_open_until_ns=current.circuit_open_until_ns,
            reason=current.reason,
        )

    def observe(self, event: CanonicalMarketEvent) -> SequenceObservation:
        key = self.key_for(event)
        current = self._state(key)
        if current.state is RecoveryState.RECOVERY_VALIDATION:
            raise RecoveryPending(
                "use validate_recovery_event while recovery validation is pending"
            )
        observation = self._sequences.observe(event)
        if observation.disposition in (
            RecoverySequenceDisposition.OUT_OF_ORDER,
            RecoverySequenceDisposition.GAP,
        ):
            current.state = RecoveryState.DEGRADED
            current.reason = observation.disposition.value
        return observation

    def schedule_reconnect(self, key: RecoveryKey, *, now_ns: int, reason: str) -> RecoverySnapshot:
        now = _now(now_ns)
        current = self._state(key)
        if current.state is RecoveryState.CIRCUIT_OPEN:
            raise RecoveryError("circuit is open")
        if current.attempts >= self._policy.max_attempts:
            current.state = RecoveryState.CIRCUIT_OPEN
            current.circuit_open_until_ns = now + self._policy.circuit_open_ns
            current.next_retry_at_ns = None
            current.reason = reason
            return self.snapshot(key)

        current.attempts += 1
        current.state = RecoveryState.WAITING_RETRY
        current.next_retry_at_ns = now + self._policy.backoff_ns(current.attempts)
        current.circuit_open_until_ns = None
        current.reason = reason
        return self.snapshot(key)

    def begin_reconnect(self, key: RecoveryKey, *, now_ns: int) -> RecoverySnapshot:
        now = _now(now_ns)
        current = self._state(key)
        if current.state is not RecoveryState.WAITING_RETRY:
            raise RecoveryError("reconnect is not scheduled")
        if current.next_retry_at_ns is None or now < current.next_retry_at_ns:
            raise RecoveryError("reconnect backoff has not elapsed")
        current.state = RecoveryState.RECONNECTING
        current.next_retry_at_ns = None
        return self.snapshot(key)

    def reconnect_failed(self, key: RecoveryKey, *, now_ns: int, reason: str) -> RecoverySnapshot:
        now = _now(now_ns)
        current = self._state(key)
        if current.state is not RecoveryState.RECONNECTING:
            raise RecoveryError("reconnect failure requires RECONNECTING state")
        if current.attempts >= self._policy.max_attempts:
            current.state = RecoveryState.CIRCUIT_OPEN
            current.circuit_open_until_ns = now + self._policy.circuit_open_ns
            current.next_retry_at_ns = None
            current.reason = reason
            return self.snapshot(key)
        return self.schedule_reconnect(key, now_ns=now, reason=reason)

    def reconnect_succeeded(self, key: RecoveryKey) -> RecoverySnapshot:
        current = self._state(key)
        if current.state is not RecoveryState.RECONNECTING:
            raise RecoveryError("reconnect success requires RECONNECTING state")
        self._sequences.reset(key)
        current.state = RecoveryState.RECOVERY_VALIDATION
        current.next_retry_at_ns = None
        current.circuit_open_until_ns = None
        current.reason = "RECOVERY_VALIDATION_REQUIRED"
        return self.snapshot(key)

    def arm_probe_after_circuit(self, key: RecoveryKey, *, now_ns: int) -> RecoverySnapshot:
        now = _now(now_ns)
        current = self._state(key)
        if current.state is not RecoveryState.CIRCUIT_OPEN:
            raise RecoveryError("circuit probe requires CIRCUIT_OPEN state")
        if current.circuit_open_until_ns is None or now < current.circuit_open_until_ns:
            raise RecoveryError("circuit cooldown has not elapsed")
        current.attempts = 1
        current.state = RecoveryState.WAITING_RETRY
        current.next_retry_at_ns = now
        current.circuit_open_until_ns = None
        current.reason = "CIRCUIT_PROBE"
        return self.snapshot(key)

    def validate_recovery_event(self, event: CanonicalMarketEvent) -> SequenceObservation:
        key = self.key_for(event)
        current = self._state(key)
        if current.state is not RecoveryState.RECOVERY_VALIDATION:
            raise RecoveryError("stream is not awaiting recovery validation")

        provider_policy = self._policy.provider(key.provider)
        if key.event_kind in provider_policy.snapshot_required_kinds:
            payload = event.payload
            if not isinstance(payload, OrderBookPayload):
                raise RecoveryPending("recovery requires an order-book snapshot")
            if payload.update_type is not OrderBookUpdateType.SNAPSHOT:
                raise RecoveryPending("recovery requires a fresh order-book SNAPSHOT")

        self._sequences.reset(key)
        observation = self._sequences.observe(event)
        if not observation.accepted:
            raise RecoveryPending("recovery validation event was not accepted")

        current.state = RecoveryState.ACTIVE
        current.attempts = 0
        current.next_retry_at_ns = None
        current.circuit_open_until_ns = None
        current.reason = None
        return observation

    def failover_disposition(
        self,
        primary: RecoveryKey,
        *,
        backup_healthy: bool,
    ) -> FailoverDisposition:
        current = self._state(primary)
        if current.state is RecoveryState.ACTIVE:
            return FailoverDisposition.PRIMARY_ACTIVE
        if backup_healthy:
            return FailoverDisposition.BACKUP_VALIDATION_REQUIRED
        return FailoverDisposition.FAIL_CLOSED
