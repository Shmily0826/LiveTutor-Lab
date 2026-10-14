"""Capture-free text entry: real bootstrap/deployment, temp stores, no devices/providers."""
import importlib.util,json,os,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import httpx
import neko_desktop_tutor_host as host
import neko_tutor_start as start
import neko_native_shell as avatar
spec=importlib.util.spec_from_file_location('actual_text_runtime',host.SOURCE_APP/'main_logic/livetutor_output_only.py')
runtime=importlib.util.module_from_spec(spec);spec.loader.exec_module(runtime)

class TextBootstrap(unittest.IsolatedAsyncioTestCase):
    async def test_text_mode_installs_before_app_and_keeps_nonvoice_json(self):
        app=FastAPI()
        @app.get('/')
        def html():return HTMLResponse('<html><head></head><body><script>originalApp()</script></body></html>')
        @app.get('/data')
        def data():return {'course':'retained'}
        with patch.dict(os.environ,{'NEKO_TEXT_ONLY':'1','NEKO_OUTPUT_ONLY':'0'}):runtime.install_output_only(app)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
            page=await client.get('/');data=await client.get('/data')
        self.assertEqual(page.headers['x-livetutor-audio-mode'],'text-only')
        self.assertIn('microphone=()',page.headers['permissions-policy'])
        self.assertLess(page.text.index('receipt.status'),page.text.index('document.write'))
        self.assertLess(page.text.index("'__NEKO_TEXT_ONLY__'"),page.text.index('document.write'))
        self.assertNotIn('<script>originalApp()',page.text)
        self.assertEqual(data.json(),{'course':'retained'})

class TextStart(unittest.TestCase):
    def test_failed_avatar_cleanup_still_attempts_other_owned_resources(self):
        from unittest.mock import Mock
        launcher=Mock();launcher.poll.return_value=None
        browser=Mock();lesson=Mock();lesson.poll.return_value=None
        with patch.object(start.avatar,'shutdown',side_effect=RuntimeError('test failure')),\
             patch.object(start,'stop_owned_tree') as host_stop,\
             patch.object(start,'remember_browser_tree') as remember,\
             patch.object(start,'stop_owned_browser') as browser_stop:
            errors=start.cleanup_resources(None,{'pid':123},launcher,[],browser,[],lesson)
            host_stop.assert_called_once();launcher.wait.assert_called_once()
            remember.assert_called_once();browser_stop.assert_called_once();lesson.terminate.assert_called_once()
        self.assertEqual(len(errors),1);self.assertIn('avatar',errors[0])

    def test_voice_command_keeps_explicit_offline_and_original_round(self):
        args=SimpleNamespace(text_only=False,offline_egress=True,voice=True,voice_connects='unlimited',budget_round='bargein-autocheck-20261012',learning_surface=True)
        command=start.host_command(1,0,2000,start.host_options(args,['www.lanlan.app']))
        self.assertIn('--offline-egress',command)
        self.assertIn('--voice',command)
        self.assertEqual(command[command.index('--budget-round')+1],args.budget_round)

    def test_native_stale_identity_and_replaced_owner_are_not_stopped_or_deleted(self):
        import subprocess
        stranger=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'])
        try:
            with tempfile.TemporaryDirectory() as folder:
                owner_file=Path(folder)/'avatar.json'
                new_owner={'pid':stranger.pid,'created_at':start.process_creation_time(stranger.pid)}
                owner_file.write_text(json.dumps(new_owner),encoding='utf-8')
                stale={'pid':stranger.pid,'created_at':1.0}
                with patch.object(avatar,'PID_FILE',owner_file):avatar.shutdown(stale)
                self.assertIsNone(stranger.poll())
                self.assertEqual(json.loads(owner_file.read_text()),new_owner)
                with patch.object(avatar,'processes',return_value=[(100,'N.E.K.O.exe',1),(101,avatar.FROZEN_BACKEND,100),(200,avatar.FROZEN_BACKEND,1)]):
                    self.assertEqual(avatar.owned_frozen_backends({'pid':100}),[101])
        finally:
            stranger.kill();stranger.wait(timeout=10)

    def test_mixed_or_fake_input_refused_before_any_startup_work(self):
        for flags in (['--text-only','--voice'],['--text-only','--audio-input','fake.wav']):
            with patch.object(sys,'argv',['tutor',*flags]),patch.object(host,'read_key') as key,patch.object(start.subprocess,'Popen') as spawn:
                with self.assertRaises(SystemExit) as result:start.main()
                self.assertEqual(result.exception.code,2);key.assert_not_called();spawn.assert_not_called()
        with patch.object(avatar,'verify_output_only_host') as verify,patch.object(avatar.subprocess,'Popen') as spawn:
            with self.assertRaisesRegex(RuntimeError,'capture devices'):avatar.launch(Path('unused'),audio_input='fake.wav',text_only=True)
            verify.assert_not_called();spawn.assert_not_called()

    def test_unprotected_native_host_is_refused_even_in_strict_silence(self):
        with patch.dict(os.environ,{'NEKO_TASK_SILENT':'1'}),\
             patch.object(host,'require_task_audio_allowed',side_effect=AssertionError('mixed gate forbidden')),\
             patch.object(host,'require_task_speaker_output_allowed',side_effect=AssertionError('speaker gate unnecessary')),\
             patch.object(avatar,'verify_output_only_host',side_effect=RuntimeError('unprotected host')) as verify,\
             patch.object(avatar.subprocess,'Popen') as spawn:
            with self.assertRaisesRegex(RuntimeError,'unprotected'):avatar.launch(Path('unused'),text_only=True)
            verify.assert_called_once_with('text-only');spawn.assert_not_called()

    def test_text_browser_is_muted_and_has_no_fake_capture_flags(self):
        with patch.dict(os.environ,{'NEKO_TASK_SILENT':'1'}),patch.object(host,'require_task_audio_allowed',side_effect=AssertionError('mixed gate forbidden')):
            command=start.chrome_command('http://127.0.0.1:48916/plugin/study_companion/ui/',text_only=True)
        self.assertIn('--mute-audio',command)
        self.assertFalse(any('fake' in flag or 'media-stream' in flag for flag in command))

    def test_study_html_is_protected_only_in_task_deployment(self):
        canonical=(host.PRODUCT/'static/index.html').read_bytes()
        with tempfile.TemporaryDirectory() as folder:
            store=Path(folder)
            host.prepare_product_plugin(store,text_only=True)
            page=store/'plugin-code/study_companion/static/index.html'
            protected=page.read_text(encoding='utf-8')
            self.assertIn('NekoCapturePolicy.installOutputOnly({enabled:true})',protected)
            self.assertIn('__NEKO_TEXT_ONLY__',protected)
            host.prepare_product_plugin(store)
            self.assertEqual(page.read_bytes(),canonical)
        self.assertEqual((host.PRODUCT/'static/index.html').read_bytes(),canonical)

    def test_bad_saved_host_configuration_is_preserved_and_unknown_settings_retained(self):
        with tempfile.TemporaryDirectory() as folder:
            store=Path(folder);config=store/'N.E.K.O/config/core_config.json';config.parent.mkdir(parents=True)
            for payload in (b'broken',b'[]'):
                config.write_bytes(payload)
                with self.assertRaisesRegex(RuntimeError,'已保留原文件'):host.prepare_store('test-only-placeholder',store)
                self.assertEqual(config.read_bytes(),payload)
            config.write_text(json.dumps({'learner_setting':{'value':7}}),encoding='utf-8')
            host.prepare_store('test-only-placeholder',store)
            self.assertEqual(json.loads(config.read_text(encoding='utf-8'))['learner_setting'],{'value':7})

if __name__=='__main__':unittest.main(verbosity=2)
