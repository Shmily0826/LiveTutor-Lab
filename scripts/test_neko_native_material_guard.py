"""Native wrapper -> actual explain entry/finalizer, fresh SQLite and fake model only."""
import asyncio
import importlib
import threading
import unittest
from unittest.mock import AsyncMock
import test_neko_explanation_language as language_tests
from test_neko_image_course_guard import product_method, explain_namespace, SOURCE
from test_neko_product_course_memory import context_module, models

materials=importlib.import_module('product_study.study_materials')

class NativeMaterialGuard(language_tests.ExplanationLanguage):
    # Reuse only the fresh data setup; do not rerun the inherited language suite.
    test_explicit_language_survives_question_rewording_and_leaves_saved_preference=None
    test_counted_chinese_request_and_negation_are_not_confused_with_language_noun=None
    test_failure_restores_language_and_invalid_override_never_calls_backend=None
    test_overlapping_one_turn_calls_do_not_restore_another_temporary_language=None

    async def prepare(self):
        h=self.h;materials.save_material(self.store,'course-A','image-A','source-A')
        await h._restart_study_session(course_id='course-A')
        h._cfg.llm_vision_enabled=True;h._cfg.communication.enabled=False
        namespace=explain_namespace()
        namespace.update({'material_context_current':materials.material_context_current,
                          'MaterialContextChanged':materials.MaterialContextChanged,
                          '_TutorFinalizeProgress':context_module._TutorFinalizeProgress,
                          '_FINALIZE_TIMEOUT_SECONDS':5,'MODE_CONCEPT_EXPLAIN':'concept_explain',
                          'build_concept_recent_context':lambda context:'',
                          'prepare_general_narration_content':lambda text:text,'Ok':lambda value:value})
        entry=product_method(SOURCE,'study_explain_text',namespace)
        h.study_explain_text=entry.__get__(h);h._resolve_study_target_lanlan=lambda kwargs:''
        h._emit_general_response_completed_event=AsyncMock(return_value=True)
        h._emit_solution_completed_event=AsyncMock(return_value=True)
        async def build(operation,*,session_id,**kwargs):
            return {'course_id':h._state.study_course_id,'session_id':session_id,
                    'study_response_mode':'general_explanation','study_semantic_status':'grounded'}
        h._build_learning_context=build
        async def model(source,**kwargs):
            return models.TutorReply(operation='concept_explain',input_text=source,reply='one current explanation',
                                    payload={'reply':'one current explanation','summary':'one current explanation'})
        h._agent=type('Agent',(),{'concept_explain':staticmethod(AsyncMock(side_effect=model))})()
        return h

    async def test_native_unchanged_snapshot_reaches_model_and_records_its_identity(self):
        h=await self.prepare();expected=materials.material_context(h)
        output=await h.study_explain_tool(question='Explain this architecture diagram',language='en-US')
        self.assertFalse(output.get('degraded'),output);self.assertEqual(output['reply'],'one current explanation')
        h._agent.concept_explain.assert_awaited_once()
        rows=self.store.list_interactions(10,session_id=h._study_session_id)
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['metadata']['material_context'],expected)
        self.assertEqual(h._cfg.language,'zh-CN')

    async def test_waiting_native_request_never_adopts_replacement_picture(self):
        for change in ('image','text','course'):
            with self.subTest(change=change):
                h=await self.prepare();h._study_explanation_language_lock=asyncio.Lock()
                await h._study_explanation_language_lock.acquire()
                request=asyncio.create_task(h.study_explain_tool(question='Explain this diagram',language='en-US'))
                await asyncio.sleep(.02)
                async with h._lock:
                    if change=='image':h._state.last_vision_image_base64='image-B'
                    elif change=='text':h._state.last_ocr_text='source-B'
                    else:h._state.study_course_id='course-B'
                h._study_explanation_language_lock.release();result=await request
                self.assertEqual(result['code'],'course_context_changed')
                h._agent.concept_explain.assert_not_awaited()
                self.assertEqual(h._cfg.language,'zh-CN')

    async def test_same_course_picture_changes_during_build_or_model_never_finalize(self):
        for phase in ('build','model'):
            with self.subTest(phase=phase):
                h=await self.prepare();finalize=AsyncMock();h._finalize_tutor_call=finalize
                if phase=='build':
                    old=h._build_learning_context
                    async def changed_build(*args,**kwargs):
                        value=await old(*args,**kwargs);h._state.last_vision_image_base64='image-B';return value
                    h._build_learning_context=changed_build
                else:
                    async def changed_model(source,**kwargs):
                        h._state.last_vision_image_base64='image-B'
                        return models.TutorReply(operation='concept_explain',input_text=source,reply='old picture reply')
                    h._agent.concept_explain=AsyncMock(side_effect=changed_model)
                result=await h.study_explain_tool(question='Explain this diagram')
                self.assertEqual(result['code'],'course_context_changed');finalize.assert_not_awaited()

    async def test_session_initialization_cannot_rebind_an_already_observed_course(self):
        h=await self.prepare()
        async def changed_ensure():h._state.study_course_id='course-B'
        h._ensure_active_study_session=changed_ensure
        result=await h.study_explain_tool(question='Explain this diagram')
        self.assertFalse(result['ok']);self.assertEqual(result['error'],'course_context_changed')
        h._agent.concept_explain.assert_not_awaited()

    async def test_explicit_source_text_does_not_send_an_unrelated_saved_picture(self):
        h=await self.prepare()
        h._build_learning_context=language_tests.ProductHarness._build_learning_context.__get__(h)
        output=await h.study_explain_tool(question='Explain this source line',text='13 return temperature;')
        self.assertFalse(output.get('degraded'),output)
        context=h._agent.concept_explain.call_args.kwargs['context']
        self.assertFalse(context['vision_enabled']);self.assertEqual(context['vision_image_base64'],'')
        self.assertIn('13 return temperature;',context['source_text'])

    async def test_ensure_allows_absent_session_initialization_but_rejects_existing_session_replacement(self):
        for initially_absent in (False, True):
            with self.subTest(initially_absent=initially_absent):
                h=await self.prepare()
                if initially_absent:
                    async with h._study_session_lock:
                        await h._end_study_session_locked()
                async def restarted_ensure():
                    return await h._restart_study_session(course_id='course-A')
                h._ensure_active_study_session=restarted_ensure
                result=await h.study_explain_tool(question='Explain this diagram')
                if initially_absent:
                    self.assertFalse(result.get('degraded'),result)
                    self.assertEqual(result['reply'],'one current explanation')
                    h._agent.concept_explain.assert_awaited_once()
                else:
                    self.assertEqual(result['error'],'course_context_changed')
                    h._agent.concept_explain.assert_not_awaited()

    async def test_stale_material_before_history_commit_writes_no_history_or_progress(self):
        h=await self.prepare();expected=materials.material_context(h)
        h._state.last_vision_image_base64='image-B'
        reply=models.TutorReply(operation='concept_explain',input_text='old material',reply='old reply')
        with self.assertRaises(materials.MaterialContextChanged):
            await h._finalize_tutor_call('concept_explain',reply,history_kind='concept_explain',metadata={},
                extra_context={'session_id':h._study_session_id,'_material_context':expected})
        self.assertEqual(self.store.list_interactions(10,session_id=h._study_session_id),[])
        self.assertEqual(h._state.recent_learning_events,[])

    async def test_replaced_material_failure_does_not_set_new_course_error(self):
        h=await self.prepare();expected=materials.material_context(h);before=h._state.last_error
        h._state.last_vision_image_base64='image-B'
        reply=models.TutorReply(operation='concept_explain',input_text='old',reply='failed',degraded=True,diagnostic='provider_unavailable')
        with self.assertRaises(materials.MaterialContextChanged):
            await h._finalize_tutor_call('concept_explain',reply,history_kind='concept_explain',metadata={},
                extra_context={'session_id':h._study_session_id,'_material_context':expected})
        self.assertEqual(h._state.last_error,before)

    async def test_material_change_waits_for_short_db_commit_then_blocks_live_seed_narration_and_return(self):
        h=await self.prepare();h._cfg.communication.enabled=True
        expected=materials.material_context(h);entered=threading.Event();release=threading.Event()
        original=self.store.append_interaction
        def paused_append(**kwargs):
            entered.set()
            if not release.wait(3):raise RuntimeError('test worker was not released')
            return original(**kwargs)
        self.store.append_interaction=paused_append
        request=asyncio.create_task(h.study_explain_tool(question='Explain this diagram'))
        self.assertTrue(await asyncio.to_thread(entered.wait,2))
        async def replace():
            async with h._lock:h._state.last_vision_image_base64='image-B'
        replacement=asyncio.create_task(replace());await asyncio.sleep(.02)
        self.assertFalse(replacement.done()) # material setter and SQL use the same existing lock
        release.set();result=await request;await replacement
        self.assertEqual(result['code'],'course_context_changed')
        rows=self.store.list_interactions(10,session_id=h._study_session_id)
        self.assertEqual(len(rows),1) # preserved history committed BEFORE replacement
        self.assertEqual(rows[0]['metadata']['material_context'],expected)
        self.assertEqual(h._state.recent_learning_events,[])
        self.assertEqual(h._state.session_summary_seed,{})
        h._emit_general_response_completed_event.assert_not_awaited()
        h._emit_solution_completed_event.assert_not_awaited()

if __name__=='__main__':unittest.main(verbosity=2)
