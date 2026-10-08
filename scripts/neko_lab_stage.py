"""Stage a backed-up runtime diagnostic without reading model credentials."""
from pathlib import Path
import hashlib
import json
import shutil
import sqlite3
import time

ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / 'benchmarks/raw/neko-app/resources/bin/plugin/plugins/study_companion'
ISOLATED = ROOT / 'benchmarks/raw/goal-isolated/study_companion'
BACKUP = ROOT / 'benchmarks/raw/evidence/goal-backups'
DB = ROOT / 'benchmarks/raw/neko-store/plugins/study_companion/data/study_companion.db'

PROBE = '''    @plugin_entry(id="study_lab_runtime_probe", name="Lab runtime probe",
                  description="Version and task-stack diagnostics; no credentials.")
    async def study_lab_runtime_probe(self, **_):
        def task_stack(task):
            chain = []
            current = task.get_coro() if task is not None else None
            for _index in range(20):
                if current is None:
                    break
                code = getattr(current, "cr_code", None) or getattr(current, "gi_code", None)
                frame = getattr(current, "cr_frame", None) or getattr(current, "gi_frame", None)
                if code is not None:
                    chain.append({"function": code.co_name, "file": code.co_filename,
                                  "line": frame.f_lineno if frame is not None else None})
                current = getattr(current, "cr_await", None) or getattr(current, "gi_yieldfrom", None)
            return chain
        code = getattr(get_os_activity_snapshot, "__code__", None)
        task = self._awareness_task
        return Ok({"awareness_active": self.is_awareness_active(),
                   "awareness_enabled": self._cfg.awareness.enabled,
                   "awareness_stack": task_stack(task),
                   "activity_helper": {"file": code.co_filename if code else None,
                                       "names": list(code.co_names) if code else []},
                   "command_watcher": self._neko_command_watcher is not None,
                   "command_transport": self._neko_command_transport is not None,
                   "os_read_failures": self._consecutive_os_read_failures,
                   "plugin_source": __file__})

'''


def main():
    BACKUP.mkdir(parents=True, exist_ok=True)
    if (BACKUP / 'manifest.json').exists():
        raise RuntimeError('backup already exists; do not overwrite the original')
    shutil.copytree(LIVE, ISOLATED)
    files = {}
    for name in ('__init__.py', 'entry_status_entries.py', 'entry_neko_commands.py', 'store.py'):
        source = LIVE / name
        shutil.copy2(source, BACKUP / name)
        files[name] = hashlib.sha256(source.read_bytes()).hexdigest()
    source_db = sqlite3.connect(DB)
    backup_db = sqlite3.connect(BACKUP / 'study_companion.db')
    try:
        source_db.backup(backup_db)
        value = source_db.execute("SELECT value FROM kv WHERE key='config'").fetchone()
        (BACKUP / 'original-study-config.json').write_text(value[0], encoding='utf-8')
    finally:
        backup_db.close()
        source_db.close()
    (BACKUP / 'manifest.json').write_text(json.dumps(
        {'created_at': time.time(), 'live': str(LIVE), 'files': files}, indent=2), encoding='utf-8')
    for directory in (ISOLATED, LIVE):
        target = directory / '__init__.py'
        text = target.read_text(encoding='utf-8')
        anchor = '    async def _run_awareness_loop(self) -> None:\n'
        if text.count(anchor) != 1:
            raise RuntimeError('unexpected source layout')
        text = text.replace(anchor, PROBE + anchor)
        compile(text, str(target), 'exec')
        target.write_text(text, encoding='utf-8')
    print(json.dumps({'backed_up_files': list(files), 'diagnostic_staged': True}))


if __name__ == '__main__':
    main()
