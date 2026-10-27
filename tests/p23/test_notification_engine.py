from __future__ import annotations

import json
from pathlib import Path
import tempfile
from typing import cast
import unittest

from packages.ux.notification_engine import NotificationEngineError, NotificationPolicy


ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/ux/notification-engine.json"
ALERTING = ROOT / "config/news-sentiment/alerting-narrative-policy.json"


class NotificationEngineTests(unittest.TestCase):
    def _policy_raw(self) -> dict[str, object]:
        value = json.loads(POLICY.read_text(encoding="utf-8"))
        self.assertIsInstance(value, dict)
        return cast(dict[str, object], value)

    def _load(self, raw: dict[str, object]) -> NotificationPolicy:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "policy.json"
            path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
            return NotificationPolicy.from_paths(path, ALERTING)

    def _event(self, severity: str) -> dict[str, str]:
        return {
            "source_event_id": "evt-001",
            "severity": severity,
            "title_fa": "هشدار نمونه",
            "body_fa": "متن نمونه",
            "created_at": "2026-10-27T00:00:00Z",
            "provenance_ref": "sha256:" + "a" * 64,
        }

    def test_canonical_policy_loads(self) -> None:
        policy = NotificationPolicy.from_paths(POLICY, ALERTING)
        self.assertEqual(policy.severities, ("INFORMATIONAL", "IMPORTANT", "CRITICAL", "SUPPRESSED"))
        self.assertEqual(policy.channels, ("IN_APP",))

    def test_ids_are_deterministic(self) -> None:
        policy = NotificationPolicy.from_paths(POLICY, ALERTING)
        first = policy.route(self._event("IMPORTANT"), in_quiet_hours=False)
        second = policy.route(self._event("IMPORTANT"), in_quiet_hours=False)
        self.assertEqual(first.notification_id, second.notification_id)
        self.assertEqual(first.dedup_key, second.dedup_key)

    def test_suppressed_never_delivers(self) -> None:
        policy = NotificationPolicy.from_paths(POLICY, ALERTING)
        route = policy.route(self._event("SUPPRESSED"), in_quiet_hours=False)
        self.assertEqual(route.action, "SUPPRESS")
        self.assertIsNone(route.channel)
        self.assertIsNone(route.escalation_target)

    def test_critical_bypasses_quiet_hours_to_in_app_only(self) -> None:
        policy = NotificationPolicy.from_paths(POLICY, ALERTING)
        route = policy.route(self._event("CRITICAL"), in_quiet_hours=True)
        self.assertEqual(route.action, "DELIVER_IN_APP")
        self.assertEqual(route.channel, "IN_APP")
        self.assertEqual(route.escalation_target, "ON_CALL_QUEUE")

    def test_noncritical_defers_during_quiet_hours(self) -> None:
        policy = NotificationPolicy.from_paths(POLICY, ALERTING)
        for severity in ("INFORMATIONAL", "IMPORTANT"):
            route = policy.route(self._event(severity), in_quiet_hours=True)
            self.assertEqual(route.action, "DEFER_IN_APP")
            self.assertEqual(route.channel, "IN_APP")
            self.assertIsNone(route.escalation_target)

    def test_unknown_severity_fails_closed(self) -> None:
        policy = NotificationPolicy.from_paths(POLICY, ALERTING)
        with self.assertRaisesRegex(NotificationEngineError, "unknown notification severity"):
            policy.route(self._event("UNKNOWN"), in_quiet_hours=False)

    def test_external_delivery_enablement_fails_closed(self) -> None:
        raw = self._policy_raw()
        delivery = cast(dict[str, object], raw["delivery"])
        delivery["external_delivery_enabled"] = True
        with self.assertRaisesRegex(NotificationEngineError, "external delivery boundary drift"):
            self._load(raw)

    def test_credential_access_fails_closed(self) -> None:
        raw = self._policy_raw()
        delivery = cast(dict[str, object], raw["delivery"])
        delivery["credential_access"] = True
        with self.assertRaisesRegex(NotificationEngineError, "external delivery boundary drift"):
            self._load(raw)

    def test_owner_authority_escalation_fails_closed(self) -> None:
        raw = self._policy_raw()
        escalation = cast(dict[str, object], raw["escalation"])
        escalation["grants_owner_authorization"] = True
        with self.assertRaisesRegex(NotificationEngineError, "forbidden escalation authority"):
            self._load(raw)

    def test_safety_drift_fails_closed(self) -> None:
        raw = self._policy_raw()
        safety = cast(dict[str, object], raw["safety"])
        safety["production_activation"] = True
        with self.assertRaisesRegex(NotificationEngineError, "P23-F safety boundary drift"):
            self._load(raw)


if __name__ == "__main__":
    unittest.main()
