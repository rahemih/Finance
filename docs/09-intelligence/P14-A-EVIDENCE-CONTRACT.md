# P14-A — Evidence Contract

State: IMPLEMENTATION_ACTIVE  
Task: `FIN-P14-WA-001`  
Linear: `HOS-269`

## Objective

Establish one deterministic cross-domain evidence envelope over canonical P08-P13 outputs before any weighting, signal fusion or empirical probability calibration occurs.

## Canonical source families

| Source phase | Source family |
|---|---|
| P08 | TECHNICAL |
| P09 | ORDER_FLOW_LIQUIDITY |
| P10 | FUNDAMENTAL_MACRO |
| P11 | NEWS_SENTIMENT |
| P12 | MARKET_MEMORY |
| P13 | TIMING_OPPORTUNITY |

Every evidence record preserves:
- source phase/family and producer-specific evidence family;
- independence group;
- subject, timeframe and regime context;
- direction (-1/0/+1), strength and evidence quality in bounded basis points;
- sample count;
- event/as-of/valid-until timestamps and explicit freshness state;
- source record identity and SHA-256 provenance;
- explicit invalidation semantics;
- non-bypassable upstream hard-veto state and reason codes.

## Determinism and safety

Evidence and bundle identities are SHA-256 hashes over canonical JSON payloads. Bundle ordering is canonical and independent of input order. Duplicate evidence identities, unknown sources, subject/as-of mismatches and invalid time/bounds fail closed.

Expired evidence remains visible as `EXPIRED`; it cannot silently masquerade as fresh.

P14-A does **not** implement:
- weighted evidence fusion (P14-B);
- empirical/calibrated probability (P14-C);
- uncertainty/confidence intervals (P14-D);
- TP/Stop outcome probability (P14-E);
- Persian explanation (P14-F);
- Red-Team challenge (P14-G);
- signal output contract (P14-H);
- G7 validation (P14-I).

LLMs may not invent empirical probabilities.

LIVE_TRADING = DISABLED.  
AUTO_TRADING = DISABLED.
