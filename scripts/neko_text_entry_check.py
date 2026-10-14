"""Inspect only this test's Native debug port; reuse the existing Native E2E transport.

No Chrome profile, model request, capture API, or audio device is opened.
The launching caller owns the port and lifetime. Screenshot is the designated
learning renderer, not the desktop. UI readiness is separate from host readiness.
"""
import argparse,asyncio,json,time,urllib.request,urllib.parse
from pathlib import Path
import websockets
from neko_native_telemetry import NativeTelemetry

READ = r'''(() => {
const box=document.querySelector('.composer-input')||document.getElementById('textInputBox');
return {url:location.href,title:document.title,textOnly:globalThis.__NEKO_TEXT_ONLY__===true,
captureBlocked:globalThis.__NEKO_OUTPUT_ONLY_CAPTURE_BLOCKED__===true,
receipt:globalThis.NekoCapturePolicy?.getResult(),
inputVisible:!!box&&!!(box.offsetWidth||box.offsetHeight)&&getComputedStyle(box).visibility!=='hidden'&&getComputedStyle(box).display!=='none',
textSample:(document.body?.innerText||'').slice(0,300),
micVisible:[...document.querySelectorAll('#micButton,#live2d-btn-mic,#vrm-btn-mic,#mmd-btn-mic')].some(e=>!!(e.offsetWidth||e.offsetHeight))};
})()'''

async def check(port,output):
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    deadline=time.monotonic()+35
    rows=[]
    while time.monotonic()<deadline:
        try:
            with opener.open(f'http://127.0.0.1:{port}/json/list',timeout=5) as response:targets=json.load(response)
        except OSError:
            await asyncio.sleep(1)
            continue
        targets=[t for t in targets if t.get('type')=='page' and urllib.parse.urlsplit(t.get('url','')).hostname in ('localhost','127.0.0.1') and urllib.parse.urlsplit(t['url']).port==48911]
        rows=[]
        for target in targets:
            async with websockets.connect(target['webSocketDebuggerUrl'],proxy=None,max_size=8*1024*1024) as socket:
                observer=NativeTelemetry(socket)
                row=await observer.evaluate(READ)
                if row and row.get('inputVisible'):
                    await observer.screenshot(output.with_suffix('.png'))
                rows.append(row)
        if any(r and r.get('inputVisible') for r in rows):break
        await asyncio.sleep(1)
    passed=bool(rows) and any(r and r.get('inputVisible') for r in rows) and all(r and r.get('textOnly') and r.get('captureBlocked') and r.get('receipt',{}).get('status')=='installed' and len(r.get('receipt',{}).get('blocked',[]))==8 and not r.get('micVisible') for r in rows)
    result={'proof':'ACTUAL_TASK_NATIVE_TEXT_RENDERER_ONLY','passed':passed,'rows':rows,'model':False,'audio_devices':False,'human':False}
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))
    return 0 if passed else 1

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',required=True,type=int)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    raise SystemExit(asyncio.run(check(args.port,args.output)))
