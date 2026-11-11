import test from "node:test";
import assert from "node:assert/strict";
import {
  AUTH_RUNTIME_ENABLED, SESSION_AUTHORITY, LOGIN_SCREENSHOT_STATES,
  LOGIN_COPY, getStateMessage, mayIssueSession
} from "../src/lib/auth/login-state.ts";

test("login preview cannot grant any session or enable runtime auth", () => {
  assert.equal(AUTH_RUNTIME_ENABLED, false);
  assert.equal(SESSION_AUTHORITY, false);
  for (const state of LOGIN_SCREENSHOT_STATES) {
    assert.equal(mayIssueSession(state), false);
  }
});

test("all eight screenshot state names are unique with safe Persian copy", () => {
  assert.equal(LOGIN_SCREENSHOT_STATES.length, 8);
  assert.equal(new Set(LOGIN_SCREENSHOT_STATES).size, 8);
  assert.equal(getStateMessage("DEFAULT"), null);
  assert.equal(getStateMessage("INVALID_CREDENTIALS"), "اطلاعات ورود معتبر نیست. دوباره تلاش کنید.");
  assert.match(getStateMessage("RATE_LIMITED"), /تلاش‌ها/);
  assert.match(getStateMessage("SESSION_EXPIRED"), /نشست شما/);
  assert.match(getStateMessage("OFFLINE"), /اینترنت/);
  assert.match(getStateMessage("SERVICE_UNAVAILABLE"), /سرویس ورود/);
  assert.equal(LOGIN_COPY.submit, "ورود به حساب");
  assert.equal(LOGIN_COPY.passkey, "ورود با کلید عبور (Passkey)");
});
