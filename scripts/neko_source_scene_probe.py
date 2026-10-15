"""Text-only Study SDK scenes over the authorized Sky Scout project (muted, no Native/audio).

One fresh task store per scene (authorization copied, learning DB new), one owned host, bounded
external calls. Every turn keeps the request, the reply, the source evidence and the stage timings
so the answer can be checked against the read-only source by hand.
The scenes are data: add a name to SCENES to cover another question type.
"""
import argparse
import asyncio
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import time

from neko_daily_code_dialogue_probe import cleanup_probe_host, host_command, prepare_contrast_grant
from neko_native_avatar_toolchain import call
from neko_relevant_history_probe import remember_children
from neko_tutor_start import plugin_server_ready, process_creation_time

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / 'benchmarks/raw/neko-desktop-egress-cap'
SYNC_SEED = ROOT / 'benchmarks/raw/neko-daily-code-contrast-20261015-m5/N.E.K.O/plugins/study_companion/data/code_sync_state.json'
COURSE = 'sky-scout-scene'
CLIENT = 'app_sky_scout/lib/data/services/weather_service.dart'
SERVER = 'server/routes/weather.js'


def explain(question, requests=None, **extra):
    arguments = {'material_source': 'project_code', 'question': question}
    if requests is not None:
        arguments['code_requests'] = requests
    return {'tool': 'study_explain', 'arguments': arguments, **extra}


def start(course=COURSE):
    return {'tool': 'study_session', 'arguments': {'action': 'start', 'course_id': course}}


SCENES = {
    # W1: an index that has not changed must not be re-synced, and a bare file name is resolved
    # from the cached listing the second time.
    'w1text': [
        start(),
        explain('weather_service.dart 在请求天气失败时是怎么处理的？两句中文。',
                [{'mode': 'explore', 'query': 'weather_service.dart 请求天气失败时如何处理非200响应'}],
                note='explore turn: expect index_sync=unchanged and no source_retry_query'),
        explain('把 weather_service.dart 的请求部分讲两句中文。',
                [{'mode': 'file', 'file': 'weather_service.dart', 'offset': 13, 'limit': 16}],
                note='bare file name, first inventory read'),
        explain('再看一下 api_config.dart 里的内容，两句中文。',
                [{'mode': 'file', 'file': 'api_config.dart', 'offset': 1, 'limit': 30}],
                note='second bare file name in the same host: inventory from cache'),
    ],
    'w2structure': [
        start(),
        explain('这个项目大概分成哪几个部分？各部分是做什么的？三句中文以内。', [{'mode': 'structure'}], kind='structure'),
    ],
    # W2: five source-teaching question kinds on the one authorized project.
    'w2kinds': [
        start(),
        explain('这个项目大概分成哪几个部分？各部分是做什么的？三句中文以内。',
                [{'mode': 'structure'}], kind='structure'),
        explain('客户端的天气请求最后是怎么到服务端、又是怎么回到客户端的？按顺序说，三句中文以内。',
                [{'mode': 'file', 'file': CLIENT, 'offset': 8, 'limit': 21},
                 {'mode': 'file', 'file': SERVER, 'offset': 1, 'limit': 25}], kind='cross-file'),
        explain('weather_service.dart 的第 22 行是什么意思？一句中文。',
                [{'mode': 'file', 'file': CLIENT, 'offset': 20, 'limit': 8}], kind='line-meaning'),
        explain('如果把 weather.js 里非法坐标时返回的 400 改成 404，客户端那边会有什么变化？三句中文以内，不确定的地方说明是推断。',
                [{'mode': 'file', 'file': SERVER, 'offset': 1, 'limit': 25},
                 {'mode': 'file', 'file': CLIENT, 'offset': 20, 'limit': 8}], kind='change-impact'),
        explain('我觉得服务端天气请求失败时会返回 200 和空数据，客户端再自己判断，对吗？请按源码核对，两句中文。',
                None, kind='wrong-claim-recheck'),
    ],
}


def spent():
    return json.loads(LEDGER.read_text(encoding='utf-8'))['spent']


def save(output, report):
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


async def main(options):
    for port in (48911, 48916, 9234):
        with socket.socket() as check:
            if check.connect_ex(('127.0.0.1', port)) == 0:
                raise RuntimeError('An existing host owns a required port; do not replace it.')
    before = json.loads(LEDGER.read_text(encoding='utf-8'))
    if before['round'] != 'bargein-autocheck-20261012' or before['spent'].get('api.deepseek.com', 0) >= 1980:
        raise RuntimeError('Preserve the approved round and leave room for this bounded scene.')
    options.contrast_only = True
    prepare_contrast_grant(options)
    data = ROOT / 'benchmarks/raw' / options.store / 'N.E.K.O/plugins/study_companion/data'
    if options.seed_sync_state:
        # The user's real install has synced this tree before; a fresh store would otherwise
        # always start with a full sync. The fingerprint is checked against the live tree anyway.
        shutil.copyfile(SYNC_SEED, data / 'code_sync_state.json')
    steps = SCENES[options.scenario]
    report = {'scenario': options.scenario, 'store': options.store, 'started_wall': time.time(),
              'ledger_before': before['spent'], 'turns': [], 'text_only': True, 'native': False,
              'microphone': False, 'seeded_sync_state': bool(options.seed_sync_state)}
    with options.output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream)
    log = ROOT / 'benchmarks/raw/neko-desktop-host.log'
    log_start = log.stat().st_size if log.exists() else 0
    command = host_command(options)
    command[command.index('--api-budget') + 1] = str(3 * len(steps))
    command[command.index('--hold') + 1] = '420'
    handle = options.output.with_suffix('.host.log').open('xb')
    process = tracker = None
    ownership = []
    try:
        process = subprocess.Popen(command, cwd=ROOT, env={**os.environ, 'NEKO_TASK_SILENT': '1', 'PYTHONIOENCODING': 'utf-8'},
                                   stdout=handle, stderr=subprocess.STDOUT)
        created = process_creation_time(process.pid)
        ownership = [{'pid': process.pid, 'created_at': created}]

        async def track():
            while process.poll() is None:
                remember_children(process, ownership)
                await asyncio.sleep(0.25)
        tracker = asyncio.create_task(track())
        ready, reason = await asyncio.to_thread(plugin_server_ready, 90, process)
        report['ready'] = ready
        if not ready:
            raise RuntimeError('Study readiness failed: ' + reason)
        for step in steps:
            started = time.monotonic()
            result = await asyncio.to_thread(call, step['tool'], step['arguments'], timeout=95)
            output = result.get('output', {}) if isinstance(result, dict) else {}
            turn = {key: step[key] for key in ('kind', 'note') if key in step}
            turn.update(tool=step['tool'], arguments=step['arguments'], ms=round((time.monotonic() - started) * 1000),
                        ok=output.get('ok', True) is not False and not output.get('degraded') and not result.get('is_error'),
                        error=output.get('error') or output.get('diagnostic') or '',
                        reply=str(output.get('reply') or ''), source_evidence=output.get('source_evidence'))
            report['turns'].append(turn)
            report['ledger_now'] = spent()
            save(options.output, report)
            if spent().get('api.deepseek.com', 0) - before['spent'].get('api.deepseek.com', 0) >= options.ceiling:
                raise RuntimeError('Scene external-call ceiling reached; stop without retry.')
            if not turn['ok']:
                raise RuntimeError(f"{step['tool']} failed: {turn['error']}")
    except Exception as error:
        report['failure'] = f'{type(error).__name__}: {error}'
    finally:
        if tracker is not None:
            tracker.cancel()
            await asyncio.gather(tracker, return_exceptions=True)
        if process is not None:
            try:
                await asyncio.to_thread(cleanup_probe_host, process, ownership)
            except Exception as error:
                report['cleanup_error'] = f'{type(error).__name__}: {error}'
            report['owned_host_exit'] = process.poll()
        handle.close()
        timings = []
        if log.is_file():
            with log.open('rb') as stream:
                stream.seek(log_start)
                for match in re.finditer(r'study_code_timing (\{[^\r\n]+\})', stream.read().decode('utf-8', 'replace')):
                    timings.append(json.loads(match.group(1)))
        report['timings'] = timings
        explains = [turn for turn in report['turns'] if turn['tool'] == 'study_explain']
        for turn, timing in zip(explains, timings):
            turn['stages'] = [(item['name'], item['elapsed_ms']) for item in timing['stages']]
            turn['total_ms'] = timing['total_ms']
        report['ledger_after'] = spent()
        report['finalized'] = True
        save(options.output, report)
    print(json.dumps({key: report.get(key) for key in ('failure', 'cleanup_error', 'ledger_before', 'ledger_after')}, ensure_ascii=False))
    for turn in report['turns']:
        print('-', turn.get('kind') or turn['tool'], turn['ms'], 'ms', '|', turn['reply'][:200].replace('\n', ' '))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--store', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--scenario', choices=sorted(SCENES), required=True)
    parser.add_argument('--seed-sync-state', action='store_true')
    parser.add_argument('--ceiling', type=int, default=30)
    result = asyncio.run(main(parser.parse_args()))
    raise SystemExit(1 if result.get('failure') or result.get('cleanup_error') else 0)
