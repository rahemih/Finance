# P01-C — Broker / Exchange Inventory & Execution Scorecards

STATE = RESEARCH_BASELINE  
TASK = `FIN-P01-WC-001`  
LINEAR = `HOS-111`  
FINAL_EXECUTION_VENUE = `NOT_SELECTED`  
OWNER_JURISDICTION = `NOT_INFERRED`  
LIVE_TRADING = `DISABLED`  
AUTO_TRADING = `DISABLED`

## 1. Objective

Build a provider-neutral execution-venue inventory for the canonical Crypto + Forex tradable universe defined in P01-A.

This workstream compares documented execution API behavior only. It does not open accounts, create credentials, move funds, place orders, choose a production venue or decide legal eligibility.

Machine-readable evidence:
`docs/03-research/p01-c-execution-venue-scorecards.json`

## 2. Evaluation dimensions

Each venue is reviewed for:
- supported target asset/product class;
- official REST/WebSocket or gateway interfaces;
- client order IDs / request correlation;
- order/fill/cancel/reject lifecycle;
- account/order/position/fill reconciliation;
- paper/demo/testnet availability and parity limits;
- public rate/pacing limits;
- instrument/symbol metadata;
- credential scope and withdrawal-separation evidence;
- timeout/reconnect recovery requirements;
- operational/status mechanisms;
- jurisdiction/product eligibility flags.

No weighted winner is produced in P01-C.

## 3. Cross-cutting execution rules

1. Venue-native semantics remain authoritative even if a common adapter is later used.
2. Client-generated order IDs should be used where supported, but native order IDs and immutable execution/fill IDs must also be persisted.
3. A timeout is not proof that an order failed. Adapters must reconcile before retrying.
4. Reconnect recovery must rebuild order, fill, position and account/balance state.
5. Demo/testnet/paper fills must never be treated as proof of live execution quality.
6. Trading credentials must use least privilege and, where supported, must exclude withdrawal authority.
7. Broad credential models require compensating controls and account segregation.
8. Jurisdiction/account/product eligibility is deferred to P01-D and must use explicit Owner/entity facts rather than inferred location.

## 4. Crypto execution candidates

### Coinbase Advanced Trade

Documented capabilities:
- REST order/account/portfolio/fill endpoints;
- authenticated WebSocket user channel for order updates;
- custom `client_order_id`;
- endpoint-level view/trade permissions;
- public WebSocket rate limits;
- static Advanced Trade sandbox.

Important parity limit: Coinbase explicitly describes its Advanced Trade sandbox as static/pre-defined mocked responses. It is useful for schema/API integration checks, not for realistic fill/slippage/latency testing.

Perpetual/international product eligibility remains account/jurisdiction specific and must be resolved in P01-D.

Official sources:
- https://docs.cdp.coinbase.com/coinbase-app/advanced-trade-apis/rest-api
- https://docs.cdp.coinbase.com/coinbase-app/advanced-trade-apis/sandbox
- https://docs.cdp.coinbase.com/coinbase-app/advanced-trade-apis/websocket/websocket-channels
- https://docs.cdp.coinbase.com/coinbase-app/advanced-trade-apis/websocket/websocket-rate-limits

### Kraken

Documented capabilities:
- Spot REST/WebSocket order APIs;
- `cl_ord_id` support;
- open/closed order and trade permissions;
- granular API-key permission model;
- official guidance explicitly notes a trading integration generally does not need `Withdraw Funds`;
- account/pair based trading-rate controls;
- derivatives API request-limit model.

Kraken support material also describes a derivatives demo environment, but the 2026 page contains transition/decommissioning language. Therefore demo availability is marked `REVALIDATE_BEFORE_USE`, not assumed.

Official sources:
- https://docs.kraken.com/exchange/api-reference/spot-websocket-v2/add_order
- https://support.kraken.com/articles/206548367-what-are-the-api-rate-limits-
- https://support.kraken.com/articles/360000919966-how-to-create-an-api-key
- https://support.kraken.com/articles/360024809011-api-testing-environment-derivatives
- https://support.kraken.com/articles/360022635612-request-limits-rest-api-derivatives

### Binance

Documented capabilities from official Spot Testnet material:
- Spot Testnet user-data streams;
- `executionReport` order lifecycle messages;
- `clientOrderId`;
- reject reason and execution-type fields;
- symbol/account permissions;
- published request/order rate-limit structures.

Derivatives are retained as a research candidate class, but current test-environment parity and exact least-privilege key controls must be revalidated before any execution trial.

Official sources:
- https://developers.binance.com/en/docs/products/spot/testnet/user-data-stream
- https://developers.binance.com/docs/binance-spot-api-docs/testnet/enums
- https://developers.binance.com/docs/binance-spot-api-docs/testnet/websocket-api/response-format

## 5. Forex / multi-asset broker candidates

### OANDA v20

Documented strengths:
- separate practice and live base URLs;
- REST order API;
- client extensions with client-defined IDs/tags/comments;
- transaction history and transaction stream;
- account snapshot + incremental account-update reconciliation model;
- documented connection/request guidance.

Security finding: OANDA documents its personal access token as granting access to all sub-accounts. That is broader than the project’s preferred least-privilege model and therefore requires explicit compensating controls if OANDA survives P01-D/E/F.

Official sources:
- https://developer.oanda.com/rest-live-v20/authentication/
- https://developer.oanda.com/rest-live-v20/order-ep/
- https://developer.oanda.com/rest-live-v20/transaction-ep/
- https://developer.oanda.com/rest-live-v20/best-practices/
- https://developer.oanda.com/rest-live-v20/development-guide/

### Interactive Brokers

Documented strengths:
- TWS API / Web API and additional connectivity options;
- order/execution/account/position interfaces;
- paper trading environment;
- order IDs, client IDs, execution IDs and permanent IDs;
- public pacing limitations;
- broad multi-asset coverage.

Important paper limitation: IBKR explicitly warns that Paper Trading uses more simulated technology and execution behavior can differ from Live.

Operational consideration: TWS API normally depends on TWS or IB Gateway, which becomes an availability/operations question for P02/P20/P22.

Official sources:
- https://ibkrcampus.com/docs/tws-api/doc/introduction
- https://ibkrcampus.com/docs/tws-api/doc/notes-limitations/tws-api-limitations
- https://ibkrcampus.com/docs/web-api/trading/usage-and-availability/pacing-limitations
- https://ibkrcampus.com/docs/tws-api/ref/execution
- https://ibkrcampus.com/docs/third-party-integrations/general-third-party-frequently-asked-questions

### Saxo OpenAPI

Documented strengths:
- SIM endpoints;
- FxSpot order APIs;
- order pre-checks and reference-data constraints;
- WebSocket streaming for prices, orders, positions and balances;
- timeout handling guidance;
- duplicate-order protections and client-side de-bouncing guidance;
- 429/rate-limit behavior.

Critical recovery rule from official guidance: an order timeout can leave the actual order status uncertain, so the application must query/reconcile rather than blindly resend.

Official sources:
- https://www.developer.saxo/openapi/referencedocs/trade/v2/orders
- https://www.developer.saxo/openapi/learn/order-placement
- https://www.developer.saxo/openapi/learn/streaming

## 6. Current execution architecture implications

P01-C supports a later architecture where Crypto and Forex execution are separate venue adapters behind a common internal order contract.

The common contract must preserve venue-specific fields rather than flatten them away, including:
- native instrument ID/symbol;
- client order ID;
- venue order ID;
- immutable fill/execution ID;
- order state and reject code;
- time-in-force;
- price/quantity precision and filters;
- leverage/margin mode where applicable;
- event/transaction sequence or cursor;
- server timestamp + local receive timestamp;
- reconnect/reconciliation watermark.

## 7. Mandatory trial tests for later phases

Before any venue can progress toward Demo/Shadow/Canary:
- duplicate-order/idempotency test;
- timeout-after-submit reconciliation;
- cancel/replace race conditions;
- partial fill handling;
- reconnect during active order;
- stale stream/heartbeat detection;
- sequence-gap recovery;
- position/balance reconciliation;
- rate-limit backoff;
- maintenance/outage behavior;
- symbol precision/filter change;
- rejected-order taxonomy;
- paper/testnet-vs-live behavior delta;
- credential scope verification;
- proof withdrawal authority is absent where separate permissions exist.

## 8. Deferred to P01-D / P01-E / P01-F

P01-D:
- Owner/entity jurisdiction;
- account/product eligibility;
- regulatory restrictions;
- API/automated-trading restrictions.

P01-E:
- commissions/fees;
- spreads/funding;
- data subscriptions;
- professional/non-professional classifications;
- licensing/contract costs.

P01-F:
- primary/backup execution design;
- independence and failure domains;
- account/counterparty concentration;
- failover/disable policy.

## 9. Result

Crypto execution candidates documented = `YES`  
Forex execution candidates documented = `YES`  
Machine-readable scorecards = `CREATED`  
Final venue selection = `NOT_PERFORMED`  
Account opening = `NONE`  
Credentials = `NONE`  
Funding = `NONE`  
Orders = `NONE`  
Live Trading = `DISABLED`
