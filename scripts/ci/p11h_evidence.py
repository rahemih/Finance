from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.news_sentiment.alerting import AlertNarrativePolicy
from packages.news_sentiment.classification import ClassificationPolicy
from packages.news_sentiment.entity_mapping import EntityRegistry
from packages.news_sentiment.evaluation import (
    AdversarialEvaluationPolicy,
    P11EvaluationDependencies,
    run_adversarial_evaluation,
)
from packages.news_sentiment.event_decay import EventDecayPolicy
from packages.news_sentiment.reliability import ReliabilityPolicy
from packages.news_sentiment.source_policy import NewsSourcePolicy


ROOT = Path(__file__).resolve().parents[2]
EVAL_POLICY = ROOT / "config/news-sentiment/adversarial-evaluation-policy.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    policy = AdversarialEvaluationPolicy.from_path(EVAL_POLICY)
    deps = P11EvaluationDependencies(
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
    report = run_adversarial_evaluation(policy, deps=deps)
    if not report.all_passed or report.pass_rate_bps != policy.required_pass_rate_bps:
        raise SystemExit("P11H_EVIDENCE=FAIL mandatory adversarial scenario failure")

    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P11H_ADVERSARIAL_EVALUATION_EVIDENCE",
        "task_id": "FIN-P11-WH-001",
        "policy_sha256": hashlib.sha256(EVAL_POLICY.read_bytes()).hexdigest(),
        "required_pass_rate_bps": policy.required_pass_rate_bps,
        "report": report.payload(),
        "network_required": policy.canonical_tests_network_required,
        "llm_required": policy.llm_required,
        "production_news_vendor": policy.production_news_vendor,
        "live_trading": policy.live_trading,
        "auto_trading": policy.auto_trading,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"P11H_EVIDENCE=PASS total={report.total} passed={report.passed} "
        f"pass_rate_bps={report.pass_rate_bps} output={args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
