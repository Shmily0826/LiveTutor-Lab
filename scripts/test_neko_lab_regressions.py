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
SOURCE = ROOT / 'benchmarks/raw/neko-app/resources/bin/plugin/plugins/study_companion'
BRIDGE_SOURCE = ROOT / 'benchmarks/raw/neko-app/resources/bin/plugins/study_companion'
GOAL_SOURCE = ROOT / 'benchmarks/raw/goal-isolated/study_companion'
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


def source_functions(filename, names, globals_dict, source_root=SOURCE):
    tree = ast.parse((source_root/filename).read_text(encoding='utf-8'))
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

    def test_concept_explain_receives_bounded_session_memory(self):
        context = {
            'study_response_mode':'general_explanation',
            'history':[
                {'kind':'concept_explain','input_text':'material: example 2',
                 'output_text':'previous explanation'},
                {'kind':'answer_evaluate','input_text':'answer 42','output_text':'verdict=wrong'},
            ],
            'last_ocr_text':'example 2 uses the 1/2 factor',
            'last_ocr_at':'2026-10-09T00:00:00Z',
            'current_question':{'question':'differentiate (3x+1)^5','topic':'chain_rule'},
            'last_answer_evaluation':{'verdict':'wrong','score':0,'feedback':'irrelevant'},
            'recent_learning_events':[{'operation':'concept_explain','topic':'substitution'}],
            'vision_image_base64':'never_send_fixture_image',
            'deadline_monotonic':1.0,
        }
        messages = prompts.build_concept_explain_messages(
            text='why is there a 1/2 in example 2',language='zh-CN',mode='companion',context=context)
        user = messages[1]['content']
        self.assertIn('Recent study context',user)
        self.assertIn('example 2 uses the 1/2 factor',user)
        self.assertIn('previous explanation',user)
        self.assertNotIn('never_send_fixture_image',user)
        self.assertIn('Recent study context',messages[0]['content'])
        self.assertEqual(prompts.build_concept_recent_context({}),'')

    def test_concept_recent_context_stays_within_budget(self):
        context = {
            'history':[{'kind':'concept_explain','input_text':'x'*9000,'output_text':'y'*9000}
                       for _ in range(12)],
            'last_ocr_text':'z'*9000,
        }
        block = prompts.build_concept_recent_context(context)
        self.assertTrue(block)
        self.assertLess(len(block),6000)

    def test_session_summary_context_prefers_session_rows(self):
        context = {
            'session_history':[{'kind':'concept_explain','input_text':'material A example 2',
                                'output_text':'explanation of the 1/2 factor'},
                               {'kind':'answer_evaluate','input_text':'asyncio blocking answer',
                                'output_text':'verdict=wrong'}],
            'history':[{'kind':'answer_evaluate','input_text':'legacy chain rule 5x^4',
                        'output_text':'wrong'}],
            'last_ocr_text':'material A',
        }
        messages = prompts.build_summarize_session_messages(
            language='zh-CN',mode='companion',context=context)
        user = messages[1]['content']
        self.assertIn('session_history',user)
        self.assertIn('explanation of the 1/2 factor',user)
        self.assertNotIn('legacy chain rule',user)

    def test_session_summary_falls_back_to_bounded_history(self):
        context = {'history':[{'kind':'concept_explain','input_text':'x'*5000,
                               'output_text':'y'*5000} for _ in range(40)]}
        messages = prompts.build_summarize_session_messages(
            language='en',mode='companion',context=context)
        user = messages[1]['content']
        self.assertIn('history',user)
        self.assertLess(len(user),20000)

    def test_material_grounding_drops_cross_subject_question_params(self):
        fields = ('target_topic_id','target_topic','weak_topics','due_reviews',
                  'retry_wrong_question','candidate_evidence')
        globals_dict = source_functions('entry_tutor_context_support.py',
            {'_drop_cross_subject_question_params'},
            {'_CROSS_SUBJECT_QUESTION_PARAM_FIELDS':fields})
        params = {'target_topic_id':'derivative_chain_rule_application',
                  'target_topic':{'id':'derivative_chain_rule_application'},
                  'weak_topics':[{'topic_id':'derivative_chain_rule_application'}],
                  'due_reviews':[{'topic_id':'derivative_chain_rule_application'}],
                  'retry_wrong_question':{'topic_id':'derivative_chain_rule_application'},
                  'candidate_evidence':[{'id':'e1'}],
                  'suggested_difficulty':3,'prompt_guidance':'recall question'}
        trimmed = globals_dict['_drop_cross_subject_question_params'](params)
        for field in fields:
            value = trimmed[field]
            self.assertIn(value, ('',{},[]),f'{field} still anchors another subject')
        self.assertEqual(trimmed['suggested_difficulty'],3)
        self.assertEqual(params['target_topic_id'],'derivative_chain_rule_application')


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

    async def test_active_window_mode_captures_the_target_and_falls_back_safely(self):
        class CaptureError(RuntimeError):
            pass
        class SdkError(RuntimeError):
            def __init__(self, message, **kwargs):
                super().__init__(message)
                self.code = kwargs.get('code')
        async def _unavailable_capture(**_):
            raise CaptureError('interactive_capture: no_renderer')
        seen_targets = []
        fullscreen_calls = []
        def capture(target=None):
            if target is None:
                fullscreen_calls.append(True)
                return SimpleNamespace(status='ok',text='fullscreen text',captured_at='fixture')
            seen_targets.append(target)
            return SimpleNamespace(status='ok',text='window text',captured_at='fixture')
        def capture_failed(target=None):
            if target is None:
                return SimpleNamespace(status='ok',text='fullscreen text',captured_at='fixture')
            return SimpleNamespace(status='capture_failed',text='',
                                   diagnostic='window_spans_across_primary_and_secondary_monitor',
                                   captured_at='fixture')
        async def persist():
            pass
        async def classify(text, update_empty=False):
            return {'screen_type': 'study'}
        owner = SimpleNamespace(_ocr_pipeline=SimpleNamespace(capture_snapshot=capture),
            _supervision=None,_persist_state=persist,_lock=asyncio.Lock(),
            _state=SimpleNamespace(last_ocr_text='',last_ocr_at=''),
            _update_screen_classification=classify)
        namespace = source_functions('entry_ocr_entries.py', {'study_ocr_snapshot'},
            {'asyncio':asyncio,'Ok':lambda data:data,'Err':lambda error:error,'SdkError':SdkError,
             'build_ocr_payload':lambda snapshot:{'status':snapshot.status,'text':snapshot.text},
             'capture_interactive_region':_unavailable_capture,'InteractiveCaptureError':CaptureError,
             '_ocr_request_lanlan':lambda args:None,
             '_entry_exception_error':lambda owner,error,**kwargs:{'error':str(error)}})

        target_fixture = {'title':'NEKO-LAB material','left':0,'top':0,'right':2880,'bottom':1800}
        namespace['_foreground_window_target'] = lambda: target_fixture
        hit = await namespace['study_ocr_snapshot'](owner,capture_mode='active_window')
        self.assertEqual(hit['capture_mode_requested'],'active_window')
        self.assertEqual(hit['capture_mode_used'],'active_window')
        self.assertEqual(hit['capture_target_title'],'NEKO-LAB material')
        self.assertEqual(seen_targets,[target_fixture])
        self.assertEqual(fullscreen_calls,[])

        namespace['_foreground_window_target'] = lambda: None
        missed = await namespace['study_ocr_snapshot'](owner,capture_mode='active_window')
        self.assertEqual(missed['capture_mode_used'],'fullscreen')
        self.assertEqual(missed['active_window_fallback_reason'],'no_usable_foreground_window')
        self.assertEqual(fullscreen_calls,[True])

        strict = await namespace['study_ocr_snapshot'](owner,capture_mode='active_window',
                                                       allow_fullscreen_fallback=False)
        self.assertIn('no_usable_foreground_window',str(strict))

        owner._ocr_pipeline = SimpleNamespace(capture_snapshot=capture_failed)
        namespace['_foreground_window_target'] = lambda: {'title':'spans monitors',
                                                          'left':0,'top':0,'right':2880,'bottom':1800}
        degraded = await namespace['study_ocr_snapshot'](owner,capture_mode='active_window')
        self.assertEqual(degraded['capture_mode_used'],'fullscreen')
        self.assertEqual(degraded['active_window_fallback_reason'],'active_window_capture_failed')
        self.assertIn('spans',degraded['active_window_capture_detail'])

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
        owner = SimpleNamespace(_cfg=SimpleNamespace(communication=SimpleNamespace(silent_mode=False),
                awareness=SimpleNamespace(push_to_llm_mode='read')),
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
        owner = SimpleNamespace(_cfg=SimpleNamespace(communication=SimpleNamespace(silent_mode=False),
                awareness=SimpleNamespace(push_to_llm_mode='read')),
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


class SessionMuteQualityTests(unittest.TestCase):
    def test_proactive_silence_is_default_and_can_be_reversed(self):
        self.assertTrue(models.build_config({}).communication.silent_mode)
        self.assertTrue(models.build_config({
            'study_companion': {'communication': {'enabled': True}}
        }).communication.silent_mode)
        self.assertFalse(models.build_config({
            'study_companion': {
                'communication': {'enabled': True, 'silent_mode': False}
            }
        }).communication.silent_mode)

    def test_silent_mode_blocks_awareness_push_before_provider_call(self):
        calls = []
        namespace = source_functions(
            '__init__.py', {'_push_awareness_context'}, {'time': __import__('time')},
        )
        owner = SimpleNamespace(
            _cfg=SimpleNamespace(
                communication=SimpleNamespace(silent_mode=True),
                awareness=SimpleNamespace(push_to_llm_mode='respond'),
            ),
            push_message=lambda **kwargs: calls.append(kwargs),
            logger=SimpleNamespace(warning=lambda *_args, **_kwargs: None),
        )
        asyncio.run(namespace['_push_awareness_context'](owner, {}))
        self.assertEqual(calls, [])

    def test_silent_mode_blocks_event_bus_output_channel(self):
        from study_fixture._event_bus import StudyEvent, StudyEventBus
        calls = []
        bus = StudyEventBus(
            plugin_ctx=SimpleNamespace(push_message=lambda **kwargs: calls.append(kwargs)),
            silent_mode=True,
        )
        async def run():
            await bus.emit(StudyEvent(name='review_due', payload={}))
            await bus._emit_open(StudyEvent(name='review_due', payload={}))
        asyncio.run(run())
        self.assertEqual(calls, [])
        self.assertEqual(bus.block_count, 2)

    def test_silent_mode_blocks_direct_command_message(self):
        calls = []
        namespace = source_functions(
            'entry_neko_commands.py', {'_push_neko_command_message'},
            {'inspect': __import__('inspect')},
        )
        owner = SimpleNamespace(
            _cfg=SimpleNamespace(communication=SimpleNamespace(silent_mode=True)),
            ctx=SimpleNamespace(push_message=lambda **kwargs: calls.append(kwargs)),
        )
        asyncio.run(namespace['_push_neko_command_message'](
            owner, visibility=['chat'], ai_behavior='respond', priority=1,
            text='should stay silent',
        ))
        self.assertEqual(calls, [])

    def test_silence_survives_plugin_reinstantiation_and_all_output_paths(self):
        from study_fixture._event_bus import StudyEvent, StudyEventBus
        calls = []
        for _reload in range(2):
            cfg = models.build_config({'study_companion': {'communication': {'enabled': True}}})
            bus = StudyEventBus(
                plugin_ctx=SimpleNamespace(push_message=lambda **kwargs: calls.append(kwargs)),
                silent_mode=cfg.communication.silent_mode,
            )
            asyncio.run(bus.emit(StudyEvent(name='review_due', payload={})))
            asyncio.run(bus._emit_open(StudyEvent(name='solution_completed', payload={})))
            awareness_entries = (
                (SOURCE, '__init__.py'),
                (SOURCE, 'lab_entry.py'),
                (BRIDGE_SOURCE, '__init__.py'),
                (GOAL_SOURCE, '__init__.py'),
            )
            for source_root, filename in awareness_entries:
                message_plane_reads = []
                async def ready(**_kwargs):
                    message_plane_reads.append(True)
                    return []
                awareness = source_functions(
                    filename, {'_push_awareness_context'},
                    {'time': __import__('time'), 'json': json, 'asyncio': asyncio,
                     '_AWARENESS_OS_TIMEOUT_SECONDS': 0.02},
                    source_root=source_root,
                )['_push_awareness_context']
                owner = SimpleNamespace(
                    _cfg=cfg,
                    ctx=SimpleNamespace(bus=SimpleNamespace(
                        messages=SimpleNamespace(get=ready),
                    )),
                    plugin_id='study-fixture',
                    push_message=lambda **kwargs: calls.append(kwargs),
                    _summary_for_llm=lambda value: value,
                    logger=SimpleNamespace(warning=lambda *_args, **_kwargs: None),
                )
                asyncio.run(awareness(owner, {}))
                self.assertEqual(message_plane_reads, [], f'{source_root.name}/{filename} reached message plane')
            command = source_functions(
                'entry_neko_commands.py', {'_push_neko_command_message'},
                {'inspect': __import__('inspect')},
            )['_push_neko_command_message']
            command_owner = SimpleNamespace(
                _cfg=cfg,
                ctx=SimpleNamespace(push_message=lambda **kwargs: calls.append(kwargs)),
            )
            asyncio.run(command(
                command_owner, visibility=['chat'], ai_behavior='respond', priority=1,
                text='must remain silent after reload',
            ))
        self.assertEqual(calls, [])

    def test_non_silent_configuration_restores_normal_message_paths(self):
        from study_fixture._event_bus import StudyEvent, StudyEventBus
        calls = []
        cfg = models.build_config({
            'study_companion': {'communication': {'enabled': True, 'silent_mode': False}}
        })
        bus = StudyEventBus(
            plugin_ctx=SimpleNamespace(push_message=lambda **kwargs: calls.append(kwargs)),
            silent_mode=cfg.communication.silent_mode,
        )
        asyncio.run(bus._emit_open(StudyEvent(name='review_due', payload={})))

        async def ready(**_kwargs):
            return []
        awareness = source_functions(
            '__init__.py', {'_push_awareness_context'},
            {'time': __import__('time'), 'json': json, 'asyncio': asyncio,
             '_AWARENESS_OS_TIMEOUT_SECONDS': 0.02},
        )['_push_awareness_context']
        asyncio.run(awareness(SimpleNamespace(
            _cfg=cfg,
            ctx=SimpleNamespace(bus=SimpleNamespace(messages=SimpleNamespace(get=ready))),
            plugin_id='study-fixture',
            push_message=lambda **kwargs: calls.append(kwargs),
            _summary_for_llm=lambda value: value,
            logger=SimpleNamespace(warning=lambda *_args, **_kwargs: None),
        ), {}))

        command = source_functions(
            'entry_neko_commands.py', {'_push_neko_command_message'},
            {'inspect': __import__('inspect'), 'Err': type('Err', (), {})},
        )['_push_neko_command_message']
        asyncio.run(command(
            SimpleNamespace(
                _cfg=cfg,
                ctx=SimpleNamespace(push_message=lambda **kwargs: calls.append(kwargs)),
            ), visibility=['chat'], ai_behavior='respond', priority=1,
            text='normal messages restored',
        ))
        self.assertEqual(len(calls), 3)

    def test_concurrent_session_open_and_idle_rollover_are_serialized(self):
        import time
        import uuid
        from types import MethodType
        namespace = source_functions(
            '__init__.py', {
                '_ensure_active_study_session',
                '_start_study_session_locked',
                '_end_study_session_locked',
                '_restart_study_session',
            },
            {'time': time, 'uuid': uuid, 'asyncio': asyncio},
        )
        created = []
        ended = []
        async def persist():
            return None
        owner = SimpleNamespace(
            _study_session_lock=asyncio.Lock(), _lock=asyncio.Lock(),
            _study_session_id='', _study_session_last_activity=0.0,
            _state=SimpleNamespace(
                active_mode='teaching', study_session_id='', session_summary_seed={},
                recent_learning_events=[], current_question={},
                last_answer_evaluation={}, last_ocr_text='', last_ocr_at='',
                last_session_summary='', last_session_summary_at='',
            ),
            _cfg=SimpleNamespace(mode='teaching'),
            _store=SimpleNamespace(
                ensure_session=lambda **kwargs: created.append(kwargs['session_id']),
                end_session=lambda **kwargs: ended.append(kwargs['session_id']),
            ),
            _persist_state=persist,
        )
        for name in ('_start_study_session_locked', '_end_study_session_locked'):
            setattr(owner, name, MethodType(namespace[name], owner))
        async def run():
            first = await asyncio.gather(*[
                namespace['_ensure_active_study_session'](owner) for _ in range(12)
            ])
            old_id = first[0]
            owner._study_session_last_activity = time.time() - 1801
            second = await asyncio.gather(*[
                namespace['_ensure_active_study_session'](owner) for _ in range(12)
            ])
            restarted = await asyncio.gather(*[
                namespace['_restart_study_session'](owner) for _ in range(6)
            ])
            return first, second, restarted, old_id
        first, second, restarted, old_id = asyncio.run(run())
        self.assertEqual(len(set(first)), 1)
        self.assertEqual(len(set(second)), 1)
        self.assertNotEqual(second[0], old_id)
        self.assertEqual(len(set(restarted)), 6)
        self.assertEqual(created, [old_id, second[0], *restarted])
        self.assertIn(old_id, ended)
        self.assertIn(second[0], ended)
        self.assertEqual(len(ended), 7)

    def test_interaction_persists_the_request_session_after_active_session_changes(self):
        captured = []
        async def append_interaction(_store, **kwargs):
            captured.append(kwargs['session_id'])
        async def await_completion(awaitable, **_kwargs):
            await awaitable
        async def noop(*_args, **_kwargs):
            return None
        async def no_tracking(*_args, **_kwargs):
            return {}
        namespace = source_functions(
            'entry_tutor_context_support.py', {'_finalize_tutor_call'},
            {
                '_TutorFinalizeProgress': lambda: object(),
                '_append_interaction_cancel_safe': append_interaction,
                '_await_completion_on_cancel': await_completion,
                'build_tutor_payload': lambda reply: {'reply': reply.reply},
                'LLM_OPERATION_SUMMARIZE_SESSION': 'summarize_session',
            },
        )
        owner = SimpleNamespace(
            _store=object(), _cfg=SimpleNamespace(history_limit=20),
            _record_tutor_result=noop, _track_learning=no_tracking,
            _persist_state=noop, _study_session_id='study-new',
        )
        reply = SimpleNamespace(
            degraded=False, diagnostic='', operation='concept_explain',
            input_text='why', reply='because', created_at='2026-10-09T00:00:00Z',
        )
        asyncio.run(namespace['_finalize_tutor_call'](
            owner, 'concept_explain', reply, history_kind='concept_explain',
            metadata={}, extra_context={'session_id': 'study-request-start'},
        ))
        self.assertEqual(captured, ['study-request-start'])

    def test_programming_topics_are_not_defaulted_to_math(self):
        markers = (
            'python', 'asyncio', 'time.sleep', 'async', 'coroutine',
            'event loop', '事件循环', '协程', '同步阻塞', '代码', 'programming',
        )
        namespace = source_functions(
            'entry_tutor_context_support.py', {'_infer_topic_subject'},
            {'_COMPUTER_SCIENCE_MARKERS': markers},
        )
        infer = namespace['_infer_topic_subject']
        self.assertEqual(infer('Python asyncio', 'time.sleep blocks'), 'computer_science')
        self.assertEqual(infer('不定积分换元法', '∫f(g(x))g\'dx'), 'math')
        self.assertEqual(infer('general', 'question'), '')

    def test_answer_tracking_keeps_the_request_session_id_for_qa(self):
        captured = []
        namespace = source_functions(
            'entry_tutor_context_support.py', {'_record_answer_knowledge'},
            {
                'asyncio': asyncio,
                '_infer_topic_subject': lambda *_: 'computer_science',
                '_detect_mastery_threshold_crossed': lambda *_: False,
            },
        )
        # The production function dispatches this synchronous Store call via to_thread.
        class Tracker:
            def get_mastery(self, _topic):
                return 0.5
            def on_answer(self, **kwargs):
                captured.append(kwargs)
                return {'topic_id': kwargs['topic_id']}
        async def run():
            owner = SimpleNamespace(
                _knowledge_tracker=Tracker(),
                _state=SimpleNamespace(active_mode='teaching'),
                _event_bus=None,
                _invalidate_knowledge_guidance_cache=lambda: None,
                logger=SimpleNamespace(warning=lambda *_args, **_kwargs: None),
            )
            eval_reply = SimpleNamespace(
                input_text='asyncio blocks here',
                payload={'topic': 'python_asyncio', 'verdict': 'wrong', 'score': 0},
            )
            track_reply = SimpleNamespace(payload={'topic': 'python_asyncio'})
            return await namespace['_record_answer_knowledge'](
                owner, eval_reply, track_reply,
                extra_context={
                    'session_id': 'study-request-start', 'question': 'Why does asyncio block?',
                    'answer': 'time.sleep blocks', 'expected_answer': 'use await',
                    'mode': 'teaching', 'question_payload': {'topic': 'python_asyncio'},
                },
            )
        asyncio.run(run())
        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0]['session_id'], 'study-request-start')

    def test_session_store_counts_answers_and_closes_persisted_session(self):
        import os
        import sqlite3
        import tempfile
        import threading
        import uuid
        from typing import Any

        fd, db_path = tempfile.mkstemp(prefix='neko-session-store-', suffix='.sqlite')
        os.close(fd)
        self.addCleanup(lambda: os.path.exists(db_path) and os.remove(db_path))
        db = sqlite3.connect(db_path)
        db.row_factory = sqlite3.Row
        self.addCleanup(lambda: db.close())
        db.executescript("""
            CREATE TABLE sessions (
                id TEXT PRIMARY KEY, mode TEXT NOT NULL,
                started_at TEXT NOT NULL DEFAULT (datetime('now')), ended_at TEXT,
                duration_minutes REAL, question_count INTEGER DEFAULT 0,
                topics_touched TEXT NOT NULL DEFAULT '[]', summary_markdown TEXT,
                notes_exported INTEGER DEFAULT 0
            );
            CREATE TABLE qa_records (
                id INTEGER PRIMARY KEY, session_id TEXT NOT NULL, topic_id TEXT,
                question TEXT, user_answer TEXT, eval_result TEXT, mode TEXT,
                response_time_ms INTEGER, created_at TEXT
            );
        """)

        def loads(value, fallback):
            try:
                return json.loads(value)
            except (TypeError, ValueError):
                return fallback

        namespace = source_functions(
            'store_qa.py',
            {'ensure_session', 'end_session', 'add_qa_record', 'list_sessions'},
            {'Any': Any, 'uuid': uuid, '_DEFAULT_APPEND_ONLY_HISTORY_LIMIT': 100,
             'safe_float': lambda value, fallback=0.0: float(value) if value is not None else fallback,
             'safe_int': lambda value, fallback=0: int(value) if value is not None else fallback},
        )
        store = SimpleNamespace(
            _lock=threading.RLock(), _require_conn=lambda: db,
            _require_read_conn=lambda: db, _json_dumps=lambda value: json.dumps(value),
            _json_loads=loads, _trim_append_only_rows=lambda *args, **kwargs: None,
        )
        namespace['ensure_session'](store, session_id='study-stable', mode='teaching')
        for _ in range(2):
            namespace['add_qa_record'](
                store, session_id='study-stable', topic_id='python_asyncio',
                question={'question': 'why does time.sleep block'},
                user_answer='blocks the event loop', eval_result={'score': 100},
                mode='teaching',
            )
        row = namespace['list_sessions'](store, 10)[0]
        self.assertEqual(row['id'], 'study-stable')
        self.assertEqual(row['question_count'], 2)
        self.assertEqual(row['topics_touched'], ['python_asyncio'])
        namespace['end_session'](store, session_id='study-stable', summary='asyncio')
        row = namespace['list_sessions'](store, 10)[0]
        self.assertTrue(row['ended_at'])
        self.assertEqual(row['summary_markdown'], 'asyncio')
        db.close()
        db = sqlite3.connect(db_path)
        db.row_factory = sqlite3.Row
        row = db.execute('SELECT * FROM sessions WHERE id=?', ('study-stable',)).fetchone()
        self.assertIsNotNone(row['ended_at'])
        self.assertEqual(row['question_count'], 2)

    def test_old_interaction_rows_survive_the_real_additive_schema_helper(self):
        import os
        import re
        import sqlite3
        import tempfile

        fd, db_path = tempfile.mkstemp(prefix='neko-migration-', suffix='.sqlite')
        os.close(fd)
        self.addCleanup(lambda: os.path.exists(db_path) and os.remove(db_path))
        db = sqlite3.connect(db_path)
        db.row_factory = sqlite3.Row
        self.addCleanup(lambda: db.close())
        db.execute('CREATE TABLE interactions (id INTEGER PRIMARY KEY, kind TEXT, input_text TEXT, output_text TEXT, metadata TEXT, created_at REAL)')
        db.execute("INSERT INTO interactions VALUES (1, 'legacy', 'old q', 'old a', '{}', 1.0)")
        db.commit()
        namespace = source_functions(
            'store_schema.py',
            {'_ensure_column', '_validate_sql_identifier', '_validate_column_definition'},
            {
                're': re,
                '_SQL_IDENT_RE': re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$'),
                '_COLUMN_DEFINITION_ALLOWLIST': {'TEXT', "TEXT NOT NULL DEFAULT ''", "TEXT NOT NULL DEFAULT '[]'"},
            },
        )
        namespace['_ensure_column'](db, 'interactions', 'session_id', 'TEXT')
        namespace['_ensure_column'](db, 'interactions', 'session_id', 'TEXT')
        db.commit()
        legacy = db.execute('SELECT * FROM interactions WHERE id=1').fetchone()
        self.assertEqual((legacy['kind'], legacy['input_text'], legacy['output_text']), ('legacy', 'old q', 'old a'))
        self.assertIsNone(legacy['session_id'])
        db.close()
        db = sqlite3.connect(db_path)
        db.row_factory = sqlite3.Row
        legacy = db.execute('SELECT * FROM interactions WHERE id=1').fetchone()
        self.assertEqual(legacy['input_text'], 'old q')
        self.assertIsNone(legacy['session_id'])
        db.close()

    def test_restart_closes_only_new_study_sessions_and_preserves_legacy_rows(self):
        import sqlite3
        import threading
        import uuid
        from typing import Any

        db = sqlite3.connect(':memory:')
        db.row_factory = sqlite3.Row
        db.executescript("""
            CREATE TABLE sessions (
                id TEXT PRIMARY KEY, mode TEXT NOT NULL,
                started_at TEXT NOT NULL DEFAULT (datetime('now')),
                ended_at TEXT, duration_minutes REAL,
                question_count INTEGER DEFAULT 0,
                topics_touched TEXT NOT NULL DEFAULT '[]', summary_markdown TEXT,
                notes_exported INTEGER DEFAULT 0
            );
        """)
        namespace = source_functions(
            'store_qa.py', {'ensure_session', 'close_open_sessions'},
            {'Any': Any, 'uuid': uuid, '_DEFAULT_APPEND_ONLY_HISTORY_LIMIT': 100,
             'safe_float': float, 'safe_int': int},
        )
        store = SimpleNamespace(_lock=threading.RLock(), _require_conn=lambda: db)
        db.execute("INSERT INTO sessions(id,mode) VALUES('legacy-run-123','teaching')")
        db.execute("INSERT INTO sessions(id,mode) VALUES('study-legacy-123','teaching')")
        historical_valid_id = 'study-' + ('b' * 32)
        db.execute("INSERT INTO sessions(id,mode) VALUES(?, 'teaching')", (historical_valid_id,))
        namespace['ensure_session'](store, session_id='study-' + ('a' * 32), mode='teaching')
        namespace['close_open_sessions'](store, session_id='study-' + ('a' * 32))
        rows = {row['id']: row for row in db.execute('SELECT * FROM sessions')}
        self.assertIsNone(rows['legacy-run-123']['ended_at'])
        self.assertIsNone(rows['study-legacy-123']['ended_at'])
        self.assertIsNone(rows[historical_valid_id]['ended_at'])
        self.assertTrue(rows['study-' + ('a' * 32)]['ended_at'])

    def test_full_credit_is_incompatible_with_missing_rubric_points(self):
        namespace = source_functions(
            'tutor_llm_agent_answer_evaluate.py', {'_normalize_evaluation'},
            {
                '_ANSWER_VERDICTS': {'correct', 'partial', 'wrong', 'dont_know'},
                '_as_str': lambda value, fallback='': str(value if value is not None else fallback),
                '_as_list': lambda value: value if isinstance(value, list) else [],
                '_clamp_int': lambda value, low, high, fallback: max(low, min(high, int(value))) if value is not None else fallback,
            },
        )
        owner = SimpleNamespace(
            _fallback_feedback=lambda *_: 'feedback',
            _fallback_next_action=lambda *_: 'next',
            _screen_type_from_context=lambda *_: 'study',
            _verdict_from_score=lambda *_args, **_kwargs: 'wrong',
        )
        result = namespace['_normalize_evaluation'](
            owner,
            {'score': 100, 'verdict': 'correct', 'error_type': 'none',
             'feedback': 'correct but omits du', 'missing_points': ['du = g\'(x)dx'],
             'covered_points': ['result']},
            {'answer': 'integral result', 'expected_answer': 'integral result'},
        )
        self.assertEqual((result['verdict'], result['score']), ('partial', 80))
        self.assertFalse(result['final_answer_correct'])

    def test_wrong_core_mechanism_cannot_keep_twenty_percent_without_credit(self):
        namespace = source_functions(
            'tutor_llm_agent_answer_evaluate.py', {'_normalize_evaluation'},
            {
                '_ANSWER_VERDICTS': {'correct', 'partial', 'wrong', 'dont_know'},
                '_as_str': lambda value, fallback='': str(value if value is not None else fallback),
                '_as_list': lambda value: value if isinstance(value, list) else [],
                '_clamp_int': lambda value, low, high, fallback: max(low, min(high, int(value))) if value is not None else fallback,
            },
        )
        owner = SimpleNamespace(
            _fallback_feedback=lambda *_: 'feedback',
            _fallback_next_action=lambda *_: 'next',
            _screen_type_from_context=lambda *_: 'study',
            _verdict_from_score=lambda *_args, **_kwargs: 'wrong',
        )
        result = namespace['_normalize_evaluation'](
            owner,
            {'score': 20, 'verdict': 'wrong', 'error_type': 'misconception',
             'feedback': 'wrong mechanism', 'missing_points': ['blocks current thread'],
             'misconceptions': ['starts new thread'], 'covered_points': []},
            {'answer': 'starts a new thread'},
        )
        self.assertEqual((result['verdict'], result['score']), ('wrong', 10))

    def test_failed_startup_session_end_error_does_not_skip_later_cleanup(self):
        namespace = source_functions(
            '__init__.py', {'_cleanup_after_failed_startup'},
            {'asyncio': asyncio},
        )
        calls = []

        class DocumentJobs:
            async def shutdown(self):
                calls.append('document_jobs')

        async def fail_session_end():
            calls.append('session_end')
            raise RuntimeError('fixture session persistence failure')

        async def no_op(*_args, **_kwargs):
            calls.append('async_cleanup')

        def async_marker(name):
            async def mark():
                calls.append(name)
            return mark

        owner = SimpleNamespace(
            _document_jobs=DocumentJobs(),
            _study_session_id='study-fixture',
            _end_study_session=fail_session_end,
            _cancel_command_worker=async_marker('commands'),
            _cancel_review_due_task=async_marker('review_task'),
            _cancel_study_idle_task=no_op,
            _cancel_pomodoro_watcher=async_marker('pomodoro'),
            stop_awareness_loop=lambda: calls.append('stop_awareness'),
            _await_awareness_stop=no_op,
            _unsubscribe_neko_commands=no_op,
            _event_bus=None,
            _agent=SimpleNamespace(shutdown=async_marker('agent')),
            _ocr_pipeline=SimpleNamespace(close=lambda: calls.append('ocr')),
            _store=SimpleNamespace(close=lambda: calls.append('store_close')),
            clear_list_actions=lambda: None,
            unregister_dynamic_entry=lambda *_: None,
            _static_ui_config=None,
            logger=SimpleNamespace(warning=lambda *_args, **_kwargs: calls.append('warning')),
        )
        asyncio.run(namespace['_cleanup_after_failed_startup'](owner))
        self.assertLess(calls.index('session_end'), calls.index('store_close'))
        self.assertIn('warning', calls)
        self.assertIn('commands', calls)
        self.assertIn('agent', calls)
        self.assertIn('ocr', calls)
        self.assertIn('store_close', calls)

    def test_shutdown_session_end_error_does_not_skip_later_cleanup(self):
        namespace = source_functions(
            '__init__.py', {'shutdown'},
            {'asyncio': asyncio, 'Ok': lambda value: value, 'STATUS_STOPPED': 'stopped'},
        )
        calls = []

        class AsyncLock:
            async def __aenter__(self):
                return self
            async def __aexit__(self, *_args):
                return False

        class DocumentJobs:
            async def shutdown(self):
                calls.append('document_jobs')

        class Store:
            def save_state(self, _state):
                calls.append('save_state')
            def close(self):
                calls.append('store_close')

        async def fail_session_end():
            calls.append('session_end')
            raise RuntimeError('fixture session persistence failure')

        async def no_op(*_args, **_kwargs):
            calls.append('async_cleanup')

        def async_marker(name):
            async def mark():
                calls.append(name)
            return mark

        owner = SimpleNamespace(
            _cancel_study_idle_task=no_op,
            _study_session_id='study-fixture',
            _end_study_session=fail_session_end,
            _document_jobs=DocumentJobs(),
            stop_awareness_loop=lambda: calls.append('stop_awareness'),
            _await_awareness_stop=no_op,
            _unsubscribe_neko_commands=async_marker('unsubscribe'),
            _cancel_command_worker=async_marker('commands'),
            _cancel_review_due_task=async_marker('review_task'),
            _cancel_pomodoro_watcher=async_marker('pomodoro'),
            _event_bus=None,
            unregister_dynamic_entry=lambda *_: None,
            _agent=SimpleNamespace(shutdown=async_marker('agent')),
            _ocr_pipeline=SimpleNamespace(close=lambda: calls.append('ocr')),
            _lock=AsyncLock(),
            _state=SimpleNamespace(status='ready'),
            _store=Store(),
            logger=SimpleNamespace(warning=lambda *_args, **_kwargs: calls.append('warning')),
        )
        asyncio.run(namespace['shutdown'](owner))
        self.assertIn('warning', calls)
        self.assertIn('document_jobs', calls)
        self.assertIn('commands', calls)
        self.assertIn('agent', calls)
        self.assertIn('ocr', calls)
        self.assertIn('store_close', calls)


if __name__ == '__main__':
    class EvidenceResult(unittest.TextTestResult):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.case_results = []

        def addSuccess(self, test):
            super().addSuccess(test)
            self.case_results.append({'test': test.id(), 'pass': True})

        def addFailure(self, test, err):
            super().addFailure(test, err)
            self.case_results.append({'test': test.id(), 'pass': False, 'kind': 'failure'})

        def addError(self, test, err):
            super().addError(test, err)
            self.case_results.append({'test': test.id(), 'pass': False, 'kind': 'error'})

    class EvidenceRunner(unittest.TextTestRunner):
        resultclass = EvidenceResult

    suite = (
        unittest.defaultTestLoader.loadTestsFromNames(sys.argv[1:], sys.modules[__name__])
        if len(sys.argv) > 1
        else unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    )
    result = EvidenceRunner(verbosity=1).run(suite)
    evidence_path = ROOT / 'benchmarks/raw/evidence/neko-goal-isolated-python-unit.json'
    evidence_path.write_text(json.dumps({
        'evidence_kind': 'ISOLATED_PYTHON_UNIT',
        'runtime': 'workspace-bundled CPython 3.11.15, -I -S; no host imports/provider calls',
        'tests_run': result.testsRun,
        'all_pass': result.wasSuccessful(),
        'checks': result.case_results,
    }, indent=2) + '\n', encoding='utf-8')
    sys.exit(not result.wasSuccessful())
