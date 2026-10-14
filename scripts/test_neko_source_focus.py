"""Actual scorer and Focus-off gates; no SDK/app/model/device imports."""
import ast
import asyncio
import hashlib
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

import neko_source_focus_patch as candidate

ROOT=Path(__file__).resolve().parents[1]
HOST=ROOT/'benchmarks/raw/neko-product-host'
settings={}
exec(compile((HOST/'config/focus_settings.py').read_text(encoding='utf-8'),'actual_focus_settings.py','exec'),settings)
config=SimpleNamespace(**{k:v for k,v in settings.items() if k.startswith('FOCUS_')})
source=(HOST/candidate.RELATIVE).read_text(encoding='utf-8')
baseline=source
if candidate.MARKER in baseline:
    for old,new in reversed(candidate.EDITS):baseline=baseline.replace(new,old,1)


def load_scorer(text,name):
    tree=ast.parse(text)
    tree.body=[n for n in tree.body if not(isinstance(n,ast.Import) and any(a.name=='config' for a in n.names))
               and not(isinstance(n,ast.ImportFrom) and n.module=='config.prompts.prompts_focus')]
    module=ModuleType(name);sys.modules[name]=module
    module.__dict__.update(config=config,scan_vulnerability_keywords=lambda text:0)
    exec(compile(tree,'actual_focus_scorer.py','exec'),module.__dict__)
    return module


original=load_scorer(baseline,'source_focus_baseline')
updated=load_scorer(candidate.patch_scorer(baseline),'source_focus_candidate')


class SourceSignal(unittest.TestCase):
    def test_explicit_chinese_source_reasoning_has_immediate_question_signal(self):
        for text in ('请解释源码里的条件和改动影响。','核对源代码：交换两个值会通过校验吗？',
                     '为什么 weather_service.dart 改名影响服务端？','解释 server/routes/weather.js 的调用流程。'):
            with self.subTest(text=text):
                result=updated.FocusScorer('fixture').score(user_text=text)
                self.assertEqual(result.signals['question'],1.0)
                self.assertGreaterEqual(result.score,config.FOCUS_CHARGE_ENTER)
                self.assertIsNone(original.FocusScorer('fixture').score(user_text=text).signals['question'])

    def test_explicit_english_source_reasoning_is_case_insensitive(self):
        for text in ('Explain this source code.','Trace the calls in helper.py.',
                     'What is the impact if we rename this code variable?','Validate the condition in MAIN.TS.'):
            with self.subTest(text=text):
                self.assertEqual(updated.FocusScorer('fixture').score(user_text=text).signals['question'],1.0)

    def test_casual_file_mentions_and_read_only_requests_do_not_force_reasoning(self):
        for text in ('打开 main.py','今天写代码好累','code is a word','解释这张架构图','你好',
                     '只展示源码，不要解释。','Just show the source code, do not explain.',
                     'No reasoning; explain this code.','不要思考，解释源码。','why is 3 < 4?'):
            with self.subTest(text=text):
                self.assertFalse(updated._source_reasoning_request(text))

    def test_existing_question_reading_and_other_scores_are_preserved(self):
        for text in ('谢谢','最近怎么样','why is 3 < 4?','show main.py'):
            reading=SimpleNamespace(complexity=.85,valence=0.,arousal=.4)
            before=original.FocusScorer('fixture').score(user_text=text,emotion_reading=reading)
            after=updated.FocusScorer('fixture').score(user_text=text,emotion_reading=reading)
            self.assertEqual(before.score,after.score);self.assertEqual(before.signals,after.signals)

    def test_current_request_does_not_need_to_wait_for_stale_complexity(self):
        reading=SimpleNamespace(complexity=.3,valence=0.,arousal=.4)
        result=updated.FocusScorer('fixture').score(user_text='解释源码校验条件。',emotion_reading=reading)
        self.assertEqual(result.signals['question'],1.0)

    def test_replay_hash_idempotence_and_unknown_source_refusal(self):
        self.assertEqual(hashlib.sha256(baseline.encode()).hexdigest(),candidate.BASE)
        patched=candidate.patch_scorer(baseline)
        self.assertEqual(candidate.patch_scorer(patched),patched)
        with self.assertRaises(ValueError):candidate.patch_scorer('unexpected source')


tree=ast.parse((HOST/'main_logic/core/focus.py').read_text(encoding='utf-8'))
method=next(n for n in ast.walk(tree) if isinstance(n,ast.AsyncFunctionDef) and n.name=='_focus_inline_decision')
facade=SimpleNamespace(aload_global_conversation_settings=AsyncMock())
gate_scope={'_core_facade':facade,'logger':Mock()}
exec(compile(ast.fix_missing_locations(ast.Module(body=[method],type_ignores=[])),'actual_focus_gate.py','exec'),gate_scope)


class OffGates(unittest.IsolatedAsyncioTestCase):
    async def check_gate(self,global_enabled,user_enabled):
        module=ModuleType('config');module.FOCUS_MODE_ENABLED=global_enabled
        facade.aload_global_conversation_settings=AsyncMock(return_value={'focusCognitionEnabled':user_enabled})
        target=SimpleNamespace(_reconcile_focus_indicator=AsyncMock(),state=SimpleNamespace(
            update_focus=AsyncMock(),clear_focus=AsyncMock()),_focus_scorer=Mock())
        with patch.dict(sys.modules,{'config':module}):
            answer=await gate_scope['_focus_inline_decision'](target,'解释源码的条件和改动影响。')
        self.assertFalse(answer);target._focus_scorer.score.assert_not_called()
        return target

    async def test_global_off_prevents_scoring_and_clears_charge(self):
        target=await self.check_gate(False,True)
        target.state.update_focus.assert_awaited_once_with(0.0)

    async def test_user_off_prevents_scoring_and_hard_clears_charge(self):
        target=await self.check_gate(True,False)
        target.state.clear_focus.assert_awaited_once_with()


if __name__=='__main__':unittest.main(verbosity=2)
