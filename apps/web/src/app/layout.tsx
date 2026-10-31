import type { ReactNode } from "react";
import "../styles/tokens.css";
/**
 * Unstyled, non-operational App Router shell boundary.
 * No page route or preview is accepted until owner-reviewed screenshot baselines.
 */
export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="fa" dir="rtl" data-theme="dark">
      <body style={{ background: "var(--nq-background)", color: "var(--nq-text)", fontFamily: '"Noto Sans Arabic", sans-serif' }}>
        {children}
      </body>
    </html>
  );
}
