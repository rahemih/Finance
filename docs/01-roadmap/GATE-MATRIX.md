# Finance / NEXUS QUANT — Gate Matrix

STATE = GOVERNED_COMPANION  
TASK = `FIN-P00-WE-001`

## 1. Gate semantics

A gate is an evidence-backed decision boundary. Passing a gate means the required conditions are proven at that point in time; it does not permanently waive future regression checks.

A gate result is one of:
- `PASS`
- `FAIL`
- `BLOCKED`
- `HUMAN_GATE`
- `EXPIRED/REVALIDATE`

Required evidence must be linked to canonical commits, CI/runtime evidence, datasets, reports or signed/attributed approvals as appropriate.

## 2. Canonical gate table

| Gate | Purpose | Minimum pass criteria | Required evidence | Decision authority |
|---|---|---|---|---|
| G0_GOVERNANCE_READY | prove project control plane | Charter/Governance/Task/Evidence/Lock/Agent/Toolchain/Roadmap package canonical; protected main active; Linear synced; no conflicting locks | merged PRs, required checks, Current State, Task Catalog, ruleset/branch evidence | A0 coordinates; A10 verifies |
| G1_PROVIDER_BASELINE | prove viable provider/legal baseline | universe defined; data/broker candidates documented; regional/legal/data-right constraints known; primary+backup path plausible; cost envelope documented | provider scorecards, official docs, compliance matrix, cost/fallback report | A1/A2/A8/A10 |
| G2_ARCHITECTURE_FREEZE | freeze implementable architecture | domain boundaries, interfaces, data/risk/execution/agent topology, environments and capacity assumptions reviewed; no unresolved critical architecture risk | ADRs, diagrams, interface contracts, capacity/risk review | A1 leads; A5/A8/A9 review; A10 verifies |
| G3_SECURITY_BASELINE | establish safe identity/security | threat model, MFA/RBAC, secrets architecture, admin exposure, audit controls, incident process and supply-chain baseline ready | threat model, access matrix, security tests, secret-leak/revocation evidence | A8 independent authority; A10 evidence |
| G4_REALTIME_DATA | prove stable real-time ingestion | canonical events, symbol/time semantics, heartbeat, gap detection, reconnect/failover and latency/soak targets pass for baseline providers | contract tests, latency distribution, soak logs, failover drill, gap-recovery evidence | A2/A9; A10 verifies |
| G5_TRUSTED_DATA | prove data can be trusted downstream | raw/history versioned; missing/duplicate/outlier/stale/cross-provider checks; provenance/confidence and quarantine/fail-close operational | data-quality reports, replayable sample, provenance traces, SLO evidence | A2 lead; A5 consumes safety status; A10 verifies |
| G6_TECHNICAL_VALIDATED | prove technical families are valid and independent enough | evidence families benchmarked; correlation/independence audit; multi-timeframe/regime behavior measured; no double-counting of correlated indicators | benchmark notebooks/reports, test datasets, independence analysis, regression tests | A3/A4; A10 verifies |
| G7_SIGNAL_VALIDATED | prove fused signals/probabilities are calibrated and explainable | common evidence contract; LONG/SHORT/WAIT/NO_TRADE; empirical calibration; sample/uncertainty; Red-Team; reproducible Persian explanation | calibration plots/tables, holdout results, reason traces, Red-Team evidence | A3/A4; A5 reviews; A10 verifies |
| G8_PRETRADE_SAFE | prove deterministic final safety firewall | freshness, drift, duplicate, size/leverage/exposure, liquidity, event/data/broker/system health and daily-loss checks fail closed | firewall contract tests, rejection scenarios, outage simulations, override-policy audit | A5 independent authority; A10 verifies |
| G9_QUANT_VALIDATED | prove strategy edge under realistic conditions | fees/spread/slippage/funding/latency/partial fill; anti-leakage; OOS/WF; Monte Carlo/stress; capacity; registry/versioning | backtest dossier, OOS/WF results, stress/MC, leakage tests, strategy/model registry entries | A4 lead; A5 risk review; A10 verifies |
| G10_SHADOW_VALIDATED | prove shadow/replay/digital twin behavior | deterministic replay; shadow decision stability; simulated-vs-observed execution drift measured; incidents replayable | replay hashes, decision traces, digital-twin reports, drift metrics | A4/A6/A7/A9; A10 verifies |
| G11_EXECUTION_VALIDATED | prove OMS/execution correctness | adapter certification in non-live/safe environment; exactly-once intent semantics; idempotency; retries/timeouts/crash recovery; reconciliation; execution-quality telemetry | broker/exchange sim reports, recovery tests, reconciliation proofs, latency/slippage reports | A6 lead; A5 veto; A8/A9 review; A10 verifies |
| G12_OPERATIONS_VALIDATED | prove operational survivability | metrics/logs/traces, system-state transitions, constrained self-heal, backups, restore drills, DR, incidents, SLO/capacity | dashboards, restore evidence, DR drills, chaos/recovery, runbooks/postmortems | A9 lead; A5/A8 review; A10 verifies |
| G13_OWNER_LIVE_APPROVAL | authorize controlled real-capital production | all prerequisite gates current; readiness dossier; kill-switch drills; low-risk staged rollout plan; credentials/security/risk verified; explicit Owner approval | readiness dossier, fresh gate summary, risk budget, execution/ops evidence, Owner approval record | **Owner Human Gate required** |

## 3. Gate freshness and regression

A gate can require revalidation when:
- provider, broker/exchange or critical dependency changes;
- architecture or major contract changes;
- risk limits materially change;
- model/strategy version changes beyond approved promotion policy;
- security credential or permission posture changes;
- observed drift exceeds thresholds;
- incident/postmortem invalidates prior assumptions;
- environment changes from Demo/Shadow/Canary/Live.

A0 tracks freshness; A10 records evidence; the domain authority decides technical pass/fail.

## 4. Gate anti-bypass rules

- A0 can coordinate but cannot force a PASS.
- A10 can verify evidence but cannot implement and self-approve a critical change.
- A5 Risk may veto trade progression even when upstream signal gates pass.
- A8 Security may block unsafe credential/access/runtime progression.
- CI success alone is insufficient for empirical Quant, Shadow, Execution or Operations gates.
- A plugin/tool result is supporting evidence, not a gate decision by itself.
- No stale or missing required evidence may be silently treated as PASS.
- G13 cannot be automated.

## 5. Gate evidence package standard

A gate dossier should contain, as applicable:
- gate ID and evaluated timestamp;
- canonical Git SHA / release / environment;
- upstream gate references;
- task IDs and merged PRs;
- dataset/version hashes;
- model/strategy/policy/config versions;
- required test summaries and raw artifact locations;
- known limitations and residual risks;
- blockers/waivers/expiry conditions;
- responsible domain sign-off;
- Owner approval when required.

## 6. Current gate state

At this roadmap task:
- G0 = `NOT_YET_EVALUATED` pending P00-E canonical closure and P00-F audit.
- G1–G13 = `NOT_STARTED`.
- LIVE_TRADING = `DISABLED`.
- AUTO_TRADING = `DISABLED`.
