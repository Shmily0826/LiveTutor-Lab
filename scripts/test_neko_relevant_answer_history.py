"""Actual Store/context/prompt with temporary SQLite; no host/model/devices."""
import json
import logging
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import Mock

import test_neko_product_course_memory as memory


class RelevantHistory(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'study.db'
        self.store = memory.Store(self.path, Path(self.temp.name) / 'none.json', logging.getLogger('history'))
        self.store.open()
        self.h = memory.ProductHarness(self.store)
        await self.h._restart_study_session(course_id='course-A')
        self.topic = 'course-A::arrows'
        self.store.ensure_topic(topic_id=self.topic, name='Arrows', subject='computer_science')
        self.store.ensure_topic(topic_id='course-A::noise', name='Other concept', subject='computer_science')

    async def asyncTearDown(self):
        self.store.close()

    def answer(self, marker, *, topic=None, verdict='correct', qid='question-A', key='binding-A', session=None, limit=5000):
        self.store.add_qa_record(session_id=session or self.h._study_session_id, topic_id=topic or self.topic,
            question={'question': marker, 'answer': 'PRIVATE_REFERENCE', 'question_id': qid,
                      'internal_private_payload': {'learning_topic_binding': {'key': key}}},
            user_answer=marker, eval_result={'verdict': verdict, 'feedback': marker,
                                            'score': 0 if verdict == 'wrong' else 100,
                                            'reference_answer': 'PRIVATE_REFERENCE'},
            mode='teaching', history_limit=limit)

    async def context(self, **extra):
        return await self.h._build_learning_context('concept_explain', input_text='Explain my earlier mistake', extra=extra)

    def prompt(self, context):
        return json.dumps(memory.prompts.build_concept_explain_messages(text='Explain my earlier mistake',
            language='en-US', context=context), ensure_ascii=False)

    async def test_old_wrong_and_later_correction_reach_prompt_after_unrelated_qa_and_new_session(self):
        self.answer('OLD_WRONG', verdict='wrong')
        self.answer('LATER_CORRECTION')
        for i in range(7):
            self.answer('LATER_SAME_CONCEPT_' + str(i), qid='other-' + str(i), key='other-' + str(i))
        for i in range(105):
            self.answer('UNRELATED_QA_' + str(i), topic='course-A::noise', qid='noise-' + str(i))
        await self.h._restart_study_session(course_id='course-A')
        context = await self.context(selected_topic_id=self.topic)
        self.assertIn(self.topic, context['course_learning_state']['topic_ids'])
        self.assertLessEqual(len(context['previous_answer_records']), 4)
        prompt = self.prompt(context)
        self.assertIn('OLD_WRONG', prompt)
        self.assertIn('LATER_CORRECTION', prompt)
        self.assertNotIn('UNRELATED_QA_104', prompt)
        self.assertNotIn('PRIVATE_REFERENCE', prompt)
        self.assertNotIn('learning_topic_binding', prompt)
        self.assertEqual({r['topic_id'] for r in context['previous_answer_records']}, {self.topic})
        self.assertEqual([r['evaluation']['score'] for r in context['previous_answer_records'][:2]], [0, 100])

    async def test_prior_session_filter_precedes_limit_and_does_not_leak_other_course(self):
        old = self.h._study_session_id
        self.store.append_interaction(kind='concept_explain', input_text='OLD_SESSION_REMEMBER',
            output_text='old explanation', session_id=old)
        self.store.ensure_session(session_id='foreign', mode='teaching', course_id='course-B')
        self.store.append_interaction(kind='concept_explain', input_text='FOREIGN_COURSE',
            output_text='foreign explanation', session_id='foreign')
        await self.h._restart_study_session(course_id='course-A')
        current = self.h._study_session_id
        for i in range(35):
            self.store.append_interaction(kind='concept_explain', input_text='CURRENT_' + str(i),
                output_text='current explanation', session_id=current, history_limit=2)
        context = await self.context()
        self.assertEqual([r['session_id'] for r in context['previous_course_history']], [old])
        self.assertIn('OLD_SESSION_REMEMBER', self.prompt(context))
        self.assertNotIn('FOREIGN_COURSE', self.prompt(context))
        self.assertTrue(all(r['session_id'] == current for r in context['history']))

    async def test_append_limits_never_delete_saved_interactions_or_answer_evidence(self):
        for i in range(31):
            self.store.append_interaction(kind='concept_explain', input_text=str(i), output_text='retained',
                session_id=self.h._study_session_id, history_limit=2)
            self.answer('ANSWER_' + str(i), limit=2)
        self.assertEqual(len(self.store.list_interactions(100)), 31)
        self.assertEqual(len(self.store.list_qa_records(100)), 31)
        self.assertEqual(len(self.store.list_interactions(2)), 2)
        self.assertEqual(len(self.store.list_qa_records_for_topic(self.topic, 2, course_id='course-A')), 2)

    async def test_exact_topic_is_still_scoped_by_actual_session_course(self):
        self.answer('LOCAL_WRONG', verdict='wrong')
        self.store.ensure_session(session_id='foreign', mode='teaching', course_id='course-B')
        self.answer('FOREIGN_POISON', verdict='wrong', session='foreign')
        context = await self.context(selected_topic_id=self.topic)
        self.assertIn('LOCAL_WRONG', self.prompt(context))
        self.assertNotIn('FOREIGN_POISON', self.prompt(context))
        self.assertFalse((await self.context(selected_topic_id='course-B::arrows'))['previous_answer_records'])

    async def test_unconfirmed_query_does_not_retrieve_unrelated_older_answers(self):
        self.answer('DO_NOT_GUESS_TOPIC', verdict='wrong')
        context = await self.context()
        self.assertEqual(context['previous_answer_records'], [])

    async def test_prompt_projection_is_bounded_and_never_includes_private_question_fields(self):
        context = await self.context()
        context['previous_answer_records'] = [{'question': {'question': 'VISIBLE', 'answer': 'PRIVATE_Q'},
            'user_answer': 'x' * 9000, 'evaluation': {'feedback': 'y' * 9000, 'rubric': 'PRIVATE_R'},
            'internal_private_payload': 'PRIVATE_METADATA'}] * 10
        block = memory.prompts.build_concept_recent_context(context)
        self.assertEqual(block.count('VISIBLE'), 4)
        self.assertLess(len(block), 3500)
        self.assertNotIn('PRIVATE_', block)

    async def test_request_extras_cannot_select_foreign_history_scope(self):
        self.store.ensure_topic(topic_id='course-B::arrows', name='Foreign arrows', subject='computer_science')
        self.store.ensure_session(session_id='foreign', mode='teaching', course_id='course-B')
        self.answer('FOREIGN_REQUEST', topic='course-B::arrows', session='foreign')
        context = await self.context(course_id='course-B', session_id='foreign', selected_topic_id='course-B::arrows')
        self.assertEqual(context['course_id'], 'course-A')
        self.assertEqual(context['session_id'], self.h._study_session_id)
        self.assertEqual(context['previous_answer_records'], [])
        self.assertNotIn('FOREIGN_REQUEST', self.prompt(context))

    async def test_actual_guidance_selected_topic_uses_same_existing_answer_identity(self):
        self.answer('ACTUAL_GUIDANCE_MISTAKE', verdict='wrong')
        self.h._build_knowledge_guidance_context = types.MethodType(
            memory.context_module._TutorContextSupportMixin._build_knowledge_guidance_context, self.h)
        context = await self.context(selected_topic_id=self.topic)
        self.assertTrue(context['knowledge_guidance']['summary']['matched'])
        self.assertEqual(context['knowledge_guidance']['topic']['id'], self.topic)
        self.assertIn('ACTUAL_GUIDANCE_MISTAKE', self.prompt(context))

    async def test_unavailable_relevant_read_keeps_current_lesson_usable(self):
        self.answer('RECORDED', verdict='wrong')
        self.store.list_qa_records_for_topic = Mock(side_effect=RuntimeError('local read unavailable'))
        context = await self.context(selected_topic_id=self.topic)
        self.assertEqual(context['previous_answer_records'], [])
        self.assertIn('Explain my earlier mistake', self.prompt(context))

    async def test_binding_changed_with_same_question_id_cannot_replace_true_correction_lookup(self):
        self.answer('OLD_WRONG', verdict='wrong')
        self.answer('CORRECTION_SAME_BINDING')
        for i in range(7):
            self.answer('OTHER_QUESTION_' + str(i), qid='q-other-' + str(i), key='key-other-' + str(i))
        self.answer('REUSED_ID_OTHER_BINDING', key='different-material')
        context = await self.context(selected_topic_id=self.topic)
        selected = context['previous_answer_records']
        self.assertIn('CORRECTION_SAME_BINDING', [r['user_answer'] for r in selected])
        self.assertIn('OLD_WRONG', [r['user_answer'] for r in selected])
        self.assertNotIn('REUSED_ID_OTHER_BINDING', [r['user_answer'] for r in selected])

    async def test_malformed_saved_text_cannot_stringify_private_data_in_relevant_or_fallback_prompt(self):
        self.store.add_qa_record(session_id=self.h._study_session_id, topic_id=self.topic,
            question={'question': {'answer': 'PRIVATE_NESTED_QUESTION'}, 'question_id': 'q-malformed'},
            user_answer='VISIBLE_LEARNER_ANSWER',
            eval_result={'verdict': 'wrong', 'score': 42,
                         'feedback': {'api_key': 'PRIVATE_NESTED_FEEDBACK'}},
            mode='teaching', history_limit=5000)
        for selected in (self.topic, ''):
            with self.subTest(selected=selected):
                context = await self.context(selected_topic_id=selected)
                prompt = self.prompt(context)
                self.assertNotIn('PRIVATE_NESTED_', prompt)
                self.assertIn('VISIBLE_LEARNER_ANSWER', prompt)
                block = memory.prompts.build_concept_recent_context(context)
                data = json.loads(block[block.index('{'):])
                row = data['previous_answers'][0]
                self.assertEqual(row['question'], '')
                self.assertEqual(row['evaluation']['feedback'], '')
                self.assertEqual(row['evaluation']['score'], 42)
        self.store.list_qa_records_for_topic = Mock(side_effect=RuntimeError('unavailable'))
        self.assertNotIn('PRIVATE_NESTED_', self.prompt(await self.context(selected_topic_id=self.topic)))

    async def test_direct_prompt_history_rejects_nontext_identifiers_answers_and_verdicts(self):
        poison = {'api_key': 'PRIVATE_NONTEXT'}
        context = await self.context()
        context['course_learning_state']['recent_answers'] = [{'question': poison,
            'topic_id': poison, 'question_id': poison, 'user_answer': poison,
            'eval_result': {'verdict': poison, 'feedback': poison, 'score': True}}]
        self.assertNotIn('PRIVATE_NONTEXT', self.prompt(context))

        context['previous_answer_records'] = [{'question': {'question': poison},
            'topic_id': poison, 'question_id': poison, 'user_answer': poison,
            'evaluation': {'verdict': poison, 'feedback': poison, 'score': float('nan')}}]
        self.assertNotIn('PRIVATE_NONTEXT', self.prompt(context))

    async def test_history_prompt_marks_coverage_and_forbids_exhaustive_negative_claims(self):
        self.answer('EARLY_WRONG', verdict='wrong')
        for selected in (self.topic, ''):
            context = await self.context(selected_topic_id=selected)
            block = memory.prompts.build_concept_recent_context(context)
            self.assertIn('selected_bounded_records_not_complete_history', block)
            self.assertIn('Missing records do not prove an event never happened', block)
            self.assertIn('Do not claim there were no other or earlier mistakes', block)


if __name__ == '__main__':
    unittest.main(verbosity=2)
