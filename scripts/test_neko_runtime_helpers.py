"""Real child imports in a temporary launcher cwd, no app/devices/providers."""
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from neko_runtime_helpers import deploy_runtime_helpers,verify_runtime_helpers
ROOT=Path(__file__).resolve().parents[1]
NAMES=('neko_phrase_input_buffer.py','neko_phrase_input_transport.py','neko_study_answer_intent.py')

class RuntimeHelpers(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='neko-host-helpers-');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.host=self.root/'host';self.host.mkdir();(self.root/'scripts').mkdir()
        self.manifest={'runtime_helpers':[]}
        for name in NAMES:
            raw=(ROOT/'scripts'/name).read_bytes();(self.root/'scripts'/name).write_bytes(raw)
            self.manifest['runtime_helpers'].append({'path':'scripts/'+name,'sha256':hashlib.sha256(raw).hexdigest(),'deployed_path':name})
    def verify(self):verify_runtime_helpers(self.root,self.host,self.manifest,Path(sys.executable))
    def test_actual_launcher_path_failed_before_deploy_and_imports_after(self):
        # Windows venv can also search its parent host, which is now deployed.
        # An import from there must not stand in for this launcher's own file.
        check="import pathlib,neko_phrase_input_transport as m; assert pathlib.Path(m.__file__).resolve()==pathlib.Path.cwd()/'neko_phrase_input_transport.py'"
        before=subprocess.run([sys.executable,'-E','-B','-c',check],cwd=self.host,capture_output=True)
        self.assertNotEqual(before.returncode,0)
        self.assertEqual(set(deploy_runtime_helpers(self.root,self.host,self.manifest)),set(NAMES))
        self.verify()
        self.assertFalse((self.host/'__pycache__').exists())
    def test_missing_or_modified_deployed_dependency_refuses_verification(self):
        deploy_runtime_helpers(self.root,self.host,self.manifest)
        (self.host/NAMES[0]).unlink()
        with self.assertRaisesRegex(RuntimeError,'deployed.*fingerprint'):self.verify()
        (self.host/NAMES[0]).write_text('different source',encoding='utf-8')
        with self.assertRaisesRegex(RuntimeError,'deployed.*fingerprint'):self.verify()
    def test_unknown_target_preserved_without_partial_copy(self):
        (self.host/NAMES[1]).write_bytes(b'unknown user code')
        with self.assertRaisesRegex(RuntimeError,'unexpected deployed'):deploy_runtime_helpers(self.root,self.host,self.manifest)
        self.assertEqual((self.host/NAMES[1]).read_bytes(),b'unknown user code')
        self.assertFalse((self.host/NAMES[0]).exists())
    def test_unknown_concurrent_create_is_never_overwritten(self):
        target=self.host/NAMES[0];original=Path.open
        def concurrent(path,*args,**kwargs):
            if path==target and args and args[0]=='xb':
                target.write_bytes(b'concurrent unknown code')
            return original(path,*args,**kwargs)
        with patch.object(Path,'open',concurrent):
            with self.assertRaisesRegex(RuntimeError,'unexpected deployed'):deploy_runtime_helpers(self.root,self.host,self.manifest)
        self.assertEqual(target.read_bytes(),b'concurrent unknown code')
        self.assertFalse((self.host/NAMES[1]).exists())
    def test_identical_concurrent_winner_is_accepted(self):
        target=self.host/NAMES[0];original=Path.open;raw=(self.root/'scripts'/NAMES[0]).read_bytes()
        def concurrent(path,*args,**kwargs):
            if path==target and args and args[0]=='xb':target.write_bytes(raw)
            return original(path,*args,**kwargs)
        with patch.object(Path,'open',concurrent):deploy_runtime_helpers(self.root,self.host,self.manifest)
        self.verify()
    def test_bad_source_hash_refused_before_any_copy(self):
        self.manifest['runtime_helpers'][1]['sha256']='0'*64
        with self.assertRaisesRegex(RuntimeError,'source fingerprint'):deploy_runtime_helpers(self.root,self.host,self.manifest)
        self.assertEqual(list(self.host.iterdir()),[])
    def test_incomplete_duplicate_and_escaping_manifest_refused(self):
        for entries in (self.manifest['runtime_helpers'][:1],self.manifest['runtime_helpers']*2,
                        [{**self.manifest['runtime_helpers'][0],'deployed_path':'../config.json'}]):
            with self.subTest(entries=entries):
                with self.assertRaises(RuntimeError):deploy_runtime_helpers(self.root,self.host,{'runtime_helpers':entries})
        self.assertEqual(list(self.host.iterdir()),[])
    def test_host_outside_project_refused_before_source_copy(self):
        with self.assertRaisesRegex(RuntimeError,'host escapes project'):
            deploy_runtime_helpers(self.root/'scripts',self.host,self.manifest)
        with self.assertRaisesRegex(RuntimeError,'host escapes project'):
            verify_runtime_helpers(self.root/'scripts',self.host,self.manifest,Path(sys.executable))
        self.assertEqual(list(self.host.iterdir()),[])
    def test_deploy_idempotent_and_import_failure_is_fail_closed(self):
        deploy_runtime_helpers(self.root,self.host,self.manifest);before={name:(self.host/name).stat().st_mtime_ns for name in NAMES}
        deploy_runtime_helpers(self.root,self.host,self.manifest)
        self.assertEqual(before,{name:(self.host/name).stat().st_mtime_ns for name in NAMES})
        raw=b'raise RuntimeError("broken helper")\n';(self.host/NAMES[1]).write_bytes(raw)
        (self.root/'scripts'/NAMES[1]).write_bytes(raw)
        self.manifest['runtime_helpers'][1]['sha256']=hashlib.sha256(raw).hexdigest()
        with self.assertRaisesRegex(RuntimeError,'import preflight failed'):self.verify()

if __name__=='__main__':unittest.main()
