# P23-C — Operational Screens

Task: `FIN-P23-WC-001`  
State: IN_PROGRESS  
Lock: `LOCK-FIN-P23-WC-001-01` / ACQUIRED

## Purpose

P23-C defines the deterministic operational-screen contract for every canonical application surface established by P23-A and consumes the product-owned P23-B design system. It does not create execution, remediation, credential, production or Live authority.

## Canonical screen coverage

1. Dashboard — `/dashboard` — monitoring shell — critical
2. Markets — `/markets` — monitoring shell — critical
3. Opportunities — `/opportunities` — analysis shell — critical
4. Trades — `/trades` — monitoring shell — critical
5. Portfolio — `/portfolio` — analysis shell — critical
6. Demo — `/demo` — monitoring shell — critical
7. Research — `/research` — analysis shell
8. Reports — `/reports` — analysis shell
9. System — `/system` — monitoring shell — critical
10. Settings — `/settings` — default shell — critical
11. Glossary — `/glossary` — default shell

Routes, Persian labels and criticality must remain byte-for-byte aligned to the P23-A information-architecture contract.

## Critical states

Every critical screen must preserve the canonical fail-visible set:

`LOADING / EMPTY / ERROR / OFFLINE / STALE / DEGRADED`

These states cannot be hidden by optimistic UI.

## Provenance

Sensitive analytics must display source and timestamp. Realtime surfaces must display freshness. Critical surfaces must display system state. These requirements are inherited from P23-A and may not be weakened.

## Directionality

- application shell and Persian narrative: RTL;
- ticker, price, percentage, IDs, hashes, ISO timestamps and versions: isolated LTR financial islands;
- canonical P23-B terminology remains authoritative.

## Authority boundary

P23-C screen authority is `READ_ONLY_NAVIGATION`.

Reserved downstream ownership:
- Learning Mode: P23-D;
- Team collaboration: P23-E;
- Notification delivery: P23-F;
- Accessibility/responsive/performance hardening: P23-G;
- Dangerous-action/security UX: P23-H.

P23-C may display status or navigation references to these concepts but may not implement their behavior.

## Figma canonical specimen

- file: `5aVGC189GMrRDokrjBbI5P`;
- page: `10:2` — P23-C — Operational Screens;
- board: `10:3` — NEXUS QUANT — P23-C Operational Screens;
- URL: https://www.figma.com/design/5aVGC189GMrRDokrjBbI5P?node-id=10-3;
- editable write succeeded using P23-B local semantic variables;
- generated screenshot: 1600×1480;
- fonts used: Noto Sans Arabic + Noto Sans;
- screen registry rows: 11;
- an extra structural read-back hit the Figma Starter-plan MCP call limit after successful creation/screenshot. This is recorded as an external tooling limitation, not a contract bypass.

## Safety

- external-order authority: false;
- runtime-state mutation: false;
- remediation authority: false;
- credential access: false;
- production activation: false;
- P24: NOT_STARTED;
- LIVE_TRADING: DISABLED;
- AUTO_TRADING: DISABLED.
