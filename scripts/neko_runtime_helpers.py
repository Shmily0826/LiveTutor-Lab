"""Deploy and verify the standard-library voice helpers in the actual host.

Tests started from scripts/ used to hide their absence from launcher.py's path.
"""
from __future__ import annotations
import ast
import hashlib
from pathlib import Path
import subprocess

_HELPERS={'neko_phrase_input_buffer.py','neko_phrase_input_transport.py','neko_study_answer_intent.py'}

def helper_plan(project_root: Path, manifest: dict):
    plan=[]
    for item in manifest.get('runtime_helpers',[]):
        destination=item.get('deployed_path')
        if destination is None:continue
        if destination not in _HELPERS or item.get('path')!='scripts/'+destination:
            raise RuntimeError('unexpected phrase runtime helper path; preserve source')
        source=project_root/item['path']
        if source.is_symlink() or not source.resolve().is_relative_to(project_root.resolve()):
            raise RuntimeError('phrase runtime helper source escapes project; preserve source')
        raw=source.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=item['sha256']:
            raise RuntimeError('phrase runtime helper source fingerprint differs: '+destination)
        ast.parse(raw.decode('utf-8'),filename=str(source))
        plan.append((destination,raw))
    if {name for name,_ in plan}!=_HELPERS or len(plan)!=len(_HELPERS):
        raise RuntimeError('phrase runtime helper deployment manifest incomplete')
    return plan

def deploy_runtime_helpers(project_root: Path, host_root: Path, manifest: dict):
    if host_root.is_symlink() or not host_root.resolve().is_relative_to(project_root.resolve()):
        raise RuntimeError('phrase runtime helper host escapes project; preserve source')
    plan=helper_plan(project_root,manifest)
    # Validate both targets before any copy; never overwrite unknown code.
    for name,raw in plan:
        target=host_root/name
        if target.is_symlink() or (target.exists() and target.read_bytes()!=raw):
            raise RuntimeError('unexpected deployed phrase runtime helper; preserve source: '+name)
    for name,raw in plan:
        target=host_root/name
        try:
            with target.open('xb') as output:output.write(raw)
        except FileExistsError:
            # A concurrent launcher may win; accept only the same regular file.
            if target.is_symlink() or not target.is_file() or target.read_bytes()!=raw:
                raise RuntimeError('unexpected deployed phrase runtime helper; preserve source: '+name) from None
    return [name for name,_ in plan]

def verify_runtime_helpers(project_root: Path, host_root: Path, manifest: dict, python: Path):
    if host_root.is_symlink() or not host_root.resolve().is_relative_to(project_root.resolve()):
        raise RuntimeError('phrase runtime helper host escapes project; preserve source')
    plan=helper_plan(project_root,manifest)
    for name,raw in plan:
        target=host_root/name
        if target.is_symlink() or not target.is_file() or target.read_bytes()!=raw:
            raise RuntimeError('deployed phrase runtime helper fingerprint differs: '+name)
    # Reproduce launcher's cwd/import path. No scripts/ injection or app imports.
    check='''import importlib,pathlib,sys
root=pathlib.Path(sys.argv[1]).resolve()
for name in ('neko_phrase_input_buffer','neko_phrase_input_transport','neko_study_answer_intent'):
    module=importlib.import_module(name)
    assert pathlib.Path(module.__file__).resolve()==root/(name+'.py'), name
assert callable(module.answer_intent) and callable(module.read_question_pin)
'''
    try:
        subprocess.run([str(python),'-E','-B','-c',check,str(host_root)],cwd=host_root,
            check=True,capture_output=True,timeout=10)
    except (OSError,subprocess.SubprocessError):
        raise RuntimeError('phrase runtime helper import preflight failed; do not start host') from None
