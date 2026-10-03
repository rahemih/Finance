# Finance / NEXUS QUANT — Agent / Plugin / Skill Matrix

STATE = GOVERNED_COMPANION  
TASK = `FIN-P00-WE-001`  
AUTHORITY_SOURCE = `docs/09-agents/AGENT-REGISTRY.md`  
TOOLCHAIN_SOURCE = `docs/09-agents/TOOLCHAIN-MATRIX.md`

## 1. Governing rule

This matrix maps useful tools to agents. It does **not** expand agent authority.

Effective authority is always the intersection of:

`Task Contract ∩ Agent Registry ∩ Toolchain Matrix ∩ Environment Policy ∩ Risk/Security/Owner Gates`.

A plugin may be installed and useful but still be unavailable to a specific task because the task's write scope or risk boundary does not permit its use.

## 2. Core agent routing

| Agent | Primary responsibilities | Preferred plugins/connectors | High-value skills | Explicit boundaries |
|---|---|---|---|---|
| A0 Governance / Orchestrator | Fresh Live Guard, dependency/lock checks, routing, phase coordination, GitHub↔Linear reconciliation | GitHub, Linear, Google Drive, Slack, Plugin Management | plugin-management, roadmap/evidence document workflows | cannot bypass gates, Risk, Security or Owner approval |
| A1 Architecture | ADRs, interfaces, system/data/network architecture, capacity/cost tradeoffs | GitHub, Context7, Exa, Figma, Vercel, Neon, Supabase | Figma diagrams, Vercel architecture skills, Neon/Supabase skills | cannot enable Live or execute trades |
| A2 Data | market feeds, storage, schemas, data quality, provenance, historical/raw pipelines | GitHub, Context7, Blockscout, Exa, Neon, Supabase | Neon Postgres, Supabase Postgres best practices, workflow/queue/storage skills | cannot submit trade orders |
| A3 Market Intelligence | technical, macro, order-flow, news, memory and narrative evidence | Exa, Blockscout, Wolfram, Legal Data Hunter, TinyFish when interaction is required | research/browser skills when task-scoped | intelligence only; no execution authority |
| A4 Quant | models, probability, calibration, backtests, strategies, statistical validation | GitHub, Wolfram, Context7, Exa, PostHog where experiment telemetry is appropriate | Python/quant tooling selected later; exact-statistics cross-checks | cannot self-promote model/strategy to Live |
| A5 Risk | risk budgets, sizing, portfolio constraints, pre-trade veto, defensive modes | GitHub, Wolfram, Exa, Legal Data Hunter | quantitative validation and evidence tools | cannot modify own ceilings; cannot send broker orders |
| A6 Execution | adapter contracts, OMS, idempotency, reconciliation, execution-quality measurement | GitHub, Context7, selected infra plugins only after architecture | workflow/queue/observability skills selected by P02/P20 | cannot override Risk or Firewall |
| A7 Learning | demo journal, datasets, experiments, retraining, champion/challenger, drift | GitHub, Wolfram, PostHog if selected, Drive for evidence exports | workflow/experiment/analytics skills | no automatic promotion to Live |
| A8 Security | threat model, access, secrets, supply-chain security, vulnerability review | GitHub, Codex Security, Context7, Vercel Firewall if relevant, Legal Data Hunter for regulatory context | security/investigation/firewall skills | no trading decision authority |
| A9 Operations | telemetry, deployment, backup/restore, diagnostics, incidents, recovery | GitHub, Vercel, Neon, Supabase, PostHog, Sentry if configured, Slack | observability, verification, investigation, workflow, storage, DB ops | cannot relax risk policy |
| A10 Evidence & Audit | evidence completeness, closure verification, source/provenance checks, state reconciliation | GitHub, Linear, Google Drive, Exa, Legal Data Hunter | Docs/Sheets evidence workflows, plugin-management | cannot implement and self-approve critical changes |

## 3. Specialist agent routing

Specialists are spawned only by an authorized Task Contract and inherit the parent phase constraints.

| Specialist | Typical phase | Useful tools | Boundary |
|---|---|---|---|
| Crypto Data Specialist | P01/P05/P09/P10 | Blockscout, Exa, GitHub, Context7 | no wallet identity claims without independent evidence |
| Forex Data Specialist | P01/P05/P09 | Exa, official/broker docs, GitHub | must label volume proxies and coverage |
| Macro Specialist | P10 | Exa, official sources, Wolfram | official-first sourcing |
| News/Sentiment Specialist | P11 | Exa, TinyFish only if needed, Legal Data Hunter for regulatory stories | rumor cannot independently trigger trade |
| Trend Specialist | P08 | GitHub, Wolfram | evidence-family output only |
| Momentum Specialist | P08 | GitHub, Wolfram | correlated variants cannot count as separate votes |
| Market Structure Specialist | P08 | GitHub, Wolfram | same evidence-contract rules |
| Order Flow Specialist | P09 | Blockscout where on-chain-relevant, GitHub, Wolfram | venue/proxy coverage must be explicit |
| Backtest Specialist | P17 | GitHub, Wolfram, Context7 | anti-leakage and reproducibility mandatory |
| Red-Team Specialist | P14/P17/P24 | GitHub, Exa, Wolfram, Legal Data Hunter | searches for reasons not to trade; no execution |
| Security Specialist | P03/P04/P20/P22 | Codex Security, GitHub, Context7 | cannot waive own findings without evidence |
| UX Specialist | P23 | Figma, Canva/Gamma for communication only, GitHub | dangerous actions require explicit UX safeguards |
| Performance Specialist | P05/P17/P20/P22 | GitHub, Vercel/observability tools if selected | cannot change correctness/risk semantics for speed |
| Documentation Specialist | cross-cutting | GitHub, Drive, Notion, Gamma | GitHub canonical docs win over mirrors |
| Cost Specialist | P01/P02/P22 | Exa, provider docs, Sheets/Drive | cost optimization cannot weaken safety controls |

## 4. Plugin classes and routing

### Core governance / engineering

- **GitHub:** canonical technical/governance evidence; A0/A1/A2/A4/A5/A6/A7/A8/A9/A10 as task scope permits.
- **Linear:** planning and execution state; primarily A0/A10; domain agents may update assigned issues only when task-scoped.
- **Figma:** architecture diagrams and P23 product design; A1 and UX specialist primarily.
- **Google Drive:** evidence packs, controlled exports and collaborative docs; A0/A10 primarily.
- **Slack:** coordination/notifications where explicitly useful; no canonical decisions only in Slack.
- **Context7:** up-to-date library/API documentation; read-only engineering research.

### Data / infrastructure candidates

- **Vercel, Neon, Supabase, PostHog:** architecture candidates and operational tools only after task-level selection.
- Installation does not authorize environment creation, production mutation or secret changes.
- A1/A2/A9 may use read/evaluation capabilities before selection; writes require explicit Task Contract scope.

### Market / research / quant

- **Blockscout:** EVM on-chain intelligence.
- **Exa:** web/research/news/paper discovery.
- **Wolfram:** exact/statistical/symbolic computation and cross-checking.
- **Legal Data Hunter:** legal/regulatory research.
- **TinyFish:** browser interaction only when static retrieval cannot satisfy the task.

These tools support evidence; none is a trading authority.

### Collaboration / artifact tools

- **Notion, Gmail, Google Calendar, Dropbox, Adobe, Canva, Gamma:** useful for project support, reporting and collaboration.
- Canonical engineering/governance truth remains GitHub.
- External sends, sharing or publication must be task-authorized.

### Conditional media / public-surface tools

- **Semrush:** future SEO/public-surface research only.
- **Runway / Higgsfield:** optional demos/media/prototypes.
- They have no role in trading logic or risk decisions.

## 5. Skill-to-phase mapping

| Skill family | Primary phases | Use |
|---|---|---|
| Figma Generate Diagram | P02, P12, P20, P22 | architecture/data/execution/recovery diagrams |
| Figma Generate Design / Library / Design-to-Code | P23 | RTL UI, design system, implementation handoff |
| Vercel AI SDK / AI Gateway | P02, P04, P14, P23 | controlled LLM/app interfaces if selected |
| Vercel Workflow / Queues / Functions / Cron | P04, P18, P22 | durable/scheduled processing if selected |
| Vercel Observability / Verification / Investigation | P22/P23 | runtime verification and incident triage |
| Vercel Firewall / Sandbox | P03/P22 | security and isolated execution if selected |
| Neon Postgres / Functions / Object Storage | P02/P04/P06/P22 | DB/backend/storage evaluation and implementation if selected |
| Supabase / Postgres Best Practices | P02/P04/P06/P22 | DB/Auth/Realtime/Storage/RLS evaluation if selected |
| Google Docs/Sheets/Slides/Drive | P00/P01/P02/P17/P22 | evidence, comparisons, reports and controlled exports |
| Sentry | P22 | read-only error inspection when token/configuration exists |
| Plugin Management | P00 and whenever capability changes | installation-state, permissions and dependency governance |

## 6. Write-action policy

A tool write is allowed only when all are true:
1. an active Task Contract exists;
2. the target system/path is within declared write scope;
3. no conflicting lock exists;
4. the action is reversible or has an approved rollback path where required;
5. it does not cross a Human Gate;
6. it preserves evidence and attribution.

Examples:
- A0 may create/update Linear issues for the active roadmap task.
- A1 may create an architecture diagram in Figma under a P02 task.
- A9 may change a non-production deployment only when the task explicitly grants that environment scope.
- A6 may not create a live broker order merely because a broker connector becomes available.

## 7. Permission posture

Default posture:
- research/read tools: read without unnecessary interruption when task-relevant;
- write tools: governed and scoped;
- high-impact actions: explicit gate/human approval;
- blanket Full Access: not a project requirement and not silently enabled.

## 8. Separation of duties

Minimum separation principles:
- A4 develops/evaluates models; A5 independently constrains risk.
- A6 executes only approved intent; A5/P16 can veto.
- A8 can block security progression.
- A10 validates evidence/closure and does not self-approve critical implementation.
- A0 routes and reconciles but does not manufacture technical PASS results.
- G13 remains Owner-only.

## 9. Audit requirement

Every high-impact tool action should be attributable to:
- task ID;
- agent/role;
- environment;
- tool/plugin;
- target resource;
- timestamp;
- before/after or request/result evidence;
- gate/approval reference where required.
