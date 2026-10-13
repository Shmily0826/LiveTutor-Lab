"""Actual summary entry/context/finalizer, fresh SQLite, fake model; no host/audio."""
import asyncio
from copy import deepcopy
import logging
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock

import test_neko_product_course_memory as product
from test_neko_image_course_guard import product_method, EntryError, StudyError

materials = product.materials
ENTRY = product.SOURCE / 'entry_tutor_summary_entries.py'
scope = {'asyncio': asyncio, 'Err': EntryError, 'Ok': lambda value: value,
         'SdkError': StudyError, 'LLM_OPERATION_SUMMARIZE_SESSION': 'summarize_session',
         'material_context': materials.material_context,
         'material_context_current': materials.material_context_current,
         'MaterialContextChanged': materials.MaterialContextChanged}
summary = product_method(ENTRY, 'study_summarize_session', scope)


class Harness(product.ProductHarness):
    study_summarize_session = summary

    def __init__(self, store):
        super().__init__(store)
        self.model_inputs = []
        async def model(history, *, mode, context):
            self.model_inputs.append((deepcopy(history), deepcopy(context)))
            return product.models.TutorReply(
                operation='summarize_session', input_text='session', reply='Original lesson summary',
                payload={'summary': 'Original lesson summary', 'markdown': 'Original notes'})
        self._agent = SimpleNamespace(summarize_session=AsyncMock(side_effect=model))
        self._emit_session_summarized_event = AsyncMock()


class SummaryMaterialGuard(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='neko-summary-guard-')
        self.store = product.Store(Path(self.temp.name) / 'study.db',
                                   Path(self.temp.name) / 'unused.json', logging.getLogger('summary-guard'))
        self.store.open()
        self.h = Harness(self.store)
        self.session = await self.h._restart_study_session(course_id='course-A')
        for text, result in [('return always produces 5', 'wrong: missing return yields None'),
                             ('return explicitly sends the result', 'correct: explicit return')]:
            self.store.append_interaction(kind='concept_explain', input_text=text, output_text=result,
                                          metadata={}, session_id=self.session)
        self.original_rows = self.store.list_interactions(100, session_id=self.session)
        self.h._state.session_summary_seed = {'answer_count': 2, 'verdict_counts': {'wrong': 1, 'correct': 1}}

    async def asyncTearDown(self):
        self.store.close()
        self.temp.cleanup()

    def assert_changed(self, result):
        self.assertEqual(result.get('code'), 'course_context_changed', result)
        self.assertNotIn('summary', result)

    def assert_old_history_preserved(self, summary_rows=0):
        rows = self.store.list_interactions(100, session_id=self.session)
        self.assertEqual([row for row in rows if row['kind'] != 'summarize_session'], self.original_rows)
        self.assertEqual(sum(row['kind'] == 'summarize_session' for row in rows), summary_rows)

    async def test_unchanged_request_uses_one_session_course_and_records_subset(self):
        expected = materials.material_context(self.h, include_material=False)
        result = await self.h.study_summarize_session(focus='corrected return', _material_context=expected)
        self.assertEqual(result['summary'], 'Original lesson summary')
        history, context = self.h.model_inputs[0]
        self.assertEqual(history, self.original_rows)
        self.assertEqual(context['history'], history)
        self.assertEqual(context['session_history'], history)
        self.assertEqual(context['session_id'], self.session)
        self.assertEqual(context['course_id'], 'course-A')
        rows = self.store.list_interactions(100, session_id=self.session)
        summary_row = next(row for row in rows if row['kind'] == 'summarize_session')
        self.assertEqual(summary_row['metadata']['material_context'], expected)
        narration = self.h._emit_session_summarized_event.call_args.args[0]
        self.assertEqual(narration['_material_context'], expected)
        self.assertEqual(narration['_session_summary_seed']['answer_count'], 2)
        self.assertNotIn('_material_context', result)
        self.assert_old_history_preserved(summary_rows=1)

    async def test_private_stale_or_malformed_context_never_rebinds_to_current_session(self):
        ensure = AsyncMock(wraps=self.h._ensure_active_study_session)
        self.h._ensure_active_study_session = ensure
        for expected in ({'course_id': 'old', 'session_id': self.session}, {}, 'invalid',
                         {**materials.material_context(self.h, include_material=False), 'material_identity': 'a'*64}):
            with self.subTest(expected=expected):
                self.assert_changed(await self.h.study_summarize_session(_material_context=expected))
        ensure.assert_not_awaited()
        self.h._agent.summarize_session.assert_not_awaited()
        self.assert_old_history_preserved()

    async def test_existing_session_replacement_during_ensure_is_refused_even_in_same_course(self):
        for course in ('course-A', 'course-B'):
            with self.subTest(course=course):
                async def replaced_ensure():
                    return await self.h._restart_study_session(course_id=course)
                self.h._ensure_active_study_session = replaced_ensure
                self.assert_changed(await self.h.study_summarize_session())
        self.h._agent.summarize_session.assert_not_awaited()
        self.assert_old_history_preserved()

    async def test_initially_absent_session_can_initialize_in_unchanged_course(self):
        await self.h._end_study_session_locked()
        result = await self.h.study_summarize_session()
        self.assertEqual(result['summary'], 'Original lesson summary')
        history, context = self.h.model_inputs[0]
        self.assertEqual(history, [])
        self.assertNotEqual(context['session_id'], self.session)
        self.assertEqual(context['course_id'], 'course-A')
        self.assert_old_history_preserved()

    async def test_absent_session_does_not_allow_initialization_into_a_different_course(self):
        await self.h._end_study_session_locked()
        async def replaced_ensure():
            return await self.h._restart_study_session(course_id='course-B')
        self.h._ensure_active_study_session = replaced_ensure
        self.assert_changed(await self.h.study_summarize_session())
        self.h._agent.summarize_session.assert_not_awaited()
        self.assert_old_history_preserved()

    async def query_race(self, blocked_query):
        original = self.store.list_interactions
        entered, release = threading.Event(), threading.Event()
        queries = []
        def paused(*args, **kwargs):
            rows = original(*args, **kwargs)
            queries.append(dict(kwargs))
            if len(queries) == blocked_query:
                entered.set()
                if not release.wait(3):
                    raise RuntimeError('test query was not released')
            return rows
        self.store.list_interactions = paused
        request = asyncio.create_task(self.h.study_summarize_session())
        try:
            self.assertTrue(await asyncio.to_thread(entered.wait, 2))
            await self.h._restart_study_session(course_id='course-B')
        finally:
            release.set()
        result = await request
        self.store.list_interactions = original
        self.assert_changed(result)
        self.h._agent.summarize_session.assert_not_awaited()
        self.assertTrue(all(query.get('course_id', 'course-A') == 'course-A' for query in queries))
        self.assertEqual(self.h._state.session_summary_seed, {})
        self.assert_old_history_preserved()

    async def test_course_change_during_history_read_stops_before_context_and_model(self):
        await self.query_race(1)

    async def test_actual_context_enrichment_keeps_old_course_then_rejects_replaced_request(self):
        # First query is entry history; second is the real context builder's
        # session history, after it has synchronously captured course-A.
        await self.query_race(2)

    async def test_mismatched_context_snapshot_is_not_given_to_model(self):
        original = self.h._build_learning_context
        async def wrong_snapshot(*args, **kwargs):
            context = await original(*args, **kwargs)
            context['course_id'] = 'course-B'
            return context
        self.h._build_learning_context = wrong_snapshot
        self.assert_changed(await self.h.study_summarize_session())
        self.h._agent.summarize_session.assert_not_awaited()
        self.assert_old_history_preserved()

    async def test_model_waiting_reply_cannot_commit_into_new_course(self):
        entered, release = asyncio.Event(), asyncio.Event()
        original = self.h._agent.summarize_session.side_effect
        async def delayed(*args, **kwargs):
            reply = await original(*args, **kwargs)
            entered.set()
            await release.wait()
            return reply
        self.h._agent.summarize_session.side_effect = delayed
        request = asyncio.create_task(self.h.study_summarize_session())
        await entered.wait()
        await self.h._restart_study_session(course_id='course-B')
        release.set()
        self.assert_changed(await request)
        self.assertEqual(self.h._state.session_summary_seed, {})
        self.assertEqual(self.h._state.last_session_summary, '')
        self.h._emit_session_summarized_event.assert_not_awaited()
        self.assert_old_history_preserved()

    async def test_picture_only_change_during_model_does_not_cancel_history_summary(self):
        self.h._cfg.llm_vision_enabled = True
        self.h._state.last_vision_image_base64 = 'image-A'
        self.h._state.last_ocr_text = 'image-A labels'
        original = self.h._agent.summarize_session.side_effect
        async def photo_replacement(*args, **kwargs):
            async with self.h._lock:
                self.h._state.last_vision_image_base64 = 'image-B'
                self.h._state.last_ocr_text = 'image-B labels'
            return await original(*args, **kwargs)
        self.h._agent.summarize_session.side_effect = photo_replacement
        result = await self.h.study_summarize_session()
        self.assertEqual(result['summary'], 'Original lesson summary')
        history, context = self.h.model_inputs[0]
        self.assertEqual(history, self.original_rows)
        self.assertFalse(context['vision_enabled'])
        self.assertEqual(context['vision_image_base64'], '')
        self.assertEqual(context['last_ocr_text'], '')
        self.assertNotIn('material_identity', context['_material_context'])
        self.assertEqual(self.h._state.last_vision_image_base64, 'image-B')
        self.assert_old_history_preserved(summary_rows=1)

    async def test_finalizer_guard_rejects_replacement_before_short_sql_commit(self):
        original = self.h._finalize_tutor_call
        async def changed_before_commit(*args, **kwargs):
            await self.h._restart_study_session(course_id='course-B')
            return await original(*args, **kwargs)
        self.h._finalize_tutor_call = changed_before_commit
        self.assert_changed(await self.h.study_summarize_session())
        self.assert_old_history_preserved()
        self.assertEqual(self.h._state.recent_learning_events, [])

    async def test_short_sql_commit_is_preserved_but_new_course_seed_narration_and_reply_are_blocked(self):
        original = self.store.append_interaction
        entered, release = threading.Event(), threading.Event()
        def paused(**kwargs):
            if kwargs['kind'] == 'summarize_session':
                entered.set()
                if not release.wait(3):
                    raise RuntimeError('test SQL worker was not released')
            return original(**kwargs)
        self.store.append_interaction = paused
        request = asyncio.create_task(self.h.study_summarize_session())
        self.assertTrue(await asyncio.to_thread(entered.wait, 2))
        replacement = asyncio.create_task(self.h._restart_study_session(course_id='course-B'))
        try:
            await asyncio.sleep(.03)
            self.assertFalse(replacement.done())
        finally:
            release.set()
        result = await request
        await replacement
        self.assert_changed(result)
        self.assert_old_history_preserved(summary_rows=1)
        self.assertEqual(self.h._state.session_summary_seed, {})
        self.assertEqual(self.h._state.recent_learning_events, [])
        self.assertEqual(self.h._state.last_session_summary, '')
        self.h._emit_session_summarized_event.assert_not_awaited()

    async def test_after_committed_history_replacement_stops_narration_and_public_reply(self):
        original = self.h._finalize_tutor_call
        async def changed_after_commit(*args, **kwargs):
            payload = await original(*args, **kwargs)
            await self.h._restart_study_session(course_id='course-B')
            return payload
        self.h._finalize_tutor_call = changed_after_commit
        self.assert_changed(await self.h.study_summarize_session())
        self.assert_old_history_preserved(summary_rows=1)
        self.h._emit_session_summarized_event.assert_not_awaited()

    async def test_narration_wait_gets_original_snapshot_and_late_change_blocks_return(self):
        captured = []
        async def changed_narration(payload):
            captured.append(deepcopy(payload))
            await self.h._restart_study_session(course_id='course-B')
        self.h._emit_session_summarized_event.side_effect = changed_narration
        self.assert_changed(await self.h.study_summarize_session())
        self.assertEqual(captured[0]['_material_context'], {'course_id': 'course-A', 'session_id': self.session})
        self.assertEqual(captured[0]['_session_summary_seed']['answer_count'], 2)
        self.assertEqual(self.h._state.session_summary_seed, {})
        self.assert_old_history_preserved(summary_rows=1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
