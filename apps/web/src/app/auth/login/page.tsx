export const metadata = {
  title: "NEXUS QUANT — پیش‌نمایش غیرعملیاتی ورود",
  robots: { index: false, follow: false },
};

import LoginPreview from "../../../components/auth/login-preview";
import "./login-preview.css";

/** Source-only page; do not expose production Auth without a reviewed BFF ADR. */
export default function LoginPage() {
  return <LoginPreview visualState="DEFAULT" />;
}
