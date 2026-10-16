# P17-C — Lookahead / Leakage / Survivorship Guards

State: CANONICAL_COMPLETE  
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


## Canonical closure evidence

- implementation PR #346 = MERGED;
- implementation head = `1e67791884992df3ba230bac4b93756736352759`;
- Governance `38915003009` = SUCCESS;
- artifact = `sha256:5b0c5606971dacfa4e9bb1cd8f5a5fef8bb8eeb694b6e87be180b0db49d13a96`;
- implementation merge = `e095c3fb04f0f83f3ec4597f2870772bc566634a`;
- `FIN-P17-WC-001` = CANONICAL_COMPLETE;
- `LOCK-FIN-P17-WC-001-01` = RELEASED;
- P17-D = READY_NOT_STARTED;
- P17-E..P17-I = NOT_STARTED;
- `G9_QUANT_VALIDATED` = NOT_REACHED.
