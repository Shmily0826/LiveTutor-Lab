"""The project-structure fold keeps top-level folders visible and the model out of wrong nesting (offline)."""
import ast
import json
from pathlib import Path
import re
import unittest

PATH = Path(__file__).resolve().parents[1] / 'patches/neko-study-2026-10-10-product/payload/study_companion/study_code_tools.py'


def fold():
    tree = ast.parse(PATH.read_text(encoding='utf-8'))
    body = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in ('_structure_lines', '_slashes')]
    scope = {'json': json, 're': re}
    exec(compile(ast.Module(body=body, type_ignores=[]), str(PATH), 'exec'), scope)
    return scope['_structure_lines']


def rows(*paths):
    return json.dumps([{'path': path, 'nodeCount': 2} for path in paths])


class StructureFold(unittest.TestCase):
    def test_top_level_siblings_are_named_first(self):
        text = fold()(rows('sky/app/lib/a.dart', 'sky/app/lib/b.dart', 'sky/server/src/w.js', 'sky/README.md'), 'sky/')
        top = next(line for line in text.splitlines() if line.startswith('top-level entries'))
        self.assertIn('sky/app (2 files)', top)
        self.assertIn('sky/server (1 files)', top)
        self.assertIn('sky (1 files)', top)  # a file directly under the project root

    def test_the_cap_drops_the_deepest_folders_not_the_alphabetically_last(self):
        deep = [f'sky/app/lib/f{n:02d}/x/y/z.dart' for n in range(45)]
        text = fold()(rows('sky/server/src/w.js', 'sky/zzz/last.js', *deep), 'sky/')
        self.assertIn('sky/server/src - 1 files', text)
        self.assertIn('sky/zzz - 1 files', text)
        self.assertRegex(text, r'\d+ deeper folders not listed')
        self.assertEqual(len([line for line in text.splitlines() if ' indexed symbols' in line]), 40)

    def test_sibling_copies_never_appear(self):
        text = fold()(rows('sky/app/main.dart', 'sky_copy/server/s.js'), 'sky/')
        self.assertNotIn('sky_copy', text)

    def test_small_trees_keep_the_old_shape(self):
        text = fold()(rows('sky/lib/main.dart', 'sky/lib/features/a.dart'), 'sky/')
        self.assertIn('entry points in the index: sky/lib/main.dart', text)
        self.assertIn('sky/lib/features - 1 files, 2 indexed symbols', text)
        self.assertTrue(text.endswith('(2 folders of 2 files)'))


if __name__ == '__main__':
    unittest.main()
