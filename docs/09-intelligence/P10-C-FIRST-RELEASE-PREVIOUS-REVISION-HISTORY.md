# P10-C — First Release / Previous-at-Time / Revision History

Task: `FIN-P10-WC-001`  
Linear: `HOS-235`  
State: IMPLEMENTATION_ACTIVE  
Lock: `LOCK-FIN-P10-WC-001-01` / ACQUIRED

## Objective

Make macro releases replay-safe by distinguishing what was first published, what the system knew as the previous value at that time, and what revisions arrived later.

## Composition

P10-C does not replace P06-E. It composes:

- P10-A canonical source identity;
- P10-B `RELEASED` event metadata;
- P06-E `MacroVintage` and `MacroVintageStore`.

The current event's revision zero is the **first release**.

## Previous-at-time

The previous value used for historical context is not today's latest revised previous period.

For current first release `R0`, P10-C anchors previous-at-time to:

`decision_time = R0.observed_at_ns`

It then resolves the greatest prior observation using the P06-E rule:

`release_time <= decision_time AND observed_at <= decision_time`

Therefore a revision of the prior period arriving after the current release cannot leak backward.

## Revision history

Two views are explicit:

- `revision_history_as_of(decision_time)` — replay-safe;
- `audit_full_revision_history()` — audit/latest context only and explicitly not for replay.

Current-value lookup also uses `resolve_current_as_of()`.

## Event linkage

P10-C requires:

- P10-B event status = `RELEASED`;
- event source exists in P10-A registry;
- all macro vintages use that same source ID;
- current revision-zero release timestamp equals P10-B actual release timestamp;
- one macro series per history object;
- P06-E zero-based contiguous revision invariants.

## Non-scope

Forecast/consensus and surprise are excluded. P10-D owns macro surprise.

## Safety

Production revision provider: NOT_SELECTED.  
Network required: false.  
Credentials required: false.  
Country assumption: NONE.  
LIVE_TRADING: DISABLED.  
AUTO_TRADING: DISABLED.
