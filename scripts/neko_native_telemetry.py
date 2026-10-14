"""Observe only a task-created N.E.K.O renderer on its explicit debug port.

Uses the native shell's DevTools protocol, not a personal Chrome profile, browser
tab inventory, or project Playwright installation. No audio/capture input is opened.
"""
from __future__ import annotations
import base64
import asyncio
import json
from pathlib import Path
import urllib.parse
import urllib.request
import websockets

INSTALL = r"""(() => {
if (window.__dailyNativeTelemetry) return {installed:true,existing:true};
const trace = {events:[],binaryFrames:0,binaryBytes:0,inputFrames:0,inputSamples:0,installedAt:Date.now()/1000};
window.__dailyNativeTelemetry = trace;
const put = event => { trace.events.push({wall:Date.now()/1000,...event}); if(trace.events.length>500) trace.events.shift(); };
window.addEventListener('neko-speech-playback-state', e => {
 const p=e.detail||{};const event={direction:'device',type:'speech_playback_state'};
 for(const key of ['active','audible','correlationId','speechId','reason'])if(key in p)event[key]=p[key];put(event);
});
const sockets = new WeakSet();
const incomingText = new Set(['gemini_response','user_transcript','input_transcript','voice_transcript','transcript']);
const install = () => {
 const socket = window.appState?.socket;
 if (!socket || sockets.has(socket)) return;
 sockets.add(socket);
 socket.addEventListener('message', e => {
  if (typeof e.data !== 'string') { const bytes=e.data.size||e.data.byteLength||0; trace.binaryFrames++;trace.binaryBytes+=bytes;put({direction:'receive',type:'audio_frame',bytes,correlation_id:trace.lastNativeCorrelation});return; }
  try { const p=JSON.parse(e.data);const event={direction:'receive',type:p.type,speech_id:p.speech_id,turn_id:p.turn_id,correlation_id:p.correlation_id};
   if(incomingText.has(p.type))event.text=String(p.text||p.data||'').slice(0,12000);
   if(p.type==='system')event.data=String(p.data||'').slice(0,200);
   if(p.type==='session_failed'||p.type==='session_ended_by_server')event.reason=String(p.reason||p.message||'').slice(0,300);
   if(p.type==='session_started')event.microphone_route=p.microphone_route;
   if(p.type==='status'){
    let status=p.message||p.data;try{if(typeof status==='string')status=JSON.parse(status);}catch{status=null;}
    if(status && ['VOICE_INPUT_CONTROL_REJECTED','VOICE_INPUT_LEASE_RESYNC_REQUIRED','ASR_INPUT_DELIVERY_FAILED'].includes(status.code)){
     event.code=status.code;event.reason=String(status.details?.reason||'').slice(0,120);
    }
   }
   if(p.type==='audio_chunk'){event.correlation_id=p.sdk_speech_correlation_id;trace.lastNativeCorrelation=p.sdk_speech_correlation_id;}
   if(p.type==='game_route_speech_cancel')event.correlation_id=p.sdk_speech_correlation_id;
   put(event);
  } catch {}
 });
 const send = socket.send.bind(socket);
 socket.send = data => { try { const p=JSON.parse(data);
  if(p.action==='stream_data' && p.input_type==='audio' && Array.isArray(p.data)){trace.inputFrames++;trace.inputSamples+=p.data.length;}
  if(['voice_input_control','native_speech_playback_state','playback_feedback','audio_playback_feedback','speech_playback_feedback'].includes(p.action)) {
   const event={direction:'send',type:p.action};for(const key of ['event','owner','lease_generation','engaged','hard_muted','focus_suppressed','active','audible','speech_id','turn_id','correlation_id','sdk_speech_correlation_id','stage','status','reason']) if(key in p)event[key]=p[key];put(event);
  }
 }catch{} return send(data); };
};
install();trace.timer=setInterval(install,100);
return {installed:true,socketReady:window.appState?.socket?.readyState,url:location.href,wall:Date.now()/1000};
})()"""

SNAPSHOT = r"""(() => {
const trace=window.__dailyNativeTelemetry;
const rows=[...document.querySelectorAll('.message-bubble,.message-text,.message-content')].map(e=>({text:(e.innerText||'').trim(),className:e.className,visible:!!(e.offsetWidth||e.offsetHeight)})).filter(e=>e.text);
return {wall:Date.now()/1000,url:location.href,title:document.title,trace:trace?{events:trace.events,binaryFrames:trace.binaryFrames,binaryBytes:trace.binaryBytes,inputFrames:trace.inputFrames,inputSamples:trace.inputSamples,installedAt:trace.installedAt}:null,playback:window.NekoSpeechPlaybackState||null,bubbles:rows.slice(-40)};
})()"""


class NativeTelemetry:
    def __init__(self, socket):
        self.socket = socket
        self.counter = 0
        self.lock = asyncio.Lock()
        self.fixed_input_id = None

    @classmethod
    async def attach(cls, port):
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(f"http://127.0.0.1:{port}/json/list", timeout=5) as response:
            targets = json.load(response)
        # This port was allocated for this test's native launch; never query Chrome.
        targets = [t for t in targets if t.get("type") == "page" and
                   urllib.parse.urlsplit(t.get("url", "")).hostname in {"127.0.0.1", "localhost"} and
                   urllib.parse.urlsplit(t.get("url", "")).port == 48911]
        # Both chat templates load the audio modules. Presence/readiness cannot
        # identify the PCM owner; only the task's known root pet page can.
        pets = [t for t in targets if urllib.parse.urlsplit(t['url']).path == '/']
        if len(pets) != 1:
            raise RuntimeError(f'task native pet renderer identity unresolved: {len(pets)} root pages')
        socket = await websockets.connect(pets[0]["webSocketDebuggerUrl"], proxy=None, max_size=8*1024*1024)
        observer = cls(socket)
        try:
            probe = await observer.evaluate("({socketReady:window.appState?.socket?.readyState,audioPlaybackAvailable:!!window.appAudioPlayback})")
            if not probe or probe.get("socketReady") != 1 or not probe.get("audioPlaybackAvailable"):
                diagnostic = {key: (probe or {}).get(key) for key in ('socketReady', 'audioPlaybackAvailable')}
                raise RuntimeError('task native pet renderer not ready: '+json.dumps(diagnostic))
            await observer.evaluate(INSTALL)
            return observer
        except BaseException:
            await socket.close()
            raise

    async def command(self, method, params=None):
        async with self.lock:
            return await self._command_locked(method, params)

    async def _command_locked(self, method, params=None):
        self.counter += 1
        identifier = self.counter
        await self.socket.send(json.dumps({"id": identifier, "method": method, "params": params or {}}))
        while True:
            response = json.loads(await asyncio.wait_for(self.socket.recv(), timeout=8))
            if response.get("id") == identifier:
                if "error" in response:
                    raise RuntimeError(str(response["error"]))
                return response.get("result", {})

    async def evaluate(self, expression):
        result = await self.command("Runtime.evaluate", {"expression": expression, "returnByValue": True})
        if result.get("exceptionDetails"):
            raise RuntimeError("native telemetry expression failed")
        return result.get("result", {}).get("value")

    async def snapshot(self):
        result = await self.evaluate(SNAPSHOT)
        if self.fixed_input_id is not None:
            result['fixed_input'] = await self.evaluate(
                f"window.appAudioCapture.fixedInputState({self.fixed_input_id})")
        return result

    async def begin_fixed_input(self):
        if self.fixed_input_id is not None:
            raise RuntimeError('Fixed input source already registered')
        receipt = await self.evaluate('window.appAudioCapture.beginFixedInput()')
        if (not isinstance(receipt, dict) or receipt.get('active') is not True
                or receipt.get('capture_started') is not False or receipt.get('owner') != 'core'
                or type(receipt.get('id')) is not int or receipt['id'] < 1
                or type(receipt.get('lease_generation')) is not int or receipt['lease_generation'] < 1):
            raise RuntimeError('Fixed input controller registration failed')
        self.fixed_input_id = receipt['id']
        return receipt

    async def end_fixed_input(self):
        identifier = self.fixed_input_id
        self.fixed_input_id = None
        if identifier is not None:
            return await self.evaluate(f'window.appAudioCapture.endFixedInput({identifier})')

    async def send_current(self, payload):
        """Fixed test input on this renderer's own controller, never the superseded socket."""
        if self.fixed_input_id is None:
            raise RuntimeError('Fixed input source not registered; control/PCM refused')
        encoded = json.dumps(payload, ensure_ascii=True)
        if payload.get('action') == 'stream_data' and payload.get('input_type') == 'audio':
            if self.fixed_input_id is None:
                raise RuntimeError('Fixed input source not registered; PCM refused')
            samples = json.dumps(payload.get('data'), ensure_ascii=True, allow_nan=False)
            result = await self.evaluate(f'window.appAudioCapture.sendFixedInputFrame({self.fixed_input_id},{samples})')
        else:
            result = await self.evaluate(f'window.appAudioCapture.sendFixedInputControl({self.fixed_input_id},{encoded})')
        if result is not True:
            raise RuntimeError('Native controller did not accept fixed input')
        if payload.get('action') == 'end_session':
            self.fixed_input_id = None

    async def screenshot(self, path):
        result = await self.command("Page.captureScreenshot", {"format": "png"})
        Path(path).write_bytes(base64.b64decode(result["data"]))

    async def close(self):
        try:
            await self.evaluate("if(window.__dailyNativeTelemetry)clearInterval(window.__dailyNativeTelemetry.timer)")
        finally:
            await self.socket.close()
