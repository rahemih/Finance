# Finance / NEXUS QUANT — Open-Source Repository & Dependency Registry

STATE = GOVERNED_RESEARCH_REGISTRY  
TASK = `FIN-P01-WR-001`  
LINEAR = `HOS-110`  
WAVE = 1  
EFFECTIVE_DATE = 2026-10-03  
PRODUCTION_SELECTIONS = NOT_AUTHORIZED

## 1. Purpose

This registry records reputable open-source finance, quantitative-research, backtesting, trading and market-data repositories that may inform or support NEXUS QUANT.

A registry entry is **not** production approval. Any direct production dependency still requires the responsible roadmap phase, dependency/license review, security review, reproducibility checks and an ADR or equivalent governed decision.

## 2. Classification

- **ADOPT_CANDIDATE** — strong candidate for direct integration after phase-specific validation.
- **USE_CANDIDATE** — potentially useful as a bounded dependency/tool, but not yet preferred.
- **REFERENCE** — architecture, algorithm, testing or workflow reference; no direct dependency implied.
- **LICENSE_RISK** — useful project with licensing terms requiring explicit review before integration.
- **REJECT** — unsuitable for the intended production role at the time of review.

## 3. Wave-1 registry

| Repository | Primary role | Upstream status on 2026-10-03 | License signal | Classification | NEXUS QUANT intended use | Key guardrail |
|---|---|---|---|---|---|---|
| `microsoft/qlib` | Quant research / ML / alpha / portfolio / backtest | Active; ~49k stars; recent push 2026-09-22 | MIT | ADOPT_CANDIDATE | Research and ML architecture benchmark; candidate bounded research dependency | Must pass P04 dependency governance and P17 benchmark/reproducibility review |
| `QuantConnect/Lean` | Algorithmic backtest / execution engine | Active; ~21k stars; push 2026-10-02 | Apache-2.0 | REFERENCE | Benchmark backtest/execution lifecycle, order model and research/live parity | Do not make it core engine without P02/P17 architecture decision |
| `nautechsystems/nautilus_trader` | Event-driven trading / OMS / execution | Highly active; ~29k stars; push 2026-10-03 | LGPL-3.0 | USE_CANDIDATE | Event-driven architecture, deterministic execution, OMS/execution reference; possible bounded adapter | LGPL integration/distribution obligations require P04-F license review |
| `AI4Finance-Foundation/FinRL` | Reinforcement-learning finance research | Active; ~16k stars; push 2026-09-28 | MIT | USE_CANDIDATE | Experimental RL lab/challenger models | RL cannot bypass P17/P18 validation or automatic-live-promotion prohibition |
| `ccxt/ccxt` | Unified crypto exchange API | Highly active; ~44k stars; push 2026-10-02 | MIT | ADOPT_CANDIDATE | Crypto exchange adapter abstraction candidate | Exchange-native behavior remains authoritative; P01-C/P05 must validate venue-specific semantics |
| `freqtrade/freqtrade` | Crypto bot / strategy / backtest | Highly active; ~55k stars; push 2026-10-02 | GPL-3.0 | LICENSE_RISK | Reference for bot lifecycle, strategy testing, protections and operational patterns | No code embedding or derivative integration without explicit GPL compatibility/legal review |
| `polakowo/vectorbt` | Vectorized research / parameter sweeps | Active; ~9k stars; push 2026-09-26 | GitHub metadata: NOASSERTION | LICENSE_RISK | Exploratory research and benchmark candidate | Treat as reference-only until exact current license/commercial terms are reviewed and approved |
| `ranaroussi/yfinance` | Yahoo Finance research-data client | Active; ~25k stars; push 2026-09-30 | Apache-2.0 | USE_CANDIDATE | Research/prototyping and non-authoritative contextual experiments | Not a production market-data backbone; upstream data rights/terms must be separately validated |
| `stefan-jansen/machine-learning-for-trading` | ML-for-trading educational/reference code | Active; ~21k stars; push 2026-10-03 | MIT | REFERENCE | Feature engineering, validation, backtest and ML workflow reference | Educational/reference material; do not treat as production framework |
| `OpenBB-finance/OpenBB` | Financial data integration / research platform | Organization announced OpenBB wind-down; assets moving to OpenBQ stewardship | Repository/license requires per-component review | REFERENCE | Study provider abstraction, data integration and agent-facing research interfaces | Do not adopt as core dependency while stewardship transition is unresolved |

## 4. Preferred Wave-1 shortlist by subsystem

### Market-data / venue adapters
1. **CCXT — ADOPT_CANDIDATE** for crypto adapter abstraction.
2. **yfinance — USE_CANDIDATE / RESEARCH ONLY** for prototyping and contextual experiments.
3. **OpenBB — REFERENCE** for provider abstraction patterns, not core adoption during stewardship transition.

### Quant research / ML
1. **Microsoft Qlib — ADOPT_CANDIDATE**.
2. **FinRL — USE_CANDIDATE** for sandboxed RL experiments.
3. **Machine Learning for Trading — REFERENCE**.

### Backtesting / simulation
1. **LEAN — REFERENCE** for event lifecycle and execution realism.
2. **Qlib — ADOPT_CANDIDATE** for research workflows.
3. **VectorBT — LICENSE_RISK** until licensing is resolved.

### Execution / OMS
1. **NautilusTrader — USE_CANDIDATE** after LGPL review.
2. **LEAN — REFERENCE**.
3. **Freqtrade — REFERENCE / LICENSE_RISK** due GPL-3.0.

## 5. Production-adoption gate

Before any registry item changes from candidate/reference to an approved production dependency, record:

- exact version/tag/commit pin;
- SPDX/license file and legal compatibility;
- transitive dependency/SBOM review;
- security/CVE and maintainer-bus-factor assessment;
- reproducible install/build;
- test coverage against NEXUS QUANT contracts;
- data/API rights where applicable;
- failure/exit plan;
- portability/replacement path;
- phase-specific benchmark evidence;
- ADR / governed approval.

## 6. Explicit non-decisions

This task does **not**:
- select a production market-data provider;
- select a broker/exchange;
- approve any repository for LIVE execution;
- install any dependency;
- close P01-B;
- change the frozen Master Roadmap;
- enable Demo, Shadow, Live or Auto Trading.

## 7. Next research actions

- P01-B remains the next canonical workstream for Market Data Provider Scorecards.
- P01-C will evaluate broker/exchange candidates and venue-native API behavior.
- P02/P04 will decide architecture and dependency governance.
- P17 will benchmark backtest/research engines against deterministic NEXUS QUANT requirements.
- P20 will revisit execution-engine candidates only after risk and architecture gates pass.
