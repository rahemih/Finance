# P23-A — Information Architecture / User Flows

Task: `FIN-P23-WA-001`  
Phase: P23 — UX / Team / Notifications  
Status: IN_PROGRESS  
Lock: `LOCK-FIN-P23-WA-001-01` / ACQUIRED

## Objective

Define the canonical Persian-first application information architecture and user-flow contract before design-system or operational-screen implementation.

P23-A turns the roadmap's UI surface list into a deterministic, testable navigation contract. It does **not** implement visual components or grant action authority.

## Canonical surfaces

The ordered core surface registry is:

1. Dashboard — `/dashboard`
2. Markets — `/markets`
3. Opportunities — `/opportunities`
4. Trades — `/trades`
5. Portfolio — `/portfolio`
6. Demo — `/demo`
7. Research — `/research`
8. Reports — `/reports`
9. System — `/system`
10. Settings — `/settings`
11. Glossary — `/glossary`

Persian is the primary locale (`fa-IR`), the application shell is RTL, and canonical financial identifiers/numbers remain LTR islands.

## Canonical workflows

P23-A defines navigation-only flows for:

- market monitoring;
- opportunity evaluation;
- trade/portfolio review;
- demo-learning monitoring;
- system-state investigation;
- explanation/glossary learning;
- settings/security-context review.

Every workflow references only canonical surfaces and has `NAVIGATION_ONLY` authority.

## Fail-visible critical states

Critical surfaces must explicitly support:

- LOADING
- EMPTY
- ERROR
- OFFLINE
- STALE
- DEGRADED

No critical surface may silently fall back from realtime/current state to stale data.

## Provenance boundary

Sensitive analytics must expose source and timestamp provenance. Realtime surfaces must expose freshness. Critical surfaces must make system state visible enough that degraded/offline conditions cannot be mistaken for normal operation.

## Authority boundary

P23-A grants no:

- external-order authority;
- broker/exchange action;
- runtime state mutation;
- remediation/self-healing action;
- credential access;
- production activation;
- P24 activation;
- Live/Auto trading.

`LIVE_TRADING` and `AUTO_TRADING` remain disabled.

## Canonical Figma source

P23 UX file: https://www.figma.com/design/5aVGC189GMrRDokrjBbI5P?node-id=1-2

The P23-A canvas contains the 11 canonical surfaces, seven navigation-only workflows, fail-visible critical states, provenance requirements and the P23-A safety boundary. It is the governed UX-intent source that precedes P23-B design-system implementation.

## Dependencies and next step

P22 is CANONICAL_COMPLETE and G12_OPERATIONS_VALIDATED = PASS in REFERENCE_OPERATIONS_VALIDATION scope. Owner P23 authorization is consumed.

P23-A is active. P23-B..P23-I remain NOT_STARTED until P23-A canonical closure.
