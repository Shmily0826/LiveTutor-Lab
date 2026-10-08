"""Apply/undo only the backed-up local Study follow-up UI; no database writes."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT/'benchmarks/raw/neko-app/resources/bin/plugin/plugins/study_companion'
SOURCE = ROOT/'benchmarks/raw/goal-isolated/study_companion'
BACKUP = ROOT/'benchmarks/raw/evidence/goal-backups/ui-followup'
FILES = ('static/main.js','static/index.html','static/style.css','i18n/en.json','i18n/zh-CN.json')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--rollback',action='store_true')
    parser.add_argument('--refresh',action='store_true')
    args = parser.parse_args()
    manifest = BACKUP/'manifest.json'
    if args.rollback:
        entries = json.loads(manifest.read_text(encoding='utf-8'))
        for name, hashes in entries.items():
            if digest(LIVE/name) != hashes['applied']:
                raise RuntimeError(f'{name}: changed since deployment; refusing overwrite')
        for name in entries:
            shutil.copy2(BACKUP/name,LIVE/name)
        print('Restored original UI; reload the task-created Study page.')
        return
    if args.refresh:
        entries = json.loads(manifest.read_text(encoding='utf-8'))
        for name in FILES:
            if digest(LIVE/name) != entries[name]['applied']:
                raise RuntimeError(f'{name}: changed since deployment; refusing overwrite')
            entries[name]['applied'] = digest(SOURCE/name)
        for name in FILES:
            shutil.copy2(SOURCE/name,LIVE/name)
        manifest.write_text(json.dumps(entries,indent=2),encoding='utf-8')
        print('Updated owned UI patch; original backup preserved.')
        return
    if manifest.exists():
        raise RuntimeError('Original backup already exists; refusing overwrite')
    entries = {}
    for name in FILES:
        target = BACKUP/name
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(LIVE/name,target)
        entries[name] = {'original':digest(target),'applied':digest(SOURCE/name)}
    manifest.write_text(json.dumps(entries,indent=2),encoding='utf-8')
    for name in FILES:
        shutil.copy2(SOURCE/name,LIVE/name)
    print('Applied five UI/i18n files; backend code and user records preserved.')


if __name__ == '__main__':
    main()
