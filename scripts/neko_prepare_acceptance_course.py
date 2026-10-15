"""Prepare a fresh task course with Sky Scout pixels; no daily data or audio."""
from __future__ import annotations
import argparse
import asyncio
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess

import neko_desktop_tutor_host as host
from neko_daily_code_dialogue_probe import cleanup_probe_host
from neko_lab_client import LabClient
from neko_learning_surface import StudyPictureSnapshot
from neko_native_avatar_toolchain import call
from neko_relevant_history_probe import remember_children
from neko_tutor_start import plugin_server_ready, process_creation_time

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'benchmarks/raw'


def fresh_target(name, raw=RAW):
    if not re.fullmatch(r'neko-acceptance-[a-z0-9][a-z0-9-]{0,79}',name):
        raise ValueError('Use a new neko-acceptance-... task store name.')
    target=(raw/name).resolve()
    if target.parent!=raw.resolve() or target.exists():
        raise ValueError('Task store must be fresh; existing learning data is never changed.')
    return target


async def prepare(options):
    store=fresh_target(options.store)
    if not options.course_id.strip() or len(options.course_id)>1000:
        raise ValueError('A stable nonempty course ID is required.')
    output=RAW/'evidence'/(options.store+'-prepare.json')
    if output.exists():raise ValueError('Preserve previous evidence.')
    ledger=RAW/'neko-desktop-egress-cap'
    before=json.loads(ledger.read_text())
    spent=before['spent'].get('api.deepseek.com',0)
    if (before['round']!='bargein-autocheck-20261012' or not spent<options.deepseek_stop<=before['budgets']['api.deepseek.com']):
        raise ValueError('The explicit stop must be above spending and within the existing round/global cap.')
    for port in (48911,48916):
        with socket.socket() as check:
            if check.connect_ex(('127.0.0.1',port))==0:raise RuntimeError('An existing host owns the ports; leave it running.')
    image=RAW/'evidence/diagram-input-sky-dark.png'
    pixels=image.read_bytes()
    store.mkdir()
    data=store/'N.E.K.O/plugins/study_companion/data';data.mkdir(parents=True)
    grant=RAW/'neko-daily-companion/N.E.K.O/plugins/study_companion/data/code_project.json'
    if grant.is_file():shutil.copy2(grant,data/'code_project.json')
    (store/'task-provenance.json').write_text(json.dumps({'fresh':True,'purpose':'acceptance preparation','learning_database_copied':False}),encoding='utf-8')
    report={'before':before,'store':str(store),'course_id':options.course_id,'image_sha256':hashlib.sha256(pixels).hexdigest(),
            'audio':False,'capture':False,'loopback':False,'steps':[]}
    def save():output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    # Launch-local copy protects the original host log and the existing global ledger.
    original=ROOT/'scripts/neko_desktop_tutor_host.py'
    source=original.read_text(encoding='utf-8')
    root_anchor='ROOT = Path(__file__).resolve().parents[1]'
    log_anchor='ROOT / "benchmarks/raw/neko-desktop-host.log"'
    cap_anchor='return self.budgets.get(host)'
    if any(source.count(anchor)!=1 for anchor in (root_anchor,log_anchor,cap_anchor)):
        raise RuntimeError('Launcher anchors changed; preserve task store and inspect before launching.')
    task_log=store/'preparation-host.log'
    source=source.replace(root_anchor,f'ROOT = Path({str(ROOT)!r})')
    source=source.replace(log_anchor,f'Path({str(task_log)!r})')
    source=source.replace(cap_anchor,f'return min(self.budgets.get(host, 0), {options.deepseek_stop}) if host == ALLOWED_HOST else self.budgets.get(host)')
    launcher=store/'preparation-launcher.py'
    compile(source,str(launcher),'exec');launcher.write_text(source,encoding='utf-8')
    report['launcher_source_sha256']=hashlib.sha256(original.read_bytes()).hexdigest()
    save()
    handle=(store/'preparation-startup.log').open('xb')
    process=subprocess.Popen([str(host.SOURCE_PYTHON),'-B',str(launcher),'--source','--text-only','--study-vision',
        '--core-provider','deepseek','--store',store.name,'--hold','300','--seconds','90','--api-budget','12',
        '--egress-budget',str(int(before['budgets']['api.deepseek.com'])),'--budget-round',before['round']],
        cwd=ROOT,env={**os.environ,'PYTHONIOENCODING':'utf-8','PYTHONPATH':str(ROOT/'scripts'),'NEKO_TASK_SILENT':'1'},stdout=handle,stderr=subprocess.STDOUT)
    ownership=[{'pid':process.pid,'created_at':process_creation_time(process.pid)}]
    async def track():
        while process.poll() is None:
            remember_children(process,ownership)
            ownership[:]=list({(r['pid'],r['created_at']):r for r in ownership}.values())
            await asyncio.sleep(.5)
    tracker=asyncio.create_task(track())
    try:
        ready,reason=await asyncio.to_thread(plugin_server_ready,100,process)
        if not ready:raise RuntimeError(reason)
        for tool,args in [('study_session',{'action':'set_course','course_id':options.course_id}),
                          ('study_preferences',{'preferences':{'language':'zh-CN','length':'brief','proactive_quiz':False},'remember':True})]:
            result=await asyncio.to_thread(call,tool,args)
            report['steps'].append({'tool':tool,'result':result});save()
            if result.get('is_error') or result.get('output',{}).get('ok') is False:raise RuntimeError('Course setup refused')
        submitted=await asyncio.to_thread(LabClient().call,'study_submit_image',{
            'image_base64':base64.b64encode(pixels).decode(),'expected_course_id':options.course_id,
            'text':'这是本课的Sky Scout架构图。请根据实际图片简短确认主要模块和天气请求路线，不出题。'})
        report['image_submission']=submitted;save()
        payload=submitted.get('data',{})
        if submitted.get('error') or payload.get('ok') is False or payload.get('degraded'):raise RuntimeError('Image submission failed')
        material=await asyncio.to_thread(call,'study_material',{})
        report['role_material']=material
        saved,_=StudyPictureSnapshot(store).read();report['saved_picture']=saved
        if (not material.get('output',{}).get('picture_available') or material.get('output',{}).get('course_id')!=options.course_id or saved.get('course_id')!=options.course_id
                or saved.get('image_sha256')!=report['image_sha256']):raise RuntimeError('Submitted image identity not confirmed')
        report['ok']=True
    except Exception as error:
        report['failure']=f'{type(error).__name__}: {error}'
    finally:
        tracker.cancel();await asyncio.gather(tracker,return_exceptions=True)
        try:await asyncio.to_thread(cleanup_probe_host,process,ownership)
        except Exception as error:report['cleanup_error']=f'{type(error).__name__}: {error}'
        handle.close();report['after']=json.loads(ledger.read_text());save()
    print(json.dumps({'ok':report.get('ok',False),'failure':report.get('failure'),'course_id':options.course_id,
        'store':store.name,'evidence':str(output),'after':report['after']['spent']},ensure_ascii=False))
    return int(not report.get('ok') or bool(report.get('cleanup_error')))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--store',required=True)
    parser.add_argument('--course-id',required=True)
    parser.add_argument('--deepseek-stop',required=True,type=int,help='explicit cumulative stop; never raises or resets the ledger')
    raise SystemExit(asyncio.run(prepare(parser.parse_args())))
