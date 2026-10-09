"""Exercise the actual gateway reservation path without network or credentials."""
import ast
import asyncio
import json
import os
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
from unittest.mock import patch


class BudgetError(Exception):
    def __init__(self, message, **fields):
        super().__init__(message)
        self.fields = fields


async def check():
    source = Path(__file__).parent / 'payload/study_companion/study_model_gateway.py'
    tree = ast.parse(source.read_text(encoding='utf-8'))
    gateway = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'StudyModelGateway')
    gateway.body = [n for n in gateway.body if getattr(n, 'name', '') in {'__init__', 'call'}]
    module = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0), gateway], type_ignores=[])
    env = dict(os=os, Path=Path, json=json, time=time, Any=object,
               QwenNativeClient=lambda **_: None, messages_have_image=lambda _: False,
               StudyModelError=BudgetError)
    exec(compile(ast.fix_missing_locations(module), str(source), 'exec'), env)
    runtime = SimpleNamespace(model_group='agent', model='offline-test', base_url='local', api_key='test', transport='openai_compatible')
    transports = []
    async def quota(*_):
        pass
    async def transport(*_, **kwargs):
        transports.append(kwargs['operation'])
        return SimpleNamespace(input_tokens=1, output_tokens=1)
    def instance():
        obj = env['StudyModelGateway'](logger=None)
        obj._reserve_agent_quota = quota
        obj._call_generic = transport
        return obj
    with tempfile.TemporaryDirectory() as temporary:
        audit = Path(temporary) / 'calls.jsonl'
        with patch.dict(os.environ, NEKO_STUDY_API_AUDIT=str(audit), NEKO_STUDY_API_BUDGET='2'):
            first = instance()
            await first.call([], operation='explain', deadline=time.monotonic()+10, runtime=runtime)
            reloaded = instance()
            assert reloaded._dev_calls == 1
            await reloaded.call([], operation='summary', deadline=time.monotonic()+10, runtime=runtime)
            try:
                await instance().call([], operation='blocked', deadline=time.monotonic()+10, runtime=runtime)
            except BudgetError as error:
                assert error.fields['diagnostic'] == 'agent_quota_exceeded'
            else:
                raise AssertionError('plugin reload reset the host budget')
            rows = [json.loads(line) for line in audit.read_text().splitlines()]
            assert [row['call'] for row in rows if row['event'] == 'started'] == [1, 2]
            assert transports == ['explain', 'summary']
    print('PASS: actual gateway limits calls across plugin reload; no network transport')


if __name__ == '__main__':
    asyncio.run(check())
