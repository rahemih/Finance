#!/usr/bin/env python3
"""Build deterministic P04-F supply-chain evidence from Syft and Trivy outputs."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def trivy_counts(report: dict) -> dict:
    counts = {
        "vulnerabilities": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNKNOWN": 0},
        "misconfigurations": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNKNOWN": 0},
        "secrets": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNKNOWN": 0},
    }
    for result in report.get("Results", []) or []:
        for item in result.get("Vulnerabilities", []) or []:
            sev = str(item.get("Severity", "UNKNOWN")).upper()
            counts["vulnerabilities"][sev if sev in counts["vulnerabilities"] else "UNKNOWN"] += 1
        for item in result.get("Misconfigurations", []) or []:
            sev = str(item.get("Severity", "UNKNOWN")).upper()
            counts["misconfigurations"][sev if sev in counts["misconfigurations"] else "UNKNOWN"] += 1
        for item in result.get("Secrets", []) or []:
            sev = str(item.get("Severity", "UNKNOWN")).upper()
            counts["secrets"][sev if sev in counts["secrets"] else "UNKNOWN"] += 1
    return counts


def license_inventory(sbom: dict) -> dict[str, int]:
    inventory: dict[str, int] = {}
    for component in sbom.get("components", []) or []:
        for entry in component.get("licenses", []) or []:
            value = None
            if isinstance(entry, dict) and isinstance(entry.get("expression"), str):
                value = entry["expression"]
            elif isinstance(entry, dict) and isinstance(entry.get("license"), dict):
                value = entry["license"].get("id") or entry["license"].get("name")
            if isinstance(value, str) and value:
                inventory[value] = inventory.get(value, 0) + 1
    return dict(sorted(inventory.items()))


def build(sbom_path: Path, trivy_path: Path, output: Path) -> None:
    sbom = load(sbom_path)
    trivy = load(trivy_path)
    policy_paths = [
        ROOT / "config/supply-chain/dependency-policy.json",
        ROOT / "config/supply-chain/license-policy.json",
        ROOT / "config/supply-chain/waivers.json",
        ROOT / ".trivyignore",
    ]
    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_SUPPLY_CHAIN_EVIDENCE",
        "tools": {
            "syft": "1.54.0",
            "trivy": "0.75.0",
            "cyclonedx": str(sbom.get("specVersion")),
        },
        "sbom": {
            "sha256": sha256(sbom_path),
            "component_count": len(sbom.get("components", []) or []),
            "license_inventory": license_inventory(sbom),
        },
        "trivy": {
            "sha256": sha256(trivy_path),
            "counts": trivy_counts(trivy),
        },
        "policies": [
            {"path": str(path.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(path)}
            for path in policy_paths
        ],
        "blocking_policy": {
            "vulnerability_severities": ["CRITICAL", "HIGH"],
            "unknown_license": "BLOCK_PENDING_REVIEW",
            "dependency_auto_merge": False,
        },
        "safety": {
            "canary": "DISABLED",
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"SUPPLY_CHAIN_EVIDENCE=PASS output={output}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sbom", type=Path, required=True)
    parser.add_argument("--trivy", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build(args.sbom, args.trivy, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
