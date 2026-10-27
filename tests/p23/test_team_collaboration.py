from __future__ import annotations

import json
from pathlib import Path
import tempfile
from typing import cast
import unittest

from packages.ux.team_collaboration import CollaborationPolicy, TeamCollaborationError

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/ux/team-collaboration.json"


class TeamCollaborationTests(unittest.TestCase):
    def _raw(self) -> dict[str, object]:
        value = json.loads(POLICY.read_text(encoding="utf-8"))
        self.assertIsInstance(value, dict)
        return cast(dict[str, object], value)

    def _load(self, raw: dict[str, object]) -> CollaborationPolicy:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "policy.json"
            path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
            return CollaborationPolicy.from_path(path)

    def test_canonical_policy_loads(self) -> None:
        policy = CollaborationPolicy.from_path(POLICY)
        self.assertEqual(policy.approval_states, ("REQUESTED","APPROVED","REJECTED","WITHDRAWN"))
        self.assertEqual(len(policy.canonical_surfaces), 11)

    def test_policy_id_is_deterministic(self) -> None:
        self.assertEqual(
            CollaborationPolicy.from_path(POLICY).policy_id,
            CollaborationPolicy.from_path(POLICY).policy_id,
        )

    def test_event_id_is_deterministic(self) -> None:
        policy = CollaborationPolicy.from_path(POLICY)
        event = {
            "event_type":"COMMENT_CREATED",
            "actor_id":"user-1",
            "target_kind":"SURFACE",
            "target_id":"dashboard",
            "occurred_at":"2026-10-27T09:00:00Z",
            "provenance_ref":"sha256:" + "a"*64,
        }
        self.assertEqual(policy.event_id(event), policy.event_id(event))

    def test_event_type_drift_fails_closed(self) -> None:
        raw=self._raw()
        cast(list[str],raw["event_types"]).reverse()
        with self.assertRaisesRegex(TeamCollaborationError,"event type"):
            self._load(raw)

    def test_owner_authorization_cannot_be_granted(self) -> None:
        raw=self._raw()
        cast(dict[str,object],raw["approval"])["grants_owner_authorization"]=True
        with self.assertRaisesRegex(TeamCollaborationError,"forbidden workflow"):
            self._load(raw)

    def test_risk_approval_cannot_be_granted(self) -> None:
        raw=self._raw()
        cast(dict[str,object],raw["approval"])["grants_risk_approval"]=True
        with self.assertRaisesRegex(TeamCollaborationError,"forbidden workflow"):
            self._load(raw)

    def test_execution_approval_cannot_be_granted(self) -> None:
        raw=self._raw()
        cast(dict[str,object],raw["approval"])["grants_execution_approval"]=True
        with self.assertRaisesRegex(TeamCollaborationError,"forbidden workflow"):
            self._load(raw)

    def test_p24_approval_cannot_be_granted(self) -> None:
        raw=self._raw()
        cast(dict[str,object],raw["approval"])["grants_p24_production_approval"]=True
        with self.assertRaisesRegex(TeamCollaborationError,"forbidden workflow"):
            self._load(raw)

    def test_assignment_cannot_grant_permissions(self) -> None:
        raw=self._raw()
        cast(dict[str,object],raw["assignment"])["grants_permissions"]=True
        with self.assertRaisesRegex(TeamCollaborationError,"forbidden assignment"):
            self._load(raw)

    def test_audit_policy_cannot_be_mutable(self) -> None:
        raw=self._raw()
        cast(dict[str,object],raw["audit"])["append_only"]=False
        with self.assertRaisesRegex(TeamCollaborationError,"audit policy"):
            self._load(raw)

    def test_event_requires_exact_fields(self) -> None:
        policy=CollaborationPolicy.from_path(POLICY)
        with self.assertRaisesRegex(TeamCollaborationError,"fields/order"):
            policy.event_id({"event_type":"COMMENT_CREATED"})

    def test_unknown_target_fails_closed(self) -> None:
        policy=CollaborationPolicy.from_path(POLICY)
        event={
            "event_type":"COMMENT_CREATED","actor_id":"u","target_kind":"ORDER",
            "target_id":"x","occurred_at":"2026-10-27T09:00:00Z","provenance_ref":"x",
        }
        with self.assertRaisesRegex(TeamCollaborationError,"target kind"):
            policy.event_id(event)

    def test_p24_activation_fails_closed(self) -> None:
        raw=self._raw()
        cast(dict[str,object],raw["safety"])["p24_state"]="ACTIVE"
        with self.assertRaisesRegex(TeamCollaborationError,"safety boundary"):
            self._load(raw)


if __name__ == "__main__":
    unittest.main()
