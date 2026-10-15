"""Content-free phases cover source processing and the existing empty-result retry."""
import asyncio
import importlib
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import test_neko_code_structure_request as actual

trace_module = importlib.import_module('product_study.study_call_trace')
Mixin = actual.scope['_StudyCodeToolsMixin']


class TimingHarness(actual.Harness):
    _code_filter = Mixin._code_filter
    _code_leak = Mixin._code_leak


class CodeTiming(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'main.py').write_text('fixture', encoding='utf-8')
        self.h = TimingHarness()
        self.h._code_authorization = lambda: {
            'root': str(self.root), 'prefix': 'fixture/', 'name': 'fixture', 'commit': 'A'}
        self.body = '**fixture/main.py**\n```\n1\tSOURCE_CONTENT_MARKER\n```'

    async def invoke(self, run, **request):
        with patch.dict(actual.scope, {'_run': run}):
            with trace_module.trace_call(None) as trace:
                result = await self.h.study_code_tool(**request)
        # Timing records contain only fixed phase names, numbers and outcome.
        for stage in trace['stages']:
            self.assertEqual(set(stage), {'name', 'at_ms', 'elapsed_ms', 'outcome'})
        self.assertNotIn('SOURCE_CONTENT_MARKER', str(trace))
        self.assertNotIn('LEARNER_CONTENT_MARKER', str(trace))
        return result, {stage['name']: stage for stage in trace['stages']}

    async def test_file_window_filter_and_shown_are_timed(self):
        async def run(*args):
            return SimpleNamespace(returncode=0, stdout='**fixture/main.py**\n1\tSOURCE_CONTENT_MARKER')
        result, stages = await self.invoke(run, mode='file', file='main.py', limit=1)
        self.assertEqual(result['shown'], [{'file': 'fixture/main.py', 'lines': [1]}])
        self.assertTrue({'source_file_window', 'source_filter', 'source_leak',
                         'source_evidence', 'source_shown', 'source_record'} <= stages.keys())

    async def test_empty_retry_sync_and_query_delays_are_separate(self):
        forced = []
        async def sync(*args, force=False):
            forced.append(force)
            if force:
                await asyncio.sleep(0.025)
            return 'synced' if force else 'unchanged'
        self.h._code_sync = sync
        calls = []
        async def run(command):
            calls.append(command)
            if len(calls) == 2:
                await asyncio.sleep(0.025)
            return SimpleNamespace(returncode=0, stdout=self.body if len(calls) == 2 else '')
        result, stages = await self.invoke(run, query='LEARNER_CONTENT_MARKER')
        self.assertEqual(forced, [False, True])
        self.assertEqual(calls[0], calls[1])
        self.assertEqual(result['index_sync'], 'synced-after-empty')
        self.assertEqual(result['shown'], [{'file': 'fixture/main.py', 'lines': [1]}])
        for name in ('sync', 'query', 'filter', 'leak', 'evidence', 'shown'):
            self.assertIn('source_retry_' + name, stages)
        for name in ('source_retry_sync', 'source_retry_query'):
            self.assertGreaterEqual(stages[name]['elapsed_ms'], 20)

    async def test_leak_refusal_keeps_record_and_retry_unreachable(self):
        self.h._code_leak = lambda *args: 'unsafe'
        async def run(*args):
            return SimpleNamespace(returncode=0, stdout=self.body)
        result, stages = await self.invoke(run, query='LEARNER_CONTENT_MARKER')
        self.assertEqual(result['error'], 'EVIDENCE_FILTER_UNSURE')
        self.assertNotIn('source_record', stages)
        self.assertFalse(any(name.startswith('source_retry_') for name in stages))

    async def test_retry_exception_and_cancellation_keep_existing_semantics(self):
        async def sync(*args, force=False):
            return 'synced' if force else 'throttled'
        self.h._code_sync = sync
        for error in (RuntimeError('fixture'), asyncio.CancelledError()):
            calls = []
            async def run(*args):
                calls.append(1)
                if len(calls) == 2:
                    raise error
                return SimpleNamespace(returncode=0, stdout='')
            with patch.dict(actual.scope, {'_run': run}):
                with trace_module.trace_call(None) as trace:
                    if isinstance(error, asyncio.CancelledError):
                        with self.assertRaises(asyncio.CancelledError):
                            await self.h.study_code_tool(query='fixture')
                    else:
                        result = await self.h.study_code_tool(query='fixture')
                        self.assertEqual(result['evidence'], '')
                        self.assertEqual(result['index_sync'], 'throttled')
            stage = next(s for s in trace['stages'] if s['name'] == 'source_retry_query')
            self.assertEqual(stage['outcome'], 'error')


if __name__ == '__main__':
    unittest.main(verbosity=2)
