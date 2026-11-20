import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
const read = (p) => readFileSync(new URL(p, import.meta.url), 'utf8');
test('exact patched runtime versions and no dependency ranges', () => {
  const p=JSON.parse(read('../package.json'));
  assert.equal(p.dependencies.next,'16.4.3');
  assert.equal(p.devDependencies.typescript,'5.9.3');
  assert.equal(p.dependencies.react,p.dependencies['react-dom']);
  assert.equal(p.engines.node,'24.21.0');
  for (const version of Object.values({...p.dependencies,...p.devDependencies})) assert.match(version,/^\d+\.\d+\.\d+$/);
});
test('root sentinel cannot submit, login, or claim a visual baseline', () => {
  const page=read('../src/app/page.tsx');
  assert.match(page,/Build-only root sentinel/);
  assert.doesNotMatch(page,/(fetch\s*\(|localStorage|sessionStorage|WebSocket\s*\(|submitOrder|createSession)/);
  const manifest=JSON.parse(read('../contracts/web-p0-pages.json'));
  assert.equal(manifest.ownerApprovedBaselineCount,0);
  assert.ok(manifest.pages.every(p=>p.implementationStatus==='NOT_IMPLEMENTED' && p.visualBaselineStatus==='REVIEW_REQUIRED'));
});

test('WEB-P0 preview does not route unavailable portfolio or demo sidebar items to dashboard', () => {
  const source=read('../src/components/markets/markets-reference-preview.tsx');
  assert.match(source, /n\.label==="پرتفوی و ریسک"\|\|n\.label==="مرکز دمو"/);
  assert.match(source, /aria-disabled="true" title="این بخش در پیش‌نمایش در دسترس نیست"/);
  assert.match(source, /ناموجود<\/span>/);
});

test('WEB-P0 preview does not misroute user access management to system health', () => {
  const source=read('../src/components/markets/markets-reference-preview.tsx');
  assert.doesNotMatch(source, /href="\/system"><span>♧<\/span>کاربران و دسترسی‌ها/);
  assert.match(source, /aria-disabled="true" title="مدیریت کاربران در پیش‌نمایش در دسترس نیست"/);
  assert.match(source, /کاربران و دسترسی‌ها · ناموجود/);
});

test('WEB-P0 static header does not advertise an operational search landmark', () => {
  const source=read('../src/components/markets/markets-reference-preview.tsx');
  assert.doesNotMatch(source, /className="nqr-top-search" role="search"/);
  assert.match(source, /className="nqr-top-search" aria-label="جست‌وجوی سامانه در این پیش‌نمایش غیرفعال است"/);
  assert.match(source, /جست‌وجو در سامانه · ناموجود/);
});
