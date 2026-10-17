#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / "config/governance/branch-hygiene-archive.json"
SHA = re.compile(r"^[0-9a-f]{40}$")


def main() -> int:
    value = json.loads(ARCHIVE.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("branch hygiene archive must be an object")
    if value.get("schema_version") != "1.0":
        raise RuntimeError("unsupported branch hygiene archive schema")
    if value.get("kind") != "NEXUS_QUANT_BRANCH_HYGIENE_ARCHIVE":
        raise RuntimeError("unexpected branch hygiene archive kind")
    if value.get("p19_started") is not False:
        raise RuntimeError("branch hygiene repair must not start P19")

    policy = value.get("policy")
    if not isinstance(policy, dict):
        raise RuntimeError("branch hygiene archive policy required")
    if policy.get("matching_rule") != "EXACT_BRANCH_NAME_AND_SHA":
        raise RuntimeError("archive matching must be exact name+SHA")
    if policy.get("sha_drift_behavior") != "RETURN_TO_ACTIVE_AUDIT":
        raise RuntimeError("archive SHA drift must return to active audit")
    if policy.get("delete_archived_unique_history") is not False:
        raise RuntimeError("archive must not authorize deletion of unique history")
    threshold = policy.get("active_noncanonical_warning_threshold")
    if not isinstance(threshold, int) or isinstance(threshold, bool) or threshold <= 0:
        raise RuntimeError("positive active branch threshold required")

    rows = value.get("branches")
    if not isinstance(rows, list):
        raise RuntimeError("branches array required")
    names: set[str] = set()
    for index, raw in enumerate(rows):
        if not isinstance(raw, dict):
            raise RuntimeError(f"branches[{index}] must be an object")
        name = raw.get("name")
        sha = raw.get("sha")
        reason = raw.get("reason")
        if not isinstance(name, str) or not name.strip() or name in {"main", "master"}:
            raise RuntimeError(f"invalid archived branch name at index {index}")
        if name in names:
            raise RuntimeError(f"duplicate archived branch: {name}")
        names.add(name)
        if not isinstance(sha, str) or SHA.fullmatch(sha) is None:
            raise RuntimeError(f"invalid archived branch SHA: {name}")
        if not isinstance(reason, str) or not reason.strip():
            raise RuntimeError(f"archived branch reason required: {name}")

    print(
        "BRANCH_HYGIENE_ARCHIVE=PASS "
        f"archived={len(rows)} active_warning_threshold={threshold}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
