"""One changed picture-source callback check, real Study vision, no audio/UI/retry."""
import argparse
import base64
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
from neko_native_avatar_toolchain import call
from neko_tutor_start import plugin_server_ready
from neko_summary_semantics_probe import snapshot

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / 'benchmarks/raw/neko-desktop-egress-cap'
IMAGE = ROOT / 'benchmarks/raw/evidence/diagram-input-sky-dark.png'
QUESTION = ('请重新检查当前图片中 Express 到外部数据源的连线，逐字引用箭头旁的中文条件，'
            '再说明什么时候会发起这条请求。看不清就直接说看不清；最多两句，不出题。')


def main(args):
    store = ROOT / 'benchmarks/raw' / args.store
    output = args.output.resolve()
    if (not args.store.startswith('neko-daily-silent-vision-') or Path(args.store).name != args.store
            or store.exists() != args.existing or output.exists()
            or not output.is_relative_to(ROOT / 'benchmarks/raw/evidence')):
        raise ValueError('explicit isolated store state and new raw evidence output required')
    db = store/'N.E.K.O/plugins/study_companion/data/study_companion.db'
    database_before = snapshot(db.resolve()) if args.existing else None
    if args.correction_only and not args.existing:
        raise ValueError('correction-only requires the exact existing picture scene')
    before = json.loads(LEDGER.read_text(encoding='utf-8'))
    assert before['round'] == 'bargein-autocheck-20261012'
    assert before['spent'].get('api.deepseek.com', 0) < 2000
    for port in (host.MAIN_PORT, host.PLUGIN_PORT):
        with socket.socket() as probe:
            if probe.connect_ex(('127.0.0.1', port)) == 0:
                raise RuntimeError('preserve existing host')
    pixels = IMAGE.read_bytes()
    assert pixels.startswith(b'\x89PNG\r\n\x1a\n')
    if args.existing:
        with sqlite3.connect(db.resolve().as_uri()+'?mode=ro',uri=True) as connection:
            key='submitted_image:'+hashlib.sha256(database_before['course_id'].encode()).hexdigest()
            material=json.loads(connection.execute('SELECT value FROM kv WHERE key=?',(key,)).fetchone()[0])
            saved=base64.b64decode(material['image'].split(',',1)[-1])
            assert saved == pixels, 'existing scene must retain this exact image'
    report = {'before_ledger':before, 'calls':[], 'store':args.store,
        'image_sha256':hashlib.sha256(pixels).hexdigest(), 'room_microphone':False,
        'speaker':False, 'loopback':False, 'native_window':False, 'voice_session':False,
        'scope':'real Study image/callback/backend/SQLite only; no role autonomous selection, device or human proof'}
    report['database_before'] = database_before
    output.parent.mkdir(parents=True, exist_ok=True)
    log = output.with_suffix('.host.log').open('wb')
    process = subprocess.Popen([str(host.SOURCE_PYTHON), '-X', 'utf8', '-B',
        str(ROOT/'scripts/neko_desktop_tutor_host.py'), '--source', '--study-vision',
        '--store', args.store, '--hold', '240', '--api-budget', '6', '--egress-budget', '2000',
        '--budget-round', 'bargein-autocheck-20261012'], cwd=ROOT,
        env={**os.environ, 'NEKO_TASK_SILENT':'1', 'PYTHONIOENCODING':'utf-8'},
        stdout=log, stderr=subprocess.STDOUT)
    report['host_launcher_pid'] = process.pid
    def save():
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    save()
    try:
        ready, reason = plugin_server_ready(85, process)
        if not ready:
            raise RuntimeError('text-only host not ready: '+reason)
        print('Reviewed text-only host ready; no browser, Native, voice or audio device', flush=True)
        client = LabClient()
        client.call('study_update_settings_config', {'config':{
            'communication':{'enabled':False}, 'awareness':{'enabled':False}, 'ocr_reader':{'enabled':False},
            'llm':{'llm_vision_enabled':True,'llm_vision_max_image_px':2048}}})
        steps = [
            ('study_submit_image', {'image_base64':base64.b64encode(pixels).decode(),
                'text':'只定位 Express 与外部数据源，不解释连线条件；一句话，不出题。'}, False),
            ('study_explain', {'question':QUESTION, 'text':'Old summary: weather cache hit triggers upstream fetch.',
                'material_source':'current_picture', '_ctx':{'lanlan_name':'SilentPictureRecheck'}}, True),
        ]
        if args.existing:
            steps = [('study_explain', {'question':
                '天气和百科请求的触发条件分别能从当前图片确定哪些？区分直接证据与推断，中文最多两句，不出题。',
                'material_source':'current_picture', '_ctx':{'lanlan_name':'SilentPictureRecheck'}}, True),
                ('study_explain', {'question':
                '你解释错了，请重新检查：应该是天气和百科都缓存命中才请求上游吧？这次只用两句英文回答，不要中文，不出题。',
                '_ctx':{'lanlan_name':'SilentPictureRecheck'}}, True)]
            if args.correction_only:
                steps = [steps[-1]]
                steps[0][1].update(material_source='current_picture',
                    text='Old summary: both weather and encyclopedia fetch upstream only on a cache hit.')
        previous_reply = ''
        for index, (entry, arguments, callback) in enumerate(steps):
            if args.existing and index == 1:
                arguments['text'] = previous_reply
            safe_args = {k:v for k,v in arguments.items() if k!='image_base64'}
            row = {'entry':entry,'arguments':safe_args,'started_wall':time.time()}
            report['calls'].append(row); save()
            row['result'] = call(entry, arguments, timeout=110) if callback else client.call(entry, arguments, timeout=110)
            row['completed_wall'] = time.time(); save()
            data = row['result'].get('output', row['result'].get('data', {}))
            if isinstance(data, str):
                data = json.loads(data)
            if row['result'].get('is_error') or data.get('degraded') or data.get('ok') is False:
                raise RuntimeError('backend refused; retain failure and do not retry')
            previous_reply = str(data.get('reply') or '')
        with sqlite3.connect(db.resolve().as_uri()+'?mode=ro',uri=True) as connection:
            connection.execute('PRAGMA query_only=ON')
            rows = connection.execute('SELECT kind,input_text,metadata FROM interactions ORDER BY id DESC LIMIT 1').fetchall()
            assert rows and rows[0][0]=='concept_explain'
            report['checks'] = {'saved_current_material_identity':bool(json.loads(rows[0][2]).get('material_context',{}).get('material_identity')),
                'old_summary_not_used_as_source':steps[-1][1].get('text','Old summary:') not in rows[0][1],
                'question_preserved':steps[-1][1]['question'] in rows[0][1]}
        if args.existing:
            after = snapshot(db.resolve())
            report['checks'].update(previous_interactions_unchanged=after['interactions'][:len(database_before['interactions'])]==database_before['interactions'],
                previous_grades_unchanged=after['qa']==database_before['qa'],same_course=after['course_id']==database_before['course_id'])
        assert all(report['checks'].values())
        report['result'] = 'REAL_BACKEND_COMPLETED_REQUIRES_PIXEL_SEMANTIC_REVIEW'
    except Exception as error:
        report['failure'] = type(error).__name__+': '+str(error)
        report['result'] = 'FAIL_OR_PARTIAL_NO_RETRY'
    finally:
        stop_owned_host(process); log.close()
        report['after_ledger'] = json.loads(LEDGER.read_text(encoding='utf-8'))
        report['finalized'] = True; save()
        print(json.dumps({'result':report['result'],'failure':report.get('failure'),
            'checks':report.get('checks'),'spent':report['after_ledger']['spent'],
            'responses':[x.get('result',{}).get('output',x.get('result',{}).get('data')) for x in report['calls']]},ensure_ascii=False),flush=True)
    return 1 if report.get('failure') else 0


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--store',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--existing',action='store_true',help='two changed correction/language checks on this exact saved scene; preserve all prior history')
    parser.add_argument('--correction-only',action='store_true',help='one changed English/polarity correction; skip passed scene setup and Chinese answer')
    raise SystemExit(main(parser.parse_args()))
