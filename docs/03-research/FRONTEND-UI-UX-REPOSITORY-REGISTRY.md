# Finance / NEXUS QUANT — Frontend UI/UX Repository Registry

STATE = GOVERNED_RESEARCH_REGISTRY  
TASK = `FIN-P01-WU-001`  
LINEAR = `HOS-112`  
EFFECTIVE_DATE = 2026-10-03  
PRODUCTION_SELECTIONS = NOT_AUTHORIZED

## 1. Frontend strategy

NEXUS QUANT will not depend on a single admin-template repository. The UI should remain product-owned and compose specialized open-source projects behind a NEXUS design system.

Preferred architecture:

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

## 2. Repository registry

| Repository | Role | Upstream signal 2026-10-03 | License signal | Classification | Guardrail |
|---|---|---|---|---|---|
| `vercel/next.js` | framework/app shell | active; ~143k stars; push 2026-10-03 | MIT | ADOPT_CANDIDATE | exact version chosen in P04 |
| `shadcn-ui/ui` | design system/components | active; ~125k stars; push 2026-10-02 | MIT | ADOPT_CANDIDATE | product-owned components; avoid template lock-in |
| `better-auth/better-auth` | auth/session/2FA/passkey | active; ~30k stars; push 2026-10-03 | MIT | ADOPT_CANDIDATE | P03 security architecture remains authoritative |
| `tradingview/lightweight-charts` | financial charting | active; ~17k stars; push 2026-10-02 | Apache-2.0 | ADOPT_CANDIDATE | chart is visual layer, never trading authority |
| `TanStack/table` | tables/data grids | active; ~28k stars; push 2026-10-01 | MIT | ADOPT_CANDIDATE | server-side scale strategy selected later |
| `TanStack/query` | server state/cache | active; ~50k stars; push 2026-10-03 | MIT | ADOPT_CANDIDATE | realtime paths may use streaming alongside it |
| `react-hook-form/react-hook-form` | forms | active; ~44k stars; push 2026-10-03 | MIT | ADOPT_CANDIDATE | validation contracts remain shared/typed |
| `colinhacks/zod` | validation | active; ~44k stars; push 2026-10-02 | MIT | ADOPT_CANDIDATE | API contracts remain canonical |
| `motiondivision/motion` | animation | active; ~33k stars; push 2026-10-02 | MIT | USE_CANDIDATE | respect reduced-motion; no decorative latency |
| `tremorlabs/tremor` | dashboards/reports | maintained but slower activity; push 2025-10-10 | Apache-2.0 | USE_CANDIDATE | use selectively; shadcn remains base design system |
| `lucide-icons/lucide` | icons | active; ~24k stars; push 2026-10-03 | GitHub metadata NOASSERTION | USE_CANDIDATE | verify exact icon/package license in P04-F |

## 3. Page-to-repository mapping

### Authentication & identity
Pages:
- Login
- Register
- Forgot Password
- Reset Password
- Email Verification
- 2FA
- Passkey
- Device Verification
- Active Sessions
- Security Settings

Stack:
- shadcn/ui
- Better Auth
- React Hook Form
- Zod
- Lucide

### Main dashboard
Surfaces:
- portfolio value
- daily PnL
- exposure
- market regime
- risk state
- opportunities
- signals
- system health

Stack:
- shadcn/ui
- Tremor
- TanStack Query
- Lightweight Charts where time-series detail is needed

### Markets
Pages:
- Markets Overview
- Crypto
- Forex
- Gold/Oil/Indices context
- Watchlist
- Screener

Stack:
- shadcn/ui
- TanStack Table
- TanStack Query
- Lightweight Charts

### Asset detail
Tabs:
- Overview
- Advanced Chart
- Technical Analysis
- Order Flow
- Liquidity
- Fundamental/Macro
- News/Sentiment
- Historical Analogs
- AI Analysis

Stack:
- Lightweight Charts for price/volume/markers
- shadcn/ui for shell/tabs/cards
- TanStack Query for server state
- TanStack Table for event/history tables
- Tremor for secondary analytical summaries

### Opportunities & signals
Pages:
- Scanner
- Ranking
- LONG
- SHORT
- WAIT
- NO_TRADE
- Signal detail
- Evidence breakdown

Stack:
- shadcn/ui
- TanStack Table
- Tremor
- TanStack Query

### Trades & orders
Pages:
- Open Positions
- Pending Orders
- Trade History
- Demo Trades
- Shadow Trades
- Trade Journal
- Order detail

Stack:
- TanStack Table
- shadcn/ui
- TanStack Query
- Lightweight Charts for execution/entry/SL/TP context

### Portfolio & risk
Pages:
- Portfolio Overview
- Allocation
- Exposure
- Correlation
- Drawdown
- Risk limits
- Risk events

Stack:
- Tremor
- shadcn/ui
- TanStack Table
- Lightweight Charts for equity/drawdown series

### Research
Pages:
- Backtests
- Strategies
- Models
- Experiments
- Datasets
- Features
- Calibration
- Walk-forward/Monte Carlo results

Stack:
- TanStack Table
- Tremor
- shadcn/ui
- TanStack Query

### Reports
Pages:
- Daily
- Weekly
- Monthly
- Performance
- Risk
- Strategy
- Model
- Export center

Stack:
- Tremor
- TanStack Table
- shadcn/ui

### System & operations
Pages:
- System Health
- Data Providers
- Broker Status
- Agents
- Logs
- Alerts
- Incidents
- Replay/Recovery status

Stack:
- shadcn/ui
- TanStack Table
- Tremor
- TanStack Query

### Settings
Pages:
- Profile
- Security
- Notifications
- Risk Settings
- Trading Settings
- Connections
- Appearance
- Accessibility

Stack:
- shadcn/ui
- Better Auth
- React Hook Form
- Zod

## 4. UX rules

- Application chrome and text: **RTL-first Persian**.
- Financial charts, tickers, OHLC, order IDs, prices, quantities and timestamps where appropriate: **LTR islands**.
- Desktop-first for analysis/trading workflows.
- Mobile-first monitoring is required for dashboard, alerts, watchlist, positions and system health.
- Dark mode is first-class, not a later theme.
- Keyboard navigation and command palette are required for power-user workflows.
- Reduced-motion must be honored.
- Dense screens must support progressive disclosure; do not expose every metric at once.
- Critical state labels must never depend on color alone.
- Risk, stale-data, degraded-mode and NO_TRADE states must be visually explicit.
- Charts must never hide uncertainty, gaps or stale data.

## 5. Reusable product components to build

Product-owned components should sit above third-party primitives:
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
- test reduced-motion;
- define replacement/exit path;
- approve in P02/P04/P23 ADR/task.

## 7. Explicit non-decisions

This registry does not:
- install any package;
- implement frontend code;
- select production auth infrastructure;
- select hosting;
- override P03 security;
- enable Demo/Shadow/Live/Auto Trading.

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
