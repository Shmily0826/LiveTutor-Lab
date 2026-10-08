"""Select a unique source entry for a frozen app; reversible manifest change."""
from pathlib import Path
import json
import shutil
import sys

from neko_lab_client import LabClient
from neko_lab_stage import LIVE, BACKUP, ISOLATED


def main():
    client = LabClient()
    client.request('/plugin/study_companion/stop', 'POST', {})
    manifest = LIVE / 'plugin.toml'
    backup = BACKUP / 'plugin.toml'
    if backup.exists():
        raise RuntimeError('manifest backup exists; do not overwrite it')
    shutil.copy2(manifest, backup)
    shutil.copy2(LIVE / '__init__.py', LIVE / 'lab_entry.py')
    shutil.copy2(BACKUP / '__init__.py', LIVE / '__init__.py')
    text = manifest.read_text(encoding='utf-8')
    old = 'entry = "plugin.plugins.study_companion:StudyCompanionPlugin"'
    if text.count(old) != 1:
        raise RuntimeError('unexpected plugin entry')
    manifest.write_text(text.replace(old,
        'entry = "plugin.plugins.study_companion.lab_entry:StudyCompanionPlugin"'), encoding='utf-8')
    print(json.dumps(client.request('/plugin/study_companion/reload', 'POST', {}, timeout=40)))


if __name__ == '__main__':
    main()
