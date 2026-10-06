from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from typing import Mapping, Sequence, cast


class ReplaySnapshotError(ValueError):
    """Replay snapshot input, policy or lineage state is invalid."""


class ReplaySnapshotIntegrityError(ReplaySnapshotError):
    """Serialized replay snapshot does not match its content identity."""


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,191}$")
_CLOCK_MODES = frozenset({"EVENT_TIME", "RECEIVE_TIME", "CONTROLLED_SIMULATION_CLOCK"})


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ReplaySnapshotError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _object_list(value: object, *, field: str) -> list[object]:
    if not isinstance(value, list):
        raise ReplaySnapshotError(f"{field} must be a list")
    return cast(list[object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReplaySnapshotError(f"{field} must be a non-empty string")
    return value.strip()


def _safe_id(value: object, *, field: str) -> str:
    text = _text(value, field=field)
    if _SAFE_ID.fullmatch(text) is None:
        raise ReplaySnapshotError(f"{field} contains unsafe characters")
    return text


def _sha256_text(value: object, *, field: str) -> str:
    text = _text(value, field=field)
    if _SHA256.fullmatch(text) is None:
        raise ReplaySnapshotError(f"{field} must be lowercase SHA-256")
    return text


def _non_negative_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ReplaySnapshotError(f"{field} must be a non-negative integer")
    return value


def _positive_int(value: object, *, field: str) -> int:
    number = _non_negative_int(value, field=field)
    if number <= 0:
        raise ReplaySnapshotError(f"{field} must be a positive integer")
    return number


def _optional_non_negative_int(value: object, *, field: str) -> int | None:
    if value is None:
        return None
    return _non_negative_int(value, field=field)


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


@dataclass(frozen=True, slots=True)
class ReplaySnapshotPolicy:
    allowed_clock_modes: frozenset[str]
    max_dataset_refs: int
    max_feature_refs: int
    max_vintage_refs: int
    max_snapshot_bytes: int
    production_replay_storage_vendor: str

    @classmethod
    def from_path(cls, path: Path) -> "ReplaySnapshotPolicy":
        try:
            raw_value: object = json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception as exc:
            raise ReplaySnapshotError(f"invalid replay-snapshot policy JSON: {exc}") from exc
        raw = _mapping(raw_value, field="root")
        if raw.get("schema_version") != "1.0":
            raise ReplaySnapshotError("unsupported replay-snapshot policy schema_version")
        if raw.get("mode") != "REFERENCE_FILESYSTEM_CONTENT_ADDRESSED_REPLAY_SNAPSHOTS":
            raise ReplaySnapshotError("unsupported replay-snapshot mode")
        if raw.get("anti_lookahead_rule") != "INFORMATION_TIME_NOT_AFTER_SIMULATED_DECISION_TIME":
            raise ReplaySnapshotError("unsupported anti-lookahead rule")
        raw_modes = _object_list(raw.get("allowed_clock_modes"), field="allowed_clock_modes")
        modes = frozenset(_text(item, field="clock_mode") for item in raw_modes)
        if modes != _CLOCK_MODES:
            raise ReplaySnapshotError("allowed_clock_modes must match canonical replay clock modes")
        if raw.get("network_required") is not False:
            raise ReplaySnapshotError("reference replay snapshots must not require network")
        if raw.get("credentials_required") is not False:
            raise ReplaySnapshotError("reference replay snapshots must not require credentials")
        return cls(
            allowed_clock_modes=modes,
            max_dataset_refs=_positive_int(raw.get("max_dataset_refs"), field="max_dataset_refs"),
            max_feature_refs=_positive_int(raw.get("max_feature_refs"), field="max_feature_refs"),
            max_vintage_refs=_positive_int(raw.get("max_vintage_refs"), field="max_vintage_refs"),
            max_snapshot_bytes=_positive_int(raw.get("max_snapshot_bytes"), field="max_snapshot_bytes"),
            production_replay_storage_vendor=_text(
                raw.get("production_replay_storage_vendor"),
                field="production_replay_storage_vendor",
            ),
        )


@dataclass(frozen=True, slots=True)
class ReplayDatasetRef:
    dataset_name: str
    dataset_version: str
    schema_version: str
    window_start_ns: int
    window_end_ns: int
    membership_root_sha256: str
    rights_class: str

    def __post_init__(self) -> None:
        _safe_id(self.dataset_name, field="dataset_name")
        _sha256_text(self.dataset_version, field="dataset_version")
        _text(self.schema_version, field="schema_version")
        start = _non_negative_int(self.window_start_ns, field="window_start_ns")
        end = _non_negative_int(self.window_end_ns, field="window_end_ns")
        if end <= start:
            raise ReplaySnapshotError("dataset window_end_ns must be greater than window_start_ns")
        _sha256_text(self.membership_root_sha256, field="membership_root_sha256")
        _text(self.rights_class, field="rights_class")

    def payload(self) -> dict[str, object]:
        return {
            "dataset_name": self.dataset_name,
            "dataset_version": self.dataset_version,
            "schema_version": self.schema_version,
            "window_start_ns": self.window_start_ns,
            "window_end_ns": self.window_end_ns,
            "membership_root_sha256": self.membership_root_sha256,
            "rights_class": self.rights_class,
        }

    @classmethod
    def from_mapping(cls, value: object) -> "ReplayDatasetRef":
        raw = _mapping(value, field="dataset_ref")
        return cls(
            dataset_name=_safe_id(raw.get("dataset_name"), field="dataset_name"),
            dataset_version=_sha256_text(raw.get("dataset_version"), field="dataset_version"),
            schema_version=_text(raw.get("schema_version"), field="schema_version"),
            window_start_ns=_non_negative_int(raw.get("window_start_ns"), field="window_start_ns"),
            window_end_ns=_non_negative_int(raw.get("window_end_ns"), field="window_end_ns"),
            membership_root_sha256=_sha256_text(
                raw.get("membership_root_sha256"),
                field="membership_root_sha256",
            ),
            rights_class=_text(raw.get("rights_class"), field="rights_class"),
        )


@dataclass(frozen=True, slots=True)
class ReplayFeatureRef:
    definition_id: str
    materialization_id: str
    entity_id: str
    event_time_ns: int
    as_of_time_ns: int
    quality_evidence_sha256: str

    def __post_init__(self) -> None:
        _sha256_text(self.definition_id, field="definition_id")
        _sha256_text(self.materialization_id, field="materialization_id")
        _safe_id(self.entity_id, field="entity_id")
        event = _non_negative_int(self.event_time_ns, field="event_time_ns")
        as_of = _non_negative_int(self.as_of_time_ns, field="as_of_time_ns")
        if event > as_of:
            raise ReplaySnapshotError("feature event_time_ns cannot exceed as_of_time_ns")
        _sha256_text(self.quality_evidence_sha256, field="quality_evidence_sha256")

    def payload(self) -> dict[str, object]:
        return {
            "definition_id": self.definition_id,
            "materialization_id": self.materialization_id,
            "entity_id": self.entity_id,
            "event_time_ns": self.event_time_ns,
            "as_of_time_ns": self.as_of_time_ns,
            "quality_evidence_sha256": self.quality_evidence_sha256,
        }

    @classmethod
    def from_mapping(cls, value: object) -> "ReplayFeatureRef":
        raw = _mapping(value, field="feature_ref")
        return cls(
            definition_id=_sha256_text(raw.get("definition_id"), field="definition_id"),
            materialization_id=_sha256_text(
                raw.get("materialization_id"),
                field="materialization_id",
            ),
            entity_id=_safe_id(raw.get("entity_id"), field="entity_id"),
            event_time_ns=_non_negative_int(raw.get("event_time_ns"), field="event_time_ns"),
            as_of_time_ns=_non_negative_int(raw.get("as_of_time_ns"), field="as_of_time_ns"),
            quality_evidence_sha256=_sha256_text(
                raw.get("quality_evidence_sha256"),
                field="quality_evidence_sha256",
            ),
        )


@dataclass(frozen=True, slots=True)
class ReplayVintageRef:
    vintage_id: str
    series_id: str
    observation_time_ns: int
    release_time_ns: int
    observed_at_ns: int

    def __post_init__(self) -> None:
        _sha256_text(self.vintage_id, field="vintage_id")
        _safe_id(self.series_id, field="series_id")
        _non_negative_int(self.observation_time_ns, field="observation_time_ns")
        release = _non_negative_int(self.release_time_ns, field="release_time_ns")
        observed = _non_negative_int(self.observed_at_ns, field="observed_at_ns")
        if observed < release:
            raise ReplaySnapshotError("vintage observed_at_ns cannot precede release_time_ns")

    def payload(self) -> dict[str, object]:
        return {
            "vintage_id": self.vintage_id,
            "series_id": self.series_id,
            "observation_time_ns": self.observation_time_ns,
            "release_time_ns": self.release_time_ns,
            "observed_at_ns": self.observed_at_ns,
        }

    @classmethod
    def from_mapping(cls, value: object) -> "ReplayVintageRef":
        raw = _mapping(value, field="vintage_ref")
        return cls(
            vintage_id=_sha256_text(raw.get("vintage_id"), field="vintage_id"),
            series_id=_safe_id(raw.get("series_id"), field="series_id"),
            observation_time_ns=_non_negative_int(
                raw.get("observation_time_ns"),
                field="observation_time_ns",
            ),
            release_time_ns=_non_negative_int(raw.get("release_time_ns"), field="release_time_ns"),
            observed_at_ns=_non_negative_int(raw.get("observed_at_ns"), field="observed_at_ns"),
        )


@dataclass(frozen=True, slots=True)
class ReplayView:
    snapshot_id: str
    decision_time_ns: int
    dataset_refs: tuple[ReplayDatasetRef, ...]
    feature_refs: tuple[ReplayFeatureRef, ...]
    vintage_refs: tuple[ReplayVintageRef, ...]


@dataclass(frozen=True, slots=True)
class ReplaySnapshot:
    replay_start_ns: int
    replay_end_ns: int
    snapshot_cutoff_ns: int
    clock_mode: str
    scope_ids: tuple[str, ...]
    dataset_refs: tuple[ReplayDatasetRef, ...]
    feature_refs: tuple[ReplayFeatureRef, ...]
    vintage_refs: tuple[ReplayVintageRef, ...]
    quality_rule_versions: tuple[str, ...]
    config_sha256: str
    code_artifact_sha256: str
    rights_class: str
    stochastic_seed: int | None
    stochastic_version: str | None
    snapshot_id: str

    @staticmethod
    def _canonicalize_ids(values: Sequence[str], *, field: str) -> tuple[str, ...]:
        canonical = tuple(sorted({_safe_id(value, field=field) for value in values}))
        if len(canonical) != len(tuple(values)):
            raise ReplaySnapshotError(f"{field} values must be unique")
        return canonical

    @classmethod
    def build(
        cls,
        *,
        replay_start_ns: int,
        replay_end_ns: int,
        snapshot_cutoff_ns: int,
        clock_mode: str,
        scope_ids: Sequence[str],
        dataset_refs: Sequence[ReplayDatasetRef],
        feature_refs: Sequence[ReplayFeatureRef],
        vintage_refs: Sequence[ReplayVintageRef],
        quality_rule_versions: Sequence[str],
        config_sha256: str,
        code_artifact_sha256: str,
        rights_class: str,
        policy: ReplaySnapshotPolicy,
        stochastic_seed: int | None = None,
        stochastic_version: str | None = None,
    ) -> "ReplaySnapshot":
        start = _non_negative_int(replay_start_ns, field="replay_start_ns")
        end = _non_negative_int(replay_end_ns, field="replay_end_ns")
        cutoff = _non_negative_int(snapshot_cutoff_ns, field="snapshot_cutoff_ns")
        if end <= start:
            raise ReplaySnapshotError("replay_end_ns must be greater than replay_start_ns")
        if cutoff < start:
            raise ReplaySnapshotError("snapshot_cutoff_ns cannot precede replay_start_ns")
        mode = _text(clock_mode, field="clock_mode")
        if mode not in policy.allowed_clock_modes:
            raise ReplaySnapshotError("unsupported replay clock_mode")

        scopes = cls._canonicalize_ids(scope_ids, field="scope_id")
        if not scopes:
            raise ReplaySnapshotError("replay snapshot requires at least one scope_id")

        datasets = tuple(sorted(dataset_refs, key=lambda item: (item.dataset_name, item.dataset_version)))
        features = tuple(
            sorted(
                feature_refs,
                key=lambda item: (
                    item.definition_id,
                    item.materialization_id,
                    item.entity_id,
                ),
            )
        )
        vintages = tuple(
            sorted(
                vintage_refs,
                key=lambda item: (
                    item.series_id,
                    item.observation_time_ns,
                    item.release_time_ns,
                    item.observed_at_ns,
                    item.vintage_id,
                ),
            )
        )
        if not datasets:
            raise ReplaySnapshotError("replay snapshot requires at least one dataset_ref")
        if len(datasets) > policy.max_dataset_refs:
            raise ReplaySnapshotError("dataset_ref count exceeds policy")
        if len(features) > policy.max_feature_refs:
            raise ReplaySnapshotError("feature_ref count exceeds policy")
        if len(vintages) > policy.max_vintage_refs:
            raise ReplaySnapshotError("vintage_ref count exceeds policy")

        dataset_keys = [(item.dataset_name, item.dataset_version) for item in datasets]
        feature_keys = [
            (item.definition_id, item.materialization_id, item.entity_id)
            for item in features
        ]
        vintage_keys = [
            (item.series_id, item.observation_time_ns, item.vintage_id)
            for item in vintages
        ]
        if len(dataset_keys) != len(set(dataset_keys)):
            raise ReplaySnapshotError("duplicate replay dataset reference")
        if len(feature_keys) != len(set(feature_keys)):
            raise ReplaySnapshotError("duplicate replay feature reference")
        if len(vintage_keys) != len(set(vintage_keys)):
            raise ReplaySnapshotError("duplicate replay vintage reference")

        for feature in features:
            if feature.as_of_time_ns > cutoff:
                raise ReplaySnapshotError("feature information exceeds snapshot cutoff")
        for vintage in vintages:
            if vintage.release_time_ns > cutoff or vintage.observed_at_ns > cutoff:
                raise ReplaySnapshotError("vintage information exceeds snapshot cutoff")

        quality_versions = cls._canonicalize_ids(
            quality_rule_versions,
            field="quality_rule_version",
        )
        config_hash = _sha256_text(config_sha256, field="config_sha256")
        code_hash = _sha256_text(code_artifact_sha256, field="code_artifact_sha256")
        rights = _text(rights_class, field="rights_class")
        seed = _optional_non_negative_int(stochastic_seed, field="stochastic_seed")
        if (seed is None) != (stochastic_version is None):
            raise ReplaySnapshotError("stochastic_seed and stochastic_version must be supplied together")
        stochastic = (
            None if stochastic_version is None else _text(stochastic_version, field="stochastic_version")
        )

        body: dict[str, object] = {
            "schema_version": "1.0",
            "replay_start_ns": start,
            "replay_end_ns": end,
            "snapshot_cutoff_ns": cutoff,
            "clock_mode": mode,
            "scope_ids": list(scopes),
            "dataset_refs": [item.payload() for item in datasets],
            "feature_refs": [item.payload() for item in features],
            "vintage_refs": [item.payload() for item in vintages],
            "quality_rule_versions": list(quality_versions),
            "config_sha256": config_hash,
            "code_artifact_sha256": code_hash,
            "rights_class": rights,
            "stochastic_seed": seed,
            "stochastic_version": stochastic,
            "anti_lookahead_rule": "INFORMATION_TIME_NOT_AFTER_SIMULATED_DECISION_TIME",
        }
        snapshot_id = hashlib.sha256(_canonical_bytes(body)).hexdigest()
        snapshot = cls(
            replay_start_ns=start,
            replay_end_ns=end,
            snapshot_cutoff_ns=cutoff,
            clock_mode=mode,
            scope_ids=scopes,
            dataset_refs=datasets,
            feature_refs=features,
            vintage_refs=vintages,
            quality_rule_versions=quality_versions,
            config_sha256=config_hash,
            code_artifact_sha256=code_hash,
            rights_class=rights,
            stochastic_seed=seed,
            stochastic_version=stochastic,
            snapshot_id=snapshot_id,
        )
        if len(snapshot.to_bytes()) > policy.max_snapshot_bytes:
            raise ReplaySnapshotError("serialized replay snapshot exceeds policy")
        return snapshot

    def body_payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "replay_start_ns": self.replay_start_ns,
            "replay_end_ns": self.replay_end_ns,
            "snapshot_cutoff_ns": self.snapshot_cutoff_ns,
            "clock_mode": self.clock_mode,
            "scope_ids": list(self.scope_ids),
            "dataset_refs": [item.payload() for item in self.dataset_refs],
            "feature_refs": [item.payload() for item in self.feature_refs],
            "vintage_refs": [item.payload() for item in self.vintage_refs],
            "quality_rule_versions": list(self.quality_rule_versions),
            "config_sha256": self.config_sha256,
            "code_artifact_sha256": self.code_artifact_sha256,
            "rights_class": self.rights_class,
            "stochastic_seed": self.stochastic_seed,
            "stochastic_version": self.stochastic_version,
            "anti_lookahead_rule": "INFORMATION_TIME_NOT_AFTER_SIMULATED_DECISION_TIME",
        }

    def to_bytes(self) -> bytes:
        payload = self.body_payload() | {"snapshot_id": self.snapshot_id}
        return (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")

    def view_at(self, decision_time_ns: int) -> ReplayView:
        decision = _non_negative_int(decision_time_ns, field="decision_time_ns")
        if decision < self.replay_start_ns or decision >= self.replay_end_ns:
            raise ReplaySnapshotError("decision_time_ns must be inside replay half-open window")
        if decision > self.snapshot_cutoff_ns:
            raise ReplaySnapshotError("decision_time_ns cannot exceed snapshot cutoff")
        datasets = tuple(
            item
            for item in self.dataset_refs
            if item.window_start_ns <= decision < item.window_end_ns
        )
        features = tuple(
            item for item in self.feature_refs if item.as_of_time_ns <= decision
        )
        vintages = tuple(
            item
            for item in self.vintage_refs
            if item.release_time_ns <= decision and item.observed_at_ns <= decision
        )
        return ReplayView(
            snapshot_id=self.snapshot_id,
            decision_time_ns=decision,
            dataset_refs=datasets,
            feature_refs=features,
            vintage_refs=vintages,
        )

    @classmethod
    def from_bytes(cls, data: bytes, policy: ReplaySnapshotPolicy) -> "ReplaySnapshot":
        if not data:
            raise ReplaySnapshotIntegrityError("replay snapshot bytes must be non-empty")
        if len(data) > policy.max_snapshot_bytes:
            raise ReplaySnapshotIntegrityError("replay snapshot bytes exceed policy")
        try:
            raw_value: object = json.loads(data.decode("utf-8"))
        except Exception as exc:
            raise ReplaySnapshotIntegrityError(f"invalid replay snapshot JSON: {exc}") from exc
        raw = _mapping(raw_value, field="root")
        if raw.get("schema_version") != "1.0":
            raise ReplaySnapshotIntegrityError("unsupported replay snapshot schema_version")
        if raw.get("anti_lookahead_rule") != "INFORMATION_TIME_NOT_AFTER_SIMULATED_DECISION_TIME":
            raise ReplaySnapshotIntegrityError("replay anti-lookahead rule mismatch")

        dataset_values = _object_list(raw.get("dataset_refs"), field="dataset_refs")
        feature_values = _object_list(raw.get("feature_refs"), field="feature_refs")
        vintage_values = _object_list(raw.get("vintage_refs"), field="vintage_refs")
        scope_values = _object_list(raw.get("scope_ids"), field="scope_ids")
        quality_values = _object_list(raw.get("quality_rule_versions"), field="quality_rule_versions")

        snapshot = cls.build(
            replay_start_ns=_non_negative_int(raw.get("replay_start_ns"), field="replay_start_ns"),
            replay_end_ns=_non_negative_int(raw.get("replay_end_ns"), field="replay_end_ns"),
            snapshot_cutoff_ns=_non_negative_int(
                raw.get("snapshot_cutoff_ns"),
                field="snapshot_cutoff_ns",
            ),
            clock_mode=_text(raw.get("clock_mode"), field="clock_mode"),
            scope_ids=tuple(_safe_id(item, field="scope_id") for item in scope_values),
            dataset_refs=tuple(ReplayDatasetRef.from_mapping(item) for item in dataset_values),
            feature_refs=tuple(ReplayFeatureRef.from_mapping(item) for item in feature_values),
            vintage_refs=tuple(ReplayVintageRef.from_mapping(item) for item in vintage_values),
            quality_rule_versions=tuple(
                _safe_id(item, field="quality_rule_version") for item in quality_values
            ),
            config_sha256=_sha256_text(raw.get("config_sha256"), field="config_sha256"),
            code_artifact_sha256=_sha256_text(
                raw.get("code_artifact_sha256"),
                field="code_artifact_sha256",
            ),
            rights_class=_text(raw.get("rights_class"), field="rights_class"),
            stochastic_seed=_optional_non_negative_int(
                raw.get("stochastic_seed"),
                field="stochastic_seed",
            ),
            stochastic_version=(
                None
                if raw.get("stochastic_version") is None
                else _text(raw.get("stochastic_version"), field="stochastic_version")
            ),
            policy=policy,
        )
        declared = _sha256_text(raw.get("snapshot_id"), field="snapshot_id")
        if declared != snapshot.snapshot_id:
            raise ReplaySnapshotIntegrityError("replay snapshot identity mismatch")
        if snapshot.to_bytes() != data:
            raise ReplaySnapshotIntegrityError("replay snapshot bytes are not canonical")
        return snapshot


@dataclass(frozen=True, slots=True)
class StoredReplaySnapshot:
    relative_path: str
    snapshot_id: str
    created: bool


class FilesystemReplaySnapshotStore:
    """Offline content-addressed snapshot store; not a production replay vendor."""

    def __init__(self, root: Path, policy: ReplaySnapshotPolicy) -> None:
        self._root = Path(root)
        self._policy = policy

    def save(self, snapshot: ReplaySnapshot) -> StoredReplaySnapshot:
        snapshot_id = _sha256_text(snapshot.snapshot_id, field="snapshot_id")
        relative = PurePosixPath("replay-snapshots") / f"{snapshot_id}.json"
        target = self._root / Path(*relative.parts)
        payload = snapshot.to_bytes()
        if len(payload) > self._policy.max_snapshot_bytes:
            raise ReplaySnapshotError("serialized replay snapshot exceeds policy")
        if target.exists():
            if target.read_bytes() != payload:
                raise ReplaySnapshotIntegrityError("existing content-addressed replay snapshot differs")
            ReplaySnapshot.from_bytes(payload, self._policy)
            return StoredReplaySnapshot(str(relative), snapshot_id, False)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(".json.tmp")
        temporary.write_bytes(payload)
        temporary.replace(target)
        return StoredReplaySnapshot(str(relative), snapshot_id, True)

    def load(self, snapshot_id: str) -> ReplaySnapshot:
        content_id = _sha256_text(snapshot_id, field="snapshot_id")
        target = self._root / "replay-snapshots" / f"{content_id}.json"
        if not target.is_file():
            raise ReplaySnapshotIntegrityError("replay snapshot does not exist")
        snapshot = ReplaySnapshot.from_bytes(target.read_bytes(), self._policy)
        if snapshot.snapshot_id != content_id:
            raise ReplaySnapshotIntegrityError("stored replay snapshot path identity mismatch")
        return snapshot
