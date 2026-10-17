from __future__ import annotations
import unittest
from packages.learning.promotion import PromotionGovernor, PromotionGovernanceError, PromotionRequest

def req(*, target: str="DEMO_CHAMPION", risk: bool=True, blockers: int=0, name: str="p-1") -> PromotionRequest:
    return PromotionRequest(
        request_name=name,target=target,candidate_record_id="a"*64,
        comparison_record_id="b"*64,drift_report_id="c"*64,audit_bundle_sha256="d"*64,
        candidate_validation_passed=True,challenger_recommended=True,
        risk_review_passed=risk,audit_complete=True,critical_blockers=blockers,
    )

class TestPromotionGovernance(unittest.TestCase):
    def test_demo_approval_record_is_deterministic(self) -> None:
        a=PromotionGovernor().evaluate(req()); b=PromotionGovernor().evaluate(req())
        self.assertEqual(a.decision_id,b.decision_id)
        self.assertEqual(a.status,"APPROVE_DEMO_CHAMPION_RECORD")
        self.assertFalse(a.registry_mutation)
        self.assertFalse(a.promotion_execution_authority)

    def test_live_always_requires_owner_gate(self) -> None:
        d=PromotionGovernor().evaluate(req(target="LIVE"))
        self.assertEqual(d.status,"OWNER_LIVE_GATE_REQUIRED")
        self.assertIn("LIVE_PROMOTION_FORBIDDEN_IN_P18",d.reasons)
        self.assertFalse(d.automatic_live_promotion)

    def test_failed_risk_holds(self) -> None:
        d=PromotionGovernor().evaluate(req(risk=False))
        self.assertEqual(d.status,"HOLD")
        self.assertIn("RISK_REVIEW_FAILED",d.reasons)

    def test_critical_blocker_holds(self) -> None:
        d=PromotionGovernor().evaluate(req(blockers=1))
        self.assertEqual(d.status,"HOLD")

    def test_duplicate_request_fails_closed(self) -> None:
        g=PromotionGovernor(); g.evaluate(req())
        with self.assertRaisesRegex(PromotionGovernanceError,"duplicate"):
            g.evaluate(req())

    def test_authority_boundary(self) -> None:
        d=PromotionGovernor().evaluate(req())
        self.assertFalse(d.registry_mutation)
        self.assertFalse(d.promotion_execution_authority)
        self.assertFalse(d.automatic_live_promotion)
        self.assertEqual(d.live_trading,"DISABLED")
        self.assertEqual(d.auto_trading,"DISABLED")

if __name__=="__main__": unittest.main()
