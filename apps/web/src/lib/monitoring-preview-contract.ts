/** WEB-P0 P0-B: read-only display contracts; never infer live state from UI. */
export const MONITORING_PREVIEW_ONLY = true as const;
export const MONITORING_BACKEND_CONNECTED = false as const;
export const MONITORING_AUTHORITY = Object.freeze({
  HEALTH_STATE_KNOWN: false,
  RISK_STATE_KNOWN: false,
  ALARMS_COUNT_KNOWN: false,
  USER_BALANCE_KNOWN: false,
  LIVE_TRADING: false,
  AUTO_TRADING: false,
  ORDER_SUBMISSION: false,
  RISK_OVERRIDE: false,
  ALARM_ACKNOWLEDGEMENT: false,
  SESSION_AUTHORITY: false,
} as const);
export type MonitoringPageId = "010" | "079" | "084";
export type AvailabilityState = "NOT_CONNECTED" | "UNAVAILABLE" | "STALE" | "DEGRADED" | "UNKNOWN";
export const MONITORING_ROUTES = Object.freeze([
  { id: "010" as const, href: "/dashboard", label: "داشبورد" },
  { id: "079" as const, href: "/system", label: "سلامت سامانه" },
  { id: "084" as const, href: "/system/alerts", label: "مرکز هشدارها" },
]);
export const UNKNOWN_DATA_MARKER = "—" as const;
export function allowedAction(_action: string): false {
  return false;
}
