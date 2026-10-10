from __future__ import annotations

from pathlib import Path
import unittest

from packages.fundamental_intelligence.source_registry import (
    OfficialSourceRegistryError,
    OfficialSourcePolicy,
    OfficialSourceRegistry,
    assert_no_source_registry_trade_authority_fields,
    build_offline_request_spec,
    registry_with_replaced_source,
    validate_registry,
    validate_secret_handle,
)

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/fundamental-intelligence/official-source-policy.json"
REGISTRY_PATH = ROOT / "config/fundamental-intelligence/official-source-registry.json"


def policy() -> OfficialSourcePolicy:
    return OfficialSourcePolicy.from_path(POLICY_PATH)


def registry() -> OfficialSourceRegistry:
    return OfficialSourceRegistry.from_path(REGISTRY_PATH, policy=policy())


class OfficialSourceRegistryTests(unittest.TestCase):
    def test_registry_exactly_matches_required_roadmap_sources(self) -> None:
        p = policy()
        r = registry()
        self.assertEqual(
            {source.source_id for source in r.sources},
            set(p.required_source_ids),
        )
        self.assertEqual(len(r.sources), len(p.required_source_ids))
        self.assertEqual(r.verified_on, "2026-10-10")

    def test_registry_identity_is_deterministic_and_content_sensitive(self) -> None:
        first = registry()
        second = registry()
        self.assertEqual(first.registry_id, second.registry_id)
        mutated = registry_with_replaced_source(
            first,
            source_id="WORLD_BANK",
            notes="content-sensitive identity check",
        )
        self.assertNotEqual(first.registry_id, mutated.registry_id)

    def test_critical_revision_and_auth_semantics_are_fail_closed(self) -> None:
        r = registry()
        self.assertEqual(r.get("FRED_ALFRED").revision_mode, "NATIVE_VINTAGE")
        self.assertEqual(r.get("ECB").revision_mode, "HISTORY_QUERY")
        self.assertIn("INCLUDE_HISTORY", r.get("ECB").capabilities)
        self.assertEqual(r.get("EUROSTAT").revision_mode, "LATEST_ONLY")
        self.assertEqual(r.get("WORLD_BANK").auth_mode, "NONE")
        self.assertEqual(r.get("EIA").auth_mode, "API_KEY_REQUIRED")
        self.assertEqual(r.get("IEA").auth_mode, "LICENSE_REVIEW_REQUIRED")
        self.assertEqual(r.get("LBMA").auth_mode, "LICENSE_REVIEW_REQUIRED")

        bad = registry_with_replaced_source(
            r,
            source_id="EUROSTAT",
            revision_mode="NATIVE_VINTAGE",
        )
        with self.assertRaises(OfficialSourceRegistryError):
            validate_registry(bad, policy=policy())

    def test_every_url_is_https_and_official_host_scoped(self) -> None:
        r = registry()
        for source in r.sources:
            self.assertTrue(source.base_url.startswith("https://"))
            self.assertTrue(source.official_docs_url.startswith("https://"))
            self.assertNotIn("@", source.base_url.split("://", 1)[1].split("/", 1)[0])

    def test_production_transport_is_not_selected(self) -> None:
        p = policy()
        r = registry()
        self.assertEqual(p.production_source_selection, "NOT_SELECTED")
        self.assertFalse(p.canonical_tests_network_required)
        self.assertEqual(p.live_trading, "DISABLED")
        self.assertEqual(p.auto_trading, "DISABLED")
        for source in r.sources:
            self.assertNotEqual(source.transport_state, "PRODUCTION_ACTIVE")

    def test_api_key_sources_require_secret_handles(self) -> None:
        r = registry()
        fred = r.get("FRED_ALFRED")
        eia = r.get("EIA")
        with self.assertRaises(OfficialSourceRegistryError):
            build_offline_request_spec(fred, relative_path="series/observations")
        with self.assertRaises(OfficialSourceRegistryError):
            build_offline_request_spec(eia, relative_path="petroleum/pri/spt/data/")
        spec = build_offline_request_spec(
            fred,
            relative_path="series/observations",
            secret_handle="secret://fundamental/fred/api-key",
        )
        self.assertEqual(spec.source_id, "FRED_ALFRED")
        self.assertEqual(spec.intended_use, "OFFLINE_REQUEST_SPEC_ONLY_NO_NETWORK")
        self.assertTrue(spec.url.startswith("https://api.stlouisfed.org/"))

    def test_raw_secret_and_absolute_path_injection_fail_closed(self) -> None:
        with self.assertRaises(OfficialSourceRegistryError):
            validate_secret_handle("abc123")
        with self.assertRaises(OfficialSourceRegistryError):
            validate_secret_handle("secret://api_key=abc123")
        wb = registry().get("WORLD_BANK")
        with self.assertRaises(OfficialSourceRegistryError):
            build_offline_request_spec(
                wb,
                relative_path="https://evil.example/data",
            )

    def test_licensed_sources_do_not_emit_request_specs(self) -> None:
        r = registry()
        for source_id in ("IEA", "WGC", "LBMA"):
            with self.assertRaises(OfficialSourceRegistryError):
                build_offline_request_spec(
                    r.get(source_id),
                    relative_path="data",
                )

    def test_no_trade_authority_or_network_runtime_imports(self) -> None:
        assert_no_source_registry_trade_authority_fields()
        source = (ROOT / "packages/fundamental_intelligence/source_registry.py").read_text(
            encoding="utf-8"
        ).lower()
        for forbidden in (
            "adapters.execution",
            "packages.execution",
            "requests",
            "httpx",
            "websocket",
            "boto3",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
