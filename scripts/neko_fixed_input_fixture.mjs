// Actual controller offline fixture; device APIs throw if called.
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const capture=readFileSync(new URL('../benchmarks/raw/neko-product-host/static/app/app-audio-capture.js',import.meta.url),'utf8');
const policy=readFileSync(new URL('./neko_capture_policy.js',import.meta.url),'utf8');
export function fixture(install=true, pathname='/') {
  const sent=[], handlers=new Map();let captured=0;
  const socket={readyState:1,send(raw){sent.push(JSON.parse(raw));}};
  const denied=()=>{captured++;throw new Error('Device initialization forbidden');};
  const S={socket,isRecording:false,isMicMuted:false,gameVoiceSttGateActive:false};
  const context=vm.createContext({appState:S,appConst:{},appUtils:{isMobile:()=>false},
    navigator:{mediaDevices:{getUserMedia:denied,getDisplayMedia:denied,enumerateDevices:denied}},
    DOMException,SpeechRecognition:denied,webkitSpeechRecognition:denied,AudioContext:denied,Audio:denied,
    WebSocket:{OPEN:1},location:{pathname,href:'http://localhost:48911'+pathname},document:{documentElement:{setAttribute(){}},getElementById(){return null;},
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
