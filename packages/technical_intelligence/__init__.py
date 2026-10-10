"""Provider-neutral technical-intelligence foundations."""

from .foundation import (
    IndicatorDefinition,
    TechnicalEvidence,
    TechnicalFoundationError,
    TechnicalFoundationPolicy,
    TrustedOHLCVBar,
    count_independent_confirmations,
    rate_of_change_bps,
    simple_moving_average,
)

__all__ = [
    "IndicatorDefinition",
    "TechnicalEvidence",
    "TechnicalFoundationError",
    "TechnicalFoundationPolicy",
    "TrustedOHLCVBar",
    "count_independent_confirmations",
    "rate_of_change_bps",
    "simple_moving_average",
    "TrendEvaluation",
    "TrendFamilyError",
    "TrendFamilyModel",
    "TrendFamilyPolicy",
]
