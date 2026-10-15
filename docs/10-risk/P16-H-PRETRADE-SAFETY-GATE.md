# P16-H — Pre-Trade Safety Gate

State: IMPLEMENTATION_ACTIVE  
Task: `FIN-P16-WH-001`  
Frozen-roadmap gate: `G8_PRETRADE_SAFE`

## Objective

Provide the final independent fail-closed barrier for P16.

G8 can pass only when there is exactly one valid certificate for every workstream from P16-A through P16-G.

## Required statuses

- P16-A: `PRETRADE_A_ELIGIBLE`
- P16-B: `PRETRADE_B_ELIGIBLE`
- P16-C: `PRETRADE_C_ELIGIBLE`
- P16-D: `PRETRADE_D_ELIGIBLE`
- P16-E: `PRETRADE_E_ELIGIBLE`
- P16-F: `PRETRADE_F_ELIGIBLE`
- P16-G: `PRETRADE_G_ELIGIBLE`

Any `VETO`, `WAITING_FOR_APPROVAL`, missing workstream, duplicate workstream, duplicate decision ID, lineage break or authority escalation fails closed.

## Lineage

P16-A has no upstream P16 decision.

Each later certificate must point to the immediately preceding P16 decision ID:

A → B → C → D → E → F → G.

## Positive result

The only positive phase-exit result is:

`G8_PRETRADE_SAFE / PASS`

That result means the P16 firewall chain is validated. It is **not** an execution command, broker-routing permission, live-trading activation or P17 authorization.

After PASS:
- P16 may close canonically;
- P17 remains `NOT_STARTED / OWNER_PHASE_AUTHORIZATION_REQUIRED`;
- LIVE_TRADING remains DISABLED;
- AUTO_TRADING remains DISABLED.
