"""One real direct SDK grade after startup, with an existing English course.

Never call an avatar/language/course-selection tool before the measured grade.
Reuse owned scene41/45 materials and preserve original records. No audio or UI.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import time

from neko_question_topic_probe import ROOT, STORE, LEDGER, snapshot
import neko_desktop_tutor_host as host
from neko_daily_voice_probe import stop_owned_host
from neko_lab_client import LabClient
from neko_tutor_start import plugin_server_ready


def main(output):
    output=output.resolve()
    if output.exists() or output.parent!=(ROOT/'benchmarks/raw/evidence').resolve():
        raise ValueError('new task evidence output required')
    db=ROOT/'benchmarks/raw'/STORE/'N.E.K.O/plugins/study_companion/data/study_companion.db'
    before=snapshot(db);old=before['tables'];rows=old['qa_records']
    if len(rows)!=7 or before['question']!={} or before['language_by_course'].get(before['course'])!='en-US':
        raise RuntimeError('existing owned scene45 state required; do not reset or create history')
    artifact=json.loads(rows[-1]['question']);topic=rows[-1]['topic_id']
    assert json.loads(rows[-2]['question'])['internal_private_payload']['learning_topic_binding']['key']==artifact['internal_private_payload']['learning_topic_binding']['key']
    ledger=json.loads(LEDGER.read_text(encoding='utf-8'))
    assert ledger['round']=='bargein-autocheck-20261012'
    assert ledger['budgets']=={'api.deepseek.com':2000.0,'www.lanlan.app':None,'www.lanlan.tech':0.0}
    assert ledger['spent'].get('api.deepseek.com',0)<2000
    manifest_path=ROOT/'patches/neko-study-2026-10-10-product/manifest.json'
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'));fingerprints={}
    for item in manifest['files']:
        source=manifest_path.parent/item['path']
        target=ROOT/manifest['deployment']/item['path'].removeprefix('payload/study_companion/')
        actual=hashlib.sha256(source.read_bytes()).hexdigest();assert actual==item['sha256']
        expected=(item['protected_deployed_sha256'] if item['path']=='static/index.html'
                  and item.get('protected_deployed_matches') is True else actual)
        assert hashlib.sha256(target.read_bytes()).hexdigest()==expected
        fingerprints[item['path']]=actual
    host.verify_source_audio_gate()
    for port in (host.MAIN_PORT,host.PLUGIN_PORT):
        with socket.socket() as probe:
            if probe.connect_ex(('127.0.0.1',port))==0:raise RuntimeError('preserve existing host')
    report={'store':STORE,'before':ledger,'before_snapshot':before,'source_sha256':fingerprints,
            'audio':False,'avatar':False,'microphone':False,'capture':False,'loopback':False,
            'scope':'one actual direct Study grade after startup; no language/course/avatar priming or device/human proof'}
    def save():output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with output.open('x',encoding='utf-8') as file:file.write(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    process=None;log=None
    try:
        log=output.with_suffix('.host.log').open('xb')
        process=subprocess.Popen([str(host.SOURCE_PYTHON),'-X','utf8','-B',str(ROOT/'scripts/neko_desktop_tutor_host.py'),
            '--source','--text-only','--core-provider','free','--store',STORE,'--hold','180',
            '--api-budget','2','--egress-budget','2000','--allow-host','www.lanlan.app:unlimited',
            '--allow-host','www.lanlan.tech:0','--budget-round','bargein-autocheck-20261012'],cwd=ROOT,
            env={**os.environ,'NEKO_TASK_SILENT':'1','PYTHONIOENCODING':'utf-8'},stdout=log,stderr=subprocess.STDOUT)
        report['launcher_pid']=process.pid;save()
        ready,reason=plugin_server_ready(85,process)
        if not ready:raise RuntimeError('host unavailable: '+reason)
        report['started_wall']=time.time();save()
        report['grade']=LabClient().call('study_evaluate_answer',{'question':artifact['question'],
            'expected_answer':artifact['answer'],'answer':'WEX 指向 NUD。'},timeout=110)
        report['completed_wall']=time.time();save()
        result=report['grade']['data']
        if result.get('degraded') or result.get('ok') is False:raise RuntimeError('grade unavailable; no retry')
        after=snapshot(db);report['after_snapshot']=after;new=after['tables']
        report['checks']={
            'one_grade':len(new['qa_records'])==len(rows)+1,
            'same_bound_question_identity':new['qa_records'][-1]['topic_id']==topic,
            'old_qa_mastery_interactions_preserved':all(new[name][:len(old[name])]==old[name] for name in ('qa_records','mastery_snapshots','interactions')),
            'one_new_mastery':len(new['mastery_snapshots'])==len(old['mastery_snapshots'])+1,
            'one_new_formal_grade':sum(row['kind']=='answer_evaluate' for row in new['interactions'])==sum(row['kind']=='answer_evaluate' for row in old['interactions'])+1,
            'no_new_fsrs_identity':{row['topic_id'] for row in new['fsrs_cards']}=={row['topic_id'] for row in old['fsrs_cards']},
            'same_course_and_saved_english':after['course']==before['course'] and after['language_by_course']==before['language_by_course'],
            'no_synthetic_pending':after['question']==before['question']=={},
        }
    except Exception as error:report['failure']=type(error).__name__+': '+str(error)
    finally:
        if process is not None:
            try:stop_owned_host(process);report['host_exit']=process.poll()
            except Exception as error:report['cleanup_error']=str(error)
        if log is not None:log.close()
        report['after']=json.loads(LEDGER.read_text(encoding='utf-8'));report['finalized']=True;save()
        print(json.dumps({'report':str(output),'failure':report.get('failure'),'cleanup_error':report.get('cleanup_error'),
                          'checks':report.get('checks'),'spent':report['after']['spent']},ensure_ascii=False),flush=True)
    return 1 if report.get('failure') or report.get('cleanup_error') or not all(report.get('checks',{}).values()) else 0


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    raise SystemExit(main(parser.parse_args().output))
