"""Actual filter and visible-stream methods, without SDK/server/provider/device imports."""
import ast
import asyncio
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch as mock_patch

import neko_dsml_output_patch as patch

ROOT = Path(__file__).resolve().parents[1]
HOST = ROOT/'benchmarks/raw/neko-product-host'
filter_source = patch.patch_filter((HOST/'utils/llm_tool_leak_filter.py').read_text(encoding='utf-8'))
filter_module = ModuleType('dsml_filter_fixture')
sys.modules[filter_module.__name__] = filter_module
exec(compile(filter_source, 'actual_llm_tool_leak_filter.py', 'exec'), filter_module.__dict__)
ToolLeakFilter = filter_module.ToolLeakFilter

LEAK = ('<｜｜DSML｜｜ invoke name="study_code">\n'
        '<｜｜DSML｜｜ parameter name="mode" string="true">find</｜｜DSML｜｜ parameter>\n'
        '<｜｜DSML｜｜ parameter name="query" string="true">routes/weather.js</｜｜DSML｜｜ parameter>\n'
        '</｜｜DSML｜｜ invoke>\n</｜｜DSML｜｜ calls>')


def drain(chunks):
    f = ToolLeakFilter(tool_names={'study_code'})
    output = []
    for chunk in chunks:
        visible, _ = f.feed(chunk)
        output.append(visible)
    tail, _ = f.finalize()
    return ''.join(output)+tail, f


def stream_class():
    path = HOST/'main_logic/omni_offline_client/_tools.py'
    tree = ast.parse(patch.patch_tools(path.read_text(encoding='utf-8')))
    names = {'_astream_visible_with_tools', '_filter_tool_leak_content'}
    methods = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in names]
    shared = ast.parse((HOST/'main_logic/omni_offline_client/_shared.py').read_text(encoding='utf-8'))
    check = next(n for n in shared.body if isinstance(n, ast.FunctionDef) and n.name=='_generation_check')
    body = [check, ast.ClassDef(name='ActualStream', bases=[], keywords=[], body=methods, decorator_list=[])]
    scope = {'ToolLeakFilter': ToolLeakFilter, 'LLMStreamChunk': SimpleNamespace,
             'log_tool_leak_filtered': lambda *a, **k: None}
    exec(compile(ast.fix_missing_locations(ast.Module(body=body, type_ignores=[])), str(path), 'exec'), scope)
    return scope['ActualStream']


class Harness(stream_class()):
    def __init__(self, chunks, *, prefiltered=False, active=True):
        self.chunks=chunks;self.prefiltered=prefiltered;self.active=active
        self.provider_calls=0;self.released=[]
    async def _astream_with_tools(self, messages, **overrides):
        self.provider_calls+=1
        for chunk in self.chunks:
            if self.prefiltered and getattr(chunk,'content',None):
                chunk.content=self._filter_tool_leak_content(chunk.content,overrides['_tool_leak_filter'])
                chunk._tool_leak_filtered=True
            yield chunk
    def _response_generation_is_active(self,generation):return self.active
    def _release_tool_image_slots(self,slots):self.released.append(slots)
    async def answer(self,**overrides):
        return ''.join([getattr(c,'content','') or '' async for c in self._astream_visible_with_tools([],**overrides)])


class DSMLFilter(unittest.TestCase):
    def test_actual_leak_at_every_split_and_single_character_chunks(self):
        for split in range(len(LEAK)+1):
            with self.subTest(split=split):
                visible,f=drain([LEAK[:split],LEAK[split:]])
                self.assertEqual(visible,'');self.assertTrue(f.dsml_filtered)
        self.assertEqual(drain(list(LEAK))[0],'')

    def test_complete_blocks_preserve_surrounding_answer(self):
        for leak in (LEAK,'<｜DSML｜function_calls><｜DSML｜invoke name="study_code">x</｜DSML｜invoke></｜DSML｜function_calls>'):
            visible,_=drain(list('之前'+leak+'之后'+leak+'完成'))
            self.assertEqual(visible,'之前之后完成')

    def test_false_end_inside_parameter_is_never_visible(self):
        leak='<｜DSML｜calls><｜DSML｜parameter name="x">before </｜DSML｜calls> private argument</｜DSML｜parameter></｜DSML｜calls>'
        for split in range(len(leak)+1):
            with self.subTest(split=split):
                self.assertEqual(drain(['正常',leak[:split],leak[split:],'结论'])[0],'正常结论')

    def test_unclosed_payload_is_dropped_with_bounded_tail(self):
        f=ToolLeakFilter();output=[]
        for chunk in ('<｜DSML｜invoke name="study_code">',*['x'*400]*100):
            output.append(f.feed(chunk)[0]);self.assertLessEqual(len(f._pending),f._max_tail)
        tail,event=f.finalize();self.assertEqual(''.join(output)+tail,'');self.assertTrue(event.finalized)

    def test_distinctive_truncated_markers_drop_but_normal_html_and_mentions_survive(self):
        for fragment in ('<｜','</｜','<｜｜D','<｜DSML','</｜｜DSML｜'):
            visible,f=drain(list(fragment));self.assertEqual(visible,'');self.assertTrue(f.dsml_filtered)
        for normal in ('DSML格式只是说明','<section>代码</section>','if (x < 3) {}','`study_code` 可以查询源码','<','</'):
            visible,f=drain(list(normal));self.assertEqual(visible,normal);self.assertFalse(f.dsml_filtered)

    def test_patch_replay_and_idempotence_bind_original_bytes(self):
        for relative,(expected,fn) in patch.TARGETS.items():
            current=(HOST/relative).read_text(encoding='utf-8')
            updated=fn(current)
            self.assertEqual(fn(updated),updated)
            edits=patch.FILTER_EDITS if relative.startswith('utils/') else patch.TOOLS_EDITS
            for old,new in reversed(edits):updated=updated.replace(new,old)
            self.assertEqual(hashlib.sha256(updated.encode()).hexdigest(),expected)
            self.assertEqual(fn(updated),fn(current))
            with self.assertRaises(ValueError):fn('def unexpected_source(): pass\n')


class ReplayDeployment(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='dsml-replay-',dir=ROOT/'benchmarks/raw')
        self.addCleanup(temp.cleanup);self.root=Path(temp.name);self.host=self.root/'host'
        self.original={};self.updated={};entries=[]
        for relative,(_,fn) in patch.TARGETS.items():
            source=(HOST/relative).read_text(encoding='utf-8')
            if patch.MARKER in source:
                edits=patch.FILTER_EDITS if relative.startswith('utils/') else patch.TOOLS_EDITS
                for old,new in reversed(edits):source=source.replace(new,old)
            self.original[relative]=source.encode();self.updated[relative]=fn(source).encode()
            target=self.host/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(self.original[relative])
            entries.append({'path':relative,'patched_sha256':hashlib.sha256(self.updated[relative]).hexdigest()})
        manifest=self.root/'patches/neko-study-2026-10-10-host/manifest.json'
        manifest.parent.mkdir(parents=True);manifest.write_text(json.dumps({'files':entries}))

    def test_replay_only_known_sources_and_idempotent_pins(self):
        with mock_patch.object(patch,'ROOT',self.root):
            patch.apply_to(self.host);patch.apply_to(self.host)
        for relative in patch.TARGETS:self.assertEqual((self.host/relative).read_bytes(),self.updated[relative])

    def test_unknown_second_target_refuses_entire_plan_before_any_write(self):
        relative=list(patch.TARGETS)[-1];(self.host/relative).write_bytes(b'unknown source preserve')
        with mock_patch.object(patch,'ROOT',self.root):
            with self.assertRaises(ValueError):patch.apply_to(self.host)
            with self.assertRaises(ValueError):patch.apply_to(self.root.parent)
        first=list(patch.TARGETS)[0]
        self.assertEqual((self.host/first).read_bytes(),self.original[first])
        self.assertEqual((self.host/relative).read_bytes(),b'unknown source preserve')


class VisibleStream(unittest.IsolatedAsyncioTestCase):
    async def test_filtered_only_answer_gets_one_honest_fallback_without_retry(self):
        for prefiltered in (False,True):
            h=Harness([SimpleNamespace(content=c) for c in list(LEAK)],prefiltered=prefiltered)
            self.assertEqual(await h.answer(),patch.FALLBACK)
            self.assertEqual(h.provider_calls,1);self.assertEqual(h.released,[[]])

    async def test_real_answer_after_markup_gets_no_extra_failure(self):
        h=Harness([SimpleNamespace(content=LEAK),SimpleNamespace(content='有证据的解释。')])
        self.assertEqual(await h.answer(),'有证据的解释。');self.assertEqual(h.provider_calls,1)

    async def test_persisted_tool_round_does_not_count_as_final_answer(self):
        h=Harness([SimpleNamespace(content='我查一下。'),SimpleNamespace(content='',tool_round_persisted=True),SimpleNamespace(content=LEAK)])
        self.assertEqual(await h.answer(),'我查一下。'+patch.FALLBACK)

    async def test_cancelled_generation_never_gets_fallback(self):
        h=Harness([SimpleNamespace(content=LEAK)],active=False)
        self.assertEqual(await h.answer(_response_generation=7),'')

    async def test_caller_owned_slots_are_not_released(self):
        h=Harness([SimpleNamespace(content='正常回答。')]);slots=[]
        self.assertEqual(await h.answer(_tool_image_slots=slots),'正常回答。');self.assertEqual(h.released,[])


if __name__=='__main__':unittest.main(verbosity=2)
