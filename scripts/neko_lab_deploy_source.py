"""Reversible source-entry deployment, preserving the existing Study database.

The temporary process-loop hook must have passed neko_lab_loop_probe.py first.
Rollback restores files and requires a backend restart to discard import caches.
"""
import argparse
import hashlib
import json
import shutil
from neko_lab_stage import LIVE, ISOLATED, ROOT
from neko_lab_client import LabClient

BACKUP = ROOT/'benchmarks/raw/evidence/goal-backups/source-deployment'
BRIDGE = LIVE.parents[2]/'plugins/study_companion'
FILES = ('__init__.py','entry_status_entries.py','entry_neko_commands.py','llm_prompts.py','entry_ocr_entries.py','plugin.toml')


def main():
    args = argparse.ArgumentParser()
    args.add_argument('--rollback',action='store_true')
    options = args.parse_args()
    client = LabClient()
    if options.rollback:
        client.request('/plugin/study_companion/stop','POST',{})
        for name in FILES:
            shutil.copy2(BACKUP/name,LIVE/name)
        print('Original compiled entry and source files restored. Restart the owned backend before starting Study.')
        return
    if BACKUP.exists() or BRIDGE.exists():
        raise RuntimeError('Deployment paths already exist; inspect before overwriting')
    client.request('/plugin/study_companion/stop','POST',{})
    BACKUP.mkdir(parents=True)
    hashes = {}
    for name in FILES:
        shutil.copy2(LIVE/name,BACKUP/name)
        hashes[name] = hashlib.sha256((LIVE/name).read_bytes()).hexdigest()
    (BACKUP/'manifest.json').write_text(json.dumps(hashes,indent=2),encoding='utf-8')
    shutil.copytree(ISOLATED,BRIDGE,ignore=shutil.ignore_patterns('__pycache__'))
    bootstrap = '''from plugins.lab_study_runtime import install
install("study_companion")
from . import StudyCompanionPlugin
'''
    for directory in (LIVE,BRIDGE):
        (directory/'lab_bootstrap.py').write_text(bootstrap,encoding='utf-8')
    for name in FILES[:-1]:
        shutil.copy2(ISOLATED/name,LIVE/name)
    text = (LIVE/'plugin.toml').read_text(encoding='utf-8')
    before = 'entry = "plugin.plugins.study_companion:StudyCompanionPlugin"'
    if text.count(before) != 1:
        raise RuntimeError('Original entry mismatch; deployment not activated')
    (LIVE/'plugin.toml').write_text(text.replace(before,
        'entry = "plugins.study_companion.lab_bootstrap:StudyCompanionPlugin"'),encoding='utf-8')
    client.request('/plugins/refresh','POST',{},timeout=40)
    print(client.request('/plugin/study_companion/start','POST',{},timeout=40))
    print('Source entry started; verify actual status and UI before declaring success.')


if __name__ == '__main__':
    main()
