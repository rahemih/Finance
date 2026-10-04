from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from scripts.ci.reproducible_build import build, verify, ReproducibleBuildError


SOURCE_SHA = "a" * 40


class ReproducibleBuildTests(unittest.TestCase):
    def make_tree(self, root: Path) -> None:
        (root / "docs").mkdir(parents=True)
        (root / "scripts").mkdir(parents=True)
        (root / "docs/example.txt").write_text("alpha\n", encoding="utf-8")
        script = root / "scripts/run.sh"
        script.write_text("#!/bin/sh\necho ok\n", encoding="utf-8")
        script.chmod(0o755)

    def test_identical_source_builds_are_byte_identical(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            root = base / "source"
            root.mkdir()
            self.make_tree(root)

            a = base / "a.tar"
            am = base / "a.json"
            b = base / "b.tar"
            bm = base / "b.json"
            build(root, SOURCE_SHA, a, am)
            build(root, SOURCE_SHA, b, bm)

            self.assertEqual(a.read_bytes(), b.read_bytes())
            self.assertEqual(am.read_bytes(), bm.read_bytes())
            verify(a, am, SOURCE_SHA)

    def test_source_change_changes_artifact_digest(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            root = base / "source"
            root.mkdir()
            self.make_tree(root)

            a = base / "a.tar"
            am = base / "a.json"
            b = base / "b.tar"
            bm = base / "b.json"
            build(root, SOURCE_SHA, a, am)
            (root / "docs/example.txt").write_text("beta\n", encoding="utf-8")
            build(root, SOURCE_SHA, b, bm)

            aj = json.loads(am.read_text(encoding="utf-8"))
            bj = json.loads(bm.read_text(encoding="utf-8"))
            self.assertNotEqual(aj["artifact"]["sha256"], bj["artifact"]["sha256"])

    def test_generated_directories_are_excluded(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            root = base / "source"
            root.mkdir()
            self.make_tree(root)
            for name in ("node_modules", ".venv", "build", "__pycache__"):
                path = root / name
                path.mkdir(parents=True)
                (path / "ignored.txt").write_text("secret-ish-local-data\n", encoding="utf-8")

            artifact = base / "out.tar"
            manifest = base / "out.json"
            build(root, SOURCE_SHA, artifact, manifest)
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            paths = [entry["path"] for entry in payload["files"]]
            self.assertFalse(any("ignored.txt" in path for path in paths))

    def test_verify_detects_artifact_tamper(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            root = base / "source"
            root.mkdir()
            self.make_tree(root)
            artifact = base / "out.tar"
            manifest = base / "out.json"
            build(root, SOURCE_SHA, artifact, manifest)

            artifact.write_bytes(artifact.read_bytes() + b"tamper")
            with self.assertRaises(ReproducibleBuildError):
                verify(artifact, manifest, SOURCE_SHA)

    def test_verify_detects_source_sha_mismatch(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            root = base / "source"
            root.mkdir()
            self.make_tree(root)
            artifact = base / "out.tar"
            manifest = base / "out.json"
            build(root, SOURCE_SHA, artifact, manifest)

            with self.assertRaises(ReproducibleBuildError):
                verify(artifact, manifest, "b" * 40)


if __name__ == "__main__":
    unittest.main()
