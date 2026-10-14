"""Refuse before device import, process spawn or readiness checks; no audio/network."""
import asyncio
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import neko_desktop_tutor_host as host
import neko_native_shell as avatar
import neko_tutor_start as start
import neko_loopback_meter as loopback
import neko_daily_voice_probe as voice


class SilentPolicy(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.root_patch = patch.object(host, 'ROOT', self.root)
        self.root_patch.start()
        self.env = patch.dict(host.os.environ, {'NEKO_TASK_SILENT':'0'})
        self.env.start()
        self.policy = self.root / 'benchmarks/raw/daily-companion-audio-policy.json'
        self.policy.parent.mkdir(parents=True)

    def tearDown(self):
        self.env.stop(); self.root_patch.stop(); self.temp.cleanup()

    def test_absent_policy_preserves_normal_start_and_silence_env_cannot_be_overridden(self):
        host.require_task_audio_allowed('check only')
        self.policy.write_text(json.dumps({'audio_allowed':True}), encoding='utf-8')
        with patch.dict(host.os.environ, {'NEKO_TASK_SILENT':'1'}):
            with self.assertRaisesRegex(RuntimeError, '严格静音'):
                host.require_task_audio_allowed('check only')

    def test_explicit_deny_and_invalid_policy_fail_closed(self):
        for content in ('{"audio_allowed":false}', '{bad', '{}', '[]', '{"audio_allowed":"false"}'):
            with self.subTest(content=content):
                self.policy.write_text(content, encoding='utf-8')
                with self.assertRaises(RuntimeError):
                    host.require_task_audio_allowed('check only')

    def test_native_and_browser_refuse_before_readiness_or_process_creation(self):
        self.policy.write_text('{"audio_allowed":false}', encoding='utf-8')
        with patch.object(avatar, 'host_ready') as ready, patch.object(avatar.subprocess, 'Popen') as spawn:
            with self.assertRaisesRegex(RuntimeError, '严格静音'):
                avatar.launch(self.root, audio_input='even-a-fake-wav.wav')
            with self.assertRaisesRegex(RuntimeError, '严格静音'):
                start.chrome_command('http://127.0.0.1/')
            ready.assert_not_called(); spawn.assert_not_called()

    def test_voice_and_loopback_refuse_before_arguments_device_import_or_spawn(self):
        self.policy.write_text('{"audio_allowed":false}', encoding='utf-8')
        with patch.dict('sys.modules', {'pyaudiowpatch':None}), patch.object(loopback.subprocess, 'Popen') as spawn:
            for call in (lambda: loopback.capture(1), lambda: loopback.read_capture(1), loopback.self_test,
                         lambda: asyncio.run(voice.main(object()))):
                with self.assertRaisesRegex(RuntimeError, '严格静音'):
                    call()
            spawn.assert_not_called()


if __name__ == '__main__':
    unittest.main(verbosity=2)
