"""Actual summary prompt projection and fresh SQLite; no model/SDK/host/audio."""
from copy import deepcopy
import asyncio
import json
import logging
from pathlib import Path
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_neko_product_course_memory as product


class SummaryInteractionRoles(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='neko-summary-roles-')
        self.store = product.Store(Path(self.temp.name) / 'study.db',
                                   Path(self.temp.name) / 'unused.json',
                                   logging.getLogger('summary-roles'))
        self.store.open()
        self.session = 'voice17-shaped-session'

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def project(self, rows, **extra):
        context = {'session_history': rows, **extra}
        before = deepcopy(context)
        messages = product.prompts.build_summarize_session_messages(language='zh-CN', context=context)
        self.assertEqual(context, before)
        prompt = messages[1]['content']
        return json.loads(prompt.split('\n\ncontext:\n', 1)[1]), prompt

    def seed_voice17_shape(self):
        self.store.append_interaction(
            kind='question_generate', input_text='PREPARATION_ONLY 新图已提交，简短说明，不出题。',
            output_text='图中链路起始、中间、结束分别是什么？',
            metadata={'source_material_context': {'material_identity': 'PRIVATE_IMAGE_HASH'},
                      'payload': {'question': '图中链路起始、中间、结束分别是什么？',
                                  'answer': 'PRIVATE_ANSWER', 'rubric': 'PRIVATE_RUBRIC'}},
            session_id=self.session)
        self.store.append_interaction(
            kind='answer_evaluate', input_text='WEX→NUD→REZ，从左到右。',
            output_text='方向相反，应为 REZ→NUD→WEX。',
            metadata={'question': '图中链路起始、中间、结束分别是什么？',
                      'material_context': {'material_identity': 'PRIVATE_IMAGE_HASH'},
                      'payload': {'verdict': 'wrong', 'score': 10,
                                  'feedback': '方向相反，应为 REZ→NUD→WEX。',
                                  'next_action': '请对照图中箭头，按起始→中间→结束顺序再说明',
                                  'misconceptions': ['将方向读反'], 'answer': 'PRIVATE_ANSWER'}},
            session_id=self.session)
        self.store.append_interaction(
            kind='summarize_session', input_text='session',
            output_text='EARLIER_TUTOR_SUMMARY：学习者先解释了箭头方向。',
            metadata={}, session_id=self.session)
        return self.store.list_interactions(100, session_id=self.session)

    def test_real_history_separates_quiz_material_answer_and_tutor_summary(self):
        rows = self.seed_voice17_shape()
        original = deepcopy(rows)
        compact, prompt = self.project(list(reversed(rows)))
        history = compact['session_history']
        self.assertEqual([row['id'] for row in history], sorted(row['id'] for row in rows))
        quiz, grade, earlier = history
        self.assertNotIn('input', quiz)
        self.assertNotIn('input_role', quiz)
        self.assertEqual(quiz['output'], next(row['output_text'] for row in rows
                                             if row['kind'] == 'question_generate'))
        self.assertEqual(grade['input_role'], 'learner_answer')
        self.assertEqual(grade['input'], 'WEX→NUD→REZ，从左到右。')
        self.assertEqual(grade['evaluation']['verdict'], 'wrong')
        self.assertEqual(grade['evaluation']['score'], 10)
        self.assertEqual(grade['evaluation']['next_action'],
                         '请对照图中箭头，按起始→中间→结束顺序再说明')
        self.assertEqual(earlier['input_role'], 'request_or_material')
        self.assertEqual([row['output_role'] for row in history], ['tutor'] * 3)
        self.assertNotIn('PREPARATION_ONLY', prompt)
        for private in ('PRIVATE_IMAGE_HASH', 'PRIVATE_ANSWER', 'PRIVATE_RUBRIC',
                        'source_material_context', 'material_context'):
            self.assertNotIn(private, prompt)
        self.assertEqual(rows, original)
        self.assertEqual(self.store.list_interactions(100, session_id=self.session), original)

    def test_explanation_material_is_request_and_only_real_grade_has_learner_role(self):
        compact, _ = self.project([
            {'id': 1, 'kind': 'concept_explain', 'input_text': '解释 return 的含义',
             'output_text': 'return 将值传给调用者。'},
            {'id': 2, 'kind': 'answer_evaluate', 'input_text': '总是返回 5',
             'output_text': '错：还取决于实际分支。',
             'metadata': {'payload': {'verdict': 'wrong', 'score': 0,
                                      'next_action': '跟踪实际分支' * 100}}},
        ])
        lesson, grade = compact['session_history']
        self.assertEqual(lesson['input_role'], 'request_or_material')
        self.assertEqual(lesson['output_role'], 'tutor')
        self.assertEqual(lesson['input'], '解释 return 的含义')
        self.assertEqual(grade['input_role'], 'learner_answer')
        self.assertEqual(grade['evaluation']['score'], 0)
        suggestion = grade['evaluation']['next_action']
        self.assertEqual(suggestion[:160], ('跟踪实际分支' * 100)[:160])
        self.assertEqual(suggestion[160:], '\n...[truncated 440 chars]')

    def test_input_only_quiz_does_not_expose_material_or_trigger_unrelated_history(self):
        compact, prompt = self.project(
            [{'id': 1, 'kind': 'question_generate', 'input_text': 'PREPARATION_ONLY', 'output_text': '',
              'metadata': {'payload': {'question': 'UNSPOKEN_PRIVATE_QUESTION'}}}],
            history=[{'id': 8, 'kind': 'concept_explain', 'input_text': 'OTHER_SESSION', 'output_text': 'old'}])
        self.assertIn('session_history', compact)
        self.assertNotIn('history', compact)
        self.assertEqual(compact['session_history'], [])
        self.assertNotIn('PREPARATION_ONLY', prompt)
        self.assertNotIn('OTHER_SESSION', prompt)
        self.assertNotIn('UNSPOKEN_PRIVATE_QUESTION', prompt)

    def test_empty_session_keeps_existing_history_fallback(self):
        compact, _ = self.project([], history=[
            {'id': 1, 'kind': 'concept_explain', 'input_text': 'request', 'output_text': 'tutor reply'}])
        self.assertNotIn('session_history', compact)
        self.assertEqual(compact['history'][0]['output'], 'tutor reply')
        self.assertEqual(compact['history'][0]['input_role'], 'request_or_material')

    def test_existing_history_limits_order_and_allowlist_remain_bounded(self):
        rows = [{'id': index, 'kind': 'concept_explain', 'input_text': 'I' * 1000,
                 'output_text': 'O' * 1000, 'metadata': {'private': 'SECRET'}} for index in range(1, 46)]
        compact, prompt = self.project(list(reversed(rows)) + [None, 'invalid'])
        history = compact['session_history']
        self.assertEqual([row['id'] for row in history], list(range(6, 46)))
        self.assertTrue(all(len(row['input']) <= 200 for row in history))
        self.assertTrue(all(len(row['output']) <= 320 for row in history))
        self.assertNotIn('SECRET', prompt)
        self.assertEqual(product.prompts._summary_interaction_rows([None, {}, 'invalid']), [])

    def test_restart_context_resumes_graded_same_course_without_current_progress(self):
        async def scenario():
            h = product.ProductHarness(self.store)
            old_session = await h._restart_study_session(course_id='diagram-course')
            self.session = old_session
            self.seed_voice17_shape()
            foreign_session = await h._restart_study_session(course_id='foreign-course')
            self.store.append_interaction(
                kind='answer_evaluate', input_text='FOREIGN_LEARNER_ANSWER', output_text='FOREIGN_FEEDBACK',
                metadata={'question': 'FOREIGN_QUESTION', 'payload': {'score': 90}}, session_id=foreign_session)
            await h._restart_study_session(course_id='diagram-course')
            await h._end_study_session_locked()
            before = deepcopy(self.store.list_interactions(100))
            self.store.close()
            self.store.open()
            restarted = product.ProductHarness(self.store)
            current = await restarted._restart_study_session(course_id='diagram-course')
            context = await restarted._build_learning_context('summarize_session', session_id=current)
            self.assertEqual(context['history'], [])
            self.assertEqual(context.get('session_history', []), [])
            self.assertEqual(len(context['previous_course_history']), 3)
            self.assertTrue(all(row['session_id'] == old_session for row in context['previous_course_history']))
            snapshot = deepcopy(context)
            messages = product.prompts.build_summarize_session_messages(language='zh-CN', context=context)
            self.assertEqual(context, snapshot)
            prompt = messages[1]['content']
            compact = json.loads(prompt.split('\n\ncontext:\n', 1)[1])
            self.assertNotIn('history', compact)
            self.assertEqual(compact.get('session_history', []), [])
            prior = compact['previous_course_history']
            self.assertEqual(len(prior), 3)
            self.assertTrue(all(row['source_scope'] == 'previous_session_same_course' for row in prior))
            quiz, grade, summary = prior
            self.assertNotIn('input', quiz)
            self.assertEqual(quiz['output'], '图中链路起始、中间、结束分别是什么？')
            self.assertEqual(grade['input_role'], 'learner_answer')
            self.assertEqual(grade['input'], 'WEX→NUD→REZ，从左到右。')
            self.assertEqual(grade['evaluation']['score'], 10)
            self.assertEqual(grade['evaluation']['verdict'], 'wrong')
            self.assertIn('REZ→NUD→WEX', grade['evaluation']['feedback'])
            self.assertIn('起始→中间→结束', grade['evaluation']['next_action'])
            self.assertEqual(summary['output_role'], 'tutor')
            for secret in ('FOREIGN_', 'PRIVATE_IMAGE_HASH', 'PRIVATE_ANSWER', 'PRIVATE_RUBRIC', 'PREPARATION_ONLY'):
                self.assertNotIn(secret, prompt)
            self.assertNotIn('course_learning_state', compact)
            self.assertEqual(self.store.list_interactions(100), before)
        asyncio.run(scenario())

    def test_prior_scope_is_separate_when_current_material_only_rows_are_filtered(self):
        prior = [{'id': index, 'kind': 'answer_evaluate', 'input_text': f'prior answer {index}',
                  'output_text': 'actual grade',
                  'metadata': {'payload': {'score': 0, 'next_action': 'recheck the arrow'}}}
                 for index in range(12, 0, -1)]
        compact, prompt = self.project(
            [{'id': 99, 'kind': 'question_generate', 'input_text': 'MATERIAL_ONLY', 'output_text': ''}],
            history=[{'id': 1, 'kind': 'concept_explain', 'input_text': 'UNFILTERED_HISTORY', 'output_text': 'old'}],
            previous_course_history=prior,
            course_learning_state={'private': 'UNNEEDED_STATE'})
        self.assertEqual(compact['session_history'], [])
        self.assertNotIn('history', compact)
        self.assertEqual([row['id'] for row in compact['previous_course_history']], list(range(5, 13)))
        self.assertTrue(all(row['source_scope'] == 'previous_session_same_course'
                            for row in compact['previous_course_history']))
        for excluded in ('MATERIAL_ONLY', 'UNFILTERED_HISTORY', 'UNNEEDED_STATE'):
            self.assertNotIn(excluded, prompt)
        self.assertEqual(compact['previous_course_history'][0]['evaluation']['score'], 0)

    def test_qa_anchor_survives_long_tutor_history_using_actual_store_legacy_and_course_filter(self):
        async def scenario():
            h = product.ProductHarness(self.store)
            old = await h._restart_study_session(course_id='anchor-course')
            # Earlier persisted QA legitimately predates course_family.
            question = {'question': 'OLD_GRADED_QUESTION: which arrow starts the chain?',
                        'question_id': 'OPAQUE_QUESTION', 'attempt_id': 'OPAQUE_ATTEMPT',
                        'answer': 'HIDDEN_ANSWER', 'rubric': {'HIDDEN_RUBRIC': 100},
                        'internal_private_payload': {'material_identity': 'PRIVATE_IMAGE_HASH'}}
            self.store.add_qa_record(session_id=old, topic_id='', question=question,
                                     user_answer='OLD_WRONG_ANSWER: left to right',
                                     eval_result={'verdict': 'wrong', 'score': 0,
                                                  'feedback': 'Actual arrows run REZ→NUD→WEX.',
                                                  'next_action': 'Trace REZ to NUD, then WEX.',
                                                  'reference_answer': 'HIDDEN_REFERENCE'}, mode='companion')
            self.store.append_interaction(kind='answer_evaluate', input_text='OLD_WRONG_ANSWER',
                                          output_text='Actual grade', metadata={}, session_id=old)
            for index in range(12):
                self.store.append_interaction(kind='summarize_session', input_text='session',
                                              output_text=f'Later tutor summary {index}', metadata={}, session_id=old)
            foreign = await h._restart_study_session(course_id='foreign-course')
            self.store.add_qa_record(session_id=foreign, topic_id='',
                                     question={'question': 'FOREIGN_QA_QUESTION'}, user_answer='FOREIGN_QA_ANSWER',
                                     eval_result={'verdict': 'correct', 'score': 100}, mode='companion')
            current = await h._restart_study_session(course_id='anchor-course')
            self.store.add_qa_record(session_id=current, topic_id='',
                                     question={'question': 'CURRENT_SESSION_QA'}, user_answer='CURRENT_QA_ANSWER',
                                     eval_result={'verdict': 'correct', 'score': 100}, mode='companion')
            before = deepcopy(self.store.list_qa_records(100))
            state_question = deepcopy(h._state.current_question)
            context = await h._build_learning_context('summarize_session', session_id=current)
            self.assertEqual(context['history'], [])
            self.assertEqual(context.get('session_history', []), [])
            self.assertEqual(len(context['previous_course_history']), 8)
            self.assertTrue(all(row['kind'] == 'summarize_session' for row in context['previous_course_history']))
            self.assertEqual(len(context['course_learning_state']['recent_answers']), 2)
            messages = product.prompts.build_summarize_session_messages(language='zh-CN', context=context)
            prompt = messages[1]['content']
            compact = json.loads(prompt.split('\n\ncontext:\n', 1)[1])
            anchors = compact['previous_answer_records']
            self.assertEqual(len(anchors), 1)
            self.assertEqual(anchors[0]['source_scope'], 'previous_session_same_course')
            self.assertEqual(anchors[0]['input_role'], 'learner_answer')
            self.assertEqual(anchors[0]['evaluation_role'], 'tutor')
            self.assertIn('OLD_GRADED_QUESTION', anchors[0]['question'])
            self.assertIn('OLD_WRONG_ANSWER', anchors[0]['user_answer'])
            self.assertEqual(anchors[0]['evaluation']['score'], 0)
            self.assertIn('REZ→NUD→WEX', anchors[0]['evaluation']['feedback'])
            self.assertEqual(anchors[0]['evaluation']['next_action'], 'Trace REZ to NUD, then WEX.')
            for secret in ('FOREIGN_QA_', 'CURRENT_SESSION_QA', 'CURRENT_QA_ANSWER',
                           'OPAQUE_QUESTION', 'OPAQUE_ATTEMPT', 'HIDDEN_', 'PRIVATE_IMAGE_HASH'):
                self.assertNotIn(secret, prompt)
            self.assertNotIn('course_learning_state', compact)
            self.assertEqual(compact.get('session_history', []), [])
            self.assertEqual(h._state.current_question, state_question)
            self.assertEqual(self.store.list_qa_records(100), before)
        asyncio.run(scenario())

    def test_qa_anchor_limits_deduplicates_durable_attempts_and_rejects_unknown_scope(self):
        rows = [{'id': index, 'session_id': 'prior',
                 'question': {'question': f'Question {index}', 'course_family': 'course',
                              'question_id': f'q{index}', 'attempt_id': f'a{index}'},
                 'user_answer': f'Answer {index}',
                 'eval_result': {'verdict': 'wrong', 'score': 0, 'next_action': 'Recheck' * 100}}
                for index in range(1, 5)]
        rows.append({**deepcopy(rows[-1]), 'id': 5})  # Same durable attempt, latest QA wins.
        rows.append({**deepcopy(rows[-1]), 'id': 6})  # Repeated QA identity also de-dupes.
        rows.append(deepcopy(rows[-1]))
        rows[-2]['question']['attempt_id'] = 'retry-a4'
        rows[-1]['question']['attempt_id'] = 'retry-a4'
        context = {'course_id': 'course', 'session_id': 'current',
                   'course_learning_state': {'course_id': 'course', 'recent_answers': rows}}
        projected = product.prompts._summary_previous_answers(context)
        self.assertEqual(len(projected), 3)
        self.assertEqual([row['question'] for row in projected], ['Question 3', 'Question 4', 'Question 4'])
        self.assertTrue(all(row['evaluation']['score'] == 0 for row in projected))
        self.assertTrue(all(len(row['evaluation']['next_action']) < 200 for row in projected))
        self.assertNotIn('id', projected[0])
        self.assertNotIn('session_id', projected[0])
        for patch in ({'session_id': ''}, {'session_id': None}, {'course_id': ''},
                      {'course_learning_state': {}},
                      {'course_learning_state': {'course_id': 'foreign', 'recent_answers': rows}},
                      {'course_learning_state': {'course_id': 'course', 'recent_answers': 'invalid'}}):
            with self.subTest(patch=patch):
                self.assertEqual(product.prompts._summary_previous_answers({**context, **patch}), [])
        compact, prompt = self.project([], previous_answer_records=[{'question': 'FORGED_ANCHOR'}])
        self.assertNotIn('previous_answer_records', compact)
        self.assertNotIn('FORGED_ANCHOR', prompt)

    def test_malformed_or_current_qa_is_not_promoted_to_prior_evidence(self):
        valid = {'id': 1, 'session_id': 'prior', 'question': {'question': 'Q'},
                 'user_answer': 'A', 'eval_result': {'verdict': 'wrong', 'score': 0}}
        invalid = [None, {}, {**valid, 'id': True}, {**valid, 'id': 0},
                   {**valid, 'session_id': ''}, {**valid, 'session_id': None},
                   {**valid, 'session_id': 'current'}, {**valid, 'session_id': 'default'},
                   {**valid, 'question': {'question': 'Q', 'course_family': 'foreign'}},
                   {**valid, 'question': {'question': ['malformed']}},
                   {**valid, 'question': {'question': 'Q', 'attempt_id': []}},
                   {**valid, 'user_answer': ['malformed']},
                   {**valid, 'eval_result': {'verdict': ['wrong'], 'score': 0}},
                   {**valid, 'eval_result': {'verdict': 'wrong', 'score': True}},
                   {**valid, 'eval_result': {'verdict': 'wrong', 'score': float('nan')}},
                   {**valid, 'eval_result': {'verdict': 'wrong', 'score': -1}},
                   {**valid, 'eval_result': {'verdict': 'wrong', 'score': 0, 'feedback': {}}}]
        for row in invalid:
            with self.subTest(row=row):
                context = {'course_id': 'course', 'session_id': 'current',
                           'course_learning_state': {'course_id': 'course', 'recent_answers': [row]}}
                self.assertEqual(product.prompts._summary_previous_answers(context), [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
