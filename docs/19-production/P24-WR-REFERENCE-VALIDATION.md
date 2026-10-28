# P24-WR — FIBO/cTrader & Tabdeal Synthetic Reference Validation

Task: `FIN-P24-WR-001`  
Workstream: **P24-WR, supplementary OFFLINE research validation only**  
State: **IN_PROGRESS on governed PR branch; not canonically complete**  
Lock: `LOCK-FIN-P24-WR-001-01` / **ACQUIRED for bounded non-live work**  
Linked tracking: https://github.com/rahemih/Finance/issues/491

## Authority and admission
Owner selected reference venues for technical research only. Forex FIBO Group cTrader DEMO remains a *reference* (no permitted Demo account access granted or used); Tabdeal Spot is a *mock API-contract reference*. P24-B Manual Live is **BLOCKED**. No production broker/exchange/provider is selected.

The scoped Task Contract is `contracts/tasks/FIN-P24-WR-001.json`; P24-A remains closed, P20 adapter/OMS core remains unchanged and cannot be weakened.

## Implementation boundary
- Immutable `config/production/offline-venue-reference-policy.json` restricts to exactly two reference venue IDs, `SIMULATED` only, credential `NONE`, network `DISABLED`, external submission false, Live/Auto disabled and no G13.
- `packages/production/offline_venue_contract.py` validates synthetic intent geometry and denies any foreign venue, LIVE environment, missing/stale sequence, duplicate intent, partial fill without known native ID, invalid cancel, A5 veto, leverage, secret/network exposure or external execution authority.
- **No real venue SDK, network I/O, local trading terminal, tokens, live API URLs, real-order submission or broker accounts**.
- `tests/p24/test_offline_venue_contract.py`: 22 named tests, covering independent negative safety cases and deterministic synthetic outputs.
- `scripts/ci/p24wr_evidence.py`: two byte-identical deterministic evidence replays (required before completion).
- Reuses existing P20 contract, idempotency/OMS/reconciliation tests as upstream; adds no routing authority.

## Ready/Done
Fresh guard: `main e1e7ac817ec3d0d9d055ef947f6c5189bf4d7aac`, open PRs 0, active task/lock none **before acquiring WR lock**, P24-A CANONICAL_COMPLETE and all P24-B gates blocked.

Completion requires **green required Governance**, strict Pyright, all P20/P24 regression suites, exactly reproducible offline evidence, A5/A8/A10 independent review, merged PR, post-merge CI and lock release. PR creation alone is **NOT PASS**.

## Explicit stop boundaries
- `PRE_FIRST_LIVE` unresolved: 9/9; first-Live Owner approval NOT_GRANTED; P24_EXIT 0/3; G13 NOT_STARTED.
- P24-B remains `BLOCKED_HUMAN_AND_PRODUCTION_PREREQUISITES`.
- `LIVE_TRADING` / `AUTO_TRADING` remain `DISABLED`.
- If real access becomes necessary, stop at the existing required Human/Production prerequisites; never infer Demo consent from research selection.

## Evidence/reconciliation
GitHub CI/run IDs, stable SHA, PR and Linear tracking must be added **after** verification. This document is a pre-merge task status, not a historical closure claim.

## Additional pre-merge policy-lineage hardening — 2026-10-28

After the first full green Governance pass, static review found that the public `OfflineVenueReference` dataclass constructor could be called with an arbitrary policy digest. Although the module had no external authority, this permitted a misleading offline verdict lineage. The `evaluate` boundary now also checks the exact hash of `EXPECTED_POLICY` independently of constructor provenance. An eighteenth negative regression test covers forged policy identity for both reference venues. No credential/network/live capability was introduced; rerun strict CI after this repair before claiming final validation.

## Policy JSON value-type integrity hardening — 2026-10-28

Final source audit also identified Python equality treating integer `0` as equal to Boolean `false`. Policy comparisons now use canonical JSON bytes so numeric/Boolean substitution cannot pass policy admission; a nineteenth negative regression test proves rejection. This only strengthens synthetic reference integrity. The previous Governance SUCCESS remains historical; required CI must pass again at the final code head before closure.

## Evidence lineage and adversarial input audit — 2026-10-28

A further review found that the first synthetic decision digest omitted some already validated intent fields (such as prior sequence, tick/step filters and zero-authority flags). The digest now binds the entire validated synthetic dataclass to the immutable policy ID. Runtime checks explicitly reject malformed text, non-Boolean Boolean fields, and non-string reconciliation IDs before canonicalization. Three additional tests (20–22) prove decision-ID differentiation and fail-closed rejection of adversarial dynamically typed inputs. These improvements apply **only** to offline evidence: no real venue, API, account, order, or permissions are introduced. The previous deterministic evidence ID is superseded; record the replacement only after the final-head Governance run succeeds.
