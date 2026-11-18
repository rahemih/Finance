'use strict';
// No browser automation or network. Execute real app.js logic in a locked-down
// Node VM with fake text nodes, protecting against false active-run claims.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const root = path.resolve(__dirname, '../..');
const script = fs.readFileSync(path.join(root, 'apps/agent-mission-control/app.js'), 'utf8');
const nodes = new Map();
const element = (id) => {
  if (!nodes.has(id)) nodes.set(id, {textContent:'', style:{}, classList:{toggle(){}},
                                      addEventListener(){}, querySelectorAll(){return []}});
  return nodes.get(id);
};
const context = vm.createContext({
  document: {readyState:'loading', addEventListener(){}, getElementById:element,
             querySelectorAll(){return []}},
  window:{}, setInterval(){}, Date, Intl, console,
});
vm.runInContext(script, context, {timeout:1000, filename:'app.js'});
const execute = (statement) => vm.runInContext(statement, context, {timeout:1000});

execute("state.runs=[{status:'in_progress'},{status:'invalid'}];state.prs=[{number:1}];state.issues=[{number:2}];state.source='waiting';renderStats()");
for (const id of ['stat-active','stat-failed','stat-prs','stat-issues']) {
  assert.equal(element(id).textContent, '—', id + ' must be unknown when stale');
}
execute("state.source='live';renderStats()");
assert.equal(element('stat-active').textContent,'1',
             'one real running GitHub workflow counted');
assert.equal(element('stat-prs').textContent,'1');
assert.equal(element('stat-issues').textContent,'1');
assert.equal(execute("jobStatus({status:'invalid'})"),'other',
             'invalid workflow state is never a running agent');
assert.equal(execute("jobStatus({status:null})"),'other');
assert.equal(execute("jobStatus({status:'completed',conclusion:'failure'})"),'failure');
assert.equal(execute("jobStatus({status:'queued'})"),'active');
execute("state.runs=[{status:'completed',conclusion:'failure'}];renderStats()");
assert.equal(element('stat-active').textContent,'0','verified zero allowed only when live');
assert.equal(element('stat-failed').textContent,'1','actual failed run is counted');
execute("state.source='waiting';renderStats()");
assert.equal(element('stat-active').textContent,'—','connection loss hides false zero');
console.log('FIN-P24-MISSION-STATUS-ACCEPTANCE: 10 checks PASSED (no network or model API)');
