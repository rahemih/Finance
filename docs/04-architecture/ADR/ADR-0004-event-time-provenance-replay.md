# ADR-0004 — Event-Time, Provenance & Replay

Status: ACCEPTED  
Task: `FIN-P02-WA-001`

## Context

Backtesting, decision replay, audit and model evaluation fail if source time, receive time, revisions and provider identity are lost.

## Decision

Material data and decision events preserve:
- source/event time;
- receive time;
- processing time where useful;
- provider/source ID;
- canonical instrument ID;
- sequence/gap metadata where available;
- schema/version;
- transformation/model/config version.

Replayability is a first-class architecture requirement.

## Alternatives considered

- Store only normalized latest state — rejected because it destroys causality and auditability.
- Rely on provider history later — rejected because provider history may differ from originally observed data.

## Consequences

Positive:
- deterministic replay and audit;
- stronger anti-lookahead controls;
- better incident analysis.

Negative:
- more storage and metadata overhead.

## Risks / mitigations

Risk: event metadata growth.  
Mitigation: retention/compaction policy in P06/P02-H without destroying required raw evidence.

## Validation / evidence

P02-C defines event/data architecture. P06/P07/P19 validate replay/provenance.

## Rollback / supersession

May change storage mechanism but not the preservation requirement.

## Related tasks / gates

P02-C, P06, P07, P19, G5, G10.
