"""One fresh task store through course switch, restart and an offline launch (text-only SDK).

Phases, each a separate owned host on the same store:
  1 online : start course, explain a source window, switch course and back, follow up
             without naming the code
  2 online : after a restart, follow up again
  3 offline: external egress denied; the follow-up must fail politely and keep history
  4 online : recovered; the follow-up works again
No audio, Native, microphone or capture. Stops on the first unexpected failure; no retries.
"""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import time

from neko_daily_code_dialogue_probe import cleanup_probe_host, host_command, prepare_contrast_grant
from neko_native_avatar_toolchain import call
from neko_relevant_history_probe import remember_children
from neko_tutor_start import plugin_server_ready, process_creation_time

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / 'benchmarks/raw/neko-desktop-egress-cap'
COURSE, OTHER = 'm5-sky-scout', 'm5-other-course'
FIRST = {'question': '请解释 weather_service.dart 里非200响应怎样处理，只用两句中文；上层处理没有证据就不要推断。',
         'code_requests': [{'mode': 'file', 'file': 'weather_service.dart', 'offset': 1, 'limit': 29}]}
FOLLOW = {'question': '刚才那段代码里，如果响应是 404，会走到哪一行？两句中文。'}


def rows(database):
    with sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True) as connection:
        connection.row_factory = sqlite3.Row
        return {str(row['id']): hashlib.sha256(json.dumps(dict(row), sort_keys=True, ensure_ascii=False).encode()).hexdigest()
                for row in connection.execute('SELECT * FROM interactions ORDER BY id')}


def spent():
    return json.loads(LEDGER.read_text(encoding='utf-8'))['spent'].get('api.deepseek.com', 0)


async def phase(options, report, name, steps, *, offline=False):
    record = {'name': name, 'offline': offline, 'steps': []}
    report['phases'].append(record)
    command = host_command(options)
    command[command.index('--api-budget') + 1] = '8'
    command[command.index('--hold') + 1] = '300'
    if offline:
        command.append('--offline-egress')
    log = options.output.with_suffix(f'.{name}.host.log').open('xb')
    process = subprocess.Popen(command, cwd=ROOT, env={**os.environ, 'NEKO_TASK_SILENT': '1', 'PYTHONIOENCODING': 'utf-8'},
                               stdout=log, stderr=subprocess.STDOUT)
    ownership = [{'pid': process.pid, 'created_at': process_creation_time(process.pid)}]
    async def track():
        while process.poll() is None:
            remember_children(process, ownership)
            await asyncio.sleep(0.25)
    tracker = asyncio.create_task(track())
    try:
        ready, reason = await asyncio.to_thread(plugin_server_ready, 90, process)
        record['ready'] = ready
        if not ready:
            raise RuntimeError('Study readiness failed: ' + reason)
        for tool, arguments, expect in steps:
            started = time.monotonic()
            result = await asyncio.to_thread(call, tool, arguments, timeout=95)
            output = result.get('output', {}) if isinstance(result, dict) else {}
            step = {'tool': tool, 'arguments': arguments, 'ms': round((time.monotonic() - started) * 1000),
                    'ok': output.get('ok', True) is not False and not output.get('degraded') and not result.get('is_error'),
                    'error': output.get('error') or output.get('diagnostic') or '',
                    'reply': str(output.get('reply') or '')[:400], 'course_id': output.get('course_id'),
                    'source_evidence': output.get('source_evidence')}
            record['steps'].append(step)
            report['ledger_now'] = spent()
            save(options, report)
            if spent() - report['ledger_before'] >= 20:
                raise RuntimeError('Scene external-call ceiling reached; stop without retry.')
            if step['ok'] != expect:
                raise RuntimeError(f'{name}: {tool} ok={step["ok"]} expected {expect}')
    finally:
        tracker.cancel()
        await asyncio.gather(tracker, return_exceptions=True)
        try:
            await asyncio.to_thread(cleanup_probe_host, process, ownership)
        except Exception as error:
            record['cleanup_error'] = f'{type(error).__name__}: {error}'
        log.close()


def save(options, report):
    options.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


async def main(options):
    options.contrast_only = True
    for port in (48911, 48916, 9234):
        with socket.socket() as check:
            if check.connect_ex(('127.0.0.1', port)) == 0:
                raise RuntimeError('An existing host owns a required port; do not replace it.')
    before = json.loads(LEDGER.read_text(encoding='utf-8'))
    if before['round'] != 'bargein-autocheck-20261012' or before['spent'].get('api.deepseek.com', 0) >= 1980:
        raise RuntimeError('Preserve the approved round and leave room for this bounded scene.')
    prepare_contrast_grant(options)
    database = ROOT / 'benchmarks/raw' / options.store / 'N.E.K.O/plugins/study_companion/data/study_companion.db'
    report = {'started_wall': time.time(), 'store': options.store, 'ledger_before': before['spent'].get('api.deepseek.com', 0),
              'phases': [], 'text_only': True, 'native': False, 'microphone': False}
    with options.output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream)
    session = lambda action, course: ('study_session', {'action': action, 'course_id': course}, True)
    explain = lambda arguments, expect=True: ('study_explain', {'material_source': 'project_code', **arguments}, expect)
    history = {}
    try:
        await phase(options, report, 'p1-online', [session('start', COURSE), explain(FIRST),
                    session('set_course', OTHER), session('set_course', COURSE), explain(FOLLOW)])
        history['after_p1'] = rows(database)
        await phase(options, report, 'p2-restart', [session('status', ''), explain(FOLLOW)])
        history['after_p2'] = rows(database)
        await phase(options, report, 'p3-offline', [session('status', ''), explain(FOLLOW, expect=False)], offline=True)
        history['after_p3'] = rows(database)
        await phase(options, report, 'p4-recovered', [session('status', ''), explain(FOLLOW)])
        history['after_p4'] = rows(database)
    except Exception as error:
        report['failure'] = f'{type(error).__name__}: {error}'
    finally:
        if database.is_file():
            history['final'] = rows(database)
        stages = list(history.values())
        report['history_rows'] = {key: len(value) for key, value in history.items()}
        report['history_append_only'] = all(all(later.get(k) == v for k, v in earlier.items())
                                            for earlier, later in zip(stages, stages[1:]))
        report['ledger_after'] = spent()
        report['finalized'] = True
        save(options, report)
    print(json.dumps({key: report.get(key) for key in ('failure', 'history_rows', 'history_append_only',
                                                       'ledger_before', 'ledger_after')}, ensure_ascii=False))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--store', required=True)
    parser.add_argument('--output', type=Path, required=True)
    result = asyncio.run(main(parser.parse_args()))
    raise SystemExit(1 if result.get('failure') or not result.get('history_append_only') else 0)
