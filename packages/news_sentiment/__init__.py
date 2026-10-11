from .source_policy import (
    NewsSourcePolicy,
    NewsSourcePolicyError,
    NewsSourceRecord,
    validate_source_record,
)

__all__ = [
    "NewsSourcePolicy",
    "NewsSourcePolicyError",
    "NewsSourceRecord",
    "validate_source_record",
]

from .ingestion import (
    DedupGroup,
    IngestionPolicy,
    NewsIngestionError,
    RawNewsItem,
    build_dedup_group,
    exact_duplicate,
    near_duplicate,
    near_duplicate_ratio,
    validate_raw_news_item,
)

__all__ += [
    "DedupGroup",
    "IngestionPolicy",
    "NewsIngestionError",
    "RawNewsItem",
    "build_dedup_group",
    "exact_duplicate",
    "near_duplicate",
    "near_duplicate_ratio",
    "validate_raw_news_item",
]

from .classification import (
    ClassificationPolicy,
    ClassificationResult,
    NewsClassificationError,
    classify_news_item,
)

__all__ += [
    "ClassificationPolicy",
    "ClassificationResult",
    "NewsClassificationError",
    "classify_news_item",
]

from .reliability import (
    ReliabilityAssessment,
    ReliabilityControlError,
    ReliabilityPolicy,
    assess_reliability,
)

__all__ += [
    "ReliabilityAssessment",
    "ReliabilityControlError",
    "ReliabilityPolicy",
    "assess_reliability",
]

from .event_decay import (
    EventDecayAssessment,
    EventDecayError,
    EventDecayPolicy,
    assess_event_decay,
)

__all__ += [
    "EventDecayAssessment",
    "EventDecayError",
    "EventDecayPolicy",
    "assess_event_decay",
]

from .alerting import (
    AlertNarrativeError,
    AlertNarrativeInput,
    AlertNarrativePolicy,
    build_alert_narrative_input,
)

__all__ += [
    "AlertNarrativeError",
    "AlertNarrativeInput",
    "AlertNarrativePolicy",
    "build_alert_narrative_input",
]

from .evaluation import (
    AdversarialCase,
    AdversarialCaseResult,
    AdversarialEvaluationError,
    AdversarialEvaluationPolicy,
    AdversarialEvaluationReport,
    P11EvaluationDependencies,
    evaluate_case,
    run_adversarial_evaluation,
)

__all__ += [
    "AdversarialCase",
    "AdversarialCaseResult",
    "AdversarialEvaluationError",
    "AdversarialEvaluationPolicy",
    "AdversarialEvaluationReport",
    "P11EvaluationDependencies",
    "evaluate_case",
    "run_adversarial_evaluation",
]
