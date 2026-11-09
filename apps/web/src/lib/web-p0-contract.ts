/** WEB-P0 source-only foundation. Never treat proposed routes as implemented endpoints. */
import manifest from "../../contracts/web-p0-pages.json";

export type Environment = "DEV" | "TEST" | "RESEARCH" | "DEMO" | "SHADOW";
// Production CANARY/LIVE cannot be enabled from the browser.
export const WEB_P0_AUTHORITY = Object.freeze({
  LIVE_TRADING: false,
  AUTO_TRADING: false,
  BROWSER_BROKER_CONNECTION: false,
  BROWSER_ORDER_SUBMISSION: false,
  BROWSER_RISK_OVERRIDE: false,
  BASELINES_APPROVED: false,
} as const);

export const WEB_P0_CONTRACT = manifest;
export type WebP0Page = (typeof manifest.pages)[number];
export function getProposedPage(route: string): WebP0Page | undefined {
  return manifest.pages.find((page) => page.proposedRoute === route);
}
export function canSubmitTrade(): false {
  return false;
}
