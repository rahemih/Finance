# P23-D — Learning Mode / Glossary

Task: `FIN-P23-WD-001`  
State: CANONICAL_COMPLETE  
Lock: `LOCK-FIN-P23-WD-001-01` / RELEASED

## Contract

Learning Mode is an explanation layer. It may clarify what the product is displaying, why a state is visible, what the limitations are and which source context supports it. It must never change a signal, probability, risk decision or execution state.

Modes:
- OFF — explanations hidden;
- GUIDED — concise contextual explanations;
- DETAILED — expanded educational explanation with limitations and source context.

Authority: `EXPLANATION_ONLY`.

## Glossary

The glossary at `/glossary` must preserve the exact P23-B terminology order and identifiers. Persian definitions may explain the terms, but canonical identifiers such as `LONG`, `SHORT`, `WAIT` and `NO_TRADE` remain visible and unchanged.

## Safety

- signal mutation: false;
- probability mutation: false;
- personalized advice: false;
- execution action: false;
- external-order authority: false;
- runtime mutation/remediation: false;
- credentials: none;
- P24: NOT_STARTED;
- LIVE_TRADING / AUTO_TRADING: DISABLED.


## Canonical closure evidence
- implementation PR #477 = MERGED;
- implementation Governance `40476712486` = SUCCESS;
- implementation artifact `12721377164` / `sha256:8970f3b4310663160eae386b8e8d8b6a65fe5a498aef117065c02b53f3023891`;
- learning_mode_id = `6958ab68d19b38026748436c06a0428702f4873fdcab1674a0624979d4a422c9`;
- evidence_id = `27357359b50c9cd666c6c5017c7fe1fd1873786641aad4de81df764c9837f60e`;
- evidence SHA256 = `c714bb3ef5c16ff0490573ebecfc4dcfe88e249fe027078892feebdd27ad1f2d`;
- post-merge Governance `40476947007` = SUCCESS;
- post-merge Branch Hygiene `40476947051` = SUCCESS.
