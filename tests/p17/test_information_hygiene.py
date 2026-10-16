from __future__ import annotations

import unittest

from packages.historical_data.replay_snapshot import (
    ReplayDatasetRef,
    ReplayFeatureRef,
    ReplaySnapshot,
    ReplaySnapshotPolicy,
    ReplayVintageRef,
)
from quant.backtesting.information_hygiene import (
    DecisionInformationAudit,
    InformationHygieneError,
    UniverseMembershipChange,
    certify_information_hygiene,
)


POLICY = ReplaySnapshotPolicy(
    allowed_clock_modes=frozenset(
        {"EVENT_TIME", "RECEIVE_TIME", "CONTROLLED_SIMULATION_CLOCK"}
    ),
    max_dataset_refs=10,
    max_feature_refs=10,
    max_vintage_refs=10,
    max_snapshot_bytes=100_000,
    production_replay_storage_vendor="UNSELECTED",
)


def snapshot() -> ReplaySnapshot:
    return ReplaySnapshot.build(
        replay_start_ns=100,
        replay_end_ns=2_000,
        snapshot_cutoff_ns=1_900,
        clock_mode="EVENT_TIME",
        scope_ids=("BTC-USD",),
        dataset_refs=(
            ReplayDatasetRef(
                "market",
                "1" * 64,
                "1.0",
                100,
                1_500,
                "2" * 64,
                "INTERNAL",
            ),
            ReplayDatasetRef(
                "future-window",
                "3" * 64,
                "1.0",
                1_500,
                2_000,
                "4" * 64,
                "INTERNAL",
            ),
        ),
        feature_refs=(
            ReplayFeatureRef(
                "5" * 64,
                "6" * 64,
                "BTC-USD",
                700,
                800,
                "7" * 64,
            ),
            ReplayFeatureRef(
                "8" * 64,
                "9" * 64,
                "BTC-USD",
                1_200,
                1_300,
                "a" * 64,
            ),
        ),
        vintage_refs=(
            ReplayVintageRef(
                "b" * 64,
                "CPI",
                500,
                700,
                750,
            ),
            ReplayVintageRef(
                "c" * 64,
                "CPI",
                1_000,
                1_250,
                1_300,
            ),
        ),
        quality_rule_versions=("q1",),
        config_sha256="d" * 64,
        code_artifact_sha256="e" * 64,
        rights_class="INTERNAL",
        policy=POLICY,
    )


def member(
    *,
    change_id: str = "member-1",
    effective: int = 100,
    available: int = 100,
    is_member: bool = True,
) -> UniverseMembershipChange:
    return UniverseMembershipChange(
        change_id,
        "BTC-USD",
        effective,
        available,
        is_member,
        "f" * 64,
    )


def audit(
    *,
    decision_id: str = "decision-1",
    time: int = 1_000,
    features: tuple[str, ...] = ("6" * 64,),
    vintages: tuple[str, ...] = ("b" * 64,),
    datasets: tuple[str, ...] = ("1" * 64,),
    labels: tuple[str, ...] = (),
) -> DecisionInformationAudit:
    return DecisionInformationAudit.build(
        decision_id=decision_id,
        asset_id="BTC-USD",
        decision_time_ns=time,
        feature_materialization_ids=features,
        vintage_ids=vintages,
        dataset_versions=datasets,
        outcome_label_ids=labels,
    )


class InformationHygieneTests(unittest.TestCase):
    def test_point_in_time_access_passes(self) -> None:
        cert = certify_information_hygiene(
            snapshot=snapshot(),
            decisions=(audit(),),
            universe_changes=(member(),),
        )
        self.assertEqual(cert.status, "PASS")
        self.assertFalse(cert.g9_authority)
        self.assertFalse(cert.profitability_claim_authority)
        self.assertFalse(cert.execution_authority)
        self.assertFalse(cert.order_routing_authority)

    def test_future_feature_access_fails_closed(self) -> None:
        with self.assertRaises(InformationHygieneError):
            certify_information_hygiene(
                snapshot=snapshot(),
                decisions=(audit(features=("9" * 64,)),),
                universe_changes=(member(),),
            )

    def test_future_vintage_access_fails_closed(self) -> None:
        with self.assertRaises(InformationHygieneError):
            certify_information_hygiene(
                snapshot=snapshot(),
                decisions=(audit(vintages=("c" * 64,)),),
                universe_changes=(member(),),
            )

    def test_dataset_outside_active_window_fails_closed(self) -> None:
        with self.assertRaises(InformationHygieneError):
            certify_information_hygiene(
                snapshot=snapshot(),
                decisions=(audit(datasets=("3" * 64,)),),
                universe_changes=(member(),),
            )

    def test_outcome_label_access_fails_closed(self) -> None:
        with self.assertRaises(InformationHygieneError):
            certify_information_hygiene(
                snapshot=snapshot(),
                decisions=(audit(labels=("future-return",)),),
                universe_changes=(member(),),
            )

    def test_missing_universe_membership_fails_closed(self) -> None:
        with self.assertRaises(InformationHygieneError):
            certify_information_hygiene(
                snapshot=snapshot(),
                decisions=(audit(),),
                universe_changes=(),
            )

    def test_known_non_member_fails_closed(self) -> None:
        with self.assertRaises(InformationHygieneError):
            certify_information_hygiene(
                snapshot=snapshot(),
                decisions=(audit(),),
                universe_changes=(member(is_member=False),),
            )

    def test_future_known_removal_does_not_leak_backward(self) -> None:
        cert = certify_information_hygiene(
            snapshot=snapshot(),
            decisions=(audit(time=1_000),),
            universe_changes=(
                member(),
                member(
                    change_id="remove-later-known",
                    effective=900,
                    available=1_100,
                    is_member=False,
                ),
            ),
        )
        self.assertEqual(cert.status, "PASS")

    def test_known_effective_removal_blocks(self) -> None:
        with self.assertRaises(InformationHygieneError):
            certify_information_hygiene(
                snapshot=snapshot(),
                decisions=(audit(time=1_000),),
                universe_changes=(
                    member(),
                    member(
                        change_id="remove-known",
                        effective=900,
                        available=900,
                        is_member=False,
                    ),
                ),
            )

    def test_duplicate_decision_audit_fails_closed(self) -> None:
        with self.assertRaises(InformationHygieneError):
            certify_information_hygiene(
                snapshot=snapshot(),
                decisions=(audit(), audit()),
                universe_changes=(member(),),
            )

    def test_duplicate_universe_change_fails_closed(self) -> None:
        with self.assertRaises(InformationHygieneError):
            certify_information_hygiene(
                snapshot=snapshot(),
                decisions=(audit(),),
                universe_changes=(member(), member()),
            )

    def test_input_order_does_not_change_identity(self) -> None:
        decisions=(
            audit(decision_id="decision-1", time=1_000),
            audit(
                decision_id="decision-2",
                time=1_400,
                features=("6" * 64, "9" * 64),
                vintages=("b" * 64, "c" * 64),
            ),
        )
        changes=(
            member(),
            member(
                change_id="member-refresh",
                effective=1_200,
                available=1_200,
                is_member=True,
            ),
        )
        left=certify_information_hygiene(
            snapshot=snapshot(),
            decisions=decisions,
            universe_changes=changes,
        )
        right=certify_information_hygiene(
            snapshot=snapshot(),
            decisions=tuple(reversed(decisions)),
            universe_changes=tuple(reversed(changes)),
        )
        self.assertEqual(left.certificate_id,right.certificate_id)


if __name__ == "__main__":
    unittest.main()
