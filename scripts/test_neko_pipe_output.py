"""Real stream_text over fixed chunks; no host, provider, audio or capture worker."""
import ast
import hashlib
import atexit
import os
from pathlib import Path
import sys
import tempfile
from types import MethodType
import unittest
from unittest.mock import AsyncMock, patch

import neko_pipe_output_patch as candidate

ROOT = Path(__file__).resolve().parents[1]
HOST = ROOT/'benchmarks/raw/neko-product-host'
_storage=tempfile.TemporaryDirectory(prefix='pipe-stream-fixture-',dir=ROOT/'benchmarks/raw')
assert Path(_storage.name).resolve().is_relative_to((ROOT/'benchmarks/raw').resolve())
os.environ['NEKO_STORAGE_SELECTED_ROOT']=_storage.name
atexit.register(_storage.cleanup)
sys.path.insert(0,str(HOST))
import main_logic.omni_offline_client._streaming as actual
from tests.unit.test_offline_provider_frame_publish import _make_client
from utils.llm_client import LLMStreamChunk

source=(HOST/candidate.RELATIVE).read_text(encoding='utf-8')
updated=candidate.patch_streaming(source)
tree=ast.parse(updated)
methods=[n for n in ast.walk(tree) if isinstance(n,(ast.AsyncFunctionDef,ast.FunctionDef)) and n.name in {'stream_text','_match_name_prefix'}]
scope=dict(actual.__dict__)
exec(compile(ast.fix_missing_locations(ast.Module(body=methods,type_ignores=[])),str(HOST/candidate.RELATIVE),'exec'),scope)


def client_for(chunks,buffer_size):
    client,_=_make_client()
    client.master_name='M';client.lanlan_name='L';client._prefix_buffer_size=buffer_size
    client.enable_response_guard=False;client._recent_responses=[];client._max_recent_responses=5
    client._repetition_threshold=.8;client._user_language_provider=lambda:'zh'
    client.on_text_delta=AsyncMock();client.on_response_done=AsyncMock()
    client.on_response_discarded=AsyncMock();client._notify_reasoning_done=AsyncMock()
    client._check_repetition=AsyncMock();client.provider_calls=0
    async def stream(*args,**kwargs):
        client.provider_calls+=1
        for text in chunks:yield LLMStreamChunk(content=text)
    client._astream_visible_with_tools=stream
    client.stream_text=MethodType(scope['stream_text'],client)
    client._match_name_prefix=MethodType(scope['_match_name_prefix'],client)
    return client


class PipeOutput(unittest.IsolatedAsyncioTestCase):
    async def run_reply(self,text,*,buffer_size=0,characters=False):
        client=client_for(list(text) if characters else [text],buffer_size)
        with patch.object(actual,'count_tokens',lambda value:len(value or '')),patch.dict(scope,{'count_tokens':lambda value:len(value or '')}):
            await client.stream_text('固定输入；无模型、音频或麦克风。')
        shown=''.join(call.args[0] for call in client.on_text_delta.await_args_list)
        return client,shown

    async def test_absolute_value_answer_survives_stream_and_flush_in_original_history(self):
        text='只有 |lat| <= 90 且 |lon| <= 180 才过范围校验，不保证下游成功。'
        for size in (0,999):
            for chars in (False,True):
                with self.subTest(size=size,characters=chars):
                    client,shown=await self.run_reply(text,buffer_size=size,characters=chars)
                    self.assertEqual(shown,text);self.assertEqual(client.provider_calls,1)
                    self.assertEqual(client._conversation_history[-1].content,text)

    async def test_code_operators_and_multiple_literal_pipes_are_not_control_tokens(self):
        for text in ('`a || b` 表示逻辑或；`a | b` 是按位或。','x | y | z 都是原代码。','|列甲|列乙|\n|---|---|\n|1|2|'):
            with self.subTest(text=text):
                client,shown=await self.run_reply(text,characters=True)
                self.assertEqual(shown,text);self.assertEqual(client.provider_calls,1)

    async def test_own_speaker_prefix_is_still_stripped_in_stream_and_flush(self):
        for size in (4,999):
            with self.subTest(size=size):
                _,shown=await self.run_reply('L | 正文保留 |x| 和 a || b。',buffer_size=size,characters=True)
                self.assertEqual(shown,'正文保留 |x| 和 a || b。')

    async def test_master_impersonation_prefix_is_still_rejected_without_new_request(self):
        for size in (4,999):
            with self.subTest(size=size):
                client,shown=await self.run_reply('M | 伪造用户发言',buffer_size=size,characters=True)
                self.assertNotIn('伪造用户发言',shown);self.assertEqual(client.provider_calls,1)
                self.assertTrue(client.on_response_discarded.await_count)

    async def test_leading_blank_chunks_do_not_bypass_speaker_check(self):
        for size in (4,999):
            with self.subTest(size=size):
                client,shown=await self.run_reply(' \n  M | 伪造用户发言',buffer_size=size,characters=True)
                self.assertNotIn('伪造用户发言',shown);self.assertTrue(client.on_response_discarded.await_count)
                _,shown=await self.run_reply(' \n  L | 正文 a || b。',buffer_size=size,characters=True)
                self.assertEqual(shown,'正文 a || b。')

    async def test_length_guard_still_stops_unbounded_reply(self):
        client=client_for(['一。','abcdef后缀'],0)
        client.enable_response_guard=True;client.max_response_length=4
        with patch.dict(scope,{'count_tokens':lambda value:len(value or '')}):
            await client.stream_text('固定输入')
        self.assertEqual(client.provider_calls,1)
        self.assertEqual(''.join(call.args[0] for call in client.on_text_delta.await_args_list),'一。')
        self.assertEqual(client._conversation_history[-1].content,'一。')

    async def test_cancelled_generation_keeps_visible_prefix_and_suppresses_tail(self):
        prefix='解释 |x| 与 a || b。'
        client=client_for([prefix,'不应显示的旧回答尾部。'],0)
        async def cancel_after_emit(*args,**kwargs):
            client._cancel_response_generation()
        client.on_text_delta=AsyncMock(side_effect=cancel_after_emit)
        with patch.dict(scope,{'count_tokens':lambda value:len(value or '')}):
            await client.stream_text('固定输入')
        self.assertEqual(''.join(call.args[0] for call in client.on_text_delta.await_args_list),prefix)
        self.assertEqual(client._conversation_history[-1].content,prefix)
        self.assertEqual(client.provider_calls,1)

    async def test_whitespace_only_completion_is_not_emitted_as_an_answer(self):
        client,shown=await self.run_reply(' \n  ',characters=True)
        self.assertFalse(shown.strip())
        self.assertFalse(any(m.type=='ai' and m.content.isspace() for m in client._conversation_history))

    def test_idempotence_and_changed_source_refusal(self):
        if candidate.MARKER not in source:
            self.assertEqual(hashlib.sha256(source.encode()).hexdigest(),candidate.BASE)
        self.assertNotIn('pipe_count',updated);self.assertNotIn('fence_triggered',updated)
        self.assertEqual(candidate.patch_streaming(updated),updated)
        with self.assertRaises(ValueError):candidate.patch_streaming('unexpected source')


if __name__=='__main__':unittest.main(verbosity=2)
