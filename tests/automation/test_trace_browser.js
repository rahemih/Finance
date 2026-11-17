'use strict';
// Test browser trace validation without external packages or a network.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');
const script = fs.readFileSync(path.resolve(__dirname,'../../apps/agent-mission-control/trace-ui.js'),'utf8');
const listeners=[];
const doc={readyState:'loading',addEventListener:(name,handler)=>listeners.push([name,handler]),getElementById:()=>null};
const win={};
const context=vm.createContext({window:win,document:doc,crypto:crypto.webcrypto,TextEncoder,Date,Uint8Array,Array,Set,String,Number,JSON,Error,globalThis:null});
context.globalThis=context;
vm.runInContext(script,context);
assert.equal(typeof win.nexusAgentTrace.validate,'function');
const canonical=o=>JSON.stringify(Object.keys(o).sort().reduce((acc,key)=>(acc[key]=o[key],acc),{}));
function event(overrides={}){
 const obj={schema_version:'fin.agent.event.v1',agent_id:'A1',task_id:'FIN-P24-WZ-002',run_id:'test-ui',event_type:'TEST_PASSED',message:'synthetic test only',target:'tests/automation/test_trace_browser.js',at_utc:'2026-11-17T12:00:00Z',financial_mode:'DEMO_ONLY',seq:1,prev_hash:'0'.repeat(64),...overrides};
 return {...obj,event_hash:crypto.createHash('sha256').update(canonical(obj)).digest('hex')};
}
(async()=>{
 const e=event();
 const report={schema_version:'fin.agent.event.v1',financial_mode:'DEMO_ONLY',source:'LOCAL_AGENT_EVENT_JOURNAL',last_hash:e.event_hash,events:[e]};
 const ok=await win.nexusAgentTrace.validate(report);
 assert.equal(ok.length,1);
 await assert.rejects(()=>win.nexusAgentTrace.validate({...report,events:[{...e,message:'tampered'}]}));
 await assert.rejects(()=>win.nexusAgentTrace.validate({...report,events:[{...e,financial_mode:'LIVE'}]}));
 await assert.rejects(()=>win.nexusAgentTrace.validate({...report,last_hash:'0'.repeat(64)}));
 await assert.rejects(()=>win.nexusAgentTrace.validate({...report,events:[{...e,agent_id:'A99'}]}));
 assert.equal(win.nexusAgentTrace.lastForAgent('A1'),null,'not imported; no phantom agent activity');
 console.log('TRACE_BROWSER_TESTS=PASS 6 checks');
})().catch(e=>{console.error(e);process.exitCode=1});
