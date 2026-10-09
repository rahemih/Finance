# Finance — NEXUS QUANT

Private, governance-first market intelligence and controlled trading platform for **Crypto + Forex**.

> Status: P06 — Historical Data & Feature Store CANONICAL_COMPLETE / P07 — Data Quality & Provenance ACTIVE / P07-A CANONICAL_COMPLETE / P07-B CANONICAL_COMPLETE / P07-C CANONICAL_COMPLETE / P07-D CANONICAL_COMPLETE / P07-E CANONICAL_COMPLETE / P07-F CANONICAL_COMPLETE / P07-G IN_PROGRESS
> Canonical branch: `main`  
> Live trading: **DISABLED**  
> Auto trading: **DISABLED**

## Project principles

Accuracy → Safety → Reliability → Quality → Speed → Simplicity → Automation.

The project is built around trusted market data, explainable analysis, independent risk controls, continuous demo learning, reproducible evidence, and controlled progression from research to live execution.

## Canonical sources

- Technical truth: GitHub `main` + CI + merged PR evidence
- Roadmap: `docs/01-roadmap/MASTER-ROADMAP-v2.0.md`
- Current state: `docs/02-current-state/CURRENT-STATE.md`
- Task catalog: `docs/13-tasks/TASK-CATALOG.md`
- Agent registry: `docs/09-agents/AGENT-REGISTRY.md`

## Safety

Never commit API keys, broker credentials, exchange secrets, private keys, passwords, production tokens, or live account identifiers.

No live or automatic trading is authorized until the roadmap's explicit production gates are satisfied.

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
