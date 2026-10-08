"""Prepare reviewable patches; never changes or restarts the packaged app."""
import ast
import difflib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'benchmarks/raw/goal-isolated/study_companion'
LIVE = ROOT/'benchmarks/raw/neko-app/resources/bin/plugin/plugins/study_companion'
BASE_SOURCE = ROOT/'benchmarks/raw/evidence/goal-backups/source-deployment'
BASE_UI = ROOT/'benchmarks/raw/evidence/goal-backups/ui-followup'
CORE = ROOT/'candidates/N.E.K.O/plugin/core/host.py'
OUT = ROOT/'patches/neko-study-2026-10-08'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    # Discard the read-only probe from the isolated entry before exporting fixes.
    entry = SOURCE/'__init__.py'
    text = entry.read_text(encoding='utf-8')
    start = text.find('    @plugin_entry(id="study_lab_runtime_probe"')
    if start >= 0:
        end = text.index('    async def _run_awareness_loop', start)
        text = text[:start]+text[end:]
        entry.write_text(text, encoding='utf-8')
    changes = []
    for name in ('__init__.py','entry_status_entries.py','entry_neko_commands.py','entry_ocr_entries.py','llm_prompts.py',
                 'static/main.js','static/index.html','static/style.css','i18n/zh-CN.json','i18n/en.json'):
        baseline = BASE_UI if name.startswith(('static/','i18n/')) else BASE_SOURCE
        old = (baseline/name).read_text(encoding='utf-8')
        new = (SOURCE/name).read_text(encoding='utf-8')
        if name.endswith('.py'):
            ast.parse(new)
        path = f'plugin/plugins/study_companion/{name}'
        changes.extend(difflib.unified_diff(old.splitlines(True),new.splitlines(True),
                                          fromfile='a/'+path,tofile='b/'+path))
    (OUT/'study.patch').write_text(''.join(changes),encoding='utf-8')

    old = CORE.read_text(encoding='utf-8')
    begin = old.index('def _plugin_process_runner(')
    end = old.index('\n_PLUGIN_HOSTS:',begin)
    body = old[begin:end].replace('def _plugin_process_runner(', 'def _plugin_process_runner_on_loop(',1)
    body = body.replace('    model_gateway_options: dict[str, str] | None = None,',
                        '    model_gateway_options: dict[str, str] | None = None,\n    _loop_runner: asyncio.Runner,',1)
    body = body.replace('asyncio.run(', '_loop_runner.run(')
    thread_call = '_loop_runner.run(_run_with_model_client_cleanup(ctx, fn()))'
    if body.count(thread_call) != 2:
        raise RuntimeError('unexpected threaded handler layout')
    body = body.replace(thread_call,
        'asyncio.run_coroutine_threadsafe(fn(), _loop_runner.get_loop()).result()')
    wrapper = '''def _plugin_process_runner(*args: Any, **kwargs: Any) -> None:
    # Startup, background tasks, entries and shutdown own one process loop.
    # Runner closes it only after the complete process lifecycle ends.
    with asyncio.Runner() as runner:
        _plugin_process_runner_on_loop(*args, _loop_runner=runner, **kwargs)


'''
    new = old[:begin]+wrapper+body+old[end:]
    ast.parse(new)
    destination = ROOT/'benchmarks/raw/goal-isolated/host.py'
    destination.write_text(new,encoding='utf-8')
    (OUT/'host-loop.patch').write_text(''.join(difflib.unified_diff(
        old.splitlines(True),new.splitlines(True),fromfile='a/plugin/core/host.py',
        tofile='b/plugin/core/host.py')),encoding='utf-8')
    print('Prepared isolated source patches; packaged runtime unchanged.')


if __name__ == '__main__':
    main()
