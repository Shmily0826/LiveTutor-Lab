"""Two bounded real grades across restart on the existing owned scene41 history.

Text only. No synthetic pending question, history rewrite, audio or capture.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import time

import neko_desktop_tutor_host as host
from neko_daily_voice_probe import stop_owned_host
from neko_lab_client import LabClient
from neko_tutor_start import plugin_server_ready

ROOT = Path(__file__).resolve().parents[1]
STORE = 'neko-daily-semantics-20261015-41'
LEDGER = ROOT / 'benchmarks/raw/neko-desktop-egress-cap'
TABLES = ('qa_records', 'mastery_snapshots', 'fsrs_cards', 'interactions')


def snapshot(db):
    with sqlite3.connect(db.resolve().as_uri()+'?mode=ro', uri=True) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute('PRAGMA query_only=ON')
        state = json.loads(connection.execute("SELECT value FROM kv WHERE key='state'").fetchone()[0])
        tables = {name: [dict(row) for row in connection.execute('SELECT * FROM '+name+' ORDER BY rowid')]
                  for name in TABLES}
        return {'course': state['study_course_id'], 'question': state.get('current_question'),
                'language_by_course': state.get('teaching_language_by_course'), 'tables': tables}


def main(output):
    output = output.resolve()
    if output.exists() or output.parent != (ROOT/'benchmarks/raw/evidence').resolve():
        raise ValueError('unique evidence output in task raw directory required')
    db = ROOT/'benchmarks/raw'/STORE/'N.E.K.O/plugins/study_companion/data/study_companion.db'
    before = snapshot(db)
    rows = before['tables']['qa_records']
    if len(rows) != 5 or before['question'] or not before['course'].startswith(STORE):
        raise RuntimeError('original owned scene44 checkpoint required; never repair/reset history')
    assert before['language_by_course'].get(before['course']) == 'en-US'
    artifacts = [json.loads(row['question']) for row in rows]
    question, reference = artifacts[0]['question'], artifacts[0]['answer']
    assert all(item['question'] == question and item['answer'] == reference for item in artifacts)
    assert len({row['topic_id'] for row in rows}) == 3
    ledger = json.loads(LEDGER.read_text(encoding='utf-8'))
    assert ledger['round'] == 'bargein-autocheck-20261012'
    assert ledger['budgets'] == {'api.deepseek.com':2000.0,'www.lanlan.app':None,'www.lanlan.tech':0.0}
    assert ledger['spent'].get('api.deepseek.com',0) <= 1998
    manifest_path = ROOT/'patches/neko-study-2026-10-10-product/manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    fingerprints, deployed_fingerprints = {}, {}
    for item in manifest['files']:
        source = manifest_path.parent/item['path']
        deployed = ROOT/manifest['deployment']/item['path'].removeprefix('payload/study_companion/')
        actual = hashlib.sha256(source.read_bytes()).hexdigest()
        assert actual == item['sha256']
        deployed_sha = hashlib.sha256(deployed.read_bytes()).hexdigest()
        expected_deployed = (item['protected_deployed_sha256']
                             if item['path']=='static/index.html' and item.get('protected_deployed_matches') is True
                             else actual)
        assert deployed_sha == expected_deployed
        fingerprints[item['path']] = actual
        deployed_fingerprints[item['path']] = deployed_sha
    host.verify_source_audio_gate()
    report = {'store':STORE,'before':ledger,'before_snapshot':before,'calls':[],
              'source_sha256':fingerprints,'deployed_sha256':deployed_fingerprints,
              'audio':False,'avatar':False,'microphone':False,
              'capture':False,'loopback':False,'scope':'actual silent Study SDK/model/SQLite; no Native/device/human proof'}

    def save():
        output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

    # Exclusive claim prevents an accidentally repeated paid run.
    with output.open('x',encoding='utf-8') as file:
        file.write(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    try:
        for index, answer in enumerate(('WEX 指向 NUD。','NUD 指向 REZ。')):
            for port in (host.MAIN_PORT,host.PLUGIN_PORT):
                with socket.socket() as probe:
                    if probe.connect_ex(('127.0.0.1',port)) == 0:
                        raise RuntimeError('existing host occupies task ports; preserve it')
            phase = {'index':index,'before_restart':snapshot(db)}
            report['calls'].append(phase);save()
            log = output.with_suffix('.host'+str(index)+'.log').open('xb')
            process = None
            try:
                process = subprocess.Popen([str(host.SOURCE_PYTHON),'-X','utf8','-B',
                    str(ROOT/'scripts/neko_desktop_tutor_host.py'),'--source','--text-only','--core-provider','free',
                    '--store',STORE,'--hold','180','--api-budget','2','--egress-budget','2000',
                    '--allow-host','www.lanlan.app:unlimited','--allow-host','www.lanlan.tech:0',
                    '--budget-round','bargein-autocheck-20261012'],cwd=ROOT,
                    env={**os.environ,'NEKO_TASK_SILENT':'1','PYTHONIOENCODING':'utf-8'},stdout=log,stderr=subprocess.STDOUT)
                phase['launcher_pid']=process.pid;save()
                ready,reason=plugin_server_ready(85,process)
                if not ready:raise RuntimeError('host unavailable: '+reason)
                client=LabClient()
                phase['started_wall']=time.time();save()
                phase['grade']=client.call('study_evaluate_answer',{'question':question,'expected_answer':reference,
                    'answer':answer},timeout=110)
                phase['completed_wall']=time.time();save()
                result=phase['grade']['data']
                if result.get('degraded') or result.get('ok') is False:
                    raise RuntimeError('grade unavailable; stop without retry')
                phase['snapshot']=snapshot(db);save()
                added=phase['snapshot']['tables']['qa_records'][len(rows):]
                if len(added)!=index+1:raise RuntimeError('unexpected grade count; stop without retry')
                print('Completed real grade '+str(index+1)+'; stopping owned silent host',flush=True)
            finally:
                if process is not None:
                    stop_owned_host(process);phase['host_exit']=process.poll()
                log.close();save()
        after=snapshot(db);report['after_snapshot']=after
        added=after['tables']['qa_records'][len(rows):]
        bindings=[json.loads(row['question'])['internal_private_payload']['learning_topic_binding'] for row in added]
        new_topic=added[0]['topic_id']
        report['checks']={
            'two_actual_grades':len(added)==2,
            'same_topic_after_restart':added[1]['topic_id']==new_topic,
            'ambiguous_history_not_arbitrarily_merged':new_topic not in {row['topic_id'] for row in rows},
            'provisional_question_scope':all(binding['scope']=='question' and binding['topic_id']==new_topic for binding in bindings),
            'same_binding_key':bindings[0]['key']==bindings[1]['key'],
            'old_qa_and_mastery_rows_unchanged':all(after['tables'][name][:len(before['tables'][name])]==before['tables'][name] for name in ('qa_records','mastery_snapshots')),
            'old_interactions_unchanged':after['tables']['interactions'][:len(before['tables']['interactions'])]==before['tables']['interactions'],
            'two_new_formal_grades':sum(row['kind']=='answer_evaluate' for row in after['tables']['interactions'])==sum(row['kind']=='answer_evaluate' for row in before['tables']['interactions'])+2,
            'old_fsrs_rows_unchanged':all(row in after['tables']['fsrs_cards'] for row in before['tables']['fsrs_cards']),
            'one_new_fsrs_identity':len(after['tables']['fsrs_cards'])==len(before['tables']['fsrs_cards'])+1,
            'two_new_mastery_rows_same_identity':len(after['tables']['mastery_snapshots'])==len(before['tables']['mastery_snapshots'])+2 and all(row['topic_id']==new_topic for row in after['tables']['mastery_snapshots'][len(before['tables']['mastery_snapshots']):]),
            'saved_course_language_unchanged':after['language_by_course']==before['language_by_course'],
            'same_course':after['course']==before['course'],
            'no_synthetic_pending_question':after['question']==before['question']=={},
        }
    except Exception as error:
        report['failure']=type(error).__name__+': '+str(error)
    finally:
        report['after']=json.loads(LEDGER.read_text(encoding='utf-8'))
        report['finalized']=True;save()
        print(json.dumps({'report':str(output),'failure':report.get('failure'),'checks':report.get('checks'),
                          'spent':report['after']['spent']},ensure_ascii=False),flush=True)
    return 1 if report.get('failure') or not all(report.get('checks',{}).values()) else 0


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    raise SystemExit(main(parser.parse_args().output))
