# Observability & Evaluation Harness

## Trace contract

Each run must emit:
- task/run/agent/specialist/model ids;
- contract/schema versions;
- source refs/freshness;
- tool calls and decision gates;
- token input/output/cached counts where available;
- estimated/actual model and tool cost where available;
- end-to-end and per-step latency;
- retries/timeouts/circuit-breaker events;
- A5/A8 decisions;
- action class;
- evidence/audit refs;
- terminal state.

OpenTelemetry-compatible semantic mapping is preferred, but runtime selection remains deferred.

## Metrics

At minimum:
- success/fail/wait/no-trade/insufficient-evidence rates;
- schema rejection rate;
- stale-input rate;
- security/risk veto rate;
- tool error rate;
- retry count;
- p50/p95 latency;
- tokens/run;
- cost/run and cost/task;
- checkpoint/resume rate;
- specialist spawn count/depth;
- provenance completeness.

## Evaluation harness

The future executable harness must materialize the existing canonical evaluation matrix and include normal, ambiguous, missing/stale/conflicting data, injection, malicious tool instruction, forbidden action, provider/model outage, high volatility, nonsensical input, look-ahead leakage, extreme spread/slippage, duplicate/corrupt messages, timeout, retry loop, circuit breaker, A5/A8 veto, safe-stop, provenance, latency, cost and reproducibility cases.

Release rule: zero bypasses of A5/A8 or authority gates; zero silent schema coercions for execution-capable outputs.
