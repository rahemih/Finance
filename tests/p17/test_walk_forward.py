from __future__ import annotations

from dataclasses import replace
import unittest

from quant.backtesting.walk_forward import (
    CandidateSelection,
    OutOfSampleResultRef,
    WalkForwardError,
    WalkForwardFold,
    certify_walk_forward,
)


def fold(
    fold_id: str,
    base: int,
)->WalkForwardFold:
    return WalkForwardFold(
        fold_id,
        base,
        base+100,
        base+100,
        base+150,
        base+160,
        base+210,
    )


def selection(fold_id: str, base: int, suffix: str)->CandidateSelection:
    return CandidateSelection(
        f"selection-{suffix}",
        fold_id,
        f"candidate-{suffix}",
        base+150,
        "a"*64,
        "b"*64,
    )


def result(fold_id: str, base: int, suffix: str)->OutOfSampleResultRef:
    return OutOfSampleResultRef(
        f"result-{suffix}",
        fold_id,
        "c"*64,
        "d"*64,
        base+160,
        base+210,
    )


class WalkForwardTests(unittest.TestCase):
    def test_valid_folds_pass(self)->None:
        cert=certify_walk_forward(
            folds=(fold("f1",100),fold("f2",300)),
            selections=(selection("f1",100,"1"),selection("f2",300,"2")),
            results=(result("f1",100,"1"),result("f2",300,"2")),
        )
        self.assertEqual(cert.status,"PASS")
        self.assertFalse(cert.g9_authority)
        self.assertFalse(cert.profitability_claim_authority)
        self.assertFalse(cert.execution_authority)

    def test_within_fold_overlap_fails_closed(self)->None:
        with self.assertRaises(WalkForwardError):
            WalkForwardFold("bad",0,100,90,150,150,200)

    def test_overlapping_test_windows_fail_closed(self)->None:
        with self.assertRaises(WalkForwardError):
            certify_walk_forward(
                folds=(fold("f1",100),fold("f2",140)),
                selections=(selection("f1",100,"1"),selection("f2",140,"2")),
                results=(result("f1",100,"1"),result("f2",140,"2")),
            )

    def test_test_informed_selection_fails_closed(self)->None:
        s=selection("f1",100,"1")
        with self.assertRaises(WalkForwardError):
            certify_walk_forward(
                folds=(fold("f1",100),),
                selections=(replace(s,selected_at_ns=260),),
                results=(result("f1",100,"1"),),
            )

    def test_missing_selection_fails_closed(self)->None:
        with self.assertRaises(WalkForwardError):
            certify_walk_forward(
                folds=(fold("f1",100),),
                selections=(),
                results=(result("f1",100,"1"),),
            )

    def test_missing_result_fails_closed(self)->None:
        with self.assertRaises(WalkForwardError):
            certify_walk_forward(
                folds=(fold("f1",100),),
                selections=(selection("f1",100,"1"),),
                results=(),
            )

    def test_mismatched_test_window_fails_closed(self)->None:
        r=result("f1",100,"1")
        with self.assertRaises(WalkForwardError):
            certify_walk_forward(
                folds=(fold("f1",100),),
                selections=(selection("f1",100,"1"),),
                results=(replace(r,test_end_ns=301),),
            )

    def test_duplicate_fold_fails_closed(self)->None:
        with self.assertRaises(WalkForwardError):
            certify_walk_forward(
                folds=(fold("f1",100),fold("f1",300)),
                selections=(selection("f1",100,"1"),),
                results=(result("f1",100,"1"),),
            )

    def test_order_independent_identity(self)->None:
        folds=(fold("f1",100),fold("f2",300))
        selections=(selection("f1",100,"1"),selection("f2",300,"2"))
        results=(result("f1",100,"1"),result("f2",300,"2"))
        left=certify_walk_forward(folds=folds,selections=selections,results=results)
        right=certify_walk_forward(
            folds=tuple(reversed(folds)),
            selections=tuple(reversed(selections)),
            results=tuple(reversed(results)),
        )
        self.assertEqual(left.certificate_id,right.certificate_id)


if __name__=="__main__":
    unittest.main()
