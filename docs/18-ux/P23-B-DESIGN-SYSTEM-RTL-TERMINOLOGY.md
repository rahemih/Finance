# P23-B — Design System / RTL / Terminology

Task: `FIN-P23-WB-001`  
Status: CANONICAL_COMPLETE  
Lock: `LOCK-FIN-P23-WB-001-01` / RELEASED

## Objective

Create the product-owned visual and language contract that all P23 operational screens must consume.

## Directionality

- application shell and Persian narrative: RTL;
- canonical financial identifiers: LTR islands with bidi isolation;
- tickers, OHLC, prices, quantities, percentages, order/trade IDs, hashes, ISO timestamps, versions and IP addresses remain LTR;
- financial values and identifiers use Latin digits; localized narrative counters/calendar labels may use Persian digits.

## Typography

Canonical Figma intent:
- Persian UI: Noto Sans Arabic;
- Latin financial content: Noto Sans.

Production font packaging remains governed by licensing/build policy; P23-B defines the product intent and fallback boundary, not CDN/runtime delivery.

## Themes

Dark mode is first-class. Both light and dark themes define background, surface, body/muted text, border and focus tokens. Body/muted text contrast is validated against WCAG 2.2 AA minimum 4.5:1.

## Semantic states

Product-owned state semantics:
- success;
- warning;
- critical;
- stale;
- degraded;
- no-trade;
- disconnected;
- pending.

Every state requires both a text label and icon cue. Color-only meaning is forbidden.

## Density

- monitoring density: compact table rows/cards for watch surfaces;
- analysis density: roomier rows/cards for deep inspection.

## Terminology

Persian-first labels are paired with canonical identifiers. Trading direction and decision identifiers remain visible:
- خرید (LONG)
- فروش (SHORT)
- انتظار (WAIT)
- عدم معامله (NO_TRADE)

## Product-owned component families

P23-B governs variants for:
- NexusAppShell;
- MetricCard;
- RiskBadge;
- MarketStatusBadge;
- EmptyState;
- DegradedState;
- StaleDataBanner.

P23-C may implement these above third-party primitives but may not change their semantic contract silently.

## Canonical Figma source

https://www.figma.com/design/5aVGC189GMrRDokrjBbI5P?node-id=7-109

The Figma file exposes a plan-level limit of one mode per variable collection. The product contract is unchanged: Light and Dark remain first-class themes in GitHub. Figma represents them with separate product-owned single-mode collections:

- `NQ / Color Light`;
- `NQ / Color Dark`.

Shared primitives, spacing and radii remain separate single-mode collections. This yields five local collections and 101 local variables. The representation strategy is `SPLIT_SINGLE_MODE_COLLECTIONS`, preserving the same semantic token names and code syntax across both theme collections.

The subscribed Simple Design System library was inspected before creation. Its generic Card assets and token model do not match NEXUS QUANT's exact RTL/financial semantic-state contract, so P23-B uses local product-owned foundations rather than silently inheriting incompatible library semantics.

## Safety

No external orders, runtime mutation/remediation, credentials, production/P24 activation or Live/Auto trading authority are created by this workstream.


## Canonical closure evidence

- implementation PR #473 = MERGED;
- final implementation head = `fc4cb6480df9099bbdefc44cf34cf31e6c609a6c`;
- implementation Governance = `40470470634` / SUCCESS;
- implementation artifact = `12718358235` / `sha256:8edfc5201b38c21d7c3210160305c0efeec07b4045513114f57e25bc7a548a18`;
- design system ID = `e9926ae77d3484c795c60d24f61b046a08e99fc39eb00fc7c6e0e9d4edc81273`;
- deterministic evidence ID = `72e469c231014a047631c48243d11210f3a07f6d97214700c19df86a4217a658`;
- deterministic evidence SHA256 = `44e3e61d148b49e16c4390534f02f8470a7b9ae48fcceca6159d22ce0e2ded3e`;
- implementation merge SHA = `260cdfaa37c3ed535094d9ee7b4da863a81cb347`;
- post-merge Governance = `40470724850` / SUCCESS;
- post-merge artifact = `12718313766` / `sha256:cc7533aba0cd641279b11419e626ff6881cad1ef0995e435348eab00c2ac55ce`;
- post-merge Branch Hygiene = `40470724880` / SUCCESS.

P23-C = READY_NOT_STARTED.  
P24 = NOT_STARTED.  
LIVE_TRADING / AUTO_TRADING = DISABLED.
