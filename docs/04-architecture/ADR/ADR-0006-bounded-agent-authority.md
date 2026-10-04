# ADR-0006 — Bounded Agent Authority

Status: ACCEPTED  
Task: `FIN-P02-WA-001`

## Context

The project uses A0–A10 and specialists, but agent autonomy must not become unrestricted system authority.

## Decision

Agents operate as bounded roles with explicit:
- read/write scope;
- tools;
- inputs/outputs;
- forbidden actions;
- escalation;
- failure behavior;
- audit evidence.

No agent may self-grant authority, bypass Governance/Risk/Security, raise risk ceilings, create withdrawal authority or auto-promote models to Live.

## Alternatives considered

- One omnipotent orchestration agent — rejected due concentration of authority and poor auditability.
- Fully isolated agents with no shared protocol — rejected due coordination/replay difficulty.

## Consequences

Positive:
- clear accountability;
- safer delegation;
- deterministic handoffs.

Negative:
- more contracts and orchestration metadata.

## Risks / mitigations

Risk: prompt/tool abuse or authority confusion.  
Mitigation: message envelope, policy checks, tool scoping, audit logs and quarantine.

## Validation / evidence

P02-F maps runtime interfaces; P03/P22 enforce security/operations controls.

## Rollback / supersession

Any authority expansion requires an explicit ADR/task and cannot bypass owner/gate policy.

## Related tasks / gates

P02-F, P03, P22, G2, G3.
