"""Source regressions for the inspected Study snapshot; no provider credentials."""
import ast
import asyncio
import importlib
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'benchmarks/raw/goal-isolated/study_companion'
sys.path.insert(0, str(ROOT / 'benchmarks/raw/goal-source-libs'))
for name, directory in [('plugin', ROOT/'candidates/N.E.K.O/plugin'),
                        ('plugin.sdk', ROOT/'candidates/N.E.K.O/plugin/sdk'),
                        ('utils', ROOT/'candidates/N.E.K.O/utils'),
                        ('study_fixture', SOURCE)]:
    package = ModuleType(name)
    package.__path__ = [str(directory)]
    sys.modules[name] = package
# Only the tokenizer's public encoding constant is needed; do not load app config.
configuration = ModuleType('config')
configuration.PERSONA_RENDER_ENCODING = 'o200k_base'
sys.modules['config'] = configuration
models = importlib.import_module('study_fixture.models')
prompts = importlib.import_module('study_fixture.llm_prompts')


def source_functions(filename, names, globals_dict):
    tree = ast.parse((SOURCE/filename).read_text(encoding='utf-8'))
    selected = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names:
            node.decorator_list = []
            selected.append(node)
    if len(selected) != len(names):
        raise AssertionError('regression functions missing from source snapshot')
    module = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0), *selected], type_ignores=[])
    exec(compile(ast.fix_missing_locations(module),filename,'exec'),globals_dict)
    return globals_dict


class PromptTests(unittest.TestCase):
    def test_oversized_answer_is_rejected_instead_of_graded_from_a_prefix(self):
        with self.assertRaises(ValueError):
            prompts._context_json_for_prompt('answer_evaluate',
                {'question':'q','answer':'unique learner detail '*10000,'expected_answer':'reference'})

    def test_learner_answer_survives_auxiliary_context_pressure(self):
        context = {name: {'history': [{'text': 'auxiliary study context '*200} for _ in range(20)]}
                   for name in sorted(prompts._PROMPT_CONTEXT_ALLOWED_FIELDS)
                   if name not in {'question','answer','expected_answer'}}
        context.update(question='Differentiate sin(x²).', answer='答案是 42。',
                       expected_answer='2x cos(x²)')
        rendered = prompts._context_json_for_prompt('answer_evaluate',context)
        parsed = json.loads(rendered)
        self.assertEqual(parsed.get('answer'), context['answer'])
        self.assertEqual(parsed.get('question'), context['question'])
        self.assertLessEqual(prompts.count_tokens(rendered),3000)

    def test_private_fields_stay_out_of_model_context(self):
        context = {'question':'q','answer':'a','expected_answer':'r',
                   'question_payload':{'api_key':'never_send_fixture_secret','rubric':['point']}}
        rendered = prompts._context_json_for_prompt('answer_evaluate',context)
        self.assertNotIn('never_send_fixture_secret',rendered)
        self.assertIn('rubric',rendered)


class SettingsTests(unittest.TestCase):
    def test_awareness_settings_are_applied_and_normalized(self):
        globals_dict = source_functions('entry_status_entries.py',
            {'_apply_settings_config','_coerce_bool','_coerce_int'}, {'StudyConfig':models.StudyConfig})
        updated = globals_dict['_apply_settings_config'](models.StudyConfig(),
            {'awareness':{'enabled':True,'snapshot_interval_seconds':0,'os_signals_enabled':'false'}})
        self.assertTrue(updated.awareness.enabled)
        self.assertEqual(updated.awareness.snapshot_interval_seconds,1)
        self.assertFalse(updated.awareness.os_signals_enabled)


class HostLoopTests(unittest.TestCase):
    def test_cold_source_import_preserves_startup_tasks_and_restores_asyncio(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location('lab_loop_fixture',ROOT/'scripts/neko_lab_runtime_loop.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        original_run = asyncio.run
        tasks = []
        async def startup():
            tasks.append(asyncio.create_task(asyncio.sleep(0.02)))
            await asyncio.sleep(0)
        async def entry():
            self.assertFalse(tasks[0].done())
            await asyncio.wait_for(tasks[0],0.1)
        try:
            module._install_child_loop()
            asyncio.run(startup())
            asyncio.run(entry())
        finally:
            module._close_child_loop()
        self.assertIs(asyncio.run,original_run)

    def test_background_consumer_survives_startup_and_receives_entry_on_same_loop(self):
        path = ROOT/'benchmarks/raw/goal-isolated/host.py'
        tree = ast.parse(path.read_text(encoding='utf-8'))
        wrapper = next(node for node in tree.body if isinstance(node,ast.FunctionDef)
                       and node.name == '_plugin_process_runner')
        observed = []
        def lifecycle(*_,_loop_runner,**__):
            tasks = []
            queue = asyncio.Queue()
            async def consumer():
                observed.append(('background_loop',asyncio.get_running_loop()))
                observed.append(('received',await queue.get()))
            async def startup():
                tasks.append(asyncio.create_task(consumer()))
                await asyncio.sleep(0)
                observed.append(('startup_loop',asyncio.get_running_loop()))
            async def entry():
                observed.append(('entry_loop',asyncio.get_running_loop()))
                self.assertFalse(tasks[0].done())
                await queue.put('task-owned observation')
                await asyncio.wait_for(tasks[0],0.1)
            _loop_runner.run(startup())
            _loop_runner.run(entry())
        namespace = {'asyncio':asyncio,'Any':object,'_plugin_process_runner_on_loop':lifecycle}
        exec(compile(ast.Module(body=[wrapper],type_ignores=[]),str(path),'exec'),namespace)
        namespace['_plugin_process_runner']()
        loops = [value for name,value in observed if name.endswith('_loop')]
        self.assertEqual(len({id(loop) for loop in loops}),1)
        self.assertIn(('received','task-owned observation'),observed)
        self.assertTrue(loops[0].is_closed())


class AwarenessTests(unittest.IsolatedAsyncioTestCase):
    async def test_fullscreen_mode_is_reported_and_explicit_area_does_not_fallback(self):
        class CaptureError(RuntimeError):
            pass
        async def unavailable(**_):
            raise CaptureError('interactive_capture: no_renderer')
        namespace = source_functions('entry_ocr_entries.py', {'study_ocr_snapshot'},
            {'asyncio':asyncio,'Ok':lambda data:data,'Err':lambda error:error,'SdkError':RuntimeError,
             'build_ocr_payload':lambda snapshot:{'status':snapshot.status,'text':snapshot.text},
             'capture_interactive_region':unavailable,'InteractiveCaptureError':CaptureError,
             '_ocr_request_lanlan':lambda args:None,
             '_entry_exception_error':lambda owner,error,**kwargs:{'error':str(error)}})
        captures = []
        def capture():
            captures.append(True)
            return SimpleNamespace(status='ok',text='',captured_at='fixture')
        async def persist():
            pass
        owner = SimpleNamespace(_ocr_pipeline=SimpleNamespace(capture_snapshot=capture),
            _supervision=None,_persist_state=persist)
        full = await namespace['study_ocr_snapshot'](owner,capture_mode='fullscreen')
        self.assertEqual(full['capture_mode_requested'],'fullscreen')
        self.assertEqual(full['capture_mode_used'],'fullscreen')
        area = await namespace['study_ocr_snapshot'](owner,capture_mode='interactive',allow_fullscreen_fallback=False)
        self.assertIn('no_renderer',area['error'])
        self.assertEqual(captures,[True])

    async def test_capture_busy_falls_back_only_when_allowed(self):
        class CaptureError(RuntimeError):
            pass
        async def busy(**_):
            raise CaptureError('interactive_capture: capture_busy')
        namespace = source_functions('entry_ocr_entries.py', {'study_ocr_snapshot'},
            {'asyncio':asyncio,'Ok':lambda data:data,'Err':lambda error:error,'SdkError':RuntimeError,
             'build_ocr_payload':lambda snapshot:{'status':snapshot.status,'text':snapshot.text},
             'capture_interactive_region':busy,'InteractiveCaptureError':CaptureError,
             '_ocr_request_lanlan':lambda args:None,
             '_entry_exception_error':lambda owner,error,**kwargs:{'error':str(error)}})
        captures = []
        def capture():
            captures.append(True)
            return SimpleNamespace(status='ok',text='',captured_at='fixture')
        async def persist():
            pass
        owner = SimpleNamespace(_ocr_pipeline=SimpleNamespace(capture_snapshot=capture),
            _supervision=None,_persist_state=persist)
        fallback = await namespace['study_ocr_snapshot'](owner,capture_mode='interactive')
        self.assertEqual(fallback['capture_mode_requested'],'interactive')
        self.assertEqual(fallback['capture_mode_used'],'fullscreen')
        self.assertEqual(fallback['interactive_fallback_reason'],'capture_busy')
        strict = await namespace['study_ocr_snapshot'](owner,capture_mode='interactive',allow_fullscreen_fallback=False)
        self.assertIn('capture_busy',strict['error'])
        self.assertEqual(captures,[True])

    async def test_plane_bootstrap_is_idempotent_and_timeout_is_bounded(self):
        tree = ast.parse((ROOT/'scripts/neko_lab_runtime_plane.py').read_text(encoding='utf-8'))
        function = next(node for node in tree.body if isinstance(node,ast.AsyncFunctionDef)
                        and node.name == '_ensure_delivery')
        calls = []
        service = SimpleNamespace(_message_plane_runner=None)
        async def start_plane():
            calls.append('plane')
            service._message_plane_runner = object()
        async def subscribe():
            calls.append('subscriptions')
        service._start_message_plane = start_plane
        lifecycle = SimpleNamespace(_service=service,
            start_bridge=lambda:calls.append('bridge'),start_proactive_bridge=lambda:calls.append('proactive'),
            bus_subscription_manager=SimpleNamespace(start=subscribe))
        fake_messaging = ModuleType('plugin.server.messaging')
        fake_messaging.plane_bridge = SimpleNamespace(refresh_ingest_endpoint=lambda:None)
        previous = sys.modules.get('plugin.server.messaging')
        sys.modules['plugin.server.messaging'] = fake_messaging
        namespace = {'asyncio':asyncio,'_gate':asyncio.Lock(),'_ready':False,
                     '_START_TIMEOUT':0.5,'_lifecycle':lifecycle}
        try:
            exec(compile(ast.Module(body=[function],type_ignores=[]),'runtime_plane','exec'),namespace)
            result = await asyncio.gather(namespace['_ensure_delivery'](),namespace['_ensure_delivery']())
            self.assertEqual(result,[True,True])
            self.assertEqual(calls,['plane','bridge','proactive','subscriptions'])
            namespace['_ready'] = False
            namespace['_START_TIMEOUT'] = 0.02
            service._message_plane_runner = None
            async def hang():
                await asyncio.Event().wait()
            service._start_message_plane = hang
            with self.assertRaises(asyncio.TimeoutError):
                await asyncio.wait_for(namespace['_ensure_delivery'](),0.08)
            self.assertFalse(namespace['_ready'])
        finally:
            if previous is None:
                sys.modules.pop('plugin.server.messaging',None)
            else:
                sys.modules['plugin.server.messaging'] = previous

    async def test_sync_watcher_start_runs_outside_the_event_loop(self):
        import inspect
        globals_dict = source_functions('entry_neko_commands.py', {'_subscribe_neko_command_bus'},
            {'asyncio':asyncio,'inspect':inspect,'threading':__import__('threading'),'Any':object,'_NEKO_COMMAND_TOPIC':'neko.study_command'})
        calls = []
        class Watcher:
            def subscribe(self, **_):
                return lambda callback:callback
            def start(self):
                with self_test.assertRaises(RuntimeError):
                    asyncio.get_running_loop()
                calls.append('started')
        self_test = self
        watcher = Watcher()
        messages = SimpleNamespace(watch=lambda *args,**kwargs:watcher)
        async def get_messages(**_):
            return messages
        owner = SimpleNamespace(ctx=SimpleNamespace(bus=SimpleNamespace(messages=SimpleNamespace(get=get_messages))),
            _dispatch_neko_command_messages=lambda *args:None,
            logger=SimpleNamespace(warning=lambda *args:None))
        self.assertTrue(await globals_dict['_subscribe_neko_command_bus'](owner))
        self.assertEqual(calls,['started'])
        self.assertIs(owner._neko_command_watcher,watcher)

    async def test_watcher_finishing_after_timeout_is_stopped(self):
        import inspect
        globals_dict = source_functions('entry_neko_commands.py', {'_subscribe_neko_command_bus'},
            {'asyncio':asyncio,'inspect':inspect,'threading':__import__('threading'),'Any':object,'_NEKO_COMMAND_TOPIC':'neko.study_command'})
        calls = []
        class Watcher:
            def subscribe(self, **_):
                return lambda callback:callback
            def start(self):
                __import__('time').sleep(0.04)
                calls.append('started')
            def stop(self):
                calls.append('stopped')
        watcher = Watcher()
        async def get_messages(**_):
            return SimpleNamespace(watch=lambda *args,**kwargs:watcher)
        owner = SimpleNamespace(ctx=SimpleNamespace(bus=SimpleNamespace(messages=SimpleNamespace(get=get_messages))),
            _dispatch_neko_command_messages=lambda *args:None,logger=SimpleNamespace(warning=lambda *args:None))
        with self.assertRaises(asyncio.TimeoutError):
            await asyncio.wait_for(globals_dict['_subscribe_neko_command_bus'](owner),0.01)
        await asyncio.sleep(0.07)
        self.assertEqual(calls,['started','stopped'])
        self.assertFalse(hasattr(owner,'_neko_command_watcher'))

    async def test_subscription_timeout_degrades_then_retry_recovers(self):
        globals_dict = source_functions('entry_neko_commands.py',
            {'_try_subscribe_neko_commands','_retry_neko_commands'},
            {'asyncio':asyncio,'_SUBSCRIPTION_TIMEOUT_SECONDS':0.02,'_SUBSCRIPTION_RETRY_SECONDS':0.01})
        ready = False
        async def transport():
            return False
        async def bus():
            if ready:
                return True
            await asyncio.Event().wait()
        logs = []
        owner = SimpleNamespace(_event_bus=object(),
            _subscribe_neko_command_transport=transport,_subscribe_neko_command_bus=bus,
            logger=SimpleNamespace(warning=lambda *args:logs.append(args),info=lambda *args:logs.append(args)))
        owner._try_subscribe_neko_commands = lambda:globals_dict['_try_subscribe_neko_commands'](owner)
        self.assertFalse(await asyncio.wait_for(owner._try_subscribe_neko_commands(),0.08))
        ready = True
        await asyncio.wait_for(globals_dict['_retry_neko_commands'](owner),0.08)
        self.assertIn(('study command subscription recovered',),logs)

    async def test_rejected_push_does_not_advance_success_clock(self):
        globals_dict = source_functions('__init__.py', {'_push_awareness_context'},
            {'json':json,'time':__import__('time'),'asyncio':asyncio,'_AWARENESS_OS_TIMEOUT_SECONDS':0.02})
        async def ready(**_):
            return []
        owner = SimpleNamespace(_cfg=SimpleNamespace(awareness=SimpleNamespace(push_to_llm_mode='read')),
            plugin_id='study-fixture',ctx=SimpleNamespace(bus=SimpleNamespace(messages=SimpleNamespace(get=ready))),
            _summary_for_llm=lambda value:value,push_message=lambda **_: {'submitted':False},
            _last_awareness_push_at=123,
            logger=SimpleNamespace(warning=lambda *args,**kwargs:None))
        await globals_dict['_push_awareness_context'](owner,{'activity_type':'study'})
        self.assertEqual(owner._last_awareness_push_at,123)
        self.assertEqual(owner._awareness_push_status,'rejected')

    async def test_unavailable_plane_does_not_accept_or_delay_push_forever(self):
        globals_dict = source_functions('__init__.py', {'_push_awareness_context'},
            {'json':json,'time':__import__('time'),'asyncio':asyncio,'_AWARENESS_OS_TIMEOUT_SECONDS':0.02})
        async def hanging(**_):
            await asyncio.Event().wait()
        accepted = []
        owner = SimpleNamespace(_cfg=SimpleNamespace(awareness=SimpleNamespace(push_to_llm_mode='read')),
            plugin_id='study-fixture',ctx=SimpleNamespace(bus=SimpleNamespace(messages=SimpleNamespace(get=hanging))),
            _summary_for_llm=lambda value:value,push_message=lambda **_:accepted.append(True),
            _last_awareness_push_at=123,logger=SimpleNamespace(warning=lambda *args,**kwargs:None))
        await asyncio.wait_for(globals_dict['_push_awareness_context'](owner,{}),0.08)
        self.assertEqual(accepted,[])
        self.assertEqual(owner._last_awareness_push_at,123)
        self.assertEqual(owner._awareness_push_status,'message_plane_unavailable')

    async def test_hung_os_signal_read_is_bounded_and_cancellation_propagates(self):
        async def hanging(*_,**__):
            await asyncio.Event().wait()
        globals_dict = source_functions('__init__.py', {'_read_awareness_activity_snapshot'},
            {'asyncio':asyncio,'get_os_activity_snapshot':hanging,'_AWARENESS_OS_TIMEOUT_SECONDS':0.02})
        owner = SimpleNamespace(plugin_id='test',_cfg=SimpleNamespace(awareness=SimpleNamespace(os_signals_enabled=True)))
        with self.assertRaises(asyncio.TimeoutError):
            await asyncio.wait_for(globals_dict['_read_awareness_activity_snapshot'](owner,now=1),0.08)
        # The inner timeout should occur well before the observation deadline.
        started = asyncio.get_running_loop().time()
        with self.assertRaises(asyncio.TimeoutError):
            await asyncio.wait_for(globals_dict['_read_awareness_activity_snapshot'](owner,now=1),0.08)
        self.assertLess(asyncio.get_running_loop().time()-started,0.06)
        task = asyncio.create_task(globals_dict['_read_awareness_activity_snapshot'](owner,now=1))
        await asyncio.sleep(0)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task


if __name__ == '__main__':
    unittest.main()
