"""Native wrappers through real quiz/grade/summary entries and fresh SQLite, offline."""
import asyncio
import logging
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock
from test_neko_answer_material_guard import GradeHarness,Store,models,materials
from test_neko_quiz_material_guard import Harness as QuestionHarness

class Harness(GradeHarness):
    _generate_question_payload=QuestionHarness._generate_question_payload
    study_generate_question=QuestionHarness.study_generate_question
    study_generate_targeted_question=QuestionHarness.study_generate_targeted_question
    _resolve_active_practice_scope=QuestionHarness._resolve_active_practice_scope
    _practice_scope_write_lock=QuestionHarness._practice_scope_write_lock
    _build_targeted_question_context=QuestionHarness._build_targeted_question_context
    def __init__(self,store):
        super().__init__(store)
        async def question(text,**kwargs):
            return models.TutorReply(operation='question_generate',input_text=text,reply='Which module calls NUD?',
                payload={'question':'Which module calls NUD?','answer':'WEX','reference_answer':'WEX',
                         'hint':'WEX','topic':'Arrows','rubric':{'correct':'WEX'}})
        async def summary(history,**kwargs):
            return models.TutorReply(operation='summarize_session',input_text='session',reply='Practise the arrow direction.',
                payload={'summary':'Practise the arrow direction.'})
        self._agent.question_generate=AsyncMock(side_effect=question)
        self._agent.summarize_session=AsyncMock(side_effect=summary)

class TeachingBinding(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory()
        self.store=Store(Path(self.temporary.name)/'study.db',Path(self.temporary.name)/'seed.json',logging.getLogger('native-binding'))
        self.store.open();self.h=Harness(self.store)
    def tearDown(self):self.store.close();self.temporary.cleanup()
    async def prepare(self,*,picture=True):
        h=self.h;materials.save_material(self.store,'course-A','image-A','Source arrows WEX to NUD')
        await h._restart_study_session(course_id='course-A');h._cfg.llm_vision_enabled=picture
        return h
    async def test_picture_quiz_held_grade_and_summary_keep_their_distinct_origins(self):
        h=await self.prepare();role={'lanlan_name':'OwnedRole'}
        quiz=await h.study_quiz_tool(_ctx=role)
        self.assertEqual(quiz['question'],'Which module calls NUD?');self.assertEqual(quiz['hint'],'')
        self.assertNotIn('answer',quiz);self.assertNotIn('internal_private_payload',quiz)
        self.assertEqual(quiz['_study_material_binding']['context'],materials.material_context(h))
        self.assertEqual(h._agent.question_generate.call_args.kwargs['context']['vision_image_base64'],'image-A')
        identity={key:h._state.current_question[key] for key in ('question_id','attempt_id')}
        origin=dict(h._state.current_question['internal_private_payload']['source_material_context'])
        h._state.last_vision_image_base64='image-B'
        grade=await h.study_answer_tool(answer='REZ',_ctx=role)
        self.assertEqual(grade['verdict'],'wrong');self.assertEqual(grade['score'],0)
        self.assertEqual(set(grade['_study_material_binding']['context']),{'course_id','session_id'})
        self.assertEqual({key:h._state.current_question[key] for key in identity},identity)
        self.assertEqual(h._state.current_question['internal_private_payload']['source_material_context'],origin)
        summary=await h.study_summary_tool(_ctx=role)
        self.assertEqual(summary['reply'],'Practise the arrow direction.')
        self.assertEqual(set(summary['_study_material_binding']['context']),{'course_id','session_id'})
        rows=self.store.list_interactions(10,session_id=h._study_session_id)
        self.assertEqual({row['kind'] for row in rows},{'question_generate','answer_evaluate','summarize_session'})
    async def test_explicit_topic_quiz_does_not_send_saved_picture(self):
        h=await self.prepare();quiz=await h.study_quiz_tool(topic='Events')
        self.assertTrue(quiz['question_id']);self.assertNotIn('material_identity',quiz['_study_material_binding']['context'])
        self.assertEqual(h._agent.question_generate.call_args.kwargs['context']['vision_image_base64'],'')
    async def test_ensure_course_change_never_adopts_new_picture_or_generates_question(self):
        h=await self.prepare()
        async def changed():h._state.study_course_id='course-B'
        h._ensure_active_study_session=changed
        output=await h.study_quiz_tool()
        self.assertEqual(output['code'],'course_context_changed');h._agent.question_generate.assert_not_awaited()
    async def test_same_course_session_change_before_summary_never_adopts_history(self):
        h=await self.prepare()
        async def changed():h._study_session_id='new-session'
        h._ensure_active_study_session=changed
        output=await h.study_summary_tool()
        self.assertEqual(output['code'],'course_context_changed');h._agent.summarize_session.assert_not_awaited()
    async def test_failed_or_late_teaching_result_never_attaches_native_binding(self):
        h=await self.prepare();context=materials.material_context(h,include_material=False)
        failed=await h._study_bind_native_teaching_result({'degraded':True},{'reply':'failure','degraded':True},context,'OwnedRole')
        self.assertNotIn('_study_material_binding',failed)
        h._study_session_id='new-session'
        late=await h._study_bind_native_teaching_result({}, {'reply':'old'},context,'OwnedRole')
        self.assertEqual(late['code'],'course_context_changed');self.assertNotIn('_study_material_binding',late)

if __name__=='__main__':unittest.main(verbosity=2)
