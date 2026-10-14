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
const trace = {events:[],binaryFrames:0,binaryBytes:0,installedAt:Date.now()/1000};
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
   if(p.type==='audio_chunk'){event.correlation_id=p.sdk_speech_correlation_id;trace.lastNativeCorrelation=p.sdk_speech_correlation_id;}
   if(p.type==='game_route_speech_cancel')event.correlation_id=p.sdk_speech_correlation_id;
   put(event);
  } catch {}
 });
 const send = socket.send.bind(socket);
 socket.send = data => { try { const p=JSON.parse(data); if(['native_speech_playback_state','playback_feedback','audio_playback_feedback','speech_playback_feedback'].includes(p.action)) { const event={direction:'send',type:p.action};for(const key of ['active','audible','speech_id','turn_id','correlation_id','sdk_speech_correlation_id','stage','status','reason']) if(key in p)event[key]=p[key];put(event); }}catch{} return send(data); };
};
install();trace.timer=setInterval(install,100);
return {installed:true,socketReady:window.appState?.socket?.readyState,url:location.href,wall:Date.now()/1000};
})()"""

SNAPSHOT = r"""(() => {
const trace=window.__dailyNativeTelemetry;
const rows=[...document.querySelectorAll('.message-bubble,.message-text,.message-content')].map(e=>({text:(e.innerText||'').trim(),className:e.className,visible:!!(e.offsetWidth||e.offsetHeight)})).filter(e=>e.text);
return {wall:Date.now()/1000,url:location.href,title:document.title,trace:trace?{events:trace.events,binaryFrames:trace.binaryFrames,binaryBytes:trace.binaryBytes,installedAt:trace.installedAt}:null,playback:window.NekoSpeechPlaybackState||null,bubbles:rows.slice(-40)};
})()"""


class NativeTelemetry:
    def __init__(self, socket):
        self.socket = socket
        self.counter = 0
        self.lock = asyncio.Lock()

    @classmethod
    async def attach(cls, port):
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(f"http://127.0.0.1:{port}/json/list", timeout=5) as response:
            targets = json.load(response)
        # This port was allocated for this test's native launch; never query Chrome.
        targets = [t for t in targets if t.get("type") == "page" and
                   urllib.parse.urlsplit(t.get("url", "")).hostname in {"127.0.0.1", "localhost"} and
                   urllib.parse.urlsplit(t.get("url", "")).port == 48911]
        # Electron's pet renderer owns PCM; chat windows proxy text only.
        targets.sort(key=lambda t: ("chat" in t["url"], t["url"]))
        if not targets:
            raise RuntimeError("task native renderer not available on the allocated debug port")
        for target in targets:
            socket = await websockets.connect(target["webSocketDebuggerUrl"], proxy=None, max_size=8*1024*1024)
            observer = cls(socket)
            probe = await observer.evaluate("({socketReady:window.appState?.socket?.readyState,audioPlaybackAvailable:!!window.appAudioPlayback})")
            if probe and probe.get("socketReady") == 1 and probe.get("audioPlaybackAvailable"):
                await observer.evaluate(INSTALL)
                return observer
            await socket.close()
        raise RuntimeError("task native audio renderer has no ready playback socket")

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
        return await self.evaluate(SNAPSHOT)

    async def send_current(self, payload):
        """Fixed test input on this renderer's own controller, never the superseded socket."""
        encoded = json.dumps(payload, ensure_ascii=True)
        result = await self.evaluate("(() => {const s=window.appState?.socket;"
            "if(!s || s.readyState!==1)throw new Error('Native controller unavailable');"
            "s.send(JSON.stringify(" + encoded + "));return true;})()")
        if result is not True:
            raise RuntimeError('Native controller did not accept fixed input')

    async def screenshot(self, path):
        result = await self.command("Page.captureScreenshot", {"format": "png"})
        Path(path).write_bytes(base64.b64decode(result["data"]))

    async def close(self):
        try:
            await self.evaluate("if(window.__dailyNativeTelemetry)clearInterval(window.__dailyNativeTelemetry.timer)")
        finally:
            await self.socket.close()
