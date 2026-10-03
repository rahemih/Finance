# Finance / NEXUS QUANT — Frontend UI/UX Repository Registry

STATE = GOVERNED_RESEARCH_REGISTRY  
TASK = `FIN-P01-WUI-001`  
LINEAR = `HOS-112`  
EFFECTIVE_DATE = 2026-10-03  
PRODUCTION_SELECTIONS = NOT_AUTHORIZED

## 1. Frontend strategy

NEXUS QUANT will not depend on a single admin-template repository. The UI should remain product-owned and compose specialized open-source projects behind a NEXUS design system.

Preferred candidate architecture:

```text
Next.js + React + TypeScript
        |
        +-- shadcn/ui ........ application design system
        +-- Better Auth ..... auth/session/security UX
        +-- Tremor .......... KPI/dashboard/report primitives
        +-- Lightweight Charts ... financial market charts
        +-- TanStack Table .. data grids/reports/trades
        +-- TanStack Query .. server-state/cache/refetch
        +-- React Hook Form . forms
        +-- Zod ............. form/schema validation
        +-- Motion .......... restrained interaction animation
        +-- Lucide .......... iconography
```

This is a candidate composition, not a production dependency decision. Exact versions and adoption decisions belong to P02/P04/P23.

## 2. Repository registry

Verified from current upstream GitHub metadata on 2026-10-03.

| Repository | Role | Upstream signal 2026-10-03 | License signal | Classification | Guardrail |
|---|---|---|---|---|---|
| `vercel/next.js` | framework/app shell | active; ~143k stars; push 2026-10-03 | MIT | ADOPT_CANDIDATE | exact version chosen in P04 |
| `shadcn-ui/ui` | design system/components | active; ~125k stars; push 2026-10-02 | MIT | ADOPT_CANDIDATE | product-owned components; avoid template lock-in |
| `better-auth/better-auth` | auth/session/2FA/passkey candidate | active; ~30k stars; push 2026-10-03 | MIT | ADOPT_CANDIDATE | P03 security architecture remains authoritative |
| `tradingview/lightweight-charts` | financial charting | active; ~17k stars; push 2026-10-02 | Apache-2.0 | ADOPT_CANDIDATE | chart is visual layer, never trading authority |
| `TanStack/table` | tables/data grids | active; ~28k stars; push 2026-10-01 | MIT | ADOPT_CANDIDATE | server-side scale strategy selected later |
| `TanStack/query` | server state/cache | active; ~50k stars; push 2026-10-03 | MIT | ADOPT_CANDIDATE | realtime paths may use streaming alongside it |
| `react-hook-form/react-hook-form` | forms | active; ~44k stars; push 2026-10-03 | MIT | ADOPT_CANDIDATE | validation contracts remain shared/typed |
| `colinhacks/zod` | validation | active; ~44k stars; push 2026-10-02 | MIT | ADOPT_CANDIDATE | API contracts remain canonical |
| `motiondivision/motion` | animation | active; ~33k stars; push 2026-10-02 | MIT | USE_CANDIDATE | respect reduced-motion; no decorative latency |
| `tremorlabs/tremor` | dashboards/reports | maintained, slower recent code activity; last push 2025-10-10 | Apache-2.0 | USE_CANDIDATE | use selectively; shadcn remains base design-system candidate |
| `lucide-icons/lucide` | icons | active; ~24k stars; push 2026-10-03 | GitHub metadata NOASSERTION | USE_CANDIDATE | verify exact package license in P04-F |

## 3. Page-to-repository mapping

### Authentication & identity
Pages: Login, Register, Forgot/Reset Password, Email Verification, 2FA, Passkey, Device Verification, Active Sessions, Security Settings.

Candidate stack: shadcn/ui + Better Auth + React Hook Form + Zod + Lucide.

### Main dashboard
Surfaces: portfolio value, PnL, exposure, regime, risk state, opportunities, signals, system health.

Candidate stack: shadcn/ui + Tremor + TanStack Query + Lightweight Charts where time-series detail is required.

### Markets
Pages: Markets Overview, Crypto, Forex, Gold/Oil/Indices context, Watchlist, Screener.

Candidate stack: shadcn/ui + TanStack Table + TanStack Query + Lightweight Charts.

### Asset detail
Tabs: Overview, Advanced Chart, Technical, Order Flow, Liquidity, Fundamental/Macro, News/Sentiment, Historical Analogs, AI Analysis.

Candidate stack: Lightweight Charts + shadcn/ui + TanStack Query + TanStack Table + optional Tremor summaries.

### Opportunities & signals
Scanner, Ranking, LONG/SHORT/WAIT/NO_TRADE, Signal Detail, Evidence Breakdown.

Candidate stack: shadcn/ui + TanStack Table + Tremor + TanStack Query.

### Trades & orders
Open Positions, Pending Orders, Trade History, Demo/Shadow Trades, Trade Journal, Order Detail.

Candidate stack: TanStack Table + shadcn/ui + TanStack Query + Lightweight Charts.

### Portfolio & risk
Portfolio Overview, Allocation, Exposure, Correlation, Drawdown, Risk Limits, Risk Events.

Candidate stack: Tremor + shadcn/ui + TanStack Table + Lightweight Charts.

### Research
Backtests, Strategies, Models, Experiments, Datasets, Features, Calibration, Walk-Forward / Monte Carlo.

Candidate stack: TanStack Table + Tremor + shadcn/ui + TanStack Query.

### Reports
Daily/Weekly/Monthly, Performance, Risk, Strategy, Model, Export Center.

Candidate stack: Tremor + TanStack Table + shadcn/ui.

### System & operations
System Health, Data Providers, Broker Status, Agents, Logs, Alerts, Incidents, Replay/Recovery.

Candidate stack: shadcn/ui + TanStack Table + Tremor + TanStack Query.

### Settings
Profile, Security, Notifications, Risk, Trading, Connections, Appearance, Accessibility.

Candidate stack: shadcn/ui + Better Auth + React Hook Form + Zod.

## 4. UX rules

- Application chrome and prose: **RTL-first Persian**.
- Charts, tickers, OHLC, order IDs, prices, quantities and other finance-native numeric sequences: **LTR islands**.
- Desktop-first for dense research/trading workflows.
- Mobile monitoring required for dashboard, alerts, watchlist, positions and system health.
- Dark mode first-class.
- Keyboard navigation and command palette required for power-user workflows.
- Reduced-motion must be honored.
- Dense screens use progressive disclosure.
- Critical state labels never depend on color alone.
- Risk, stale-data, degraded-mode and NO_TRADE states must be explicit.
- Charts must expose gaps, stale data and uncertainty rather than visually hiding them.
- Persian explanatory copy may wrap RTL around LTR market identifiers without reordering symbol semantics.

## 5. Product-owned components

Candidate reusable components:
- `NexusAppShell`
- `MetricCard`
- `RiskBadge`
- `MarketStatusBadge`
- `SignalCard`
- `EvidenceStack`
- `AssetHeader`
- `MarketChart`
- `OrderMarkerLayer`
- `OpportunityTable`
- `TradeTable`
- `ProviderHealthCard`
- `AgentStatusCard`
- `ReportSection`
- `EmptyState`
- `DegradedState`
- `StaleDataBanner`

## 6. Adoption gate

Before production adoption:
- pin exact version/commit;
- verify package license/SPDX;
- generate SBOM;
- review CVEs/transitives;
- benchmark bundle/runtime cost;
- verify SSR/RSC/browser compatibility;
- verify RTL/accessibility;
- test dark mode and mobile;
- test reduced motion;
- define replacement/exit path;
- approve in P02/P04/P23 ADR/task.

## 7. Explicit non-decisions

This registry does not install packages, implement frontend code, select production auth or hosting, override P03 security, or enable Demo/Shadow/Live/Auto Trading.

## 8. Recommended implementation order for P23

1. Design tokens + shadcn foundation
2. App shell/navigation
3. Authentication/security UX
4. Dashboard
5. Markets + Asset Detail
6. Opportunities/Signals
7. Trades/Portfolio/Risk
8. Research/Reports
9. System/Operations
10. Settings/Accessibility
11. Responsive/mobile hardening
12. E2E/accessibility/performance validation
