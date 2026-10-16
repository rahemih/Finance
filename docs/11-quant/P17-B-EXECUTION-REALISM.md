# P17-B — Fees / Spread / Slippage / Funding / Latency / Partial Fill Model

State: IMPLEMENTATION_ACTIVE  
Task: `FIN-P17-WB-001`

## Objective

Add deterministic execution realism to the canonical P17-A event-driven backtest engine without introducing hidden production assumptions.

P17-B implements a simulation-only execution adapter. It never connects to a broker or exchange.

## Explicit inputs

Every simulated market event must have a matching historical execution context containing:
- event sequence and time;
- information-availability time;
- asset identity and price scale;
- visible bid depth;
- visible ask depth;
- source evidence SHA-256;
- optional historical funding event/rate/mark/evidence.

Runtime policy must explicitly provide:
- taker fee bps;
- decision latency nanoseconds;
- maximum displayed-depth participation bps.

There are **no production numeric defaults**.

## Spread and slippage

Buy decisions consume the historical ask side.

Sell decisions consume the historical bid side.

The simulator walks displayed depth deterministically. Fill price is the depth-weighted average executable price represented on the canonical integer price scale.

Conservative scaled-price rounding is used:
- BUY → ceiling;
- SELL → floor.

Therefore spread and slippage are consequences of the supplied historical book rather than a hidden fixed slippage parameter.

## Partial fill / capacity

At each displayed level only the explicitly governed participation share is available to the simulator.

If available historical depth cannot complete the order:
- a partial fill is emitted;
- the P17-A decision remains unresolved;
- later market events may fill the remaining quantity.

Unresolved execution is never silently treated as a completed trade.

## Latency

A decision has an explicit eligibility time:

`decision_time_ns + decision_latency_ns`

No fill is possible before that time.

The next compatible historical execution context after eligibility may produce a fill.

## Fees

Each fill receives an explicit cash cost:

`abs(fill_notional) × taker_fee_bps / 10000`

The fee is included in P17-A cash/equity accounting.

## Funding

Funding is applied only when the historical context explicitly marks a funding event as due and carries:
- decimal funding rate;
- funding mark price;
- funding evidence SHA-256.

For signed position `q`:

`funding_cash_adjustment = -(q × funding_mark × funding_rate)`

Thus, for a positive funding rate:
- long pays;
- short receives.

P17-B extends P17-A with an optional signed `SimulatedCashAdjustment` hook. Simulators that do not implement the hook preserve the original P17-A behavior.

Deterministic event ordering is:
1. update market mark/context;
2. apply latency-eligible delayed fills;
3. apply explicit funding cash adjustment;
4. evaluate strategy;
5. apply an immediate fill only when latency permits.

## Point-in-time safety

Execution context must satisfy:

`available_at_ns <= simulated event_time_ns`

Missing or future context fails closed.

## Canonical upstream relationship

P17-B is designed to consume historical evidence derived from the existing canonical boundaries:
- P09-D Order Book / Spread / Depth / Imbalance;
- P09-E Liquidity Heatmap / displayed capacity;
- P09-F Funding observations;
- P05 canonical clock/latency evidence.

P17-B does not reinterpret those upstream modules as execution authority.

## Authority boundary

P17-B has no:
- profitability claim authority;
- G9 authority;
- broker/exchange execution authority;
- order-routing authority;
- Demo/Shadow/Live promotion authority.

P17-C..P17-I = NOT_STARTED.  
`G9_QUANT_VALIDATED` = NOT_REACHED.  
P18 = NOT_STARTED.  
LIVE_TRADING = DISABLED.  
AUTO_TRADING = DISABLED.
