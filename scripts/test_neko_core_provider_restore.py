"""Daily runtime provider restoration; temporary configs, no services or secrets."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from neko_tutor_start import CoreProviderOverride


class ProviderRestoreTest(unittest.TestCase):
    def make(self, folder, data):
        store = Path(folder)
        path = store / 'N.E.K.O/config/core_config.json'
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(data), encoding='utf-8')
        return store, path

    def test_runtime_switch_restores_original_without_losing_other_edits(self):
        for original, runtime in (('free', 'deepseek'), ('deepseek', 'free')):
            with self.subTest(original=original), tempfile.TemporaryDirectory() as folder:
                store, path = self.make(folder, {'coreApi': original, 'retained': 7})
                lease = CoreProviderOverride(store, runtime)
                path.write_text(json.dumps({'coreApi': runtime, 'retained': 8, 'new_setting': True}))
                lease.restore()
                self.assertEqual(json.loads(path.read_text()), {'coreApi': original, 'retained': 8, 'new_setting': True})
                self.assertFalse(list(path.parent.glob('.daily-provider-*')))

    def test_existing_missing_field_restored_but_new_store_keeps_defaults(self):
        with tempfile.TemporaryDirectory() as folder:
            store, path = self.make(folder, {'retained': 7})
            lease = CoreProviderOverride(store, 'deepseek')
            path.write_text(json.dumps({'coreApi': 'deepseek', 'retained': 7}))
            lease.restore()
            self.assertEqual(json.loads(path.read_text()), {'retained': 7})
        with tempfile.TemporaryDirectory() as folder:
            store = Path(folder)
            lease = CoreProviderOverride(store, 'deepseek')
            path = store / 'N.E.K.O/config/core_config.json'
            path.parent.mkdir(parents=True)
            path.write_text('{"coreApi":"deepseek"}')
            before = path.read_bytes()
            lease.restore()
            self.assertEqual(path.read_bytes(), before)

    def test_foreign_provider_and_bad_file_retained(self):
        for replacement in ('{"coreApi":"user-choice","retained":9}', 'broken', '[]'):
            with self.subTest(replacement=replacement), tempfile.TemporaryDirectory() as folder:
                store, path = self.make(folder, {'coreApi': 'free'})
                lease = CoreProviderOverride(store, 'deepseek')
                path.write_text(replacement)
                with self.assertRaises((RuntimeError, ValueError)):
                    lease.restore()
                self.assertEqual(path.read_text(), replacement)

    def test_writes_and_replace_are_blocked_until_restore_handle_closes(self):
        with tempfile.TemporaryDirectory() as folder:
            store, path = self.make(folder, {'coreApi': 'free'})
            lease = CoreProviderOverride(store, 'deepseek')
            path.write_text('{"coreApi":"deepseek"}')
            replacement = path.with_suffix('.other')
            replacement.write_text('{"learner_edit":true}')
            flush = os.fsync
            checked = False
            def check_lock(fd):
                nonlocal checked
                with self.assertRaises(PermissionError):
                    path.write_text('{"learner_edit":true}')
                with self.assertRaises(PermissionError):
                    os.replace(replacement, path)
                checked = True
                flush(fd)
            with patch('neko_tutor_start.os.fsync', side_effect=check_lock):
                lease.restore()
            self.assertTrue(checked)
            self.assertEqual(json.loads(path.read_text()), {'coreApi': 'free'})
            path.write_text('{"coreApi":"free","learner_edit":true}')
            self.assertTrue(json.loads(path.read_text())['learner_edit'])
            self.assertFalse(list(path.parent.glob('.daily-provider-*')))

    def test_existing_writer_prevents_restore_without_modification(self):
        with tempfile.TemporaryDirectory() as folder:
            store, path = self.make(folder, {'coreApi': 'free'})
            lease = CoreProviderOverride(store, 'deepseek')
            path.write_text('{"coreApi":"deepseek"}')
            before = path.read_bytes()
            with path.open('r+b'):
                with self.assertRaises(OSError):
                    lease.restore()
            self.assertEqual(path.read_bytes(), before)

    def test_unchanged_choice_is_byte_preserving(self):
        with tempfile.TemporaryDirectory() as folder:
            store, path = self.make(folder, {'coreApi': 'free', 'learner': 9})
            lease = CoreProviderOverride(store, 'free')
            before = path.read_bytes()
            with patch('neko_tutor_start.os.replace') as replace:
                lease.restore()
                replace.assert_not_called()
            self.assertEqual(path.read_bytes(), before)

    def test_hardlinked_config_is_not_updated(self):
        with tempfile.TemporaryDirectory() as folder:
            store, path = self.make(folder, {'coreApi': 'free'})
            lease = CoreProviderOverride(store, 'deepseek')
            path.write_text('{"coreApi":"deepseek"}')
            other = Path(folder) / 'shared-config.json'
            os.link(path, other)
            before = other.read_bytes()
            with self.assertRaisesRegex(RuntimeError, '包含链接'):
                lease.restore()
            self.assertEqual(other.read_bytes(), before)


if __name__ == '__main__':
    unittest.main(verbosity=2)
