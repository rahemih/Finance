#!/usr/bin/env python3
"""NEXUS QUANT P04-C foundation CI checks.

No third-party Python dependencies are required.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[2]
TASK_SCHEMA = ROOT / "contracts/schemas/task-contract.schema.json"
P04C_CONTRACT = ROOT / "contracts/tasks/FIN-P04-WC-001.json"
CI_MANIFEST = ROOT / "docs/06-engineering/ci-cd-foundation.json"
RUNTIME_MANIFEST = ROOT / "docs/06-engineering/runtime-dependency-baseline.json"

PRODUCTION_ZONES = ("apps", "packages", "adapters", "quant")
PRODUCT_SOURCE_SUFFIXES = {".ts", ".tsx", ".mts", ".cts", ".py"}
SECRET_FILE_PATTERNS = (
    re.compile(r"(^|/)\.env(?:\..+)?$"),
    re.compile(r"\.(pem|key|p12|pfx)$", re.IGNORECASE),
)
ALLOWED_SECRET_TEMPLATE = re.compile(r"(^|/)\.env\.example$")


class CheckFailure(RuntimeError):
    pass


def fail(message: str) -> None:
    raise CheckFailure(message)


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"JSON_INVALID path={path.relative_to(ROOT)} error={exc}")
    if not isinstance(value, dict):
        fail(f"JSON_OBJECT_REQUIRED path={path.relative_to(ROOT)}")
    return value


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.strip()


def tracked_files(*patterns: str) -> list[Path]:
    args = ["ls-files"]
    if patterns:
        args.extend(["--", *patterns])
    output = git(*args)
    if not output:
        return []
    return [ROOT / line for line in output.splitlines() if line.strip()]


def check_lint() -> None:
    for path in tracked_files("*.py"):
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            fail(f"PYTHON_SYNTAX_FAIL path={path.relative_to(ROOT)} line={exc.lineno}")

    for path in tracked_files("*.json"):
        json.loads(path.read_text(encoding="utf-8"))

    pyproject = ROOT / "pyproject.toml"
    if pyproject.is_file():
        with pyproject.open("rb") as handle:
            tomllib.load(handle)

    print("FOUNDATION_LINT=PASS")


def product_source_files() -> list[Path]:
    found: list[Path] = []
    for zone in PRODUCTION_ZONES:
        base = ROOT / zone
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_file() and path.suffix.lower() in PRODUCT_SOURCE_SUFFIXES:
                found.append(path)
    return sorted(found)


def check_typecheck_readiness() -> None:
    sources = product_source_files()
    if not sources:
        print("TYPECHECK_READINESS=PASS_NO_PRODUCT_SOURCE")
        return

    config_path = ROOT / "pyrightconfig.json"
    if not config_path.is_file():
        listing = ", ".join(str(p.relative_to(ROOT)) for p in sources[:20])
        fail(
            "TYPECHECK_READINESS_FAIL product source exists without governed "
            f"pyrightconfig.json: {listing}"
        )

    config = read_json(config_path)
    if config.get("typeCheckingMode") != "strict":
        fail("TYPECHECK_READINESS_FAIL pyright typeCheckingMode must be strict")
    if config.get("pythonVersion") != "3.14":
        fail("TYPECHECK_READINESS_FAIL pyright pythonVersion must be 3.14")
    includes = config.get("include")
    if not isinstance(includes, list):
        fail("TYPECHECK_READINESS_FAIL pyright include must be an array")
    required_zones = set(PRODUCTION_ZONES)
    actual_zones = {item for item in includes if isinstance(item, str)}
    if not required_zones.issubset(actual_zones):
        missing = sorted(required_zones - actual_zones)
        fail(f"TYPECHECK_READINESS_FAIL pyright missing production zones: {missing}")

    print(f"TYPECHECK_READINESS=PASS_PYRIGHT_CONFIGURED sources={len(sources)}")


def check_unit() -> None:
    package = read_json(ROOT / "package.json")
    runtime = read_json(RUNTIME_MANIFEST)
    ci = read_json(CI_MANIFEST)

    assert package["engines"]["node"] == "24.21.0"
    assert package["engines"]["pnpm"] == "11.28.4"
    assert package["packageManager"] == "pnpm@11.28.4"
    assert (ROOT / ".node-version").read_text(encoding="utf-8").strip() == "24.21.0"
    assert (ROOT / ".python-version").read_text(encoding="utf-8").strip() == "3.14.8"
    assert runtime["runtimes"]["node"]["version"] == "24.21.0"
    assert runtime["runtimes"]["python"]["version"] == "3.14.8"
    assert runtime["package_managers"]["pnpm"]["version"] == "11.28.4"
    assert runtime["package_managers"]["uv"]["version"] == "0.12.23"
    assert ci["enforcement"]["required_status_context"] == "governance"
    assert ci["promotion"]["state"] == "DISABLED_PENDING_P04_D"
    assert ci["live_trading"] == "DISABLED"
    assert ci["auto_trading"] == "DISABLED"

    with (ROOT / "pyproject.toml").open("rb") as handle:
        pyproject = tomllib.load(handle)
    assert pyproject["project"]["requires-python"] == "==3.14.*"

    pnpm_lock = (ROOT / "pnpm-lock.yaml").read_text(encoding="utf-8")
    uv_lock = (ROOT / "uv.lock").read_text(encoding="utf-8")
    assert "lockfileVersion: '9.0'" in pnpm_lock
    assert 'requires-python = "==3.14.*"' in uv_lock

    print("CI_UNIT_SELF_CHECKS=PASS")


def validate_contract_against_schema(contract_path: Path) -> None:
    schema = read_json(TASK_SCHEMA)
    contract = read_json(contract_path)

    required = set(schema["required"])
    allowed = set(schema["properties"])
    keys = set(contract)

    missing = sorted(required - keys)
    extra = sorted(keys - allowed)
    if missing:
        fail(f"TASK_CONTRACT_MISSING path={contract_path.relative_to(ROOT)} keys={missing}")
    if extra:
        fail(f"TASK_CONTRACT_EXTRA path={contract_path.relative_to(ROOT)} keys={extra}")

    for key, rule in schema["properties"].items():
        if key not in contract:
            continue
        value = contract[key]
        rule_type = rule.get("type")
        if rule_type == "string" and not isinstance(value, str):
            fail(f"TASK_CONTRACT_TYPE path={contract_path.relative_to(ROOT)} key={key}")
        if rule_type == "boolean" and not isinstance(value, bool):
            fail(f"TASK_CONTRACT_TYPE path={contract_path.relative_to(ROOT)} key={key}")
        if rule_type == "array":
            if not isinstance(value, list):
                fail(f"TASK_CONTRACT_TYPE path={contract_path.relative_to(ROOT)} key={key}")
            item_type = rule.get("items", {}).get("type")
            if item_type == "string" and not all(isinstance(item, str) for item in value):
                fail(f"TASK_CONTRACT_ITEM_TYPE path={contract_path.relative_to(ROOT)} key={key}")
        if "enum" in rule and value not in rule["enum"]:
            fail(f"TASK_CONTRACT_ENUM path={contract_path.relative_to(ROOT)} key={key}")
        pattern = rule.get("pattern")
        if pattern and isinstance(value, str) and re.fullmatch(pattern, value) is None:
            fail(f"TASK_CONTRACT_PATTERN path={contract_path.relative_to(ROOT)} key={key}")

    print(f"TASK_CONTRACT_SCHEMA=PASS path={contract_path.relative_to(ROOT)}")


def changed_task_contracts() -> list[Path]:
    base = os.environ.get("CI_BASE_SHA", "").strip()
    candidates: list[Path] = []

    if base and base != "0" * 40:
        try:
            names = git("diff", "--name-only", f"{base}...HEAD")
        except subprocess.CalledProcessError:
            names = ""
        for name in names.splitlines():
            if name.startswith("contracts/tasks/") and name.endswith(".json"):
                path = ROOT / name
                if path.is_file():
                    candidates.append(path)

    if not candidates:
        candidates.append(P04C_CONTRACT)

    return sorted(set(candidates))


def check_contracts() -> None:
    # Syntax-check all tracked JSON. Structural Task Contract validation is
    # forward-only for contracts changed by the current governed change.
    for path in tracked_files("*.json"):
        json.loads(path.read_text(encoding="utf-8"))

    for path in changed_task_contracts():
        validate_contract_against_schema(path)

    print("FORWARD_CONTRACT_VALIDATION=PASS")


def check_workflow_security() -> None:
    workflow_files = tracked_files(".github/workflows/*.yml", ".github/workflows/*.yaml")
    uses_re = re.compile(r"^\s*uses:\s*([^\s#]+)", re.MULTILINE)
    sha_re = re.compile(r"^[0-9a-fA-F]{40}$")

    for path in workflow_files:
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(ROOT)

        if "pull_request_target:" in text:
            fail(f"WORKFLOW_FORBIDDEN_TRIGGER path={rel} trigger=pull_request_target")
        if re.search(r"^\s*permissions:\s*write-all\s*$", text, re.MULTILINE):
            fail(f"WORKFLOW_WRITE_ALL path={rel}")
        if re.search(r"^\s*secrets:\s*inherit\s*$", text, re.MULTILINE):
            fail(f"WORKFLOW_SECRETS_INHERIT path={rel}")

        for match in uses_re.finditer(text):
            ref = match.group(1)
            if ref.startswith("./") or ref.startswith("docker://"):
                continue
            if "@" not in ref:
                fail(f"WORKFLOW_ACTION_REF_MISSING path={rel} ref={ref}")
            _, revision = ref.rsplit("@", 1)
            if sha_re.fullmatch(revision) is None:
                fail(f"WORKFLOW_ACTION_NOT_SHA_PINNED path={rel} ref={ref}")

        if "actions/checkout@" in text:
            lines = text.splitlines()
            for index, line in enumerate(lines):
                if "actions/checkout@" not in line:
                    continue
                window = "\n".join(lines[index : index + 8])
                if "persist-credentials: false" not in window:
                    fail(f"CHECKOUT_CREDENTIAL_PERSISTENCE path={rel} line={index + 1}")

    for path in tracked_files():
        rel = path.relative_to(ROOT).as_posix()
        if ALLOWED_SECRET_TEMPLATE.search(rel):
            continue
        if any(pattern.search(rel) for pattern in SECRET_FILE_PATTERNS):
            fail(f"TRACKED_SECRET_FILENAME path={rel}")

    print("WORKFLOW_SECURITY=PASS")


def check_promotion_disabled() -> None:
    ci = read_json(CI_MANIFEST)
    if ci["promotion"]["state"] != "DISABLED_PENDING_P04_D":
        fail("PROMOTION_STATE_NOT_DISABLED")

    for path in tracked_files(".github/workflows/*.yml", ".github/workflows/*.yaml"):
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(ROOT)
        if re.search(r"^\s*environment:\s*", text, re.MULTILINE):
            fail(f"PROMOTION_ENVIRONMENT_PRESENT path={rel}")
        if re.search(r"^\s*deployments:\s*write\s*$", text, re.MULTILINE):
            fail(f"DEPLOYMENT_PERMISSION_PRESENT path={rel}")
        if re.search(r"^\s*id-token:\s*write\s*$", text, re.MULTILINE):
            fail(f"OIDC_WRITE_PRESENT path={rel}")

    roadmap = (ROOT / "docs/01-roadmap/MASTER-ROADMAP-v2.0.md").read_text(encoding="utf-8")
    for marker in ("LIVE_TRADING = DISABLED", "AUTO_TRADING = DISABLED"):
        if marker not in roadmap:
            fail(f"SAFETY_MARKER_MISSING marker={marker}")

    print("PROMOTION_DISABLED=PASS")


BUILD_INPUTS = [
    ".node-version",
    ".python-version",
    "package.json",
    "pnpm-workspace.yaml",
    "pnpm-lock.yaml",
    "pyproject.toml",
    "uv.lock",
    "docs/06-engineering/WORKSPACE-STRUCTURE.md",
    "docs/06-engineering/workspace-structure.json",
    "docs/06-engineering/RUNTIME-DEPENDENCY-BASELINE.md",
    "docs/06-engineering/runtime-dependency-baseline.json",
    "docs/06-engineering/CI-CD-FOUNDATION.md",
    "docs/06-engineering/ci-cd-foundation.json",
    "contracts/tasks/FIN-P04-WC-001.json",
    "contracts/tasks/FIN-P04-WD-001.json",
    "docs/06-engineering/CONFIG-ENVIRONMENT-CONTRACT.md",
    "docs/06-engineering/config-environment-contract.json",
    "config/README.md",
    "config/environment-config.schema.json",
    "config/config-policy.json",
    "config/base.json",
    "config/runtime-overrides.example.json",
    "config/environments/dev.json",
    "config/environments/test.json",
    "config/environments/research.json",
    "config/environments/demo.json",
    "config/environments/shadow.json",
    "config/environments/canary.json",
    "config/environments/live.json",
    "scripts/ci/config_contract.py",
    "contracts/tasks/FIN-P04-WE-001.json",
    "docs/06-engineering/TEST-HARNESS.md",
    "docs/06-engineering/test-harness.json",
    "tests/README.md",
    "tests/__init__.py",
    "tests/harness/__init__.py",
    "tests/harness/core.py",
    "tests/foundation/__init__.py",
    "tests/foundation/test_harness.py",
    "tests/fixtures/foundation/replay-basic.json",
    "tests/fixtures/foundation/provider-unknown.json",
    "scripts/ci/test_harness_evidence.py",
    "contracts/tasks/FIN-P04-WF-001.json",
    "docs/06-engineering/DEPENDENCY-LICENSE-SBOM-GOVERNANCE.md",
    "docs/06-engineering/dependency-license-sbom-governance.json",
    "config/supply-chain/dependency-policy.json",
    "config/supply-chain/license-policy.json",
    "config/supply-chain/waivers.json",
    ".trivyignore",
    "scripts/ci/supply_chain_policy.py",
    "scripts/ci/supply_chain_evidence.py",
    "contracts/tasks/FIN-P04-WG-001.json",
    "docs/06-engineering/DEVELOPER-TOOLING.md",
    "docs/06-engineering/developer-tooling.json",
    "scripts/dev/__init__.py",
    "scripts/dev/common.py",
    "scripts/dev/doctor.py",
    "scripts/dev/bootstrap.py",
    "scripts/dev/local_gate.py",
    "scripts/dev/install_hooks.py",
    "scripts/dev/hooks/pre-commit",
    "scripts/dev/hooks/pre-push",
    "scripts/ci/developer_tooling_contract.py",
    "contracts/tasks/FIN-P04-WH-001.json",
    "docs/06-engineering/REPRODUCIBLE-BUILD-EVIDENCE.md",
    "docs/06-engineering/reproducible-build-evidence.json",
    "scripts/ci/reproducible_build.py",
    "tests/foundation/test_reproducible_build.py",
    "scripts/ci/p04_exit.py",
    "contracts/tasks/FIN-P05-WA-001.json",
    "docs/07-data/P05-A-CRYPTO-REALTIME-ADAPTER.md",
    "docs/07-data/p05-a-crypto-realtime-adapter.json",
    "packages/contracts/market_data.py",
    "adapters/market_data/kaiko.py",
    "tests/p05/test_kaiko_adapter.py",
    "tests/p05/fixtures/kaiko_trade.json",
    "tests/p05/fixtures/kaiko_orderbook_snapshot.json",
    "tests/p05/fixtures/kaiko_orderbook_update.json",
    "scripts/ci/p05a_evidence.py",
    "contracts/tasks/FIN-P05-WA-001-R01.json",
    "docs/07-data/P05-A-FRESH-REVALIDATION.md",
    "docs/07-data/p05-a-fresh-revalidation.json",
    "scripts/ci/p05a_revalidation.py",
    "tests/foundation/test_p04_exit.py",
    "contracts/tasks/FIN-P05-WB-001.json",
    "docs/07-data/P05-B-FOREX-REALTIME-ADAPTER.md",
    "docs/07-data/p05-b-forex-realtime-adapter.json",
    "adapters/market_data/dxfeed.py",
    "tests/p05/test_dxfeed_adapter.py",
    "tests/p05/fixtures/dxfeed_eurusd_quote.json",
    "scripts/ci/p05b_evidence.py",
    "contracts/tasks/FIN-P05-WC-001.json",
    "docs/07-data/P05-C-CONTEXT-MARKET-ADAPTER.md",
    "docs/07-data/p05-c-context-market-adapter.json",
    "adapters/market_data/databento.py",
    "tests/p05/test_databento_context_adapter.py",
    "tests/p05/fixtures/databento_gc_mbp1.json",
    "scripts/ci/p05c_evidence.py",
    "contracts/tasks/FIN-P05-WD-001.json",
    "config/market-data/symbol-master.json",
    "config/market-data/clock-model.json",
    "packages/market_data/__init__.py",
    "packages/market_data/symbol_master.py",
    "packages/market_data/normalization.py",
    "tests/p05/test_canonical_normalization.py",
    "scripts/ci/p05d_evidence.py",
    "docs/07-data/P05-D-CANONICAL-NORMALIZATION-SYMBOL-CLOCK.md",
    "docs/07-data/p05-d-canonical-normalization-symbol-clock.json",
    "contracts/tasks/FIN-P05-WE-001.json",
    "config/market-data/streaming-policy.json",
    "packages/market_data/streaming.py",
    "tests/p05/test_streaming_heartbeat_backpressure.py",
    "scripts/ci/p05e_evidence.py",
    "docs/07-data/P05-E-STREAMING-HEARTBEAT-BACKPRESSURE.md",
    "docs/07-data/p05-e-streaming-heartbeat-backpressure.json",
    "contracts/tasks/FIN-P05-WF-001.json",
    "config/market-data/recovery-policy.json",
    "packages/market_data/recovery.py",
    "tests/p05/test_reconnect_failover_gap_recovery.py",
    "scripts/ci/p05f_evidence.py",
    "docs/07-data/P05-F-RECONNECT-FAILOVER-GAP-RECOVERY.md",
    "docs/07-data/p05-f-reconnect-failover-gap-recovery.json",
    "contracts/tasks/FIN-P05-WG-001.json",
    "config/market-data/performance-policy.json",
    "tests/p05/test_performance_policy.py",
    "scripts/ci/p05g_performance.py",
    "scripts/ci/p05g_contract_evidence.py",
    "docs/07-data/P05-G-LATENCY-THROUGHPUT-SOAK-VALIDATION.md",
    "docs/07-data/p05-g-latency-throughput-soak-validation.json",
    "contracts/tasks/FIN-P05-WH-001.json",
    "docs/07-data/P05-H-REALTIME-DATA-GATE.md",
    "docs/07-data/p05-h-realtime-data-gate.json",
    "docs/00-governance/G4-REALTIME-DATA.md",
    "scripts/ci/p05_exit.py",
    "contracts/tasks/FIN-P06-WA-001.json",
    "config/historical-data/raw-archive-policy.json",
    "packages/historical_data/__init__.py",
    "packages/historical_data/raw_archive.py",
    "tests/p06/__init__.py",
    "tests/p06/test_raw_archive.py",
    "scripts/ci/p06a_evidence.py",
    "docs/07-data/P06-A-IMMUTABLE-RAW-ARCHIVE.md",
    "docs/07-data/p06-a-immutable-raw-archive.json",
    "contracts/tasks/FIN-P06-WB-001.json",
    "config/historical-data/backfill-policy.json",
    "packages/historical_data/backfill.py",
    "tests/p06/test_historical_backfill.py",
    "scripts/ci/p06b_evidence.py",
    "docs/07-data/P06-B-HISTORICAL-BACKFILL.md",
    "docs/07-data/p06-b-historical-backfill.json",
    "contracts/tasks/FIN-P06-WC-001.json",
    "config/historical-data/query-layer-policy.json",
    "packages/historical_data/query_layer.py",
    "tests/p06/test_time_series_query_layer.py",
    "scripts/ci/p06c_evidence.py",
    "scripts/ci/p06c_performance.py",
    "docs/07-data/P06-C-TIME-SERIES-QUERY-LAYER.md",
    "docs/07-data/p06-c-time-series-query-layer.json",
    "contracts/tasks/FIN-P06-WD-001.json",
    "config/historical-data/dataset-manifest-policy.json",
    "packages/historical_data/dataset_manifest.py",
    "tests/p06/test_dataset_manifest.py",
    "scripts/ci/p06d_evidence.py",
    "docs/07-data/P06-D-DATASET-MANIFESTS-VERSIONING.md",
    "docs/07-data/p06-d-dataset-manifests-versioning.json",
    "pyrightconfig.json",
    "docs/06-engineering/P04-ENGINEERING-FOUNDATION-CLOSURE.md",
    "docs/06-engineering/p04-engineering-foundation-closure.json",
    "contracts/tasks/FIN-P04-WH-001-R01.json",
    "contracts/tasks/FIN-P04-WH-001-R02.json",
    "docs/06-engineering/P04-POST-CLOSURE-AUDIT.md",
    "docs/06-engineering/p04-post-closure-audit.json",
    "docs/02-current-state/BUILD-READINESS-CHECKLIST.md",
    "docs/01-roadmap/EXECUTION-ROADMAP.md",
    "scripts/ci/foundation_ci.py",
    ".github/workflows/governance.yml",
    ".github/workflows/branch-hygiene.yml",
]


def build_manifest(output: Path) -> None:
    files = []
    for relative in sorted(BUILD_INPUTS):
        path = ROOT / relative
        if not path.is_file():
            fail(f"BUILD_INPUT_MISSING path={relative}")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        files.append({"path": relative, "sha256": digest})

    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_FOUNDATION_CI_MANIFEST",
        "source_sha": git("rev-parse", "HEAD"),
        "files": files,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"FOUNDATION_BUILD=PASS output={output}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode",
        choices=("lint", "typecheck", "unit", "contract", "security", "promotion", "build"),
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    try:
        if args.mode == "lint":
            check_lint()
        elif args.mode == "typecheck":
            check_typecheck_readiness()
        elif args.mode == "unit":
            check_unit()
        elif args.mode == "contract":
            check_contracts()
        elif args.mode == "security":
            check_workflow_security()
        elif args.mode == "promotion":
            check_promotion_disabled()
        elif args.mode == "build":
            if args.output is None:
                fail("BUILD_OUTPUT_REQUIRED")
            build_manifest(args.output)
    except (AssertionError, CheckFailure, KeyError, subprocess.CalledProcessError) as exc:
        print(f"FOUNDATION_CI=FAIL mode={args.mode} error={exc}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
