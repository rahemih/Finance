# P23-D — Learning Mode / Glossary

Task: `FIN-P23-WD-001`  
State: IN_PROGRESS  
Lock: `LOCK-FIN-P23-WD-001-01` / ACQUIRED

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
