"""Actual observer preflight, stopping before any port/host/device operation."""
import __future__
import ast
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
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
        self.wav=self.root/'fixed.wav';self.wav.write_bytes(b'not opened during preflight')
        self.host=SimpleNamespace(require_task_speaker_output_allowed=Mock(),require_task_audio_allowed=Mock(),
            MAIN_PORT=48911,PLUGIN_PORT=48916)
        self.ports=Mock(side_effect=Planned('preflight complete; no port opened'))
        tree=ast.parse((Path(__file__).parent/'neko_daily_voice_probe.py').read_text(encoding='utf-8'))
        node=next(node for node in tree.body if isinstance(node,ast.AsyncFunctionDef) and node.name=='main')
        namespace={'host':self.host,'ROOT':self.root,'json':json,'os':os,'sockets':SimpleNamespace(socket=self.ports)}
        exec(compile(ast.Module(body=[node],type_ignores=[]),'actual voice probe preflight','exec',
            flags=__future__.annotations.compiler_flag),namespace)
        self.main=namespace['main']
        predicate=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='grade_quiz_prepared')
        exec(compile(ast.Module(body=[predicate],type_ignores=[]),'actual quiz receipt','exec'),namespace)
        self.quiz_prepared=namespace['grade_quiz_prepared']
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

    async def test_actual_rich_quiz_receipt_does_not_require_nonexistent_ok_flag(self):
        value={'is_error':False,'output':{'tool':'study_quiz','degraded':False,
            'question':'Where does the arrow start?','question_id':'q','attempt_id':'a'}}
        self.assertTrue(self.quiz_prepared(value))
        for change in ({'question_id':''},{'attempt_id':None},{'degraded':True},{'ok':False},{'tool':'study_explain'}):
            with self.subTest(change=change):
                self.assertFalse(self.quiz_prepared({'is_error':False,'output':{**value['output'],**change}}))
        self.assertFalse(self.quiz_prepared({'is_error':True,'output':value['output']}))


if __name__=='__main__':unittest.main(verbosity=2)
