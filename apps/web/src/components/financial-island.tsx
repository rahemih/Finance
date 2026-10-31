import type { ReactNode } from "react";
/** Bidi isolation for IDs/quantities/prices; style is canonical P23-B, never a decision/approval control. */
export function FinancialIsland({ children }: { children: ReactNode }) {
  return <bdi dir="ltr" className="nq-financial-island">{children}</bdi>;
}
