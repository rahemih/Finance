# P14-F — Persian Explainability

State: CANONICAL_COMPLETE  
Task: `FIN-P14-WF-001`  
Linear: `HOS-274`  
Lock: `LOCK-FIN-P14-WF-001-01` / RELEASED

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


## Canonical closure evidence

- implementation PR #293 = MERGED
- implementation head `20f8854a2ea142e92426d47956776ef1406961ca`
- implementation Governance `38411846344` = SUCCESS
- implementation artifact `sha256:5b18bed7ae5a27ec4bb232e8b2794437226bf5f281e1e3bb09af2cd3f7064070`
- implementation merge SHA `a2d34e58e16185f9882c8e9b15063542f7b515c7`
- post-merge Governance `38412158040` = SUCCESS
- Branch Hygiene `38412157804` = SUCCESS
- implementation branch = DELETED
- P14-G = READY_NOT_STARTED
