from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import unittest

from packages.news_sentiment.alerting import AlertNarrativePolicy
from packages.news_sentiment.classification import ClassificationPolicy
from packages.news_sentiment.entity_mapping import EntityRegistry
from packages.news_sentiment.evaluation import (
    AdversarialEvaluationPolicy,
    P11EvaluationDependencies,
    evaluate_case,
    run_adversarial_evaluation,
)
from packages.news_sentiment.event_decay import EventDecayPolicy
from packages.news_sentiment.reliability import ReliabilityPolicy
from packages.news_sentiment.source_policy import NewsSourcePolicy


ROOT = Path(__file__).resolve().parents[2]
EVAL_POLICY = ROOT / "config/news-sentiment/adversarial-evaluation-policy.json"


def dependencies() -> P11EvaluationDependencies:
    return P11EvaluationDependencies(
        source_policy=NewsSourcePolicy.from_path(ROOT / "config/news-sentiment/source-license-policy.json"),
        registry=EntityRegistry.from_path(ROOT / "config/news-sentiment/entity-asset-registry.json"),
        classification_policy=ClassificationPolicy.from_path(
            ROOT / "config/news-sentiment/sentiment-topic-importance-policy.json"
        ),
        reliability_policy=ReliabilityPolicy.from_path(
            ROOT / "config/news-sentiment/reliability-rumor-policy.json"
        ),
        decay_policy=EventDecayPolicy.from_path(ROOT / "config/news-sentiment/event-horizon-decay-policy.json"),
        alert_policy=AlertNarrativePolicy.from_path(ROOT / "config/news-sentiment/alerting-narrative-policy.json"),
    )


class AdversarialEvaluationTests(unittest.TestCase):
    def test_all_mandatory_scenarios_pass(self) -> None:
        policy = AdversarialEvaluationPolicy.from_path(EVAL_POLICY)
        report = run_adversarial_evaluation(policy, deps=dependencies())
        self.assertEqual(report.total, 8)
        self.assertEqual(report.passed, 8)
        self.assertEqual(report.failed, 0)
        self.assertEqual(report.pass_rate_bps, 10000)
        self.assertTrue(report.all_passed)

    def test_required_fail_closed_cases_pass_expectations(self) -> None:
        policy = AdversarialEvaluationPolicy.from_path(EVAL_POLICY)
        report = run_adversarial_evaluation(policy, deps=dependencies())
        by_name = {result.name: result for result in report.results}
        self.assertTrue(by_name["as_of_before_observed"].passed)
        self.assertEqual(dict(by_name["as_of_before_observed"].actual)["error"], "EventDecayError")
        self.assertTrue(by_name["tampered_content_identity"].passed)
        self.assertEqual(dict(by_name["tampered_content_identity"].actual)["error"], "ReliabilityControlError")

    def test_entity_boundary_case_does_not_map_ethics_to_eth(self) -> None:
        policy = AdversarialEvaluationPolicy.from_path(EVAL_POLICY)
        case = next(case for case in policy.cases if case.name == "ethics_entity_boundary")
        result = evaluate_case(case, deps=dependencies())
        actual = dict(result.actual)
        self.assertTrue(result.passed)
        self.assertEqual(actual["mapping_state"], "NONE")
        self.assertEqual(actual["entity_ids"], [])

    def test_unconfirmed_case_is_quarantined_and_suppressed(self) -> None:
        policy = AdversarialEvaluationPolicy.from_path(EVAL_POLICY)
        case = next(case for case in policy.cases if case.name == "unconfirmed_suppressed")
        result = evaluate_case(case, deps=dependencies())
        actual = dict(result.actual)
        self.assertTrue(result.passed)
        self.assertEqual(actual["review_state"], "QUARANTINED")
        self.assertEqual(actual["freshness_state"], "BLOCKED")
        self.assertEqual(actual["severity"], "SUPPRESSED")

    def test_wrong_expectation_causes_case_failure(self) -> None:
        policy = AdversarialEvaluationPolicy.from_path(EVAL_POLICY)
        original = next(case for case in policy.cases if case.name == "confirmed_critical_fresh")
        wrong = replace(original, expected=(("severity", "INFORMATIONAL"),))
        result = evaluate_case(wrong, deps=dependencies())
        self.assertFalse(result.passed)

    def test_report_is_deterministic(self) -> None:
        policy = AdversarialEvaluationPolicy.from_path(EVAL_POLICY)
        first = run_adversarial_evaluation(policy, deps=dependencies())
        second = run_adversarial_evaluation(policy, deps=dependencies())
        self.assertEqual(first, second)
        self.assertEqual(first.payload(), second.payload())

    def test_module_has_no_network_llm_or_execution_imports(self) -> None:
        source_text = (ROOT / "packages/news_sentiment/evaluation.py").read_text(encoding="utf-8").lower()
        for forbidden in (
            "packages.execution",
            "adapters.execution",
            "import requests",
            "import httpx",
            "openai",
            "anthropic",
        ):
            self.assertNotIn(forbidden, source_text)


if __name__ == "__main__":
    unittest.main()
