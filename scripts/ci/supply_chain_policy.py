#!/usr/bin/env python3
"""P04-F dependency, waiver, SBOM and license policy enforcement."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys
import tomllib
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SUPPLY = ROOT / "config/supply-chain"
DEPENDENCY_POLICY = SUPPLY / "dependency-policy.json"
LICENSE_POLICY = SUPPLY / "license-policy.json"
WAIVERS = SUPPLY / "waivers.json"
TRIVY_IGNORE = ROOT / ".trivyignore"

EXACT_NPM = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")
EXACT_PYTHON = re.compile(
    r"^[A-Za-z0-9_.-]+(?:\[[A-Za-z0-9_,.-]+\])?\s*==\s*[A-Za-z0-9_.+!-]+(?:\s*;\s*.+)?$"
)
FORBIDDEN_NPM_PREFIXES = ("^", "~", "git+", "http://", "https://", "github:", "file:")
FORBIDDEN_NPM_VALUES = {"*", "latest", "next"}
REQUIRED_WAIVER_FIELDS = {
    "id","kind","subject","severity","rationale","compensating_control","owner",
    "environments","approved_at","expires_at","evidence","remediation_plan",
}


class PolicyFailure(RuntimeError):
    pass


def fail(message: str) -> None:
    raise PolicyFailure(message)


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"JSON_INVALID path={path.relative_to(ROOT)} error={exc}")
    if not isinstance(value, dict):
        fail(f"JSON_OBJECT_REQUIRED path={path.relative_to(ROOT)}")
    return value


def git_files(pattern: str) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--", pattern],
        cwd=ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return [ROOT / line for line in result.stdout.splitlines() if line.strip()]


def validate_policy_documents() -> tuple[dict, dict, dict]:
    dep = load_json(DEPENDENCY_POLICY)
    lic = load_json(LICENSE_POLICY)
    wai = load_json(WAIVERS)

    if dep.get("schema_version") != "1.0":
        fail("DEPENDENCY_POLICY_SCHEMA_VERSION")
    if lic.get("schema_version") != "1.0":
        fail("LICENSE_POLICY_SCHEMA_VERSION")
    if wai.get("schema_version") != "1.0":
        fail("WAIVER_POLICY_SCHEMA_VERSION")

    allow = set(lic.get("allow", []))
    review = set(lic.get("review", []))
    block = set(lic.get("block", []))
    if not allow or not review or not block:
        fail("LICENSE_POLICY_CLASS_EMPTY")
    if allow & review or allow & block or review & block:
        fail("LICENSE_POLICY_CLASSES_OVERLAP")

    if dep.get("sbom", {}).get("generator") != "Syft":
        fail("SBOM_GENERATOR_POLICY_INVALID")
    if dep.get("sbom", {}).get("generator_version") != "1.54.0":
        fail("SBOM_GENERATOR_VERSION_INVALID")
    if dep.get("sbom", {}).get("spec_version") != "1.7":
        fail("SBOM_SPEC_POLICY_INVALID")
    if dep.get("vulnerability_gate", {}).get("scanner") != "Trivy":
        fail("VULN_SCANNER_POLICY_INVALID")
    if dep.get("vulnerability_gate", {}).get("scanner_version") != "0.75.0":
        fail("VULN_SCANNER_VERSION_INVALID")
    if set(dep.get("vulnerability_gate", {}).get("block_severities", [])) != {"CRITICAL", "HIGH"}:
        fail("VULN_BLOCK_SEVERITIES_INVALID")

    return dep, lic, wai


def validate_npm_manifests() -> None:
    for path in git_files("**/package.json") + ([ROOT / "package.json"] if (ROOT / "package.json").is_file() else []):
        if not path.is_file():
            continue
        package = load_json(path)
        rel = path.relative_to(ROOT)
        for section in ("dependencies", "devDependencies", "optionalDependencies"):
            deps = package.get(section, {})
            if deps is None:
                continue
            if not isinstance(deps, dict):
                fail(f"NPM_DEPENDENCY_SECTION_NOT_OBJECT path={rel} section={section}")
            for name, spec in deps.items():
                if not isinstance(spec, str):
                    fail(f"NPM_DEPENDENCY_SPEC_NOT_STRING path={rel} dependency={name}")
                if spec.startswith("workspace:"):
                    continue
                if spec in FORBIDDEN_NPM_VALUES or spec.startswith(FORBIDDEN_NPM_PREFIXES):
                    fail(f"NPM_MUTABLE_OR_UNAPPROVED_SPEC path={rel} dependency={name} spec={spec}")
                if EXACT_NPM.fullmatch(spec) is None:
                    fail(f"NPM_DIRECT_DEPENDENCY_NOT_EXACT path={rel} dependency={name} spec={spec}")

        peers = package.get("peerDependencies", {})
        if isinstance(peers, dict):
            for name, spec in peers.items():
                if not isinstance(spec, str):
                    fail(f"NPM_PEER_SPEC_NOT_STRING path={rel} dependency={name}")
                if spec.startswith(("git+", "http://", "https://", "github:", "file:")):
                    fail(f"NPM_PEER_MUTABLE_SOURCE path={rel} dependency={name}")

    print("NPM_DEPENDENCY_POLICY=PASS")


def iter_python_dependency_strings(pyproject: dict[str, Any]) -> list[str]:
    values: list[str] = []
    project = pyproject.get("project", {})
    if isinstance(project, dict):
        deps = project.get("dependencies", [])
        if isinstance(deps, list):
            values.extend(x for x in deps if isinstance(x, str))
        optional = project.get("optional-dependencies", {})
        if isinstance(optional, dict):
            for group in optional.values():
                if isinstance(group, list):
                    values.extend(x for x in group if isinstance(x, str))
    groups = pyproject.get("dependency-groups", {})
    if isinstance(groups, dict):
        for group in groups.values():
            if isinstance(group, list):
                values.extend(x for x in group if isinstance(x, str))
    return values


def validate_python_manifests() -> None:
    paths = git_files("**/pyproject.toml")
    root = ROOT / "pyproject.toml"
    if root.is_file() and root not in paths:
        paths.append(root)

    for path in paths:
        with path.open("rb") as handle:
            pyproject = tomllib.load(handle)
        for spec in iter_python_dependency_strings(pyproject):
            if " @ " in spec or spec.startswith(("http://", "https://", "git+")):
                fail(f"PYTHON_MUTABLE_OR_URL_DEPENDENCY path={path.relative_to(ROOT)} spec={spec}")
            if EXACT_PYTHON.fullmatch(spec.strip()) is None:
                fail(f"PYTHON_DIRECT_DEPENDENCY_NOT_EXACT path={path.relative_to(ROOT)} spec={spec}")

    print("PYTHON_DEPENDENCY_POLICY=PASS")


def parse_datetime(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception as exc:
        fail(f"WAIVER_DATETIME_INVALID value={value} error={exc}")
    if parsed.tzinfo is None:
        fail(f"WAIVER_DATETIME_TIMEZONE_REQUIRED value={value}")
    return parsed.astimezone(timezone.utc)


def active_waivers(registry: dict[str, Any]) -> list[dict[str, Any]]:
    waivers = registry.get("waivers", [])
    if not isinstance(waivers, list):
        fail("WAIVERS_ARRAY_REQUIRED")

    now = datetime.now(timezone.utc)
    ids: set[str] = set()
    active: list[dict[str, Any]] = []
    for waiver in waivers:
        if not isinstance(waiver, dict):
            fail("WAIVER_OBJECT_REQUIRED")
        missing = REQUIRED_WAIVER_FIELDS - set(waiver)
        extra = set(waiver) - REQUIRED_WAIVER_FIELDS
        if missing or extra:
            fail(f"WAIVER_FIELDS_INVALID missing={sorted(missing)} extra={sorted(extra)}")
        wid = waiver["id"]
        if not isinstance(wid, str) or not wid:
            fail("WAIVER_ID_INVALID")
        if wid in ids:
            fail(f"WAIVER_ID_DUPLICATE id={wid}")
        ids.add(wid)
        if waiver["kind"] not in {"VULNERABILITY", "LICENSE_REVIEW"}:
            fail(f"WAIVER_KIND_INVALID id={wid}")
        if not isinstance(waiver["subject"], str) or not waiver["subject"]:
            fail(f"WAIVER_SUBJECT_INVALID id={wid}")
        if not isinstance(waiver["environments"], list) or not waiver["environments"]:
            fail(f"WAIVER_ENVIRONMENTS_INVALID id={wid}")
        approved = parse_datetime(waiver["approved_at"])
        expires = parse_datetime(waiver["expires_at"])
        if expires <= approved:
            fail(f"WAIVER_EXPIRY_ORDER_INVALID id={wid}")
        if expires <= now:
            fail(f"WAIVER_EXPIRED id={wid} expires={waiver['expires_at']}")
        for field in ("rationale","compensating_control","owner","evidence","remediation_plan"):
            if not isinstance(waiver[field], str) or not waiver[field].strip():
                fail(f"WAIVER_FIELD_EMPTY id={wid} field={field}")
        active.append(waiver)

    return active


def trivy_ignore_entries() -> set[str]:
    entries: set[str] = set()
    for raw in TRIVY_IGNORE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        entries.add(line)
    return entries


def validate_waivers(registry: dict[str, Any]) -> list[dict[str, Any]]:
    active = active_waivers(registry)
    vulnerability_subjects = {
        item["subject"] for item in active if item["kind"] == "VULNERABILITY"
    }
    ignores = trivy_ignore_entries()
    if ignores != vulnerability_subjects:
        fail(
            "TRIVY_IGNORE_WAIVER_MISMATCH "
            f"ignore_only={sorted(ignores-vulnerability_subjects)} "
            f"waiver_only={sorted(vulnerability_subjects-ignores)}"
        )
    print(f"WAIVER_POLICY=PASS active={len(active)}")
    return active


def component_identity(component: dict[str, Any]) -> str:
    purl = component.get("purl")
    if isinstance(purl, str) and purl:
        return purl
    name = str(component.get("name", "UNKNOWN"))
    version = str(component.get("version", "UNKNOWN"))
    return f"{name}@{version}"


def component_licenses(component: dict[str, Any]) -> list[str]:
    out: list[str] = []
    values = component.get("licenses", [])
    if not isinstance(values, list):
        return out
    for item in values:
        if not isinstance(item, dict):
            continue
        if isinstance(item.get("expression"), str) and item["expression"].strip():
            out.append(item["expression"].strip())
            continue
        lic = item.get("license")
        if isinstance(lic, dict):
            value = lic.get("id") or lic.get("name")
            if isinstance(value, str) and value.strip():
                out.append(value.strip())
    return out


def has_license_waiver(active: list[dict[str, Any]], identity: str, license_value: str) -> bool:
    subject = f"{identity}|{license_value}"
    return any(
        item["kind"] == "LICENSE_REVIEW" and item["subject"] == subject
        for item in active
    )


def curated_license_assertion(license_policy: dict[str, Any], identity: str) -> str | None:
    assertions = license_policy.get("curated_assertions", [])
    if not isinstance(assertions, list):
        fail("LICENSE_ASSERTIONS_ARRAY_REQUIRED")
    for item in assertions:
        if not isinstance(item, dict):
            fail("LICENSE_ASSERTION_OBJECT_REQUIRED")
        required = {"identity_prefix", "exact_version", "license", "evidence", "scope"}
        if set(item) != required:
            fail(f"LICENSE_ASSERTION_FIELDS_INVALID prefix={item.get('identity_prefix')}")
        if not all(isinstance(item[key], str) and item[key].strip() for key in required):
            fail(f"LICENSE_ASSERTION_VALUE_INVALID prefix={item.get('identity_prefix')}")
        prefix = item["identity_prefix"]
        version = item["exact_version"]
        if identity.startswith(prefix) and identity.endswith(f"@{version}"):
            return item["license"]
    return None


def validate_sbom(path: Path, license_policy: dict[str, Any], active: list[dict[str, Any]]) -> None:
    sbom = load_json(path)
    if sbom.get("bomFormat") != "CycloneDX":
        fail("SBOM_FORMAT_NOT_CYCLONEDX")
    if sbom.get("specVersion") != "1.7":
        fail(f"SBOM_SPEC_VERSION_INVALID actual={sbom.get('specVersion')}")

    components = sbom.get("components", [])
    if components is None:
        components = []
    if not isinstance(components, list):
        fail("SBOM_COMPONENTS_ARRAY_REQUIRED")

    allow = set(license_policy["allow"])
    review = set(license_policy["review"])
    block = set(license_policy["block"])
    blocked_patterns = [x.lower() for x in license_policy.get("blocked_name_patterns", [])]
    first_party = set(license_policy.get("behavior", {}).get("first_party_names", []))

    reviewed_count = 0
    third_party_count = 0
    violations: list[str] = []

    for component in components:
        if not isinstance(component, dict):
            violations.append("SBOM_COMPONENT_OBJECT_REQUIRED")
            continue
        name = component.get("name")
        if name in first_party:
            continue

        third_party_count += 1
        identity = component_identity(component)
        licenses = component_licenses(component)

        if not licenses:
            asserted = curated_license_assertion(license_policy, identity)
            if asserted is not None:
                licenses = [asserted]
            else:
                marker = "MISSING"
                if has_license_waiver(active, identity, marker):
                    reviewed_count += 1
                    continue
                violations.append(f"SBOM_LICENSE_MISSING component={identity}")
                continue

        for value in licenses:
            lowered = value.lower()
            if value in block or any(pattern in lowered for pattern in blocked_patterns):
                violations.append(f"SBOM_LICENSE_BLOCKED component={identity} license={value}")
                continue
            if value in allow:
                continue
            if value in review:
                if has_license_waiver(active, identity, value):
                    reviewed_count += 1
                    continue
                violations.append(f"SBOM_LICENSE_REVIEW_REQUIRED component={identity} license={value}")
                continue
            if value in {"UNKNOWN", "NOASSERTION"}:
                if has_license_waiver(active, identity, value):
                    reviewed_count += 1
                    continue
                violations.append(f"SBOM_LICENSE_UNKNOWN component={identity} license={value}")
                continue
            if has_license_waiver(active, identity, value):
                reviewed_count += 1
                continue
            violations.append(f"SBOM_LICENSE_UNCLASSIFIED component={identity} license={value}")

    if violations:
        fail("SBOM_LICENSE_VIOLATIONS " + " || ".join(sorted(violations)))

    print(
        "SBOM_LICENSE_POLICY=PASS "
        f"components={len(components)} third_party={third_party_count} reviewed={reviewed_count}"
    )


def mode_manifest() -> None:
    dep, lic, wai = validate_policy_documents()
    validate_npm_manifests()
    validate_python_manifests()
    active = validate_waivers(wai)
    if dep.get("dependency_auto_merge") is True:
        fail("DEPENDENCY_AUTO_MERGE_FORBIDDEN")
    print(f"SUPPLY_CHAIN_MANIFEST_POLICY=PASS active_waivers={len(active)}")


def mode_sbom(path: Path) -> None:
    _, lic, wai = validate_policy_documents()
    active = validate_waivers(wai)
    validate_sbom(path, lic, active)


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="mode", required=True)
    sub.add_parser("manifest")
    sbom = sub.add_parser("sbom")
    sbom.add_argument("--sbom", type=Path, required=True)
    args = parser.parse_args()

    try:
        if args.mode == "manifest":
            mode_manifest()
        else:
            mode_sbom(args.sbom)
    except (PolicyFailure, subprocess.CalledProcessError, AssertionError, KeyError) as exc:
        print(f"SUPPLY_CHAIN_POLICY=FAIL error={exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
