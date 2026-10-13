"""Three actual character text turns; no source prefetch, audio or room microphone."""
import argparse
import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import subprocess
import time
from urllib.parse import quote
import websockets
from neko_daily_voice_probe import stop_owned_host
from neko_tutor_start import plugin_server_ready
from neko_lab_client import LabClient
import neko_desktop_tutor_host as host

ROOT = Path(__file__).resolve().parents[1]
QUESTIONS = [
    'Sky Scout 的主要模块怎么分？请先查已授权项目的实际结构，简短说明，再给一条值得接着学的路径。',
    '接着看 weather_service.dart：第17行是什么意思？和第16行有什么关系？先读实际源码，用两句中文讲，不出题。',
    '如果把这里的查询键改名，哪些地方需要核对？先查消费处的真实证据，简短说你确认了什么、哪些只是推断。',
]
CORRECTION = '你刚说 lat 和 lon 这两行“顺序不能调换”。是不是把调换 map 中的行顺序，与把键对应的纬度/经度值写反混淆了？请重新读取客户端以及 server/routes/weather.js 的实际行号，纠正错误，用两句中文答。'
FOLLOW_UPS = [
    '已经纠正过行顺序。再核对客户端第16、17行和 server/routes/weather.js 第8、9行：只交换 map 两行的位置、不改键和值，会改变服务端收到的坐标吗？两句短答，不出题。',
    '只讲漏掉一个查询键的影响。现在读取 server/routes/weather.js 及其坐标解析辅助函数，指出实际判断和 HTTP 返回；用两句短答，区分事实与没确认的影响。',
]


async def main(options):
    if options.output.exists(): raise RuntimeError('keep original evidence; new output only')
    for port in (48911,48916):
        with socket.socket() as check:
            if check.connect_ex(('127.0.0.1',port))==0: raise RuntimeError('existing host owns ports')
    ledger = ROOT/'benchmarks/raw/neko-desktop-egress-cap'
    report = {'started':datetime.now(timezone.utc).isoformat(), 'before':json.loads(ledger.read_text()),
              'turns':[], 'room_microphone':False, 'audio_started':False,
              'proof':'actual character brain via its existing text websocket; not textbox/DOM/device/human proof; no source prefetch'}
    assert report['before']['round']=='bargein-autocheck-20261012'
    log = ROOT/'benchmarks/raw/neko-desktop-host.log'
    log_start=log.stat().st_size if log.exists() else 0
    store=ROOT/'benchmarks/raw'/options.store
    assert store.resolve().is_relative_to((ROOT/'benchmarks/raw').resolve())
    core_path=store/'N.E.K.O/config/core_config.json'
    saved_core=json.loads(core_path.read_text(encoding='utf-8')).get('coreApi','free') if core_path.is_file() else 'free'
    receipts=list(store.rglob('code_evidence.jsonl'))
    sizes={str(p):p.stat().st_size for p in receipts}
    handle=options.output.with_suffix('.host.log').open('wb')
    process=subprocess.Popen([str(host.SOURCE_PYTHON),'-X','utf8',str(ROOT/'scripts/neko_desktop_tutor_host.py'),
        '--source','--core-provider','deepseek','--store',options.store,'--hold','380','--seconds','1','--api-budget','24',
        '--egress-budget','2000','--allow-host','www.lanlan.app:unlimited','--allow-host','www.lanlan.tech:0','--budget-round','bargein-autocheck-20261012'],
        cwd=ROOT,env={**os.environ,'PYTHONIOENCODING':'utf-8'},stdout=handle,stderr=subprocess.STDOUT)
    def save(): options.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    try:
        ready,reason=await asyncio.to_thread(plugin_server_ready,100,process)
        if not ready: raise RuntimeError('not ready: '+reason)
        report['host_ready']=True; report['owned_host_pid']=process.pid
        client=LabClient()
        report['study_state_before']=await asyncio.to_thread(client.call,'study_status')
        from urllib.request import build_opener,ProxyHandler
        opener=build_opener(ProxyHandler({}))
        with opener.open('http://127.0.0.1:48911/api/characters/current_catgirl',timeout=10) as response:
            character=json.load(response)['current_catgirl']
        print('Actual role text host ready; three questions, no source prefetch/audio',flush=True)
        async with websockets.connect('ws://127.0.0.1:48911/ws/'+quote(character),proxy=None,max_size=2*1024*1024) as ws:
            async def ping():
                while True:
                    await asyncio.sleep(5); await ws.send(json.dumps({'action':'ping'}))
            ping_task=asyncio.create_task(ping())
            try:
                await ws.send(json.dumps({'action':'start_session','input_type':'text','new_session':False,'request_id':'daily-code-text-ready'}))
                deadline=time.monotonic()+40
                while time.monotonic()<deadline:
                    event=json.loads(await asyncio.wait_for(ws.recv(),timeout=40))
                    if event.get('type')=='session_started': break
                    if event.get('type') in ('session_failed','session_ended_by_server'): raise RuntimeError('text session failed; no retry')
                else: raise RuntimeError('text session readiness timeout')
                questions = FOLLOW_UPS if options.follow_up_only else QUESTIONS + ([CORRECTION] if options.correction else [])
                for number,question in enumerate(questions,1):
                    turn={'number':number,'question':question,'sent_wall':time.time(),'events':[]}
                    report['turns'].append(turn); save()
                    await ws.send(json.dumps({'action':'stream_data','input_type':'text','data':question,'request_id':f'daily-code-text-{number}'},ensure_ascii=False))
                    deadline=time.monotonic()+100
                    while time.monotonic()<deadline:
                        frame=await asyncio.wait_for(ws.recv(),timeout=max(.1,deadline-time.monotonic()))
                        if isinstance(frame,bytes): raise RuntimeError('unexpected audio in text scene')
                        event=json.loads(frame); kind=event.get('type')
                        turn['events'].append({k:event[k] for k in ('type','text','data','error','status','message') if k in event}|{'wall':time.time()})
                        if kind=='error': raise RuntimeError('provider or core error; stop this route, no retry')
                        if kind in ('session_failed','session_ended_by_server'): raise RuntimeError('session failed; no retry')
                        if kind=='system' and event.get('data')=='turn end': break
                    else: raise RuntimeError('turn timeout; no replacement session')
                    turn['reply']=''.join(str(e.get('text') or '') for e in turn['events'] if e.get('type') in ('gemini_response','ai_response','text_response'))
                    turn['finished_wall']=time.time(); save()
                    print('Completed actual character text turn',number,flush=True)
                await ws.send(json.dumps({'action':'end_session','reason':'bounded_code_dialogue'}))
            finally:
                ping_task.cancel(); await asyncio.gather(ping_task,return_exceptions=True)
        report['study_state_after']=await asyncio.to_thread(client.call,'study_status')
    except Exception as error:
        report['failure']=type(error).__name__+': '+str(error)
    finally:
        await asyncio.to_thread(stop_owned_host,process);handle.close()
        report['after']=json.loads(ledger.read_text())
        report['owned_host_exit']=process.poll()
        if core_path.is_file():
            core=json.loads(core_path.read_text(encoding='utf-8'))
            if core.get('coreApi')=='deepseek':
                core['coreApi']=saved_core
                core_path.write_text(json.dumps(core,ensure_ascii=False,indent=2),encoding='utf-8')
                report['core_provider_restore']='restored only the prior coreApi field; keys/preferences/history retained'
            else:
                report['core_provider_restore']='kept a changed coreApi field'
        report['code_receipts']=[]
        for p in store.rglob('code_evidence.jsonl'):
            with p.open('rb') as read:
                read.seek(sizes.get(str(p),0))
                for line in read.read().decode('utf-8').splitlines():
                    report['code_receipts'].append(json.loads(line))
        if log.exists():
            with log.open('rb') as read:
                read.seek(log_start);lines=read.read().decode('utf-8',errors='replace').splitlines()
            report['tool_log']=[line for line in lines if 'TRIGGER entry=\'__llm_tool__study_' in line or 'study_code ' in line]
        report['semantics']='PENDING actual replies and receipts review; completed transport is not teaching acceptance'
        save()
        print(json.dumps({'report':str(options.output),'failure':report.get('failure'),'turns':len(report['turns']),'receipts':len(report['code_receipts']),'spent':report['after']['spent']},ensure_ascii=False),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--store',default='neko-daily-companion')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--correction',action='store_true',help='one additional explicit correction of the observed map-order error')
    parser.add_argument('--follow-up-only',action='store_true',help='two affected short follow-ups; do not repeat accepted structure round')
    asyncio.run(main(parser.parse_args()))
