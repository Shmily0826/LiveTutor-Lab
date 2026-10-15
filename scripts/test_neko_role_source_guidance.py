"""Check the actual launcher guidance without importing or starting the host."""
import ast
import json
from pathlib import Path
import tempfile
import unittest


SOURCE = Path(__file__).with_name('neko_desktop_tutor_host.py')
tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
names = {'TUTOR_ROLE_GUIDANCE_PREFIX', 'TUTOR_ROLE_GUIDANCE'}
nodes = [node for node in tree.body if
         (isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in names for t in node.targets))
         or (isinstance(node, ast.FunctionDef) and node.name == 'apply_tutor_role_guidance')]
namespace = {'Path': Path, 'json': json}
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SOURCE), 'exec'), namespace)


class SourceGuidance(unittest.TestCase):
    def test_line_explanations_and_followups_use_teacher(self):
        guidance = namespace['TUTOR_ROLE_GUIDANCE']
        self.assertNotIn('For a specific source line use study_code', guidance)
        self.assertIn('line meanings, hypothetical edits and follow-ups', guidance)
        self.assertIn('call study_explain material_source=project_code', guidance)
        self.assertIn('study_code is only for lookup', guidance)

    def test_old_owned_guidance_upgrades_but_learner_guidance_survives(self):
        for existing, expected in [('Study Companion mode: old conflicting rule', 'upgraded'),
                                   ('My own teaching style', "kept the learner's own guidance")]:
            with self.subTest(existing=existing), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                path = root / 'config/characters.json'
                path.parent.mkdir()
                override = {'prompt_guidance': existing}
                data = {'当前猫娘': 'test', '猫娘': {'test': {'_reserved': {'persona_override': override}}}}
                path.write_text(json.dumps(data), encoding='utf-8')
                self.assertEqual(namespace['apply_tutor_role_guidance'](root), expected)
                actual = json.loads(path.read_text(encoding='utf-8'))['猫娘']['test']['_reserved']['persona_override']
                self.assertEqual(actual['prompt_guidance'], namespace['TUTOR_ROLE_GUIDANCE'] if expected == 'upgraded' else existing)


if __name__ == '__main__':
    unittest.main(verbosity=2)
