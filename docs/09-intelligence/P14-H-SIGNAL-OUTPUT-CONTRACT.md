# P14-H — Signal Output Contract

State: CANONICAL_COMPLETE  
Task: `FIN-P14-WH-001`  
Linear: SYNC_BLOCKED_FREE_ISSUE_LIMIT

## Objective

Produce the final deterministic **analytical** signal envelope for P14:

- `LONG`
- `SHORT`
- `WAIT`
- `NO_TRADE`

This is not risk approval and not an execution order.

## Precedence

1. P13 hard no-trade, blocked fusion, or Red-Team REJECT -> `NO_TRADE`.
2. Expired/no-chase, ineligible candidate, Red-Team CAUTION, or insufficient probability/outcome support -> `WAIT`.
3. Only a fully coherent ACTIVE + FUSED + QUALIFIED + CALIBRATED_TP_STOP + Red-Team CLEAR chain may become `LONG` or `SHORT`.

## Price geometry

Directional outputs require explicit versioned scaled-integer geometry:
- reference price;
- entry low/high;
- entry anchor;
- invalidation price;
- price scale;
- geometry version hash.

Candidate Stop and Target are deterministically derived from the P14-E canonical barrier distances using nearest-half-up basis-point arithmetic.

P14-H does not invent a reference price, entry zone, invalidation distance, risk budget, size or leverage.

WAIT / NO_TRADE outputs carry no directional price geometry.

## Preserved analytical context

The output preserves:
- empirical directional probability;
- overall uncertainty;
- TP_FIRST / STOP_FIRST / NEITHER probabilities;
- evidence freshness exclusions;
- Persian reasons for/against;
- exact upstream fusion, qualification, outcome, explanation and Red-Team identities.

## Authority boundary

P14-H has no portfolio-risk, sizing, leverage, risk-approval or execution authority. Those remain later-phase concerns.

LIVE_TRADING = DISABLED.  
AUTO_TRADING = DISABLED.


## Canonical closure

- Implementation PR: #297
- Implementation Governance: `38514304803` / SUCCESS
- Implementation artifact: `sha256:56a1ca1ae2f175138290430fba40ad015fba4cbef7fe4e7a66500f9e27b277d0`
- Implementation merge: `394a2ee0aa194b119ac3441ac7b11e260353cd67`
- Post-merge Governance: `38514523908` / SUCCESS
- Branch Hygiene: `38514523830` / SUCCESS
- Lock: RELEASED
- Linear sync: BLOCKED_FREE_ISSUE_LIMIT
- P14-I: READY_NOT_STARTED
- P15: NOT_STARTED
