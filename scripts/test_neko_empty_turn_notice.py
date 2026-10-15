"""Actual patched transport method: retry hint after an empty answer to a complete question."""
import ast
import asyncio
import logging
import time
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'benchmarks/raw/neko-product-host/main_logic/omni_realtime_client/_transport.py'
tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
node = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == '_livetutor_note_empty_answer')
scope = {'asyncio': asyncio, 'time': time, 'logger': logging.getLogger('empty-turn-test')}
exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), str(SOURCE), 'exec'), scope)
note = scope['_livetutor_note_empty_answer']


class EmptyTurnNotice(unittest.IsolatedAsyncioTestCase):
    def client(self, **overrides):
        sent = []
        async def status(text):
            sent.append(text)
        now = time.time()
        values = dict(_late_raw_transcript_at=now - 0.5, _audio_delta_count=0, _current_response_transcript='',
                      _response_done_total=4, _connection_generation=1, _is_responding=False,
                      _user_recent_activity_time=now - 3.0, on_status_message=status)
        values.update(overrides)
        return SimpleNamespace(**values), sent

    async def settle(self, client, change=None):
        note(client)
        if change:
            change(client)
        await asyncio.sleep(3.1)

    async def test_empty_answer_to_a_fresh_question_shows_the_hint_once(self):
        client, sent = self.client()
        await self.settle(client)
        self.assertEqual(sent, ['角色这次没有回应，请再说一遍。'])
        note(client)  # Same question: no second hint.
        await asyncio.sleep(3.1)
        self.assertEqual(len(sent), 1)

    async def test_tool_calls_audio_text_and_old_questions_are_not_empty_answers(self):
        cases = [dict(_audio_delta_count=3), dict(_current_response_transcript='hi'),
                 dict(_late_raw_transcript_at=time.time() - 20), dict(on_status_message=None)]
        for overrides in cases:
            client, sent = self.client(**overrides)
            if overrides.get('on_status_message', 1) is None:
                note(client)
                continue
            await self.settle(client)
            self.assertEqual(sent, [], overrides)
        client, sent = self.client()
        client._livetutor_call_seen_at = client._late_raw_transcript_at + 0.1
        await self.settle(client)
        self.assertEqual(sent, [])

    async def test_anything_happening_in_the_next_three_seconds_cancels_the_hint(self):
        changes = [lambda c: setattr(c, '_response_done_total', 5),
                   lambda c: setattr(c, '_is_responding', True),
                   lambda c: setattr(c, '_late_raw_transcript_at', time.time()),
                   lambda c: setattr(c, '_livetutor_call_seen_at', time.time()),
                   lambda c: setattr(c, '_user_recent_activity_time', time.time() + 3.0),
                   lambda c: setattr(c, '_connection_generation', 2)]
        for change in changes:
            client, sent = self.client()
            await self.settle(client, change)
            self.assertEqual(sent, [])


if __name__ == '__main__': unittest.main(verbosity=2)
