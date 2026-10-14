"""Actual grading entries / Store / Tracker, temporary SQLite, model double only."""
import asyncio
from copy import deepcopy
import json
import unittest
from unittest.mock import AsyncMock
import test_neko_answer_material_guard as grade

QUESTION='已有关系对照图的两条连接是 WEX→NUD、NUD→REZ。从 NUD 出发的那条箭头，起点和终点分别是什么？'
REFERENCE='起点 NUD，终点 REZ。'


class QuestionTopicBinding(unittest.IsolatedAsyncioTestCase):
    setUp=grade.AnswerMaterial.setUp
    tearDown=grade.AnswerMaterial.tearDown
    prepare=grade.AnswerMaterial.prepare

    def model(self, h):
        async def evaluate(**kwargs):
            label='directed relations' if h._cfg.language=='en-US' else '有向关系'
            return grade.models.TutorReply(operation='answer_evaluate',input_text=kwargs['answer'],reply=label,
                payload={'verdict':'wrong','score':0,'feedback':label,'related_topics':[label]})
        h._agent.answer_evaluate=AsyncMock(side_effect=evaluate)

    async def anonymous(self):
        await self.h._restart_study_session(course_id='course-A')
        self.model(self.h)
        return self.h

    async def supplied(self, h=None, **changes):
        h=h or self.h
        return await h.study_evaluate_answer(**{'question':QUESTION,'expected_answer':REFERENCE,
                                                'answer':'WEX指向NUD',**changes})

    def identities(self):
        conn=self.store._require_conn()
        return {table:{row[0] for row in conn.execute('SELECT DISTINCT topic_id FROM '+table)}
                for table in ('qa_records','mastery_snapshots','fsrs_cards')}

    async def retry(self,h):
        q=h._state.current_question
        result=await h.study_retry_question(question_id=q['question_id'],attempt_id=q['attempt_id'],
            course_id=h._state.study_course_id,session_id=h._state.study_session_id)
        self.assertTrue(result['retried'])

    def seed_legacy(self,topic,question=QUESTION,reference=REFERENCE):
        scoped='course-A::'+topic
        self.store.ensure_topic(topic_id=scoped,name=topic,subject='computer_science')
        self.store.add_qa_record(session_id=self.h._study_session_id,topic_id=scoped,mode='teaching',
            question={'question':question,'answer':reference,'course_family':'course-A'},
            user_answer='old answer',eval_result={'verdict':'wrong','score':0})

    async def test_topicless_held_retry_languages_share_mastery_and_fsrs_and_preserve_old_grade(self):
        h=await self.prepare();h._state.current_question.pop('topic');self.model(h)
        first=await h.study_answer_tool(answer='REZ');self.assertEqual(first['verdict'],'wrong')
        before=deepcopy(self.store.list_qa_records());binding=h._state.current_question['internal_private_payload']['learning_topic_binding']
        self.assertEqual(binding['scope'],'question')
        self.assertNotIn('learning_topic_binding',json.dumps(grade.models.public_current_question_payload(h._state.current_question)))
        await self.retry(h);h._cfg.language='en-US'
        await h.study_answer_tool(answer='REZ')
        rows=self.store.list_qa_records();self.assertEqual(rows[:1],before)
        self.assertEqual(len(rows),2);self.assertEqual(rows[0]['topic_id'],rows[1]['topic_id'])
        self.assertNotEqual(rows[0]['question']['attempt_id'],rows[1]['question']['attempt_id'])
        self.assertEqual(self.identities(),{table:{binding['topic_id']} for table in self.identities()})
        self.assertEqual(self.store.get_topic(binding['topic_id'])['name'],binding['label'])

    async def test_existing_held_topic_and_explicit_seed_remain_authoritative(self):
        h=await self.prepare();self.model(h)
        await h.study_answer_tool(answer='REZ');await self.retry(h);h._cfg.language='en-US'
        await h.study_answer_tool(answer='REZ')
        self.assertEqual({r['topic_id'] for r in self.store.list_qa_records()},{'course-A::arrows'})
        h._state.current_question={}
        await self.supplied(selected_topic_id='arrows')
        self.assertEqual({r['topic_id'] for r in self.store.list_qa_records()},{'course-A::arrows'})

    async def test_anonymous_same_question_uses_one_provisional_identity_across_languages(self):
        h=await self.anonymous();await self.supplied();old=deepcopy(self.store.list_qa_records())
        h._cfg.language='en-US';await self.supplied()
        rows=self.store.list_qa_records();self.assertEqual(rows[:1],old)
        self.assertEqual(len({r['topic_id'] for r in rows}),1)
        self.assertTrue(all(r['question']['internal_private_payload']['learning_topic_binding']['scope']=='question' for r in rows))

    async def test_unique_legacy_question_reuses_existing_topic_without_rewriting_history(self):
        await self.anonymous();self.seed_legacy('有向关系');old=deepcopy(self.store.list_qa_records())
        await self.supplied()
        rows=self.store.list_qa_records();self.assertEqual(rows[:1],old)
        self.assertEqual(rows[-1]['topic_id'],old[0]['topic_id'])

    async def test_ambiguous_legacy_topics_are_not_arbitrarily_selected_or_merged(self):
        h=await self.anonymous();self.seed_legacy('有向关系');self.seed_legacy('directed relations')
        old=deepcopy(self.store.list_qa_records());await self.supplied();h._cfg.language='en-US';await self.supplied()
        rows=self.store.list_qa_records();self.assertEqual(rows[:2],old)
        self.assertNotIn(rows[2]['topic_id'],{r['topic_id'] for r in old})
        self.assertEqual(rows[2]['topic_id'],rows[3]['topic_id'])
        self.assertEqual(rows[2]['question']['internal_private_payload']['learning_topic_binding']['source'],'ambiguous_history')

    async def test_changed_reference_question_image_or_course_never_reuses_provisional_identity(self):
        h=await self.anonymous()
        for changes in ({},{'expected_answer':'起点REZ，终点NUD'},
                        {'question':QUESTION+' 请解释为什么。'},
                        {'vision_image_base64':'image-A'},{'vision_image_base64':'image-B'}):
            await self.supplied(**changes)
        ids=[r['topic_id'] for r in self.store.list_qa_records()];self.assertEqual(len(set(ids)),5)
        await h._restart_study_session(course_id='course-B');await self.supplied()
        rows=self.store.list_qa_records();self.assertTrue(rows[-1]['topic_id'].startswith('course-B::'))

    async def test_explicit_material_scope_changes_identity_but_ordinary_text_does_not_consult_current_picture(self):
        h=await self.anonymous();await self.supplied()
        h._state.last_vision_image_base64='new unrelated current image';await self.supplied()
        rows=self.store.list_qa_records();self.assertEqual(rows[0]['topic_id'],rows[1]['topic_id'])
        for image in ('explicit image A','explicit image B'):
            h._state.last_vision_image_base64=image
            await self.supplied(_material_context=grade.materials.material_context(h))
        rows=self.store.list_qa_records();self.assertEqual(len({row['topic_id'] for row in rows}),3)

    async def test_restart_and_course_return_keep_held_binding_and_original_qa(self):
        h=await self.prepare();h._state.current_question.pop('topic');self.model(h)
        await h.study_answer_tool(answer='REZ');before=deepcopy(self.store.list_qa_records())
        binding=deepcopy(h._state.current_question['internal_private_payload']['learning_topic_binding'])
        await h._persist_state();h=grade.GradeHarness(self.store);self.h=h;self.model(h)
        await h._start_study_session(h._state.active_mode,resume_current_progress=True)
        await h.study_set_course(course_id='course-B');await h.study_set_course(course_id='course-A')
        self.assertEqual(h._state.current_question['internal_private_payload']['learning_topic_binding'],binding)
        await self.retry(h);h._cfg.language='en-US';await h.study_answer_tool(answer='REZ')
        rows=self.store.list_qa_records();self.assertEqual(rows[:1],before);self.assertEqual(rows[-1]['topic_id'],before[0]['topic_id'])

    async def test_foreign_scoped_selection_and_scope_change_during_lookup_never_call_model(self):
        h=await self.anonymous();result=await self.supplied(selected_topic_id='course-B::arrows')
        self.assertEqual(result['code'],'course_context_changed');h._agent.answer_evaluate.assert_not_awaited()
        self.store.ensure_topic(topic_id='course-B::arrows',name='foreign legacy runtime',subject='computer_science')
        result=await self.supplied(selected_topic_id='course-B::arrows')
        self.assertEqual(result['code'],'course_context_changed');h._agent.answer_evaluate.assert_not_awaited()
        original=h._resolve_learning_topic_binding
        async def moved(*args,**kwargs):
            value=await original(*args,**kwargs);h._state.study_course_id='course-B';return value
        h._resolve_learning_topic_binding=moved
        result=await self.supplied();self.assertEqual(result['code'],'course_context_changed');h._agent.answer_evaluate.assert_not_awaited()
        self.assertEqual(self.store.list_qa_records(),[])

    async def test_only_known_seed_namespace_can_be_scoped_under_current_course(self):
        await self.anonymous()
        self.store.upsert_topic({'id':'computer_science::arrows','name':'Arrows','subject':'computer_science','source':'seed'})
        await self.supplied(selected_topic_id='computer_science::arrows')
        self.assertEqual(self.store.list_qa_records()[-1]['topic_id'],'course-A::computer_science::arrows')

    async def test_failed_grade_clears_reservation_without_saving_a_binding(self):
        h=await self.prepare();h._state.current_question.pop('topic')
        h._agent.answer_evaluate=AsyncMock(side_effect=RuntimeError('isolated ensure failure'))
        result=await h.study_answer_tool(answer='REZ');self.assertIn('error',result)
        self.assertNotIn('learning_topic_binding',h._state.current_question['internal_private_payload'])
        self.assertNotIn('attempt_evaluation_owner',h._state.current_question)
        self.assertEqual(self.store.list_qa_records(),[])

    async def test_history_uniqueness_is_not_decided_from_only_the_latest_rows(self):
        await self.anonymous();self.seed_legacy('old-stable')
        for n in range(105):self.seed_legacy('other',question='Unrelated '+str(n))
        self.seed_legacy('different-stable');old=deepcopy(self.store.list_qa_records(200))
        await self.supplied();rows=self.store.list_qa_records(200)
        self.assertEqual(rows[:-1],old)
        self.assertEqual(rows[-1]['question']['internal_private_payload']['learning_topic_binding']['source'],'ambiguous_history')


if __name__=='__main__':unittest.main(verbosity=2)
