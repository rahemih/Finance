# P17-C — Lookahead / Leakage / Survivorship Guards

State: IMPLEMENTATION_ACTIVE  
Task: `FIN-P17-WC-001`

## Objective

Independently certify that a P17 backtest decision path used only information that was legitimately available at the simulated decision time and only assets that belonged to the point-in-time historical universe.

This certificate is an acceptance guard for later P17 validation. It does not grant G9 authority.

## Point-in-time information

Every audited strategy decision declares the historical information it consumed:
- feature materialization IDs;
- macro vintage IDs;
- dataset versions;
- outcome-label IDs.

The guard resolves the canonical `ReplaySnapshot.view_at(decision_time_ns)`.

A feature, vintage or dataset version absent from that point-in-time view fails closed.

Outcome labels are forbidden in the strategy decision information set.

## Survivorship-bias control

Universe membership is represented as historical changes with:
- asset ID;
- effective time;
- information-availability time;
- membership state;
- evidence SHA-256.

At decision time the guard uses only changes that are both:
- effective by the decision time; and
- known by the decision time.

Future-known removals are intentionally ignored until their historical availability time, preventing future delisting/index knowledge from leaking backward.

A decision without explicit point-in-time universe membership, or for an asset known to be outside the universe, fails closed.

## Determinism

Decision audits and universe changes are canonicalized before certificate hashing.

Input ordering cannot change the certificate identity.

## Authority boundary

P17-C has no:
- G9 authority;
- profitability-claim authority;
- execution authority;
- order-routing authority;
- P18 promotion authority.

P17-D..P17-I = NOT_STARTED.  
`G9_QUANT_VALIDATED` = NOT_REACHED.  
P18 = NOT_STARTED.  
LIVE_TRADING = DISABLED.  
AUTO_TRADING = DISABLED.
