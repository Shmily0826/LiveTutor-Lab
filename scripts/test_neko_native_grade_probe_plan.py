"""Actual observer preflight, stopping before any port/host/device operation."""
import __future__
import ast
import json
import math
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
import wave
from unittest.mock import Mock


class Planned(Exception):pass


class GradeProbePlan(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='neko-grade-plan-')
        self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.store=self.root/'benchmarks/raw/neko-daily-continuous-text-fixture'
        self.store.mkdir(parents=True)
        self.provenance=self.store/'task-provenance.json'
        self.provenance.write_text(json.dumps({'fresh':True}),encoding='utf-8')
        self.wav=self.root/'fixed.wav'
        with wave.open(str(self.wav),'wb') as wav:
            wav.setparams((1,2,48000,0,'NONE','not compressed'));wav.writeframes(b'\0\0'*480)
        self.host=SimpleNamespace(require_task_speaker_output_allowed=Mock(),require_task_audio_allowed=Mock(),
            MAIN_PORT=48911,PLUGIN_PORT=48916)
        self.ports=Mock(side_effect=Planned('preflight complete; no port opened'))
        tree=ast.parse((Path(__file__).parent/'neko_daily_voice_probe.py').read_text(encoding='utf-8'))
        node=next(node for node in tree.body if isinstance(node,ast.AsyncFunctionDef) and node.name=='main')
        namespace={'host':self.host,'ROOT':self.root,'json':json,'os':os,'wave':wave,'math':math,
            'sockets':SimpleNamespace(socket=self.ports)}
        duration=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='teaching_capture_seconds')
        exec(compile(ast.Module(body=[duration],type_ignores=[]),'actual duration preflight','exec'),namespace)
        exec(compile(ast.Module(body=[node],type_ignores=[]),'actual voice probe preflight','exec',
            flags=__future__.annotations.compiler_flag),namespace)
        self.main=namespace['main']
        predicate=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='grade_quiz_prepared')
        exec(compile(ast.Module(body=[predicate],type_ignores=[]),'actual quiz receipt','exec'),namespace)
        self.quiz_prepared=namespace['grade_quiz_prepared']
        predicate=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='grade_baseline_matches')
        exec(compile(ast.Module(body=[predicate],type_ignores=[]),'actual baseline receipt','exec'),namespace)
        self.baseline_matches=namespace['grade_baseline_matches']
    def args(self,**changes):
        values=dict(output_only=True,grade_current=True,prepare_grade_quiz=False,
            output=self.root/'result.json',teaching_text_chain=False,teaching_wav=None,
            wav=self.wav,verify_picture_state=True,followup_wav=None,prepare_picture=False,
            point_code=False,manual_turn_probe=False,replace_picture_on_playback=None,
            store=self.store.name)
        values.update(changes);return SimpleNamespace(**values)
    async def reject(self,**changes):
        with self.assertRaises((ValueError,FileNotFoundError)):
            await self.main(self.args(**changes))
        self.ports.assert_not_called()
    async def test_grade_requires_output_only_one_wav_and_existing_material(self):
        for change in ({'output_only':False},{'wav':None},{'verify_picture_state':False},
                {'followup_wav':self.wav},{'prepare_picture':True},{'point_code':True},
                {'manual_turn_probe':True},{'teaching_wav':[self.wav]*3}):
            with self.subTest(change=change):await self.reject(**change)
    async def test_quiz_preparation_cannot_run_outside_grade_scene(self):
        await self.reject(grade_current=False,prepare_grade_quiz=True)
    async def test_original_daily_and_unproven_task_are_refused(self):
        await self.reject(store='neko-daily-companion')
        self.provenance.write_text(json.dumps({'fresh':False}),encoding='utf-8')
        await self.reject()
    async def test_missing_provenance_cannot_start_host(self):
        self.provenance.unlink();await self.reject()
    async def test_valid_fixed_task_scene_reaches_port_preflight_only(self):
        with self.assertRaises(Planned):await self.main(self.args(prepare_grade_quiz=True))
        self.host.require_task_speaker_output_allowed.assert_called_once()
        self.ports.assert_called_once()

    async def test_continuous_scene_requires_owned_output_only_three_wavs_without_preparation(self):
        changes=dict(grade_current=False,grade_chain=True,teaching_wav=[self.wav]*3,wav=None)
        for invalid in ({'output_only':False},{'grade_current':True},{'teaching_wav':None},
                {'verify_picture_state':False},{'prepare_grade_quiz':True},{'grade_correction':True},
                {'followup_wav':self.wav},{'store':'neko-daily-companion'}):
            with self.subTest(invalid=invalid):await self.reject(**{**changes,**invalid})
        with self.assertRaises(Planned):await self.main(self.args(**changes))
        self.ports.reset_mock()
        with self.assertRaises(Planned):
            await self.main(self.args(**{**changes,'prepare_picture':True,'store':'neko-daily-speech-acceptance-fresh'}))
        self.assertFalse((self.root/'benchmarks/raw/neko-daily-speech-acceptance-fresh').exists())

    async def test_actual_rich_quiz_receipt_does_not_require_nonexistent_ok_flag(self):
        value={'is_error':False,'output':{'tool':'study_quiz','degraded':False,
            'question':'Where does the arrow start?','question_id':'q','attempt_id':'a'}}
        self.assertTrue(self.quiz_prepared(value))
        for change in ({'question_id':''},{'attempt_id':None},{'degraded':True},{'ok':False},{'tool':'study_explain'}):
            with self.subTest(change=change):
                self.assertFalse(self.quiz_prepared({'is_error':False,'output':{**value['output'],**change}}))
        self.assertFalse(self.quiz_prepared({'is_error':True,'output':value['output']}))

    async def test_correction_cannot_replace_question_or_start_outside_grade_scene(self):
        await self.reject(grade_current=False,grade_correction=True)
        await self.reject(prepare_grade_quiz=True,grade_correction=True)
        with self.assertRaises(Planned):await self.main(self.args(grade_correction=True))

    async def test_baseline_and_pin_agree_before_native_for_both_modes(self):
        pin=dict(course_id='course',session_id='session',question_id='q',attempt_id='a',attempt_evaluated=False)
        baseline={'ok':True,'course_id':'course','session_id':'session',
            'question':{k:pin[k] for k in ('question_id','attempt_id','attempt_evaluated')},'last_answer_evaluation':{}}
        self.assertTrue(self.baseline_matches(baseline,pin))
        self.assertFalse(self.baseline_matches(baseline,pin,correction=True))
        for change in ({'ok':False},{'course_id':'other'},{'session_id':'other'}):
            self.assertFalse(self.baseline_matches({**baseline,**change},pin))
        self.assertFalse(self.baseline_matches(baseline,{**pin,'attempt_id':'other'}))
        pin['attempt_evaluated']=True;baseline['question']['attempt_evaluated']=True
        for verdict in ('wrong','partial'):
            baseline['last_answer_evaluation']={'verdict':verdict}
            self.assertTrue(self.baseline_matches(baseline,pin,correction=True))
            self.assertFalse(self.baseline_matches(baseline,pin))
        baseline['last_answer_evaluation']={'verdict':'correct'}
        self.assertFalse(self.baseline_matches(baseline,pin,correction=True))


if __name__=='__main__':unittest.main(verbosity=2)
