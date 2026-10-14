import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {test} from 'node:test';

const capture=readFileSync(new URL('../benchmarks/raw/neko-product-host/static/app/app-audio-capture.js',import.meta.url),'utf8');
const policy=readFileSync(new URL('./neko_capture_policy.js',import.meta.url),'utf8');
function fixture(install=true) {
  const sent=[], handlers=new Map();let captured=0;
  const socket={readyState:1,send(raw){sent.push(JSON.parse(raw));}};
  const denied=()=>{captured++;throw new Error('Device initialization forbidden');};
  const S={socket,isRecording:false,isMicMuted:false,gameVoiceSttGateActive:false};
  const context=vm.createContext({appState:S,appConst:{},appUtils:{isMobile:()=>false},
    navigator:{mediaDevices:{getUserMedia:denied,getDisplayMedia:denied,enumerateDevices:denied}},
    DOMException,SpeechRecognition:denied,webkitSpeechRecognition:denied,AudioContext:denied,Audio:denied,
    WebSocket:{OPEN:1},document:{documentElement:{setAttribute(){}},getElementById(){return null;},
      addEventListener(){},querySelectorAll(){return [];}},
    CustomEvent:class{constructor(type,options){this.type=type;this.detail=options?.detail;}},
    addEventListener(name,callback){if(!handlers.has(name))handlers.set(name,[]);handlers.get(name).push(callback);},
    dispatchEvent(event){for(const handler of handlers.get(event.type)||[])handler(event);},
    setTimeout(){return 1;},clearTimeout(){},setInterval(){return 1;},clearInterval(){},console});
  vm.runInContext('window=globalThis;',context);
  vm.runInContext(policy,context);
  if(install)vm.runInContext('NekoCapturePolicy.installOutputOnly({enabled:true})',context);
  vm.runInContext(capture,context);
  const api=context.appAudioCapture;
  context.dispatchEvent({type:'voice-input-socket-open',detail:{socket}});
  return {api,S,context,sent,captured:()=>captured};
}

test('actual module sends monotonic core lease and PCM without a capture flag or device',()=>{
  const f=fixture();const idle=f.sent.at(-1);
  assert.equal(idle.owner,'none');assert.equal(idle.engaged,false);
  const ticket=f.api.beginFixedInput(), control=f.sent.at(-1);
  assert.equal(ticket.active,true);assert.equal(ticket.capture_started,false);
  assert.equal(control.owner,'core');assert.equal(control.engaged,true);
  assert.ok(control.lease_generation>idle.lease_generation);
  assert.equal(f.S.isRecording,false);assert.equal(f.api.sendFixedInputFrame(ticket.id,[0,12,-12]),true);
  assert.deepEqual(f.sent.at(-1),{action:'stream_data',input_type:'audio',data:[0,12,-12]});
  assert.equal(f.api.endFixedInput(ticket.id),true);
  assert.equal(f.sent.at(-1).owner,'none');assert.ok(f.sent.at(-1).lease_generation>control.lease_generation);
  assert.equal(f.api.sendFixedInputFrame(ticket.id,[1]),false);
  assert.equal(f.captured(),0);
});
test('unguarded ordinary mode refuses a fixed source and preserves its ordinary lease',()=>{
  const f=fixture(false);assert.throws(()=>f.api.beginFixedInput());
  f.S.isRecording=true;assert.equal(f.api.refreshMicLease(),'core');
  assert.equal(f.sent.at(-1).owner,'core');assert.equal(f.captured(),0);
});
for(const [name,change] of [
  ['mute',S=>S.isMicMuted=true],['focus',S=>{S.focusModeEnabled=true;S.isPlaying=true;}],
  ['game',S=>S.gameVoiceSttGateActive=true],['blocked route',S=>S.voiceInputRouteBlocked=true],
  ['recording takeover',S=>S.isRecording=true],['closed socket',S=>S.socket.readyState=3],
  ['new socket',S=>S.socket={readyState:1,send(){}}]
])test(name+' retires the source and never resumes its old ticket',()=>{
  const f=fixture(), ticket=f.api.beginFixedInput();change(f.S);
  const before=f.sent.filter(x=>x.action==='stream_data').length;
  assert.equal(f.api.sendFixedInputFrame(ticket.id,[1]),false);
  Object.assign(f.S,{isRecording:false,isMicMuted:false,focusModeEnabled:false,gameVoiceSttGateActive:false,voiceInputRouteBlocked:false});
  assert.equal(f.api.sendFixedInputFrame(ticket.id,[1]),false);
  assert.equal(f.sent.filter(x=>x.action==='stream_data').length,before);assert.equal(f.captured(),0);
});
test('old release cannot revoke a subsequent source and duplicate begin is refused',()=>{
  const f=fixture(), first=f.api.beginFixedInput();assert.throws(()=>f.api.beginFixedInput());
  f.api.endFixedInput(first.id);const next=f.api.beginFixedInput();
  assert.equal(f.api.endFixedInput(first.id),false);
  assert.equal(f.api.sendFixedInputFrame(next.id,[1]),true);
});
test('invalid PCM cannot be submitted',()=>{
  const f=fixture(), ticket=f.api.beginFixedInput();
  for(const data of [[],[NaN],[32768],[-32769],[.5],Array(481).fill(0),'audio'])assert.equal(f.api.sendFixedInputFrame(ticket.id,data),false);
  assert.equal(f.sent.filter(x=>x.action==='stream_data').length,0);
});
test('lifecycle commands remain bound to source, and end then release is atomic',()=>{
  const f=fixture(), ticket=f.api.beginFixedInput();
  assert.equal(f.api.sendFixedInputControl(ticket.id,{action:'start_session',input_type:'audio'}),true);
  const before=f.sent.length;
  assert.equal(f.api.sendFixedInputControl(ticket.id,{action:'stream_data',input_type:'text',data:'no'}),false);
  assert.equal(f.sent.length,before);
  assert.equal(f.api.sendFixedInputControl(ticket.id,{action:'end_session'}),true);
  assert.equal(f.sent.at(-2).action,'end_session');assert.equal(f.sent.at(-1).owner,'none');
  assert.equal(f.api.fixedInputState(ticket.id).active,false);
});
test('old lifecycle or release cannot send control to a new socket',()=>{
  const f=fixture(), ticket=f.api.beginFixedInput(), newer=[];
  f.S.socket={readyState:1,send(raw){newer.push(JSON.parse(raw));}};
  assert.equal(f.api.endFixedInput(ticket.id),true);assert.equal(newer.length,0);
  for(const action of ['start_session','end_session','end_audio_turn'])assert.equal(f.api.sendFixedInputControl(ticket.id,{action,input_type:'audio'}),false);
  assert.equal(newer.some(x=>['start_session','end_session','end_audio_turn'].includes(x.action)),false);
});
test('capture readiness revocation permanently invalidates an old source',()=>{
  const f=fixture(), ticket=f.api.beginFixedInput();f.context.nekoVoiceCaptureReadiness={blocked:()=>true};
  assert.equal(f.api.fixedInputState(ticket.id).active,false);
  f.context.nekoVoiceCaptureReadiness.blocked=()=>false;
  assert.equal(f.api.sendFixedInputFrame(ticket.id,[1]),false);
});
test('a readiness exception also retires the ticket permanently',()=>{
  const f=fixture(), ticket=f.api.beginFixedInput();
  f.context.nekoVoiceCaptureReadiness={blocked(){throw Error('Unknown readiness');}};
  assert.equal(f.api.fixedInputState(ticket.id).active,false);
  f.context.nekoVoiceCaptureReadiness.blocked=()=>false;
  assert.equal(f.api.sendFixedInputFrame(ticket.id,[1]),false);
});
