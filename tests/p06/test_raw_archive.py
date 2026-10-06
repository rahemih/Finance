from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from packages.historical_data import (
    FilesystemRawArchive, RawArchiveError, RawArchiveIntegrityError,
    RawArchivePolicy, RawArchiveRightsError, RawEvidence, RightsState,
)

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/historical-data/raw-archive-policy.json"
PAYLOAD = b'{"provider":"example","price":"123.45"}\n'


def evidence(*, rights_state: RightsState = RightsState.RETENTION_ALLOWED, retention_expires_at: str | None = None, provider: str = "kaiko") -> RawEvidence:
    return RawEvidence(
        provider=provider, source_stream="cbse:spot:btc-usd:trades",
        captured_at_ns=1_780_819_200_123_456_789, rights_state=rights_state,
        retention_class="MARKET_DATA_RAW", media_type="application/json",
        source_event_id="trade-001", source_timestamp="2026-06-07T00:00:00.123456789Z",
        retention_expires_at=retention_expires_at,
    )


class RawArchivePolicyTests(unittest.TestCase):
    def test_policy_loads_fail_closed_baseline(self):
        policy = RawArchivePolicy.from_path(POLICY)
        self.assertIn("RETENTION_ALLOWED", policy.allowed_rights_states)
        self.assertIn("RETENTION_UNVERIFIED", policy.denied_rights_states)
        self.assertEqual(policy.production_storage_vendor, "NOT_SELECTED")


class FilesystemRawArchiveTests(unittest.TestCase):
    def test_exact_raw_bytes_and_sha256_are_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); archive=FilesystemRawArchive(root, RawArchivePolicy.from_path(POLICY))
            result=archive.archive(PAYLOAD,evidence())
            self.assertTrue(result.created)
            self.assertEqual(result.payload_sha256, hashlib.sha256(PAYLOAD).hexdigest())
            self.assertEqual((root/result.object_relative_path).read_bytes(), PAYLOAD)
            value: object=json.loads((root/result.metadata_relative_path).read_text(encoding="utf-8"))
            self.assertIsInstance(value,dict)
            if not isinstance(value,dict): self.fail("metadata must be an object")
            self.assertEqual(value.get("payload_sha256"),result.payload_sha256)
            self.assertEqual(value.get("rights_state"),"RETENTION_ALLOWED")
            self.assertEqual(value.get("provider"),"kaiko")
            self.assertEqual(value.get("payload_size"),len(PAYLOAD))

    def test_same_payload_and_metadata_are_idempotent(self):
        with tempfile.TemporaryDirectory() as temp:
            archive=FilesystemRawArchive(Path(temp),RawArchivePolicy.from_path(POLICY))
            first=archive.archive(PAYLOAD,evidence()); second=archive.archive(PAYLOAD,evidence())
            self.assertTrue(first.created); self.assertFalse(second.created)
            self.assertEqual(first.object_relative_path,second.object_relative_path)

    def test_forbidden_and_unverified_rights_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            archive=FilesystemRawArchive(Path(temp),RawArchivePolicy.from_path(POLICY))
            for state in (RightsState.RETENTION_FORBIDDEN,RightsState.RETENTION_UNVERIFIED):
                with self.subTest(state=state):
                    with self.assertRaises(RawArchiveRightsError):
                        archive.archive(PAYLOAD,evidence(rights_state=state))

    def test_limited_retention_requires_expiry(self):
        with tempfile.TemporaryDirectory() as temp:
            archive=FilesystemRawArchive(Path(temp),RawArchivePolicy.from_path(POLICY))
            with self.assertRaises(RawArchiveRightsError):
                archive.archive(PAYLOAD,evidence(rights_state=RightsState.RETENTION_ALLOWED_WITH_LIMIT))
            result=archive.archive(PAYLOAD,evidence(rights_state=RightsState.RETENTION_ALLOWED_WITH_LIMIT,retention_expires_at="2026-07-07T00:00:00Z"))
            self.assertTrue(result.created)

    def test_tampered_existing_object_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); archive=FilesystemRawArchive(root,RawArchivePolicy.from_path(POLICY))
            result=archive.archive(PAYLOAD,evidence()); (root/result.object_relative_path).write_bytes(b"tampered")
            with self.assertRaises(RawArchiveIntegrityError): archive.archive(PAYLOAD,evidence())

    def test_incomplete_archive_pair_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); archive=FilesystemRawArchive(root,RawArchivePolicy.from_path(POLICY))
            result=archive.archive(PAYLOAD,evidence()); (root/result.metadata_relative_path).unlink()
            with self.assertRaises(RawArchiveIntegrityError): archive.archive(PAYLOAD,evidence())

    def test_path_unsafe_provider_is_rejected(self):
        with self.assertRaises(RawArchiveError): evidence(provider="../escape")

    def test_empty_payload_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            archive=FilesystemRawArchive(Path(temp),RawArchivePolicy.from_path(POLICY))
            with self.assertRaises(RawArchiveError): archive.archive(b"",evidence())

    def test_core_module_is_provider_neutral(self):
        text=(ROOT/"packages/historical_data/raw_archive.py").read_text(encoding="utf-8").lower()
        self.assertNotIn("adapters.",text); self.assertNotIn("kaiko",text)
        self.assertNotIn("dxfeed",text); self.assertNotIn("databento",text)


if __name__ == "__main__":
    unittest.main()
