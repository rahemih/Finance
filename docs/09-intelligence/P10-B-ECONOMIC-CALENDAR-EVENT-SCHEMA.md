# P10-B — Economic Calendar / Event Schema

Task: `FIN-P10-WB-001`  
Linear: `HOS-234`  
State: IMPLEMENTATION_ACTIVE  
Lock: `LOCK-FIN-P10-WB-001-01` / ACQUIRED

## Objective

Define the point-in-time event shell used by later fundamental intelligence without mixing calendar metadata with release values, revisions or surprise calculations.

## Lifecycle

- `SCHEDULED`: future or upcoming schedule metadata only.
- `RELEASED`: requires an actual release timestamp that cannot be later than the calendar's observed-at timestamp.
- `RESCHEDULED`: records the previous scheduled timestamp and a distinct new scheduled timestamp.
- `CANCELLED`: requires an official/source cancellation reason.

Lifecycle-incompatible fields fail closed.

## Time semantics

The event records an epoch-nanosecond scheduled timestamp plus a declared IANA timezone such as `America/New_York` or `Europe/Berlin`.

The epoch timestamp is the machine comparison key. The timezone preserves publication-calendar interpretation, daylight-saving context and user-facing reconstruction.

A future scheduled time is valid even when it is after `observed_at_ns`: calendars describe future events. By contrast, an actual release time cannot be after `observed_at_ns`.

## Source and provenance

Every event binds to a source ID that must exist in the P10-A canonical official-source registry and carries deterministic dataset-version and quality-evidence SHA-256 values.

## Deliberate separation from P10-C/D

P10-B does not contain:

- actual numeric release value;
- forecast value;
- previous value;
- revision number/history;
- surprise value;
- trade importance score.

P10-C owns first-release / previous-at-time / revision history. P10-D owns surprise.

## Safety

Production calendar provider: NOT_SELECTED.  
Network required by canonical tests: false.  
Country assumption: NONE.  
LIVE_TRADING: DISABLED.  
AUTO_TRADING: DISABLED.
