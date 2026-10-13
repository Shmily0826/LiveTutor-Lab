"""Actual authorized CodeGraph callback -> filtered surface -> Study point -> DOM.

No audio, room microphone, supplier reconnect or learner source modification.
"""
import argparse
import base64
import hashlib
import json
import os
import re
from pathlib import Path
import socket
import subprocess
import threading
from urllib.parse import urlsplit
from neko_learning_surface import LearningSurface, SurfaceHandler, DEFAULT_MATERIALS
from neko_native_avatar_toolchain import call
from neko_tutor_start import plugin_server_ready
from neko_daily_voice_probe import stop_owned_host
from neko_lab_client import LabClient
import neko_desktop_tutor_host as host

ROOT = Path(__file__).resolve().parents[1]
CHECK = r'''<script>
(async()=>{const checks=[];const wait=async f=>{for(let i=0;i<100;i++){if(f())return;await new Promise(r=>setTimeout(r,50))}throw Error('timed out')};try{
const client=window.learningSurface;await wait(()=>client.ready);
const select=document.getElementById('materials');select.value=__CODE_ID__;select.dispatchEvent(new Event('change'));
await wait(()=>client.ready&&client.material.id===__CODE_ID__);
checks.push({name:'actual source visible',pass:document.getElementById('frame').contentDocument.body.innerText.includes('fetchWeather')});
// The learner moves the material; the tutor's callback only points.
const line=[...document.getElementById('frame').contentDocument.querySelectorAll('[data-line]')].find(e=>/^\d+\s/.test(e.textContent)&&e.textContent.includes('fetchWeather'));
line?.scrollIntoView({block:'center',inline:'center',behavior:'instant'});
const pointed=await fetch('/probe-point',{method:'POST'}).then(r=>r.json());
await wait(()=>client.command&&client.geometry());client.draw();
checks.push({name:'actual Study callback pointer visible',pass:!document.getElementById('marks').hasAttribute('hidden')&&client.command.selector===pointed.selector});
}catch(error){checks.push({name:String(error),pass:false})}await fetch('/probe-result',{method:'POST',body:JSON.stringify(checks)})})();
</script><script defer src="/probe-done.js"></script>'''


class ProbeHandler(SurfaceHandler):
    def do_GET(self):
        if self.path == '/':
            page = (ROOT/'scripts/neko_learning_surface.html').read_text(encoding='utf-8').replace('__BOOTSTRAP__',json.dumps({'token':self.server.token}))
            check = CHECK.replace('__CODE_ID__',json.dumps(self.server.code_id))
            self.reply(200,page.replace('</html>',check+'</html>').encode(),'text/html; charset=utf-8')
        elif self.path == '/probe-done.js':
            self.server.done.wait(15);self.reply(200,b'/* done */','application/javascript')
        else: super().do_GET()

    def do_POST(self):
        if self.path == '/probe-point':
            status = call('study_point',{'kind':'status'})
            self.server.report['point_status'] = status
            targets = (status.get('output',{}).get('material') or {}).get('targets_for_pointing',[])
            selected = next((t for t in targets if 'fetchWeather' in t.get('label','') and re.match(r'^\d+\s',t.get('label',''))),None)
            if not selected: raise RuntimeError('no returned source target for fetchWeather')
            selector = selected['selector']
            result = call('study_point',{'material_id':self.server.code_id,'kind':'selector','selector':selector,'label':'当前版本的 fetchWeather 源码'})
            self.server.report['point_callback'] = result
            self.reply(200,{'selector':selector,'callback':result})
        elif self.path == '/probe-result':
            self.server.report['browser_checks'] = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            self.server.done.set();self.reply(200,{'ok':True})
        else: super().do_POST()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--verify-image-guard',action='store_true',help='one real vision call after the changed image entry; preserves existing course')
    args=parser.parse_args()
    if args.output.exists(): raise RuntimeError('preserve previous probe evidence')
    for port in (host.MAIN_PORT,host.PLUGIN_PORT):
        with socket.socket() as probe:
            if probe.connect_ex(('127.0.0.1',port))==0:raise RuntimeError('existing host owns ports')
    ledger=ROOT/'benchmarks/raw/neko-desktop-egress-cap'
    report={'before':json.loads(ledger.read_text()),'proof':'actual CLI/callback/DOM integration; no new role-selection, model, playback or human claim'}
    assert report['before']['round']=='bargein-autocheck-20261012'
    server=LearningSurface([p for p in DEFAULT_MATERIALS if p.is_file()],0);server.RequestHandlerClass=ProbeHandler;server.report=report;server.done=threading.Event()
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    env={**os.environ,'PYTHONIOENCODING':'utf-8','NEKO_LEARNING_SURFACE_URL':f'http://127.0.0.1:{server.server_port}','NEKO_LEARNING_SURFACE_TOKEN':server.token}
    handle=args.output.with_suffix('.host.log').open('wb')
    process=subprocess.Popen([str(host.SOURCE_PYTHON),'-X','utf8',str(ROOT/'scripts/neko_desktop_tutor_host.py'),'--source','--core-provider','free','--store','neko-daily-acceptance-20261014','--hold','180','--api-budget','10','--egress-budget','2000','--budget-round','bargein-autocheck-20261012','--allow-host','www.lanlan.app:unlimited','--allow-host','www.lanlan.tech:0','--study-vision'],cwd=ROOT,env=env,stdout=handle,stderr=subprocess.STDOUT)
    try:
        ready,reason=plugin_server_ready(100,process)
        if not ready:raise RuntimeError(reason)
        if args.verify_image_guard:
            client=LabClient();status=client.call('study_status')['data']
            course=str(status.get('study_course_id') or status.get('state',{}).get('study_course_id') or '')
            if not course:raise RuntimeError('no existing acceptance course; do not invent a new one')
            image=ROOT/'benchmarks/raw/evidence/diagram-input-sky-dark.png'
            fields={'image_base64':base64.b64encode(image.read_bytes()).decode(),'text':'用两句话解释图中天气请求的主要方向。不出题；看不清就说明。','expected_course_id':course+'-stale'}
            spent_before=json.loads(ledger.read_text())['spent']
            try:client.call('study_submit_image',fields);raise AssertionError('stale course image accepted')
            except RuntimeError as error:
                if '课程已切换' not in str(error):raise
                report['stale_image_refusal']=str(error)
            assert json.loads(ledger.read_text())['spent']==spent_before
            fields['expected_course_id']=course
            report['current_image_reply']=client.call('study_submit_image',fields)
            report['input_image_sha256']=hashlib.sha256(image.read_bytes()).hexdigest()
            if report['current_image_reply']['data'].get('degraded'):raise RuntimeError('real current image call degraded')
            report['proof']='actual changed image entry: stale course refusal with no paid request, current course real vision/API/DB; no playback or human claim'
            return
        result=call('study_code',{'mode':'explore','query':'WeatherService fetchWeather in weather_service.dart: show actual request construction and HTTP response handling'})
        report['code_callback']=result;data=result.get('output',{})
        if result.get('is_error') or not data.get('ok') or not data.get('shown'):raise RuntimeError('actual authorized source unavailable')
        publication=data.get('learning_surface') or {}
        if not publication.get('available'):raise RuntimeError('filtered code surface publication failed')
        server.code_id=publication['material_id']
        run=subprocess.run(['node',r'D:\AI\tools\web-inspector\cli.mjs',f'http://127.0.0.1:{server.server_port}/','--desktop','--screenshot','--json'],capture_output=True,text=True,encoding='utf-8',timeout=35)
        report['inspector']=json.loads(run.stdout)
        if run.returncode or not report.get('browser_checks') or not all(c['pass'] for c in report['browser_checks']):raise RuntimeError('actual browser callback pointer not verified')
    except Exception as error:report['failure']=type(error).__name__+': '+str(error)
    finally:
        stop_owned_host(process);handle.close();server.done.set();server.shutdown();server.server_close();thread.join(timeout=3)
        report['after']=json.loads(ledger.read_text());args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({'evidence':str(args.output),'failure':report.get('failure'),'checks':report.get('browser_checks'),'spent':report['after']['spent']},ensure_ascii=False))


if __name__=='__main__':main()
