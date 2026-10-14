"""Actual avatar wrapper and existing SQLite preferences; fake teaching backend only."""
import ast
import asyncio
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import tempfile
from typing import Any
import unittest
from urllib.parse import quote
import httpx
from test_neko_product_course_memory import ProductHarness, Store, SOURCE, models
from test_neko_learning_preferences import prefs

tree=ast.parse((SOURCE/'study_avatar_tools.py').read_text(encoding='utf-8'))
nodes=[n for n in tree.body if isinstance(n,(ast.Assign,ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))]
for n in ast.walk(ast.Module(body=nodes,type_ignores=[])):
    if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):n.decorator_list=[]
scope={'asyncio':asyncio,'hashlib':hashlib,'json':json,'logging':logging,'os':os,'re':re,'Any':Any,'httpx':httpx,'quote':quote,
       'public_current_question_payload':models.public_current_question_payload,
       '__name__':'product_study.avatar_language_test','__package__':'product_study'}
exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),str(SOURCE/'study_avatar_tools.py'),'exec'),scope)

class Harness(scope['_StudyAvatarToolsMixin'],ProductHarness):
    def __init__(self,store):
        ProductHarness.__init__(self,store);self.calls=[];self.fail=False
        self._cfg.language='zh-CN'
    async def study_explain_text(self,*,text,**kwargs):
        self.calls.append((self._cfg.language,text))
        if self.fail:raise RuntimeError('controlled model failure')
        return {'reply':'First sentence. Second sentence.' if self._cfg.language=='en-US' else '第一句。第二句。'}

class ExplanationLanguage(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.store=Store(Path(self.temp.name)/'study.db',Path(self.temp.name)/'unused.json',logging.getLogger('language-test'))
        self.store.open();prefs.update_preferences(self.store,{'language':'zh-CN'},remember=True)
        self.h=Harness(self.store)
    def tearDown(self):self.store.close();self.temp.cleanup()
    async def test_explicit_language_survives_question_rewording_and_leaves_saved_preference(self):
        before=self.store.get_raw(prefs.PREFERENCES_KEY)
        reply=await self.h.study_explain_tool(question='Explain the route; do not save English as a preference; no quiz.',language='en-US')
        self.assertEqual(self.h.calls[0][0],'en-US')
        self.assertIn('Teach this in English',self.h.calls[0][1])
        self.assertEqual(reply['reply'],'First sentence. Second sentence.')
        self.assertEqual(self.h._cfg.language,'zh-CN')
        self.assertEqual(self.store.get_raw(prefs.PREFERENCES_KEY),before)
    async def test_counted_chinese_request_and_negation_are_not_confused_with_language_noun(self):
        for question,wanted in [('这次只用两句英文回答，不要出题。','en-US'),
                                ('不要用英文，用两句中文回答。','zh-CN'),
                                ('Do not answer in English. Use Chinese.','zh-CN'),
                                ('Explain the route; do not save English as a preference.','zh-CN')]:
            with self.subTest(question=question):
                await self.h.study_explain_tool(question=question)
                self.assertEqual(self.h.calls[-1][0],wanted)
                self.assertEqual(self.h._cfg.language,'zh-CN')
        self.assertEqual(prefs.load_preferences(self.store)['language'],'zh-CN')
    async def test_failure_restores_language_and_invalid_override_never_calls_backend(self):
        self.h.fail=True
        with self.assertRaisesRegex(RuntimeError,'controlled'):
            await self.h.study_explain_tool(question='route?',language='en-US')
        self.assertEqual(self.h._cfg.language,'zh-CN')
        before=len(self.h.calls)
        invalid=await self.h.study_explain_tool(language='not-supported')
        self.assertFalse(invalid['ok']);self.assertEqual(len(self.h.calls),before)
        self.assertEqual(prefs.load_preferences(self.store)['language'],'zh-CN')

    async def test_turn_modifiers_do_not_discard_supplied_relation_notes_for_missing_picture(self):
        material='Relation notes: WEX points to NUD; NUD points to REZ.'
        self.h._cfg.llm_vision_enabled=True
        self.h._state.last_vision_image_base64=''
        for question,wanted in [
            ('这一次只用两句中文解释从NUD出发的箭头，不要保存偏好。','zh-CN'),
            ('这次用两句英文解释NUD的箭头，不要出题。','en-US'),
            ('This time explain the arrow leaving NUD in English.','en-US')]:
            with self.subTest(question=question):
                result=await self.h.study_explain_tool(question=question,text=material)
                self.assertFalse(result.get('degraded',False))
                self.assertIn(material,self.h.calls[-1][1])
                self.assertEqual(self.h.calls[-1][0],wanted)
                self.assertEqual(self.h._cfg.language,'zh-CN')
        calls=len(self.h.calls)
        for question in ('请核对这条箭头。','Explain this arrow.','请核对当前图片。'):
            with self.subTest(question=question):
                result=await self.h.study_explain_tool(question=question,text=material)
                self.assertTrue(result['degraded'])
                self.assertEqual(result['diagnostic'],'visual_context_missing')
                self.assertEqual(len(self.h.calls),calls)

    async def test_no_persistence_clause_keeps_temporary_chinese_on_remembered_english_course(self):
        self.h._state.study_course_id='course-A'
        self.h._state.teaching_language_by_course={'course-A':'en-US'}
        self.h._cfg.language='en-US'
        before=self.store.get_raw(prefs.PREFERENCES_KEY)
        for question in (
            '这一次只用两句中文解释从NUD出发的箭头，不要出题，不要把这次中文要求保存成长期偏好。',
            'Use Chinese this time; do not save this as a permanent preference.',
            "Use Chinese; don't remember this as a preference going forward."):
            with self.subTest(question=question):
                await self.h.study_explain_tool(question=question,text='NUD points to REZ.')
                self.assertEqual(self.h.calls[-1][0],'zh-CN')
                self.assertEqual(self.h._cfg.language,'en-US')
                self.assertEqual(self.h._state.teaching_language_by_course,{'course-A':'en-US'})
                self.assertEqual(self.store.get_raw(prefs.PREFERENCES_KEY),before)
        await self.h.study_explain_tool(question='Explain the next connection.',text='WEX points to NUD.')
        self.assertEqual(self.h.calls[-1][0],'en-US')
        request=scope['_turn_language_request']
        for question in ('以后这门课用中文','Use Chinese always.','这次用中文，以后一直用英文。',
                         '不要用中文解释。','Do not use Chinese.',
                         '这次用中文；不要忘记以后用英文并保存为长期偏好。',
                         '这次用中文；不要忘了以后一直用英文并保存成长期偏好。',
                         '这次用中文；别忘了以后用英文并记为长期设置。'):
            self.assertEqual(request(question),'',question)

    async def test_overlapping_one_turn_calls_do_not_restore_another_temporary_language(self):
        entered=asyncio.Event();release=asyncio.Event();calls=[]
        async def slow_backend(*,text,**kwargs):
            calls.append(self.h._cfg.language)
            if len(calls)==1:
                entered.set();await release.wait()
            return {'reply':'First sentence. Second sentence.'}
        self.h.study_explain_text=slow_backend
        first=asyncio.create_task(self.h.study_explain_tool(question='first',language='en-US'))
        await entered.wait()
        second=asyncio.create_task(self.h.study_explain_tool(question='second',language='en-US'))
        await asyncio.sleep(.02)
        self.assertEqual(calls,['en-US'])
        release.set();await asyncio.gather(first,second)
        self.assertEqual(calls,['en-US','en-US'])
        self.assertEqual(self.h._cfg.language,'zh-CN')
        await self.h.study_explain_tool(question='next, no language switch')
        self.assertEqual(calls[-1],'zh-CN')
        self.assertEqual(prefs.load_preferences(self.store)['language'],'zh-CN')

if __name__=='__main__':unittest.main(verbosity=2)
