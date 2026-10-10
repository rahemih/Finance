#!/usr/bin/env python3
"""Deterministic AR-0 Research Governance validation and evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Mapping, cast

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "research/governance"

FILES = (
    ROOT / "contracts/tasks/FIN-P08-WJ-003.json",
    BASE / "AR-0-RESEARCH-GOVERNANCE.md",
    BASE / "ar0-research-governance.json",
    BASE / "point-in-time-safety-contract.json",
    BASE / "dataset-access-boundary.json",
    BASE / "exploratory-confirmatory-split-policy.json",
    BASE / "metric-registry.json",
    BASE / "candidate-decision-vocabulary.json",
    BASE / "regime-universe-methodology.json",
    BASE / "TOOL-BUILD-VS-BUY-ADR-PLAN.md",
    BASE / "schemas/arft-evidence-envelope.schema.json",
    BASE / "schemas/confirmatory-hypothesis-contract.schema.json",
    ROOT / "docs/09-agents/specialists/RESEARCH-VALIDATION-SPECIALIST.json",
    ROOT / "docs/01-roadmap/addenda/ALPHA-RESEARCH-FAST-TRACK.md",
)

CANDIDATE_DECISIONS = {
    "REJECT",
    "RETAIN_FOR_CONFIRMATION",
    "RETAIN_FOR_P17",
    "INVESTIGATE",
}


class AR0ValidationError(RuntimeError):
    pass


def fail(message: str) -> None:
    raise AR0ValidationError(message)


def load_json(path: Path) -> object:
    if not path.is_file():
        fail(f"AR0_REQUIRED_FILE_MISSING path={path.relative_to(ROOT)}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AR0ValidationError(
            f"AR0_JSON_INVALID path={path.relative_to(ROOT)}"
        ) from exc


def mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        fail(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        fail(f"{field} must be non-empty text")
    return value.strip()


def string_list(value: object, *, field: str) -> list[str]:
    if not isinstance(value, list):
        fail(f"{field} must be an array")
    result: list[str] = []
    for item in value:
        result.append(text(item, field=field))
    return result


def git_sha() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_schema_instance(instance: object, schema_value: object, *, path: str = "$") -> None:
    schema = mapping(schema_value, field=f"{path} schema")

    expected_type = schema.get("type")
    if expected_type == "object":
        if not isinstance(instance, dict):
            fail(f"SCHEMA_TYPE_MISMATCH path={path} expected=object")
        obj = cast(dict[str, object], instance)
        required = schema.get("required", [])
        if not isinstance(required, list):
            fail(f"SCHEMA_REQUIRED_INVALID path={path}")
        for key in required:
            if not isinstance(key, str) or key not in obj:
                fail(f"SCHEMA_REQUIRED_MISSING path={path}.{key}")
        properties_value = schema.get("properties", {})
        if not isinstance(properties_value, dict):
            fail(f"SCHEMA_PROPERTIES_INVALID path={path}")
        properties = cast(dict[str, object], properties_value)
        additional = schema.get("additionalProperties", True)
        if additional is False:
            unexpected = sorted(set(obj) - set(properties))
            if unexpected:
                fail(f"SCHEMA_ADDITIONAL_PROPERTY path={path} keys={unexpected}")
        for key, value in obj.items():
            if key in properties:
                validate_schema_instance(value, properties[key], path=f"{path}.{key}")
            elif isinstance(additional, dict):
                validate_schema_instance(value, additional, path=f"{path}.{key}")
        minimum = schema.get("minProperties")
        if isinstance(minimum, int) and len(obj) < minimum:
            fail(f"SCHEMA_MIN_PROPERTIES path={path}")
    elif expected_type == "array":
        if not isinstance(instance, list):
            fail(f"SCHEMA_TYPE_MISMATCH path={path} expected=array")
        minimum = schema.get("minItems")
        if isinstance(minimum, int) and len(instance) < minimum:
            fail(f"SCHEMA_MIN_ITEMS path={path}")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(instance):
                validate_schema_instance(item, item_schema, path=f"{path}[{index}]")
    elif expected_type == "string":
        if not isinstance(instance, str):
            fail(f"SCHEMA_TYPE_MISMATCH path={path} expected=string")
        minimum = schema.get("minLength")
        if isinstance(minimum, int) and len(instance) < minimum:
            fail(f"SCHEMA_MIN_LENGTH path={path}")
        pattern = schema.get("pattern")
        if isinstance(pattern, str) and re.fullmatch(pattern, instance) is None:
            fail(f"SCHEMA_PATTERN_MISMATCH path={path}")
    elif expected_type == "boolean":
        if not isinstance(instance, bool):
            fail(f"SCHEMA_TYPE_MISMATCH path={path} expected=boolean")
    elif expected_type == "integer":
        if isinstance(instance, bool) or not isinstance(instance, int):
            fail(f"SCHEMA_TYPE_MISMATCH path={path} expected=integer")

    if "const" in schema and instance != schema["const"]:
        fail(f"SCHEMA_CONST_MISMATCH path={path}")
    enum = schema.get("enum")
    if isinstance(enum, list) and instance not in enum:
        fail(f"SCHEMA_ENUM_MISMATCH path={path}")


def validate() -> dict[str, object]:
    for path in FILES:
        if not path.is_file():
            fail(f"AR0_REQUIRED_FILE_MISSING path={path.relative_to(ROOT)}")

    governance = mapping(
        load_json(BASE / "ar0-research-governance.json"),
        field="governance",
    )
    if governance.get("protocol_version") != "arft-research-protocol-v1":
        fail("AR0_PROTOCOL_VERSION_INVALID")
    if governance.get("generic_protocol_frozen") is not True:
        fail("AR0_GENERIC_PROTOCOL_NOT_FROZEN")
    if governance.get("candidate_specific_hypotheses_pre_registered") is not False:
        fail("AR0_CANDIDATE_HYPOTHESES_MUST_NOT_BE_PRE_REGISTERED")
    if governance.get("canonical_gate_substitution_allowed") is not False:
        fail("AR0_GATE_SUBSTITUTION_FORBIDDEN")
    for key in (
        "production_validation_claim_allowed",
        "profitability_claim_allowed",
        "buy_sell_authority",
        "risk_approval_authority",
        "execution_authority",
        "demo_authority",
        "shadow_authority",
    ):
        if governance.get(key) is not False:
            fail(f"AR0_AUTHORITY_MUST_BE_FALSE field={key}")
    if governance.get("live_trading") != "DISABLED" or governance.get("auto_trading") != "DISABLED":
        fail("AR0_TRADING_MUST_REMAIN_DISABLED")

    thresholds = mapping(governance.get("threshold_policy"), field="threshold_policy")
    if thresholds.get("unresolved_threshold_status") != "TO_BE_CALIBRATED":
        fail("AR0_UNRESOLVED_THRESHOLDS_MUST_BE_CALIBRATION_GOVERNED")
    for key, value in thresholds.items():
        if key == "unresolved_threshold_status":
            continue
        if value != "FORBIDDEN":
            fail(f"AR0_ARBITRARY_THRESHOLD_POLICY_INVALID field={key}")

    pit = mapping(load_json(BASE / "point-in-time-safety-contract.json"), field="point_in_time")
    if pit.get("fail_closed_on_uncertainty") is not True:
        fail("AR0_POINT_IN_TIME_MUST_FAIL_CLOSED")
    if pit.get("generic_shift_rule_sufficient") is not False:
        fail("AR0_GENERIC_SHIFT_CANNOT_PROVE_SAFETY")
    if pit.get("uncertainty_result") != "BLOCKED":
        fail("AR0_POINT_IN_TIME_UNCERTAINTY_MUST_BLOCK")
    required_times = mapping(pit.get("required_time_semantics"), field="required_time_semantics")
    for key in (
        "source_information_availability_time",
        "feature_availability_time",
        "decision_evaluation_time",
        "label_horizon",
        "timezone_clock_semantics",
    ):
        if required_times.get(key) != "REQUIRED":
            fail(f"AR0_REQUIRED_TIME_SEMANTIC_MISSING field={key}")

    access = mapping(load_json(BASE / "dataset-access-boundary.json"), field="dataset_access")
    partitions = mapping(access.get("partitions"), field="partitions")
    confirmatory = mapping(partitions.get("CONFIRMATORY_PROTECTED"), field="confirmatory")
    preconditions = set(string_list(confirmatory.get("access_preconditions"), field="access_preconditions"))
    for required in (
        "CANDIDATE_DEFINITION_FROZEN",
        "PARAMETERS_FROZEN",
        "CONFIRMATORY_HYPOTHESIS_CONTRACT_FROZEN",
        "CONFIRMATORY_DATASET_REFERENCES_FROZEN",
    ):
        if required not in preconditions:
            fail(f"AR0_CONFIRMATORY_PRECONDITION_MISSING value={required}")
    if access.get("premature_confirmatory_access_result") != "CONTAMINATED_AND_RETIRED":
        fail("AR0_PREMATURE_CONFIRMATORY_ACCESS_MUST_RETIRE_PARTITION")
    if access.get("repeated_peeking_result") != "CONTAMINATED_AND_RETIRED":
        fail("AR0_REPEATED_PEEKING_MUST_RETIRE_PARTITION")

    split = mapping(
        load_json(BASE / "exploratory-confirmatory-split-policy.json"),
        field="split_policy",
    )
    if split.get("confirmatory_requires_frozen_contract") is not True:
        fail("AR0_CONFIRMATORY_CONTRACT_FREEZE_REQUIRED")
    if split.get("confirmatory_candidate_mutation_after_outcome_access") != "FORBIDDEN":
        fail("AR0_POST_OUTCOME_CANDIDATE_MUTATION_FORBIDDEN")
    for key in (
        "fixed_p_value_threshold",
        "fixed_sample_count_threshold",
        "fixed_fold_count",
        "fixed_monte_carlo_count",
    ):
        if split.get(key) != "TO_BE_CALIBRATED":
            fail(f"AR0_FIXED_THRESHOLD_FORBIDDEN field={key}")

    metrics = mapping(load_json(BASE / "metric-registry.json"), field="metrics")
    metric_families = metrics.get("metric_families")
    if not isinstance(metric_families, list) or not metric_families:
        fail("AR0_METRIC_REGISTRY_EMPTY")
    metric_ids: set[str] = set()
    for item in metric_families:
        metric = mapping(item, field="metric")
        metric_id = text(metric.get("id"), field="metric.id")
        if metric_id in metric_ids:
            fail(f"AR0_DUPLICATE_METRIC id={metric_id}")
        metric_ids.add(metric_id)
        if metric.get("decision_threshold") != "TO_BE_CALIBRATED":
            fail(f"AR0_METRIC_THRESHOLD_NOT_CALIBRATION_GOVERNED id={metric_id}")

    decisions = mapping(
        load_json(BASE / "candidate-decision-vocabulary.json"),
        field="decision_vocabulary",
    )
    allowed = set(string_list(decisions.get("allowed_decisions"), field="allowed_decisions"))
    if allowed != CANDIDATE_DECISIONS:
        fail("AR0_DECISION_VOCABULARY_MISMATCH")
    if decisions.get("positive_research_evidence_ceiling") != "RETAIN_FOR_P17":
        fail("AR0_POSITIVE_EVIDENCE_CEILING_INVALID")

    universe = mapping(
        load_json(BASE / "regime-universe-methodology.json"),
        field="regime_universe",
    )
    if universe.get("universe_selection_timing") != "EX_ANTE_BEFORE_CANDIDATE_OUTCOME_REVIEW":
        fail("AR0_UNIVERSE_MUST_BE_SELECTED_EX_ANTE")
    if universe.get("post_outcome_asset_switching_to_improve_results") != "FORBIDDEN":
        fail("AR0_POST_OUTCOME_ASSET_SWITCHING_FORBIDDEN")
    for key in (
        "fixed_market_cap_rank_cutoff",
        "fixed_history_length_cutoff",
        "fixed_correlation_band_cutoff",
        "regime_numeric_boundaries",
    ):
        if universe.get(key) != "TO_BE_CALIBRATED":
            fail(f"AR0_UNIVERSE_THRESHOLD_NOT_CALIBRATION_GOVERNED field={key}")

    specialist = mapping(
        load_json(ROOT / "docs/09-agents/specialists/RESEARCH-VALIDATION-SPECIALIST.json"),
        field="research_validation_specialist",
    )
    if specialist.get("parent_agent") != "A4":
        fail("AR0_RVS_PARENT_MUST_REMAIN_A4")
    authority = set(string_list(specialist.get("authority"), field="specialist.authority"))
    if not any("REJECT" in value and "RETAIN_FOR_P17" in value for value in authority):
        fail("AR0_RVS_DECISION_AUTHORITY_MISSING")
    forbidden = string_list(specialist.get("forbidden_actions"), field="specialist.forbidden_actions")
    if not any("G6" in value and "G9" in value for value in forbidden):
        fail("AR0_RVS_GATE_BYPASS_PROHIBITION_MISSING")

    task = mapping(load_json(ROOT / "contracts/tasks/FIN-P08-WJ-003.json"), field="task")
    write_paths = set(string_list(task.get("write_paths"), field="task.write_paths"))
    if "docs/01-roadmap/MASTER-ROADMAP-v2.0.md" in write_paths:
        fail("AR0_MASTER_ROADMAP_WRITE_FORBIDDEN")
    forbidden_paths = set(string_list(task.get("forbidden_paths"), field="task.forbidden_paths"))
    if "docs/01-roadmap/MASTER-ROADMAP-v2.0.md" not in forbidden_paths:
        fail("AR0_MASTER_ROADMAP_MUST_BE_EXPLICITLY_FORBIDDEN")

    addendum = (ROOT / "docs/01-roadmap/addenda/ALPHA-RESEARCH-FAST-TRACK.md").read_text(
        encoding="utf-8"
    )
    for phrase in (
        "AR-0 — Research Governance",
        "TO_BE_CALIBRATED",
        "arbitrary sample-count",
        "Point-in-Time Safety Contract",
    ):
        if phrase not in addendum:
            fail(f"AR0_ADDENDUM_REQUIREMENT_MISSING phrase={phrase}")

    evidence_schema = load_json(BASE / "schemas/arft-evidence-envelope.schema.json")
    hypothesis_schema = mapping(
        load_json(BASE / "schemas/confirmatory-hypothesis-contract.schema.json"),
        field="hypothesis_schema",
    )
    if hypothesis_schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        fail("AR0_HYPOTHESIS_SCHEMA_DRAFT_INVALID")
    hypothesis_properties = mapping(hypothesis_schema.get("properties"), field="hypothesis_properties")
    state_schema = mapping(hypothesis_properties.get("state"), field="hypothesis_state")
    if state_schema.get("const") != "FROZEN_BEFORE_CONFIRMATORY_ACCESS":
        fail("AR0_HYPOTHESIS_FREEZE_STATE_INVALID")

    protocol_hashes = {
        str(path.relative_to(ROOT)): sha256(path)
        for path in FILES
        if path.is_file()
    }

    evidence: dict[str, object] = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_ARFT_RESEARCH_EVIDENCE_ENVELOPE",
        "protocol_version": "arft-research-protocol-v1",
        "task_id": "FIN-P08-WJ-003",
        "run_id": "FIN-P08-WJ-003-CI",
        "stage": "AR-0",
        "candidate_id": "AR0_GOVERNANCE",
        "builder_identity": "A0/A4",
        "evaluator_identity": "A10",
        "code_git_sha": git_sha(),
        "dataset_references": [
            {
                "dataset_id": "AR0_GOVERNANCE_NO_MARKET_DATA",
                "version_or_hash": sha256(BASE / "dataset-access-boundary.json"),
                "access_class": "NOT_APPLICABLE_GOVERNANCE",
            }
        ],
        "protocol_artifact_hashes": protocol_hashes,
        "point_in_time_status": "NOT_APPLICABLE_GOVERNANCE",
        "decision": "NOT_APPLICABLE_GOVERNANCE",
        "metric_results": [],
        "limitations": [
            "AR-0 freezes generic governance only; it does not validate a market candidate.",
            "Tool implementation remains TO_BE_DECIDED_BY_ADR in AR-1.",
            "Candidate-specific numeric thresholds remain TO_BE_CALIBRATED.",
        ],
        "uncertainty": [
            "Candidate-specific hypothesis, metric procedure, universe and thresholds are intentionally deferred.",
        ],
        "artifact_hashes": {
            "research_governance": sha256(BASE / "ar0-research-governance.json"),
            "point_in_time_contract": sha256(BASE / "point-in-time-safety-contract.json"),
            "evidence_schema": sha256(BASE / "schemas/arft-evidence-envelope.schema.json"),
            "hypothesis_schema": sha256(
                BASE / "schemas/confirmatory-hypothesis-contract.schema.json"
            ),
        },
    }
    validate_schema_instance(evidence, evidence_schema)
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        evidence = validate()
    except AR0ValidationError as exc:
        print(f"AR0_RESEARCH_GOVERNANCE=FAIL reason={exc}")
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(evidence, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"AR0_RESEARCH_GOVERNANCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
