# NEXUS QUANT — Capital Intelligence & Rotation Architecture Addendum

STATE = ADDENDUM_CANONICAL  
ID = `CIRA-001`  
TASK = `FIN-P00-WZ-001`  
LINEAR = `HOS-250`  
OWNER_AUTHORIZATION = `2026-10-11`  
MASTER_ROADMAP = `v2.0 / FROZEN / UNCHANGED`  
P12_PHASE_AUTHORIZATION = `REQUIRED / NOT_GRANTED_BY_THIS_ADDENDUM`  
LIVE_TRADING = `DISABLED`  
AUTO_TRADING = `DISABLED`

## 1. Purpose

This addendum extends NEXUS QUANT from an asset-level signal platform into a governed **capital-intelligence and allocation system** while preserving every canonical gate and completed phase.

It introduces two primary capabilities:

1. **SCFI — Smart Capital Flow Intelligence**
2. **CARE — Cross-Asset Capital Rotation & Reallocation Engine**

It also formalizes thirteen supporting capabilities:

- No-Trade Guardian;
- Market Regime Brain/gating;
- Relative Strength engine;
- Market Memory;
- Decision Autopsy;
- Probability Calibration feedback;
- Capital Preservation Mode;
- Devil's Advocate / Red-Team challenge;
- Cost-aware rotation;
- Opportunity League;
- Portfolio Risk Budget;
- permanent 20-account / two-month Demo-Shadow laboratory;
- Staged Entry / Staged Exit / Adaptive Position Scaling.

## 2. Non-negotiable boundaries

- The frozen Master Roadmap is not edited.
- P08-P11 remain CANONICAL_COMPLETE.
- P12 remains OWNER_PHASE_AUTHORIZATION_REQUIRED.
- Whale activity is **never** a primary standalone signal.
- A single large transfer, wallet move, COT observation, news item, indicator, order-book event or LLM judgment cannot directly create a trade.
- Existing canonical contracts are not destructively rewritten.
- Future changes to completed contracts must be backward-compatible extensions or separately versioned contracts under a governed task.
- A5 Risk Engine and P16 Pre-Trade Firewall retain independent veto.
- Positive intelligence evidence is not execution authority.
- Live and Auto Trading remain disabled until the canonical roadmap reaches explicit gates and Owner approval.

## 3. SCFI — Smart Capital Flow Intelligence

### 3.1 Goal

SCFI answers:

> "Where is meaningful capital pressure building or leaving, how reliable is that observation, and is it consistent across independent evidence families?"

### 3.2 Evidence families

SCFI may consume:

**Market microstructure / P09**
- signed trade flow;
- Delta / CVD;
- volume profile;
- order-book depth and imbalance;
- spread and liquidity;
- open interest;
- funding;
- liquidation pressure;
- crowding/capacity.

**Crypto fundamental/on-chain / P10**
- chain-anchored transaction/transfer activity;
- supply/holder/network activity;
- validated exchange-flow evidence only where wallet attribution is independently supported;
- stablecoin issuance/flow evidence only when source/provenance is governed;
- exchange-to-wallet / wallet-to-exchange context only with confidence metadata.

**Macro / commodities / P10**
- rates/yields;
- currency macro differentials;
- gold/oil supply-demand/flow context;
- CFTC/COT or other official positioning evidence where available.

**News / P11**
- reliable event context;
- topic/importance;
- sentiment;
- freshness/decay;
- rumor controls.

### 3.3 Output classes

SCFI may emit descriptive capital-flow states such as:

- `INFLOW`
- `OUTFLOW`
- `ACCUMULATION`
- `DISTRIBUTION`
- `ROTATION_SUSPECTED`
- `CROWDING_RISK`
- `NEUTRAL`
- `INSUFFICIENT_EVIDENCE`

Each output must include source lineage, as-of time, evidence families, confidence/uncertainty, invalidation conditions and attribution limitations.

### 3.4 Whale safety rule

"Whale tracking" is treated as **large-flow evidence**, not identity certainty.

Unknown or weakly labelled wallets remain unknown. An exchange transfer does not imply a sale; a withdrawal does not imply a buy. Entity attribution must be provenance-aware and fail closed when uncertain.

## 4. CARE — Cross-Asset Capital Rotation & Reallocation Engine

### 4.1 Goal

CARE answers:

> "Given what we already own, is there a materially better risk-adjusted place for some of this capital?"

Eligible comparison may include governed Crypto spot/futures, Forex exposures, Gold/context instruments and cash-like/unallocated capital.

### 4.2 Portfolio-action candidates

CARE may emit:

- `KEEP`
- `REDUCE`
- `ROTATE`
- `HEDGE`
- `EXIT`
- `NO_ACTION`

These are **portfolio-action candidates**, not broker orders.

### 4.3 Rotation decision basis

A rotation must compare at least:

- expected opportunity/return evidence;
- uncertainty;
- volatility and drawdown risk;
- portfolio correlation/concentration;
- liquidity/capacity;
- spread;
- fees/commissions;
- slippage;
- funding/carry;
- latency/partial-fill risk;
- event risk;
- regime compatibility;
- tax/legal/account constraints when later known;
- opportunity persistence/hysteresis.

A small improvement is not enough. Rotation must survive costs and uncertainty.

No fixed production threshold is declared here; thresholds require governed empirical calibration.

## 5. Supporting capability set

### 5.1 No-Trade Guardian

The system must be allowed to decide that the best action is **nothing**.

Triggers may include contradictory evidence, degraded data, event risk, poor liquidity, excessive spread, stale signals, insufficient sample/context, extreme uncertainty or portfolio-risk exhaustion.

### 5.2 Market Regime Brain

Canonical P08-G Regime output remains valid and is reused rather than rebuilt.

Future consumers should gate strategy/feature usefulness by conditions such as trending, ranging, transition/conflict, volatility state and event-driven regime.

No completed P08 contract requires destructive modification.

### 5.3 Relative Strength

P13 should compare opportunities cross-sectionally rather than evaluate each asset in isolation.

Relative-strength output is ranking evidence, not a trade by itself.

### 5.4 Market Memory

P12 should store regime-aware historical relationships, analogs, event studies and lead/lag evidence for SCFI/CARE.

Historical similarity is evidence with uncertainty, never a promise that history will repeat.

### 5.5 Decision Autopsy

P18/P22 should explain losing and winning decisions by cause category:

- thesis/evidence failure;
- timing failure;
- regime mismatch;
- execution/slippage failure;
- event shock;
- sizing/risk failure;
- data-quality failure;
- model/calibration error;
- normal probabilistic loss.

A losing trade is not automatically a bad decision, and a winning trade is not automatically a good decision.

### 5.6 Probability Calibration

P14 probabilities must be tested against realized outcomes.

If events scored near 70% only occur near 50%, the model is miscalibrated even if recent PnL is positive.

Calibration correction must not auto-promote a model to Live.

### 5.7 Capital Preservation Mode

P15/P22 should support NORMAL, DEFENSIVE, DE_RISK and HALT-style capital postures driven by governed drawdown, uncertainty and system-health rules.

The system may reduce size, leverage, strategy count or new-risk intake, but cannot silently relax risk ceilings.

### 5.8 Devil's Advocate / Red-Team

P14-G already contains independent Red-Team challenge. This addendum strengthens its future acceptance criteria:

Before a material action candidate, the challenge path should search for contrary evidence, crowding, event risk, stale assumptions, hidden correlation and failure modes.

### 5.9 Cost-Aware Rotation

CARE must include full transition cost and not chase small ranking changes.

Hysteresis/cooldown policy should prevent repeated BTC↔Gold↔BTC churn caused by noise.

### 5.10 Opportunity League

P13/P23 should expose a ranked opportunity table across assets/markets.

Ranking must separate:
- opportunity;
- risk;
- uncertainty;
- liquidity/capacity;
- cost;
- regime quality;
- evidence freshness.

A single opaque "magic score" is not sufficient as the only explanation.

### 5.11 Portfolio Risk Budget

P15 should allocate a finite total risk budget across strategies/assets/markets.

One strategy cannot spend risk independently of the rest of the portfolio.

### 5.12 Permanent 20-account / two-month Demo-Shadow laboratory

P18/P19 should operate a governed parallel laboratory.

Reference topology:
- ~5 Champion/Baseline portfolios;
- ~5 Strategy Challengers;
- ~5 Risk/Allocation Challengers;
- ~5 Execution/Stress variants.

The exact count may be calibrated, but **20** is the initial target.

The platform remains operational 24/7. Crypto may generate decisions 24/7; Forex follows actual market sessions.

The first major evaluation window is **at least two continuous months**, but time alone is insufficient. Promotion also requires:
- adequate decision/trade sample size;
- regime diversity;
- cross-asset coverage as applicable;
- realistic spread/slippage/funding/latency;
- calibration evidence;
- drawdown/risk evidence;
- reproducibility;
- no unresolved critical incidents.

Twenty accounts are not twenty independent samples when they share the same signal/data. Statistical analysis must account for shared dependence.

### 5.13 Staged Entry / Staged Exit / Adaptive Position Scaling

The system may split a governed position or portfolio reallocation into multiple tranches instead of entering or exiting all at once.

**Ownership and sequence**
- P14 may describe an entry zone / invalidation and signal state, but does not decide risk size.
- P15 defines the maximum approved position, portfolio risk budget and candidate tranche plan.
- P16 independently revalidates every tranche that adds exposure immediately before execution.
- P20 executes accepted tranches idempotently and handles cancellation, partial fill, retry and reconciliation.
- P21 manages partial closes, reductions, trailing remainder and staged exit lifecycle.

**Mandatory rules**
- total maximum position and maximum loss/risk are bounded before the first entry tranche;
- filled plus pending approved exposure cannot exceed P15 ceilings;
- each additional risk-increasing tranche requires fresh signal/thesis, regime, data quality, liquidity, event-risk and portfolio-risk validation;
- an invalidation breach cancels all remaining entry tranches;
- deterioration to WAIT / NO_TRADE, insufficient liquidity, stale data, risk-budget exhaustion or firewall failure cancels or blocks the next tranche;
- price moving against the position is **not** by itself a reason to add size;
- Martingale, loss-chasing size escalation and uncapped averaging down are forbidden;
- pyramiding into a winning/strengthening thesis may be considered only inside the original or newly re-approved total risk ceiling;
- tranche count, spacing and size are not universal constants and remain empirically calibrated per strategy/market/regime;
- staged exits may include partial profit-taking, de-risking, hedge reduction, break-even/trailing protection and emergency risk reduction;
- CARE rotation/reallocation may be staged to reduce timing, liquidity and execution risk.

**Example semantics — illustrative only**

A future P15 policy might approve a BTC position with a maximum exposure of 10,000 units and a maximum governed risk budget. A candidate plan may use three tranches such as 30% / 30% / 40%, but those percentages are not canonical defaults.

After tranche 1, tranche 2 is executed only if the thesis remains valid and P16 still passes. If price falls solely because the trade is wrong and invalidation is breached, the remaining tranches are cancelled rather than used to average down.

For exits, a governed policy may reduce exposure progressively, for example at multiple validated targets or risk-state changes, while a remainder is protected by a trailing or dynamic rule. Exact percentages require P17/P18/P19 evidence.

## 6. Impact and remediation matrix

| Phase | Existing work | Decision | Required action |
|---|---|---|---|
| P05 Real-Time Data | CANONICAL_COMPLETE | NO_CHANGE | Reuse canonical streams. Add new provider adapters only later if SCFI requires a source not already covered. |
| P06 Historical / Feature Store | CANONICAL_COMPLETE | EXTEND_LATER | Add versioned capital-flow/relative-strength/rotation features only through backward-compatible definitions. |
| P07 Data Quality / Provenance | CANONICAL_COMPLETE / G5 PASS | NO_CHANGE + REUSE | Apply existing quality/provenance/quarantine rules to every future flow/label source. |
| P08 Technical Intelligence | CANONICAL_COMPLETE / G6 PASS | NO_CHANGE | Reuse technical/regime evidence. Do not reopen family models for this addendum. |
| P09 Order Flow / Liquidity | CANONICAL_COMPLETE | NO_CHANGE + COMPOSE | SCFI composes existing Delta/CVD/book/OI/funding/liquidation/crowding evidence downstream. |
| P10 Fundamental / Macro | CANONICAL_COMPLETE | NO_CHANGE + EXTEND_SOURCE_LATER | Reuse macro/gold/on-chain contracts. Independently validate wallet/entity labels before exchange-flow claims. |
| P11 News / Sentiment | CANONICAL_COMPLETE | NO_CHANGE | Reuse reliability/freshness/topic/sentiment context. |
| P12 Market Memory | NOT_STARTED | EXTEND_PLANNED_SCOPE | Add capital-flow edges, rotation episodes, cross-asset lead/lag and analog provenance when Owner authorizes P12. |
| P13 Timing / Opportunity | NOT_STARTED | EXTEND_PLANNED_SCOPE | Add Relative Strength, Opportunity League, No-Trade Guardian and rotation opportunity ranking. |
| P14 Signal / Probability | NOT_STARTED | EXTEND_PLANNED_SCOPE | Add calibration/Red-Team inputs and entry-zone/invalidation semantics that can support staged plans; signal remains separate from risk sizing. |
| P15 Risk / Portfolio | NOT_STARTED | MAJOR_EXTENSION | Add CARE optimizer, risk budget, concentration/correlation-aware sizing, Capital Preservation Mode, maximum position sizing and adaptive tranche-plan ownership. |
| P16 Pre-Trade Firewall | NOT_STARTED | EXTEND_PLANNED_SCOPE | Add rotation cost/liquidity/stale-price/two-leg checks plus mandatory fresh approval for every risk-increasing tranche. |
| P17 Backtest / Strategy Factory | NOT_STARTED | MAJOR_EXTENSION | Backtest SCFI/CARE and staged entry/exit/scaling policies with realistic costs, OOS/walk-forward, Monte Carlo, sensitivity, capacity and anti-Martingale controls. |
| P18 Demo Learning | NOT_STARTED | MAJOR_EXTENSION | Add 20-account laboratory, Decision Autopsy, Champion/Challenger, calibration and staged-plan outcome tracking. |
| P19 Shadow / Digital Twin | NOT_STARTED | MAJOR_EXTENSION | Run two-month real-data/no-capital program including tranche timing, partial-fill, cancellation and staged execution drift. |
| P20 Execution / OMS | NOT_STARTED | EXTEND_PLANNED_SCOPE | Support staged entry/exit/rebalance/rotation, tranche state machine, idempotent execution, partial-fill handling, cancellation, orphan-leg recovery and reconciliation. |
| P21 Position Management | NOT_STARTED | EXTEND_PLANNED_SCOPE | Support partial closes/reductions, staged exits, trailing remainder, hedges and staged portfolio rebalance lifecycle. |
| P22 Operations | NOT_STARTED | EXTEND_PLANNED_SCOPE | Add Decision Autopsy telemetry, capital-preservation state, diagnostics and safe self-healing. |
| P23 UX | NOT_STARTED | EXTEND_PLANNED_SCOPE | Add Capital Flow Map, Opportunity League, portfolio-rotation proposal plus staged-plan view showing total target, filled/pending tranches, risk and cancellation reasons. |
| P24 Controlled Production | NOT_STARTED | NO_GATE_BYPASS | CARE/SCFI remain subject to Manual → Semi-Auto → Micro-Capital → Canary → Controlled Auto and explicit Owner approval. |

## 7. Delete / modify / add decision

### Delete

**Nothing from canonical P05-P11 is deleted.**

No completed technical, order-flow, fundamental or news module is made obsolete by this addendum.

### Modify later

Only future governed, backward-compatible extensions are expected for:
- P06 feature definitions;
- optional P10 source/label validation where needed;
- P12-P23 planned contracts before implementation.

### Add

New logical components:
- SCFI;
- CARE;
- Relative Strength / Opportunity League;
- No-Trade Guardian integration;
- Capital Preservation / portfolio risk-budget logic;
- Decision Autopsy;
- Demo-Shadow laboratory orchestration;
- Staged Entry / Staged Exit / Adaptive Position Scaling policy.

## 8. Evaluation model

SCFI and CARE cannot be accepted because they "look sensible."

They require:
- point-in-time data;
- anti-lookahead;
- independent-source/provenance checks;
- negative controls;
- out-of-sample and walk-forward evaluation;
- realistic transaction/execution costs;
- calibration;
- regime slicing;
- stress/sensitivity;
- capacity/liquidity testing;
- portfolio-level drawdown/risk-of-ruin;
- Demo/Shadow evidence.

Primary performance question:

> Does the policy improve **risk-adjusted portfolio outcomes after realistic costs** versus governed baselines?

Win rate alone is insufficient.

## 9. Example decision semantics

Example only, not a live recommendation:

Current portfolio:
- BTC exposure = 100 units.

Evidence:
- BTC technical momentum weakening;
- SCFI = distribution/outflow evidence with uncertainty;
- Gold macro/regime evidence improving;
- Gold relative opportunity stronger;
- event risk tomorrow is high.

Correct behavior may be:

`NO_ACTION / RECHECK_AFTER_EVENT`

rather than immediate rotation.

If the event passes and the advantage persists after costs/risk, CARE might later produce:

`ROTATE_CANDIDATE: REDUCE BTC 20-30%, ADD GOLD EXPOSURE 20-30%`

The actual percentage must be produced by P15 portfolio/risk policy and must pass P16 before any future execution.

## 10. Governance and adoption sequence

1. Canonicalize this addendum.
2. Do **not** start P12 automatically.
3. When Owner authorizes P12, incorporate the P12 items from the impact matrix into its governed Task Contracts.
4. Carry the planned extensions forward through P13-P23.
5. Validate SCFI/CARE in P17.
6. Run the parallel Demo/Shadow laboratory in P18/P19.
7. Do not permit real-capital rotation until canonical safety and production gates pass.

## 11. Final principle

NEXUS QUANT should not merely ask:

> "Should I buy BTC?"

It should ask:

> "Given all available opportunities, uncertainty, costs and portfolio risk, where should capital be allocated now — and is doing nothing better?"

The default when evidence is insufficient is **WAIT / NO_ACTION**, not forced activity.


## 12. Canonical closure evidence — 2026-10-11

- Task: `FIN-P00-WZ-001 = CANONICAL_COMPLETE`
- Linear: `HOS-250`
- Implementation PR: `#239 = MERGED`
- Final implementation head: `3d5b1ce16bd878f6cdf84026f48f59ffcd7d143a`
- Implementation merge SHA: `3e52542b4c27465019af34c444d21d754b010297`
- PR Governance: `38129992612 = SUCCESS`
- PR artifact: `sha256:4f980bc300db85f45dbb214a1151a629ec3031eb067f7b80871e16e05a4a13e9`
- Post-merge Governance: `38130068247 = SUCCESS`
- Post-merge artifact: `sha256:0de2ad3dae04f3e53c6c7139073a7e97323c0f51c3cbabd8b0c92be28c37f042`
- Post-merge Branch Hygiene: `38130068333 = SUCCESS`
- Governance regression steps: `111/111 completed with no failures`
- Master Roadmap v2.0: `UNCHANGED / FROZEN`
- P08-P11 canonical closures: `UNCHANGED / VALID`
- P12: `OWNER_PHASE_AUTHORIZATION_REQUIRED`
- LIVE_TRADING: `DISABLED`
- AUTO_TRADING: `DISABLED`
- Lock: `LOCK-FIN-P00-WZ-001-01 = RELEASED`

Canonical decision:
- no deletion of completed P05-P11 functionality;
- no destructive modification to completed contracts;
- future extensions are governed and backward-compatible/versioned;
- SCFI/CARE and the supporting capability set are adopted as cross-cutting future requirements;
- P12 implementation does not start as part of this closure.


## 13. CIRA-001 staged-scaling extension — 2026-10-11

Task: `FIN-P00-WY-001`  
Linear: `HOS-252`  
State: IMPLEMENTATION_ACTIVE

Owner-authorized extension:
- staged entry / scale-in;
- staged exit / scale-out;
- adaptive tranche sizing;
- staged CARE rotation / rebalance;
- per-tranche P15/P16 revalidation;
- explicit anti-Martingale / anti-loss-chasing boundary.

This extension does not authorize P12 and does not enable Live or Auto Trading.
