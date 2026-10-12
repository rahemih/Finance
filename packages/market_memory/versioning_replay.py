from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Mapping, cast

from packages.historical_data.replay_snapshot import (
    ReplaySnapshot,
    ReplaySnapshotError,
)

from .knowledge_graph import KnowledgeGraphSnapshot


class MarketMemoryReplayError(ValueError):
    """P12-H versioning or replay evidence violates governed invariants."""


class MarketMemoryReplayMismatch(MarketMemoryReplayError):
    """Two supposedly equivalent market-memory replays do not match."""


_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MarketMemoryReplayError(f"{field} must be non-empty text")
    return value.strip()


def _sha256(value: object, *, field: str) -> str:
    text = _text(value, field=field)
    if _SHA256.fullmatch(text) is None:
        raise MarketMemoryReplayError(f"{field} must be lowercase SHA-256")
    return text


def _non_negative_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise MarketMemoryReplayError(f"{field} must be non-negative integer")
    return value


def _string_tuple(value: object, *, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise MarketMemoryReplayError(f"{field} must be non-empty list")
    normalized = tuple(str(item).strip().upper() for item in cast(list[object], value))
    if any(not item for item in normalized) or len(normalized) != len(set(normalized)):
        raise MarketMemoryReplayError(f"{field} must contain unique non-empty values")
    return normalized


def _canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise MarketMemoryReplayError(f"value is not canonical JSON: {exc}") from exc


@dataclass(frozen=True, slots=True)
class MarketMemoryReplayPolicy:
    required_policy_components: tuple[str, ...]
    required_replay_output_components: tuple[str, ...]
    hash_algorithm: str
    require_p06_replay_snapshot: bool
    anti_lookahead_owner: str
    end_to_end_decision_replay_owner: str
    production_memory_version_store_vendor: str
    canonical_tests_network_required: bool
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "MarketMemoryReplayPolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw_value, Mapping):
            raise MarketMemoryReplayError("policy root must be object")
        raw = cast(Mapping[str, object], raw_value)
        if raw.get("schema_version") != "1.0" or raw.get("mode") != "P12_MARKET_MEMORY_VERSIONED_REPLAY":
            raise MarketMemoryReplayError("unsupported P12-H policy")
        policy_components = _string_tuple(raw.get("required_policy_components"), field="required_policy_components")
        expected_policy = {
            "P12_A_KNOWLEDGE_GRAPH",
            "P12_B_CONDITIONAL_CORRELATION",
            "P12_C_LEAD_LAG",
            "P12_D_EVENT_STUDY",
            "P12_E_HISTORICAL_ANALOG",
            "P12_F_SEASONALITY",
            "P12_G_ATTRIBUTION_GUARDRAIL",
        }
        if set(policy_components) != expected_policy:
            raise MarketMemoryReplayError("required P12 policy component set drift")
        output_components = _string_tuple(
            raw.get("required_replay_output_components"),
            field="required_replay_output_components",
        )
        expected_outputs = expected_policy - {"P12_A_KNOWLEDGE_GRAPH"}
        if set(output_components) != expected_outputs:
            raise MarketMemoryReplayError("required replay output component set drift")
        if raw.get("hash_algorithm") != "SHA256":
            raise MarketMemoryReplayError("P12-H hash algorithm must be SHA256")
        if raw.get("require_p06_replay_snapshot") is not True:
            raise MarketMemoryReplayError("P12-H must bind canonical P06-G replay snapshot")
        if raw.get("anti_lookahead_owner") != "P06_G_REPLAY_SNAPSHOT":
            raise MarketMemoryReplayError("P06-G must remain anti-lookahead owner")
        if raw.get("end_to_end_decision_replay_owner") != "P19":
            raise MarketMemoryReplayError("P19 must remain end-to-end decision replay owner")
        if raw.get("production_memory_version_store_vendor") != "NOT_SELECTED":
            raise MarketMemoryReplayError("production memory-version store vendor cannot be selected in P12-H")
        if raw.get("canonical_tests_network_required") is not False:
            raise MarketMemoryReplayError("canonical P12-H tests must remain offline")
        if raw.get("live_trading") != "DISABLED" or raw.get("auto_trading") != "DISABLED":
            raise MarketMemoryReplayError("P12-H cannot enable trading")
        return cls(
            required_policy_components=policy_components,
            required_replay_output_components=output_components,
            hash_algorithm="SHA256",
            require_p06_replay_snapshot=True,
            anti_lookahead_owner="P06_G_REPLAY_SNAPSHOT",
            end_to_end_decision_replay_owner="P19",
            production_memory_version_store_vendor="NOT_SELECTED",
            canonical_tests_network_required=False,
            live_trading="DISABLED",
            auto_trading="DISABLED",
        )


@dataclass(frozen=True, slots=True)
class MarketMemoryVersionBundle:
    as_of_ns: int
    replay_snapshot_id: str
    graph_snapshot_id: str
    component_policy_sha256: tuple[tuple[str, str], ...]
    graph_source_dataset_versions: tuple[str, ...]
    replay_dataset_versions: tuple[str, ...]
    graph_provenance_sha256: tuple[str, ...]
    version_id: str

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "as_of_ns": self.as_of_ns,
            "replay_snapshot_id": self.replay_snapshot_id,
            "graph_snapshot_id": self.graph_snapshot_id,
            "component_policy_sha256": [
                {"component": name, "sha256": digest}
                for name, digest in self.component_policy_sha256
            ],
            "graph_source_dataset_versions": list(self.graph_source_dataset_versions),
            "replay_dataset_versions": list(self.replay_dataset_versions),
            "graph_provenance_sha256": list(self.graph_provenance_sha256),
            "version_id": self.version_id,
        }


@dataclass(frozen=True, slots=True)
class MarketMemoryReplayRecord:
    version_id: str
    decision_time_ns: int
    component_output_sha256: tuple[tuple[str, str], ...]
    record_id: str

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "version_id": self.version_id,
            "decision_time_ns": self.decision_time_ns,
            "component_output_sha256": [
                {"component": name, "sha256": digest}
                for name, digest in self.component_output_sha256
            ],
            "record_id": self.record_id,
        }


def build_market_memory_version_bundle(
    *,
    as_of_ns: int,
    replay_snapshot: ReplaySnapshot,
    graph_snapshot: KnowledgeGraphSnapshot,
    component_policy_sha256: Mapping[str, str],
    policy: MarketMemoryReplayPolicy,
) -> MarketMemoryVersionBundle:
    as_of = _non_negative_int(as_of_ns, field="as_of_ns")
    if not policy.require_p06_replay_snapshot:
        raise MarketMemoryReplayError("P06-G replay snapshot binding is required")
    try:
        replay_view = replay_snapshot.view_at(as_of)
    except ReplaySnapshotError as exc:
        raise MarketMemoryReplayError(f"P06-G anti-lookahead replay view rejected as_of_ns: {exc}") from exc
    if not replay_view.dataset_refs:
        raise MarketMemoryReplayError("P06-G replay view has no dataset context at as_of_ns")

    replay_id = _sha256(replay_snapshot.snapshot_id, field="replay_snapshot_id")
    graph_id = _sha256(graph_snapshot.snapshot_id, field="graph_snapshot_id")
    for edge in graph_snapshot.edges:
        if edge.valid_to_ns > as_of + 1:
            raise MarketMemoryReplayError("graph evidence window extends beyond replay as_of_ns")

    normalized_policies = tuple(sorted(
        (
            _text(name, field="policy_component").upper(),
            _sha256(digest, field="policy_sha256"),
        )
        for name, digest in component_policy_sha256.items()
    ))
    names = tuple(name for name, _ in normalized_policies)
    if len(names) != len(set(names)):
        raise MarketMemoryReplayError("duplicate policy component")
    if set(names) != set(policy.required_policy_components):
        raise MarketMemoryReplayError("component policy set must exactly match P12-A..P12-G")

    graph_versions = tuple(sorted({
        version
        for edge in graph_snapshot.edges
        for version in edge.source_dataset_versions
    }))
    graph_provenance = tuple(sorted({
        digest
        for edge in graph_snapshot.edges
        for digest in edge.provenance_sha256
    }))
    if graph_snapshot.edges and (not graph_versions or not graph_provenance):
        raise MarketMemoryReplayError("graph lineage is incomplete")
    replay_versions = tuple(sorted({item.dataset_version for item in replay_view.dataset_refs}))
    if not replay_versions:
        raise MarketMemoryReplayError("replay dataset lineage is empty")

    body: dict[str, object] = {
        "schema_version": "1.0",
        "as_of_ns": as_of,
        "replay_snapshot_id": replay_id,
        "graph_snapshot_id": graph_id,
        "component_policy_sha256": [
            {"component": name, "sha256": digest}
            for name, digest in normalized_policies
        ],
        "graph_source_dataset_versions": list(graph_versions),
        "replay_dataset_versions": list(replay_versions),
        "graph_provenance_sha256": list(graph_provenance),
    }
    version_id = hashlib.sha256(_canonical_bytes(body)).hexdigest()
    return MarketMemoryVersionBundle(
        as_of_ns=as_of,
        replay_snapshot_id=replay_id,
        graph_snapshot_id=graph_id,
        component_policy_sha256=normalized_policies,
        graph_source_dataset_versions=graph_versions,
        replay_dataset_versions=replay_versions,
        graph_provenance_sha256=graph_provenance,
        version_id=version_id,
    )


def build_market_memory_replay_record(
    *,
    bundle: MarketMemoryVersionBundle,
    component_outputs: Mapping[str, object],
    policy: MarketMemoryReplayPolicy,
) -> MarketMemoryReplayRecord:
    normalized_outputs = tuple(sorted(
        (
            _text(name, field="replay_component").upper(),
            hashlib.sha256(_canonical_bytes(value)).hexdigest(),
        )
        for name, value in component_outputs.items()
    ))
    names = tuple(name for name, _ in normalized_outputs)
    if len(names) != len(set(names)):
        raise MarketMemoryReplayError("duplicate replay output component")
    if set(names) != set(policy.required_replay_output_components):
        raise MarketMemoryReplayError("replay output set must exactly match P12-B..P12-G")
    version_id = _sha256(bundle.version_id, field="version_id")
    body: dict[str, object] = {
        "schema_version": "1.0",
        "version_id": version_id,
        "decision_time_ns": bundle.as_of_ns,
        "component_output_sha256": [
            {"component": name, "sha256": digest}
            for name, digest in normalized_outputs
        ],
    }
    record_id = hashlib.sha256(_canonical_bytes(body)).hexdigest()
    return MarketMemoryReplayRecord(
        version_id=version_id,
        decision_time_ns=bundle.as_of_ns,
        component_output_sha256=normalized_outputs,
        record_id=record_id,
    )


def assert_market_memory_replay_equivalent(
    expected: MarketMemoryReplayRecord,
    actual: MarketMemoryReplayRecord,
) -> None:
    if expected.version_id != actual.version_id:
        raise MarketMemoryReplayMismatch("market-memory version_id mismatch")
    if expected.decision_time_ns != actual.decision_time_ns:
        raise MarketMemoryReplayMismatch("market-memory decision_time_ns mismatch")
    if expected.component_output_sha256 != actual.component_output_sha256:
        raise MarketMemoryReplayMismatch("market-memory component output digest mismatch")
    if expected.record_id != actual.record_id:
        raise MarketMemoryReplayMismatch("market-memory replay record identity mismatch")
