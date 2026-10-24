from pathlib import Path
import unittest

from packages.position_management import CanonicalPositionPolicy

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/position-management/canonical-position-state-policy.json"


class CanonicalPositionPolicyTests(unittest.TestCase):
    def test_reference_only_policy(self) -> None:
        policy = CanonicalPositionPolicy.from_path(POLICY)
        self.assertEqual(policy.markets, ("CRYPTO", "FOREX"))
        self.assertEqual(policy.live_trading, "DISABLED")
        self.assertEqual(policy.auto_trading, "DISABLED")


if __name__ == "__main__":
    unittest.main()
