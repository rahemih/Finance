# G1 — Provider Baseline Dossier

GATE = `G1_PROVIDER_BASELINE`  
TASK = `FIN-P01-WG-004`  
STATE = `PASS_PENDING_CANONICAL_MERGE`  
DATE = `2026-10-04`  
COUNTRY_LOCATION = `NOT_USED`

## 1. Gate purpose

Prove that Finance / NEXUS QUANT has a sufficiently evidenced provider baseline to enter P02 architecture while remaining portable across future account jurisdictions and provider legal entities.

G1 is not a trading/account activation gate.

## 2. Mandatory evidence

PASS:
- P01-A Market Universe = CANONICAL_COMPLETE
- P01-B Market Data Providers = CANONICAL_COMPLETE
- P01-C Broker / Exchange Inventory = CANONICAL_COMPLETE
- P01-D Compliance constraint library = CANONICAL_COMPLETE
- P01-E Cost / Licensing / Data Rights = CANONICAL_COMPLETE
- P01-F Primary / Backup Strategy = CANONICAL_COMPLETE
- P01-G country-neutral decision matrix = READY
- primary/backup/cross-check architecture = PLAUSIBLE
- cost envelope / quote-required items = DOCUMENTED
- country/location excluded from ranking = VERIFIED
- Live Trading = DISABLED
- Auto Trading = DISABLED

## 3. Provider baseline

### Crypto data
Primary reference: Kaiko  
Backup: CoinAPI  
Cross-check: venue-native feed

### Forex data
Primary reference: dxFeed  
Backup: Twelve Data  
Secondary validation: Massive  
Future execution cross-check: actual selected broker quote

### Futures / context
Primary reference: Databento  
Backup: dxFeed  
Authority: exchange/index owner

### Macro / rates
Primary: direct official sources  
Secondary: FRED/ALFRED

### On-chain
Supplemental: Blockscout  
Independent verification: direct node / second indexer when required

## 4. Execution reference baseline

Crypto adapter reference order:
1. Kraken
2. Binance
3. Coinbase Advanced

Forex adapter reference order:
1. Saxo OpenAPI
2. OANDA v20
3. Interactive Brokers

These are architecture references only.

Final execution account/provider selection is explicitly deferred to account-opening / production activation.

## 5. Deferred activation evidence

Before any real provider/broker/exchange activation:
- actual account legal entity and product availability;
- actual client classification where material;
- KYC/account approval;
- current contract/fee/rights terms;
- live API permissions;
- exchange/index entitlements;
- no-withdrawal/least-privilege confirmation;
- execution certification and later Risk/Firewall gates.

## 6. Owner directive

No country or location may be used or inferred for this P01-G decision.

Any prior transient country-specific research is not part of the canonical G1 basis.

## 7. Gate verdict

`G1_PROVIDER_BASELINE = PASS_PENDING_CANONICAL_MERGE`

Meaning:
- P02 architecture may start after canonical merge/closure.
- provider portability is mandatory;
- production execution selection remains deferred;
- no trading authority is granted.

## 8. Safety

Production account selected: NO  
Production broker/exchange selected: NO  
Accounts/KYC: NONE  
Subscriptions/contracts: NONE  
Credentials: NONE  
Funding: NONE  
Orders: NONE  
Demo Trading: NOT_STARTED  
Shadow Trading: NOT_STARTED  
Live Trading: DISABLED  
Auto Trading: DISABLED
