"""Real ASGI middleware, pinned patch, and pre-spawn permissions; no devices/egress."""
import asyncio
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, Response
import httpx
import neko_desktop_tutor_host as host
import neko_native_shell as avatar
import neko_output_only_patch as migration

ROOT=Path(__file__).resolve().parents[1]
path=ROOT/'benchmarks/raw/neko-product-host/main_logic/livetutor_output_only.py'
spec=importlib.util.spec_from_file_location('output_only_actual',path)
runtime=importlib.util.module_from_spec(spec);spec.loader.exec_module(runtime)


class OutputOnly(unittest.IsolatedAsyncioTestCase):
    async def test_policy_content_and_header_use_one_snapshot(self):
        app=FastAPI()
        @app.get('/')
        def page():return HTMLResponse('<html>original</html>')
        first=b'/* first policy snapshot */'; second=b'/* replaced policy snapshot */'
        with patch.dict(runtime.os.environ,{'NEKO_OUTPUT_ONLY':'1'}), \
             patch.object(runtime.Path,'read_bytes',side_effect=[first,second]) as read, \
             patch.object(runtime.Path,'read_text',side_effect=AssertionError('separate snapshot forbidden')):
            runtime.install_output_only(app)
        read.assert_called_once()
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
            response=await client.get('/')
        self.assertIn(first.decode(),response.text)
        self.assertNotIn(second.decode(),response.text)
        self.assertEqual(response.headers['x-livetutor-capture-policy-sha256'],hashlib.sha256(first).hexdigest())

    async def test_actual_middleware_protects_html_before_scripts_and_keeps_json(self):
        app=FastAPI()
        @app.get('/page')
        def page():return HTMLResponse('<html><title>Original</title><script>window.originalStarted=true;</script></html>')
        @app.get('/json')
        def data():return {'unchanged':True}
        with patch.dict(runtime.os.environ,{'NEKO_OUTPUT_ONLY':'1'}):runtime.install_output_only(app)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
            page=await client.get('/page');data=await client.get('/json')
        self.assertEqual(page.status_code,200)
        self.assertIn('microphone=()',page.headers['permissions-policy'])
        self.assertIn('NekoCapturePolicy.installOutputOnly({enabled:true})',page.text)
        self.assertNotIn('<script>window.originalStarted=true;',page.text)
        self.assertLess(page.text.index('receipt.status'),page.text.index('document.write'))
        self.assertEqual(int(page.headers['content-length']),len(page.content))
        self.assertEqual(data.json(),{'unchanged':True})
        self.assertEqual(data.headers['x-livetutor-audio-mode'],'output-only')

    async def test_normal_mode_leaves_original_app_untouched(self):
        app=FastAPI();original='<html>Normal untouched</html>'
        @app.get('/')
        def page():return HTMLResponse(original)
        with patch.dict(runtime.os.environ,{'NEKO_OUTPUT_ONLY':'0'}):runtime.install_output_only(app)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
            page=await client.get('/')
        self.assertEqual(page.text,original)
        self.assertNotIn('x-livetutor-audio-mode',page.headers)

    async def test_unknown_encoded_or_overbound_html_fails_without_original_app(self):
        for headers,body in [({'content-encoding':'unknown'},b'<html>originalStarted</html>'),
                             ({},b'<html>'+b'x'*2_000_001)]:
            app=FastAPI()
            @app.get('/')
            def page():return Response(body,media_type='text/html',headers=headers)
            with patch.dict(runtime.os.environ,{'NEKO_OUTPUT_ONLY':'1'}):runtime.install_output_only(app)
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
                page=await client.get('/')
            self.assertEqual(page.status_code,503)
            self.assertNotIn('originalStarted',page.text)

    async def test_pinned_replay_is_idempotent_and_unknown_changes_are_rejected(self):
        source=ROOT/'candidates/N.E.K.O'
        base=subprocess.check_output(['git','-C',str(source),'show','1d814cf32fba8c02b5727d2890710e4e7b8ece24:'+migration.RELATIVE]).decode('utf-8')
        once=migration.patched_web_app(base)
        self.assertEqual(migration.patched_web_app(once),once)
        for bad in (once+'\n# unknown',base.replace(migration.BEFORE,migration.BEFORE*2),once+once):
            with self.assertRaises(ValueError):migration.patched_web_app(bad)
        current=(source/migration.CAPTURE_RELATIVE).read_text(encoding='utf-8')
        self.assertEqual(migration.patched_capture(current),current)
        with self.assertRaises(ValueError):migration.patched_capture(current+'\n// unknown')

    async def test_output_permission_does_not_grant_capture_or_old_native_entry(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(host,'ROOT',Path(folder)),patch.dict(host.os.environ,{'NEKO_TASK_SILENT':'0'}):
            policy=Path(folder)/'benchmarks/raw/daily-companion-audio-policy.json';policy.parent.mkdir(parents=True)
            policy.write_text(json.dumps({'audio_allowed':False,'speaker_output_allowed':True,
                                         'microphone_allowed':False,'capture_devices_allowed':False}),encoding='utf-8')
            host.require_task_speaker_output_allowed('check')
            with self.assertRaises(RuntimeError):host.require_task_audio_allowed('mixed path')
            with patch.object(avatar,'verify_output_only_host') as verify,patch.object(avatar.subprocess,'Popen') as spawn:
                with self.assertRaisesRegex(RuntimeError,'capture devices'):
                    avatar.launch(Path(folder),audio_input='fake.wav',output_only=True)
                verify.assert_not_called();spawn.assert_not_called()
            with patch.dict(host.os.environ,{'NEKO_TASK_SILENT':'1'}):
                with self.assertRaises(RuntimeError):host.require_task_speaker_output_allowed('check')
            for value in ('true',False,None):
                policy.write_text(json.dumps({'speaker_output_allowed':value,'microphone_allowed':False,
                                              'capture_devices_allowed':False}),encoding='utf-8')
                with self.assertRaises(RuntimeError):host.require_task_speaker_output_allowed('check')


if __name__=='__main__':unittest.main(verbosity=2)
