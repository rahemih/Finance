# ADR-0007 — Domain Boundaries & Dependency Direction

Status: ACCEPTED  
Task: `FIN-P02-WB-001`

## Context

P02-A established modular-core-first architecture, provider portability, independent Risk/Firewall authority, replayability and bounded agents.

P02-B must translate those principles into explicit logical domains and dependency rules without prematurely creating microservices.

## Decision

Adopt the canonical logical domain map defined in:

- `docs/04-architecture/DOMAIN-BOUNDARIES.md`
- `docs/04-architecture/domain-boundaries.json`

The main executable decision direction is:

`Adapters → Canonical Data → Quality → Evidence → Intelligence/Quant → Signal → Risk → Firewall → Execution`

Cross-domain state mutation is forbidden except through explicit contracts owned by the target domain.

Provider-specific APIs/SDKs terminate at adapter boundaries.

Country/location is not a domain dependency.

## Alternatives considered

### Shared-data monolith with informal boundaries
Rejected because table-level coupling would bypass ownership and make replay/security/risk authority difficult to verify.

### Microservices per domain immediately
Rejected because the private <=10-user scope does not justify the operational burden before scale/isolation evidence exists.

### Direct strategy-to-broker integration
Rejected because it bypasses independent Risk/Firewall and deterministic OMS semantics.

## Consequences

Positive:
- clear ownership;
- provider portability;
- auditable decision path;
- easier replay/testing;
- safer agent access;
- later physical decomposition remains possible.

Negative:
- explicit contracts and read models require more design discipline;
- some feedback paths must use events rather than direct shared-state calls.

## Physical extraction guidance

Strong candidates:
- Market Data Adapters;
- Execution / OMS;
- Agent Control Plane;
- User-facing Application API.

Conditional:
- Risk / Pre-Trade Firewall.

Default modular-core:
- Intelligence / Quant / Signal, with workers where justified.

This guidance is not a deployment freeze; P02-G owns final topology.

## Risks / mitigations

Risk: too many logical boundaries become accidental complexity.  
Mitigation: boundaries define ownership, not mandatory services.

Risk: event feedback creates hidden cycles.  
Mitigation: command dependency remains directional; feedback is event/read-model based.

Risk: direct DB access bypasses domain contracts.  
Mitigation: authoritative-state ownership and cross-domain write prohibition.

## Validation / evidence

- every domain has a primary owner;
- forbidden coupling list is explicit;
- Risk/Firewall/Execution path cannot be bypassed;
- agent/UX/provider access remains bounded;
- country/location absent from dependency design.

## Rollback / supersession

Boundary names/responsibilities may be refined by later ADRs, but any change that weakens Risk, Security, provider portability or replay guarantees requires explicit A1/A5/A8/A10 review.

## Related tasks / gates

P02-B, P02-C, P02-D, P02-E, P02-F, P02-G, P02-I, G2.
