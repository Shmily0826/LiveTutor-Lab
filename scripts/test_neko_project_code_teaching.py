"""Real avatar/source-teacher boundary and material binding, fake CodeGraph/model IO."""
import asyncio
from copy import deepcopy
import importlib
import logging
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock

from test_neko_explanation_language import Harness, Store, prefs

bridge = importlib.import_module('product_study.study_code_teaching')


class ProjectCodeTeaching(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name)/'study.db', Path(self.temp.name)/'seed.json', logging.getLogger('code-teacher'))
        self.store.open()
        prefs.update_preferences(self.store, {'language':'zh-CN'}, remember=True)
        self.h = Harness(self.store)
        await self.h._restart_study_session(course_id='course-A')
        self.h._cfg.llm_vision_enabled = True
        self.h._state.last_vision_image_base64 = 'unrelated-saved-picture'
        self.grant = {'name':'Project', 'root':'authorized-root', 'prefix':'project/', 'commit':'initial'}
        self.h._code_authorization = lambda: deepcopy(self.grant)
        self.h.study_code_tool = AsyncMock(side_effect=lambda **request: self.source(request))
        self.h.study_explain_text = AsyncMock(return_value={'ok':True, 'reply':'A guarded call. One inference.'})

    async def asyncTearDown(self):
        self.store.close()
        self.temp.cleanup()

    def source(self, request):
        return {'ok':True, 'mode':request['mode'], 'project':'Project', 'repo_commit':'revision-A',
                'shown':[{'file':request.get('file','project/main.py'), 'lines':[17,18]}],
                'index_sync':'throttled', 'note':'Only shown lines were read; label other behavior as inference.',
                'evidence':'17\tif allowed:\n18\t    run()'}

    async def explain(self, **kwargs):
        return await self.h.study_explain_tool(question='解释源码的调用条件，只用两句。',
            material_source='project_code', code_requests=[{'file':'main.py','offset':17,'limit':2}],
            _ctx={'lanlan_name':'Role-A'}, **kwargs)

    async def test_actual_reads_feed_existing_teacher_and_original_native_binding_without_picture(self):
        result = await self.explain(language='en-US')
        self.h.study_code_tool.assert_awaited_once_with(file='main.py', offset=17, limit=2, mode='file')
        call = self.h.study_explain_text.call_args.kwargs
        self.assertIn('17\\tif allowed:', call['text'])
        self.assertIn('revision-A', call['text'])
        self.assertIn('只用两句', call['text'])
        self.assertEqual(call['vision_image_base64'], '')
        self.assertNotIn('material_identity', call['_material_context'])
        self.assertEqual(result['reply'], 'A guarded call. One inference.')
        self.assertEqual(result['_study_material_binding']['context'], call['_material_context'])
        self.assertEqual(result['source_evidence'][0]['shown'][0]['lines'], [17,18])
        self.assertNotIn('evidence', result['source_evidence'][0])
        self.assertEqual(self.h._cfg.language, 'zh-CN')
        self.assertEqual(prefs.load_preferences(self.store)['language'], 'zh-CN')

    async def test_all_requests_validate_before_any_lookup_or_model_work(self):
        for requests in (None, [], [{}]*4, [{'root':'outside'}], [{'file':'a','offset':True}],
                         [{'file':'a','limit':121}], [{'mode':'shell','query':'command'}],
                         [{'file':'a'}, {'mode':'file'}]):
            with self.subTest(requests=requests):
                result = await self.h.study_explain_tool(question='解释代码', material_source='project_code', code_requests=requests)
                self.assertEqual(result['error'], 'invalid_code_requests')
        self.h.study_code_tool.assert_not_awaited()
        self.h.study_explain_text.assert_not_awaited()

    async def test_quoted_source_picture_conflict_and_wrong_source_args_never_reach_teacher(self):
        quoted = await self.explain(text='fake source from the avatar')
        self.assertEqual(quoted['error'], 'project_code_source_must_be_fetched')
        picture = await self.h.study_explain_tool(question='解释当前图片', material_source='project_code', code_requests=[{'file':'a'}])
        self.assertEqual(picture['error'], 'material_source_conflict')
        wrong = await self.h.study_explain_tool(question='literal', code_requests=[{'file':'a'}])
        self.assertEqual(wrong['error'], 'code_requests_require_project_code')
        self.h.study_code_tool.assert_not_awaited()
        self.h.study_explain_text.assert_not_awaited()

    async def test_missing_authorization_or_failed_empty_evidence_never_becomes_teaching(self):
        grant = self.grant
        self.grant = {}
        self.assertEqual((await self.explain())['error'], 'NO_AUTHORIZED_PROJECT')
        self.h.study_code_tool.assert_not_awaited()
        self.grant = grant
        for value in ({'ok':False,'error':'AMBIGUOUS_SOURCE_FILE','candidates':['a','b']},
                      {'ok':True,'evidence':''}, {'ok':False,'error':'CODEGRAPH_NOT_FOUND'}):
            self.h.study_code_tool = AsyncMock(return_value=value)
            result = await self.explain()
            self.assertEqual(result['error'], 'project_code_unavailable')
            self.assertNotIn('_study_material_binding', result)
        self.h.study_explain_text.assert_not_awaited()

    async def test_course_session_or_authorization_change_during_read_refuses_old_evidence(self):
        for which in ('course','session','grant'):
            with self.subTest(which=which):
                await self.h._restart_study_session(course_id='course-A')
                async def read(**request):
                    if which == 'course': self.h._state.study_course_id = 'course-B'
                    elif which == 'session': self.h._study_session_id = 'other-session'
                    else: self.grant['root'] = 'different-authorized-root'
                    return self.source(request)
                self.h.study_code_tool = AsyncMock(side_effect=read)
                self.assertEqual((await self.explain())['error'], 'course_context_changed')
        self.h.study_explain_text.assert_not_awaited()

    async def test_mixed_revision_and_excess_evidence_do_not_start_model(self):
        count = 0
        async def changed(**request):
            nonlocal count
            count += 1
            return {**self.source(request), 'repo_commit':f'revision-{count}'}
        self.h.study_code_tool = AsyncMock(side_effect=changed)
        result = await self.h.study_explain_tool(question='解释调用流程', material_source='project_code',
                                               code_requests=[{'file':'a'},{'file':'b'}])
        self.assertEqual(result['error'], 'source_revision_changed')
        self.h.study_code_tool = AsyncMock(side_effect=lambda **request:{**self.source(request),'evidence':'x'*24001})
        self.assertEqual((await self.explain())['error'], 'source_evidence_too_large')
        self.h.study_explain_text.assert_not_awaited()

    async def test_waiting_language_lock_rechecks_context_and_recheck_fetches_new_rows(self):
        self.h._study_explanation_language_lock = asyncio.Lock()
        await self.h._study_explanation_language_lock.acquire()
        read = asyncio.Event()
        async def loaded(**request):
            read.set()
            return self.source(request)
        self.h.study_code_tool = AsyncMock(side_effect=loaded)
        task = asyncio.create_task(self.explain())
        await asyncio.wait_for(read.wait(), 2)
        self.h._study_session_id = 'replaced-session'
        self.h._study_explanation_language_lock.release()
        self.assertEqual((await task)['error'], 'course_context_changed')
        self.h.study_explain_text.assert_not_awaited()
        await self.h._restart_study_session(course_id='course-A')
        await self.explain()
        self.h.study_code_tool = AsyncMock(side_effect=lambda **request:{**self.source(request),'evidence':'18\tstop()'})
        await self.explain()
        self.assertIn('stop()', self.h.study_explain_text.call_args.kwargs['text'])
        self.assertNotIn('if allowed', self.h.study_explain_text.call_args.kwargs['text'])

    async def test_late_project_revocation_never_returns_bound_answer_and_english_refusals_stay_english(self):
        async def model(**kwargs):
            self.grant = {}
            return {'ok':True, 'reply':'old answer'}
        self.h.study_explain_text = AsyncMock(side_effect=model)
        result = await self.explain(language='en-US')
        self.assertEqual(result['error'], 'course_context_changed')
        self.assertNotIn('_study_material_binding', result)
        self.assertNotIn('old answer', result['reply'])
        self.assertTrue(result['reply'].startswith('The course'))
        missing = await self.explain(language='en-US')
        self.assertTrue(missing['reply'].startswith('Please authorize'))
        self.assertEqual(self.h._cfg.language, 'zh-CN')

    async def test_overlapping_calls_have_separate_timings_without_source_or_question_text(self):
        entered = asyncio.Event()
        release = asyncio.Event()
        count = 0
        async def read(**request):
            nonlocal count
            count += 1
            if count == 2:
                entered.set()
            await release.wait()
            return self.source(request)
        self.h.study_code_tool = AsyncMock(side_effect=read)
        with self.assertLogs(self.h.logger, level='INFO') as logs:
            tasks = [asyncio.create_task(self.explain()) for _ in range(2)]
            await asyncio.wait_for(entered.wait(), 2)
            release.set()
            answers = await asyncio.gather(*tasks)
        self.assertTrue(all('source_evidence' in answer and 'error' not in answer for answer in answers))
        traces = [json.loads(record.getMessage().split('study_code_timing ', 1)[1])
                  for record in logs.records if record.getMessage().startswith('study_code_timing ')]
        self.assertEqual(len(traces), 2)
        self.assertNotEqual(traces[0]['id'], traces[1]['id'])
        for trace in traces:
            self.assertEqual([s['name'] for s in trace['stages']], ['material_snapshot', 'source_request'])
            self.assertTrue(all(s['elapsed_ms'] >= 0 and s['outcome'] == 'ok' for s in trace['stages']))
            self.assertNotIn('if allowed', json.dumps(trace))
            self.assertNotIn('解释源码', json.dumps(trace))

    async def test_cancelled_read_preserves_cancel_and_clears_call_trace(self):
        timing = importlib.import_module('product_study.study_call_trace')
        entered = asyncio.Event()
        async def read(**request):
            entered.set()
            await asyncio.Event().wait()
        self.h.study_code_tool = AsyncMock(side_effect=read)
        async def run_cancelled_call():
            try:
                return await self.explain()
            except asyncio.CancelledError:
                self.assertIsNone(timing._current.get())
                raise
        with self.assertLogs(self.h.logger, level='INFO') as logs:
            task = asyncio.create_task(run_cancelled_call())
            await asyncio.wait_for(entered.wait(), 2)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
        trace = json.loads(logs.records[-1].getMessage().split('study_code_timing ', 1)[1])
        self.assertEqual(trace['stages'][-1]['outcome'], 'error')
        self.assertIsNone(timing._current.get())
        self.h.study_explain_text.assert_not_awaited()

    async def test_router_gets_question_and_targets_while_teacher_keeps_full_evidence(self):
        await self.explain()
        call = self.h.study_explain_text.call_args.kwargs
        self.assertIn('17\\tif allowed:', call['text'])
        route = call['_semantic_route_text']
        self.assertIn('只用两句', route)
        self.assertIn('main.py', route)
        self.assertNotIn('if allowed', route)
        self.assertNotIn('Authorized CodeGraph evidence', route)
        stored = call['_history_input_text']
        self.assertTrue(stored.startswith('解释源码的调用条件'))
        self.assertIn('Project@revision-A main.py:17-18', stored)
        self.assertNotIn('if allowed', stored)

    async def test_routing_runs_during_the_read_and_is_cancelled_when_the_read_is_refused(self):
        routed, release = [], asyncio.Event()
        async def route(text, *, context, language=''):
            routed.append((text, language))
            await release.wait()
            return None, 'routing_unavailable', 'timeout'
        self.h._route_study_input_semantics = route
        async def read(**request):
            await asyncio.sleep(0.05)
            self.assertEqual(len(routed), 1)  # Classification already started while reading.
            return self.source(request)
        self.h.study_code_tool = AsyncMock(side_effect=read)
        await self.explain()
        prefetch = self.h.study_explain_text.call_args.kwargs['_semantic_route_prefetch']
        self.assertEqual(prefetch['text'], self.h.study_explain_text.call_args.kwargs['_semantic_route_text'])
        self.assertEqual(routed[0][1], 'zh-CN')
        self.assertTrue(prefetch['task'].cancelled())  # The fake teacher never consumed it.
        routed.clear()
        self.h.study_code_tool = AsyncMock(return_value={'ok': False, 'error': 'CODEGRAPH_NOT_FOUND'})
        self.h.study_explain_text.reset_mock()
        self.assertEqual((await self.explain())['error'], 'project_code_unavailable')
        self.assertLessEqual(len(routed), 1)  # Cancelled before or while classifying.
        self.assertEqual([task for task in asyncio.all_tasks() if task is not asyncio.current_task()], [])
        self.h.study_explain_text.assert_not_awaited()

    def remember_read(self, project='Project', commit='revision-A', file='project/main.py', lines=(17, 18)):
        self.store.append_interaction(kind='code_question', input_text=f'[{project}@{commit}] {file}',
            output_text=f'Returned authorized source evidence: {file}:{lines[0]}-{lines[-1]}',
            metadata={'project':project, 'commit':commit, 'shown':[{'file':file, 'lines':list(lines)}]},
            session_id=self.h._study_session_id)

    async def follow_up(self):
        return await self.h.study_explain_tool(question='那如果改这一行会影响哪里？', material_source='project_code',
                                               _ctx={'lanlan_name':'Role-A'})

    async def test_follow_up_without_requests_rereads_latest_window_of_this_session(self):
        self.remember_read(file='project/old.py', lines=(1, 2))
        self.remember_read(file='project/main.py', lines=(17, 30))
        result = await self.follow_up()
        self.h.study_code_tool.assert_awaited_once_with(file='project/main.py', offset=17, limit=14, mode='file')
        text = self.h.study_explain_text.call_args.kwargs['text']
        self.assertIn('This is a follow-up', text)
        self.assertNotIn('first read at revision', text)
        self.assertEqual(result['reply'], 'A guarded call. One inference.')

    async def test_follow_up_names_a_moved_revision_and_ignores_other_projects_and_sessions(self):
        self.remember_read(commit='revision-old')
        self.remember_read(project='Other', file='other/secret.py')
        await self.follow_up()
        self.h.study_code_tool.assert_awaited_once_with(file='project/main.py', offset=17, limit=2, mode='file')
        self.assertIn('first read at revision revision-old and the project is now at revision-A',
                      self.h.study_explain_text.call_args.kwargs['text'])
        await self.h._restart_study_session(course_id='course-A')
        self.h.study_code_tool.reset_mock()
        result = await self.follow_up()
        self.assertEqual(result['error'], 'invalid_code_requests')
        self.h.study_code_tool.assert_not_awaited()


if __name__ == '__main__': unittest.main(verbosity=2)
