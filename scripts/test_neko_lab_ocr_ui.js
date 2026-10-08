const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname,
  '../benchmarks/raw/goal-isolated/study_companion/static/main.js'),'utf8');
const start = source.indexOf('async function runOcr(');
const end = source.indexOf('\nfunction buildFollowupText',start);
assert.ok(start>=0 && end>start);

async function verify() {
  const calls = [];
  const context = {
    $id:()=>({value:'fullscreen'}),studyInput:{value:''},ocrN:'',ocrT:'',
    t:(_,fallback)=>fallback,tf:(_,fallback,args)=>fallback.replace('{status}',args.status),
    setStatus:()=>{},setReply:()=>{},refreshStatus:async()=>{},
    setTimeout:callback=>callback(),interactiveOcrErrorMessage:()=>'',
    interactiveOcrFallbackMessage:()=>'',
    callPlugin:async(entry,args)=>{calls.push({entry,args});return {status:'ok',text:'fixture',capture_mode_used:'fullscreen'};},
  };
  vm.createContext(context);
  vm.runInContext(source.slice(start,end),context);
  await context.runOcr();
  assert.equal(calls[0].args.capture_mode,'fullscreen');
  assert.equal(calls[0].args.allow_fullscreen_fallback,false);
  assert.match(context.ocrN,/entire screen/);
  context.$id = ()=>({value:'interactive'});
  context.callPlugin = async(entry,args)=>{calls.push({entry,args});throw new Error('capture_busy');};
  await assert.rejects(context.runOcr(),/capture_busy/);
  assert.equal(calls.length,2);
  assert.equal(calls[1].args.capture_mode,'interactive');
  console.log('Explicit capture area and busy-error checks passed.');
}
verify().catch(error=>{console.error(error);process.exitCode=1;});
