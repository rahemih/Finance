# P05-F — Reconnect / Failover / Gap Recovery

Task: `FIN-P05-WF-001`  
Linear: `HOS-192`  
State: IN_PROGRESS  
Lead: A2 Data Agent  
Supporting: A9 Operations, A8 Security, A10 Evidence/Audit, A1 Architecture, A0 Governance

## Objective

Define the provider-neutral recovery-control boundary after canonical streaming/heartbeat/backpressure. P05-F implements deterministic recovery state and evidence; it does not open provider network connections, resolve credentials or activate automatic data-source failover.

## Sequence integrity

Current canonical provider baselines do not justify a universal contiguity assumption.

- Kaiko: `sequenceId` is lexicographically sortable; contiguity is explicitly not claimed.
- dxFeed: the baseline preserves an integer sequence but P05-B did not certify contiguous semantics.
- Databento: the baseline preserves venue sequence but P05-C did not certify that every integer must be contiguous for the canonical consumer stream.

Therefore current provider policies can detect:
- FIRST;
- ADVANCING;
- DUPLICATE;
- OUT_OF_ORDER.

A `GAP` is emitted only when a future governed provider policy explicitly marks integer sequence semantics as contiguous. This prevents false missing-data claims.

## Reconnect policy

Canonical deterministic retry budget:

- max attempts: 5;
- base backoff: 1 second;
- capped backoff: 30 seconds;
- circuit-open cooldown: 60 seconds;
- jitter: none in the deterministic canonical baseline.

State flow:

`ACTIVE/DEGRADED → WAITING_RETRY → RECONNECTING → RECOVERY_VALIDATION → ACTIVE`

Retry exhaustion moves the stream to `CIRCUIT_OPEN`. A cooldown must elapse before a controlled probe.

A successful transport reconnect is never sufficient by itself to mark market data healthy.

## Recovery validation

After reconnect:
- sequence tracking restarts explicitly for the affected stream;
- the first accepted event establishes a new recovery baseline;
- Kaiko ORDER_BOOK specifically requires a fresh full `SNAPSHOT` before returning ACTIVE;
- an UPDATE before the required snapshot remains recovery-pending.

## Data failover

P01-F defines candidate redundancy but does not authorize automatic source switching.

P05-F therefore exposes only:
- `PRIMARY_ACTIVE`;
- `BACKUP_VALIDATION_REQUIRED`;
- `FAIL_CLOSED`.

A healthy candidate backup is not activated automatically. Cross-provider freshness/schema/divergence validation and authorization remain P07 work.

Current conditional backup metadata is preserved from P01-F:
- Crypto / Kaiko → CoinAPI candidate;
- Forex / dxFeed → Massive or Twelve Data candidate;
- Futures context / Databento → dxFeed candidate.

No new provider is selected by P05-F.

## Safety

- production network reconnect: NOT_IMPLEMENTED;
- live endpoint: NONE;
- credential resolution: NONE;
- automatic data failover: DISABLED;
- execution failover: OUT_OF_SCOPE;
- CANARY: DISABLED;
- LIVE_TRADING: DISABLED;
- AUTO_TRADING: DISABLED.
