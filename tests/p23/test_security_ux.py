from __future__ import annotations

import json
from pathlib import Path
import tempfile
from typing import cast
import unittest

from packages.ux.security_ux import SecurityUxError, SecurityUxPolicy


ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/ux/dangerous-action-security-ux.json"
P03 = ROOT / "docs/05-security/p03-security-validation.json"


class SecurityUxTests(unittest.TestCase):
    def _raw(self) -> dict[str, object]:
        value = json.loads(POLICY.read_text(encoding="utf-8"))
        self.assertIsInstance(value, dict)
        return cast(dict[str, object], value)

    def _load(self, raw: dict[str, object]) -> SecurityUxPolicy:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "policy.json"
            path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
            return SecurityUxPolicy.from_paths(path, P03)

    def _request(self) -> dict[str, str]:
        return {
            "action_id": "act-001",
            "action_type": "LIVE_TRADING_ENABLE_REQUEST",
            "target_resource": "execution-mode",
            "environment": "production",
            "requested_change_digest": "sha256:" + "a" * 64,
            "expires_at": "2026-10-27T12:00:00Z",
            "provenance_ref": "sha256:" + "b" * 64,
        }

    def test_canonical_policy_loads(self) -> None:
        policy = SecurityUxPolicy.from_paths(POLICY, P03)
        self.assertEqual(len(policy.action_types), 8)
        self.assertFalse(policy.approval_boundaries["grants_owner_authorization"])
        self.assertFalse(policy.safety["production_activation"])

    def test_confirmation_id_is_deterministic(self) -> None:
        policy = SecurityUxPolicy.from_paths(POLICY, P03)
        first = policy.confirmation_id(self._request())
        second = policy.confirmation_id(self._request())
        self.assertEqual(first, second)

    def test_client_only_authorization_cannot_be_enabled(self) -> None:
        raw = self._raw()
        confirmation = cast(dict[str, object], raw["confirmation"])
        confirmation["client_side_authorization_forbidden"] = False
        with self.assertRaisesRegex(SecurityUxError, "client-side authorization"):
            self._load(raw)

    def test_server_authorization_cannot_be_disabled(self) -> None:
        raw = self._raw()
        confirmation = cast(dict[str, object], raw["confirmation"])
        confirmation["server_side_authorization_required"] = False
        with self.assertRaisesRegex(SecurityUxError, "confirmation requirement weakened"):
            self._load(raw)

    def test_owner_authorization_cannot_be_granted_by_ux(self) -> None:
        raw = self._raw()
        approvals = cast(dict[str, object], raw["approval_boundaries"])
        approvals["grants_owner_authorization"] = True
        with self.assertRaisesRegex(SecurityUxError, "approval authority boundary drift"):
            self._load(raw)

    def test_a5_veto_cannot_be_bypassed(self) -> None:
        raw = self._raw()
        approvals = cast(dict[str, object], raw["approval_boundaries"])
        approvals["a5_risk_veto_bypass"] = True
        with self.assertRaisesRegex(SecurityUxError, "approval authority boundary drift"):
            self._load(raw)

    def test_browser_secret_storage_cannot_be_enabled(self) -> None:
        raw = self._raw()
        storage = cast(dict[str, object], raw["security_storage"])
        storage["secrets_in_browser_storage"] = True
        with self.assertRaisesRegex(SecurityUxError, "security storage boundary drift"):
            self._load(raw)

    def test_invalid_digest_fails_closed(self) -> None:
        policy = SecurityUxPolicy.from_paths(POLICY, P03)
        request = self._request()
        request["requested_change_digest"] = "not-a-digest"
        with self.assertRaisesRegex(SecurityUxError, "must be sha256"):
            policy.confirmation_id(request)

    def test_live_enable_request_does_not_enable_live(self) -> None:
        policy = SecurityUxPolicy.from_paths(POLICY, P03)
        self.assertIn("LIVE_TRADING_ENABLE_REQUEST", policy.action_types)
        self.assertEqual(policy.safety["live_trading"], "DISABLED")
        self.assertFalse(policy.safety["execution_authority_mutation"])

    def test_safety_drift_fails_closed(self) -> None:
        raw = self._raw()
        safety = cast(dict[str, object], raw["safety"])
        safety["production_activation"] = True
        with self.assertRaisesRegex(SecurityUxError, "P23-H safety boundary drift"):
            self._load(raw)


if __name__ == "__main__":
    unittest.main()
