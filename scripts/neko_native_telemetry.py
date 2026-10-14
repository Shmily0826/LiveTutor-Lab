"""Observe only a task-created N.E.K.O renderer on its explicit debug port.

Uses the native shell's DevTools protocol, not a personal Chrome profile, browser
tab inventory, or project Playwright installation. No audio/capture input is opened.
"""
from __future__ import annotations
import base64
import asyncio
import json
import math
from pathlib import Path
import urllib.parse
import urllib.error
import urllib.request
import websockets

INSTALL = r"""(() => {
if (window.__dailyNativeTelemetry) { window.__dailyNativeTelemetry.refreshSocket(); return {installed:true,existing:true}; }
const trace = {events:[],eventSequence:0,binaryFrames:0,binaryBytes:0,inputFrames:0,inputSamples:0,socketCount:0,currentSocketId:null,installedAt:Date.now()/1000};
window.__dailyNativeTelemetry = trace;
const put = event => { trace.events.push({wall:Date.now()/1000,...event,observer_sequence:++trace.eventSequence}); if(trace.events.length>500) trace.events.shift(); };
window.addEventListener('neko-speech-playback-state', e => {
 const p=e.detail||{};const event={direction:'device',type:'speech_playback_state'};
 for(const key of ['active','audible','correlationId','speechId','reason','remainingSeconds','updatedAt'])if(key in p)event[key]=p[key];put(event);
});
const sockets = new WeakMap();
const incomingText = new Set(['gemini_response','user_transcript','input_transcript','voice_transcript','transcript']);
const install = () => {
 const socket = window.appState?.socket;
 if (!socket) { trace.currentSocketId=null; return; }
 if (sockets.has(socket)) { trace.currentSocketId=sockets.get(socket); return; }
 const socketId=++trace.socketCount;
 sockets.set(socket,socketId);trace.currentSocketId=socketId;
 let lastNativeCorrelation=null;
 socket.addEventListener('message', e => {
  if (typeof e.data !== 'string') { const bytes=e.data.size||e.data.byteLength||0; trace.binaryFrames++;trace.binaryBytes+=bytes;put({direction:'receive',type:'audio_frame',socket_id:socketId,bytes,correlation_id:lastNativeCorrelation});return; }
  try { const p=JSON.parse(e.data);const event={direction:'receive',type:p.type,socket_id:socketId,speech_id:p.speech_id,turn_id:p.turn_id,correlation_id:p.correlation_id};
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
   if(p.type==='audio_chunk'){event.correlation_id=p.sdk_speech_correlation_id;lastNativeCorrelation=p.sdk_speech_correlation_id;}
   if(p.type==='game_route_speech_cancel')event.correlation_id=p.sdk_speech_correlation_id;
   put(event);
  } catch {}
 });
 const send = socket.send.bind(socket);
 socket.send = data => { try { const p=JSON.parse(data);
  if(p.action==='stream_data' && p.input_type==='audio' && Array.isArray(p.data)){trace.inputFrames++;trace.inputSamples+=p.data.length;}
  if(['voice_input_control','native_speech_playback_state','playback_feedback','audio_playback_feedback','speech_playback_feedback'].includes(p.action)) {
   const event={direction:'send',type:p.action,socket_id:socketId};for(const key of ['event','owner','lease_generation','engaged','hard_muted','focus_suppressed','active','audible','speech_id','turn_id','correlation_id','sdk_speech_correlation_id','stage','status','reason']) if(key in p)event[key]=p[key];put(event);
  }
 }catch{} return send(data); };
};
trace.refreshSocket=install;install();trace.timer=setInterval(install,100);
return {installed:true,socketReady:window.appState?.socket?.readyState,url:location.href,wall:Date.now()/1000};
})()"""

BEGIN_FIXED_INPUT = r'''(() => {
const trace=window.__dailyNativeTelemetry;
if (!trace || typeof trace.refreshSocket!=='function') throw Error('Fixed input observer is not installed');
trace.refreshSocket();
const socket=window.appState?.socket;
const socketId=trace.currentSocketId;
const started=Date.now()/1000;
if (!socket || !socketId) throw Error('Fixed input socket is unavailable');
const receipt=window.appAudioCapture.beginFixedInput();
if (socket!==window.appState?.socket) {
    window.appAudioCapture.endFixedInput(receipt.id);
    throw Error('Fixed input socket changed during registration');
}
return {...receipt,socket_id:socketId,started_wall:started};
})()'''

SNAPSHOT = r"""(() => {
const trace=window.__dailyNativeTelemetry;
const rows=[...document.querySelectorAll('.message-bubble,.message-text,.message-content')].map(e=>({text:(e.innerText||'').trim(),className:e.className,visible:!!(e.offsetWidth||e.offsetHeight)})).filter(e=>e.text);
return {wall:Date.now()/1000,url:location.href,title:document.title,trace:trace?{events:trace.events,eventSequence:trace.eventSequence,currentSocketId:trace.currentSocketId,binaryFrames:trace.binaryFrames,binaryBytes:trace.binaryBytes,inputFrames:trace.inputFrames,inputSamples:trace.inputSamples,installedAt:trace.installedAt}:null,playback:window.NekoSpeechPlaybackState||null,bubbles:rows.slice(-40)};
})()"""


class NativeTraceHistory:
    """Accumulate the task observer's bounded ring; sequences are local, not ASR IDs."""
    def __init__(self, *, limit=12000):
        self.limit=limit
        self.installed_at=None
        self.events=[]

    def capture(self, snapshot):
        trace=snapshot.get('trace') or {}
        installed=trace.get('installedAt')
        sequence=trace.get('eventSequence')
        batch=trace.get('events')
        if (type(installed) not in (int,float) or not math.isfinite(installed) or installed<=0
                or self.installed_at is not None and installed!=self.installed_at
                or type(sequence) is not int or not len(self.events)<=sequence<=self.limit
                or not isinstance(batch,list) or len(batch)>500 or len(batch)>sequence
                or (sequence>0 and not batch)):
            raise RuntimeError('Native observer identity, sequence or capacity changed')
        expected=sequence-len(batch)+1
        added=[]
        for event in batch:
            if (not isinstance(event,dict) or type(event.get('observer_sequence')) is not int
                    or event['observer_sequence']!=expected
                    or type(event.get('wall')) not in (int,float) or not math.isfinite(event['wall'])
                    or event['wall']<installed):
                raise RuntimeError('Native observer sequence is incomplete')
            if expected<=len(self.events):
                if event!=self.events[expected-1]:
                    raise RuntimeError('Native observer changed a retained event')
            else:
                if expected!=len(self.events)+len(added)+1:
                    raise RuntimeError('Native observer ring lost events between polls')
                added.append(dict(event))
            expected+=1
        all_events=self.events+added
        frames=[e for e in all_events if e.get('type')=='audio_frame']
        if (type(trace.get('binaryFrames')) is not int or trace['binaryFrames']!=len(frames)
                or any(type(e.get('bytes')) is not int or e['bytes']<0 for e in frames)
                or type(trace.get('binaryBytes')) is not int
                or trace['binaryBytes']!=sum(e['bytes'] for e in frames)):
            raise RuntimeError('Native observer PCM counters disagree with retained events')
        self.installed_at=installed
        self.events=all_events
        return {**snapshot,'trace':{**trace,'events':[dict(e) for e in all_events],
            'collection':{'sequence_complete':True,'first_sequence':1 if sequence else 0,
                'last_sequence':sequence,'limit':self.limit}}}


class NativeRendererPending(RuntimeError):
    """The task's known pet surface has not finished loading."""


def read_task_targets(port, timeout):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(f"http://127.0.0.1:{port}/json/list", timeout=timeout) as response:
        return json.load(response)


async def close_failed_attachment(socket):
    try:
        await asyncio.wait_for(socket.close(), timeout=2)
    except Exception:
        transport = getattr(socket, 'transport', None)
        if transport is not None:
            transport.abort()


class NativeTelemetry:
    def __init__(self, socket):
        self.socket = socket
        self.counter = 0
        self.lock = asyncio.Lock()
        self.fixed_input_id = None
        self.fixed_input_scope = None

    @classmethod
    async def attach(cls, port, *, timeout=8):
        deadline = asyncio.get_running_loop().time() + timeout
        def remaining():
            value = deadline - asyncio.get_running_loop().time()
            if value <= 0:
                raise TimeoutError('task native attachment deadline expired')
            return value
        # Blocking local HTTP must not prevent the readiness deadline from firing.
        targets = await asyncio.wait_for(asyncio.to_thread(read_task_targets, port, min(5, remaining())),
                                         timeout=remaining())
        targets_before_filter = targets
        # This port was allocated for this test's native launch; never query Chrome.
        targets = [t for t in targets if t.get("type") == "page" and
                   urllib.parse.urlsplit(t.get("url", "")).hostname in {"127.0.0.1", "localhost"} and
                   urllib.parse.urlsplit(t.get("url", "")).port == 48911]
        # Both chat templates load the audio modules. Presence/readiness cannot
        # identify the PCM owner; only the task's known root pet page can.
        pets = [t for t in targets if urllib.parse.urlsplit(t['url']).path == '/']
        if not pets:
            foreign_roots = [t for t in targets_before_filter if t.get('type') == 'page'
                             and urllib.parse.urlsplit(t.get('url', '')).scheme in {'http', 'https'}
                             and urllib.parse.urlsplit(t.get('url', '')).path == '/']
            if foreign_roots:
                raise RuntimeError('task native pet renderer identity unresolved: foreign root')
            raise NativeRendererPending('task native pet renderer identity unresolved: 0 root pages')
        if len(pets) != 1:
            raise RuntimeError(f'task native pet renderer identity unresolved: {len(pets)} root pages')
        socket = await websockets.connect(pets[0]["webSocketDebuggerUrl"], proxy=None,
                                         max_size=8*1024*1024, open_timeout=min(5, remaining()), close_timeout=2)
        observer = cls(socket)
        try:
            probe = await asyncio.wait_for(observer.evaluate("({socketReady:window.appState?.socket?.readyState,audioPlaybackAvailable:!!window.appAudioPlayback})"),timeout=remaining())
            if not probe or probe.get("socketReady") != 1 or not probe.get("audioPlaybackAvailable"):
                diagnostic = {key: (probe or {}).get(key) for key in ('socketReady', 'audioPlaybackAvailable')}
                raise NativeRendererPending('task native pet renderer not ready: '+json.dumps(diagnostic))
            try:
                await asyncio.wait_for(observer.evaluate(INSTALL), timeout=remaining())
            except TimeoutError as error:
                raise RuntimeError('task native telemetry installation timed out') from error
            return observer
        except BaseException:
            await close_failed_attachment(socket)
            raise

    @classmethod
    async def attach_when_ready(cls, port, timeout=35):
        deadline = asyncio.get_running_loop().time() + timeout
        last = None
        while True:
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                raise TimeoutError('task native renderer readiness deadline expired') from last
            try:
                return await cls.attach(port, timeout=min(8, remaining))
            except (NativeRendererPending, ConnectionRefusedError, TimeoutError) as error:
                last = error
            except urllib.error.URLError as error:
                if not isinstance(error.reason, ConnectionRefusedError):
                    raise
                last = error
            # Poll the same task surface; never launch a replacement or connect a provider.
            await asyncio.sleep(min(.5, max(0, deadline - asyncio.get_running_loop().time())))

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
        result['fixed_input_scope'] = self.fixed_input_scope
        if self.fixed_input_id is not None:
            result['fixed_input'] = await self.evaluate(
                f"window.appAudioCapture.fixedInputState({self.fixed_input_id})")
        return result

    async def begin_fixed_input(self):
        if self.fixed_input_id is not None:
            raise RuntimeError('Fixed input source already registered')
        receipt = await self.evaluate(BEGIN_FIXED_INPUT)
        if (not isinstance(receipt, dict) or receipt.get('active') is not True
                or receipt.get('capture_started') is not False or receipt.get('owner') != 'core'
                or type(receipt.get('id')) is not int or receipt['id'] < 1
                or type(receipt.get('lease_generation')) is not int or receipt['lease_generation'] < 1
                or type(receipt.get('socket_id')) is not int or receipt['socket_id'] < 1
                or type(receipt.get('started_wall')) not in (int,float) or not receipt['started_wall']>0):
            raise RuntimeError('Fixed input controller registration failed')
        self.fixed_input_id = receipt['id']
        self.fixed_input_scope = {'ticket_id':receipt['id'],'socket_id':receipt['socket_id'],
                                 'started_wall':receipt['started_wall']}
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
