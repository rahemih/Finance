# NEXUS QUANT — P05-A Crypto Real-Time Adapter / Kaiko Baseline

STATE = P05-A IMPLEMENTATION  
TASK = `FIN-P05-WA-001`  
LINEAR = `HOS-183`  
DATE = 2026-10-05  
LEAD = A2 Data Agent

## 1. Objective

P05-A introduces the first production-zone market-data code in NEXUS QUANT.

The implementation remains provider-portable:
- provider-neutral envelope/types live under `packages/contracts`;
- Kaiko-specific translation lives under `adapters/market_data`;
- no strategy, risk, execution or UX code imports the provider implementation.

First controlled feed identity:

`Kaiko / cbse / spot / btc-usd`

This is a **market-data integration reference only**. It does not select Coinbase or any other venue for trade execution.

## 2. Fresh provider evidence

The P01-G canonical baseline selected:
- Crypto market-data primary reference: **Kaiko**;
- backup reference: **CoinAPI**;
- direct venue-native feed required later as a traded-venue cross-check.

Official Kaiko documentation was revalidated on 2026-10-05.

Current documented Stream behavior relevant to P05-A:
- Level 1 tick trades are available through Stream;
- Level 2 tick-level all bids/asks are available through Stream;
- L2 starts with a full snapshot then continuous updates;
- a later full snapshot must replace the local snapshot;
- amount `0` means downstream book state should remove that price level;
- `sequenceId` is lexicographically sortable;
- messages expose `tsExchange`, `tsCollection`, and `tsEvent`;
- testing HTTP examples use `X-Api-Key`.

Official source pages:
- https://docs.kaiko.com/explore-our-data/subscriptions-channel-availability
- https://docs.kaiko.com/stream/cefi-spot-market-data/all-trades.md
- https://docs.kaiko.com/stream/cefi-spot-market-data/bids-and-asks.md
- https://www.kaiko.com/about-kaiko/pricing-and-contracts

Kaiko pricing/subscription remains commercial/custom. P05-A does not claim an entitlement.

## 3. Contract boundary

Provider-neutral contract owns:
- provider identifier;
- provider-native instrument identity;
- event kind;
- provider sequence ID;
- exchange timestamp;
- collection timestamp;
- provider-event timestamp;
- local receive timestamp;
- typed trade/order-book payload;
- immutable provider metadata.

P05-A intentionally does **not** finalize:
- canonical cross-provider symbol IDs;
- universal clock/freshness policy;
- canonical gap metadata;
- cross-provider normalization.

Those belong to P05-D/P05-F.

## 4. Timestamp policy

Kaiko timestamps can carry nanosecond precision.

P05-A stores:
- original RFC3339 text;
- exact integer epoch nanoseconds.

The parser does not down-cast provider timestamps to floating-point seconds.

The caller supplies `received_at_ns`, which makes parsing deterministic in tests and keeps receive-time measurement under the ingestion runtime rather than hidden inside the parser.

## 5. Sequence policy

Kaiko documents `sequenceId` as lexicographically sortable.

P05-A therefore supports:
- FIRST;
- ADVANCING;
- DUPLICATE;
- OUT_OF_ORDER.

It does **not** claim IDs are contiguous. Missing-data/gap recovery is P05-F scope.

## 6. Order-book semantics

Supported provider update types:
- `SNAPSHOT`;
- `UPDATE`;
- `UPDATED` accepted as a documented/observed naming alias and normalized to `UPDATE`.

The parser preserves zero-amount levels. It does not silently delete them because local-book mutation belongs to downstream book-state logic.

A new snapshot is preserved as `SNAPSHOT`; downstream state must replace its existing book.

## 7. Credential handling

P05-A configuration accepts only a secret handle such as:

`secret://market-data/kaiko/api-key`

No raw API key is stored in config, source, fixture or test.

Request specifications expose:
- endpoint;
- HTTP method;
- required API-key header name;
- secret handle;
- deterministic request JSON.

They do not resolve the secret.

## 8. Live connectivity

Canonical P05-A state:

`LIVE_PROVIDER_CONNECTIVITY = DISABLED_ENTITLEMENT_REQUIRED`

Reason:
- no Kaiko subscription/trial is claimed;
- no API key exists in repository state;
- no licensing/entitlement is assumed.

Canonical CI is entirely offline.

A later governed activation task may resolve the secret handle and open a provider stream only after contract/entitlement review.

## 9. Real type checking

P05-A is the first product-source task.

Required CI therefore activates:
- `jakebailey/pyright-action` v3.0.2;
- action commit `8ec14b5cfe41f26e5f41686a31eb6012758217ef`;
- Pyright `1.1.414`;
- strict `pyrightconfig.json`;
- Python target `3.14`.

Action license was revalidated as MIT.

The prior P04 `PASS_NO_PRODUCT_SOURCE` readiness state becomes a real enforced typecheck.

## 10. Deterministic certification

Canonical tests are offline and cover:
- valid trade mapping;
- valid snapshot/update mapping;
- nanosecond timestamp preservation;
- zero-amount book semantics;
- duplicate/out-of-order sequence behavior;
- invalid instrument;
- invalid timestamp;
- invalid levels;
- raw-secret rejection;
- request-spec secret isolation;
- deterministic repeated parsing.

A deterministic evidence generator serializes representative adapter outputs twice and CI requires byte equality.

## 11. Safety

Production subscription: NONE  
Provider API credential: NONE  
Provider network connection: DISABLED  
Execution venue selection: NONE  
Orders/funding: NONE  
CANARY: DISABLED  
LIVE_TRADING: DISABLED  
AUTO_TRADING: DISABLED

## 12. Handoff

After canonical closure:

`P05-B — Forex Real-Time Adapters`

P05-A does not start P05-B itself.
