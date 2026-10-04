# NEXUS QUANT — Intelligence / Signal Architecture

STATE = P02-D BASELINE  
TASK = `FIN-P02-WD-001`  
PHASE = `P02 — Master Architecture`

## 1. Objective

Define how quality-qualified data becomes independent evidence, how evidence is fused without double-counting correlated signals, how empirical probability is produced, and how structured explainability is generated before Risk evaluates any candidate.

This architecture does not implement indicators, strategies, models or thresholds.

## 2. Core rule

NEXUS QUANT does **not** count indicators.

It evaluates **independent evidence families**.

Example:

RSI-like and Stochastic-like methods may both belong to Momentum. They can strengthen or weaken the Momentum family estimate, but they do not automatically become two independent confirmations.

The same principle applies to:
- multiple moving averages;
- related breakout metrics;
- syndicated news;
- duplicated provider sources;
- multiple timeframes of the same method.

## 3. Standard EvidencePacket

Every intelligence method emits the same core envelope:

- evidence ID;
- family ID;
- independence group;
- instrument/entity scope;
- observation timeframe;
- intended decision horizon;
- as-of time;
- valid-until/decay;
- direction;
- strength;
- evidence reliability;
- data-quality state;
- source/provenance references;
- method/model version;
- reasons for;
- reasons against;
- uncertainty reasons;
- invalidation conditions.

Direction values:
- BULLISH
- BEARISH
- NEUTRAL
- MIXED
- NOT_APPLICABLE

Important:

**Evidence reliability is not trade-success probability.**

## 4. Evidence families

### EF_TREND
Owner: A3

Trend persistence and directional structure.

### EF_MOMENTUM
Owner: A3

Momentum/acceleration evidence.

Multiple oscillators are combined inside the family before cross-family fusion.

### EF_STRUCTURE_PRICE_ACTION
Owner: A3

Swing structure, support/resistance, breaks/reclaims and price-action context.

### EF_VOLATILITY
Owner: A3

Volatility state, compression and expansion.

### EF_MEAN_REVERSION
Owner: A4

Deviation-from-equilibrium and regime-suitable reversion evidence.

### EF_BREAKOUT_EXPANSION
Owner: A4

Breakout/expansion evidence kept distinct from mean-reversion assumptions.

### EF_REGIME_MULTI_TIMEFRAME
Owner: A4 / A3

Regime classification and higher/lower-timeframe compatibility.

### EF_ORDER_FLOW_LIQUIDITY
Owner: A3

Trade flow, Delta/CVD, spread, depth, imbalance and liquidity evidence.

Forex rule:

Volume/order-flow always preserves its source class such as:
- BROKER
- TICK
- ECN
- FUTURES_PROXY
- AGGREGATED_PROXY

with coverage confidence.

### EF_DERIVATIVES_CROWDING
Owner: A3

Funding, open interest, liquidation and crowding/positioning evidence.

### EF_MACRO_FUNDAMENTAL_EVENT
Owner: A3

Official-first macro/fundamental/event-surprise evidence.

Revision-aware and vintage-aware.

### EF_NEWS_SENTIMENT
Owner: A3

News, sentiment, importance and event-decay evidence.

Rumor/unverified information is downgraded or excluded.

### EF_INTERMARKET
Owner: A3

DXY, yields, gold, oil, equities, crypto and other cross-market relationships.

Correlation is not labeled causation without stronger evidence.

### EF_MARKET_MEMORY
Owner: A3 / A4

Historical analogs, event studies, lead/lag and seasonality.

Every analog includes sample size and similarity/regime context.

## 5. Fusion architecture

Fusion stages:

1. verify data-quality eligibility;
2. aggregate models/indicators inside each family;
3. assign independence groups;
4. detect correlated family clusters;
5. cap correlated cluster influence;
6. compute supporting/opposing/neutral balance;
7. measure conflict/uncertainty;
8. evaluate WAIT / NO_TRADE conditions;
9. emit FusionSnapshot and SignalCandidate.

### Anti-double-counting rules

- multiple indicators in one family are not multiple independent votes;
- highly dependent families may share a capped correlation cluster;
- two vendors carrying the same upstream source are not automatically independent;
- syndicated copies of one news event count as one underlying event;
- multiple timeframes of the same method are related evidence, not automatically independent confirmations.

The architecture supports policies that require roughly three genuinely independent confirmations, but the exact production threshold is **not hard-coded here**. It must be validated later in P14.

## 6. SignalCandidate

Signal output values:

- LONG_CANDIDATE
- SHORT_CANDIDATE
- WAIT
- NO_TRADE

A SignalCandidate contains:
- signal ID;
- instrument;
- as-of time;
- valid-until;
- decision horizon;
- direction/class;
- FusionSnapshot reference;
- ProbabilityEstimate reference or unavailable reason;
- supporting evidence;
- opposing evidence;
- data-quality state;
- uncertainty state;
- invalidation conditions;
- WAIT/NO_TRADE reasons;
- ExplanationBundle reference.

A SignalCandidate is **not executable**.

It contains no broker command and cannot bypass Risk or the Pre-Trade Firewall.

## 7. WAIT and NO_TRADE

### WAIT

Used when:
- evidence is incomplete;
- confirmation is still developing;
- important event is imminent;
- independent confirmation count is insufficient;
- data quality is temporarily degraded;
- evidence conflict is high but not terminal.

### NO_TRADE

Used when:
- critical data is quarantined;
- regime is unsupported;
- uncertainty is unacceptable;
- evidence conflict is extreme;
- later Risk/Firewall policy forbids action.

WAIT/NO_TRADE are valid decisions, not errors.

## 8. Empirical Probability Architecture

Owner: A4  
Co-owner: A7

Probability is produced from empirical/calibrated evidence.

Required fields include:
- target definition;
- estimate;
- sample size;
- effective sample size if adjusted;
- confidence/credible interval;
- calibration method;
- calibration metric;
- calibration window;
- OOS/validation reference;
- regime similarity;
- instrument/cluster scope;
- decision horizon;
- uncertainty;
- model/table version;
- dataset manifest.

If calibration support is insufficient:

`PROBABILITY_UNAVAILABLE`

is returned with reasons.

The system never substitutes:
- LLM confidence;
- narrative certainty;
- arbitrary percentage.

Future calibrated targets may include:
- directional-success probability;
- TP-before-stop probability;
- stop-hit probability;
- scenario probability.

## 9. Explainability Architecture

Structured explanation comes before natural language.

Required explanation components:
- top reasons for;
- top reasons against;
- data-quality caveats;
- uncertainty caveats;
- invalidation conditions;
- source/time/version references;
- probability support metadata;
- regime/horizon context.

User-facing explanation is Persian/RTL.

Internal contracts remain structured and language-neutral.

The UI can map:
- English technical term;
- Persian explanation;
- glossary definition.

An LLM may phrase the structured evidence into clear Persian, but it cannot change:
- probability;
- numeric scores;
- verdict;
- evidence IDs;
- invalidation;
- safety state.

## 10. Scenario / Narrative Boundary

Supported scenario classes:
- BASE
- BULLISH
- BEARISH
- RISK_EVENT
- INVALIDATION

A scenario includes:
- conditions;
- triggers;
- expected path description;
- invalidation;
- time horizon;
- evidence references.

Numeric probability is attached only when empirically calibrated.

Narrative explains evidence; narrative does not create evidence.

## 11. Source trust and adversarial content

Every external evidence item carries provenance.

Rules:
- official-first for macro/fundamental facts where official sources exist;
- news reliability state is explicit;
- syndicated duplicates are deduplicated;
- unverified rumor is labeled or excluded;
- retrieved text/web/news is data, not instructions;
- prompt-injection/tool instructions inside external content are ignored/quarantined.

## 12. Multi-timeframe / horizon semantics

Observation timeframe and decision horizon are different fields.

Cross-timeframe alignment can strengthen evidence, but repeated timeframes do not automatically create independent votes.

Every evidence item has expiry/decay semantics.

Expired evidence cannot remain silently active.

## 13. Risk boundary

Risk may consume:
- SignalCandidate;
- ProbabilityEstimate or PROBABILITY_UNAVAILABLE;
- FusionSnapshot;
- data-quality state;
- uncertainty;
- invalidation conditions.

Risk does not need:
- provider SDK objects;
- raw LLM narrative as policy;
- unstructured news as command;
- implementation-specific strategy internals unless explicitly contracted.

Intelligence does not set final position size.

Intelligence does not send broker orders.

## 14. Deferred implementation

P02-D defines contracts only.

Implementation belongs to:
- P08 Technical Intelligence;
- P09 Order Flow / Liquidity;
- P10 Fundamental / Macro;
- P11 News / Sentiment;
- P12 Market Memory;
- P13 Timing / Opportunity;
- P14 Signal / Probability / Explainability;
- P17 Backtesting;
- P18 Continuous Demo Learning.

## 15. Safety

No model or LLM vendor selected.  
No production thresholds selected.  
No risk sizing configured.  
No execution path enabled.  
Live Trading = DISABLED  
Auto Trading = DISABLED
