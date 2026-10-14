"""Window-command and independent cleanup checks; no browser/host is started."""
import unittest
from unittest.mock import Mock, patch
import neko_tutor_start as start


class MaterialWindows(unittest.TestCase):
    def setUp(self):
        self.template = start.chrome_command('http://127.0.0.1:48916/plugin/study_companion/ui/', text_only=True)
        self.surface = 'http://127.0.0.1:54321'

    def test_study_and_material_have_separate_single_url_app_commands_with_same_muted_profile(self):
        before = list(self.template)
        commands = start.browser_window_commands(self.template, study_ui=True, surface_url=self.surface)
        self.assertEqual(len(commands), 2)
        self.assertEqual(commands[0], before)
        self.assertEqual(self.template, before)
        for command in commands:
            self.assertEqual(sum(arg.startswith('--app=') for arg in command), 1)
            self.assertIn('--mute-audio', command)
            self.assertIn('--disable-features=MediaRouter,Translate', command)
            self.assertNotIn('--new-window', command)
            self.assertEqual([arg for arg in command if arg.startswith('--user-data-dir=')],
                             [arg for arg in before if arg.startswith('--user-data-dir=')])
        self.assertIn('--app=' + self.surface, commands[1])

    def test_surface_only_still_opens_material_and_legacy_study_only_is_unchanged(self):
        only = start.browser_window_commands(self.template, study_ui=False, surface_url=self.surface)
        self.assertEqual(len(only), 1)
        self.assertIn('--app=' + self.surface, only[0])
        self.assertEqual(start.browser_window_commands(self.template, study_ui=True), [self.template])
        self.assertEqual(start.browser_window_commands(None, study_ui=False), [])

    def test_cleanup_records_both_launches_but_closes_only_the_existing_owned_profile_tree(self):
        launcher = Mock(); launcher.poll.return_value = 0
        first, second, records = Mock(), Mock(), []
        with patch.object(start, 'remember_browser_tree') as remember, patch.object(start, 'stop_owned_browser') as stop:
            errors = start.cleanup_resources(None, None, launcher, [], first, records, None, [second])
        self.assertEqual(errors, [])
        self.assertEqual([call.args[0] for call in remember.call_args_list], [first, second])
        stop.assert_called_once_with(records)

    def test_one_browser_ownership_failure_does_not_skip_other_record_or_owned_cleanup(self):
        launcher = Mock(); launcher.poll.return_value = 0
        first, second, records = Mock(), Mock(), []
        with patch.object(start, 'remember_browser_tree', side_effect=[RuntimeError('fixture failure'), None]) as remember, \
                patch.object(start, 'stop_owned_browser') as stop:
            errors = start.cleanup_resources(None, None, launcher, [], first, records, None, [second])
        self.assertEqual(remember.call_count, 2)
        stop.assert_called_once_with(records)
        self.assertEqual(len(errors), 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
