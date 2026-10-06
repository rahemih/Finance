# P06-G — Replay Snapshot Interfaces

Task: `FIN-P06-WG-001`  
Linear: `HOS-201`  
State: IN_PROGRESS  
Lead: A2 Data  
Supporting: A0 Governance, A1 Architecture, A4 Quant, A7 Learning/Replay, A8 Security, A9 Operations, A10 Evidence/Audit

## Objective

Freeze exact reproducible replay inputs into a content-addressed snapshot while preserving point-in-time visibility rules required for historical simulation.

## Snapshot identity

The snapshot ID is SHA-256 over a canonical body that pins:

- replay start/end and frozen information cutoff;
- clock mode;
- canonical instrument/series scope;
- exact P06-D dataset versions, membership roots and windows;
- exact P06-F feature definition/materialization IDs and quality evidence hashes;
- exact P06-E macro vintage IDs plus release/observed times;
- quality-rule versions;
- config and code/artifact SHA-256;
- rights class;
- optional stochastic seed + stochastic version;
- anti-lookahead rule.

Input ordering does not affect snapshot identity.

## Clock modes

Only these frozen architecture modes are accepted:

- `EVENT_TIME`
- `RECEIVE_TIME`
- `CONTROLLED_SIMULATION_CLOCK`

## Anti-lookahead interface

A snapshot may contain a frozen historical timeline, but `view_at(decision_time)` exposes only:

- dataset refs whose event window contains the decision time;
- feature refs with `as_of_time <= decision_time`;
- macro vintages with both `release_time <= decision_time` and `observed_at <= decision_time`.

All feature/vintage information must also be no later than the snapshot's frozen cutoff.

This interface does not run the replay engine; it defines the deterministic, verifiable visibility contract that a later replay/backtest engine must consume.

## Stochastic reproducibility

If stochastic behavior is referenced, `stochastic_seed` and `stochastic_version` must be supplied together. A partial stochastic identity fails closed.

## Reference snapshot store

The offline reference store writes:

`replay-snapshots/<snapshot_id>.json`

Identical rewrites are idempotent. Existing differing bytes for the same content ID fail closed. Loads revalidate the exact snapshot identity and canonical serialization.

This filesystem implementation is not a production replay/storage vendor selection.

## Downstream boundary

P06-H owns retention, compaction and storage-cost certification.  
P07 owns actual quality/provenance scoring and quarantine.  
Backtest/replay execution engines are later work and must consume this interface rather than rebuild informal queries.

## Safety

Production replay storage vendor: NOT_SELECTED.  
Network required: false.  
Credentials required: false.  
Country assumption: NONE.  
CANARY: DISABLED.  
LIVE_TRADING: DISABLED.  
AUTO_TRADING: DISABLED.

P06-H remains blocked until P06-G canonical closure.
