# P23-A — Information Architecture / User Flows

Task: `FIN-P23-WA-001`  
Phase: P23 — UX / Team / Notifications  
Status: CANONICAL_COMPLETE  
Lock: `LOCK-FIN-P23-WA-001-01` / RELEASED

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

P23-A is CANONICAL_COMPLETE. P23-B — Design System / RTL / Terminology is READY_NOT_STARTED. P23-C..P23-I remain NOT_STARTED.


## Canonical closure evidence

- implementation PR #471 = MERGED;
- final implementation head = `496268171eeaaf6bb03a2d48a2d834b77456edae`;
- implementation Governance run = `40468620582` / SUCCESS;
- implementation artifact = `12717303404` / `sha256:fc58cd47ebf6a741822644fb80f69c58406bf9586bfbda610127a4c1e71ac031`;
- architecture ID = `b41f86261b7427e3b617489908210a5a9284445d526a238a7fec71deabc02299`;
- deterministic evidence ID = `099afc90d6d517b43165b2dc283cccaf06bf9614c22989f967e05cd0199d76b4`;
- deterministic evidence SHA256 = `1424e802df343ea65b960dc96c12149e9bb5132c831f7bdc8e454232f2845eff`;
- implementation merge SHA = `d0202f7623767db73ddf5c3a59e7c5754c612f89`;
- post-merge Governance = `40468844757` / SUCCESS;
- post-merge artifact = `12717523519` / `sha256:0762f921c92bbc342dab77aeb98e99b549f2d5c5175a122c10f978e8d5e73f5c`;
- post-merge Branch Hygiene = `40468844694` / SUCCESS;
- lock = RELEASED.

Historical CI repair:
- initial Governance run `40468437944` failed closed only because the P23-A fail-closed test helper omitted `typing.cast`;
- repair commit `496268171eeaaf6bb03a2d48a2d834b77456edae` added the missing import;
- no invariant, safety boundary, or test criterion was relaxed.

P23-B = READY_NOT_STARTED.  
P24 = NOT_STARTED.  
LIVE_TRADING / AUTO_TRADING = DISABLED.
