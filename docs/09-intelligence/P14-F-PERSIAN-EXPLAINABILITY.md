# P14-F — Persian Explainability

State: CLOSURE_RECONCILIATION  
Task: `FIN-P14-WF-001`  
Linear: `HOS-274`

## Objective

Render the canonical P14 evidence/fusion/probability state into deterministic Persian explanations without creating or modifying any empirical number or trading authority.

## Inputs

- P14-B `WeightedFusionResult`
- P14-D `ProbabilityUncertaintyQualification` for directional fused states
- P14-E `TPStopOutcomeProbability` for directional fused states

The P14-E object must reference the exact P14-D qualification ID. General empirical probability and overall uncertainty must match exactly across the upstream chain.

## Persian explanation fields

The canonical output contains:
- Persian summary of fusion state/direction;
- supporting, opposing and neutral independence groups;
- hard-veto reasons when blocked;
- exact empirical probability and sample count when available;
- exact 95% interval and overall uncertainty when available;
- exact TP_FIRST / STOP_FIRST / NEITHER probabilities when available;
- excluded expired/correlated evidence counts;
- immutable machine-readable upstream numeric values and identities.

Blocked or insufficient-evidence states never receive invented probability text.

## Authority boundary

P14-F does not output LONG/SHORT/WAIT/NO_TRADE. That remains P14-H.

The baseline renderer uses governed deterministic Persian templates. LLM/free-form numeric authority is forbidden. Any future narrative model may only paraphrase already-governed values under a separate governed task; it may never create or change probability, uncertainty, veto or action.

LIVE_TRADING = DISABLED.  
AUTO_TRADING = DISABLED.
