"""One offline-relay Native control diagnostic; no session start, PCM or capture."""
from __future__ import annotations
import argparse, asyncio, json, os, socket, subprocess, time
from pathlib import Path
import neko_desktop_tutor_host as host
import neko_native_shell as avatar
from neko_native_telemetry import NativeTelemetry
from neko_daily_voice_probe import stop_owned_host
from neko_tutor_start import plugin_server_ready

ROOT=Path(__file__).resolve().parents[1]

async def run(output, store_name):
    host.require_task_speaker_output_allowed('capture-blocked Native control diagnostic')
    if output.exists():raise RuntimeError('do not overwrite diagnostic evidence')
    for port in (host.MAIN_PORT,host.PLUGIN_PORT):
        with socket.socket() as check:
            if check.connect_ex(('127.0.0.1',port))==0:raise RuntimeError('existing host owns ports; leave it alone')
    ledger=ROOT/'benchmarks/raw/neko-desktop-egress-cap';original=ledger.read_bytes()
    before=json.loads(original)
    if before.get('round')!='bargein-autocheck-20261012':raise RuntimeError('ledger round differs; do not reset')
    store=(ROOT/'benchmarks/raw'/store_name).resolve()
    if (not store.is_relative_to((ROOT/'benchmarks/raw').resolve()) or not store.is_dir()
            or not store.name.startswith('neko-daily-silent-vision-')):
        raise RuntimeError('use an existing isolated task fixture; no new store or user history copy')
    report={'before':before,'capture_devices':False,'loopback':False,'volume_changed':False,
            'session_start_sent':False,'pcm_sent':False,'snapshots':[]}
    output.parent.mkdir(parents=True,exist_ok=True)
    log=output.with_suffix('.host.log').open('xb');native=None;observer=None
    process=subprocess.Popen([str(host.SOURCE_PYTHON),'-X','utf8','-B',str(ROOT/'scripts/neko_desktop_tutor_host.py'),
        '--source','--voice','--output-only','--offline-egress','--core-provider','free','--store',store.name,
        '--hold','180','--seconds','100','--api-budget','0','--egress-budget','2000',
        '--allow-host','www.lanlan.app:unlimited','--allow-host','www.lanlan.tech:0',
        '--budget-round','bargein-autocheck-20261012'],cwd=ROOT,env={**os.environ,'PYTHONIOENCODING':'utf-8'},
        stdout=log,stderr=subprocess.STDOUT)
    report['host_launcher_pid']=process.pid
    def save():output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    try:
        ready,reason=await asyncio.to_thread(plugin_server_ready,100,process)
        if not ready:raise RuntimeError('host not ready: '+reason)
        with socket.socket() as allocation:
            allocation.bind(('127.0.0.1',0));port=allocation.getsockname()[1]
        native=await asyncio.to_thread(avatar.launch,store,90,'compact',port,None,True)
        report['native_pid']=native['pid'];await asyncio.sleep(4)
        deadline=time.monotonic()+25
        while observer is None:
            try:observer=await NativeTelemetry.attach(port)
            except RuntimeError as error:
                if str(error) not in ('task native audio renderer has no ready playback socket',
                                     'task native renderer not available on the allocated debug port'):
                    raise
                if time.monotonic()>=deadline:raise
                # Poll only this still-owned renderer; do not launch another shell.
                await asyncio.sleep(.5)
        report['capture_policy']=await observer.evaluate('({receipt:NekoCapturePolicy.getResult(),blocked:__NEKO_OUTPUT_ONLY_CAPTURE_BLOCKED__===true})')
        if not report['capture_policy']['blocked'] or report['capture_policy']['receipt']['status']!='installed':
            raise RuntimeError('capture protection not installed')
        report['surface']=await observer.evaluate('({url:location.href,socketConstructor:appState.socket.constructor.name,socketURL:appState.socket.url,socketReady:appState.socket.readyState})')
        report['source']=await observer.begin_fixed_input();save()
        for _ in range(48):
            snapshot=await observer.snapshot();snapshot.pop('bubbles',None)
            report['snapshots'].append(snapshot);save()
            if ledger.read_bytes()!=original:raise RuntimeError('unexpected ledger change; stop diagnostic')
            await asyncio.sleep(.25)
        report['release']=await observer.end_fixed_input()
        snapshot=await observer.snapshot();snapshot.pop('bubbles',None);report['snapshots'].append(snapshot)
    except Exception as error:
        report['failure']=type(error).__name__+': '+str(error)
    finally:
        if observer:
            try:report['cleanup_release']=await observer.end_fixed_input();await observer.close()
            except Exception as error:report['cleanup_error']=type(error).__name__
        if native:avatar.shutdown(native)
        await asyncio.to_thread(stop_owned_host,process);log.close()
        report['after']=json.loads(ledger.read_text(encoding='utf-8'))
        report['ledger_bytes_unchanged']=ledger.read_bytes()==original
        report['finalized']=True;save()
        print(json.dumps({'report':str(output),'failure':report.get('failure'),
            'ledger_bytes_unchanged':report['ledger_bytes_unchanged'],'source':report.get('source')},ensure_ascii=False))
    return 1 if report.get('failure') or not report['ledger_bytes_unchanged'] else 0

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--store',default='neko-daily-silent-vision-20261014-recheck21')
    args=parser.parse_args();raise SystemExit(asyncio.run(run(args.output,args.store)))
