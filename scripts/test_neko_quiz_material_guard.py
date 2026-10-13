"""Actual quiz entries/context/finalizer and fresh SQLite; local async model only."""
from __future__ import annotations

import ast
import asyncio
from contextlib import asynccontextmanager
import importlib
from pathlib import Path
import sys
import tempfile
import threading
from types import SimpleNamespace
from typing import Any
import unittest
from unittest.mock import AsyncMock
import uuid

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_neko_product_course_memory as memory

materials = importlib.import_module('product_study.study_materials')
models = memory.models
SOURCE = memory.SOURCE / 'entry_tutor_question_entries.py'


class SdkError(Exception):
    def __init__(self, message, code=''):
        super().__init__(message)
        self.code = code


class Err:
    def __init__(self, error):
        self.error = error


tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
names = {'study_generate_question', 'study_generate_targeted_question', '_generate_question_payload'}
nodes = [node for node in tree.body if isinstance(node, (ast.Assign, ast.FunctionDef, ast.AsyncFunctionDef))]
question_class = next(node for node in tree.body if isinstance(node, ast.ClassDef))
for node in question_class.body:
    if getattr(node, 'name', '') in names:
        node.decorator_list = []
        nodes.append(node)
scope = {'Any': Any, 'asyncio': asyncio, 'uuid': uuid, 'TutorReply': models.TutorReply,
         'SdkError': SdkError, 'Err': Err, 'Ok': lambda value: value,
         'public_current_question_payload': models.public_current_question_payload,
         'material_context': materials.material_context,
         'material_context_current': materials.material_context_current,
         'MaterialContextChanged': materials.MaterialContextChanged,
         'LLM_OPERATION_QUESTION_GENERATE': 'question_generate',
         '_validate_optional_vision_image_payload': lambda _self, value, **_: value,
         '_entry_exception_error': lambda _self, error, **_: Err(error)}
exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])), str(SOURCE), 'exec'), scope)


class Harness(memory.ProductHarness):
    _generate_question_payload = scope['_generate_question_payload']
    study_generate_question = scope['study_generate_question']
    study_generate_targeted_question = scope['study_generate_targeted_question']

    def _resolve_active_practice_scope(self):
        return SimpleNamespace(scope_key='one-topic')

    @asynccontextmanager
    async def _practice_scope_write_lock(self):
        yield

    def _build_targeted_question_context(self):
        return {'selected_topic_id': 'course-A::Arrows', 'selected_topic_name': 'Arrows',
                'selection_reason': 'weak_topic', 'question_params': {},
                'scope_key': 'one-topic', 'scope_revision': self._state.practice_scope_revision}


class QuizMaterialGuard(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = memory.Store(Path(self.temp.name) / 'study.db', Path(self.temp.name) / 'unused.json',
                                  memory.logging.getLogger('quiz-material-test'))
        self.store.open()

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    async def prepare(self):
        h = Harness(self.store)
        materials.save_material(self.store, 'course-A', 'image-A', 'source-A: arrows A to B')
        await h._restart_study_session(course_id='course-A')
        h._cfg.llm_vision_enabled = True
        async def question(text, **kwargs):
            return models.TutorReply(operation='question_generate', input_text=text,
                reply='Which direction does the arrow point?', payload={
                    'question': 'Which direction does the arrow point?', 'answer': 'A to B',
                    'reference_answer': 'A to B', 'hint': 'A to B', 'topic': 'Arrows',
                    'key_points': ['arrow direction'], 'rubric': {'correct': 'A to B'}})
        h._agent = SimpleNamespace(question_generate=AsyncMock(side_effect=question))
        return h

    def assert_stale(self, result):
        self.assertIsInstance(result, Err)
        self.assertEqual(result.error.code, 'course_context_changed')

    def rows(self, h):
        return self.store.list_interactions(20, session_id=h._study_session_id)

    async def test_current_image_origin_is_private_persistent_and_not_prompt_binding(self):
        h = await self.prepare()
        expected = materials.material_context(h)
        result = await h.study_generate_question(text=h._state.last_ocr_text, vision_image_base64='image-A',
                                                _material_context=expected)
        self.assertNotIsInstance(result, Err)
        self.assertTrue(result['question_id']); self.assertTrue(result['attempt_id'])
        self.assertEqual(result['hint'], '')
        for key in models.PRIVATE_CURRENT_QUESTION_FIELDS:
            self.assertNotIn(key, result)
        self.assertNotIn('source_material_context', result)
        private = h._state.current_question
        self.assertEqual(private['answer'], 'A to B')
        self.assertEqual(private['internal_private_payload']['source_material_context'], expected)
        rows = self.rows(h)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['metadata']['material_context'], expected)
        self.assertEqual(rows[0]['metadata']['source_material_context'], expected)
        self.assertNotIn('internal_private_payload', rows[0]['metadata']['payload'])
        context = h._agent.question_generate.call_args.kwargs['context']
        self.assertEqual(context['vision_image_base64'], 'image-A')
        prompt = memory.prompts._context_json_for_prompt('question_generate', context)
        self.assertNotIn('_material_context', prompt)
        self.assertNotIn('material_identity', prompt)
        restored = Harness(self.store)
        self.assertEqual(restored._state.current_question['question_id'], result['question_id'])
        self.assertEqual(restored._state.current_question['internal_private_payload']['source_material_context'], expected)
        next_context = await h._build_learning_context('question_generate', input_text='next question')
        next_prompt = memory.prompts._context_json_for_prompt('question_generate', next_context)
        self.assertNotIn('source_material_context', next_prompt)
        self.assertNotIn('material_identity', next_prompt)

    async def test_stale_degraded_model_does_not_set_new_material_error_or_question(self):
        h = await self.prepare(); baseline_error = h._state.last_error
        async def failure(text, **kwargs):
            h._state.last_vision_image_base64 = 'image-B'
            return models.TutorReply(operation='question_generate', input_text=text, reply='failed',
                                    degraded=True, diagnostic='provider_unavailable')
        h._agent.question_generate.side_effect = failure
        result = await h.study_generate_question()
        self.assert_stale(result)
        self.assertEqual(h._state.last_error, baseline_error)
        self.assertEqual(h._state.current_question, {})
        self.assertEqual(self.rows(h), [])

    async def test_stale_request_is_rejected_before_any_ensure_or_model(self):
        h = await self.prepare(); expected = materials.material_context(h)
        h._state.last_vision_image_base64 = 'image-B'
        h._ensure_active_study_session = AsyncMock()
        result = await h.study_generate_question(text='old source', vision_image_base64='image-A',
                                                _material_context=expected)
        self.assert_stale(result)
        h._ensure_active_study_session.assert_not_awaited()
        h._agent.question_generate.assert_not_awaited()
        self.assertEqual(self.rows(h), [])

    async def test_initial_empty_session_can_initialize_but_existing_session_cannot_rebind(self):
        for targeted in (False, True):
            for initially_empty in (False, True):
                with self.subTest(targeted=targeted, initially_empty=initially_empty):
                    h = await self.prepare()
                    if initially_empty:
                        await h._end_study_session_locked()
                    expected = materials.material_context(h, include_material=not targeted)
                    async def restart():
                        return await h._restart_study_session(course_id='course-A')
                    h._ensure_active_study_session = restart
                    # Context receives the resolved session and must not ensure a second time.
                    if targeted:
                        result = await h.study_generate_targeted_question(_material_context=expected)
                    else:
                        result = await h.study_generate_question(text='arrows', vision_image_base64='image-A',
                                                                _material_context=expected)
                    if initially_empty:
                        self.assertNotIsInstance(result, Err)
                        origin = h._state.current_question['internal_private_payload']['source_material_context']
                        self.assertEqual(origin['session_id'], h._study_session_id)
                        self.assertTrue(origin['session_id'])
                    else:
                        self.assert_stale(result)
                        h._agent.question_generate.assert_not_awaited()

    async def test_ensure_cannot_change_course_or_ocr_when_session_was_empty(self):
        for change in ('course', 'ocr'):
            with self.subTest(change=change):
                h = await self.prepare(); await h._end_study_session_locked()
                async def changed_ensure():
                    await h._restart_study_session(course_id='course-B' if change == 'course' else 'course-A')
                    if change == 'ocr': h._state.last_ocr_text = 'different text'
                    return h._study_session_id
                h._ensure_active_study_session = changed_ensure
                result = await h.study_generate_question()
                self.assert_stale(result)
                h._agent.question_generate.assert_not_awaited()
                self.assertEqual(self.rows(h), [])

    async def test_course_session_image_changes_during_build_or_model_reject_before_history(self):
        for phase in ('build', 'model'):
            for change in ('course', 'session', 'image'):
                with self.subTest(phase=phase, change=change):
                    h = await self.prepare(); expected = materials.material_context(h)
                    def replace():
                        if change == 'course': h._state.study_course_id = 'course-B'
                        elif change == 'session': h._study_session_id = 'new-session'
                        else: h._state.last_vision_image_base64 = 'image-B'
                    if phase == 'build':
                        original = h._build_learning_context
                        async def build(*args, **kwargs):
                            context = await original(*args, **kwargs); replace(); return context
                        h._build_learning_context = build
                    else:
                        original = h._agent.question_generate.side_effect
                        async def model(*args, **kwargs):
                            reply = await original(*args, **kwargs); replace(); return reply
                        h._agent.question_generate.side_effect = model
                    result = await h.study_generate_question(text='arrows', vision_image_base64='image-A',
                                                            _material_context=expected)
                    self.assert_stale(result)
                    self.assertEqual(self.store.list_interactions(20, session_id=expected['session_id']), [])
                    self.assertEqual(h._state.current_question, {})
                    self.assertEqual(h._state.recent_learning_events, [])
                    if phase == 'build': h._agent.question_generate.assert_not_awaited()

    async def test_wrong_context_snapshot_is_rejected_even_if_live_material_matches(self):
        h = await self.prepare(); original = h._build_learning_context
        async def mixed(*args, **kwargs):
            context = await original(*args, **kwargs); context['course_id'] = 'wrong-course'; return context
        h._build_learning_context = mixed
        result = await h.study_generate_question(text='immutable source')
        self.assert_stale(result); h._agent.question_generate.assert_not_awaited()

    async def test_async_waiting_model_cannot_replace_new_course_question(self):
        h = await self.prepare(); entered = asyncio.Event(); release = asyncio.Event()
        old_session = h._study_session_id; original = h._agent.question_generate.side_effect
        async def delayed(*args, **kwargs):
            entered.set(); await release.wait(); return await original(*args, **kwargs)
        h._agent.question_generate.side_effect = delayed
        request = asyncio.create_task(h.study_generate_question())
        await asyncio.wait_for(entered.wait(), 2)
        await h._restart_study_session(course_id='course-B')
        held = {'question': 'New course question', 'question_id': 'q-new', 'attempt_id': 'a-new'}
        async with h._lock: h._state.current_question = dict(held)
        release.set(); result = await request
        self.assert_stale(result)
        self.assertEqual(h._state.current_question, held)
        self.assertEqual(self.store.list_interactions(20, session_id=old_session), [])
        self.assertEqual(self.rows(h), [])

    async def test_literal_and_targeted_sources_never_borrow_saved_picture_and_survive_image_only_change(self):
        for targeted in (False, True):
            with self.subTest(targeted=targeted):
                h = await self.prepare(); original = h._agent.question_generate.side_effect
                async def replace_picture(*args, **kwargs):
                    h._state.last_vision_image_base64 = 'image-B'
                    return await original(*args, **kwargs)
                h._agent.question_generate.side_effect = replace_picture
                result = (await h.study_generate_targeted_question() if targeted
                          else await h.study_generate_question(text='immutable source'))
                self.assertNotIsInstance(result, Err)
                context = h._agent.question_generate.call_args.kwargs['context']
                self.assertFalse(context['vision_enabled']); self.assertEqual(context['vision_image_base64'], '')
                self.assertEqual(context['vision_snapshot'], {})
                origin = h._state.current_question['internal_private_payload']['source_material_context']
                self.assertNotIn('material_identity', origin)
                self.assertEqual(len(self.rows(h)), 1)

    async def test_targeted_scope_revision_checks_remain_before_and_inside_finalize_scope(self):
        for phase in ('model', 'scope_lock'):
            with self.subTest(phase=phase):
                h = await self.prepare()
                if phase == 'model':
                    original = h._agent.question_generate.side_effect
                    async def revise(*args, **kwargs):
                        reply = await original(*args, **kwargs); h._state.practice_scope_revision += 1; return reply
                    h._agent.question_generate.side_effect = revise
                else:
                    @asynccontextmanager
                    async def revise_lock():
                        h._state.practice_scope_revision += 1; yield
                    h._practice_scope_write_lock = revise_lock
                result = await h.study_generate_targeted_question()
                self.assertIsInstance(result, Err)
                self.assertEqual(result.error.code, 'SELECTION_SCOPE_CHANGED')
                self.assertEqual(self.rows(h), []); self.assertEqual(h._state.current_question, {})

    async def test_material_change_just_before_actual_sql_commit_writes_nothing(self):
        h = await self.prepare(); original = h._finalize_tutor_call
        async def finalize(*args, **kwargs):
            h._state.last_vision_image_base64 = 'image-B'
            return await original(*args, **kwargs)
        h._finalize_tutor_call = finalize
        result = await h.study_generate_question()
        self.assert_stale(result)
        self.assertEqual(self.rows(h), []); self.assertEqual(h._state.current_question, {})

    async def test_short_sql_commit_is_coordinated_then_late_return_is_rejected_without_deleting_history(self):
        h = await self.prepare(); expected = materials.material_context(h)
        entered = threading.Event(); release = threading.Event()
        original = self.store.append_interaction
        def append(**kwargs):
            entered.set()
            if not release.wait(3): raise RuntimeError('test SQL release missing')
            return original(**kwargs)
        self.store.append_interaction = append
        request = asyncio.create_task(h.study_generate_question())
        self.assertTrue(await asyncio.to_thread(entered.wait, 2))
        async def replace():
            async with h._lock: h._state.last_vision_image_base64 = 'image-B'
        replacement = asyncio.create_task(replace()); await asyncio.sleep(.02)
        self.assertFalse(replacement.done())
        release.set(); result = await request; await replacement
        self.assert_stale(result)
        rows = self.rows(h)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['metadata']['source_material_context'], expected)
        self.assertEqual(h._state.current_question, {})
        self.assertEqual(h._state.recent_learning_events, [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
