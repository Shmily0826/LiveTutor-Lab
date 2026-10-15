"""The role's actual pointing description distinguishes surface identity from vision."""
import ast
import unittest
from test_neko_source_tool_routing import schema


class PointIntent(unittest.TestCase):
    def test_explicit_point_request_uses_status_without_a_desktop_window_title(self):
        description=ast.literal_eval(schema('study_avatar_tools.py','study_point')['description'])
        self.assertIn('指给我看',description)
        self.assertIn('No desktop window title',description)
        self.assertIn('do not invent a rectangle',description)


if __name__=='__main__':unittest.main(verbosity=2)
