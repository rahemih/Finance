from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

from scripts.ci.p24wt_review_policy import ReviewPolicyError, validate

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/governance/p24-offline-solo-review-proposal.json"


def fixture() -> dict[str, object]:
    return json.loads(POLICY.read_text(encoding="utf-8"))


class SoloOwnerReviewProposalTests(unittest.TestCase):
    def refused(self, changed: object) -> None:
        with self.assertRaises(ReviewPolicyError):
            validate(changed)

    def test_01_proposal_valid_but_no_authority(self) -> None:
        out = validate(fixture())
        self.assertEqual(out["status"], "VALID_PROPOSAL_ONLY_NO_MERGE_AUTHORITY")
        self.assertEqual(out["owner_policy_gate"], "NOT_GRANTED")
        self.assertEqual(out["owner_pr_merge_gates"], "NOT_GRANTED")

    def test_02_exact_five_prs(self) -> None:
        self.assertEqual(validate(fixture())["candidates"], [492, 493, 494, 499, 502])

    def test_03_deterministic_evidence(self) -> None:
        self.assertEqual(validate(fixture()), validate(fixture()))

    def test_04_effective_true_forbidden(self) -> None:
        x = fixture()
        x["effective"] = True
        self.refused(x)

    def test_05_effective_zero_type_spoof_forbidden(self) -> None:
        x = fixture()
        x["effective"] = 0
        self.refused(x)

    def test_06_status_approved_forbidden(self) -> None:
        x = fixture()
        x["status"] = "OWNER_APPROVED"
        self.refused(x)

    def test_07_owner_gate_claim_forbidden(self) -> None:
        x = fixture()
        x["review_model"]["human_gate_policy_adoption"] = "APPROVED"
        self.refused(x)

    def test_08_pr_specific_merge_gate_claim_forbidden(self) -> None:
        x = fixture()
        x["review_model"]["human_gate_each_final_pr_sha"] = "PASS"
        self.refused(x)

    def test_09_self_review_forbidden(self) -> None:
        x = fixture()
        x["review_model"]["self_git_review"] = True
        self.refused(x)

    def test_10_automatic_merge_forbidden(self) -> None:
        x = fixture()
        x["review_model"]["automated_merge"] = True
        self.refused(x)

    def test_11_no_second_human_fiction(self) -> None:
        x = fixture()
        x["review_model"]["external_human_github_reviewer"] = "APPROVED"
        self.refused(x)

    def test_12_risk_veto_cannot_be_removed(self) -> None:
        x = fixture()
        x["review_model"]["A5_independent_runtime_risk_veto"] = "WAIVED"
        self.refused(x)

    def test_13_security_control_cannot_be_removed(self) -> None:
        x = fixture()
        x["review_model"]["A8_security_and_provenance_controls"] = "OPTIONAL"
        self.refused(x)

    def test_14_evidence_control_cannot_be_removed(self) -> None:
        x = fixture()
        x["review_model"]["A10_ci_and_evidence_verification"] = "DISABLED"
        self.refused(x)

    def test_15_real_order_review_nonwaivable(self) -> None:
        x = fixture()
        x["review_model"]["independent_human_review_if_code_adds_order_network_auth_production"] = "WAIVED"
        self.refused(x)

    def test_16_live_permission_forbidden(self) -> None:
        x = fixture()
        x["production_state"]["live_trading"] = "ENABLED"
        self.refused(x)

    def test_17_g13_promotion_forbidden(self) -> None:
        x = fixture()
        x["production_state"]["g13"] = "PASS"
        self.refused(x)

    def test_18_bool_spoof_pr_number_forbidden(self) -> None:
        x = fixture()
        x["candidates"][0]["pr"] = True
        self.refused(x)

    def test_19_unapproved_pr_number_forbidden(self) -> None:
        x = fixture()
        x["candidates"][0]["pr"] = 498
        self.refused(x)

    def test_20_duplicate_pr_forbidden(self) -> None:
        x = fixture()
        x["candidates"][1] = deepcopy(x["candidates"][0])
        self.refused(x)

    def test_21_missing_pr_forbidden(self) -> None:
        x = fixture()
        x["candidates"] = x["candidates"][:-1]
        self.refused(x)

    def test_22_unaudited_head_forbidden(self) -> None:
        x = fixture()
        x["candidates"][0]["reviewed_head"] = "f" * 40
        self.refused(x)

    def test_23_task_id_spoof_forbidden(self) -> None:
        x = fixture()
        x["candidates"][0]["task_id"] = "FIN-P24-FAKE"
        self.refused(x)

    def test_24_candidate_elevated_scope_forbidden(self) -> None:
        x = fixture()
        x["candidates"][0]["mandatory_live_review"] = "WAIVED"
        self.refused(x)

    def test_25_missing_scope_reason_forbidden(self) -> None:
        x = fixture()
        x["candidates"][2]["extra_guard"] = ""
        self.refused(x)

    def test_26_extra_unknown_policy_permission_forbidden(self) -> None:
        x = fixture()
        x["merge_now"] = True
        self.refused(x)

    def test_27_extra_review_category_forbidden(self) -> None:
        x = fixture()
        x["review_model"]["allow_live"] = True
        self.refused(x)

    def test_28_missing_approval_conditions_forbidden(self) -> None:
        x = fixture()
        x["approval_conditions"] = []
        self.refused(x)

    def test_29_account_access_denied(self) -> None:
        x = fixture()
        x["review_model"]["no_credential_access"] = False
        self.refused(x)

    def test_30_data_type_denial(self) -> None:
        self.refused(None)
        self.refused([])
        self.refused("hello")

    def test_31_bool_as_pre_first_live_count_forbidden(self) -> None:
        x = fixture()
        x["production_state"]["pre_first_live_satisfied"] = False
        self.refused(x)

    def test_32_test_requirement_cannot_be_optional(self) -> None:
        x = fixture()
        x["review_model"]["tests_and_supply_chain_scan"] = "OPTIONAL"
        self.refused(x)


if __name__ == "__main__":
    unittest.main()
