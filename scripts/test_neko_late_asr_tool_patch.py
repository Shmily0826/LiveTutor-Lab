"""Actual tool lifecycle plus candidate ordering, with no host/provider/input."""
import ast
import asyncio
import sys
import time
import types
import unittest
from pathlib import Path
import test_neko_late_asr_tools as original
from neko_late_asr_tool_patch import UPGRADES, MIGRATIONS, normalize_ordering_helpers

source=normalize_ordering_helpers(original.SOURCE.read_text(encoding='utf-8'))
for relative,before,after in MIGRATIONS:
    if relative.endswith('_tools.py') and after not in source and source.count(before)==1:
        source=source.replace(before,after,1)
for before,after in UPGRADES['main_logic/omni_realtime_client/_tools.py']:
    if after in source: continue
    if source.count(before)>1: raise RuntimeError('ambiguous tool source for candidate test')
    if before in source:source=source.replace(before,after,1)
if not all(after in source for _,after in UPGRADES['main_logic/omni_realtime_client/_tools.py']):
    raise RuntimeError('unknown tool source for candidate test')
candidate=types.ModuleType('candidate_late_asr_tools');candidate.__dict__.update(original.module.__dict__)
candidate.__name__='candidate_late_asr_tools';sys.modules[candidate.__name__]=candidate
nodes=[n for n in ast.parse(source).body if isinstance(n,(ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef,ast.Assign))]
exec(compile(ast.fix_missing_locations(ast.Module(body=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0),*nodes],type_ignores=[])),str(original.SOURCE),'exec'),candidate.__dict__)


class Harness(candidate._ToolingMixin, original.Harness):
    _read_host_turn_id=original.Harness._read_host_turn_id
    _execute_tool_call=original.Harness._execute_tool_call
    _send_tool_results_openai_realtime=original.Harness._send_tool_results_openai_realtime
    def __init__(self):
        original.Harness.__init__(self)
        self._realtime_protocol_capabilities=types.SimpleNamespace(route_key='lanlan_app_gemini')
        self._is_free_proxy=True;self._has_server_vad=False
        self._late_raw_connection_foreign_scope=0
        self._last_local_loud_time=time.time();self._LATE_ASR_TOOL_WAIT_SECONDS=.04
        self.abandoned=[]

    async def _close_unanswered_tool_calls(self,batch,owner):
        if self._tool_task_connection_is_current(owner):
            self.abandoned.extend(e.call.call_id for e in batch.entries)

    def completed(self):
        self._late_raw_expected_asr_advance=True
        try:self.note_user_turn_started()
        finally:self._late_raw_expected_asr_advance=False
        self._begin_raw_input_transcript()
        self._finish_raw_input_transcript()


class LateAsrPatch(unittest.IsolatedAsyncioTestCase):
    def call(self):return types.SimpleNamespace(name='study_point',arguments={},call_id='new-call')

    async def test_one_expected_asr_retires_old_work_then_dispatches_current_call(self):
        h=Harness();owner=h._capture_tool_task_owner(h.ws)
        older=asyncio.create_task(asyncio.sleep(10));h._track_tool_task(older)
        pending=h._start_raw_tool_call(self.call(),owner,response_id='unannounced')
        await asyncio.sleep(0)
        self.assertFalse(h.entered.is_set())
        h.completed();await pending;await h.entered.wait()
        self.assertTrue(older.cancelled());self.assertEqual(h._tool_scope_generation,2)
        h.release.set();await asyncio.gather(*tuple(h._tool_tasks),return_exceptions=True)
        self.assertEqual(len(h.outputs),1)

    async def test_foreign_scope_reconnect_replacement_or_two_completions_never_rebind(self):
        for mutation in ('foreign','connection','session','handoff','two_asr'):
            with self.subTest(mutation=mutation):
                h=Harness();owner=h._capture_tool_task_owner(h.ws)
                pending=h._start_raw_tool_call(self.call(),owner,response_id='unannounced')
                await asyncio.sleep(0)
                if mutation=='foreign':h.note_user_turn_started();h.completed()
                elif mutation=='connection':h._connection_generation+=1;h.completed()
                elif mutation=='session':h.ws=object();h.completed()
                elif mutation=='handoff':h._native_barge_in_pending=True;h.completed()
                else:h.completed();h.completed()
                await pending
                self.assertFalse(h.entered.is_set());self.assertEqual(h.outputs,[])
                self.assertEqual(h._late_raw_tool_pending,[])

    async def test_no_asr_timeout_keeps_exact_original_owner(self):
        h=Harness();owner=h._capture_tool_task_owner(h.ws)
        # Existing later-input fallback, outside the bounded first-ASR wait.
        h._late_raw_transcript_connection=h._connection_generation
        pending=h._start_raw_tool_call(self.call(),owner,response_id='unannounced')
        await pending;await h.entered.wait();h.release.set()
        await asyncio.gather(*tuple(h._tool_tasks),return_exceptions=True)
        self.assertEqual(h._tool_scope_generation,1);self.assertEqual(len(h.outputs),1)

    async def test_observed_asr_waits_for_slow_host_callback_without_promoting_other_turns(self):
        h=Harness();h._LATE_ASR_CALLBACK_WAIT_SECONDS=.12
        owner=h._capture_tool_task_owner(h.ws)
        pending=h._start_raw_tool_call(self.call(),owner,response_id='unannounced')
        await asyncio.sleep(0)
        h._late_raw_expected_asr_advance=True
        try:h.note_user_turn_started()
        finally:h._late_raw_expected_asr_advance=False
        h._begin_raw_input_transcript()
        await asyncio.sleep(.06)
        self.assertFalse(pending.done());self.assertEqual(h.abandoned,[])
        h._finish_raw_input_transcript();await pending;await h.entered.wait()
        h.release.set();await asyncio.gather(*tuple(h._tool_tasks),return_exceptions=True)
        self.assertEqual(len(h.outputs),1)

    async def test_other_routes_server_vad_already_transcribed_or_no_voice_do_not_wait(self):
        for mutation in ('route','paid','vad','transcribed','old_voice'):
            with self.subTest(mutation=mutation):
                h=Harness()
                if mutation=='route':h._realtime_protocol_capabilities.route_key='lanlan_tech_glm'
                elif mutation=='paid':h._is_free_proxy=False
                elif mutation=='vad':h._has_server_vad=True
                elif mutation=='transcribed':h._late_raw_transcript_at=time.time()+1
                else:h._last_local_loud_time=0
                h._start_raw_tool_call(self.call(),h._capture_tool_task_owner(h.ws),response_id='unannounced')
                await h.entered.wait();self.assertFalse(getattr(h,'_late_raw_tool_pending',None))
                h.release.set();await asyncio.gather(*tuple(h._tool_tasks),return_exceptions=True)

    async def test_replay_targets_apply_once_preserve_original_onset_and_parse(self):
        import neko_voice_host_patch as voice
        from neko_late_asr_tool_patch import upgrade_targets
        targets,replay=voice.TARGETS,voice._OWNER_TRACE_REPLAY
        rebuilt,extra=upgrade_targets(targets)
        self.assertEqual(rebuilt,targets);self.assertEqual(extra,())
        for relative,pairs in targets:
            if not relative.endswith(('_tools.py','_transport.py')):continue
            path=Path(__file__).resolve().parents[1]/'candidates/N.E.K.O'/relative
            text=normalize_ordering_helpers(path.read_text(encoding='utf-8'))
            for rel,before,after in replay:
                if rel==relative and after not in text and text.count(before)==1:text=text.replace(before,after,1)
            for before,after in pairs:
                if after in text:continue
                self.assertEqual(text.count(before),1,(relative,before[:80]));text=text.replace(before,after,1)
            ast.parse(text)
            self.assertTrue(all(after in text for _,after in pairs))
            again=text
            for rel,before,after in replay:
                if rel==relative and after not in again and again.count(before)==1:again=again.replace(before,after,1)
            for before,after in pairs:
                if after not in again:again=again.replace(before,after,1)
            self.assertEqual(again,text)

    async def test_actual_apply_validates_even_canonical_hunks_and_preserves_unknown_files(self):
        import tempfile
        import neko_voice_host_patch as voice
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'main_logic/omni_realtime_client/_tools.py'
            path.parent.mkdir(parents=True)
            path.write_text(source,encoding='utf-8',newline='\n')
            voice.apply_to(path)
            canonical=path.read_text(encoding='utf-8')
            self.assertEqual(voice.apply_to(path),'already patched')
            for invalid in (canonical+'\n    # late-asr-tool-ordering-v1\n',
                            canonical.replace('_STUDY_LATE_ORDERING_ASR_SECONDS = 0.4',
                                              '_STUDY_LATE_ORDERING_ASR_SECONDS = 99.0',1)):
                path.write_text(invalid,encoding='utf-8',newline='\n')
                original_bytes=path.read_bytes()
                with self.assertRaises(RuntimeError):voice.state(path)
                with self.assertRaises(RuntimeError):voice.apply_to(path)
                self.assertEqual(path.read_bytes(),original_bytes)


if __name__=='__main__':unittest.main(verbosity=2)
