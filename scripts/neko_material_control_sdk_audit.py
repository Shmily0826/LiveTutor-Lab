"""Real SDK entry/kwargs/context and result branches, offline SQLite/fake model only."""
from __future__ import annotations
import ast
import asyncio
import contextlib
import contextvars
from dataclasses import dataclass, field
import json
from pathlib import Path
import queue
import sys
import threading
import types

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
HOST = ROOT / 'benchmarks/raw/neko-product-host'
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(HOST))

# Avoid legacy plugin.core.__init__/settings importing provider/config registries.
# Compile its actual dataclass fields and task-local recipient methods instead.
core_package = types.ModuleType('plugin.core')
core_package.__path__ = [str(HOST/'plugin/core')]
sys.modules['plugin.core'] = core_package
context_tree = ast.parse((HOST/'plugin/core/context.py').read_text(encoding='utf-8'))
context_class = next(n for n in context_tree.body if isinstance(n, ast.ClassDef) and n.name == 'PluginContext')
context_class.body = [n for n in context_class.body if isinstance(n, ast.AnnAssign)
                      or getattr(n, 'name', '') in {'_lanlan_scope', 'current_lanlan'}]
context_namespace = {'dataclass': dataclass, 'field': field, 'threading': threading,
                     'contextlib':contextlib, '_CURRENT_LANLAN':contextvars.ContextVar('audit_role', default=None)}
future = ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0)
exec(compile(ast.fix_missing_locations(ast.Module(body=[future, context_class], type_ignores=[])),
             'actual-context-fields-and-recipient', 'exec'), context_namespace)
PluginContext = context_namespace['PluginContext']
from plugin.sdk.shared.core.context import SdkContext
from plugin.sdk.shared.core.entry_runtime import prepare_entry_kwargs
from plugin.sdk.plugin.base import NekoPluginBase
from plugin.sdk.plugin.llm_tool import LlmToolMeta

import test_neko_material_control as fixture_module


class QuietLogger:
    def __getattr__(self, name):
        return lambda *args, **kwargs: None


def host_result_serializer():
    tree = ast.parse((HOST/'plugin/core/host.py').read_text(encoding='utf-8'))
    handler = next(n for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef) and n.name == '_handle_trigger')
    serialization = next(n for n in ast.walk(handler) if isinstance(n, ast.If)
                         and 'hasattr(result' in ast.unparse(n.test))
    function = ast.parse("def serialize(result):\n    ret={'success':False,'data':None,'error':None}\n").body[0]
    function.body.extend([serialization, ast.Return(value=ast.Name(id='ret', ctx=ast.Load()))])
    namespace = {}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[])), 'actual-host-serialization', 'exec'), namespace)
    return namespace['serialize']


def callback_function(state):
    source = HOST/'plugin/server/routes/llm_tools.py'
    tree = ast.parse(source.read_text(encoding='utf-8'))
    function = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == 'llm_tool_callback')
    function.decorator_list = []
    function.args.defaults = []
    namespace = {'state': state, 'has_plugin_tool': lambda *args: True,
                 'get_plugin_tool_timeout': lambda *args: 150.0,
                 '_entry_id_for_tool': lambda name: '__llm_tool__'+name,
                 'logger': QuietLogger(), '_DEFAULT_TOOL_TIMEOUT_SECONDS':150}
    future = ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[future,function], type_ignores=[])), str(source), 'exec'), namespace)
    return namespace['llm_tool_callback']


async def audit():
    fixture = fixture_module.MaterialControl(methodName='runTest')
    fixture.setUp()
    try:
        product = await fixture.prepare()
        legacy = PluginContext(plugin_id='study_companion', config_path=Path(fixture.temp.name)/'plugin.toml',
                               logger=QuietLogger(), status_queue=queue.Queue(), message_queue=queue.Queue())
        sdk = SdkContext(legacy)
        product.ctx = sdk
        product.push_message = sdk.push_message
        # Do not initialize plugin logging/storage/services. Use the actual registry
        # class/methods with real SDK context and an in-memory registration queue.
        registry = NekoPluginBase.__new__(NekoPluginBase)
        registry._host_ctx, registry.ctx, registry.logger = legacy, sdk, QuietLogger()
        registry._routers, registry._dynamic_entries, registry._llm_tools = [], {}, {}
        avatar = ast.parse((fixture_module.course.SOURCE/'study_avatar_tools.py').read_text(encoding='utf-8'))
        method = next(n for n in ast.walk(avatar) if isinstance(n, ast.AsyncFunctionDef) and n.name=='study_explain_tool')
        parameters = next(k.value for k in method.decorator_list[0].keywords if k.arg=='parameters')
        meta = LlmToolMeta(name='study_explain', description='actual wrapper audit', parameters=ast.literal_eval(parameters), timeout_seconds=150)
        registry._register_llm_tool_internal(meta, product.study_explain_tool)
        entry = registry.collect_entries()['__llm_tool__study_explain']
        assert entry.handler == product.study_explain_tool
        serialize = host_result_serializer()
        seen = []

        class LocalTrigger:
            async def trigger(self, entry_id, arguments, timeout):
                registered = registry.collect_entries()[entry_id]
                kwargs = prepare_entry_kwargs(plugin_id='study_companion', entry_id=entry_id,
                    handler=registered.handler, meta=registered.meta, args=arguments)
                seen.append({'input_ctx': arguments.get('_ctx'), 'prepared_ctx': kwargs.get('_ctx')})
                name = (kwargs.get('_ctx') or {}).get('lanlan_name')
                with legacy._lanlan_scope(name):
                    result = await registered.handler(**kwargs)
                packet = serialize(result)
                assert packet['success'], packet
                return packet['data']

        class LocalState:
            plugin_hosts = {'study_companion': LocalTrigger()}
            def acquire_plugin_hosts_read_lock(self):
                return contextlib.nullcontext()

        callback = callback_function(LocalState())
        routed = await callback('study_companion', 'study_explain', {
            'arguments': {'question':'Explain this diagram', 'language':'en-US', '_ctx':{'lanlan_name':'ExactRole'}},
            'call_id':'offline-exact'})
        assert not routed['is_error']
        output = json.loads(json.dumps(routed))['output']
        binding = output['_study_material_binding']
        assert seen[-1]['prepared_ctx'] == {'lanlan_name':'ExactRole'}, seen
        assert 'ExactRole' in product._study_material_output_targets
        assert binding['context'] == fixture_module.materials.material_context(product)
        assert len(binding['boot_id']) == 32
        # Actual facade does not expose legacy private or public recipient access.
        with legacy._lanlan_scope('ScopedRole'):
            legacy._current_lanlan = 'MutablePreviousRole'
            assert legacy.current_lanlan == 'ScopedRole'
            facade_private = getattr(sdk, '_current_lanlan', '')
            facade_public = getattr(sdk, 'current_lanlan', '')
            fallback = fixture_module.materials.material_output_target(product, {})
        assert facade_private == '' and facade_public == '' and fallback == ''
        product._study_material_output_targets.clear()
        no_role = await callback('study_companion', 'study_explain', {
            'arguments': {'question':'Explain this diagram'}, 'call_id':'offline-no-context'})
        assert '_study_material_binding' in no_role['output']
        assert product._study_material_output_targets == {}
        assert seen[-1]['prepared_ctx'] is None
        # A named **kwargs wrapper opts in to _ctx; preparation must retain it.
        assert entry.meta.params is None
        print(json.dumps({'registered_entry':entry.meta.id, 'handler_accepts_ctx':True,
            'ctx_retained_through_actual_callback_prepare':seen[0]['prepared_ctx'],
            'binding_survives_actual_host_and_callback_serialization':True,
            'binding_boot_hex_length':len(binding['boot_id']),
            'real_sdk_context_type':type(sdk).__module__+'.'+type(sdk).__name__,
            'legacy_contextvar_role_visible':True, 'sdk_private_recipient_visible':bool(facade_private),
            'sdk_public_recipient_visible':bool(facade_public),
            'producer_no_ctx_target':fallback, 'no_ctx_still_returns_binding_but_registers_no_target':True,
            'external_calls':0}, ensure_ascii=False, indent=2))
    finally:
        fixture.tearDown()


if __name__ == '__main__':
    asyncio.run(audit())
