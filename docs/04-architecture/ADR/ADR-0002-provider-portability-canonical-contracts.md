# ADR-0002 — Provider Portability & Canonical Contracts

Status: ACCEPTED  
Task: `FIN-P02-WA-001`

## Context

P01 established multiple data/provider/execution candidates and explicitly forbids country/location assumptions in the architecture baseline.

## Decision

All external provider/broker/exchange integrations terminate at adapters that map into **canonical internal contracts**.

Provider-specific symbols, order IDs, field names, funding conventions, timestamps or permission models do not become domain primitives.

Country/location is not an architectural dependency.

## Alternatives considered

- Build directly around one provider SDK/schema — rejected because it creates lock-in and weakens failover.
- Normalize only later — rejected because provider leakage becomes expensive to remove.

## Consequences

Positive:
- provider replacement is localized;
- multi-provider validation is possible;
- P02 remains country-neutral.

Negative:
- adapter layer and canonical schema design require more upfront discipline.

## Risks / mitigations

Risk: canonical model becomes lowest-common-denominator.  
Mitigation: support provider-specific extension metadata without contaminating core contracts.

## Validation / evidence

P02-B/C/E must show provider-neutral domain contracts and adapter boundaries.

## Rollback / supersession

Only superseded by an ADR proving provider lock-in is unavoidable and safer, which requires explicit A1/A8/A10 review.

## Related tasks / gates

P01-G, P02-B, P02-C, P02-E, G2.
