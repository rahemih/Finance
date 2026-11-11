/** PAGE-001 — source-only auth state contract. Never issues a session. */
export const LOGIN_SCREENSHOT_STATES = [
  "DEFAULT",
  "AUTHENTICATING",
  "INVALID_CREDENTIALS",
  "RATE_LIMITED",
  "ACCOUNT_RESTRICTED",
  "SESSION_EXPIRED",
  "OFFLINE",
  "SERVICE_UNAVAILABLE",
] as const;

export type LoginVisualState = typeof LOGIN_SCREENSHOT_STATES[number];
export const AUTH_RUNTIME_ENABLED = false as const;
export const SESSION_AUTHORITY = false as const;

export const LOGIN_COPY = Object.freeze({
  title: "ورود به حساب کاربری",
  subtitle: "دسترسی امن به سامانه خصوصی NEXUS QUANT",
  identifier: "شناسه کاربری",
  identifierPlaceholder: "ایمیل یا نام کاربری",
  password: "گذرواژه",
  passwordPlaceholder: "گذرواژه خود را وارد کنید",
  submit: "ورود به حساب",
  passkey: "ورود با کلید عبور (Passkey)",
  recovery: "بازیابی دسترسی",
  help: "راهنمای ورود",
  securityNotice: "این سامانه فقط برای کاربران مجاز است. فعالیت‌های امنیتی ثبت می‌شوند.",
  support: "برای مشکل دسترسی، با مسئول امنیت سامانه تماس بگیرید.",
  previewBlocked: "پیش‌نمایش غیرعملیاتی است؛ سرویس احراز هویت هنوز متصل نشده است.",
} as const);

const STATE_MESSAGES: Readonly<Record<LoginVisualState, string | null>> = Object.freeze({
  DEFAULT: null,
  AUTHENTICATING: "در حال بررسی اطلاعات ورود…",
  INVALID_CREDENTIALS: "اطلاعات ورود معتبر نیست. دوباره تلاش کنید.",
  RATE_LIMITED: "تعداد تلاش‌ها بیش از حد مجاز است. کمی بعد دوباره تلاش کنید.",
  ACCOUNT_RESTRICTED: "در حال حاضر ورود به این حساب امکان‌پذیر نیست. با مسئول امنیت تماس بگیرید.",
  SESSION_EXPIRED: "نشست شما به پایان رسیده است. دوباره وارد شوید.",
  OFFLINE: "ارتباط اینترنت برقرار نیست. اتصال را بررسی کنید.",
  SERVICE_UNAVAILABLE: "سرویس ورود موقتاً در دسترس نیست. بعداً تلاش کنید.",
});

export function getStateMessage(state: LoginVisualState): string | null {
  return STATE_MESSAGES[state];
}

/** Any future "success" transition must be a NEW security-reviewed backend contract. */
export function mayIssueSession(_state: LoginVisualState): false {
  return false;
}
