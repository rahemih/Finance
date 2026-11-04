"""Static guards for mandatory Trivy OCI scan — synthetic checks, not a scan PASS."""
from __future__ import annotations

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/governance.yml"
MANIFEST_DIGEST = "sha256:9db099105405c648166e6b94155eb32f8da12673cf1f455207f7385cc9a77283"


def trivy_block() -> str:
    source = WORKFLOW.read_text(encoding="utf-8")
    first = source.split("      - name: Trivy supply-chain scan\n", 1)
    if len(first) != 2:
        raise AssertionError("Required Trivy gate missing")
    return first[1].split("      - name: Build supply-chain evidence\n", 1)[0]


class TrivyOciNoBypassTests(unittest.TestCase):
    def test_immutable_official_version_and_digest(self) -> None:
        section = trivy_block()
        self.assertIn("docker.io/aquasec/trivy@" + MANIFEST_DIGEST, section)
        self.assertIn("--platform linux/amd64", section)
        self.assertIn("grep -qx 'Version: 0.75.0'", section)
        self.assertNotIn(":latest", section)
        self.assertNotIn("trivy-action@", section)

    def test_three_original_scanners_mandatory(self) -> None:
        section = trivy_block()
        self.assertIn("--scanners vuln,misconfig,secret", section)
        self.assertIn("--severity HIGH,CRITICAL", section)
        self.assertIn("--ignore-unfixed=false", section)
        self.assertIn("--exit-code 1", section)
        self.assertIn("--ignorefile .trivyignore", section)
        self.assertNotIn("--ignore-unfixed=true", section)
        self.assertNotIn("--exit-code 0", section)

    def test_scan_json_mandatory_for_next_step(self) -> None:
        section = trivy_block()
        self.assertIn("--output /scan-output/trivy.json", section)
        self.assertIn("test -s build/trivy.json", section)
        self.assertIn("python -m json.tool build/trivy.json", section)
        self.assertIn("rm -f build/trivy.json", section)
        self.assertIn("set -euo pipefail", section)
        self.assertNotIn("continue-on-error", section)

    def test_container_does_not_mount_docker_socket_or_privilege(self) -> None:
        section = trivy_block()
        self.assertIn("--read-only", section)
        self.assertIn("--cap-drop ALL", section)
        self.assertIn("--security-opt no-new-privileges", section)
        self.assertIn("--user", section)
        self.assertIn("target=/workspace,readonly", section)
        self.assertIn("target=/scan-output", section)
        self.assertIn("--env TRIVY_CACHE_DIR=/trivy-cache", section)
        self.assertIn("source=$RUNNER_TEMP/p24-trivy-cache,target=/trivy-cache", section)
        self.assertIn("mkdir -p build \"$RUNNER_TEMP/p24-trivy-cache\"", section)
        self.assertNotIn("/var/run/docker.sock", section)
        self.assertNotIn("--privileged", section)

    def test_downstream_supply_chain_evidence_and_artifact_retained(self) -> None:
        source = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python scripts/ci/supply_chain_policy.py sbom --sbom build/sbom.cdx.json", source)
        self.assertIn("--trivy build/trivy.json", source)
        self.assertIn("build/supply-chain-summary.json", source)
        self.assertIn("build/trivy.json", source)
        self.assertIn("name: foundation-ci-manifest", source)
        self.assertIn("if-no-files-found: error", source)

    def test_trivy_step_must_be_executable_not_only_comment(self) -> None:
        section = trivy_block()
        self.assertRegex(section, r'(?m)^          docker run --rm --platform linux/amd64')
        self.assertRegex(section, r'(?m)^            "\$TRIVY_IMAGE" fs')
        self.assertNotRegex(section, r'(?m)^\s*#\s*docker run')
        self.assertNotIn("|| true", section)

    def test_no_alternate_security_waiver(self) -> None:
        section = trivy_block()
        for bad in ("TRIVY_SKIP", "TRIVY_IGNORE_UNFIXED", "exit 0", "continue-on-error: true",
                    "--skip-db-update", "--skip-java-db-update"):
            with self.subTest(token=bad):
                self.assertNotIn(bad, section)
        self.assertIsNone(re.search(r"(?m)^\s*if:.*false", section))

    def test_scan_is_proposed_not_proven_by_unit_tests(self) -> None:
        section = trivy_block()
        self.assertIn("docker pull --platform linux/amd64", section)
        self.assertIn("--format json", section)


if __name__ == "__main__":
    unittest.main()
