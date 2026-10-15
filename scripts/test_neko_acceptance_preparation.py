"""The preparation command cannot select an existing or daily store."""
from pathlib import Path
import tempfile
import unittest
from neko_prepare_acceptance_course import fresh_target


class AcceptancePreparation(unittest.TestCase):
    def test_refuses_daily_existing_and_escaped_targets_without_modifying_them(self):
        with tempfile.TemporaryDirectory() as folder:
            raw=Path(folder)
            existing=raw/'neko-acceptance-used';existing.mkdir()
            marker=existing/'keep.txt';marker.write_text('history')
            for name in ('neko-daily-companion','../neko-acceptance-escape','neko-acceptance-used',str(existing)):
                with self.subTest(name=name),self.assertRaises(ValueError):fresh_target(name,raw)
            self.assertEqual(marker.read_text(),'history')

    def test_validates_a_fresh_name_without_creating_a_store(self):
        with tempfile.TemporaryDirectory() as folder:
            raw=Path(folder);target=fresh_target('neko-acceptance-fresh',raw)
            self.assertEqual(target.parent,raw.resolve());self.assertFalse(target.exists())


if __name__=='__main__':unittest.main(verbosity=2)
