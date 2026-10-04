# ADR-0005 — Environment Isolation & Fail-Closed States

Status: ACCEPTED  
Task: `FIN-P02-WA-001`

## Context

Research, Demo, Shadow and Live have materially different risk. Shared credentials/state can accidentally escalate authority.

## Decision

DEV, TEST, RESEARCH, DEMO, SHADOW, CANARY and LIVE are separate risk/security contexts.

Critical unknown state fails closed.

Runtime state machines explicitly support at least:
- NORMAL;
- DEGRADED;
- SAFE_MODE;
- HALTED;
- EMERGENCY;
- RECOVERY.

## Alternatives considered

- One environment with feature flags only — rejected for critical execution/security separation.
- Silent degradation — rejected because it hides uncertainty.

## Consequences

Positive:
- safer promotion;
- clear incident behavior;
- credential/risk isolation.

Negative:
- more configuration/environment management.

## Risks / mitigations

Risk: configuration drift.  
Mitigation: config-as-code, environment contracts and promotion evidence in P03/P04.

## Validation / evidence

P02-G defines topology; P03/P04 implement security/config foundations; P22 validates recovery.

## Rollback / supersession

Environment count may be consolidated if equivalent isolation is proven, but LIVE authority must remain separately controlled.

## Related tasks / gates

P02-G, P03, P04, P22, G3.
