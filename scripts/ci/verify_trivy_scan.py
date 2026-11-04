#!/usr/bin/env python3
"""Fail-closed verification of the real Trivy fs JSON from pinned OCI scanner.

This does not perform the scan; a prior mandatory docker run executes Trivy and
must exit zero. No fabricated/fixture output may be accepted as production CI.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any

FAMILIES = ("Vulnerabilities", "Misconfigurations", "Secrets")
BLOCKED = frozenset(("HIGH", "CRITICAL"))


class TrivyReportError(RuntimeError):
    """Scanner report incomplete, malformed or contains blocking findings."""


def check_report(path: Path) -> dict[str, int]:
    if not path.is_file() or not (32 < path.stat().st_size < 60_000_000):
        raise TrivyReportError("TRIVY_REPORT_MISSING_OR_INVALID_SIZE")
    try:
        obj: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise TrivyReportError("TRIVY_REPORT_NOT_VALID_JSON") from exc
    if not isinstance(obj, dict) or type(obj.get("SchemaVersion")) is not int:
        raise TrivyReportError("TRIVY_SCHEMA_NOT_VERIFIED")
    # Trivy >=0.68 uses ArtifactType="repository" automatically when a
    # git worktree is found under `trivy fs`. This is the same full fs scan.
    if obj["SchemaVersion"] != 2:
        raise TrivyReportError("TRIVY_JSON_SCHEMA_V2_REQUIRED")
    artifact_type = obj.get("ArtifactType")
    if artifact_type not in ("filesystem", "repository"):
        raise TrivyReportError("TRIVY_NOT_FILESYSTEM_OR_REPOSITORY_SCAN")
    if artifact_type == "repository":
        meta = obj.get("Metadata")
        commit = meta.get("Commit") if isinstance(meta, dict) else None
        expected_commit = os.environ.get("GITHUB_SHA", "")
        if (not isinstance(commit, str)
                or re.fullmatch(r"[0-9a-f]{40}", commit) is None
                or not expected_commit
                or commit != expected_commit):
            raise TrivyReportError("TRIVY_REPOSITORY_COMMIT_ATTESTATION_MISMATCH")
    if not isinstance(obj.get("ArtifactName"), str) or not obj["ArtifactName"]:
        raise TrivyReportError("TRIVY_ARTIFACT_NAME_MISSING")
    results = obj.get("Results")
    if not isinstance(results, list):
        raise TrivyReportError("TRIVY_SCAN_RESULTS_MISSING")
    counts = {name: 0 for name in FAMILIES}
    for item in results:
        if not isinstance(item, dict) or not isinstance(item.get("Target"), str) or not item["Target"]:
            raise TrivyReportError("TRIVY_RESULT_TARGET_INVALID")
        for family in FAMILIES:
            findings = item.get(family, [])
            if findings is None:
                findings = []
            if not isinstance(findings, list):
                raise TrivyReportError("TRIVY_FINDING_LIST_INVALID")
            for finding in findings:
                if not isinstance(finding, dict) or not isinstance(finding.get("Severity"), str):
                    raise TrivyReportError("TRIVY_FINDING_SEVERITY_INVALID")
                if finding["Severity"].upper() in BLOCKED:
                    counts[family] += 1
    if any(counts.values()):
        raise TrivyReportError("TRIVY_HIGH_CRITICAL_FINDINGS_BLOCKED")
    return counts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    try:
        counts = check_report(args.report)
    except TrivyReportError as exc:
        parser.exit(status=1, message=f"{exc}\n")
    print(f"TRIVY_REPORT_VALIDATED=PASS family_counts={counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
