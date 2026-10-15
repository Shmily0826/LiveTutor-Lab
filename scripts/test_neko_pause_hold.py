"""Actual patched host methods: pause hold on the free uplink and the Study wait toast."""
import ast
import asyncio
import logging
import os
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
HOST = ROOT / 'benchmarks/raw/neko-product-host/main_logic'


def method(relative, cls_name_hint, name, scope):
    tree = ast.parse((HOST / relative).read_text(encoding='utf-8'))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            module = ast.Module(body=[node], type_ignores=[])
            exec(compile(ast.fix_missing_locations(module), str(HOST / relative), 'exec'), scope)
            return scope[name]
    raise AssertionError(f'{name} not found in {relative}')


hold = method('omni_realtime_client/_transport.py', '', '_livetutor_pause_hold',
              {'logger': logging.getLogger('pause-hold-test')})
FRAME = b'\x00\x00' * 160  # 10 ms of 16 kHz PCM16


class PauseHold(unittest.TestCase):
    def setUp(self):
        self.client = SimpleNamespace(_connection_generation=1)
        for key in ('NEKO_PAUSE_HOLD_KEEP_MS', 'NEKO_PAUSE_HOLD_MS'):
            os.environ.pop(key, None)

    def feed(self, voiced, frames):
        return [hold(self.client, FRAME, voiced) for _ in range(frames)]

    def test_short_internal_pause_is_cut_to_keep_and_speech_is_never_delayed(self):
        self.assertTrue(all(out == FRAME for out in self.feed(True, 50)))
        pause = self.feed(False, 90)  # 0.9 s, the pause that split real turns
        self.assertEqual(sum(1 for out in pause if out), 30)  # first 300 ms only
        resumed = self.feed(True, 5)
        self.assertTrue(all(out == FRAME for out in resumed))
        self.assertEqual(self.client._livetutor_hold['held'], [])

    def test_a_real_stop_releases_all_held_silence_at_once(self):
        self.feed(True, 20)
        out = self.feed(False, 140)
        sent = [len(part) for part in out if part]
        self.assertEqual(sum(sent), 140 * len(FRAME))  # nothing dropped: 30 kept, 100 held + 1 released, 9 after
        self.assertEqual(max(sent), 101 * len(FRAME))
        self.assertTrue(all(part == FRAME for part in self.feed(False, 20)))  # no new utterance: pass-through

    def test_leading_silence_and_new_connection_are_untouched(self):
        self.assertTrue(all(out == FRAME for out in self.feed(False, 200)))
        self.feed(True, 5)
        self.feed(False, 50)
        self.client._connection_generation = 2
        self.assertTrue(all(out == FRAME for out in self.feed(False, 50)))

    def test_limits_are_configurable(self):
        os.environ['NEKO_PAUSE_HOLD_KEEP_MS'] = '100'
        os.environ['NEKO_PAUSE_HOLD_MS'] = '200'
        self.feed(True, 5)
        out = self.feed(False, 40)
        self.assertEqual(sum(1 for part in out if part == FRAME), 10 + 9)  # 100 ms kept, then pass after 300 ms
        self.assertIn(21 * len(FRAME), [len(part) for part in out])


notice = method('core/tool_calling.py', '', '_start_study_wait_notice', {'os': os, 'asyncio': asyncio})


class WaitNotice(unittest.IsolatedAsyncioTestCase):
    def manager(self, source='plugin:study_companion'):
        sent = []
        definition = SimpleNamespace(metadata={'source': source})
        session = object()
        async def send_status(text):
            sent.append(text)
        manager = SimpleNamespace(tool_registry=SimpleNamespace(get=lambda name: definition),
                                  session=session, send_status=send_status)
        return manager, session, sent

    async def run_tool(self, seconds, name='study_explain', arguments=None, source='plugin:study_companion', same=True):
        manager, session, sent = self.manager(source)
        call = SimpleNamespace(name=name, arguments=arguments or {'material_source': 'project_code'})
        task = notice(manager, call, session if same else object())
        await asyncio.sleep(seconds)
        if task is not None:
            task.cancel()
        await asyncio.sleep(0)
        return sent, task

    async def test_fast_tools_show_nothing_and_slow_tools_show_the_toast(self):
        self.assertEqual((await self.run_tool(0.2))[0], [])
        sent, _ = await self.run_tool(1.7)
        self.assertEqual(sent, ['正在查看源码……'])

    async def test_only_study_plugin_tools_of_the_current_session(self):
        for kwargs in ({'name': 'recall_memory'}, {'source': 'plugin:other'}, {'same': False}):
            sent, task = await self.run_tool(1.7, **kwargs)
            self.assertEqual((sent, task), ([], None))
        os.environ['NEKO_STUDY_WAIT_NOTICE'] = '0'
        try:
            self.assertEqual((await self.run_tool(1.7))[1], None)
        finally:
            os.environ.pop('NEKO_STUDY_WAIT_NOTICE')

    async def test_wording_follows_tool_and_one_turn_language(self):
        self.assertEqual((await self.run_tool(1.7, name='study_quiz', arguments={}))[0], ['正在出题……'])
        self.assertEqual((await self.run_tool(1.7, arguments={'language': 'en-US'}))[0], ['Looking at the material...'])


if __name__ == '__main__': unittest.main(verbosity=2)
