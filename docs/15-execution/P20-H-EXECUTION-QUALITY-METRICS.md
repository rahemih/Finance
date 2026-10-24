# P20-H — Execution-quality Metrics

Task: `FIN-P20-WH-001`  
Phase: P20 — Execution & Order Management  
State: IN_PROGRESS  
Lock: `LOCK-FIN-P20-WH-001-01`  
Dependency: P20-A..P20-G CANONICAL_COMPLETE

## Objective

Measure deterministic execution quality over explicit reference/sandbox execution observations while preserving exact P20-G reconciliation lineage.

P20-H does **not** claim observed production quality and does not validate G11. It provides a deterministic measurement contract for P20-I simulation/gate work.

## Metrics

- ACK latency in integer nanoseconds;
- first-fill latency in integer nanoseconds when a fill exists;
- terminal latency in integer nanoseconds;
- fill ratio in integer PPM;
- signed adverse slippage in integer PPM:
  - positive = adverse;
  - negative = price improvement;
  - BUY and SELL direction are normalized.

Summaries use deterministic nearest-rank p50/p95, maximum latency/slippage and minimum fill ratio.

## Input integrity

Only observations with exact P20-G `MATCHED` reconciliation lineage are admitted. Unresolved reconciliation discrepancies must not contaminate execution-quality statistics.

## Quality bands

`WITHIN_REFERENCE_BUDGET`, `DEGRADED_REFERENCE`, and `REFERENCE_FAIL` are reference-policy classifications only. They are not production SLA certifications and cannot promote G11.

## Safety boundary

- source = explicit reference/sandbox execution only;
- real venue query = false;
- production execution certification = false;
- broker certification = false;
- credentials/account/KYC/funding = NONE;
- network mode = DISABLED;
- external order submission/mutation = false;
- automatic OMS mutation = false;
- Live execution authority = false;
- P20-I = NOT_STARTED;
- G11_EXECUTION_VALIDATED = NOT_REACHED;
- P21 = NOT_STARTED;
- LIVE_TRADING/AUTO_TRADING = DISABLED.
