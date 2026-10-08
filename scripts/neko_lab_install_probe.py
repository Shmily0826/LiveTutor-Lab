"""Verify the official source-package route with a fresh diagnostic identity."""
import json
from pathlib import Path
import shutil
import sys
import urllib.error

from neko_lab_client import LabClient
from neko_lab_diagnostic_plugin import SOURCE
from neko_lab_stage import LIVE, ROOT

PLUGIN = 'study_lab_probe_installed'


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    source = (LIVE.parent / PLUGIN).resolve()
    archive = (ROOT / 'benchmarks/raw/goal-isolated' / PLUGIN).resolve()
    if not source.is_relative_to(ROOT) or not archive.is_relative_to(ROOT):
        raise RuntimeError('diagnostic source paths escaped workspace')
    if source.exists() or archive.exists():
        raise RuntimeError('fresh diagnostic identity is already occupied')
    source.mkdir()
    (source / '__init__.py').write_text(SOURCE, encoding='utf-8')
    template = (ROOT / 'benchmarks/raw/goal-isolated/installed-probe-source/plugin.toml').read_text(encoding='utf-8')
    (source / 'plugin.toml').write_text(template.replace('study_lab_probe',PLUGIN),encoding='utf-8')
    client = LabClient(plugin=PLUGIN)
    client.request('/plugins/refresh','POST',{},timeout=30)
    package = ROOT / f'benchmarks/raw/neko-store/.neko-plugin-packages/{PLUGIN}.neko-plugin'
    built = client.request('/plugin-cli/build','POST',{
        'mode':'single','plugin':PLUGIN,'out':str(package)},timeout=40)
    if not built.get('ok'):
        raise RuntimeError('official build did not succeed')
    shutil.move(source, archive)
    client.request('/plugins/refresh','POST',{},timeout=30)
    plan = client.request('/plugin-cli/install-plan','POST',{'package':str(package)},timeout=30)
    print('install_plan',json.dumps(plan,ensure_ascii=False))
    if plan.get('action') == 'blocked':
        return
    installed = client.request('/plugin-cli/install','POST',{
        'package':str(package),'on_conflict':'fail','install_source':'imported'},timeout=40)
    print('installed',json.dumps(installed,ensure_ascii=False)[:1600])
    client.request('/plugins/refresh','POST',{},timeout=30)
    try:
        print('start',client.request(f'/plugin/{PLUGIN}/start','POST',{},timeout=30))
    except urllib.error.HTTPError as error:
        print('start_error',error.code,error.read(1000).decode())


if __name__ == '__main__':
    main()
