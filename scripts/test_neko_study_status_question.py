"""Actual status projection and public-question helper; no host, DB or devices."""
from __future__ import annotations
import copy
import importlib
from pathlib import Path
import sys
import types
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'patches/neko-study-2026-10-10-product/payload/study_companion'
BASE = ROOT / 'benchmarks/raw/neko-app/resources/bin/plugins/study_companion'
package = types.ModuleType('status_question_product')
package.__path__ = [str(SOURCE), str(BASE)]
sys.modules[package.__name__] = package
models = importlib.import_module(package.__name__ + '.models')
service = importlib.import_module(package.__name__ + '.service')

class StatusQuestion(unittest.TestCase):
    def state(self, question):
        return models.StudyState(study_course_id='course-a', study_session_id='current-session',
                                current_question=question)

    def test_pending_projection_keeps_identity_but_hides_private_fields_without_mutation(self):
        question = {'question_id': 'q1', 'attempt_id': 'a1', 'question': 'Which arrow?',
                    'options': ['left', 'right'], 'hint': 'Check the starting node.'}
        question.update({key: 'PRIVATE_' + key for key in models.PRIVATE_CURRENT_QUESTION_FIELDS})
        question.update(attempt_evaluated=False, answer_evaluation_cache={'answer': 'PRIVATE_CACHE'})
        state = self.state(question)
        before = copy.deepcopy(state.to_dict())
        result = service.build_status_payload(config=models.StudyConfig(), state=state)
        self.assertEqual(result['study_course_id'], 'course-a')
        self.assertEqual(result['study_session_id'], 'current-session')
        self.assertEqual(result['question_state'], 'pending')
        public = result['current_question']
        self.assertEqual(public['question_id'], 'q1')
        self.assertEqual(public['attempt_id'], 'a1')
        self.assertEqual(public['options'], ['left', 'right'])
        for key in models.PRIVATE_CURRENT_QUESTION_FIELDS | {'answer_evaluation_cache'}:
            self.assertNotIn(key, public)
        self.assertEqual(state.to_dict(), before)
        public['options'].append('changed UI copy')
        self.assertEqual(state.current_question['options'], ['left', 'right'])

    def test_evaluated_question_has_explicit_state_without_exposing_cached_evaluation(self):
        state = self.state({'question_id': 'q2', 'attempt_id': 'a2', 'question': 'Source question',
                            'attempt_evaluated': True, 'answer_evaluation_cache': {'score': 0}})
        state.last_answer_evaluation = {'verdict': 'wrong', 'score': 0}
        result = service.build_status_payload(config=models.StudyConfig(), state=state)
        self.assertEqual(result['question_state'], 'evaluated')
        self.assertEqual(result['last_answer_evaluation']['score'], 0)
        self.assertNotIn('attempt_evaluated', result['current_question'])
        self.assertNotIn('answer_evaluation_cache', result['current_question'])

    def test_no_held_question_is_none_and_retains_current_real_session(self):
        state = self.state({})
        history = [{'id': 1, 'kind': 'question_generate', 'output_text': 'OLD_TUTOR_QUESTION'}]
        result = service.build_status_payload(config=models.StudyConfig(), state=state, history=history)
        self.assertEqual(result['question_state'], 'none')
        self.assertEqual(result['current_question'], {})
        self.assertEqual(result['study_session_id'], 'current-session')
        self.assertEqual(result['history'], history)  # History is not promoted into a held question.

if __name__ == '__main__':
    unittest.main(verbosity=2)
