# P24-WP-001-R01 — Read-only MT5 clock provenance probe (S1) and offline review

**Task:** FIN-P24-WP-001-R01. **2026-11-02.**  
**Canonical P24 position:** A complete *assessment-only*; B BLOCKED, C..I NOT_STARTED; 0/9 PRE_FIRST_LIVE, FIRST_LIVE_OWNER_GATE not granted, G13 NOT_STARTED; Live/Auto DISABLED. Engineering handoff PR #516 merged, operational Demo tracker [#508](https://github.com/rahemih/Finance/issues/508) and production tracker [#491](https://github.com/rahemih/Finance/issues/491) remain OPEN. No broker has been selected or certified.

## Why this exists

On 2026-11-02 user-local read-only Python MT5 samples from independent MetaQuotes-Demo FX and LiteFinance-MT5-Demo crypto terminals showed raw tick-time-milliseconds interpreted as Unix UTC approximately **+7202 seconds** relative to host OS UTC. Windows Iran Standard Time configuration and public NTP observations do **not** explain the full delta. The broker-specific time origin and quote freshness remain **UNVERIFIED**.

This package prepares a separate, native MQL5 read-only measurement to compare against Python timestamps and a local offline analyzer. It cannot directly observe the user's terminals from GitHub CI and does **not** compile/run a native .mq5 program in CI. Until the Owner runs it and the broker legally attests time semantics, no data-freshness or operational Demo validation can be claimed.

## Official time semantics (first-party MetaQuotes sources)

- [TimeCurrent](https://www.mql5.com/en/docs/dateandtime/timecurrent): last known **server** time from a Market Watch quote, not necessarily an atomic time snapshot for the requested symbol. Do not assume it is live now.
- [TimeTradeServer](https://www.mql5.com/en/docs/dateandtime/timetradeserver): current **estimated** trade-server time, computed on terminal and dependent on local machine time settings. Not independent network certification.
- [TimeGMT](https://www.mql5.com/en/docs/dateandtime/timegmt): GMT calculated from terminal computer's local time and DST/time-zone configuration. Cannot substitute for independently attested NTP.
- [SymbolInfoTick](https://www.mql5.com/en/docs/marketinformation/symbolinfotick) and [MqlTick](https://www.mql5.com/en/docs/constants/structures/mqltick): last-price-update raw time/time_msc and other fields; this probe **does not print bid/ask, volume or other market data**. MQL5 docs describe tick_time_msc as milliseconds since epoch; the observed broker-specific +7202s discrepancy remains unexplained.
- [TimeGMTOffset semantics](https://www.mql5.com/en/book/common/timing/timing_gmt): local-to-GMT time offset. Sanity compare TimeGMT ≈ TimeLocal + TimeGMTOffset, allowing a few seconds for non-atomic function calls. **Do not auto-subtract 7200.**

All actual rights to use the feed remain subject to separate legal data entitlement; no source licencing is inferred from access to a Demo terminal.

## Read-only native probe and privacy controls

Native script: [P24ReadOnlyClockProbe.mq5](../../tools/mt5/P24ReadOnlyClockProbe.mq5).

It uses ONLY SymbolInfoTick and MQL5 local/server time getters, then prints **three** lines, 1.2 seconds apart, per operator-selected symbol; it has no OrderSend, order_check, account credential, file-write, WebRequest, Socket, SymbolSelect, market data export, or settings-changing calls. Source static tests detect forbidden APIs. This is **not a native compilation attestation**.

Fixed log line schema, with synthetic placeholder values, **NOT observed actual data**:

\`\`\`
P24_CLOCK_V1|sample=1|symbol=EURUSD|tick_s=1793607202|tick_ms=1793607202573|gmt_s=1793600000|local_s=1793612600|gmt_offset_s=-12600|server_last_s=1793607202|server_est_s=1793607202|status=OK
\`\`\`

No account number, name, legal address, terminal path, server identifier, investor/master password, personally identifying text or quote prices are included. Never upload an entire terminal Journal, login screenshot or account details to GitHub or a chat.

## Windows 10 / MetaTrader 5 — Owner-local procedure

1. Open the **Forex Demo** terminal in its own window. In MT5 select **File > Open Data Folder**; open \`MQL5\Scripts\` and place a copy of the .mq5 source there. Do not alter terminal installation/configuration. Open that copy in **MetaEditor**, compile, and check there are no build errors. The GitHub test suite cannot perform this MetaEditor compile.
2. In the terminal Navigator > Scripts, run \`P24ReadOnlyClockProbe\` once with \`InpSymbol=EURUSD\` (or a verified visible symbol). This script will print exactly three \`P24_CLOCK_V1|\` records in the **Experts** tab; any \`P24_CLOCK_V1_ERROR|\` record is a failure, **not** evidence of healthy quotes. Use one instrument and retain the three original lines together.
3. Repeat independently in the **Crypto Demo** terminal using its own MT5 Data Folder and \`InpSymbol=BTCUSD\` if visible, otherwise a verified already-visible instrument such as \`ADAUSD\`. Never copy the Forex configuration or credentials to the crypto terminal; never run trade functions.
4. In Windows CMD, independently sample a public time reference without changing host settings:
   \`w32tm /stripchart /computer:time.windows.com /dataonly /samples:3\`.
   Record only offsets and the actual execution date/time. If it errors, record **NTP_UNAVAILABLE**. Do not restart Windows services or require admin for this diagnostic.
5. Copy **only the three fixed \`P24_CLOCK_V1|\` lines** per terminal into separate local UTF-8 text files named \`forex_clock.txt\` and \`crypto_clock.txt\`, not into public version control. Before sharing, confirm there are no unexpected extra fields or identifiers. Do not share raw MT5 Journal or account screenshots.
6. From the repository root, analyze the lines with these **one-line** CMD commands (quotes as shown). The review script is pure Python and performs **no network or MT5 connection**:

   Forex:
   \`python -c "from packages.production.mt5_clock_evidence import review_probe_lines;import json;f=open('forex_clock.txt',encoding='utf-8');print(json.dumps(review_probe_lines([x.strip() for x in f if x.startswith('P24_CLOCK_V1|')],tier='FOREX'),indent=2));f.close()"\`

   Crypto:
   \`python -c "from packages.production.mt5_clock_evidence import review_probe_lines;import json;f=open('crypto_clock.txt',encoding='utf-8');print(json.dumps(review_probe_lines([x.strip() for x in f if x.startswith('P24_CLOCK_V1|')],tier='CRYPTO'),indent=2));f.close()"\`

7. Preserve only a **redacted** report and hashes through the P24 Demo evidence workflow. Human reviewer validates separately: local date/time, OS/NTP confidence, active true broker/entity, actual quote source contract, and permitted trading-session status. Do **not** claim session-based freshness from a simulated fixture.

## Review gate: never normalize or pass by matching numbers alone

Parser: [mt5_clock_evidence.py](../../packages/production/mt5_clock_evidence.py), Tests: [test_mt5_clock_evidence.py](../../tests/p24/test_mt5_clock_evidence.py).

The strict parser accepts exactly ten fields in canonical order, 1–3 consecutive samples per tier, one symbol per tier, plausible Unix ranges, matching tick seconds/milliseconds, and a local GMT offset sanity flag. It rejects account/server/path extra fields, unexpected keys/order, malformed types, missing samples and tick-time regression. A failure of a consistency check is retained as \`INCONSISTENT\`; all results are permanently marked \`UNVERIFIED_FAIL_CLOSED\`.

**Evidence always remains:**
- \`clock_provenance = BROKER_NOT_ATTESTED\`
- \`machine_ntp_independently_verified = false\` (NTP needs separate real review)
- \`source_time_correction_applied = false\`
- \`data_freshness_certified = false\`
- \`read_only_mt5_compilation_and_execution_in_ci = NOT_RUN\`
- \`broker_sanctioned_order_tests = NOT_RUN\`
- \`operational_reconnect_drill = NOT_RUN\`
- \`pre_first_live_satisfied = 0\`, P24-B BLOCKED, G13 NOT_STARTED, Live/Auto DISABLED.

A small signed UTC delta alone cannot certify data; an anomaly near +7200 seconds cannot justify universal subtraction or a new broker server timezone assumption. Market closure and weekends, host clock offset, server time standards, actual market-data update source, actual venue contracts and independently documented broker time semantics must be assessed separately.

## Governance and resumption

This is a **S1 read-only diagnostic *preparation*** package, not an executed S1 run or certified S2 broker Sandbox. GitHub CI can only validate static MQL5 no-order properties and pure parser fixtures. No terminal connectivity is available to CI.

For actual local evidence validation, first obtain Owner-provided redacted outputs and independently review provider timestamps. For a real reconnect observation, wait for naturally occurring drop/recovery and fresh tick; no injected network faults under this task. Broker order ACK, risk-veto, emergency Kill Switch and Live readiness stay outside scope.

This PR changes exactly six allowlisted files; original P24 risk engine, WO S0 model, production dossier, frozen roadmap, Current State, workflow, credentials and all Live/Auto flags untouched. A **separate PR-specific exact Head + Governance Artifact SHA256 Owner Human Gate** must precede any merge. After protected-main merge, require exact-main Governance and Branch Hygiene and GitHub #508/#491 plus Linear reconciliation. Otherwise keep task unmerged. No status promotion to \`OPERATIONAL_DEMO_VALIDATED\` or \`P24_CANONICAL_COMPLETE\`.
