"""Reproduce awareness with scoped config rollback, preserving learning records."""
import json
from pathlib import Path
import sqlite3
import sys
import time

from neko_lab_client import LabClient, status_summary
from neko_lab_stage import DB


def update_awareness(value):
    with sqlite3.connect(DB) as connection:
        row = connection.execute("SELECT value FROM kv WHERE key='config'").fetchone()
        config = json.loads(row[0])
        config['awareness'] = value
        connection.execute("UPDATE kv SET value=?,updated_at=? WHERE key='config'",
                           (json.dumps(config, ensure_ascii=False), time.time()))


def stop(client):
    client.request('/plugin/study_companion/stop', 'POST', {})
    info = client.request('/server/info')
    if 'study_companion' in (info.get('running_plugins_status') or {}):
        raise RuntimeError('plugin still running; do not edit its database')


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    client = LabClient()
    with sqlite3.connect(f'file:{DB}?mode=ro', uri=True) as connection:
        config = json.loads(connection.execute("SELECT value FROM kv WHERE key='config'").fetchone()[0])
    original = config['awareness']
    evidence = {'original_awareness': original, 'observations': []}
    target = Path(__file__).resolve().parents[1] / 'benchmarks/raw/evidence/goal-awareness-baseline.json'
    try:
        stop(client)
        update_awareness({**original, 'enabled': True})
        client.request('/plugin/study_companion/start', 'POST', {}, timeout=40)
        started = time.monotonic()
        for _ in range(7):
            state = status_summary(client.call('study_status'))
            messages = client.request('/plugin/messages?plugin_id=study_companion&max_count=30')
            row = {'elapsed_s': round(time.monotonic()-started, 2),
                   'awareness': state['awareness'], 'supervision': state['supervision'],
                   'classification_count': state['classification_count'],
                   'message_count': messages.get('count'),
                   'message_shapes': [list(m) for m in messages.get('messages', [])[:2]]}
            evidence['observations'].append(row)
            target.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding='utf-8')
            print(json.dumps(row, ensure_ascii=False), flush=True)
            time.sleep(5)
    finally:
        stop(client)
        update_awareness(original)
        client.request('/plugin/study_companion/start', 'POST', {}, timeout=40)
        state = status_summary(client.call('study_status'))
        evidence['restored_awareness'] = state['awareness']
        evidence['rollback_ok'] = state['awareness'] == original
        target.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding='utf-8')
        print('rollback_ok', evidence['rollback_ok'], flush=True)


if __name__ == '__main__':
    main()
