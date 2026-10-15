"""Four actual Git LF sources -> canonical host patch; no services/providers."""
import ast
import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest

import neko_voice_host_patch as patch
import neko_pause_hold_patch as pause_hold
import neko_empty_turn_notice_patch as empty_turn
from neko_phrase_input_patch import normalize_phrase_helpers, normalize_phrase_transport

ROOT = Path(__file__).resolve().parents[1]
REVISION = '1d814cf32fba8c02b5727d2890710e4e7b8ece24'
FILES = ('main_logic/core/session_lifecycle.py', 'main_logic/core/asr_runtime.py',
         'main_logic/omni_realtime_client/_transport.py', 'main_logic/omni_realtime_client/_audio.py')


class PhrasePatchReplay(unittest.TestCase):
    def test_fresh_git_lf_replay_matches_both_real_trees_and_is_idempotent(self):
        for relative in FILES:
            with self.subTest(relative=relative), tempfile.TemporaryDirectory(prefix='neko-phrase-replay-') as folder:
                target = Path(folder) / relative
                target.parent.mkdir(parents=True)
                base = subprocess.check_output(['git', '-C', str(ROOT / 'candidates/N.E.K.O'),
                                                'show', REVISION + ':' + relative])
                target.write_bytes(base)
                patch.apply_to(target)
                # Same order as the launch chain (apply_voice_host_patch).
                if relative == pause_hold.TARGET:
                    pause_hold.apply_to(target)
                    empty_turn.apply_to(target)
                actual = target.read_bytes()
                ast.parse(actual.decode('utf-8'))
                self.assertEqual(patch.state(target), 'patched')
                self.assertEqual(patch.apply_to(target), 'already patched')
                if relative == pause_hold.TARGET:
                    self.assertEqual(pause_hold.apply_to(target), 'already patched')
                    self.assertEqual(empty_turn.apply_to(target), 'already patched')
                self.assertEqual(target.read_bytes(), actual)
                for host in patch.HOSTS:
                    self.assertEqual(actual, (host / relative).read_bytes())

    def test_unknown_or_duplicate_authority_is_refused_before_any_write(self):
        source = (patch.HOSTS[0] / FILES[0]).read_text(encoding='utf-8')
        unknown = source.replace('or self._voice_lease_owner != "core"', 'or self._voice_lease_owner != "changed-owner"', 1)
        duplicate = source.replace('    def _bind_owned_output_callbacks',
                                   '    def _native_phrase_input_authority(self, session):\n        return True\n\n    def _bind_owned_output_callbacks', 1)
        for value in (unknown, duplicate):
            with self.assertRaises(RuntimeError):
                normalize_phrase_helpers(value)
            with tempfile.TemporaryDirectory(prefix='neko-phrase-refuse-') as folder:
                target = Path(folder) / FILES[0]
                target.parent.mkdir(parents=True)
                target.write_text(value, encoding='utf-8', newline='\n')
                before = target.read_bytes()
                with self.assertRaises(RuntimeError):
                    patch.apply_to(target)
                self.assertEqual(target.read_bytes(), before)

    def test_unknown_transport_helper_and_third_admission_copy_are_refused(self):
        from neko_phrase_input_patch import _DELIVERY_BLOCK
        source = (patch.HOSTS[0] / FILES[2]).read_text(encoding='utf-8')
        unknown = source.replace('driver.protect_clear()', 'driver.changed_clear()', 1)
        duplicate = source.replace(_DELIVERY_BLOCK, _DELIVERY_BLOCK * 3, 1)
        for value in (unknown, duplicate):
            with self.assertRaises(RuntimeError):
                normalize_phrase_transport(value)
            with tempfile.TemporaryDirectory(prefix='neko-phrase-transport-refuse-') as folder:
                target = Path(folder) / FILES[2]
                target.parent.mkdir(parents=True)
                target.write_text(value, encoding='utf-8', newline='\n')
                before = target.read_bytes()
                with self.assertRaises(RuntimeError):
                    patch.apply_to(target)
                self.assertEqual(target.read_bytes(), before)


if __name__ == '__main__':
    unittest.main(verbosity=2)
