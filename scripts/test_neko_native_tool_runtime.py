"""Exercise deployed host imports without staging or replacing its methods."""
import asyncio
import inspect
import logging
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
HOST = ROOT / 'benchmarks/raw/neko-product-host'
sys.path.insert(0, str(HOST))
import neko_phrase_input_transport as producer
from main_logic.omni_realtime_client import _response_arbiter, _tools, _transport
from main_logic.tool_calling import ToolResult
import test_neko_phrase_input_transport as fixture


class DeployedToolJoin(fixture.PhraseTransport):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.calls = []
        async def handler(call):
            self.calls.append(call.call_id)
            return ToolResult(call_id=call.call_id, name=call.name, output={'question': '方向是哪边？'})
        self.client.on_tool_call = handler

    async def asyncTearDown(self):
        driver = getattr(self.client, '_native_phrase_uplink', None)
        tasks = list(getattr(self.client, '_tool_tasks', ()))
        if driver is not None:
            tasks.extend(task for task in (driver.writer, driver.response_waiter, driver.watchdog)
                         if task is not None)
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await super().asyncTearDown()
        await self.client._response_arbiter.shutdown()

    async def settle(self, predicate):
        async with asyncio.timeout(.7):
            while not predicate():
                await asyncio.sleep(.001)

    def outputs(self):
        return [item for item in self.socket.sent if item.get('item', {}).get('type') == 'function_call_output']

    async def test_actual_host_imports_return_tool_inside_original_slot(self):
        for module in (producer, _response_arbiter, _tools, _transport):
            self.assertTrue(Path(module.__file__).resolve().is_relative_to(HOST.resolve()))
        self.assertIs(type(self.client._response_arbiter), _response_arbiter.RealtimeResponseArbiter)
        self.assertEqual(inspect.getsourcefile(self.client._start_raw_tool_call), str(HOST / 'main_logic/omni_realtime_client/_tools.py'))
        await self.phrase()
        await self.finish_writer()
        self.assertIs(type(self.client._native_phrase_uplink), producer.NativePhraseUplink)
        arbiter = self.client._response_arbiter
        original = arbiter._current.ticket
        self.socket.feed({'type': 'response.function_call_arguments.done', 'name': 'study_quiz',
                          'call_id': 'actual-runtime-call', 'response_id': 'function-parent', 'arguments': '{}'})
        self.socket.feed({'type': 'response.done', 'response': {'id': 'different-parent', 'status': 'completed'}})
        await self.settle(lambda: bool(self.outputs()))
        self.assertEqual(self.calls, ['actual-runtime-call'])
        self.assertIs(arbiter._current.ticket, original)
        self.assertEqual(arbiter._queue.qsize(), 0)
        self.assertFalse(original.started.done())
        self.assertEqual(self.outputs()[0]['item']['call_id'], 'actual-runtime-call')
        self.assertFalse(any(item['type'] == 'response.create' for item in self.socket.sent))
        self.socket.feed({'type': 'response.audio_transcript.delta', 'response_id': 'runtime-audio', 'delta': '方向'})
        await self.settle(lambda: original.started.done())
        self.socket.feed({'type': 'response.done', 'response': {'id': 'runtime-audio', 'status': 'completed'}})
        await self.settle(lambda: self.client._native_phrase_uplink.waiting is None)
        self.assertIsNone(original.done.exception())
        self.assertFalse(self.client._voice_handoff_input_open)
        self.assertFalse(self.client._fatal_error_occurred)

    async def test_actual_host_rejects_missing_wire_id_before_tool_execution(self):
        await self.phrase()
        await self.finish_writer()
        self.socket.feed({'type': 'response.function_call_arguments.done', 'name': 'study_quiz',
                          'response_id': 'wire-id-missing', 'arguments': '{}'})
        await self.settle(lambda: self.client._fatal_error_occurred)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.outputs(), [])
        self.assertTrue(self.client._voice_handoff_input_open)


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.CRITICAL)
    names = [name for name in DeployedToolJoin.__dict__ if name.startswith('test_')]
    result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(DeployedToolJoin(name) for name in names))
    sys.exit(not result.wasSuccessful())
