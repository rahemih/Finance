# ADR-0009 — Independent Evidence Fusion & Calibrated Probability

Status: ACCEPTED  
Task: `FIN-P02-WD-001`

## Context

NEXUS QUANT combines technical, order-flow, macro, news, intermarket and market-memory evidence. Counting raw indicators would overstate confidence because many indicators are correlated or derived from the same source.

The project also requires explainable probabilities that are empirically calibrated rather than guessed by an LLM.

## Decision

Adopt the intelligence architecture defined in:

- `docs/04-architecture/INTELLIGENCE-SIGNAL-ARCHITECTURE.md`
- `docs/04-architecture/intelligence-signal-architecture.json`

All intelligence methods emit a common `EvidencePacket`.

Evidence is aggregated **within a family first** and only then fused across independence groups.

Correlated families/sources are subject to cluster caps and cannot multiply their influence merely through indicator count, vendor duplication or syndicated copies.

Fusion emits a non-executable `SignalCandidate` whose allowed high-level outcomes include:
- LONG_CANDIDATE;
- SHORT_CANDIDATE;
- WAIT;
- NO_TRADE.

Trade probability is produced only by an empirical/calibration layer with explicit:
- target definition;
- sample size;
- uncertainty;
- calibration method/metric;
- out-of-sample reference;
- regime similarity;
- dataset/model version.

If support is insufficient, output `PROBABILITY_UNAVAILABLE`.

LLMs may summarize/explain structured evidence but may not create or alter:
- calibrated probability;
- fusion score;
- evidence IDs;
- signal verdict;
- invalidation;
- safety state.

## Alternatives considered

### Count every indicator as one vote
Rejected because correlated indicators create false confirmation.

### Single opaque end-to-end model emits trade + probability
Rejected because it weakens provenance, independence analysis, calibration evidence and Risk consumption.

### LLM-generated probability/confidence
Rejected because natural-language certainty is not empirical calibration.

### Binary long/short only
Rejected because WAIT and NO_TRADE are essential safety/uncertainty outcomes.

## Consequences

Positive:
- independent confirmations are meaningful;
- reasons for/against remain auditable;
- probability has measurable calibration support;
- downstream Risk receives structured, provider-neutral inputs;
- model/indicator families can evolve independently.

Negative:
- more metadata and family governance;
- correlation/dependence analysis must be maintained;
- probability may be unavailable more often than a narrative system would suggest.

## Risks / mitigations

Risk: hidden dependence between families inflates confidence.  
Mitigation: independence groups, empirical dependence audits and cluster caps.

Risk: calibration decays across regimes.  
Mitigation: regime similarity, calibration-window versioning and drift checks.

Risk: external news/content injects instructions into agents.  
Mitigation: treat retrieved content as untrusted evidence, never tool/control instructions.

Risk: natural-language explanation drifts from numeric decision.  
Mitigation: explanation is generated from immutable structured reason fields.

## Validation / evidence

P08 validates technical-family independence.

P09 validates order-flow/liquidity evidence.

P10/P11 validate macro/news reliability.

P12 validates market-memory relationships.

P14 validates fusion thresholds and probability calibration.

P17/P18 provide out-of-sample and continuous-learning evidence.

## Rollback / supersession

Implementation techniques may change without superseding this ADR if the following guarantees remain:
- family-level independence accounting;
- structured provenance;
- WAIT/NO_TRADE support;
- empirical calibrated probability;
- LLM non-authority over numeric/safety fields.

Weakening those guarantees requires explicit ADR supersession and A3/A4/A5/A8/A10 review.

## Related tasks / gates

P02-D, P08-P14, P17, P18, G2, G6, G7, G8.
