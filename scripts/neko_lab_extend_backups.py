"""Add previously untouched OCR/style originals to the existing owned backups."""
import hashlib
import json
import shutil
from neko_lab_stage import LIVE,ROOT


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ui = ROOT/'benchmarks/raw/evidence/goal-backups/ui-followup'
    style = ui/'static/style.css'
    if style.exists():
        raise RuntimeError('Style original already saved; refusing overwrite')
    shutil.copy2(LIVE/'static/style.css',style)
    manifest = ui/'manifest.json'
    value = json.loads(manifest.read_text(encoding='utf-8'))
    value['static/style.css'] = {'original':digest(style),'applied':digest(LIVE/'static/style.css')}
    manifest.write_text(json.dumps(value,indent=2),encoding='utf-8')
    backend = ROOT/'benchmarks/raw/evidence/goal-backups/source-deployment'
    manifest = backend/'manifest.json'
    value = json.loads(manifest.read_text(encoding='utf-8'))
    value['entry_ocr_entries.py'] = digest(backend/'entry_ocr_entries.py')
    manifest.write_text(json.dumps(value,indent=2),encoding='utf-8')
    print('Original backups extended without overwriting existing originals.')


if __name__ == '__main__':
    main()
