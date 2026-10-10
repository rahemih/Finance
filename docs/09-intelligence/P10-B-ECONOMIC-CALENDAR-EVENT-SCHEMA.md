# P10-B — Economic Calendar / Event Schema

Task: `FIN-P10-WB-001`  
Linear: `HOS-234`  
State: CANONICAL_COMPLETE  
Lock: RELEASED

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


## Canonical closure evidence

- Implementation PR: `#208` = MERGED
- Final implementation head: `1d06a79d82b53defe7a1ba29def6973c6200d158`
- Implementation merge SHA: `e4a68752501e5394c4bc33f9747dcc7b40fef419`
- Final PR Governance: `38058992238` = SUCCESS
- PR artifact: `sha256:f30b9ef5b55c02a24e3621ced981223f29d6d8935189f2d78fe30d0def37f7be`
- Post-merge Governance: `38059073925` = SUCCESS
- Post-merge artifact: `sha256:0761d1b589406182394b87bef8d5b1f33b241c8c410ae1f6a2536d0486c968c7`
- Post-merge Branch Hygiene: `38059073919` = SUCCESS
- R01 canonical IANA timezone repair: PASS

P10-C becomes `READY_NOT_STARTED`.
