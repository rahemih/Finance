"""P24-CI #518: offline tests of mandatory digest-pinned Trivy OCI gate.

A fake Docker executable tests refusal semantics only. These tests never claim
that a real Trivy vulnerability scan, container pull or vulnerability DB ran.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "scripts" / "ci" / "run_trivy_oci.sh"
VERIFIER = ROOT / "scripts" / "ci" / "verify_trivy_scan.py"
WORKFLOW = ROOT / ".github" / "workflows" / "governance.yml"
IMAGE_DIGEST = "sha256:9db099105405c648166e6b94155eb32f8da12673cf1f455207f7385cc9a77283"

FAKE_DOCKER = r'''#!/usr/bin/env python3
import json
import os
from pathlib import Path
import sys

argv = sys.argv[1:]
mode = os.environ.get("TEST_DOCKER_MODE", "clean")
root = Path(os.environ["TEST_DOCKER_ROOT"])
with (root / "docker-calls.jsonl").open("a", encoding="utf-8") as f:
    f.write(json.dumps(argv) + "\n")
if argv and argv[0] == "pull":
    if mode == "pullfail" or (mode == "primaryfail" and "ghcr.io/" in argv[-1]):
        sys.exit(1)
    sys.exit(0)
if argv and argv[0] == "run":
    if "--version" in argv:
        print("Version: 0.74.0" if mode == "wrongversion" else "Version: 0.75.0")
        sys.exit(0)
    if mode == "scan_error":
        sys.exit(1)
    dest = root / "build" / "trivy.json"
    if mode == "missing":
        sys.exit(0)
    if mode == "malformed":
        dest.write_text("not json", encoding="utf-8")
        sys.exit(0)
    if mode == "fake_high":
        issues = [{"Severity": "HIGH", "VulnerabilityID": "SYNTHETIC-CVE"}]
    else:
        issues = []
    if mode == "fake_secret":
        result = {"Target": "file", "Secrets": [{"Severity": "CRITICAL", "RuleID": "SYNTHETIC_SECRET"}]}
    else:
        result = {"Target": "package.json", "Vulnerabilities": issues}
    report = {"SchemaVersion": 2, "ArtifactType": "filesystem",
              "ArtifactName": "/scan", "Results": [result]}
    dest.write_text(json.dumps(report), encoding="utf-8")
    sys.exit(0)
sys.exit(2)
'''


class TrivyOCIContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="finance-trivy-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "scripts" / "ci").mkdir(parents=True)
        (self.root / "config" / "supply-chain").mkdir(parents=True)
        (self.root / "bin").mkdir()
        (self.root / "temp").mkdir()
        (self.root / ".trivyignore").write_text("# no waiver\n", encoding="utf-8")
        (self.root / "config" / "supply-chain" / "dependency-policy.json").write_text(
            "{}", encoding="utf-8")
        shutil.copyfile(RUNNER, self.root / "scripts" / "ci" / RUNNER.name)
        shutil.copyfile(VERIFIER, self.root / "scripts" / "ci" / VERIFIER.name)
        docker = self.root / "bin" / "docker"
        docker.write_text(FAKE_DOCKER, encoding="utf-8")
        docker.chmod(0o755)

    def invoke(self, mode: str = "clean") -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["PATH"] = str(self.root / "bin") + os.pathsep + env.get("PATH", "")
        env["RUNNER_TEMP"] = str(self.root / "temp")
        env["TEST_DOCKER_MODE"] = mode
        env["TEST_DOCKER_ROOT"] = str(self.root)
        return subprocess.run(
            ["bash", str(self.root / "scripts" / "ci" / RUNNER.name)],
            cwd=self.root, env=env, capture_output=True, text=True, check=False, timeout=15,
        )

    def calls(self) -> list[list[str]]:
        path = self.root / "docker-calls.jsonl"
        return [json.loads(row) for row in path.read_text(encoding="utf-8").splitlines()]

    def test_clean_fixture_path_reports_verifier_pass_only(self) -> None:
        p = self.invoke()
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("TRIVY_REPORT_VALIDATED=PASS", p.stdout)
        self.assertIn("TRIVY_OCI_SCANNER_VERIFIED=PASS", p.stdout)

    def test_official_digest_pinned_both_registries(self) -> None:
        p = self.invoke("primaryfail")
        self.assertEqual(p.returncode, 0, p.stderr)
        pulls = [x for x in self.calls() if x[0] == "pull"]
        self.assertEqual(len(pulls), 2)
        self.assertIn("ghcr.io/aquasecurity/trivy@" + IMAGE_DIGEST, pulls[0])
        self.assertIn("docker.io/aquasec/trivy@" + IMAGE_DIGEST, pulls[1])

    def test_both_registry_unavailable_is_failure(self) -> None:
        p = self.invoke("pullfail")
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("TRIVY_PINNED_OFFICIAL_IMAGE_UNAVAILABLE", p.stderr)
        self.assertFalse((self.root / "build" / "trivy.json").exists())

    def test_binary_version_mismatch_is_failure(self) -> None:
        p = self.invoke("wrongversion")
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("TRIVY_BINARY_VERSION_MISMATCH", p.stderr)

    def test_actual_scanner_error_remains_failure(self) -> None:
        self.assertNotEqual(self.invoke("scan_error").returncode, 0)

    def test_missing_report_remains_failure(self) -> None:
        p = self.invoke("missing")
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("TRIVY_REPORT_MISSING_OR_INVALID_SIZE", p.stderr)

    def test_malformed_report_remains_failure(self) -> None:
        p = self.invoke("malformed")
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("TRIVY_REPORT_NOT_VALID_JSON", p.stderr)

    def test_independent_validator_rejects_high_even_if_scanner_returned_zero(self) -> None:
        p = self.invoke("fake_high")
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("TRIVY_HIGH_CRITICAL_FINDINGS_BLOCKED", p.stderr)

    def test_independent_validator_rejects_critical_secret(self) -> None:
        p = self.invoke("fake_secret")
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("TRIVY_HIGH_CRITICAL_FINDINGS_BLOCKED", p.stderr)

    def test_real_command_fidelity_without_docker_socket(self) -> None:
        self.assertEqual(self.invoke().returncode, 0)
        scans = [x for x in self.calls() if "fs" in x]
        self.assertEqual(len(scans), 1)
        scan = scans[0]
        for flag, expected in [
            ("--scanners", "vuln,misconfig,secret"),
            ("--severity", "HIGH,CRITICAL"),
            ("--exit-code", "1"),
            ("--format", "json"),
            ("--ignorefile", "/scan/.trivyignore"),
        ]:
            self.assertEqual(scan[scan.index(flag) + 1], expected)
        self.assertIn("--read-only", scan)
        self.assertIn("--cap-drop", scan)
        self.assertIn("--security-opt", scan)
        self.assertNotIn("/var/run/docker.sock", " ".join(scan))
        self.assertNotIn("--privileged", scan)
        self.assertIn(":/scan:ro", " ".join(scan))
        self.assertEqual(scan[-1], "/scan")

    def test_mandatory_workflow_and_other_stages_preserved(self) -> None:
        wf = WORKFLOW.read_text(encoding="utf-8")
        self.assertEqual(wf.count("      - name: Trivy supply-chain scan"), 1)
        self.assertIn("run: bash scripts/ci/run_trivy_oci.sh", wf)
        self.assertNotIn("aquasecurity/trivy-action@", wf)
        self.assertIn("      - name: Validate SBOM / license policy", wf)
        self.assertIn("      - name: Build supply-chain evidence", wf)
        self.assertIn("      - name: P24 controlled production contract tests", wf)

    def test_no_security_downgrade_or_network_suppression(self) -> None:
        src = RUNNER.read_text(encoding="utf-8")
        for mandatory in ("--scanners vuln,misconfig,secret", "--severity HIGH,CRITICAL",
                          "--exit-code 1", "--ignorefile /scan/.trivyignore",
                          "--network bridge", "sha256:9db099105405"):
            self.assertIn(mandatory, src)
        for bypass in ("--skip-db-update", "--skip-vuln-update", "--offline-scan",
                       "--ignore-unfixed", "continue-on-error", "|| true", "--privileged"):
            self.assertNotIn(bypass, src)


if __name__ == "__main__":
    unittest.main()
