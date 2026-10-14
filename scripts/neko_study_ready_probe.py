"""Inspect the complete Study bootstrap with the shared inspector and real local SDK.

Only the bootstrap promise is exposed for observation; no plugin result is mocked.
The relay permits a fixed set of local reading entries and never forwards model work.
"""
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import threading
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import build_opener, ProxyHandler, Request

import neko_desktop_tutor_host as host
from neko_daily_code_dialogue_probe import cleanup_probe_host
from neko_lab_client import LabClient
from neko_output_only_runtime import protected_html, POLICY_HEADERS
from neko_relevant_history_probe import remember_children
from neko_tutor_start import plugin_server_ready, process_creation_time

ROOT=Path(__file__).resolve().parents[1]
STORE=ROOT/'benchmarks/raw/neko-daily-material-window-20261015-54'
OUTPUT=ROOT/'benchmarks/raw/evidence/daily-companion-study-ready65.json'
BASE='http://127.0.0.1:48916'
UI='/plugin/study_companion/ui/'
ALLOWED={'study_status','__llm_tool__study_material','study_get_practice_scope',
         'study_question_context','study_memory_list_decks'}
PROVENANCE_HEADERS=('Content-Type','Origin','Referer','Cookie','X-CSRF-Token',
                    'Sec-Fetch-Site','Sec-Fetch-Mode','Sec-Fetch-Dest','Sec-Fetch-User')


def allowed_request(data):
    if data.get('plugin_id')!='study_companion' or data.get('entry_id') not in ALLOWED:return False
    args=data.get('args') or {}
    if not isinstance(args,dict):return False
    if data['entry_id']=='__llm_tool__study_material':
        return args.get('action','status')=='status' and set(args)<= {'action','locale'}
    if data['entry_id']=='study_memory_list_decks':
        return (set(args)<= {'locale','limit','offset'}
                and type(args.get('limit')) is int and args['limit']==100
                and type(args.get('offset')) is int and 0<=args['offset']<=10000)
    return set(args)<= {'locale'}


OBSERVER=r'''(async()=>{
const checks=[];let timer;
const check=(name,pass,detail)=>checks.push({name,pass:Boolean(pass),detail});
try {
 await Promise.race([globalThis.__phase54Bootstrap,new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('bootstrap deadline')),10000)})]);
 clearTimeout(timer);
 check('full bootstrap settled',Boolean(globalThis.__phase54Bootstrap));
 check('real service ready',studyServiceReady);
 check('capture policy installed',globalThis.__NEKO_OUTPUT_ONLY_CAPTURE_BLOCKED__===true);
 check('text mode',document.documentElement.dataset.nekoTextOnly==='true');
 const course=String(lastStatusPayload.study_course_id||lastStatusPayload.state?.study_course_id||'');
 check('course visible',course&&document.getElementById('selectedStudyCourse').textContent.includes(course),course);
 const previous=lastStatusPayload;
 const refresh=document.getElementById('refreshBtn');
 check('refresh control ready',refresh&&!refresh.disabled);
 refresh.click();
 for(let i=0;i<80&&(lastStatusPayload===previous||uiActionInFlight);i++)await new Promise(r=>setTimeout(r,50));
 check('real refresh completed',lastStatusPayload!==previous&&!uiActionInFlight&&studyServiceReady);
 check('same course after refresh',String(lastStatusPayload.study_course_id||lastStatusPayload.state?.study_course_id||'')===course);
 check('status finished',!/Refreshing|刷新中|Starting\.\.\./i.test(document.getElementById('statusLine').textContent),document.getElementById('statusLine').textContent);
}catch(error){checks.push({name:'observer failure',pass:false,detail:String(error)});}
finally{clearTimeout(timer);await fetch('/__phase54_result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(checks)});}
})();'''


def observed_main(source):
    marker='bootstrap().catch((error) => {'
    if source.count(marker)!=1:raise ValueError('bootstrap anchor changed; do not inspect an unknown variant')
    return source.replace(marker,'globalThis.__phase54Bootstrap = bootstrap();\nglobalThis.__phase54Bootstrap.catch((error) => {',1)


def qa_snapshot():
    db=STORE/'N.E.K.O/plugins/study_companion/data/study_companion.db'
    with sqlite3.connect(db.resolve().as_uri()+'?mode=ro',uri=True) as connection:
        connection.execute('PRAGMA query_only=ON')
        rows=connection.execute('SELECT * FROM qa_records ORDER BY id').fetchall()
    return {'count':len(rows),'sha256':hashlib.sha256(json.dumps(rows,ensure_ascii=False,sort_keys=True).encode()).hexdigest()}


class Relay(BaseHTTPRequestHandler):
    def log_message(self,*args):pass

    def reply(self,status,body,content_type='application/javascript; charset=utf-8'):
        self.send_response(status)
        self.send_header('Content-Type',content_type)
        self.send_header('Content-Length',str(len(body)))
        for key,value in {**POLICY_HEADERS,'X-LiveTutor-Audio-Mode':'text-only'}.items():self.send_header(key,value)
        self.end_headers();self.wfile.write(body)

    def do_GET(self):
        path=urlsplit(self.path).path
        if path=='/__phase54_observer.js':return self.reply(200,OBSERVER.encode())
        if path=='/__phase54_gate.js':
            self.server.done.wait(14)
            return self.reply(200,b'/* bounded observation gate released */')
        if path in (UI,UI+'index.html'):
            page=self.server.index.replace('</body>','<script src="/__phase54_observer.js"></script><script defer src="/__phase54_gate.js"></script></body>')
            page=protected_html(page,self.server.policy,text_only=True)
            return self.reply(200,page.encode(),'text/html; charset=utf-8')
        self.forward()

    def do_POST(self):
        length=int(self.headers.get('Content-Length','0'))
        if length<0 or length>1_000_000:return self.reply(413,b'{}','application/json')
        body=self.rfile.read(length)
        if self.path=='/__phase54_result':
            self.server.report['dom_checks']=json.loads(body)
            self.server.done.set()
            return self.reply(200,b'{}','application/json')
        if self.path!='/runs':return self.reply(403,b'{"error":"probe path refused"}','application/json')
        data=json.loads(body)
        entry=data.get('entry_id')
        if not allowed_request(data):
            self.server.report.setdefault('refused_entries',[]).append(str(entry))
            return self.reply(403,b'{"error":"probe permits reading entries only"}','application/json')
        self.server.report.setdefault('reading_entries',[]).append(entry)
        self.forward(body)

    def forward(self,body=None):
        parsed=urlsplit(self.path)
        if parsed.scheme or parsed.netloc or not self.path.startswith('/') or self.path.startswith('//'):
            return self.reply(403,b'{}','application/json')
        headers={key:self.headers[key] for key in PROVENANCE_HEADERS if key in self.headers}
        request=Request(BASE+self.path,data=body,headers=headers,method='POST' if body is not None else 'GET')
        try:
            response=self.server.opener.open(request,timeout=15)
        except HTTPError as error:response=error
        with response:
            payload=response.read();status=response.status;kind=response.headers.get('Content-Type','application/octet-stream')
        if status==200 and parsed.path=='/runs' and body is not None:
            run=json.loads(payload);name=json.loads(body)['entry_id']
            self.server.runs[str(run.get('run_id') or run.get('id'))]=name
        if status==200 and parsed.path.startswith('/runs/') and parsed.path.count('/')==2:
            run=json.loads(payload)
            if run.get('status') in ('succeeded','failed','canceled','timeout'):
                self.server.report.setdefault('completed_runs',{})[parsed.path.rsplit('/',1)[-1]]={
                    'entry':self.server.runs.get(parsed.path.rsplit('/',1)[-1]),'status':run['status']}
        if parsed.path==UI+'main.js' and status==200:
            self.server.report['main_original_sha256']=hashlib.sha256(payload).hexdigest()
            payload=observed_main(payload.decode('utf-8')).encode()
            self.server.report['main_observed_sha256']=hashlib.sha256(payload).hexdigest()
        self.reply(status,payload,kind)


def main():
    if OUTPUT.exists() or OUTPUT.with_suffix('.host.log').exists():raise ValueError('preserve prior scene evidence')
    if (not STORE.is_dir() or STORE.is_symlink()
            or STORE.resolve().parent!=(ROOT/'benchmarks/raw').resolve()):
        raise ValueError('existing contained task54 store required; never create substitute learner data')
    for port in (48911,48916,9234):
        with socket.socket() as probe:
            probe.settimeout(.2)
            if probe.connect_ex(('127.0.0.1',port))==0:raise ValueError('existing host owns the port')
    ledger=ROOT/'benchmarks/raw/neko-desktop-egress-cap'
    before=json.loads(ledger.read_text());assert before['round']=='bargein-autocheck-20261012'
    core=json.loads((STORE/'N.E.K.O/config/core_config.json').read_text()).get('coreApi')
    if core not in ('free','deepseek'):raise ValueError('preserve unknown task provider')
    report={'before':before,'audio':False,'microphone':False,'capture':False,'loopback':False,
            'proof':'real complete Study bootstrap/SDK in shared headless inspector through a reading-only local relay; bootstrap promise observed, not mocked; not physical user Chrome/Native/model/human'}
    def save():OUTPUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    with OUTPUT.open('x',encoding='utf-8') as stream:json.dump(report,stream)
    report['qa_before_start']=qa_snapshot();save()
    server=ThreadingHTTPServer(('127.0.0.1',0),Relay)
    server.report=report;server.runs={};server.done=threading.Event();server.opener=build_opener(ProxyHandler({}))
    # The backend explicitly supports a custom frontend origin; never forge or strip browser provenance.
    frontend_origin=f'http://127.0.0.1:{server.server_port}'
    report['configured_frontend_origin']=frontend_origin
    server.index=(host.PRODUCT/'static/index.html').read_text(encoding='utf-8')
    server.policy=(ROOT/'scripts/neko_capture_policy.js').read_text(encoding='utf-8')
    threading.Thread(target=server.serve_forever,daemon=True).start()
    handle=OUTPUT.with_suffix('.host.log').open('xb');ownership=[];roots=[];lock=threading.RLock();stop=threading.Event();tracker=None;process=None;inspector=None
    try:
        process=subprocess.Popen([str(host.SOURCE_PYTHON),'-X','utf8','-B',str(ROOT/'scripts/neko_desktop_tutor_host.py'),
            '--source','--core-provider','deepseek','--store',STORE.name,'--text-only','--offline-egress',
            '--hold','180','--api-budget','0','--egress-budget','2000','--budget-round','bargein-autocheck-20261012'],
            cwd=ROOT,env={**os.environ,'NEKO_TASK_SILENT':'1','PYTHONIOENCODING':'utf-8',
                          'NEKO_PLUGIN_MUTATION_ALLOWED_ORIGINS':frontend_origin},stdout=handle,stderr=subprocess.STDOUT)
        created=process_creation_time(process.pid)
        if created is None:raise RuntimeError('launcher identity unavailable')
        ownership.append({'pid':process.pid,'created_at':created});report['ownership']=ownership;save()
        roots.append(process)
        def track():
            try:
                while not stop.wait(.25):
                    with lock:
                        for root in roots:
                            if root.poll() is None:remember_children(root,ownership)
                        ownership[:]=list({(x['pid'],x['created_at']):x for x in ownership}.values())
            except Exception as error:report['tracker_error']=type(error).__name__+': '+str(error)
        tracker=threading.Thread(target=track,daemon=True);tracker.start()
        ready,reason=plugin_server_ready(90,process)
        if not ready:raise RuntimeError(reason)
        print('Actual read-only Study host ready; no model/audio/capture',flush=True)
        client=LabClient();report['status_before']=client.call('study_status');report['qa_before']=qa_snapshot();save()
        target=f'http://127.0.0.1:{server.server_port}'+UI
        inspector=subprocess.Popen(['node',r'D:\AI\tools\web-inspector\cli.mjs',target,'--json','--screenshot'],
                                   cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8')
        created=process_creation_time(inspector.pid)
        if created is None:raise RuntimeError('inspector identity unavailable')
        with lock:
            ownership.append({'pid':inspector.pid,'created_at':created});roots.append(inspector)
        stdout,stderr=inspector.communicate(timeout=35)
        report['inspector_exit']=inspector.returncode
        report['inspector_stderr']=stderr[:1000]
        report['inspector']=json.loads(stdout)
        assert all(view['success'] and not view['pageErrors'] and not view['consoleErrors']
                   and not view['failedRequests'] for view in report['inspector']['results']),'browser reported failures'
        assert report['main_original_sha256']==hashlib.sha256((host.PRODUCT/'static/main.js').read_bytes()).hexdigest(),'served main differs from current source'
        report['qa_after']=qa_snapshot();report['status_after']=client.call('study_status')
        assert report['qa_before_start']==report['qa_before']==report['qa_after'],'task QA changed'
        assert inspector.returncode==0,'inspector failed'
        assert report.get('dom_checks') and all(c['pass'] for c in report['dom_checks']),report.get('dom_checks')
        assert not report.get('refused_entries'),'unexpected entry requested'
        assert report.get('completed_runs') and all(run['status']=='succeeded' for run in report['completed_runs'].values()),'a reading run failed'
        assert set(server.runs)==set(report['completed_runs']),'a reading run was not observed to finish'
        report['result']='PASS: complete bootstrap/real refresh/text protection; QA unchanged'
    except Exception as error:
        report['failure']=type(error).__name__+': '+str(error)
    finally:
        server.done.set();stop.set()
        if tracker is not None:tracker.join(timeout=2)
        if process is not None:
            try:cleanup_probe_host(process,ownership)
            except Exception as error:report['cleanup_error']=str(error)
            report['owned_host_exit']=process.poll()
        if inspector is not None:
            try:inspector.wait(timeout=10)
            except subprocess.TimeoutExpired:report['cleanup_error']='inspector still running after owned cleanup'
        handle.close();server.shutdown();server.server_close()
        report['qa_final']=qa_snapshot()
        if report['qa_final']!=report['qa_before_start']:report['failure']='task QA changed'
        report['relay_port']=server.server_port;report['after']=json.loads(ledger.read_text())
        if process is not None and process.poll() is not None:
            config_path=STORE/'N.E.K.O/config/core_config.json'
            current=json.loads(config_path.read_text(encoding='utf-8'))
            if current.get('coreApi')=='deepseek':
                current['coreApi']=core
                config_path.write_text(json.dumps(current,ensure_ascii=False,indent=2),encoding='utf-8')
                report['task_core_provider_restored']=True
            else:report['config_error']='task provider changed unexpectedly; preserved'
        if report['after']!=before:report['budget_error']='original ledger changed'
        save()
    print(json.dumps({'output':str(OUTPUT),'result':report.get('result'),'failure':report.get('failure'),
                      'cleanup_error':report.get('cleanup_error'),'spent':report['after']['spent']},ensure_ascii=False),flush=True)
    return 1 if any(report.get(k) for k in ('failure','cleanup_error','tracker_error','budget_error','config_error')) else 0


if __name__=='__main__':raise SystemExit(main())
