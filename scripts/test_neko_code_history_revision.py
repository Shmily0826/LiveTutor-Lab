"""Actual code history method records the queried version, retaining grant identity."""
import ast
from pathlib import Path
import types
import unittest
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / 'patches/neko-study-2026-10-10-product/payload/study_companion/study_code_tools.py'
tree = ast.parse(PATH.read_text(encoding='utf-8'))
method = next(n for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef) and n.name == '_code_record')
namespace = {'Any': Any, 'current_call_id': lambda: 'call-1'}
exec(compile(ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])), str(PATH), 'exec'), namespace)


class CodeHistoryRevision(unittest.IsolatedAsyncioTestCase):
    async def test_repository_advance_records_current_evidence_and_keeps_original_grant(self):
        for head in ('current-revision-B', ''):
            with self.subTest(head=head):
                rows = []
                store = types.SimpleNamespace(append_interaction=lambda **values: rows.append(values))
                state = types.SimpleNamespace(study_session_id='session-1', session_summary_seed={'event_count': 7})
                host = types.SimpleNamespace(_store=store, _state=state)
                result = await namespace['_code_record'](host, 'node', 'meaning of line 17',
                    {'name': 'project', 'commit': 'authorized-revision-A'},
                    [{'file': 'weather_service.dart', 'lines': [16,17]}], {'chars': 80}, repo_commit=head)
                expected = head or 'authorized-revision-A'
                self.assertEqual(result, 'session-1')
                self.assertEqual(rows[0]['session_id'], 'session-1')
                self.assertEqual(rows[0]['metadata']['commit'], expected)
                self.assertEqual(rows[0]['metadata']['authorized_commit'], 'authorized-revision-A')
                self.assertEqual(rows[0]['metadata']['call'], 'call-1')  # rows of one explanation share the call id
                self.assertIn('@' + expected + ']', rows[0]['input_text'])
                self.assertEqual(state.session_summary_seed['last_code_commit'], expected)
                self.assertEqual(state.session_summary_seed['event_count'], 7)


if __name__ == '__main__': unittest.main(verbosity=2)
