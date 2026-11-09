# P24-C — Semi-Auto S0 readiness preflight (PREPARATION ONLY)

**Task:** `FIN-P24-WV-001`. **Scope:** offline synthetic preparation for future P24-C; **not** canonical P24-C implementation or authorization.

## Frozen stage sequence and present blocker

The frozen [master details](../01-roadmap/MASTER-ROADMAP-DETAILS.md) and [execution roadmap](../01-roadmap/EXECUTION-ROADMAP.md) require `P24-B Manual Live → P24-C Semi-Automatic`, followed by micro-capital, canary, controlled auto, emergency drills, live monitoring and explicit G13 Owner gate. Each new scope of autonomy/capital needs fresh evidence and authorization. It cannot inherit prior approval.

The [production readiness dossier](../../config/production/production-readiness-dossier.json) currently says P24-A assessment-only CANONICAL_COMPLETE, P24-B BLOCKED, **nine PRE_FIRST_LIVE blockers unsatisfied**, first-Live Owner approval NOT_GRANTED, P24-C..I NOT_STARTED, G13 NOT_STARTED, Live/Auto DISABLED. The user request to work on C authorizes **preparatory S0 research only**, not broker connectivity or stage promotion.

## Future P24-C execution prerequisites (not currently met)

1. P24-B formally CANONICAL_COMPLETE, with exact-main postmerge Governance/Branch Hygiene evidence, independently accepted real Manual Live execution and reconciliation, and released stage lock.
2. Separate semi-auto Owner authorization and A5/A6/A8/A9/A10 review of bounded strategy/asset/account/method, data rights and risk budget; no inferred source legality.
3. Per-intent UI must present immutable venue, strategy, instrument, side, quantities, limits and risk impact; an authenticated human must approve that **exact current revision and digest**, not a prior similar order.
4. A5 independent pretrade veto must re-evaluate after approval and immediately before any executable routing; a human or AI cannot override it.
5. A8 signed/authenticated human and credential isolation, A10 identity, event version, replay protection and audit provenance, session freshness and broker clock attestation, active kill-switch, known ACK/reconnect and reconciliation.
6. A separate implementation contract/PR and full integration, security, recovery, live sandbox and Owner gates before any scope broadening; never treat this S0 model as a production adapter.

## S0-only contract / evidence

Source: `packages/production/semiauto_s0_preflight.py` and `tests/p24/test_semiauto_s0_preflight.py`.

- `SyntheticIntent.digest()` binds an explicitly synthetic proposal ID, revision, venue tag, strategy tag, instrument, side and integer quantity unit. There is no real account information, price, broker data or quote.
- `SyntheticApproval` is only a **fixture**. It is not an authenticated human signature or Owner approval. A mismatch, prior-use acknowledgement ID, stale (or unbounded) synthetic expiry, changed intent or revision fails closed.
- `SyntheticControls` defaults all flags false, including P24-B, independent A5, A8, A10, source rights/time/freshness, real-B approval, kill latch, broker ACK and reconciliation. A fully true vector is a **simulated test fixture only**.
- `evaluate_s0` is pure (no OS time, filesystem writes, credentials, external market data, network, MetaTrader, SDK or execution API). It produces only `S0_BLOCKED` or `S0_FIXTURE_ELIGIBLE`, with `next_action=NO_ORDER`, `external_order_authority=False`, `operational_demo_certified=False`, `p24_c_stage_activated=False`, `live_trading_enabled=False` and `auto_trading_enabled=False` in ALL cases.
- An `S0_FIXTURE_ELIGIBLE` result must **never** be promoted to broker-ready, Demo-ready, P24-C started/completed or live authority. No amounts/leverage/venue are being selected by this package.

## Acceptance / negative suite

Verify denial when any flag is absent; type-forged booleans/integers, missing A5 veto, missing human acknowledgement, altered intent binding, replay, invalid venue/quantity/direction, stale or future synthetic time, unknown ACK and kill switch. Assert source contains no broker/network/order transport imports or methods. Verify exact production dossier all nine live blockers still false.

Only a separate scoped PR **with current exact HEAD, mandatory full Governance, real Trivy/SBOM, independent A5/A8/A10 domain evidence, unexpired SHA256 artifact and a new Owner Human Gate** may merge this strictly offline package. After merger, postmerge CI/Branch Hygiene must pass before this *preparatory task* closes. Formal P24-C still remains NOT_STARTED until P24-B is legitimately complete. GitHub Demo [#508](https://github.com/rahemih/Finance/issues/508) and Live [#491](https://github.com/rahemih/Finance/issues/491) remain open.
