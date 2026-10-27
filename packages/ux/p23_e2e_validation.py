from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import cast


class P23E2EValidationError(ValueError):
    """P23-I fail-closed reference E2E validation failure."""


EXPECTED_MANIFESTS = (
    ("P23-A", "FIN-P23-WA-001", "docs/18-ux/p23-a-information-architecture.json"),
    ("P23-B", "FIN-P23-WB-001", "docs/18-ux/p23-b-design-system.json"),
    ("P23-C", "FIN-P23-WC-001", "config/ux/operational-screens.json"),
    ("P23-D", "FIN-P23-WD-001", "config/ux/learning-mode-glossary.json"),
    ("P23-E", "FIN-P23-WE-001", "config/ux/team-collaboration.json"),
    ("P23-F", "FIN-P23-WF-001", "docs/18-ux/p23-f-notification-engine.json"),
    ("P23-G", "FIN-P23-WG-001", "docs/18-ux/p23-g-accessibility-responsive-performance.json"),
    ("P23-H", "FIN-P23-WH-001", "docs/18-ux/p23-h-dangerous-action-security-ux.json"),
)
EXPECTED_JOURNEYS = (
    ("MARKET_DECISION_REVIEW", ("dashboard", "markets", "opportunities", "reports")),
    ("DEMO_LEARNING_REVIEW", ("dashboard", "demo", "research", "reports")),
    ("OPERATIONS_HEALTH_REVIEW", ("dashboard", "system", "reports")),
    ("EXPLANATION_GLOSSARY_REVIEW", ("opportunities", "glossary", "reports")),
    ("SECURITY_SETTINGS_REVIEW", ("settings", "system", "reports")),
)
FORBIDDEN_TRUE_SAFETY_KEYS = (
    "credential_access",
    "permission_mutation",
    "network_mutation",
    "execution_authority_mutation",
    "external_order_authority",
    "runtime_state_mutation",
    "remediation_authority",
    "production_activation",
)
HEX_CHARS = frozenset("0123456789abcdef")


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _object(value: object, *, field: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise P23E2EValidationError(f"{field} must be an object")
    raw = cast(dict[object, object], value)
    result: dict[str, object] = {}
    for key, item in raw.items():
        if not isinstance(key, str):
            raise P23E2EValidationError(f"{field} keys must be strings")
        result[key] = item
    return result


def _list(value: object, *, field: str) -> list[object]:
    if not isinstance(value, list):
        raise P23E2EValidationError(f"{field} must be a list")
    return cast(list[object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise P23E2EValidationError(f"{field} must be non-empty text")
    return value


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise P23E2EValidationError(f"{field} must be a positive integer")
    return value


def _sha256_hex(value: object, *, field: str) -> str:
    text = _text(value, field=field)
    if len(text) != 64 or any(ch not in HEX_CHARS for ch in text):
        raise P23E2EValidationError(f"{field} must be lowercase sha256 hex")
    return text


@dataclass(frozen=True, slots=True)
class UpstreamValidation:
    workstream: str
    task_id: str
    path: str
    manifest_sha256: str


@dataclass(frozen=True, slots=True)
class P23E2EValidation:
    upstream: tuple[UpstreamValidation, ...]
    journeys: tuple[tuple[str, tuple[str, ...]], ...]
    canonical_surfaces: tuple[str, ...]
    safety: dict[str, object]

    @classmethod
    def from_root(cls, policy_path: Path, root: Path) -> "P23E2EValidation":
        try:
            policy_value: object = json.loads(policy_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise P23E2EValidationError(f"invalid P23-I policy JSON: {exc}") from exc
        policy = _object(policy_value, field="root")

        expected_static: dict[str, object] = {
            "schema_version": "1.0",
            "kind": "NEXUS_QUANT_P23I_E2E_VALIDATION",
            "task_id": "FIN-P23-WI-001",
            "phase": "P23",
            "workstream": "P23-I",
            "claim_scope": "REFERENCE_UX_E2E_VALIDATION",
            "canonical_information_architecture": "config/ux/information-architecture.json",
        }
        for key, expected in expected_static.items():
            if policy.get(key) != expected:
                raise P23E2EValidationError(f"P23-I policy mismatch: {key}")

        manifest_items = _list(policy.get("upstream_manifests"), field="upstream_manifests")
        observed_manifest_spec: list[tuple[str, str, str]] = []
        for index, value in enumerate(manifest_items):
            item = _object(value, field=f"upstream_manifests[{index}]")
            observed_manifest_spec.append(
                (
                    _text(item.get("workstream"), field=f"upstream[{index}].workstream"),
                    _text(item.get("task_id"), field=f"upstream[{index}].task_id"),
                    _text(item.get("path"), field=f"upstream[{index}].path"),
                )
            )
        if tuple(observed_manifest_spec) != EXPECTED_MANIFESTS:
            raise P23E2EValidationError("upstream manifest order/task/path drift")

        ia_path = root / "config/ux/information-architecture.json"
        try:
            ia_value: object = json.loads(ia_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise P23E2EValidationError(f"invalid canonical IA JSON: {exc}") from exc
        ia = _object(ia_value, field="information_architecture")
        surfaces_raw = _list(ia.get("surfaces"), field="information_architecture.surfaces")
        canonical_surfaces: list[str] = []
        for index, value in enumerate(surfaces_raw):
            surface = _object(value, field=f"surfaces[{index}]")
            canonical_surfaces.append(_text(surface.get("id"), field=f"surfaces[{index}].id"))
        if len(canonical_surfaces) != 11 or len(set(canonical_surfaces)) != 11:
            raise P23E2EValidationError("canonical surface registry drift")

        upstream_results: list[UpstreamValidation] = []
        for workstream, task_id, relative_path in EXPECTED_MANIFESTS:
            manifest_path = root / relative_path
            try:
                manifest_bytes = manifest_path.read_bytes()
                manifest_value: object = json.loads(manifest_bytes.decode("utf-8"))
            except Exception as exc:
                raise P23E2EValidationError(
                    f"invalid upstream manifest {relative_path}: {exc}"
                ) from exc
            manifest = _object(manifest_value, field=workstream)
            if manifest.get("task_id") != task_id:
                raise P23E2EValidationError(f"{workstream} task ID drift")
            if manifest.get("state") != "CANONICAL_COMPLETE":
                raise P23E2EValidationError(f"{workstream} is not CANONICAL_COMPLETE")
            if manifest.get("lock_state") != "RELEASED":
                raise P23E2EValidationError(f"{workstream} lock is not RELEASED")

            closure = _object(manifest.get("closure"), field=f"{workstream}.closure")
            _positive_int(closure.get("implementation_pr"), field=f"{workstream}.implementation_pr")
            _positive_int(
                closure.get("implementation_governance_run"),
                field=f"{workstream}.implementation_governance_run",
            )
            _positive_int(
                closure.get("post_merge_governance_run"),
                field=f"{workstream}.post_merge_governance_run",
            )
            _positive_int(
                closure.get("post_merge_branch_hygiene_run"),
                field=f"{workstream}.post_merge_branch_hygiene_run",
            )
            _sha256_hex(
                closure.get("implementation_artifact_sha256"),
                field=f"{workstream}.implementation_artifact_sha256",
            )
            _sha256_hex(
                closure.get("post_merge_artifact_sha256"),
                field=f"{workstream}.post_merge_artifact_sha256",
            )

            safety = _object(manifest.get("safety"), field=f"{workstream}.safety")
            for key in FORBIDDEN_TRUE_SAFETY_KEYS:
                if key in safety and safety.get(key) is not False:
                    raise P23E2EValidationError(f"{workstream} forbidden authority drift: {key}")
            if safety.get("production_activation") is not False:
                raise P23E2EValidationError(f"{workstream} production activation drift")
            if safety.get("live_trading") != "DISABLED":
                raise P23E2EValidationError(f"{workstream} Live Trading drift")
            if safety.get("auto_trading") != "DISABLED":
                raise P23E2EValidationError(f"{workstream} Auto Trading drift")
            if "p24_state" in safety and safety.get("p24_state") != "NOT_STARTED":
                raise P23E2EValidationError(f"{workstream} P24 state drift")

            upstream_results.append(
                UpstreamValidation(
                    workstream=workstream,
                    task_id=task_id,
                    path=relative_path,
                    manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),
                )
            )

        journeys_raw = _list(policy.get("reference_journeys"), field="reference_journeys")
        journeys: list[tuple[str, tuple[str, ...]]] = []
        for index, value in enumerate(journeys_raw):
            item = _object(value, field=f"reference_journeys[{index}]")
            journey_id = _text(item.get("id"), field=f"journey[{index}].id")
            surfaces = tuple(
                _text(surface, field=f"journey[{index}].surfaces[]")
                for surface in _list(item.get("surfaces"), field=f"journey[{index}].surfaces")
            )
            journeys.append((journey_id, surfaces))
            for surface in surfaces:
                if surface not in canonical_surfaces:
                    raise P23E2EValidationError(
                        f"journey {journey_id} references noncanonical surface {surface}"
                    )
        if tuple(journeys) != EXPECTED_JOURNEYS:
            raise P23E2EValidationError("reference journey order/coverage drift")

        lineage = _object(policy.get("lineage_requirements"), field="lineage_requirements")
        required_lineage_flags = (
            "implementation_pr_required",
            "implementation_governance_success_required",
            "implementation_artifact_sha256_required",
            "post_merge_governance_success_required",
            "post_merge_artifact_sha256_required",
            "post_merge_branch_hygiene_success_required",
        )
        for flag in required_lineage_flags:
            if lineage.get(flag) is not True:
                raise P23E2EValidationError(f"lineage requirement weakened: {flag}")

        certifications = _object(
            policy.get("certification_boundaries"), field="certification_boundaries"
        )
        expected_certifications: dict[str, object] = {
            "browser_runtime_certification": False,
            "production_readiness": False,
            "real_user_monitoring_certification": False,
            "production_performance_certification": False,
            "p24_activation": False,
        }
        if certifications != expected_certifications:
            raise P23E2EValidationError("certification boundary drift")

        safety = _object(policy.get("safety"), field="safety")
        expected_safety: dict[str, object] = {
            "credential_access": False,
            "permission_mutation": False,
            "network_mutation": False,
            "execution_authority_mutation": False,
            "external_order_authority": False,
            "runtime_state_mutation": False,
            "remediation_authority": False,
            "production_activation": False,
            "p24_state": "NOT_STARTED",
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        }
        if safety != expected_safety:
            raise P23E2EValidationError("P23-I safety boundary drift")

        return cls(
            upstream=tuple(upstream_results),
            journeys=tuple(journeys),
            canonical_surfaces=tuple(canonical_surfaces),
            safety=safety,
        )

    @property
    def validation_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()

    def payload(self) -> dict[str, object]:
        return {
            "upstream": [
                {
                    "workstream": item.workstream,
                    "task_id": item.task_id,
                    "path": item.path,
                    "manifest_sha256": item.manifest_sha256,
                }
                for item in self.upstream
            ],
            "journeys": [
                {"id": journey_id, "surfaces": list(surfaces)}
                for journey_id, surfaces in self.journeys
            ],
            "canonical_surfaces": list(self.canonical_surfaces),
            "safety": self.safety,
        }
