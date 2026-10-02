# Governance

## Source of truth

Technical truth: GitHub `main` + merged commits + CI evidence + runtime/deployment state.

Governance truth: Master Roadmap, Project Charter, Task Catalog, Agent Registry, risk/security policies.

Operational truth: CURRENT-STATE, active locks, incidents, deployments, model/strategy registries.

## Core rules

- No governed task executes without a valid Task Contract.
- Fresh Live Guard precedes implementation work.
- Least privilege applies to people, agents, plugins, and runtime services.
- Risk and Pre-Trade Firewall may veto any trade.
- AI/LLM output is never sole authority for a live order.
- Auto-retrain may be allowed; auto-promotion to live is forbidden.
- Frozen roadmap changes use ERRATA, ADR, RFC, or ADDENDUM.
- Canonical completion requires merge + post-merge evidence + state reconciliation.

## Task states

NOT_STARTED, NOT_READY, READY, ACTIVE, PAUSED, BLOCKED, HUMAN_GATE, REPAIR, VALIDATION, PASS, CANONICAL_COMPLETE, DEFERRED, RETIRED.

## Risk classes

LOW, MEDIUM, HIGH, CRITICAL.
