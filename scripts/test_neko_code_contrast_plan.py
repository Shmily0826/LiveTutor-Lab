"""Offline scope and no-audio checks for the existing role text probe."""
import json
import asyncio
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import neko_daily_code_dialogue_probe as probe


class CodeContrastPlan(unittest.TestCase):
    def setUp(self):
        raw = (probe.ROOT/'benchmarks/raw').resolve()
        self.temp = tempfile.TemporaryDirectory(prefix='code-contrast-plan-', dir=raw)
        self.root = Path(self.temp.name).resolve()
        assert self.root.is_relative_to(raw)
        self.addCleanup(self.temp.cleanup)
        self.raw = self.root/'benchmarks/raw'
        (self.raw/'evidence').mkdir(parents=True)
        self.options = SimpleNamespace(store='neko-daily-code-contrast-fixture',
            output=self.raw/'evidence/result.json', contrast_only=True)

    def test_host_command_has_strict_text_mode_original_round_and_no_voice_allowance(self):
        command = probe.host_command(self.options)
        self.assertIn('--text-only', command)
        self.assertEqual(command[command.index('--core-provider')+1], 'deepseek')
        self.assertEqual(command[command.index('--budget-round')+1], 'bargein-autocheck-20261012')
        self.assertEqual(command[command.index('--egress-budget')+1], '2000')
        self.assertFalse(set(command) & {'--voice', '--audio-input', '--allow-host'})

    def test_contrast_requires_fresh_scoped_store_and_evidence(self):
        with patch.object(probe, 'ROOT', self.root):
            for store in ('neko-daily-companion', '../outside', 'neko-daily-code-contrast-x/../../outside'):
                self.options.store = store
                with self.subTest(store=store), self.assertRaises(ValueError):
                    probe.prepare_contrast_grant(self.options)
            self.options.store = 'neko-daily-code-contrast-fixture'
            (self.raw/self.options.store).mkdir()
            with self.assertRaises(ValueError): probe.prepare_contrast_grant(self.options)
            self.options.store = 'neko-daily-code-contrast-other'
            self.options.output = self.root/'outside.json'
            with self.assertRaises(ValueError): probe.prepare_contrast_grant(self.options)

    def test_reuses_only_exact_authorization_and_rejects_another_root(self):
        source = self.raw/'neko-daily-companion/N.E.K.O/plugins/study_companion/data/code_project.json'
        source.parent.mkdir(parents=True)
        data = {'root': str(Path(r'D:\UoA\S2\COMPSCI 734\project\Sky Scout\sky_scout')), 'fixture': 'grant only'}
        original = json.dumps(data).encode()
        source.write_bytes(original)
        (source.parent/'study_companion.db').write_bytes(b'not copied')
        with patch.object(probe, 'ROOT', self.root):
            probe.prepare_contrast_grant(self.options)
            copied = self.raw/self.options.store/'N.E.K.O/plugins/study_companion/data'
            self.assertEqual((copied/'code_project.json').read_bytes(), original)
            self.assertEqual([p.name for p in copied.iterdir()], ['code_project.json'])
            self.options.store = 'neko-daily-code-contrast-other'
            source.write_text(json.dumps({'root': str(self.root)}))
            with self.assertRaises(ValueError): probe.prepare_contrast_grant(self.options)
            self.assertFalse((self.raw/self.options.store).exists())

    def test_store_reservation_refuses_a_concurrent_winner_even_if_precheck_missed_it(self):
        source = self.raw/'neko-daily-companion/N.E.K.O/plugins/study_companion/data/code_project.json'
        source.parent.mkdir(parents=True)
        source.write_text(json.dumps({'root': r'D:\UoA\S2\COMPSCI 734\project\Sky Scout\sky_scout'}))
        winner = self.raw/self.options.store
        winner.mkdir()
        marker = winner/'preserve.txt'
        marker.write_bytes(b'another owner')
        original_exists = Path.exists
        def stale_precheck(path):
            return False if path == winner else original_exists(path)
        with patch.object(probe, 'ROOT', self.root), patch.object(Path, 'exists', stale_precheck):
            with self.assertRaises(FileExistsError): probe.prepare_contrast_grant(self.options)
        self.assertEqual(marker.read_bytes(), b'another owner')
        self.assertEqual([p.name for p in winner.iterdir()], ['preserve.txt'])

    def test_cleanup_keeps_recorded_child_identity_even_after_parent_exits(self):
        process = Mock()
        process.poll.return_value = 0
        records = [{'pid': 123, 'created_at': 47.0}, {'pid': 124, 'created_at': 48.0}]
        with patch.object(probe, 'stop_owned_tree') as stop:
            probe.cleanup_probe_host(process, records)
        stop.assert_called_once_with(records)
        process.wait.assert_called_once_with(timeout=20)

    def test_main_rejects_external_output_before_creation_or_process_start(self):
        self.options.output = self.root/'outside.json'
        with patch.object(probe, 'ROOT', self.root), patch.object(probe.subprocess, 'Popen') as launch:
            with self.assertRaises(ValueError): asyncio.run(probe.main(self.options))
        self.assertFalse(self.options.output.exists())
        launch.assert_not_called()


if __name__ == '__main__':
    unittest.main(verbosity=2)
