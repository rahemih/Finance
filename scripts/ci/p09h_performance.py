#!/usr/bin/env python3
"""Measure the P09 unit-suite CI regression budget.

This is deliberately an offline CI regression budget, not a production SLO.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.order_flow_liquidity.p09_validation import P09ValidationPolicy

POLICY_PATH = ROOT / "config/order-flow-liquidity/p09-validation-policy.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    policy = P09ValidationPolicy.from_path(POLICY_PATH)
    command = [
        sys.executable,
        "-m",
        "unittest",
        "discover",
        "-s",
        "tests/p09",
        "-p",
        "test_*.py",
    ]
    started = time.perf_counter()
    timed_out = False
    return_code = 1
    stdout = ""
    stderr = ""
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=policy.p09_unit_suite_max_seconds,
            check=False,
        )
        return_code = completed.returncode
        stdout = completed.stdout
        stderr = completed.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""

    elapsed = time.perf_counter() - started
    passed = (
        not timed_out
        and return_code == 0
        and elapsed <= policy.p09_unit_suite_max_seconds
    )

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P09H_CI_REGRESSION_PERFORMANCE_EVIDENCE",
        "task_id": "FIN-P09-WH-001",
        "performance_semantics": policy.performance_semantics,
        "production_slo_certified": policy.production_slo_certified,
        "production_provider_performance_certified": policy.production_provider_performance_certified,
        "network_required": policy.network_required,
        "command": command[1:],
        "elapsed_seconds": round(elapsed, 6),
        "budget_seconds": policy.p09_unit_suite_max_seconds,
        "timed_out": timed_out,
        "return_code": return_code,
        "passed": passed,
        "runner": {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "platform": platform.platform()
        }
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    if not passed:
        if stdout:
            print(stdout, file=sys.stderr)
        if stderr:
            print(stderr, file=sys.stderr)
        print(
            f"P09H_PERFORMANCE=FAIL elapsed={elapsed:.6f}s "
            f"budget={policy.p09_unit_suite_max_seconds}s output={args.output}",
            file=sys.stderr,
        )
        return 1

    print(
        f"P09H_PERFORMANCE=PASS elapsed={elapsed:.6f}s "
        f"budget={policy.p09_unit_suite_max_seconds}s output={args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
