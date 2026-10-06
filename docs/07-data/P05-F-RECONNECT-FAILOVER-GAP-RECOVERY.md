# P05-F — Reconnect / Failover / Gap Recovery

Task: `FIN-P05-WF-001`  
Linear: `HOS-192`  
State: CANONICAL_COMPLETE  
Lock: RELEASED  
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


## Canonical closure evidence

- implementation PR: `#128` = MERGED;
- implementation head: `d3eb774e22618c3fb8a7b94ed675e827d1d772b1`;
- implementation merge SHA: `e2283b344f21b533395df1c6194c5c8ca74b9e59`;
- PR Governance run: `37449455344` = SUCCESS;
- PR artifact: `11405795185`;
- PR artifact digest: `sha256:00c2f97b3bef457eb8738d709aa12eecbef5773c6b017d53a3cd18580a848f20`;
- post-merge Governance run: `37449575606` = SUCCESS;
- post-merge artifact: `11405835208`;
- post-merge artifact digest: `sha256:9b34690a418313b51d90018f7ac23ebf40d275086a7e1c9d505241daf2bcc7d7`;
- post-merge Branch Hygiene run: `37449575567` = SUCCESS;
- strict Pyright: `0 errors / 0 warnings`;
- foundation tests: `22/22 PASS`;
- P05 tests: `95/95 PASS`;
- deterministic P05-F observations: `5`;
- deterministic P05-F evidence SHA-256: `0d1f7d3cd22a2c4409f0586b95244aa3cf22a2fd63faa27cdb8348f399e4f22f`;
- reproducible artifact SHA-256: `c2e05c4b1e0b25c3eb5041c9e890c35b18973e90371ca71900dc7be5b309145f`;
- rollback manifest SHA-256: `8540fda3cd2e809831b0899393c8d92562493be7ce4f9f35f8e873997fdea74c`;
- verdict: PASS.

Next ready workstream: `P05-G — Latency / Throughput / Soak Validation`.
