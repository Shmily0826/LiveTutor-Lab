"""Actual agent/entry methods, fresh SQLite; no host or audio devices."""
import ast
import asyncio
import json
import re
import time
from pathlib import Path
from types import SimpleNamespace
from contextvars import ContextVar
from typing import Any
import unittest
from unittest.mock import AsyncMock
from test_neko_product_course_memory import SOURCE, models, prompts

path = SOURCE / 'tutor_llm_agent_concept_explain.py'
tree = ast.parse(path.read_text(encoding='utf-8'))
nodes = [ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0)] + [
    n for n in tree.body if isinstance(n, (ast.Assign, ast.FunctionDef, ast.AsyncFunctionDef))]
scope = dict(time=time, asyncio=asyncio, json=json, re=re, ast=ast, Any=Any,
    TutorReply=models.TutorReply, utc_now_iso=models.utc_now_iso,
    MODE_CONCEPT_EXPLAIN='concept_explain', MODE_COMPANION='companion', MODE_TEACHING='teaching',
    normalize_mode=lambda value:value, build_transition_phrase=lambda *args, **kwargs:'',
    build_concept_explain_messages=prompts.build_concept_explain_messages,
    SdkError=RuntimeError, diagnostic_code_for_exception=lambda exc:'controlled_error')
scope['STUDY_FALLBACK_EXPLANATION_DEFAULT']='Material changed.'
exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])), str(path), 'exec'), scope)
spans = scope['english_prose_spans']
repair = scope['repair_english_prose']

def result(text, truncated=False):
    return SimpleNamespace(text=text, output_limit_reached=truncated)

class EnglishReplyGuard(unittest.IsolatedAsyncioTestCase):
    async def translate(self, response, draft='The label is "天气未命中 / 百科 HTTPS"; `fetchOpenMeteo(12)` stays the same.'):
        agent=SimpleNamespace(_call_model_result=AsyncMock(return_value=result(response)))
        runtime=object();image={'type':'image_url', 'image_url':{'url':'data:image/png;base64,original'}}
        output=await repair(agent,draft,'',messages=[{'content':[image]}],runtime=runtime,
                            deadline=time.monotonic()+10)
        return output, agent, runtime, image

    async def test_only_spans_change_and_primary_vision_runtime_and_image_are_reused(self):
        out,agent,runtime,image=await self.translate('["weather cache miss", "encyclopedia"]')
        self.assertEqual(out,'The label is "weather cache miss / encyclopedia HTTPS"; `fetchOpenMeteo(12)` stays the same.')
        call=agent._call_model_result.call_args
        self.assertIs(call.kwargs['runtime'],runtime)
        self.assertIs(call.args[0][-1]['content'][-1],image)
        agent._call_model_result.assert_awaited_once()

    async def test_invalid_json_han_count_digits_empty_and_reversed_miss_are_rejected_once(self):
        for text in ['not JSON','{}','["weather cache miss"]','["天气未命中", "encyclopedia"]',
                     '["weather cache hit", "encyclopedia"]','["weather miss 9", "encyclopedia"]',
                     '["", "encyclopedia"]','["weather miss", "`new_code`"]',
                     '["weather cache hit, not a miss", "encyclopedia"]',
                     '["weather cache hit, no retry", "encyclopedia"]',
                     '["not a weather cache miss", "encyclopedia"]']:
            with self.subTest(text=text):
                out,agent,_,_=await self.translate(text)
                self.assertIsNone(out);agent._call_model_result.assert_awaited_once()

    async def test_literal_unicode_identifier_and_fenced_source_are_preserved_but_diagram_label_is_prose(self):
        draft='`天气计数` is 12. ```python\n天气计数 = 12\n``` The label is "天气未命中 / 百科 HTTPS".'
        found=spans(draft,'Read this source:\n```python\n天气计数 = 12\n```')
        self.assertEqual([s[2] for s in found],['天气未命中','百科'])
        out,_,_,_=await self.translate('["weather cache miss", "encyclopedia"]',draft)
        # Without fenced source evidence the inline Unicode token needs a third span.
        self.assertIsNone(out)
        agent=SimpleNamespace(_call_model_result=AsyncMock(return_value=result('["weather cache miss", "encyclopedia"]')))
        out=await repair(agent,draft,'```python\r\n天气计数 = 12\r\n```',messages=[],runtime=None,
                         deadline=time.monotonic()+10)
        self.assertIn('`天气计数` is 12.',out)
        self.assertIn('```python\n天气计数 = 12\n```',out)
        self.assertIn('"weather cache miss / encyclopedia HTTPS"',out)

    async def test_backtick_diagram_labels_and_text_fences_are_not_code_exemptions(self):
        self.assertEqual([s[2] for s in spans('Branch is `天气未命中`.','Explain label `天气未命中` in English.')],['天气未命中'])
        self.assertEqual([s[2] for s in spans('```text\n天气未命中\n```','Explain in English.')],['天气未命中'])
        self.assertEqual([s[2] for s in spans('```text\n天气未命中\n```','Translate this label:\n```text\n天气未命中\n```')],['天气未命中'])
        agent=SimpleNamespace(_call_model_result=AsyncMock())
        self.assertIsNone(await repair(agent,'```python\n天气未命中\n```','Explain in English.',
                                      messages=[],runtime=None,deadline=time.monotonic()+10))
        agent._call_model_result.assert_not_awaited()
        for broken in ('```python\n城市 = 1','Use `城市 + 1'):
            self.assertIsNone(await repair(agent,broken,'',messages=[],runtime=None,deadline=time.monotonic()+10))
        agent._call_model_result.assert_not_awaited()
        self.assertEqual(spans('Use fetch天气_count and 天气计数.',
                               '```python\nfetch天气_count = 天气计数\n```'),[])
        for language in ('json','yaml','xml','html','mermaid'):
            data=f'```{language}\n{{"城市":"北京"}}\n```'
            self.assertEqual(spans(data,data),[])
            self.assertEqual(await repair(agent,data,data,messages=[],runtime=None,deadline=0),data)
        unknown='```unlisted-data\n{"城市":"北京"}\n```'
        self.assertIsNone(await repair(agent,unknown,unknown,messages=[],runtime=None,deadline=time.monotonic()+10))
        agent._call_model_result.assert_not_awaited()
        for inline in ('`{"城市":"北京"}`','`fetch("北京")`','`city["城市"]`','`config.城市`'):
            self.assertEqual(spans(inline,inline),[])
            self.assertEqual(await repair(agent,inline,inline,messages=[],runtime=None,deadline=0),inline)
        for inline in ('`x = "北京"`','`城市 + 1`','`城市`','`天气未命中`'):
            self.assertIsNone(await repair(agent,inline,inline,messages=[],runtime=None,
                                          deadline=time.monotonic()+10))
        agent._call_model_result.assert_not_awaited()

    async def test_deadline_and_size_limit_do_not_call_provider(self):
        agent=SimpleNamespace(_call_model_result=AsyncMock())
        for draft,deadline in [('天气未命中',time.monotonic()+.01),('天气'*700,time.monotonic()+10),
                               ('汉 '*13,time.monotonic()+10)]:
            self.assertIsNone(await repair(agent,draft,'',messages=[],runtime=object(),deadline=deadline))
        agent._call_model_result.assert_not_awaited()

    async def test_clean_prose_needs_no_call_and_cancellation_propagates(self):
        agent=SimpleNamespace(_call_model_result=AsyncMock(side_effect=asyncio.CancelledError))
        self.assertEqual(await repair(agent,'Cache miss.','',messages=[],runtime=None,deadline=0),'Cache miss.')
        agent._call_model_result.assert_not_awaited()
        with self.assertRaises(asyncio.CancelledError):
            await repair(agent,'天气未命中','',messages=[],runtime=None,deadline=time.monotonic()+10)

    def agent(self, responses):
        runtime=object()
        return SimpleNamespace(_config=SimpleNamespace(language='en-US'),
            _current_model_runtime=AsyncMock(return_value=runtime),
            _new_operation_deadline=lambda *args:time.monotonic()+15,
            _attach_vision_image=lambda messages,image:messages+[{'role':'user','content':[
                {'type':'image_url','image_url':{'url':image}}]}],
            _call_model_result=AsyncMock(side_effect=responses),
            _logger=SimpleNamespace(warning=lambda *args:None), runtime=runtime)

    async def test_actual_agent_uses_same_runtime_once_then_returns_corrected_reply(self):
        agent=self.agent([result('Actually it is a miss: "天气未命中 / 百科 HTTPS".'),
                          result('["weather cache miss", "encyclopedia"]')])
        output=await scope['concept_explain'](agent,'Explain this image in English.',
            context={'vision_image_base64':'original', '_reply_material_is_current':AsyncMock(return_value=True)})
        self.assertFalse(output.degraded);self.assertNotIn('天气',output.reply)
        self.assertTrue(output.payload['reply_language_repair_attempted'])
        self.assertEqual(agent._call_model_result.await_count,2)
        for call in agent._call_model_result.call_args_list:
            self.assertIs(call.kwargs['runtime'],agent.runtime)

    async def test_actual_agent_invalid_repair_is_honest_degraded_english(self):
        agent=self.agent([result('天气未命中'),result('["weather cache hit"]')])
        output=await scope['concept_explain'](agent,'Explain in English.')
        self.assertTrue(output.degraded);self.assertEqual(output.diagnostic,'reply_language_unresolved')
        self.assertTrue(output.reply.isascii());self.assertEqual(agent._call_model_result.await_count,2)

    async def test_material_change_during_primary_skips_the_optional_repair(self):
        agent=self.agent([result('天气未命中')]);agent._localize_reply=lambda *args,**kwargs:'Material changed.'
        output=await scope['concept_explain'](agent,'Explain in English.',
            context={'_reply_material_is_current':AsyncMock(return_value=False)})
        self.assertTrue(output.degraded);agent._call_model_result.assert_awaited_once()

    async def test_primary_truncation_does_not_become_a_complete_explanation(self):
        agent=self.agent([result('天气未命中',True),result('["weather cache miss"]')])
        output=await scope['concept_explain'](agent,'Explain in English.')
        self.assertEqual(output.diagnostic,'output_truncated')
        self.assertTrue(output.degraded);agent._call_model_result.assert_awaited_once()

    async def test_actual_runtime_getter_preserves_bound_snapshot_even_if_group_mismatch(self):
        runtime_tree=ast.parse((SOURCE/'tutor_llm_agent.py').read_text(encoding='utf-8'))
        method=next(n for n in ast.walk(runtime_tree) if isinstance(n,ast.AsyncFunctionDef) and n.name=='_current_model_runtime')
        binding=ContextVar('test_pinned_runtime',default=None)
        namespace={'_bound_model_runtime':binding}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[method],type_ignores=[])),'actual_runtime_getter','exec'),namespace)
        host=SimpleNamespace(resolve_model_runtime=AsyncMock(return_value='configured'))
        getter=namespace['_current_model_runtime']
        pinned=SimpleNamespace(model_group='vision');token=binding.set(pinned)
        try:
            self.assertIs(await getter(host,'vision'),pinned)
            self.assertIs(await getter(host,'agent'),pinned)
            host.resolve_model_runtime.assert_not_awaited()
        finally:binding.reset(token)
        self.assertEqual(await getter(host,'agent'),'configured')
        host.resolve_model_runtime.assert_awaited_once_with('agent')

    async def test_final_entry_rejects_han_before_history_and_keeps_saved_language(self):
        from test_neko_native_material_guard import NativeMaterialGuard
        fixture=NativeMaterialGuard('test_native_unchanged_snapshot_reaches_model_and_records_its_identity')
        fixture.setUp()
        try:
            host=await fixture.prepare()
            async def unguarded_model(source,**kwargs):
                self.assertTrue(callable(kwargs['context']['_reply_material_is_current']))
                return models.TutorReply(operation='concept_explain',input_text=source,reply='天气未命中')
            host._agent.concept_explain=AsyncMock(side_effect=unguarded_model)
            before=fixture.store.list_interactions(30)
            output=await host.study_explain_tool(question='Explain this diagram',language='en-US')
            self.assertEqual(output['code'],'reply_language_unresolved')
            self.assertEqual(fixture.store.list_interactions(30),before)
            self.assertEqual(host._cfg.language,'zh-CN')
        finally:
            fixture.tearDown()

if __name__=='__main__':unittest.main(verbosity=2)
