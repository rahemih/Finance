"use client";

import { useState, type FormEvent } from "react";
import { AUTH_RUNTIME_ENABLED, LOGIN_COPY, getStateMessage, type LoginVisualState } from "../../lib/auth/login-state";

/**
 * PAGE-001 accessible, non-operational preview.
 * Forms are disabled and no identifiers/passwords are accepted or submitted.
 * Not visually accepted until owner baseline + Playwright comparisons.
 */
export default function LoginPreview({ visualState = "DEFAULT" }: { visualState?: LoginVisualState }) {
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const stateMessage = getStateMessage(visualState);

  function blockSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
  }

  return (
    <main className="login-preview" data-theme={theme} dir="rtl">
      <div className="login-preview__container">
        <section className="login-preview__card" aria-labelledby="login-title">
          <div className="login-preview__brand" dir="ltr">NEXUS QUANT</div>
          <h1 id="login-title">{LOGIN_COPY.title}</h1>
          <p className="login-preview__subtitle">{LOGIN_COPY.subtitle}</p>

          <p className="login-preview__unavailable" id="login-unavailable" role="status">
            {LOGIN_COPY.previewBlocked}
          </p>

          {stateMessage ? (
            <p className="login-preview__state" role="alert" aria-live="assertive">
              {stateMessage}
            </p>
          ) : null}

          <form method="post" onSubmit={blockSubmit} aria-describedby="login-unavailable">
            <fieldset className="login-preview__fields" disabled>
              <label htmlFor="login-identifier">{LOGIN_COPY.identifier}</label>
              <input
                id="login-identifier"
                name="identifier"
                type="text"
                autoComplete="off"
                placeholder={LOGIN_COPY.identifierPlaceholder}
                aria-describedby="login-unavailable"
                disabled
              />
              <label htmlFor="login-password">{LOGIN_COPY.password}</label>
              <input
                id="login-password"
                name="password"
                type="password"
                autoComplete="off"
                placeholder={LOGIN_COPY.passwordPlaceholder}
                aria-describedby="login-unavailable"
                disabled
              />
              <button className="login-preview__primary" type="submit" disabled>
                {LOGIN_COPY.submit}
              </button>
              <button className="login-preview__secondary" type="button" disabled>
                {LOGIN_COPY.passkey}
              </button>
            </fieldset>
          </form>

          <nav className="login-preview__actions" aria-label="راهنمای ورود و بازیابی">
            <span aria-disabled="true">{LOGIN_COPY.recovery} — غیرفعال</span>
            <details>
              <summary>{LOGIN_COPY.help}</summary>
              <p>{LOGIN_COPY.support}</p>
            </details>
          </nav>

          <p className="login-preview__notice">{LOGIN_COPY.securityNotice}</p>
        </section>

        <aside className="login-preview__aside" aria-label="معرفی عمومی سامانه">
          <p className="login-preview__eyebrow" dir="ltr">NEXUS QUANT</p>
          <h2>سامانه خصوصی تحلیل و مدیریت معاملات</h2>
          <p>نمای اولیه رابط کاربری؛ بدون نمایش اطلاعات حساب، بازار یا معاملات.</p>
        </aside>
      </div>

      <footer className="login-preview__footer">
        <span dir="ltr">WEB-P0 · PAGE-001 · PREVIEW</span>
        <button type="button" onClick={() => setTheme(theme === "dark" ? "light" : "dark")} aria-pressed={theme === "light"}>
          {theme === "dark" ? "حالت روشن" : "حالت تاریک"}
        </button>
      </footer>

      <span className="login-preview__sr-only">وضعیت سرویس ورود: غیرفعال در نسخه پیش‌نمایش</span>
      {!AUTH_RUNTIME_ENABLED ? null : null}
    </main>
  );
}
