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
