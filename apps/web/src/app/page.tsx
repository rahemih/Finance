/** Build-only root sentinel, intentionally NOT one of the 34 approved WEB-P0 pages. */
export const metadata = {
  title: "WEB-P0 — پیش‌نمایش غیرعملیاتی",
  robots: { index: false, follow: false },
};

export default function SourceBuildSentinel() {
  return (
    <main aria-label="وضعیت پیش‌نمایش غیرعملیاتی" style={{ maxWidth: "48rem", margin: "3rem auto", padding: "2rem" }}>
      <h1>پیش‌نمایش WEB-P0 هنوز فعال نیست</h1>
      <p>این خروجی صرفاً برای آزمون Build است. ورود به حساب، داده‌های بازار و عملیات معاملاتی در این مرحله غیرفعال هستند.</p>
      <p>وضعیت: بدون اتصال و بدون مجوز معامله</p>
    </main>
  );
}
