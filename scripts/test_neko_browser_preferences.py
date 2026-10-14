"""Preference preservation and refusal boundaries; no browser or host starts."""
import json
import contextlib
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import neko_tutor_start as start


class BrowserPreferences(unittest.TestCase):
    def setUp(self):
        raw = (start.ROOT / 'benchmarks/raw').resolve()
        self.task = tempfile.TemporaryDirectory(prefix='browser-prefs-', dir=raw)
        self.root = Path(self.task.name).resolve()
        assert self.root.is_relative_to(raw)
        self.addCleanup(self.task.cleanup)
        self.profile = self.root / 'browser/text-profile'
        self.prefs = self.profile / 'Default/Preferences'

    def write(self, content):
        self.prefs.parent.mkdir(parents=True, exist_ok=True)
        self.prefs.write_bytes(content)

    def test_fresh_profile_disables_only_automatic_translate(self):
        start.prepare_browser_profile(self.profile)
        self.assertEqual(json.loads(self.prefs.read_text()), {'translate': {'enabled': False}})

    def test_existing_unknown_settings_are_preserved_and_second_call_leaves_exact_bytes(self):
        original = {'translate': {'enabled': True, 'other': ['中文']}, 'session': {'last': 'keep'}, 'unknown': 47}
        self.write(json.dumps(original).encode())
        start.prepare_browser_profile(self.profile)
        actual = json.loads(self.prefs.read_text(encoding='utf-8'))
        original['translate']['enabled'] = False
        self.assertEqual(actual, original)
        before = self.prefs.read_bytes()
        start.prepare_browser_profile(self.profile)
        self.assertEqual(self.prefs.read_bytes(), before)
        self.assertFalse(self.prefs.with_name('Preferences.livetutor-tmp').exists())

    def test_malformed_or_wrong_shape_preferences_are_preserved_without_temporary_write(self):
        for content in (b'{bad', b'[]', b'{"translate":null}', b'{"translate":[]}', b'\xff'):
            with self.subTest(content=content):
                self.write(content)
                with self.assertRaises(RuntimeError): start.prepare_browser_profile(self.profile)
                self.assertEqual(self.prefs.read_bytes(), content)
                self.assertFalse(self.prefs.with_name('Preferences.livetutor-tmp').exists())

    def test_outside_task_raw_and_existing_temporary_are_not_overwritten(self):
        with self.assertRaises(RuntimeError): start.prepare_browser_profile(start.ROOT)
        self.write(b'{"keep":true}')
        temporary = self.prefs.with_name('Preferences.livetutor-tmp')
        temporary.write_bytes(b'preserve unfinished write')
        with self.assertRaises(FileExistsError): start.prepare_browser_profile(self.profile)
        self.assertEqual(self.prefs.read_bytes(), b'{"keep":true}')
        self.assertEqual(temporary.read_bytes(), b'preserve unfinished write')

    def test_failed_atomic_replace_preserves_original(self):
        self.write(b'{"keep":true}')
        with patch.object(start.os, 'replace', side_effect=OSError('fixture locked file')):
            with self.assertRaises(OSError): start.prepare_browser_profile(self.profile)
        self.assertEqual(self.prefs.read_bytes(), b'{"keep":true}')
        self.assertEqual(json.loads(self.prefs.with_name('Preferences.livetutor-tmp').read_text()),
                         {'keep': True, 'translate': {'enabled': False}})

    def test_live_recorded_browser_is_refused_before_any_preferences_write(self):
        self.write(b'{"translate":{"enabled":true},"keep":"exact"}')
        before = self.prefs.read_bytes()
        owner = self.profile.parent / 'browser-owner.json'
        owner.write_text(json.dumps([{'pid': os.getpid(), 'created_at': start.process_creation_time(os.getpid())}]))
        network = unittest.mock.MagicMock()
        network.return_value.__enter__.return_value.connect_ex.return_value = 1
        with patch.object(start, 'BROWSER_PROFILE', start.BROWSER_PROFILE), \
                patch.object(start, 'BROWSER_OWNER_FILE', start.BROWSER_OWNER_FILE), \
                patch.object(start.sys, 'argv', ['tutor', '--store', self.root.name, '--text-only', '--study-ui', '--code-root', 'keep']), \
                patch.object(start.socket, 'socket', network), \
                patch.object(start.host, 'read_key'), patch.object(start.host, 'apply_voice_host_patch'), \
                patch.object(start.host, 'verify_source_audio_gate'), patch.object(start, 'chrome_command', return_value=['chrome']), \
                patch.object(start, 'prepare_browser_profile', wraps=start.prepare_browser_profile) as prepare, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(start.main(), 1)
            prepare.assert_not_called()
        self.assertEqual(self.prefs.read_bytes(), before)


if __name__ == '__main__':
    unittest.main(verbosity=2)
