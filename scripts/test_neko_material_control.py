"""Actual product methods, fresh SQLite and local SDK push stub; no host/audio/provider."""
import asyncio
import importlib
import logging
from pathlib import Path
import tempfile
import sys
from types import SimpleNamespace, MethodType
import unittest
from unittest.mock import AsyncMock

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_neko_product_course_memory as course
import test_neko_explanation_language as language
import test_neko_native_material_guard as guarded
from test_neko_image_course_guard import product_method, SOURCE, EntryError, StudyError

materials = importlib.import_module('product_study.study_materials')
# The existing AST lifecycle fixture binds module imports explicitly.
course.namespace.update({key: getattr(materials, key) for key in
                         ('material_context', 'material_changes', 'submit_material_changes')})


class MaterialControl(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = course.Store(Path(self.temp.name)/'study.db', Path(self.temp.name)/'unused.json', logging.getLogger('control'))
        self.store.open()
        self.h = language.Harness(self.store)
        self.events = []

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    async def prepare(self):
        h = await guarded.NativeMaterialGuard.prepare(self)
        h.ctx = SimpleNamespace(_current_lanlan='ImageRole')
        def push(**payload):
            self.assertFalse(h._lock.locked(), 'SDK push must run outside state lock')
            self.events.append(payload)
            return {'submitted': True}
        h.push_message = push
        return h

    def submit_method(self, h):
        def normalize(image):
            if image == 'invalid':
                raise ValueError('invalid fixture')
            return image
        namespace = {'asyncio': asyncio, '_normalize_submitted_image_payload': normalize,
                     '_plugin_lock': lambda lock: lock, 'Err': EntryError, 'SdkError': StudyError,
                     '_entry_exception_error': lambda host, error, **kwargs: EntryError(error),
                     '_image_only_explain_prompt': lambda language: 'Explain image',
                     **{key: getattr(materials, key) for key in
                        ('save_material', 'material_context', 'material_changes', 'submit_material_changes')}}
        h.study_explain_text = AsyncMock(side_effect=lambda **kwargs: {'ok': True, 'reply': 'accepted fixture'})
        return MethodType(product_method(SOURCE, 'study_submit_image', namespace), h)

    async def test_success_binding_then_ui_picture_change_targets_original_role_with_blind_control(self):
        h = await self.prepare()
        output = await h.study_explain_tool(question='Explain this diagram', _ctx={'lanlan_name': 'ExactRole'})
        binding = output['_study_material_binding']
        self.assertEqual(set(binding), {'v', 'boot_id', 'change_seq', 'context'})
        self.assertRegex(binding['boot_id'], r'^[0-9a-f]{32}$')
        self.assertEqual(binding['context'], materials.material_context(h))
        self.assertEqual(set(h._study_material_output_targets), {'ExactRole'})
        submit = self.submit_method(h)
        h.ctx._current_lanlan = 'DifferentCurrentRole'
        result = await submit('image-B', 'source-B', expected_course_id='course-A')
        self.assertEqual(len(self.events), 1)
        event = self.events[0]
        self.assertEqual(event['target_lanlan'], 'ExactRole')
        self.assertEqual(event['visibility'], [])
        self.assertEqual(event['ai_behavior'], 'blind')
        self.assertTrue(event['parts'][0]['text'])
        control = event['metadata']['study_material_control']
        self.assertEqual(set(control), {'v', 'boot_id', 'change_seq', 'before', 'after', 'reason'})
        self.assertEqual(control['before'], binding['context'])
        self.assertEqual(control['after'], materials.material_context(h))
        self.assertEqual(control['boot_id'], binding['boot_id'])
        self.assertGreater(control['change_seq'], binding['change_seq'])
        self.assertEqual(result['material_control_submission'][0]['status'], 'submitted')
        self.assertEqual(materials.load_material(self.store, 'course-A')['image'], 'image-B')

    async def test_invalid_same_content_and_wrong_course_never_cancel_or_advance_sequence(self):
        h = await self.prepare()
        await h.study_explain_tool(question='Explain this diagram')
        seq = h._study_material_change_seq
        submit = self.submit_method(h)
        for image, text, course_id in [('invalid', 'bad', 'course-A'),
                                      ('image-B', 'bad', 'wrong-course'),
                                      ('image-A', 'source-A', 'course-A')]:
            await submit(image, text, expected_course_id=course_id)
        self.assertEqual(self.events, [])
        self.assertEqual(h._study_material_change_seq, seq)
        self.assertEqual(h._state.last_vision_image_base64, 'image-A')

    async def test_explicit_source_binding_ignores_image_only_change_but_not_session_or_course(self):
        h = await self.prepare()
        await h.study_explain_tool(question='Explain this diagram', _ctx={'lanlan_name': 'ImageRole'})
        source = await h.study_explain_tool(question='Explain source', text='13 return temperature;', _ctx={'lanlan_name': 'SourceRole'})
        self.assertEqual(set(source['_study_material_binding']['context']), {'course_id', 'session_id'})
        submit = self.submit_method(h)
        await submit('image-B', 'source-B')
        self.assertEqual([e['target_lanlan'] for e in self.events], ['ImageRole'])
        await h._restart_study_session(course_id='course-B')
        end_events = [e for e in self.events if e['metadata']['study_material_control']['reason'] == 'session_ended']
        self.assertEqual({e['target_lanlan'] for e in end_events}, {'ImageRole', 'SourceRole'})
        self.assertEqual(end_events[-1]['metadata']['study_material_control']['after']['session_id'], '')

    async def test_end_then_start_have_independent_sequence_and_do_not_lose_old_session_notification(self):
        h = await self.prepare()
        output = await h.study_explain_tool(question='Explain this diagram')
        before_seq = output['_study_material_binding']['change_seq']
        old_session = h._study_session_id
        await h._restart_study_session(course_id='course-A')
        self.assertEqual(len(self.events), 2)
        control = self.events[0]['metadata']['study_material_control']
        self.assertEqual(control['before']['session_id'], old_session)
        self.assertEqual(control['after']['session_id'], '')
        self.assertEqual(control['change_seq'], before_seq + 1)
        self.assertEqual(h._study_material_change_seq, before_seq + 2)
        self.assertNotEqual(h._study_session_id, old_session)
        started = self.events[1]['metadata']['study_material_control']
        self.assertEqual(started['reason'], 'session_started')
        self.assertEqual(started['change_seq'], before_seq + 2)
        self.assertEqual(started['before']['session_id'], '')
        self.assertEqual(started['after']['session_id'], h._study_session_id)

    async def test_no_exact_target_never_broadcasts_and_boot_is_per_instance(self):
        h = await self.prepare()
        h.ctx._current_lanlan = ''
        output = await h.study_explain_tool(question='Explain this diagram', _ctx={})
        binding = output['_study_material_binding']
        self.assertEqual(h._study_material_output_targets, {})
        await self.submit_method(h)('image-B', 'source-B')
        self.assertEqual(self.events, [])
        other = SimpleNamespace(_state=h._state, _study_session_id=h._study_session_id)
        second = materials.bind_material_output(other, materials.material_context(other), '')
        self.assertNotEqual(second['boot_id'], binding['boot_id'])

    async def test_submission_failure_is_reported_without_reverting_accepted_material_or_history(self):
        h = await self.prepare()
        await h.study_explain_tool(question='Explain this diagram')
        h.push_message = lambda **payload: {'submitted': False}
        result = await self.submit_method(h)('image-B', 'source-B')
        self.assertEqual(result['material_control_submission'][0]['status'], 'not_submitted')
        self.assertEqual(h._state.last_vision_image_base64, 'image-B')
        self.assertEqual(materials.load_material(self.store, 'course-A')['image'], 'image-B')
        self.assertEqual(len(self.store.list_interactions(10, session_id=h._study_session_id)), 1)

    async def test_push_exception_and_unknown_receipt_are_honest(self):
        h = await self.prepare()
        await h.study_explain_tool(question='Explain this diagram')
        def failed(**payload):
            raise RuntimeError('local push failure')
        h.push_message = failed
        result = await self.submit_method(h)('image-B', 'source-B')
        self.assertEqual(result['material_control_submission'][0]['status'], 'exception')
        self.assertEqual(result['material_control_submission'][0]['error_type'], 'RuntimeError')
        materials.bind_material_output(h, materials.material_context(h), 'ImageRole')
        h.push_message = lambda **payload: {'ok': True}
        result = await self.submit_method(h)('image-C', 'source-C')
        self.assertEqual(result['material_control_submission'][0]['status'], 'submission_unknown')

    async def test_missed_intermediate_change_still_notifies_precise_old_output_target(self):
        h = await self.prepare()
        binding = (await h.study_explain_tool(question='Explain this diagram'))['_study_material_binding']
        h.push_message = lambda **payload: {'submitted': False}
        submit = self.submit_method(h)
        first = await submit('image-B', 'source-B')
        self.assertEqual(first['material_control_submission'][0]['status'], 'not_submitted')
        before_c = materials.material_context(h)
        def push(**payload):
            self.events.append(payload)
            return {'submitted': True}
        h.push_message = push
        second = await submit('image-C', 'source-C')
        self.assertEqual(second['material_control_submission'][0]['status'], 'submitted')
        self.assertEqual(len(self.events), 1)
        self.assertEqual(self.events[0]['target_lanlan'], 'ImageRole')
        control = self.events[0]['metadata']['study_material_control']
        self.assertEqual(control['boot_id'], binding['boot_id'])
        self.assertEqual(control['before'], before_c)
        self.assertEqual(control['after'], materials.material_context(h))
        self.assertGreater(control['change_seq'], first['material_control_submission'][0]['change_seq'])

    async def test_degraded_and_stale_explanations_never_register_output_binding(self):
        h = await self.prepare()
        async def degraded(source, **kwargs):
            return course.models.TutorReply(operation='concept_explain', input_text=source,
                reply='model failed', degraded=True, diagnostic='provider_unavailable')
        h._agent.concept_explain = AsyncMock(side_effect=degraded)
        output = await h.study_explain_tool(question='Explain this diagram')
        self.assertNotIn('_study_material_binding', output)
        self.assertEqual(getattr(h, '_study_material_output_targets', {}), {})
        async def stale(source, **kwargs):
            h._state.last_vision_image_base64 = 'replacement'
            return course.models.TutorReply(operation='concept_explain', input_text=source, reply='old explanation')
        h._agent.concept_explain = AsyncMock(side_effect=stale)
        output = await h.study_explain_tool(question='Explain this diagram')
        self.assertNotIn('_study_material_binding', output)
        self.assertEqual(getattr(h, '_study_material_output_targets', {}), {})

    async def test_store_rejection_leaves_original_material_and_sends_nothing(self):
        h = await self.prepare()
        await h.study_explain_tool(question='Explain this diagram')
        expected, seq = materials.material_context(h), h._study_material_change_seq
        def failed_store(*args, **kwargs):
            raise RuntimeError('controlled SQLite write rejection')
        self.store.set_raw = failed_store
        with self.assertRaisesRegex(RuntimeError, 'controlled SQLite'):
            await self.submit_method(h)('image-B', 'source-B')
        self.assertEqual(materials.material_context(h), expected)
        self.assertEqual(h._study_material_change_seq, seq)
        self.assertEqual(self.events, [])

    async def test_cancelled_submission_retains_accepted_image_and_reports_unknown(self):
        h = await self.prepare()
        await h.study_explain_tool(question='Explain this diagram')
        entered = asyncio.Event()
        async def delayed_push(**kwargs):
            self.assertFalse(h._lock.locked())
            entered.set()
            await asyncio.Event().wait()
        h.push_message = delayed_push
        submit = self.submit_method(h)
        request = asyncio.create_task(submit('image-B', 'source-B'))
        await entered.wait()
        request.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await request
        self.assertEqual(h._state.last_vision_image_base64, 'image-B')
        self.assertEqual(h._study_material_control_submission[0]['status'], 'submission_unknown')
        self.assertEqual(h._study_material_control_submission[0]['error_type'], 'CancelledError')


if __name__ == '__main__':
    unittest.main(verbosity=2)
