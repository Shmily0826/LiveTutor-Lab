// Serialize actual controller frames for the Python router/ASR offline check.
import {fixture} from './neko_fixed_input_fixture.mjs';
const mode=process.argv[2];
if(!['normal','same-socket-reset','new-socket-reset'].includes(mode))throw Error('Unknown case');
const f=fixture(),ticket=f.api.beginFixedInput();
const before=f.sent.length;
f.api.fixedInputState(ticket.id);
if(f.sent.length!==before)throw Error('State read emitted duplicate control');
const rows=f.sent.map(message=>({connection:'pet',message}));
if(mode==='normal'){
  if(!f.api.sendFixedInputFrame(ticket.id,[1,0,-1]))throw Error('Fixed frame refused');
  f.api.endFixedInput(ticket.id);
  rows.push(...f.sent.slice(before).map(message=>({connection:'pet',message})));
}else if(mode==='same-socket-reset'){
  if(!f.api.sendFixedInputFrame(ticket.id,[1,0,-1]))throw Error('Fixed frame refused');
  f.context.dispatchEvent({type:'voice-input-socket-open',detail:{socket:f.S.socket}});
  rows.push(...f.sent.slice(before).map(message=>({connection:'pet',message})));
}else{
  f.S.socket={readyState:1,send(raw){rows.push({connection:'pet-new',message:JSON.parse(raw)});}};
  f.context.dispatchEvent({type:'voice-input-socket-open',detail:{socket:f.S.socket}});
  const next=f.api.beginFixedInput();
  if(f.api.sendFixedInputFrame(ticket.id,[1]))throw Error('Old ticket revived');
  if(!f.api.sendFixedInputFrame(next.id,[1,0,-1]))throw Error('New ticket refused');
}
if(f.captured()!==0)throw Error('Device call attempted');
process.stdout.write(JSON.stringify({mode,rows,captureCalls:f.captured()}));
