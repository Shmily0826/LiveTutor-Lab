"""Actual grading/SQLite/Tracker; known aliases only, no model or devices."""
from copy import deepcopy
import json
import unittest
import test_neko_question_topic_binding as binding


class ConceptLabelIdentity(unittest.IsolatedAsyncioTestCase):
    setUp = binding.grade.AnswerMaterial.setUp
    tearDown = binding.grade.AnswerMaterial.tearDown
    model = binding.QuestionTopicBinding.model
    identities = binding.QuestionTopicBinding.identities
    retry = binding.QuestionTopicBinding.retry

    async def start(self):
        await self.h._restart_study_session(course_id='course-A')
        self.model(self.h)

    def catalog(self, topic='arrows', name='有向关系', aliases=None, family=''):
        self.store.upsert_topic({'id': topic, 'name': name, 'subject': 'computer_science',
            'source': 'seed', 'course_family': family,
            'aliases': ['directed relations'] if aliases is None else aliases})

    def question(self, label='有向关系', qid='q-one'):
        self.h._state.current_question = {'question': 'Explain direction for ' + qid,
            'answer': 'source to target', 'question_id': qid, 'attempt_id': 'a-' + qid,
            'topic': label, 'internal_private_payload': {'source_material_context': {
                'course_id': 'course-A', 'session_id': self.h._study_session_id,
                'material_identity': 'a' * 64}}}

    def concept_attempt(self, topic, *, course='course-A', scope='concept', name='有向关系'):
        session = 'owned-' + course
        self.store.ensure_session(session_id=session, course_id=course, mode='teaching')
        self.store.upsert_topic({'id': topic, 'name': name, 'subject': 'computer_science',
            'source': 'runtime', 'aliases': ['directed relations']})
        self.store.add_qa_record(session_id=session, topic_id=topic,
            question={'question': 'Previous different question', 'answer': 'old reference',
                'internal_private_payload': {'learning_topic_binding': {'scope': scope}}},
            user_answer='old answer', eval_result={'verdict': 'wrong', 'score': 0}, mode='teaching')

    async def test_two_distinct_questions_with_registered_translated_alias_share_mastery_and_review_after_restart(self):
        await self.start(); self.catalog(); self.question()
        await self.h.study_answer_tool(answer='wrong first')
        old = deepcopy(self.store.list_qa_records())
        await self.h._persist_state()
        self.h = binding.grade.GradeHarness(self.store); self.model(self.h)
        await self.h._start_study_session('teaching', resume_current_progress=True)
        await self.h.study_set_course(course_id='course-B')
        await self.h.study_set_course(course_id='course-A')
        self.h._cfg.language = 'en-US'; self.question('directed relations', 'q-two')
        await self.h.study_answer_tool(answer='wrong second')
        rows = self.store.list_qa_records()
        self.assertEqual(rows[:1], old)
        self.assertEqual(len(rows), 2)
        self.assertEqual(self.identities(), {table: {'course-A::arrows'} for table in self.identities()})
        self.assertTrue(all(r['question']['internal_private_payload']['learning_topic_binding']['source']
                            == 'unique_concept_label' for r in rows))

    async def test_unknown_display_labels_do_not_create_shared_concepts_or_promote_question_scope(self):
        await self.start(); self.question('new unknown concept')
        await self.h.study_answer_tool(answer='first')
        self.question('new unknown concept', 'q-two')
        await self.h.study_answer_tool(answer='second')
        rows = self.store.list_qa_records()
        self.assertEqual(len({r['topic_id'] for r in rows}), 2)
        self.assertTrue(all(r['topic_id'].startswith('course-A::question_') for r in rows))
        self.assertTrue(all(r['question']['internal_private_payload']['learning_topic_binding']['scope']
                            == 'question' for r in rows))

    async def test_existing_confirmed_course_concept_alias_reuses_identity_without_rewriting_old_qa(self):
        await self.start(); self.concept_attempt('course-A::stable')
        old = deepcopy(self.store.list_qa_records()); self.question('directed relations')
        await self.h.study_answer_tool(answer='later')
        rows = self.store.list_qa_records()
        self.assertEqual(rows[:-1], old)
        self.assertEqual(rows[-1]['topic_id'], 'course-A::stable')

    async def test_ambiguous_registered_alias_does_not_choose_or_merge(self):
        await self.start(); self.catalog('one'); self.catalog('two')
        self.question('directed relations'); await self.h.study_answer_tool(answer='first')
        row = self.store.list_qa_records()[-1]
        self.assertTrue(row['topic_id'].startswith('course-A::question_'))
        self.assertEqual(row['question']['internal_private_payload']['learning_topic_binding']['source'],
                         'ambiguous_concept_label')

    async def test_canonical_dedup_precedes_limit_and_preserves_ambiguity(self):
        await self.start(); self.catalog('one'); self.concept_attempt('course-A::one')
        self.assertEqual(self.store.concept_label_candidates(course_id='course-A', label='directed relations'),
                         ['course-A::one'])
        self.catalog('two')
        self.assertEqual(self.store.concept_label_candidates(course_id='course-A', label='directed relations'),
                         ['course-A::one', 'course-A::two'])

    async def test_foreign_actual_course_or_seed_family_cannot_supply_local_label_identity(self):
        await self.start(); self.concept_attempt('course-A::poison', course='course-B')
        self.catalog('foreign', family='course-B')
        self.assertEqual(self.store.concept_label_candidates(course_id='course-A', label='directed relations'), [])
        self.question('directed relations'); await self.h.study_answer_tool(answer='first')
        self.assertTrue(self.store.list_qa_records(course_id='course-A')[-1]['topic_id'].startswith('course-A::question_'))

    async def test_registered_code_names_are_case_sensitive_and_json_aliases_must_be_text_arrays(self):
        await self.start(); self.catalog('one', name='Foo', aliases=[{'name': 'bad'}, 42, 'Known'])
        for label in ('foo', 'known', 'bad', '42', {'private': 'Known'}):
            self.assertEqual(self.store.concept_label_candidates(course_id='course-A', label=label), [])
        self.assertEqual(self.store.concept_label_candidates(course_id='course-A', label='Known'), ['course-A::one'])
        conn = self.store._require_conn()
        for aliases in ('{broken', json.dumps({'alias': 'Known'}), json.dumps('Known')):
            conn.execute('UPDATE topics SET aliases=? WHERE id=?', (aliases, 'one')); conn.commit()
            self.assertEqual(self.store.concept_label_candidates(course_id='course-A', label='Known'), [])

    async def test_existing_held_binding_is_not_relabelled_by_new_label_or_conflicting_explicit_selection(self):
        await self.start(); self.catalog(); self.question()
        await self.h.study_answer_tool(answer='first'); await self.retry(self.h)
        self.h._state.current_question['topic'] = 'unrelated display label'
        old = deepcopy(self.h._state.current_question['internal_private_payload']['learning_topic_binding'])
        await self.h.study_answer_tool(answer='second')
        self.assertEqual(self.h._state.current_question['internal_private_payload']['learning_topic_binding'], old)
        await self.retry(self.h)
        # Also cover a legacy held artifact whose stable ID lives only privately.
        self.h._state.current_question.pop('selected_topic_id', None)
        self.h._state.current_question.pop('topic_id', None)
        count = self.h._agent.answer_evaluate.await_count
        current = self.h._state.current_question
        result = await self.h.study_evaluate_answer(answer='third', selected_topic_id='different',
            question_id=current['question_id'], attempt_id=current['attempt_id'])
        self.assertEqual(result['code'], 'course_context_changed')
        self.assertEqual(self.h._agent.answer_evaluate.await_count, count)
        self.assertEqual(len(self.store.list_qa_records()), 2)

    async def test_same_question_history_precedes_a_later_catalog_label_match(self):
        await self.start(); self.question('unknown label')
        await self.h.study_answer_tool(answer='first')
        original = self.store.list_qa_records()[0]['topic_id']
        self.catalog(name='unknown label')
        self.question('unknown label')
        # Same question artifact, but no copied private binding: existing QA wins.
        await self.h.study_answer_tool(answer='second')
        self.assertEqual({r['topic_id'] for r in self.store.list_qa_records()}, {original})

    async def test_course_change_during_label_query_does_not_reserve_grade_or_call_model(self):
        await self.start(); self.catalog(); self.question()
        original = self.store.concept_label_candidates
        def changed(**kwargs):
            result = original(**kwargs)
            self.h._state.study_course_id = 'course-B'
            return result
        self.store.concept_label_candidates = changed
        result = await self.h.study_answer_tool(answer='first')
        self.assertEqual(result['code'], 'course_context_changed')
        self.h._agent.answer_evaluate.assert_not_awaited()
        self.assertEqual(self.store.list_qa_records(), [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
