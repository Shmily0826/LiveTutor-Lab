"""Actual isolated host defaults; never import the host or start processes."""
import ast
import json
from pathlib import Path
import tempfile
import unittest

SOURCE = Path(__file__).with_name('neko_desktop_tutor_host.py')
tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'prepare_tutor_conversation_defaults')
namespace = {'Path': Path, 'json': json}
exec(compile(ast.Module(body=[function], type_ignores=[]), str(SOURCE), 'exec'), namespace)
prepare = namespace[function.name]


class DailyDefaults(unittest.TestCase):
    def test_initial_default_off_saved_choice_and_invalid_file_retained(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); path = root / 'config/user_preferences.json'
            prepare(root)
            rows = json.loads(path.read_text(encoding='utf-8'))
            self.assertFalse(rows[0]['proactiveChatEnabled'])
            rows[0]['proactiveChatEnabled'] = True
            rows.append({'model_path': 'learner', 'custom': 'preserved'})
            path.write_text(json.dumps(rows), encoding='utf-8')
            before = path.read_bytes(); prepare(root)
            self.assertEqual(path.read_bytes(), before)
            path.write_text('{bad json', encoding='utf-8')
            with self.assertRaises(ValueError): prepare(root)
            self.assertEqual(path.read_text(), '{bad json')


if __name__ == '__main__': unittest.main(verbosity=2)
