"""Actual grade entry/wrapper/finalizer/SQLite, fake model only; no host or audio."""
import ast
import asyncio
import contextlib
import importlib
import logging
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import AsyncMock
from test_neko_explanation_language import Harness
from test_neko_product_course_memory import SOURCE,Store,models

materials=importlib.import_module('product_study.study_materials')
class EntryError(Exception):
    def __init__(self,message,*,code=''):super().__init__(message);self.code=code
class EntryErrorResult(dict):
    def __init__(self,error):super().__init__(error=str(error),code=getattr(error,'code',''))
def unexpected_entry_error(host,error,**kwargs):
    if str(error)=='isolated ensure failure':return {'error':str(error),'code':type(error).__name__}
    raise error
scope={'asyncio':asyncio,'contextlib':contextlib,'Err':EntryErrorResult,
       'Ok':lambda value:value,'SdkError':EntryError,'LLM_OPERATION_ANSWER_EVALUATE':'answer_evaluate',
       '_entry_exception_error':unexpected_entry_error,
       '_validate_optional_vision_image_payload':lambda host,value,**kwargs:value,
       'public_current_question_payload':models.public_current_question_payload,
       'material_context':materials.material_context,'material_context_current':materials.material_context_current,
       'MaterialContextChanged':materials.MaterialContextChanged}
tree=ast.parse((SOURCE/'entry_tutor_answer_entries.py').read_text(encoding='utf-8'))
entry=next(node for node in tree.body if isinstance(node,ast.ClassDef))
for method in entry.body:
    if isinstance(method,(ast.FunctionDef,ast.AsyncFunctionDef)):method.decorator_list=[]
exec(compile(ast.fix_missing_locations(ast.Module(body=[entry],type_ignores=[])),'actual grade entry','exec'),scope)

class GradeHarness(scope[entry.name],Harness):
    def __init__(self,store):
        Harness.__init__(self,store)
        self._resolve_study_target_lanlan=lambda kwargs:'';self._resolve_current_run_id=lambda kwargs:''
        # No screen observation or knowledge-guidance UI cache in this offline
        # fixture; answer/tracker/Store methods themselves remain real.
        self._screen_classification_context=lambda:{}
        self._invalidate_knowledge_guidance_cache=lambda:None
        self._emit_answer_evaluated_event=AsyncMock(return_value=True)
        self._agent=types.SimpleNamespace(answer_evaluate=AsyncMock(side_effect=self.model))
    async def model(self,**kwargs):
        return models.TutorReply(operation='answer_evaluate',input_text=kwargs['answer'],reply='The held question expected WEX.',
            payload={'feedback':'The held question expected WEX.','verdict':'wrong','score':0,'topic':'arrows','misconceptions':['direction']})

class AnswerMaterial(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory()
        self.store=Store(Path(self.temporary.name)/'study.db',Path(self.temporary.name)/'seed.json',logging.getLogger('answer-material'))
        self.store.open();self.h=GradeHarness(self.store)
    def tearDown(self):self.store.close();self.temporary.cleanup()
    async def prepare(self):
        h=self.h;await h._restart_study_session(course_id='course-A')
        self.origin={'course_id':'course-A','session_id':'original-question-session','material_identity':'a'*64}
        h._state.current_question={'question':'Which module calls NUD?','answer':'WEX','question_id':'question-owned',
            'attempt_id':'attempt-owned','topic':'arrows','internal_private_payload':{'source_material_context':dict(self.origin)}}
        return h
    async def test_held_question_grade_preserves_origin_ids_and_binds_only_request_scope(self):
        h=await self.prepare();output=await h.study_answer_tool(answer='REZ',_ctx={'lanlan_name':'GradeRole'})
        self.assertEqual(output['verdict'],'wrong');self.assertEqual(output['score'],0)
        self.assertEqual(set(output['_study_material_binding']['context']),{'course_id','session_id'})
        self.assertEqual(h._agent.answer_evaluate.await_count,1)
        rows=self.store.list_interactions(10,session_id=h._study_session_id)
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['metadata']['source_material_context'],self.origin)
        self.assertTrue(h._state.current_question['attempt_evaluated'])
        again=await h.study_answer_tool(answer='REZ')
        self.assertEqual(again['code'],'ATTEMPT_ALREADY_EVALUATED');self.assertEqual(h._agent.answer_evaluate.await_count,1)
        self.assertEqual(len(self.store.list_interactions(10,session_id=h._study_session_id)),1)
    async def test_picture_only_change_during_grade_does_not_relabel_or_invalidate_held_question(self):
        h=await self.prepare();original=h.model
        async def changed(**kwargs):h._state.last_vision_image_base64='new-current-picture';return await original(**kwargs)
        h._agent.answer_evaluate=AsyncMock(side_effect=changed)
        output=await h.study_answer_tool(answer='REZ')
        self.assertEqual(output['verdict'],'wrong')
        self.assertNotIn('material_identity',output['_study_material_binding']['context'])
        self.assertEqual(h._agent.answer_evaluate.call_args.kwargs['expected_answer'],'WEX')
    async def test_immutable_grade_does_not_send_new_image_or_ocr_to_model(self):
        h=await self.prepare();h._cfg.llm_vision_enabled=True
        h._state.last_vision_image_base64='NEW unrelated picture';h._state.last_ocr_text='NEW unrelated OCR'
        output=await h.study_answer_tool(answer='REZ')
        self.assertEqual(output['verdict'],'wrong')
        context=h._agent.answer_evaluate.call_args.kwargs['context']
        self.assertFalse(context['vision_enabled']);self.assertEqual(context['vision_image_base64'],'')
        self.assertEqual(context['last_ocr_text'],'')
    async def test_empty_active_session_cannot_write_to_a_supplied_foreign_session(self):
        h=await self.prepare();h._study_session_id='';h._state.study_session_id=''
        output=await h.study_evaluate_answer(answer='REZ',question_id='question-owned',attempt_id='attempt-owned',session_id='foreign')
        self.assertEqual(output['code'],'course_context_changed')
        self.assertEqual(self.store.list_interactions(10,session_id='foreign'),[])
        h._agent.answer_evaluate.assert_not_awaited()
        self.assertNotIn('attempt_evaluation_pending',h._state.current_question)
    async def test_direct_grade_new_question_rejects_old_feedback_after_retaining_original_history(self):
        h=await self.prepare();original=h.model
        new={'question':'New task','answer':'NUD','question_id':'new-question','attempt_id':'new-attempt'}
        async def changed(**kwargs):h._state.current_question=dict(new);return await original(**kwargs)
        h._agent.answer_evaluate=AsyncMock(side_effect=changed)
        output=await h.study_evaluate_answer(answer='REZ',question_id='question-owned',attempt_id='attempt-owned')
        self.assertEqual(output['code'],'course_context_changed')
        h._emit_answer_evaluated_event.assert_not_awaited();self.assertEqual(h._state.current_question,new)
        self.assertEqual(h._state.last_answer_evaluation,{})
        rows=self.store.list_interactions(10,session_id=h._study_session_id)
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['metadata']['question_id'],'question-owned')
    async def test_course_change_during_model_records_no_fake_grade_and_clears_reservation(self):
        h=await self.prepare();session=h._study_session_id;original=h.model
        async def changed(**kwargs):h._state.study_course_id='course-B';return await original(**kwargs)
        h._agent.answer_evaluate=AsyncMock(side_effect=changed)
        output=await h.study_answer_tool(answer='REZ')
        self.assertEqual(output['code'],'course_context_changed')
        self.assertNotIn('_study_material_binding',output)
        self.assertEqual(self.store.list_interactions(10,session_id=session),[])
        self.assertNotIn('attempt_evaluation_pending',h._state.current_question)
        self.assertFalse(h._state.current_question.get('attempt_evaluated',False))
        h._emit_answer_evaluated_event.assert_not_awaited()
    async def test_wrong_question_identity_never_reserves_or_calls_model(self):
        h=await self.prepare()
        output=await h.study_evaluate_answer(answer='REZ',question_id='other-question',attempt_id='attempt-owned')
        self.assertEqual(output['code'],'QUESTION_MISMATCH');h._agent.answer_evaluate.assert_not_awaited()
        self.assertNotIn('attempt_evaluation_pending',h._state.current_question)
    async def test_ensure_failure_does_not_leave_attempt_reserved(self):
        h=await self.prepare()
        async def fail():raise RuntimeError('isolated ensure failure')
        h._ensure_active_study_session=fail
        output=await h.study_evaluate_answer(answer='REZ',question_id='question-owned',attempt_id='attempt-owned')
        self.assertEqual(output['code'],'RuntimeError')
        self.assertNotIn('attempt_evaluation_pending',h._state.current_question)
        h._agent.answer_evaluate.assert_not_awaited()
    async def test_new_question_during_grade_retains_old_history_but_never_returns_current_feedback(self):
        h=await self.prepare();original=h.model
        new={'question':'New task','answer':'NUD','question_id':'new-question','attempt_id':'new-attempt'}
        async def changed(**kwargs):h._state.current_question=dict(new);return await original(**kwargs)
        h._agent.answer_evaluate=AsyncMock(side_effect=changed)
        output=await h.study_answer_tool(answer='REZ')
        self.assertEqual(output['code'],'course_context_changed');self.assertNotIn('_study_material_binding',output)
        self.assertEqual(h._state.current_question,new)
        rows=self.store.list_interactions(10,session_id=h._study_session_id)
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['metadata']['question_id'],'question-owned')
    async def test_course_change_after_commit_keeps_original_history_and_suppresses_return(self):
        h=await self.prepare();original=h._finalize_tutor_call;session=h._study_session_id
        async def changed(*args,**kwargs):
            result=await original(*args,**kwargs);h._state.study_course_id='course-B';return result
        h._finalize_tutor_call=changed
        output=await h.study_answer_tool(answer='REZ')
        self.assertEqual(output['code'],'course_context_changed');h._emit_answer_evaluated_event.assert_not_awaited()
        rows=self.store.list_interactions(10,session_id=session)
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['metadata']['material_context']['course_id'],'course-A')

if __name__=='__main__':unittest.main(verbosity=2)
