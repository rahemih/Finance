import { readFileSync } from 'node:fs';
const file=JSON.parse(readFileSync(new URL('../contracts/license-evidence-missing.json',import.meta.url),'utf8'));
const entries=file.purls.filter(x=>x.startsWith('pkg:npm/'));
const results=[];
for (let i=0;i<entries.length;i+=8) {
  const batch=entries.slice(i,i+8);
  results.push(...await Promise.all(batch.map(async purl=>{
    const nameVersion=purl.slice('pkg:npm/'.length);
    const split=nameVersion.lastIndexOf('@');
    const name=decodeURIComponent(nameVersion.slice(0,split));
    const version=nameVersion.slice(split+1);
    const uri='https://registry.npmjs.org/'+encodeURIComponent(name)+'/'+encodeURIComponent(version);
    try {
      const resp=await fetch(uri,{headers:{accept:'application/json'},signal:AbortSignal.timeout(10000)});
      if (!resp.ok) return {purl,name,version,status:'HTTP_'+resp.status,source:uri,license:null};
      const meta=await resp.json();
      const license=typeof meta.license==='string'?meta.license:(meta.license?.type??null);
      return {purl,name,version,status:'REGISTRY_RECEIVED',source:uri,license,integrity:meta.dist?.integrity??null};
    } catch(error) {
      return {purl,name,version,status:'FETCH_ERROR',license:null,source:uri,error:String(error)};
    }
  })));
}
const failures=results.filter(x=>!x.license);
console.log('BEGIN_WEB_P0_NPM_LICENSE_RESEARCH_JSON');
console.log(JSON.stringify({source:'official npm registry exact package/version metadata; unreviewed evidence only',count:results.length,unresolved:failures.length,results},null,0));
console.log('END_WEB_P0_NPM_LICENSE_RESEARCH_JSON');
if(failures.length) console.error('Unresolved npm license metadata:',failures.map(x=>x.purl).join(', '));
// Deliberately do not assert license approval or change P04 policy here.
