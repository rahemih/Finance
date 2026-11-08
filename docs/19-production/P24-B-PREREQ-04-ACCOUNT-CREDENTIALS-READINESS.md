# P24-B / Prerequisite 04 — owner-only accounts, credentials and least privilege

**Contract:** `FIN-P24-WK-001` • **Reviewed:** 2026-11-08 • **Status:** `DESIGN_AND_EVIDENCE_PLAN_ONLY / PRODUCTION_CREDENTIALS_READY_UNSATISFIED`  
**Scope:** read-only security architecture and evidence intake for **xChief MT5** and **Toobit API**; no account opening, KYC, funding, API secret creation, data-feed ingestion, trading, activation or deployment.

## 1. Hard boundary and context

The Owner approved #1–#3 **from their own decision/selection perspective** (3/9 Owner-approved); these are **not three separately independently certified production gate passes**. The protected `config/production/production-readiness-dossier.json` currently has **0/9 PRE_FIRST_LIVE satisfied**, including `PRODUCTION_CREDENTIALS_READY=false` with marker **"Accounts/KYC/credentials/funding/orders: NONE"**. P24-B is `BLOCKED_HUMAN_AND_PRODUCTION_PREREQUISITES`, G13 NOT_STARTED, Live and Auto DISABLED, FIRST_LIVE_OWNER_APPROVAL false. This file must not change those assertions.

The Owner has **not authorised creating real accounts now**; previous LiteFinance/MetaQuotes read-only Demo evidence [#508](https://github.com/rahemih/Finance/issues/508) cannot serve as xChief or Toobit account, KYC, funding or production access proof. No Demo order rights are granted here either.

**Account identity policy:** Only Owner ↔ chosen lawful venue handles personal KYC and account agreements. Never collect, request or paste in ChatGPT, GitHub or Linear: passports/IDs, residence evidence, tax IDs, phone/email, actual account number, Investor/Master password, API key/secret, Google Authenticator/2FA code, seed phrase, recovery codes or bank/payment details. Evidence requests accept **ONLY redacted PASS/FAIL attestations** with source, scope, authorised reviewer, date, expiry and SHA256; do not publish any raw private provider confirmation. No proxy, borrowed identity, altered residence or circumventing geo/KYC restriction.

## 2. Exact access map — design, NOT provisioned accounts

| Asset / integration | Desired privileges | Explicitly prohibited now | First-party evidence | Actual status |
| --- | --- | --- | --- | --- |
| **xChief MT5 read-only terminal** | Later, if an authorised Owner account exists: `Investor password` mode to observe prices and balance; distinct terminal/server/data folder, no orders | `Master` password, live trading/modify positions, credentials shared with assistant, terminal auto-trading, sending test orders | [MetaTrader 5 account connection](https://www.metatrader5.com/en/mobile-trading/iphone/help/settings_accounts/account_connect) explicitly separates investor read-only and master trading | **NOT_CREATED_OR_PROVISIONED** for approved xChief; older other-venue Demo not promoted |
| **xChief client portal** | Owner-held legitimate account profile and KYC with venue alone, MFA if supported; separate future redacted eligibility receipt | Credential/identity intake by assistant, payout or funds from assistant, automatic browser sign-up | [xChief AML](https://www2.xchief.com/about/aml/), [xChief privacy](https://www.xchief.com/about/privacy/) describe identity checks | **DEFERRED_OWNER_ONLY** |
| **Toobit public market stream** | If permitted by applicable licence and origin, prefer public `NONE` market endpoints for research without authenticated account access; respect rate limits and ToS | Assume public access = legal data use; poll real data in this task, trade, withdrawal or market-making | [API introduction](https://api-docs.toobit.com/api/introduction.html) describes keys on *some* endpoints | **NO_ACTIVE_FEED_OR_KEY** |
| **Toobit private read-only API** | Future separately scoped `READ` API for account balances/permissions if authorized; secure Vault storage, per-app keys, IP allowlist, no trade/withdraw | Any `TRADE`, `WITHDRAW`, transfers, custody/admin access, exposed private keys, implicit upgrade to write | [Toobit API FAQ dated 2026-01-22](https://www.toobit.com/en-US/support/api-faq), [key guide dated 2025-11-28](https://www.toobit.com/en-US/support/toobit-api-key-creation-guide) | **NO_REAL_KEY**, no private API |
| **Toobit write/trade API** | **DISABLED**; only a future separately governed decision after full onboarding, legal permission, independently bound A5/A8/A10 gates and exact Owner approval can even contemplate it | Enabling advanced-KYC write, Demo/Live orders, withdrawal, account transfer based on this doc | Toobit API FAQ says read-only no advanced KYC, writable trade/withdraw requires advanced KYC; also says **no external Testnet** | **FORBIDDEN_UNDER_CURRENT_SCOPE** |
| **Funding/withdrawal** | No real money movement at this stage; future funding path subject to own legal/financial controls with Owner only | Fund wallets/brokers, enable instant withdrawals, disable withdrawal controls, collect bank/crypto info | [Toobit withdrawal allowlist guidance](https://www.toobit.com/en-US/support/toobit-withdrawal-address-allowlist-guide) | **DEFERRED / ZERO MONEY MOVEMENT** |

**Do not derive binding law from API guides:** Toobit public FAQ's "no KYC for read-only API" describes API permission prerequisites, **not** a positive assurance that a particular Iran-resident real account is permitted; registration and ToS are separate. MetaTrader investor permission is a platform capability, **not** independent evidence that a broker has issued a usable xChief investor password to the Owner.

**Secret lifecycle ambiguity:** Toobit [2026 API FAQ](https://www.toobit.com/en-US/support/api-faq) says keys without IP allowlist expire after 90 days and IP-whitelisted keys may not expire; older [key-creation guide](https://www.toobit.com/en-US/support/toobit-api-key-creation-guide) broadly says keys expire after 90 days. **Never infer perpetual key safety from non-expiration**: require a future explicit signed provider policy and conservative rotation/revocation schedule no longer than 90 days until verified; forced shorter rotation on incident, privilege change or suspected leakage. No keys issued in this project by this task.

## 3. Credential policy to implement only under a separate task

| Control | Proposed policy / default | Proof required to mark verified |
| --- | --- | --- |
| Access boundary | `NO_ACCOUNT` => no authenticated sources; unauthenticated public quote collection also needs applicable market data rights; default `DENY` | Independent provider acceptance/contract + scoped permissions |
| Separation | Three roles: Owner-only provider administration, isolated read-only quote observer, and *future* execution role in a separate secret/environment never joined to read-only process | A8 graph proving no `WRITE` route from research app |
| Vault custody | Operator-managed encrypted Vault, no .env checked into Git, no chat/upload, no CI/plain logs; masked opaque evidence handles only | Vault-backed secret reference, access/egress/rotation proofs **without raw values** |
| MFA | Owner controls MFA/2FA/passkeys with backup recovery managed privately; no 2FA through AI; independently check platform capability | A8 redacted control attestation |
| Network security | Restrict API/terminal access to eligible, stable known egress; whitelist IP when offered and lawful; no VPN/proxy to bypass regional rules | Egress+IP ACL policy, exact grant, period, permitted territory |
| Lease / expiry | Define issue/last-validated/review/expiration time; conservatively rotate at least every 90 days when operational, renew on ToS/provider change | Vault version, redacted rotation log, no stale credential on resumed runner |
| Revocation | On leak, anomaly, lockout, bad permissions, region or terms change: revoke **at provider** by Owner/operator, revoke local Vault ref, stop service and quarantine data; no auto re-grant | Deactivation timestamp, revoked identifier hash, tested deny in sanctioned environment |
| Logs & alerts | No secret, PII, account number, bank/wallet info in evidence or telemetry; log role, operation class, env, request outcome and redacted handle | Automated secret/redaction scans and A10 retention policy |
| Provider entitlement | Match actual xChief/Toobit entity/product/account/region/permission with previously independently reviewed gates #1–#3 | Signed acceptance for exact entity and product with validity/expiry |
| Risk stop | Even any future *read-only* credential cannot enable new orders. Wrong role/missing/ambiguous permission, expired right, stale price or untrusted clock => A5 `NO_NEW_ORDERS` | Independent A5/A8/A10 simulation then authorized target environment drill |

## 4. Offline test matrix — NOT executed against providers

Each future test must be synthetic/isolated until separately authorised and independently reviewed, and only an approved environment can produce production-grade proof:

- `ACL-01`: simulated public market feed can read only permitted data and cannot access private account positions without authorized credentials.
- `ACL-02`: synthetic MT5 `INVESTOR` observes state but fails any command with `ORDER_SEND`/position modification intent; fail-closed on unknown MT5 login role.
- `ACL-03`: Toobit synthetic READ key can access only permitted read endpoints; reject TRADE, TRANSFER and WITHDRAW even if the upstream product UI accidentally enables them.
- `ACL-04`: missing, mismatched, expired or revoked secret => no network operation; no credentials logged; quarantine related evidence.
- `ACL-05`: mismatched venue/region/product/account class or read-only role promoted to write => A5 veto and A8 alert.
- `ACL-06`: expiring key, lost Vault access, rotation collision and IP egress drift produce safe deny and actionable redacted incident log.
- `ACL-07`: secrets/Git history/report redaction scans, separate FX/crypto principals, 10 internal user visibility boundary without 10-user secret distribution.
- `ACL-08`: provider-side revoke evidence and no replay of cached credential/old session before read-only reconnection.
- `ACL-09`: no test plan silently converts Toobit public documentation's "no dedicated testnet" into an imaginary sanctioned external sandbox.
- `ACL-10`: source clock discrepancy previously seen on a different MT5 Demo broker is not assumed corrected; do not use unresolved feed for model/risk approval.

**DoR/DoD:** All read-only policies and test definitions above can be reviewed today. **No actual operations or entitlement provisioning are claimed**. To eventually mark `PRODUCTION_CREDENTIALS_READY=true`, require Owner-completed legitimate account and KYC (privately and only when Owner chooses), specific jurisdiction/account/product entitlements and contractual funding path, real provider permissions with vault-backed segregated scope, independently reproducible A5/A8/A10 assessments, expiry/invalidation, exact evidence SHA256 and a separately approved canonical state PR plus postmerge tests. Until then #4 remains `UNSATISFIED`.

## 5. Decision/gate and follow-up

- [x] Owner-approved choices for #1/#2/#3 respected; no repeated venue or personal country questions.
- [x] Read-only provider authentication capabilities documented by first-party publications; actual account not created.
- [x] Owner-only KYC/privacy and no-secret rule established for this task.
- [x] ACL tests, source scope and redacted evidence requirements **specified** (not executed).
- [ ] Authenticated read-only authorized xChief investor session **not evidenced for selected xChief**; any other-broker Demo session is separate and remains Demo evidence only.
- [ ] Toobit actual authorized account/private read-only key **not provided and not requested**.
- [ ] Provider-bound vault/ACL/A5/A8/A10 testing, real entity/product/KYC/funding and credentials remain deferred until future separate Owner decision.
- [ ] `PRODUCTION_CREDENTIALS_READY` still **false**, 9 PRE_FIRST_LIVE false, P24-B blocked, FIRST_LIVE_OWNER_APPROVAL not granted, G13 NOT_STARTED and Live/Auto DISABLED.

**Governance status:** Three files only in this PR (task contract, this plan, one task catalog row). Full Governance verification, immutable artifact SHA256 and PR-specific Owner Human Gate **before merge**. Postmerge exact-main Governance and Branch Hygiene independently verified; [issue #527](https://github.com/rahemih/Finance/issues/527) may continue as separate branch-hygiene exception. Do not bypass it or claim fully clean merge if it fails. [Live tracker #491](https://github.com/rahemih/Finance/issues/491), [readiness checklist #528](https://github.com/rahemih/Finance/issues/528), [Demo tracker #508](https://github.com/rahemih/Finance/issues/508).
