"""One real muted Study callback; preserve task history and bound owned processes."""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import sqlite3
import subprocess
import time

from neko_daily_code_dialogue_probe import cleanup_probe_host, host_command
from neko_native_avatar_toolchain import call
from neko_relevant_history_probe import remember_children
from neko_tutor_start import plugin_server_ready, process_creation_time
import neko_desktop_tutor_host as host

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / 'benchmarks/raw/neko-desktop-egress-cap'


def history_snapshot(database):
    with sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute('PRAGMA query_only=ON')
        return {table: {str(row['id']): hashlib.sha256(json.dumps(dict(row), sort_keys=True,
                    ensure_ascii=False).encode()).hexdigest()
                for row in connection.execute('SELECT * FROM ' + table + ' ORDER BY id')}
                for table in ('interactions', 'qa_records')}


async def main(options):
    raw = (ROOT / 'benchmarks/raw').resolve()
    store = (raw / options.store).resolve()
    output = options.output.resolve()
    if (not options.store.startswith('neko-daily-code-contrast-') or store.parent != raw
            or output.parent != raw / 'evidence' or output.exists()):
        raise ValueError('Use an existing task code store and new raw/evidence output.')
    data = store / 'N.E.K.O/plugins/study_companion/data'
    database = data / 'study_companion.db'
    if not database.is_file() or not (data / 'code_project.json').is_file():
        raise ValueError('Existing task database and source authorization are required.')
    for port in (48911, 48916, 9234):
        with socket.socket() as check:
            if check.connect_ex(('127.0.0.1', port)) == 0:
                raise RuntimeError('An existing host owns a required port; do not replace it.')
    before = json.loads(LEDGER.read_text(encoding='utf-8'))
    if (before['round'] != 'bargein-autocheck-20261012'
            or before['budgets'] != {'api.deepseek.com': 2000, 'www.lanlan.app': None, 'www.lanlan.tech': 0}
            or before['spent'].get('api.deepseek.com', 0) >= 1994):
        raise RuntimeError('Preserve the approved round and leave room for this bounded call.')
    report = {'started_wall': time.time(), 'before': before, 'history_before': history_snapshot(database), 'timings': [],
              'text_only': True, 'task_silent': True, 'room_microphone': False,
              'capture': False, 'loopback': False, 'native_started': False,
              'proof': 'real Study SDK/model timing, not autonomous avatar, device or human proof'}
    def save():
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    with output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    core_path = store / 'N.E.K.O/config/core_config.json'
    saved_core = json.loads(core_path.read_text(encoding='utf-8')).get('coreApi', 'free')
    log = ROOT / 'benchmarks/raw/neko-desktop-host.log'
    log_start = log.stat().st_size if log.exists() else 0
    command = host_command(options)
    command[command.index('--api-budget') + 1] = '6'
    command[command.index('--hold') + 1] = '240'
    handle = output.with_suffix('.host.log').open('xb')
    process = None
    tracker = None
    ownership = []
    try:
        process = subprocess.Popen(command, cwd=ROOT, env={**os.environ, 'NEKO_TASK_SILENT': '1',
            'PYTHONIOENCODING': 'utf-8'}, stdout=handle, stderr=subprocess.STDOUT)
        created = process_creation_time(process.pid)
        if created is None:
            process.terminate()
            process.wait(timeout=10)
            raise RuntimeError('Launcher identity unavailable; stop the owned handle.')
        ownership = [{'pid': process.pid, 'created_at': created}]
        report['owned_launcher'] = ownership[0]
        save()
        async def track_children():
            while process.poll() is None:
                remember_children(process, ownership)
                ownership[:] = list({(item['pid'], item['created_at']): item for item in ownership}.values())
                await asyncio.sleep(0.25)
        tracker = asyncio.create_task(track_children())
        ready, reason = await asyncio.to_thread(plugin_server_ready, 90, process)
        report['ready'] = ready
        if not ready:
            raise RuntimeError('Study readiness failed: ' + reason)
        print('Muted Study SDK ready; one bounded source-teacher callback', flush=True)
        started = time.monotonic()
        report['request_started_wall'] = time.time()
        request = asyncio.create_task(asyncio.to_thread(call, 'study_explain', {
            'material_source': 'project_code',
            'question': '请解释 weather_service.dart 的非200状态分支，只用两句中文；上层处理没有证据就不要推断。',
            'code_requests': [{'mode': 'file', 'file': 'weather_service.dart', 'offset': 1, 'limit': 29}],
        }, timeout=95))
        while not request.done():
            if tracker.done():
                tracker.result()
            spent = json.loads(LEDGER.read_text(encoding='utf-8'))['spent'].get('api.deepseek.com', 0)
            if spent - before['spent'].get('api.deepseek.com', 0) >= 12:
                raise RuntimeError('Scene external-call ceiling reached; stop without retry.')
            if time.monotonic() - started > 100:
                raise TimeoutError('Existing callback observation expired; stop owned host, no restart.')
            await asyncio.wait({request}, timeout=0.5)
        report['result'] = await request
        report['request_finished_wall'] = time.time()
        report['callback_ms'] = round((time.monotonic() - started) * 1000, 3)
        answer = report['result'].get('output', {})
        if (report['result'].get('is_error') or answer.get('ok', True) is False
                or answer.get('degraded') or not answer.get('reply')):
            raise RuntimeError('Study callback failed; retain result, no retry.')
        print('Single callback terminal; collecting content-free stage records', flush=True)
    except Exception as error:
        report['failure'] = type(error).__name__ + ': ' + str(error)
    finally:
        if tracker is not None:
            tracker.cancel()
            tracked = await asyncio.gather(tracker, return_exceptions=True)
            if tracked and isinstance(tracked[0], Exception):
                report['tracker_error'] = type(tracked[0]).__name__
        if process is not None:
            try:
                await asyncio.to_thread(cleanup_probe_host, process, ownership)
            except Exception as error:
                report['cleanup_error'] = type(error).__name__ + ': ' + str(error)
            report['owned_host_exit'] = process.poll()
        handle.close()
        if core_path.is_file():
            core = json.loads(core_path.read_text(encoding='utf-8'))
            if core.get('coreApi') == 'deepseek':
                core['coreApi'] = saved_core
                core_path.write_text(json.dumps(core, ensure_ascii=False, indent=2), encoding='utf-8')
                report['core_provider_restored'] = saved_core
        if log.is_file():
            with log.open('rb') as stream:
                stream.seek(log_start)
                for match in re.finditer(r'study_code_timing (\{[^\r\n]+\})', stream.read().decode('utf-8', 'replace')):
                    report['timings'].append(json.loads(match.group(1)))
        report['history_after'] = history_snapshot(database)
        report['old_history_unchanged'] = all(report['history_after'][table].get(key) == value
            for table, rows in report['history_before'].items() for key, value in rows.items())
        report['after'] = json.loads(LEDGER.read_text(encoding='utf-8'))
        report['owned_processes'] = ownership
        report['finalized'] = True
        save()
    print(json.dumps({key: report.get(key) for key in ('failure', 'cleanup_error', 'tracker_error',
        'callback_ms', 'old_history_unchanged', 'timings', 'after')}, ensure_ascii=False), flush=True)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--store', required=True)
    parser.add_argument('--output', type=Path, required=True)
    result = asyncio.run(main(parser.parse_args()))
    raise SystemExit(1 if any(result.get(k) for k in ('failure', 'cleanup_error', 'tracker_error'))
                     or not result.get('old_history_unchanged') or len(result['timings']) != 1 else 0)
