from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest

from packages.historical_data import (
    BackfillPage,
    BackfillPolicy,
    BackfillRequest,
    FilesystemRawArchive,
    HistoricalBackfillError,
    HistoricalBackfillRunner,
    RawArchivePolicy,
    RawArchiveRightsError,
    RightsState,
)

ROOT = Path(__file__).resolve().parents[2]
RAW_POLICY = ROOT / "config/historical-data/raw-archive-policy.json"
BACKFILL_POLICY = ROOT / "config/historical-data/backfill-policy.json"
PAGES = (
    BackfillPage(
        ordinal=0,
        payload=b'{"page":0,"trade":"a"}\n',
        captured_at_ns=1_780_819_201_000_000_000,
        source_event_id="historical-page-0",
        source_timestamp="2026-06-07T00:00:01Z",
    ),
    BackfillPage(
        ordinal=1,
        payload=b'{"page":1,"trade":"b"}\n',
        captured_at_ns=1_780_819_202_000_000_000,
        source_event_id="historical-page-1",
        source_timestamp="2026-06-07T00:00:02Z",
    ),
)


def request(
    *,
    rights_state: RightsState = RightsState.RETENTION_ALLOWED,
    retention_expires_at: str | None = None,
) -> BackfillRequest:
    return BackfillRequest(
        provider="reference-provider",
        source_stream="venue:spot:asset-usd:trades:historical",
        window_start_ns=1_780_819_200_000_000_000,
        window_end_ns=1_780_905_600_000_000_000,
        rights_state=rights_state,
        retention_class="MARKET_DATA_RAW",
        media_type="application/json",
        retention_expires_at=retention_expires_at,
    )


def runner(root: Path, *, policy: BackfillPolicy | None = None) -> HistoricalBackfillRunner:
    return HistoricalBackfillRunner(
        FilesystemRawArchive(root, RawArchivePolicy.from_path(RAW_POLICY)),
        policy or BackfillPolicy.from_path(BACKFILL_POLICY),
    )


class BackfillPolicyTests(unittest.TestCase):
    def test_policy_is_offline_and_vendor_neutral(self):
        policy = BackfillPolicy.from_path(BACKFILL_POLICY)
        self.assertTrue(policy.require_contiguous_ordinals)
        self.assertEqual(policy.production_historical_provider_entitlement, "NOT_ASSUMED")
        self.assertEqual(policy.production_storage_vendor, "NOT_SELECTED")


class HistoricalBackfillTests(unittest.TestCase):
    def test_exact_pages_archive_with_content_digests(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = runner(root).run(request(), PAGES)
            self.assertEqual(result.page_count, 2)
            self.assertEqual(result.created_pages, 2)
            self.assertEqual(result.idempotent_pages, 0)
            for source, archived in zip(PAGES, result.pages, strict=True):
                self.assertEqual(archived.payload_sha256, hashlib.sha256(source.payload).hexdigest())
                self.assertEqual((root / archived.object_relative_path).read_bytes(), source.payload)

    def test_rerun_is_idempotent_and_fingerprint_stable(self):
        with tempfile.TemporaryDirectory() as temp:
            backfill = runner(Path(temp))
            first = backfill.run(request(), PAGES)
            second = backfill.run(request(), PAGES)
            self.assertEqual(first.request_fingerprint, second.request_fingerprint)
            self.assertEqual(first.created_pages, 2)
            self.assertEqual(second.created_pages, 0)
            self.assertEqual(second.idempotent_pages, 2)

    def test_fingerprint_changes_when_exact_payload_changes(self):
        changed = (
            PAGES[0],
            BackfillPage(
                ordinal=1,
                payload=b'{"page":1,"trade":"changed"}\n',
                captured_at_ns=PAGES[1].captured_at_ns,
                source_event_id=PAGES[1].source_event_id,
                source_timestamp=PAGES[1].source_timestamp,
            ),
        )
        with tempfile.TemporaryDirectory() as temp:
            backfill = runner(Path(temp))
            original = backfill.run(request(), PAGES)
        with tempfile.TemporaryDirectory() as temp:
            modified = runner(Path(temp)).run(request(), changed)
        self.assertNotEqual(original.request_fingerprint, modified.request_fingerprint)

    def test_invalid_window_fails_closed(self):
        with self.assertRaises(HistoricalBackfillError):
            BackfillRequest(
                provider="reference-provider",
                source_stream="historical",
                window_start_ns=10,
                window_end_ns=10,
                rights_state=RightsState.RETENTION_ALLOWED,
                retention_class="MARKET_DATA_RAW",
                media_type="application/json",
            )

    def test_gapped_ordinals_fail_before_archive_mutation(self):
        pages = (
            PAGES[0],
            BackfillPage(
                ordinal=2,
                payload=PAGES[1].payload,
                captured_at_ns=PAGES[1].captured_at_ns,
            ),
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaises(HistoricalBackfillError):
                runner(root).run(request(), pages)
            self.assertEqual(list(root.rglob("*")), [])

    def test_policy_page_and_byte_bounds_fail_before_archive_mutation(self):
        tiny = BackfillPolicy(
            max_pages_per_run=1,
            max_total_bytes_per_run=8,
            require_contiguous_ordinals=True,
            production_historical_provider_entitlement="NOT_ASSUMED",
            production_storage_vendor="NOT_SELECTED",
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaises(HistoricalBackfillError):
                runner(root, policy=tiny).run(request(), PAGES)
            self.assertEqual(list(root.rglob("*")), [])

    def test_forbidden_and_unverified_rights_fail_closed(self):
        for state in (RightsState.RETENTION_FORBIDDEN, RightsState.RETENTION_UNVERIFIED):
            with self.subTest(state=state), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                with self.assertRaises(RawArchiveRightsError):
                    runner(root).run(request(rights_state=state), PAGES)
                self.assertEqual(list(root.rglob("*")), [])

    def test_limited_retention_requires_expiry(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaises(RawArchiveRightsError):
                runner(root).run(
                    request(rights_state=RightsState.RETENTION_ALLOWED_WITH_LIMIT),
                    PAGES,
                )
            self.assertEqual(list(root.rglob("*")), [])
        with tempfile.TemporaryDirectory() as temp:
            result = runner(Path(temp)).run(
                request(
                    rights_state=RightsState.RETENTION_ALLOWED_WITH_LIMIT,
                    retention_expires_at="2026-07-07T00:00:00Z",
                ),
                PAGES,
            )
            self.assertEqual(result.created_pages, 2)

    def test_core_module_is_provider_neutral(self):
        text = (ROOT / "packages/historical_data/backfill.py").read_text(encoding="utf-8").lower()
        self.assertNotIn("adapters.", text)
        self.assertNotIn("kaiko", text)
        self.assertNotIn("dxfeed", text)
        self.assertNotIn("databento", text)


if __name__ == "__main__":
    unittest.main()
