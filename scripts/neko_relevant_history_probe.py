"""One silent model recall, using labelled synthetic QA in a NEW owned store.

No grading, recording, browser, avatar, audio devices, retries or user database.
"""
from __future__ import annotations

import argparse
import asyncio
import ast
import hashlib
import json
import logging
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys

import psutil
import neko_desktop_tutor_host as host
from neko_lab_client import LabClient
from neko_tutor_start import (plugin_server_ready, process_creation_time,
                             owned_browser_pids, stop_owned_tree)

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / 'benchmarks/raw/neko-daily-relevant-history-20261015-52'
COURSE = 'relevant-history-fixture52'
DB = STORE / 'N.E.K.O/plugins/study_companion/data/study_companion.db'
RECEIPT = STORE / 'actual-explain-messages.jsonl'
OUTPUT = ROOT / 'benchmarks/raw/evidence/daily-companion-relevant-history52.json'
PROMPT = ('继续讲解软件架构图的箭头方向。根据我保存的更早答题记录，'
          '我具体误读过哪一步，后来有没有纠正？没有记录就说不知道。'
          '只用两句简短中文，不出题，不补没有证据的模块职责。')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ledger():
    value = json.loads((ROOT / 'benchmarks/raw/neko-desktop-egress-cap').read_text())
    assert value['round'] == 'bargein-autocheck-20261012'
    assert value['budgets'] == {'api.deepseek.com': 2000.0, 'www.lanlan.app': None, 'www.lanlan.tech': 0.0}
    return value


def snapshot():
    with sqlite3.connect(DB.resolve().as_uri() + '?mode=ro', uri=True) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA query_only=ON')
        rows = [dict(row) for row in conn.execute('SELECT * FROM qa_records ORDER BY id')]
        return {'qa_count': len(rows), 'qa_sha256': hashlib.sha256(
            json.dumps(rows, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
            'interactions': [dict(row) for row in conn.execute('SELECT * FROM interactions ORDER BY id')]}


def seed_fixture():
    # This is explicitly synthetic saved history, never presented as human work.
    import test_neko_product_course_memory as memory
    DB.parent.mkdir(parents=True)
    store = memory.Store(DB, STORE / 'no-seed.json', logging.getLogger('recall-fixture'))
    store.open()
    try:
        plugin = memory.ProductHarness(store)
        asyncio.run(plugin._restart_study_session(course_id=COURSE))
        topic = COURSE + '::arrows'
        store.ensure_topic(topic_id=topic, name='箭头方向', subject='computer_science')
        store.ensure_topic(topic_id=COURSE + '::noise', name='Python变量', subject='computer_science')

        def add(text, *, qid='original-arrow', key='original-material', target=topic, wrong=False):
            store.add_qa_record(session_id=plugin._study_session_id, topic_id=target,
                question={'question': '图中WEX与NUD的箭头起点、终点分别是什么？',
                    'answer': 'PRIVATE_REFERENCE_SENTINEL', 'question_id': qid,
                    'internal_private_payload': {'learning_topic_binding': {'key': key}}},
                user_answer=text, eval_result={'verdict': 'wrong' if wrong else 'correct',
                    'score': 0 if wrong else 100, 'feedback': '方向读反了。' if wrong else '这次方向已纠正。'},
                mode='teaching', history_limit=5000)

        add('我把WEX到NUD读成NUD到WEX。', wrong=True)
        add('我已改正：箭头尖在NUD，所以是WEX到NUD。')
        for i in range(7):
            add('随后另一道方向题' + str(i), qid='other-' + str(i), key='other-' + str(i))
        for i in range(105):
            add('无关变量练习' + str(i), qid='noise-' + str(i), target=COURSE + '::noise')
    finally:
        store.close()


def worker():
    # Hook only the launcher-created task plugin, after canonical deployment.
    original = host.prepare_product_plugin

    def prepare(store, **kwargs):
        assert store.resolve() == STORE.resolve() and os.getenv('NEKO_TASK_SILENT') == '1'
        original(store, **kwargs)
        path = store / 'plugin-code/study_companion/study_model_gateway.py'
        canonical = ROOT / 'patches/neko-study-2026-10-10-product/payload/study_companion/study_model_gateway.py'
        assert path.read_bytes() == canonical.read_bytes()
        text = path.read_text(encoding='utf-8')
        anchor = '        audit("started")\n'
        assert text.count(anchor) == 1 and not RECEIPT.exists()
        addition = ('        if operation == "concept_explain":\n'
            f'            with Path({str(RECEIPT)!r}).open("a", encoding="utf-8") as receipt:\n'
            '                receipt.write(json.dumps({"operation": operation, "messages": messages}, '
            'ensure_ascii=False) + "\\n")\n')
        patched = text.replace(anchor, addition + anchor, 1)
        ast.parse(patched)
        path.write_text(patched, encoding='utf-8', newline='\n')

    host.prepare_product_plugin = prepare
    sys.argv = ['neko_desktop_tutor_host.py', '--source', '--text-only', '--core-provider', 'free',
        '--store', STORE.name, '--hold', '180', '--api-budget', '4', '--egress-budget', '2000',
        '--allow-host', 'www.lanlan.app:unlimited', '--allow-host', 'www.lanlan.tech:0',
        '--budget-round', 'bargein-autocheck-20261012']
    return host.main()


def remember_children(process, ownership):
    if process.poll() is not None or process.pid not in owned_browser_pids(ownership):
        return
    parent = psutil.Process(process.pid)
    root = next(item for item in ownership if item['pid'] == process.pid)
    if abs(parent.create_time() - root['created_at']) > 1:
        return
    for child in parent.children(recursive=True):
        created = process_creation_time(child.pid)
        if created is not None and abs(child.create_time() - created) <= 1:
            ownership.append({'pid': child.pid, 'created_at': created})


def main():
    before = ledger()
    assert before['spent'].get('api.deepseek.com', 0) <= 1996
    assert not OUTPUT.exists() and not STORE.exists(), 'preserve earlier evidence; no repeated paid recall'
    for port in (host.MAIN_PORT, host.PLUGIN_PORT):
        with socket.socket() as probe:
            assert probe.connect_ex(('127.0.0.1', port)) != 0, 'preserve existing host'
    host.verify_source_audio_gate()
    manifest_path = ROOT / 'patches/neko-study-2026-10-10-product/manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    for item in manifest['files']:
        assert sha(manifest_path.parent / item['path']) == item['sha256']
    report = {'store': str(STORE), 'fixture': 'synthetic saved QA; real model reply, not human answers',
        'before': before, 'manifest_sha256': sha(manifest_path), 'prompt': PROMPT,
        'audio': False, 'capture': False, 'microphone': False, 'loopback': False, 'avatar': False,
        'semantic_review': 'PENDING; nonempty reply and prompt checks are structural evidence only'}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open('x', encoding='utf-8') as f:
        f.write(json.dumps(report, ensure_ascii=False, indent=2) + '\n')

    def save():
        OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    process = None
    ownership = []
    try:
        STORE.mkdir()
        seed_fixture()
        report['before_snapshot'] = snapshot()
        save()
        with OUTPUT.with_suffix('.host.log').open('xb') as log:
            process = subprocess.Popen([str(host.SOURCE_PYTHON), '-X', 'utf8', '-B',
                str(Path(__file__).resolve()), '--worker'], cwd=ROOT,
                env={**os.environ, 'NEKO_TASK_SILENT': '1', 'PYTHONIOENCODING': 'utf-8'},
                stdout=log, stderr=subprocess.STDOUT)
            report['launcher_pid'] = process.pid
            created = process_creation_time(process.pid)
            if created is None:
                raise RuntimeError('launcher identity unavailable; preserve evidence')
            ownership.append({'pid': process.pid, 'created_at': created})
            report['ownership'] = ownership
            save()
            ready, reason = plugin_server_ready(85, process)
            if not ready:
                raise RuntimeError('silent host unavailable: ' + reason)
            remember_children(process, ownership)
            save()
            report['result'] = LabClient().call('study_explain_text', {'text': PROMPT}, timeout=110)
            save()
            data = report['result']['data']
            if data.get('degraded') or data.get('ok') is False:
                raise RuntimeError('recall unavailable; stop without retry')
            report['actual_messages'] = [json.loads(line) for line in RECEIPT.read_text(encoding='utf-8').splitlines()]
            messages = json.dumps(report['actual_messages'], ensure_ascii=False)
            report['after_snapshot'] = snapshot()
            report['checks'] = {
                'actual_explain_prompt_contains_old_wrong': '我把WEX到NUD读成NUD到WEX。' in messages,
                'actual_explain_prompt_contains_later_correction': '我已改正：箭头尖在NUD，所以是WEX到NUD。' in messages,
                'no_reference_sentinel_in_explain': 'PRIVATE_REFERENCE_SENTINEL' not in messages,
                'qa_history_not_regraded_or_changed': report['before_snapshot']['qa_sha256'] == report['after_snapshot']['qa_sha256'],
                'nonempty_reply': bool(str(data.get('reply') or data.get('summary') or '').strip()),
            }
    except Exception as error:
        report['failure'] = type(error).__name__ + ': ' + str(error)
    finally:
        try:
            if process is not None:
                # Existing creation-time gate also protects recorded orphan children.
                # Do not unlink a shared numeric PID file as proof of ownership.
                stop_owned_tree(ownership)
                process.wait(timeout=20)
                report['host_exit'] = process.poll()
        except Exception as error:
            report['cleanup_error'] = type(error).__name__ + ': ' + str(error)
        report['after'] = ledger()
        report['finalized'] = True
        save()
        print(json.dumps({'report': str(OUTPUT), 'failure': report.get('failure'),
            'cleanup_error': report.get('cleanup_error'), 'checks': report.get('checks'),
            'spent': report['after']['spent']}, ensure_ascii=False), flush=True)
    return int(bool(report.get('failure') or report.get('cleanup_error') or not all(report.get('checks', {}).values())))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    raise SystemExit(worker() if parser.parse_args().worker else main())
