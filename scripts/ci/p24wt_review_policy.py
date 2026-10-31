#!/usr/bin/env python3
"""Fail-closed validation of proposed P24 solo-owner reviewer exception.

This checker verifies a PROPOSAL only. It has zero permission to approve,
merge, self-review, modify contracts, issue orders or bypass Owner Human Gates.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import cast

EXPECTED_HEADS = {
    492: ("FIN-P24-WR-001", "529f43142befee4ced4a652a2472bd41e509c32d"),
    493: ("FIN-P24-WO-001", "4d1945db6c59aee7cb4d341c022f75d208f96d0f"),
    494: ("FIN-P24-WP-001", "57672f2df93bc483ecc0df9b9f2b6fca64d8087b"),
    499: ("FIN-P24-WQ-001", "0b31559eef7b3cc2ec2e669fd36a49f10d116144"),
    502: ("FIN-P24-WS-001", "64eb2f14f1a995e417005cc2b43d9d8d5711da53"),
}
EXPECTED_FALSE = (
    "automated_merge", "self_git_review",
)
EXPECTED_TRUE = (
    "no_credential_access", "only_nonlive_synthetic",
)
EXPECTED_REQUIRED = (
    "A5_independent_runtime_risk_veto",
    "A8_security_and_provenance_controls",
    "A10_ci_and_evidence_verification",
    "tests_and_supply_chain_scan",
    "human_gate_each_final_pr_sha",
    "human_gate_policy_adoption",
    "independent_human_review_if_code_adds_order_network_auth_production",
)
OWNER_TEXT = "MANDATORY_AND_NOT_YET_GRANTED"


class ReviewPolicyError(ValueError):
    """Attempted review authority escalation or malformed review exception."""


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _mapping(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or any(type(k) is not str for k in value):
        raise ReviewPolicyError("policy object must have string keys")
    return cast(dict[str, object], value)


def validate(proposal: object) -> dict[str, object]:
    policy = _mapping(proposal)
    required_fields = {
        "schema_version", "task_id", "kind", "status", "effective",
        "authority", "upstream_policy", "purpose", "candidates",
        "review_model", "approval_conditions", "production_state",
    }
    if set(policy) != required_fields:
        raise ReviewPolicyError("missing or surplus policy fields")
    if (policy["schema_version"] != "1.0"
            or policy["task_id"] != "FIN-P24-WT-001"
            or policy["kind"] != "P24_SYNTHETIC_SOLO_OWNER_REVIEW_EXCEPTION_PROPOSAL"
            or policy["status"] != "PROPOSED_NOT_EFFECTIVE"
            or type(policy["effective"]) is not bool or policy["effective"] is not False
            or policy["authority"] != "NONE_UNTIL_SEPARATE_EXPLICIT_OWNER_POLICY_HUMAN_GATE_AND_APPROVED_MERGE"):
        raise ReviewPolicyError("proposal must not claim adoption, approval or merge authority")
    if "FIN-P00-WX-001" not in str(policy["upstream_policy"]):
        raise ReviewPolicyError("solo-owner upstream governance missing")
    rows_obj = policy["candidates"]
    if not isinstance(rows_obj, list) or len(rows_obj) != 5:
        raise ReviewPolicyError("exactly five bounded PRs required")
    rows = cast(list[object], rows_obj)
    observed: set[int] = set()
    for item in rows:
        r = _mapping(item)
        if set(r) != {"pr", "task_id", "reviewed_head", "scope",
                      "allow_human_reviewer_exception", "mandatory_live_review", "extra_guard"}:
            raise ReviewPolicyError("unrecognized candidate field")
        number = r["pr"]
        if type(number) is not int or number not in EXPECTED_HEADS:
            raise ReviewPolicyError("unexpected PR candidate")
        n = cast(int, number)
        if n in observed:
            raise ReviewPolicyError("duplicate PR")
        observed.add(n)
        task_id, sha = EXPECTED_HEADS[n]
        if r["task_id"] != task_id or r["reviewed_head"] != sha:
            raise ReviewPolicyError("PR identity or reviewed HEAD mismatch")
        if type(r["allow_human_reviewer_exception"]) is not bool or r["allow_human_reviewer_exception"] is not True:
            raise ReviewPolicyError("missing bounded exception marker")
        if r["mandatory_live_review"] != "NOT_APPLICABLE_TO_THIS_SIMULATOR":
            raise ReviewPolicyError("must exclude live review from synthetic waiver")
        for name in ("scope", "extra_guard"):
            value = r[name]
            if type(value) is not str or not cast(str, value).strip():
                raise ReviewPolicyError("each PR must have explicit nonlive scope and guard")
    if observed != set(EXPECTED_HEADS):
        raise ReviewPolicyError("incomplete PR set")
    model = _mapping(policy["review_model"])
    allowed = set(EXPECTED_FALSE) | set(EXPECTED_TRUE) | set(EXPECTED_REQUIRED) | {
        "external_human_github_reviewer",
    }
    if set(model) != allowed:
        raise ReviewPolicyError("missing review/control category")
    if model["external_human_github_reviewer"] != "PROPOSED_NOT_APPLICABLE_IF_OWNER_ADOPTS_SPECIFIC_EXCEPTION":
        raise ReviewPolicyError("cannot claim existing second-human approval")
    for key in EXPECTED_FALSE:
        if type(model[key]) is not bool or model[key] is not False:
            raise ReviewPolicyError("automatic merge or self review is forbidden")
    for key in EXPECTED_TRUE:
        if type(model[key]) is not bool or model[key] is not True:
            raise ReviewPolicyError("non-live privacy scope is mandatory")
    for key in EXPECTED_REQUIRED:
        if key.startswith("human_gate_"):
            if model[key] != OWNER_TEXT:
                raise ReviewPolicyError("Owner human gate cannot be granted by proposal")
        elif model[key] != "MANDATORY_UNWAIVABLE" and model[key] != "MANDATORY_NOT_REPLACED":
            raise ReviewPolicyError("independent domain control cannot be waived")
    conditions = policy["approval_conditions"]
    if not isinstance(conditions, list) or len(conditions) < 6 or any(
        type(x) is not str or not x for x in conditions
    ):
        raise ReviewPolicyError("explicit owner and control conditions required")
    state = _mapping(policy["production_state"])
    if state != {
        "pre_first_live_satisfied": 0, "first_live_owner_approval": "NOT_GRANTED",
        "p24_b": "BLOCKED", "g13": "NOT_STARTED",
        "live_trading": "DISABLED", "auto_trading": "DISABLED",
    } or type(state["pre_first_live_satisfied"]) is not int:
        raise ReviewPolicyError("production authority unchanged only")
    return {
        "task_id": "FIN-P24-WT-001",
        "status": "VALID_PROPOSAL_ONLY_NO_MERGE_AUTHORITY",
        "proposal_sha256": hashlib.sha256(canonical(policy)).hexdigest(),
        "candidates": sorted(observed),
        "candidate_count": len(observed),
        "owner_policy_gate": "NOT_GRANTED",
        "owner_pr_merge_gates": "NOT_GRANTED",
        "second_human_github_review": "NOT_APPLICABLE_ONLY_IF_SPECIFICALLY_ADOPTED",
        "independent_domain_controls": "ALL_REQUIRED",
        "pre_first_live_satisfied": 0,
        "g13": "NOT_STARTED",
        "live_trading": "DISABLED",
        "auto_trading": "DISABLED",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, default=Path("config/governance/p24-offline-solo-review-proposal.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        source: object = json.loads(args.policy.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ReviewPolicyError("policy file missing or invalid") from exc
    report = validate(source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical(report) + b"\n")
    print("P24_WT_SOLO_REVIEW_PROPOSAL=PASS (NOT APPROVED)")
    print("proposal_sha256=" + str(report["proposal_sha256"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
