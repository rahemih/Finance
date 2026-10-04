# ADR-0001 — Modular Core First

Status: ACCEPTED  
Task: `FIN-P02-WA-001`

## Context

NEXUS QUANT is a private system for a small team. The roadmap requires strong safety boundaries but does not require hyperscale public-SaaS architecture.

## Decision

Use a **modular core first** architecture.

Network-separated services are introduced only when justified by:
- fault isolation;
- security boundary;
- independent scaling;
- distinct latency/runtime needs;
- deployment ownership;
- external integration isolation.

## Alternatives considered

- Microservices by default — rejected because it adds operational complexity before evidence requires it.
- Single undifferentiated monolith — rejected because Risk, Execution, Data and Agent authority need explicit boundaries.

## Consequences

Positive:
- lower operating burden;
- easier deterministic testing/replay;
- fewer distributed failure modes.

Negative:
- module boundaries must be enforced carefully in code/contracts.

## Risks / mitigations

Risk: hidden coupling inside one process.  
Mitigation: explicit module contracts, ownership and dependency rules in P02-B.

## Validation / evidence

Validate in P02-B/P02-I that critical boundaries remain enforceable without unnecessary service extraction.

## Rollback / supersession

May be superseded if measured scale, security or fault-isolation evidence proves dedicated services necessary.

## Related tasks / gates

P02-B, P02-G, P02-I, G2.
