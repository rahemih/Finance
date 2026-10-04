#!/usr/bin/env python3
"""Deterministic P04-H foundation artifact builder and verifier."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tarfile
from typing import Iterable

EXCLUDED_PARTS = {
    ".git",
    "node_modules",
    ".venv",
    "build",
    "dist",
    ".cache",
    ".pytest_cache",
    "__pycache__",
    ".mypy_cache",
    ".ruff_cache",
    ".pnpm-store",
    ".tox",
}
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
TOOLCHAIN = {
    "node": "24.21.0",
    "pnpm": "11.28.4",
    "python": "3.14.8",
    "uv": "0.12.23",
}


class ReproducibleBuildError(RuntimeError):
    pass


def fail(message: str) -> None:
    raise ReproducibleBuildError(message)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_excluded(relative: Path) -> bool:
    return any(part in EXCLUDED_PARTS for part in relative.parts)


def safe_archive_name(name: str) -> None:
    pure = PurePosixPath(name)
    if pure.is_absolute() or ".." in pure.parts or not pure.parts:
        fail(f"UNSAFE_ARCHIVE_PATH path={name}")


def collect_entries(root: Path) -> list[dict]:
    root = root.resolve()
    if not root.is_dir():
        fail(f"ROOT_NOT_DIRECTORY path={root}")

    entries: list[dict] = []
    for path in sorted(root.rglob("*"), key=lambda p: p.relative_to(root).as_posix()):
        relative = path.relative_to(root)
        if is_excluded(relative):
            continue
        if path.is_dir():
            continue

        rel = relative.as_posix()
        safe_archive_name(rel)
        st = path.lstat()

        if stat.S_ISLNK(st.st_mode):
            target = os.readlink(path)
            digest = sha256_bytes(("symlink:" + target).encode("utf-8"))
            entries.append(
                {
                    "path": rel,
                    "type": "symlink",
                    "mode": "0777",
                    "size": 0,
                    "sha256": digest,
                    "link_target": target,
                }
            )
            continue

        if not stat.S_ISREG(st.st_mode):
            fail(f"UNSUPPORTED_SOURCE_TYPE path={rel}")

        executable = bool(st.st_mode & stat.S_IXUSR)
        mode = "0755" if executable else "0644"
        data = path.read_bytes()
        entries.append(
            {
                "path": rel,
                "type": "file",
                "mode": mode,
                "size": len(data),
                "sha256": sha256_bytes(data),
            }
        )
    return entries


def inventory_digest(entries: Iterable[dict]) -> str:
    payload = json.dumps(
        list(entries),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return sha256_bytes(payload)


def build_tar(root: Path, entries: list[dict], output: Path) -> None:
    root = root.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(output, "w", format=tarfile.GNU_FORMAT) as archive:
        for entry in entries:
            name = entry["path"]
            source = root / name
            info = tarfile.TarInfo(name=name)
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""
            info.mtime = 0
            info.mode = int(entry["mode"], 8)

            if entry["type"] == "symlink":
                info.type = tarfile.SYMTYPE
                info.linkname = entry["link_target"]
                info.size = 0
                archive.addfile(info)
                continue

            info.type = tarfile.REGTYPE
            data = source.read_bytes()
            info.size = len(data)
            from io import BytesIO

            archive.addfile(info, BytesIO(data))


def build_manifest(source_sha: str, artifact: Path, entries: list[dict]) -> dict:
    if SHA_RE.fullmatch(source_sha) is None:
        fail(f"SOURCE_SHA_INVALID value={source_sha}")
    return {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P04_FOUNDATION_ROLLBACK_MANIFEST",
        "source_sha": source_sha,
        "artifact": {
            "name": "foundation-source.tar",
            "sha256": sha256_file(artifact),
            "size_bytes": artifact.stat().st_size,
            "format": "tar",
        },
        "file_inventory_sha256": inventory_digest(entries),
        "file_count": len(entries),
        "files": entries,
        "toolchain": TOOLCHAIN,
        "normalization": {
            "mtime": 0,
            "uid": 0,
            "gid": 0,
            "uname": "",
            "gname": "",
            "path_order": "LEXICAL",
        },
        "excluded_roots": sorted(EXCLUDED_PARTS),
        "safety": {
            "production_deployment": "NONE",
            "canary": "DISABLED",
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        },
    }


def write_manifest(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def build(root: Path, source_sha: str, output: Path, manifest: Path) -> None:
    entries = collect_entries(root)
    if not entries:
        fail("SOURCE_TREE_EMPTY")
    build_tar(root, entries, output)
    payload = build_manifest(source_sha, output, entries)
    write_manifest(manifest, payload)
    print(f"REPRODUCIBLE_BUILD=PASS artifact={output} sha256={payload['artifact']['sha256']}")
    print(f"ROLLBACK_MANIFEST=PASS files={payload['file_count']} inventory_sha256={payload['file_inventory_sha256']}")


def load_manifest(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"MANIFEST_INVALID error={exc}")
    if not isinstance(value, dict):
        fail("MANIFEST_OBJECT_REQUIRED")
    return value


def verify_member(member: tarfile.TarInfo, expected: dict, archive: tarfile.TarFile) -> None:
    safe_archive_name(member.name)
    if any(part in EXCLUDED_PARTS for part in PurePosixPath(member.name).parts):
        fail(f"EXCLUDED_PATH_PRESENT path={member.name}")

    if member.name != expected["path"]:
        fail(f"MEMBER_PATH_MISMATCH actual={member.name} expected={expected['path']}")
    if f"{member.mode & 0o7777:04o}" != expected["mode"]:
        fail(f"MEMBER_MODE_MISMATCH path={member.name}")

    if expected["type"] == "symlink":
        if not member.issym():
            fail(f"MEMBER_TYPE_MISMATCH path={member.name}")
        if member.linkname != expected["link_target"]:
            fail(f"SYMLINK_TARGET_MISMATCH path={member.name}")
        digest = sha256_bytes(("symlink:" + member.linkname).encode("utf-8"))
        if digest != expected["sha256"]:
            fail(f"SYMLINK_DIGEST_MISMATCH path={member.name}")
        return

    if not member.isfile():
        fail(f"MEMBER_TYPE_MISMATCH path={member.name}")
    extracted = archive.extractfile(member)
    if extracted is None:
        fail(f"MEMBER_READ_FAIL path={member.name}")
    data = extracted.read()
    if len(data) != expected["size"]:
        fail(f"MEMBER_SIZE_MISMATCH path={member.name}")
    if sha256_bytes(data) != expected["sha256"]:
        fail(f"MEMBER_DIGEST_MISMATCH path={member.name}")


def verify(artifact: Path, manifest_path: Path, expected_source_sha: str | None) -> None:
    manifest = load_manifest(manifest_path)
    if manifest.get("schema_version") != "1.0":
        fail("MANIFEST_SCHEMA_VERSION_INVALID")
    if manifest.get("kind") != "NEXUS_QUANT_P04_FOUNDATION_ROLLBACK_MANIFEST":
        fail("MANIFEST_KIND_INVALID")

    source_sha = manifest.get("source_sha")
    if not isinstance(source_sha, str) or SHA_RE.fullmatch(source_sha) is None:
        fail("MANIFEST_SOURCE_SHA_INVALID")
    if expected_source_sha is not None and source_sha != expected_source_sha:
        fail(f"SOURCE_SHA_MISMATCH actual={source_sha} expected={expected_source_sha}")

    artifact_meta = manifest.get("artifact")
    if not isinstance(artifact_meta, dict):
        fail("MANIFEST_ARTIFACT_OBJECT_REQUIRED")
    actual_sha = sha256_file(artifact)
    if artifact_meta.get("sha256") != actual_sha:
        fail(f"ARTIFACT_SHA_MISMATCH actual={actual_sha} expected={artifact_meta.get('sha256')}")
    if artifact_meta.get("size_bytes") != artifact.stat().st_size:
        fail("ARTIFACT_SIZE_MISMATCH")

    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        fail("MANIFEST_FILES_REQUIRED")
    if manifest.get("file_count") != len(files):
        fail("MANIFEST_FILE_COUNT_MISMATCH")
    if manifest.get("file_inventory_sha256") != inventory_digest(files):
        fail("MANIFEST_INVENTORY_DIGEST_MISMATCH")

    expected_paths = [entry.get("path") for entry in files]
    if expected_paths != sorted(expected_paths):
        fail("MANIFEST_PATH_ORDER_INVALID")
    if len(expected_paths) != len(set(expected_paths)):
        fail("MANIFEST_DUPLICATE_PATH")

    with tarfile.open(artifact, "r:") as archive:
        members = archive.getmembers()
        actual_paths = [member.name for member in members]
        if actual_paths != expected_paths:
            fail("ARCHIVE_MEMBER_SET_OR_ORDER_MISMATCH")
        for member, expected in zip(members, files, strict=True):
            verify_member(member, expected, archive)

    if manifest.get("toolchain") != TOOLCHAIN:
        fail("MANIFEST_TOOLCHAIN_INVALID")
    safety = manifest.get("safety", {})
    if safety != {
        "production_deployment": "NONE",
        "canary": "DISABLED",
        "live_trading": "DISABLED",
        "auto_trading": "DISABLED",
    }:
        fail("MANIFEST_SAFETY_INVALID")

    print(f"REPRODUCIBLE_ARTIFACT_VERIFY=PASS sha256={actual_sha} files={len(files)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    build_p = sub.add_parser("build")
    build_p.add_argument("--root", type=Path, required=True)
    build_p.add_argument("--source-sha", required=True)
    build_p.add_argument("--output", type=Path, required=True)
    build_p.add_argument("--manifest", type=Path, required=True)

    verify_p = sub.add_parser("verify")
    verify_p.add_argument("--artifact", type=Path, required=True)
    verify_p.add_argument("--manifest", type=Path, required=True)
    verify_p.add_argument("--source-sha")

    args = parser.parse_args()
    try:
        if args.command == "build":
            build(args.root, args.source_sha, args.output, args.manifest)
        else:
            verify(args.artifact, args.manifest, args.source_sha)
    except (OSError, tarfile.TarError, KeyError, ValueError, ReproducibleBuildError) as exc:
        print(f"REPRODUCIBLE_BUILD=FAIL error={exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
