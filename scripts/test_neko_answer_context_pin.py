"""Pinned grade identity with actual entries/SQLite; local model, no host/audio."""
from copy import deepcopy
import ast
import contextlib
import json
from pathlib import Path
import queue
import unittest
from unittest.mock import AsyncMock
import test_neko_answer_material_guard as grade

class AnswerContextPin(unittest.IsolatedAsyncioTestCase):
    setUp=grade.AnswerMaterial.setUp
    tearDown=grade.AnswerMaterial.tearDown
    prepare=grade.AnswerMaterial.prepare

    def pin(self,h):
        return {'question_id':h._state.current_question['question_id'],
                'attempt_id':h._state.current_question['attempt_id'],
                'course_id':h._state.study_course_id,'session_id':h._state.study_session_id}

    async def test_exact_pin_grades_original_answer_once_and_persists_original_identity(self):
        h=await self.prepare();pin=self.pin(h)
        answer='我先回答刚才那道题，箭头从右向左，请判断对不对，最多两句话说明原因。'
        result=await h.study_answer_tool(answer=answer,_expected_question=pin)
        self.assertEqual(result['verdict'],'wrong')
        self.assertTrue(h._state.current_question['attempt_evaluated'])
        args=h._agent.answer_evaluate.call_args.kwargs
        self.assertEqual(args['answer'],answer)
        rows=self.store.list_interactions(10,session_id=h._study_session_id)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['metadata']['question_id'],pin['question_id'])
        self.assertEqual(rows[0]['metadata']['attempt_id'],pin['attempt_id'])
        await h.study_answer_tool(answer=answer,_expected_question=pin)
        self.assertEqual(h._agent.answer_evaluate.await_count,1)
        self.assertEqual(len(self.store.list_interactions(10,session_id=h._study_session_id)),1)

    async def test_changed_identity_or_incomplete_snapshot_never_grades_latest_question(self):
        for field in ('question_id','attempt_id','course_id','session_id','missing','extra','empty','non_object'):
            with self.subTest(field=field):
                h=await self.prepare();pin=self.pin(h)
                if field in pin:pin[field]='previous-'+pin[field]
                elif field=='missing':pin.pop('attempt_id')
                elif field=='extra':pin['unknown']='untrusted'
                elif field=='empty':pin['question_id']=''
                else:pin='not a snapshot'
                before=deepcopy(h._state.current_question)
                result=await h.study_answer_tool(answer='REZ',_expected_question=pin)
                self.assertFalse(result['ok']);self.assertEqual(result['code'],'QUESTION_CONTEXT_CHANGED')
                h._agent.answer_evaluate.assert_not_awaited()
                self.assertEqual(h._state.current_question,before)
                self.assertEqual(self.store.list_interactions(10,session_id=h._study_session_id),[])

    async def test_snapshot_then_waiting_for_wrapper_lock_cannot_adopt_new_question(self):
        h=await self.prepare();pin=self.pin(h)
        original=h._study_native_material_snapshot
        async def replaced(**kwargs):
            result=await original(**kwargs)
            h._state.current_question.update(question_id='new-question',attempt_id='new-attempt',answer='NUD')
            return result
        h._study_native_material_snapshot=replaced
        result=await h.study_answer_tool(answer='REZ',_expected_question=pin)
        self.assertEqual(result['code'],'QUESTION_CONTEXT_CHANGED')
        h._agent.answer_evaluate.assert_not_awaited()
        self.assertFalse(h._state.current_question.get('attempt_evaluated',False))

    async def test_actual_sdk_callback_preserves_private_pin_and_rejects_it_before_grading(self):
        import neko_material_control_sdk_audit as sdk
        h=await self.prepare();pin=self.pin(h)
        legacy=sdk.PluginContext(plugin_id='study_companion',config_path=Path(self.temporary.name)/'plugin.toml',
                                logger=sdk.QuietLogger(),status_queue=queue.Queue(),message_queue=queue.Queue())
        registry=sdk.NekoPluginBase.__new__(sdk.NekoPluginBase)
        registry._host_ctx,registry.ctx,registry.logger=legacy,sdk.SdkContext(legacy),sdk.QuietLogger()
        registry._routers,registry._dynamic_entries,registry._llm_tools=[],{},{}
        tree=ast.parse((grade.SOURCE/'study_avatar_tools.py').read_text(encoding='utf-8'))
        method=next(node for node in ast.walk(tree) if isinstance(node,ast.AsyncFunctionDef) and node.name=='study_answer_tool')
        schema=ast.literal_eval(next(keyword.value for keyword in method.decorator_list[0].keywords if keyword.arg=='parameters'))
        self.assertNotIn('_expected_question',schema['properties'])
        registry._register_llm_tool_internal(sdk.LlmToolMeta(name='study_answer',description='grade identity check',parameters=schema),h.study_answer_tool)
        serialize=sdk.host_result_serializer()
        observed=[]
        class Trigger:
            async def trigger(inner,entry_id,arguments,timeout):
                entry=registry.collect_entries()[entry_id]
                kwargs=sdk.prepare_entry_kwargs(plugin_id='study_companion',entry_id=entry_id,
                    handler=entry.handler,meta=entry.meta,args=arguments)
                observed.append(kwargs.get('_expected_question'))
                packet=serialize(await entry.handler(**kwargs))
                return packet['data']
        class State:
            plugin_hosts={'study_companion':Trigger()}
            def acquire_plugin_hosts_read_lock(inner):return contextlib.nullcontext()
        callback=sdk.callback_function(State())
        async def run(expected):
            body=json.loads(json.dumps({'arguments':{'answer':'REZ','_expected_question':expected},'call_id':'local-sdk-audit'}))
            return await callback('study_companion','study_answer',body)
        wrong={**pin,'attempt_id':'old-attempt'}
        refused=await run(wrong)
        self.assertEqual(refused['output']['code'],'QUESTION_CONTEXT_CHANGED')
        self.assertEqual(observed[-1],wrong)
        h._agent.answer_evaluate.assert_not_awaited()
        accepted=await run(pin)
        self.assertEqual(accepted['output']['verdict'],'wrong')
        self.assertEqual(observed[-1],pin)
        self.assertTrue(h._state.current_question['attempt_evaluated'])
        self.assertEqual(len(self.store.list_interactions(10,session_id=h._study_session_id)),1)

if __name__=='__main__':unittest.main(verbosity=2)
