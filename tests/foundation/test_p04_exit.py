from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from scripts.ci import p04_exit


class P04ExitPhaseProgressionTests(unittest.TestCase):
    def test_active_p05_is_valid_after_p04_closure(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "CURRENT-STATE.md"
            path.write_text(
                "Current Phase: P05 — Real-Time Data / ACTIVE  \n"
                "P04 state: CANONICAL_COMPLETE\n",
                encoding="utf-8",
            )
            original = p04_exit.CURRENT_STATE
            try:
                p04_exit.CURRENT_STATE = path
                self.assertEqual(
                    p04_exit.check_phase_progression(),
                    "P05 — Real-Time Data / ACTIVE",
                )
            finally:
                p04_exit.CURRENT_STATE = original

    def test_phase_regression_before_p04_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "CURRENT-STATE.md"
            path.write_text(
                "Current Phase: P03 — Security & Identity / ACTIVE\n"
                "P04 state: CANONICAL_COMPLETE\n",
                encoding="utf-8",
            )
            original = p04_exit.CURRENT_STATE
            try:
                p04_exit.CURRENT_STATE = path
                with self.assertRaises(p04_exit.ExitFailure):
                    p04_exit.check_phase_progression()
            finally:
                p04_exit.CURRENT_STATE = original


if __name__ == "__main__":
    unittest.main()
