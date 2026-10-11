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
