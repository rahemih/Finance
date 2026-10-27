# P23-B — Design System / RTL / Terminology

Task: `FIN-P23-WB-001`  
Status: IN_PROGRESS  
Lock: `LOCK-FIN-P23-WB-001-01` / ACQUIRED

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
