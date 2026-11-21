# Finance — NEXUS QUANT

Public source repository for a governance-first market intelligence and controlled trading platform for **Crypto + Forex**. Credentials, private account data and trading authorization are never part of the public repository.

> Project status: consult [`CURRENT-STATE.md`](docs/02-current-state/CURRENT-STATE.md), the frozen [`MASTER-ROADMAP-v2.0.md`](docs/01-roadmap/MASTER-ROADMAP-v2.0.md), and current GitHub CI/PR evidence. `CURRENT-STATE.md` currently identifies its last reconciliation as **2026-11-04**; it is a historical checkpoint, not proof that later PRs, reviews, CI or gates passed. WEB-P0 and P24-B acceptance remain separately gated; see [license review #530](https://github.com/rahemih/Finance/issues/530), [builder evidence #531](https://github.com/rahemih/Finance/issues/531), and [P24-B evidence #528](https://github.com/rahemih/Finance/issues/528).
> Canonical branch: `main`  
> Live trading: **DISABLED**  
> Auto trading: **DISABLED**

## Project principles

Accuracy → Safety → Reliability → Quality → Speed → Simplicity → Automation.

The project is built around trusted market data, explainable analysis, independent risk controls, evidence-gated demo evaluation, reproducible evidence, and controlled progression from research toward any separately authorized production readiness. This description is an architecture goal, not a claim of running agents, validated Demo execution, or Live readiness.

## Canonical sources

- Technical truth: GitHub `main` + CI + merged PR evidence
- Roadmap: `docs/01-roadmap/MASTER-ROADMAP-v2.0.md`
- Cross-cutting research addendum: `docs/01-roadmap/addenda/ALPHA-RESEARCH-FAST-TRACK.md`
- Current state: `docs/02-current-state/CURRENT-STATE.md` (check its reconciliation date)
- Task catalog: `docs/13-tasks/TASK-CATALOG.md`
- Agent registry: `docs/09-agents/AGENT-REGISTRY.md`

## Safety

Never commit API keys, broker credentials, exchange secrets, private keys, passwords, production tokens, or live account identifiers.

No live or automatic trading is authorized until the roadmap's explicit production gates are satisfied.

Demo and simulation evidence is not authorization to place orders. Any Demo order activity requires its own explicit governing approval; documentation, CI success, or a dashboard Start audit cannot grant it. Independent A5/A8/A10 veto, exact-head Owner/Human Gate, and protected-branch checks remain binding.

WEB-P0 dependency and license acceptance is separately **BLOCKED** pending independent review and the `caniuse-lite` disposition tracked in [#530](https://github.com/rahemih/Finance/issues/530). A successful Governance workflow does not replace SBOM/license approval, a formal independent review, or the PR-specific Owner gate. Do not broaden license allow-lists to bypass this blocker.

## Mission Control and engineering execution

Mission Control and GitHub Actions provide observable audit/test evidence, not an on-demand ChatGPT execution endpoint. A public **Start** action does not immediately launch an autonomous engineering run, prove that A0–A10 workers are active, or grant an approval. Engineering progress must be substantiated by actual commits, workflow runs, review identities and GitHub–Linear records. Scheduled ChatGPT work is separate from the dashboard and subject to its own schedule and tool availability.

## Repository

Canonical repository: `rahemih/Finance`


## Workspace

Canonical engineering workspace decision:
- governed polyglot monorepo;
- modular-core-first;
- provider/vendor SDKs isolated under `adapters/`;
- production code never imports `research/`;
- exact runtime/package-manager versions are selected in P04-B.

See `docs/06-engineering/WORKSPACE-STRUCTURE.md`.


### Developer commands

```text
pnpm doctor
pnpm bootstrap
pnpm check:fast
pnpm check:full
pnpm test:foundation
pnpm hooks:install
```

Local commands accelerate feedback; protected GitHub CI remains authoritative.
