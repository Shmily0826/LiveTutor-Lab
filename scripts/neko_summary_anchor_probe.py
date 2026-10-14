"""One focused real summary; preserved real QA plus explicitly offline neutral windows."""
from __future__ import annotations
import argparse,hashlib,json,logging,os,socket,sqlite3,subprocess,time
from pathlib import Path
import neko_desktop_tutor_host as host
from neko_daily_voice_probe import stop_owned_host
from neko_lab_client import LabClient
from neko_tutor_start import plugin_server_ready
from neko_summary_semantics_probe import snapshot

ROOT=Path(__file__).resolve().parents[1]
STORE=ROOT/'benchmarks/raw/neko-daily-speech-acceptance-20261014'
OUTPUT=ROOT/'benchmarks/raw/evidence/daily-companion-20261014-summary-anchor30.json'
LEDGER=ROOT/'benchmarks/raw/neko-desktop-egress-cap'
DB=STORE/'N.E.K.O/plugins/study_companion/data/study_companion.db'
FOCUS='只回顾更早那次我用英文回答左右箭头方向的题：用两句话说明我当时的错答、已有判分和下一步；明确这是此前的记录，忽略较晚那次中文回答及后来的源码讨论，不出新题。'
def digest(value):return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def state():
    with sqlite3.connect(DB.as_uri()+'?mode=ro',uri=True) as c:
        c.execute('PRAGMA query_only=ON')
        return json.loads(c.execute("SELECT value FROM kv WHERE key='state'").fetchone()[0])
def protected(value):
    return {k:v for k,v in value.items() if any(word in k for word in ('question','evaluation','preference','material','image','course'))}

def main():
    if OUTPUT.exists():raise RuntimeError('unique attempt only; preserve evidence')
    before=snapshot(DB);old=json.loads((ROOT/'benchmarks/raw/evidence/daily-companion-20261014-summary-continuity-quality19.json').read_text(encoding='utf-8'))['after_database']
    assert digest(before['interactions'][:len(old['interactions'])])==digest(old['interactions'])
    assert digest(before['qa'])==digest(old['qa']) and before['course_id']==old['course_id']
    for port in (host.MAIN_PORT,host.PLUGIN_PORT):
        with socket.socket() as check:
            if check.connect_ex(('127.0.0.1',port))==0:raise RuntimeError('existing host owns ports')
    report={'before':before,'before_ledger':json.loads(LEDGER.read_text(encoding='utf-8')),
            'audio':False,'native':False,'fixture_batch':'summary-anchor30-offline-v1','fixture_rows':[]}
    assert report['before_ledger']['round']=='bargein-autocheck-20261012'
    def save():OUTPUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    save();opened=time.time();log=OUTPUT.with_suffix('.host.log').open('xb')
    process=subprocess.Popen([str(host.SOURCE_PYTHON),'-X','utf8','-B',str(ROOT/'scripts/neko_desktop_tutor_host.py'),
        '--source','--core-provider','free','--summary-prompt-audit','--store',STORE.name,
        '--hold','300','--seconds','100','--api-budget','10','--egress-budget','2000',
        '--allow-host','www.lanlan.app:unlimited','--allow-host','www.lanlan.tech:0',
        '--budget-round','bargein-autocheck-20261012'],cwd=ROOT,
        env={**os.environ,'PYTHONIOENCODING':'utf-8','NEKO_TASK_SILENT':'1'},stdout=log,stderr=subprocess.STDOUT)
    report['host_launcher_pid']=process.pid;save()
    try:
        ready,reason=plugin_server_ready(100,process)
        if not ready:raise RuntimeError('host not ready: '+reason)
        baseline=snapshot(DB);baseline_state=protected(state())
        assert baseline['course_id']==before['course_id'] and digest(baseline['qa'])==digest(before['qa'])
        current=baseline['session_id'];prior=before['qa'][0][1]
        assert prior and prior!=current
        # Actual Store class; its ordinary append API, without a Core/Memory import.
        import test_neko_product_course_memory as product
        store=product.Store(DB,STORE/'unused-anchor-seed.json',logging.getLogger('anchor-fixture'))
        store.open()
        try:
            if store.load_config(product.models.build_config({})).history_limit < len(baseline['interactions'])+17:
                raise RuntimeError('retention cannot preserve the original prefix; do not append')
            # If the current window contains old teacher recap, isolate both windows.
            scopes=[prior]+([current] if any(row[6]==current for row in baseline['interactions']) else [])
            for target in scopes:
                for index in range(8):
                    ok=store.append_interaction(kind='concept_explain',input_text='',
                        output_text='这是一条离线教师窗口夹具，仅占用历史窗口，不表示学习者完成了任何学习行为。',
                        metadata={'test_fixture':'qa_anchor_teacher_window_v1','fixture_batch':report['fixture_batch'],
                                  'fixture_index':index+1,'source_scope':'offline_fixture','learner_progress':False},
                        session_id=target,history_limit=max(100,len(baseline['interactions'])+25))
                    if not ok:raise RuntimeError('fixture append not confirmed; no model')
                    report['fixture_rows'].append({'session_sha256':digest(target),'index':index+1});save()
        finally:store.close()
        prepared=snapshot(DB)
        assert digest(prepared['interactions'][:len(baseline['interactions'])])==digest(baseline['interactions'])
        assert digest(prepared['qa'])==digest(baseline['qa']) and protected(state())==baseline_state
        report['prepared']=prepared;report['protected_baseline_sha256']=digest(baseline_state);save()
        client=LabClient();report['call_started_wall']=time.time();save()
        report['result']=client.call('study_summarize_session',{'focus':FOCUS},timeout=120)
        report['call_completed_wall']=time.time();save()
        after=snapshot(DB);report['after']=after
        report['checks']={'old_prefix_unchanged':digest(after['interactions'][:len(before['interactions'])])==digest(before['interactions']),
                          'qa_unchanged':digest(after['qa'])==digest(before['qa']),
                          'protected_state_unchanged':protected(state())==baseline_state,
                          'expected_one_summary_append':len(after['interactions'])==len(prepared['interactions'])+1}
        audits=list((ROOT/'benchmarks/raw/evidence').glob('neko-product-api-*.jsonl'))
        report['actual_api_audits']=[]
        for path in audits:
            if path.stat().st_mtime<opened:continue
            rows=[json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line]
            if any(row.get('operation')=='summarize_session' for row in rows):
                report['actual_api_audits'].append({'path':str(path),'records':rows})
    except Exception as error:
        report['failure']=type(error).__name__+': '+str(error)
        report['observation_timeout']=isinstance(error,TimeoutError)
    finally:
        # An observation timeout is kept alive for a later poll of that same run.
        if not report.get('observation_timeout'):
            stop_owned_host(process);log.close();report['finalized']=True
        else:report['pending_owned_host']=process.pid
        report['after_ledger']=json.loads(LEDGER.read_text(encoding='utf-8'));save()
        print(json.dumps({'report':str(OUTPUT),'failure':report.get('failure'),'checks':report.get('checks'),
                          'fixtures':len(report['fixture_rows']),'spent':report['after_ledger']['spent']},ensure_ascii=False))
    return 1 if report.get('failure') or not all(report.get('checks',{}).values()) else 0

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();OUTPUT=args.output.resolve()
    if not OUTPUT.is_relative_to((ROOT/'benchmarks/raw/evidence').resolve()):raise RuntimeError('private evidence output only')
    raise SystemExit(main())
