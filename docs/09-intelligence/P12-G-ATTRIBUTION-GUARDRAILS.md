# P12-G — Attribution Guardrails

Task: `FIN-P12-WG-001`  
Linear: `HOS-258`  
State: CANONICAL_COMPLETE  
Lock: `LOCK-FIN-P12-WG-001-01` / RELEASED  
Canonical base: `7c0dc7b48d98965352ecfc5b2bd1427af3f8396a`

## Objective

Permit evidence-backed narrative attribution without mutating canonical P12-A relationships or presenting correlation, temporal precedence or narrative labels as causal proof.

## Architecture

P12-G is a separate assessment layer. Canonical `GraphEdge.attribution_label` remains `UNATTRIBUTED`.

Governed narrative labels:
- LIKELY_DRIVER
- SUPPORTING_FACTOR
- CONTEXT_ONLY
- INSUFFICIENT_EVIDENCE

Stronger labels require coherent primary evidence families, sufficient samples, bounded uncertainty, meaningful strength and consistent direction. `LIKELY_DRIVER` additionally requires an event/context source kind and a governed driver-context edge.

`HISTORICAL` and `COMPOSITE` evidence do not count as independent primary attribution families.

## Guardrails

- correlation alone cannot produce LIKELY_DRIVER;
- temporal precedence alone cannot produce LIKELY_DRIVER;
- conflicting direction degrades stronger labels;
- weak/high-uncertainty evidence degrades;
- LIKELY_DRIVER is narrative evidence, not causal proof;
- labels are not empirical probabilities;
- no signal/risk/execution authority is introduced;
- LIVE_TRADING and AUTO_TRADING remain DISABLED.


## Canonical closure evidence
- implementation PR #258 = MERGED
- final implementation head `378f1d712b4de48cc64e587a84507823d1d2aef1`
- implementation Governance `38223562855` = SUCCESS
- implementation artifact `sha256:26fccbf31c653ecf87161a33f6283f1bbdc2efc8cd7aea6e593e4b366e070885`
- implementation merge SHA `07d082f397e58b944722d38910fa3ca84dece3cf`
- post-merge Governance `38223827419` = SUCCESS
- post-merge Branch Hygiene `38223827467` = SUCCESS
- P12-H = READY_NOT_STARTED
