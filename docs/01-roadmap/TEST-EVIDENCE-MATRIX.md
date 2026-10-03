# Finance / NEXUS QUANT — Test & Evidence Matrix

STATE = GOVERNED_COMPANION  
TASK = `FIN-P00-WE-001`

## 1. Principle

A task is not complete because a test command is green. Evidence must show that the correct behavior was tested against the correct version, environment, data and policy.

Every evidence item should be attributable to:
- Task ID;
- Git SHA / build artifact;
- environment;
- dataset/provider/model/strategy/config/policy version where relevant;
- test or scenario identifier;
- timestamp;
- result and limitations;
- artifact/log/report location.

## 2. Validation-class matrix

| Validation class | Main purpose | Typical phases | Minimum evidence | Blocking when required? |
|---|---|---|---|---|
| Unit | local deterministic correctness | P04–P23 | test report tied to SHA | YES |
| Integration | component interaction | P04–P23 | integration report/logs | YES |
| Contract | API/event/schema compatibility | P02/P04/P05/P14/P16/P20 | schema/contract test output | YES |
| Regression | prevent known breakage | all implementation phases | named regression cases | YES |
| E2E | end-user/end-system flow | P20–P24, P23 | full-flow trace/screenshots/logs | YES |
| Security | vulnerabilities/access/abuse controls | P03/P04/P20/P22/P24 | scan + exploit/negative-test evidence | YES |
| Performance | latency/throughput/resource behavior | P05/P14/P20/P22/P23 | percentile distributions and environment | YES where target exists |
| Load | sustained expected workload | P05/P20/P22 | workload definition + resource/latency results | YES |
| Spike | sudden burst behavior | P05/P20/P22 | burst profile + recovery evidence | YES |
| Stress | behavior beyond expected limits | P05/P17/P20/P22 | failure boundary + safe degradation | YES |
| Soak | long-duration stability/leaks | P05/P20/P22 | duration, errors, memory/resource trend | YES |
| Chaos | controlled dependency/failure injection | P05/P20/P22 | scenario, blast radius, state transitions | gate-specific |
| Recovery | crash/restart/failover correctness | P05/P20/P21/P22 | recovery trace and reconciliation | YES |
| Restore | backup restoration correctness | P06/P22 | restored artifact/data verification | YES |
| Replay | deterministic reproduction | P06/P07/P19 | input snapshot + output hash/trace | YES |
| Data Quality | completeness/stale/outlier/provenance | P05–P12 | quality report and failed-data behavior | YES |
| Backtest | historical strategy behavior | P17 | dataset/strategy/cost version + results | YES |
| Walk-Forward | temporal robustness | P17 | fold definitions + OOS results | YES |
| Monte Carlo | uncertainty/path robustness | P17 | seed/config/distribution results | YES |
| Calibration | probability reliability | P14/P17 | reliability/calibration metrics | YES |
| Paper/Demo | non-capital operational behavior | P18 | journal, outcomes, risk/firewall traces | YES |
| Shadow | decisions alongside live market without execution | P19 | shadow trace and comparison metrics | YES |
| Broker Simulation | OMS/execution semantics | P20/P21 | order lifecycle/reject/fill/recovery scenarios | YES |
| Failover | backup provider/path behavior | P05/P20/P22 | trigger, switchover, gaps, recovery | YES |
| Accessibility | usable UI | P23 | automated + manual checks | YES for critical flows |
| Localization/RTL | Persian UX correctness | P23 | RTL screenshots/tests/terminology checks | YES |
| Audit/Reproducibility | reconstruct material decisions | P00/P14/P17/P19/P20/P24 | version/provenance chain | YES |

## 3. Phase evidence expectations

### P00

Evidence:
- protected `main`;
- required status checks;
- Task Contract schema;
- branch hygiene;
- Linear project/milestones;
- Toolchain Matrix;
- detailed roadmap package;
- no active conflicting locks.

Primary validation: Governance CI, state reconciliation, negative branch/rules checks.

### P01

Evidence:
- source-linked provider scorecards;
- jurisdiction/legal source dates;
- pricing/licensing assumptions with retrieval date;
- primary/backup comparison;
- explicit unknowns.

No provider passes because of popularity alone.

### P02

Evidence:
- ADRs;
- architecture diagrams;
- interface contracts;
- failure-mode analysis;
- capacity assumptions;
- security/risk reviews.

Architecture gate requires unresolved alternatives and tradeoffs to be documented.

### P03

Evidence:
- threat model;
- RBAC/MFA tests;
- secret-leak prevention;
- credential revocation;
- access-review records;
- audit integrity;
- incident exercise.

### P04

Evidence:
- clean bootstrap;
- reproducible build;
- CI runs;
- dependency lock/SBOM;
- test harness;
- clean-environment setup.

### P05

Evidence:
- per-provider contract tests;
- heartbeat/gap/reconnect;
- timestamp/sequence validation;
- latency p50/p95/p99 where applicable;
- expected-load and soak;
- failover/gap-recovery.

### P06

Evidence:
- raw-to-normalized lineage;
- historical completeness;
- dataset manifests/hashes;
- feature regeneration;
- retention and restore sample;
- macro vintage reconstruction.

### P07

Evidence:
- synthetic and real missing/duplicate/outlier/stale cases;
- cross-provider discrepancy cases;
- provenance/confidence traces;
- quarantine and fail-closed outputs;
- data-quality SLO dashboard/report.

### P08

Evidence:
- per-family benchmarks;
- independence/correlation analysis;
- regime/timeframe breakdowns;
- unit/regression tests;
- ablation evidence where useful.

### P09

Evidence:
- venue/order-book/trade reconciliation;
- delta/CVD/profile correctness;
- liquidity/capacity scenarios;
- derivative metric provenance;
- explicit Forex proxy labels and coverage confidence.

### P10

Evidence:
- official-source retrieval;
- event/vintage timeline reconstruction;
- revision handling;
- surprise calculations;
- release-time tests;
- stale-source behavior.

### P11

Evidence:
- dedup precision/recall sample;
- entity mapping evaluation;
- sentiment/importance evaluation;
- rumor/unconfirmed-source negative tests;
- source reliability metadata.

### P12

Evidence:
- relation provenance;
- rolling/conditional correlation validation;
- lead/lag methodology;
- event-study sample definitions;
- analog retrieval reproducibility;
- causality-language guardrail tests.

### P13

Evidence:
- session/calendar correctness;
- timing/ranking backtests;
- no-trade effectiveness;
- expiry/no-chase cases;
- ranking stability and concentration review.

### P14

Evidence:
- calibration curves/scores;
- sample sizes;
- uncertainty/confidence intervals;
- regime similarity;
- TP/Stop outcome definitions;
- Persian reason trace;
- Red-Team counter-evidence;
- deterministic signal contract.

### P15

Evidence:
- sizing scenarios;
- correlated exposure tests;
- leverage/margin stress;
- drawdown and risk-of-ruin simulations;
- counterparty caps;
- defensive-mode transitions.

### P16

Evidence:
- each firewall rejection reason;
- stale signal;
- price drift;
- duplicate;
- over-size/over-leverage;
- high spread/low liquidity;
- event/data/broker/system degradation;
- daily-loss breach;
- fail-closed behavior.

### P17

Evidence:
- realistic cost assumptions;
- anti-lookahead/leakage tests;
- OOS/WF;
- Monte Carlo/stress;
- capacity;
- strategy/model registry entry;
- reproducible report tied to dataset hash.

### P18

Evidence:
- continuous paper journal;
- outcome labeling;
- training-dataset lineage;
- experiment records;
- retraining reproducibility;
- challenger comparison;
- drift/decay alerts;
- proof that promotion requires governance.

### P19

Evidence:
- deterministic replay hashes/traces;
- shadow decisions;
- incident replay;
- Digital Twin fill/slippage comparison;
- paper/live drift metrics.

### P20

Evidence:
- adapter contract;
- order state transitions;
- idempotency;
- duplicate-prevention race tests;
- rejects/cancels/partial fills;
- retry/timeout/crash recovery;
- broker/exchange reconciliation;
- execution-quality metrics.

### P21

Evidence:
- TP/SL/partial/BE/trailing lifecycle;
- restart recovery;
- broker mismatch repair;
- emergency exit scenarios.

### P22

Evidence:
- telemetry coverage;
- state transitions NORMAL→DEGRADED→SAFE_MODE/HALTED/etc.;
- diagnostic accuracy;
- constrained self-heal rollback;
- backup and restore drills;
- DR exercise;
- incident/postmortem;
- capacity/SLO trends.

### P23

Evidence:
- Figma→implementation consistency;
- Persian RTL;
- responsive breakpoints;
- keyboard/focus/accessibility;
- notification severity/dedup/escalation;
- dangerous-action confirmations;
- core E2E workflows.

### P24

Evidence:
- fresh readiness dossier;
- all prerequisite gate freshness;
- kill-switch drills;
- manual/semi-auto/micro/canary stage results;
- capital/risk limits;
- reconciliation;
- incident readiness;
- explicit Owner approval at G13.

## 4. Evidence artifact hierarchy

Preferred order:
1. machine-readable test result/artifact;
2. deterministic log/trace/report tied to SHA;
3. dataset/model/config hash;
4. screenshots/video only when visual state matters;
5. human sign-off only where judgment/approval is genuinely required.

Screenshots alone should not prove backend correctness when machine evidence is available.

## 5. Required negative testing

High-risk controls must test rejection/failure paths, not only success paths.

Examples:
- invalid/stale market data;
- malformed events;
- duplicated order intent;
- exceeded risk limit;
- expired signal;
- provider outage;
- auth/permission denial;
- secret missing/rotated;
- crash between order send and acknowledgement;
- restore from backup;
- broker-reported state differs from local state;
- notification channel unavailable;
- model drift or calibration degradation.

## 6. Determinism and reproducibility

For research/quant decisions, record:
- code SHA;
- environment/runtime versions;
- dataset IDs/hashes;
- feature versions;
- strategy/model IDs;
- random seeds;
- cost/slippage assumptions;
- evaluation windows and split definitions.

For operational decisions, record:
- policy/config versions;
- source event IDs;
- system state;
- risk/firewall verdict;
- order/position correlation IDs.

## 7. Performance evidence rules

Performance targets must be defined by the relevant architecture/task from measured requirements. Do not invent universal latency numbers solely to create a target.

When reporting performance include:
- hardware/environment;
- concurrency/instrument count/event rate;
- dataset size;
- warm/cold state;
- percentiles, not only averages;
- error/drop/retry counts;
- CPU/memory/network where relevant;
- test duration.

## 8. Security evidence rules

A security finding is not closed because a code change exists. Closure requires:
- finding identifier;
- affected versions;
- remediation commit;
- regression test or scan;
- re-test result;
- residual risk;
- reviewer/auditor evidence for high/critical cases.

## 9. Gate dossier linkage

Each G0–G13 dossier references the tests/evidence required by `GATE-MATRIX.md`. Missing mandatory evidence produces BLOCKED/FAIL, not an assumed PASS.

## 10. Retention

Evidence retention policy is finalized in P03/P06/P22, but material governance, model/strategy, risk, execution and incident evidence must be retained long enough to reconstruct significant decisions and satisfy legal/operational requirements.
