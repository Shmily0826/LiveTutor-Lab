"""Exercise the actual image entry's course guard without a model or host."""
import ast
import asyncio
import importlib.util
from copy import deepcopy
from pathlib import Path
import time
from types import SimpleNamespace, MethodType
import unittest
from unittest.mock import AsyncMock

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'patches/neko-study-2026-10-10-product/payload/study_companion/entry_tutor_explain_entries.py'
spec = importlib.util.spec_from_file_location('actual_materials', SOURCE.with_name('study_materials.py'))
materials = importlib.util.module_from_spec(spec)
spec.loader.exec_module(materials)


class EntryError(dict):
    def __init__(self, error):
        super().__init__(error=str(error), code=getattr(error, 'code', ''))


class StudyError(Exception):
    def __init__(self, message, *, code=''):
        super().__init__(message)
        self.code = code


def product_method(path, name, namespace):
    tree = ast.parse(path.read_text(encoding='utf-8'))
    method = next(n for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef) and n.name == name)
    method.decorator_list = []
    module = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0), method], type_ignores=[])
    exec(compile(ast.fix_missing_locations(module), str(path), 'exec'), namespace)
    return namespace[name]


def explain_namespace():
    def unexpected_error(_host, error, **kwargs):
        raise AssertionError(f'unexpected product error: {type(error).__name__}: {error}')
    return {'asyncio': asyncio, 'monotonic': time.monotonic, '_PRIMARY_EXPLAIN_TIMEOUT_SECONDS': 70,
            '_plugin_lock': lambda lock: lock, 'Err': EntryError, 'SdkError': StudyError,
            'handle_user_intent': lambda text, **kwargs: {'matched': False, 'remaining_text': text},
            '_validate_optional_vision_image_payload': lambda host, image, **kwargs: image,
            'LLM_OPERATION_CONCEPT_EXPLAIN': 'concept_explain', '_entry_exception_error': unexpected_error,
            'material_context_current':materials.material_context_current, 'MaterialContextChanged':materials.MaterialContextChanged}


class ImageCourseGuard(unittest.IsolatedAsyncioTestCase):
    async def test_course_changed_after_preflight_does_not_save_or_explain_old_image(self):
        tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
        method = next(n for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef) and n.name == 'study_submit_image')
        method.decorator_list = []
        saves, explanations = [], []
        namespace = {'asyncio': asyncio, '_normalize_submitted_image_payload': lambda s: s,
                     '_plugin_lock': lambda lock: lock, 'Err': lambda e: {'error': str(e)},
                     'SdkError': lambda message, **kwargs: ValueError(message), 'save_material': lambda *args: saves.append(args),
                     'material_context':materials.material_context}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(SOURCE), 'exec'), namespace)
        state = SimpleNamespace(study_course_id='before', last_vision_image_base64='current-image', last_ocr_text='current')
        async def ensure(): state.study_course_id = 'after'
        async def explain(**kwargs): explanations.append(kwargs); return {'ok': True}
        host = SimpleNamespace(_cfg=SimpleNamespace(llm_vision_enabled=True), _state=state,
                               _lock=asyncio.Lock(), _ensure_active_study_session=ensure,
                               study_explain_text=explain, _store=object(), _study_session_id='session-after')
        submit = MethodType(namespace['study_submit_image'], host)
        result = await submit('old-image', 'old-course question', expected_course_id='before')
        self.assertIn('课程已切换', result['error'])
        self.assertEqual(state.last_vision_image_base64, 'current-image')
        self.assertEqual(saves, [])
        self.assertEqual(explanations, [])
        result = await submit('new-image', 'new-course question', expected_course_id='after')
        self.assertTrue(result['ok'])
        self.assertEqual(saves[0][1], 'after')
        self.assertEqual(explanations[0]['vision_image_base64'], 'new-image')
        self.assertEqual(explanations[0]['_material_context']['course_id'], 'after')
        self.assertEqual(explanations[0]['_material_context']['session_id'], 'session-after')
        self.assertEqual(len(explanations[0]['_material_context']['material_identity']), 64)

    async def test_course_changes_while_context_building_refuses_before_model(self):
        explain = product_method(SOURCE, 'study_explain_text', explain_namespace())
        for change_course in (True, False):
            with self.subTest(change_course=change_course):
                agent = SimpleNamespace(concept_explain=AsyncMock())
                host = SimpleNamespace(_agent=agent, _cfg=SimpleNamespace(language='zh-CN'),
                    _state=SimpleNamespace(study_course_id='A', active_mode='teaching'),
                    _study_session_id='session-A', _lock=asyncio.Lock(), _resolve_study_target_lanlan=lambda kwargs: '')
                async def build(operation, *, session_id, **kwargs):
                    self.assertEqual(session_id, 'session-A')
                    host._study_session_id = 'session-B'
                    if change_course: host._state.study_course_id = 'B'
                    return {'course_id': 'A', 'session_id': session_id}
                host._build_learning_context = build
                result = await explain(host, text='Explain A picture', vision_image_base64='image-A',
                    _material_context={'course_id': 'A', 'session_id': 'session-A'})
                self.assertEqual(result['code'], 'course_context_changed')
                agent.concept_explain.assert_not_awaited()

    async def test_course_changes_while_model_runs_refuses_stale_result(self):
        explain = product_method(SOURCE, 'study_explain_text', explain_namespace())
        host = SimpleNamespace(_cfg=SimpleNamespace(language='zh-CN'),
            _state=SimpleNamespace(study_course_id='A', active_mode='teaching'), _study_session_id='session-A',
            _lock=asyncio.Lock(), _resolve_study_target_lanlan=lambda kwargs: '', _finalize_tutor_call=AsyncMock())
        host._build_learning_context = AsyncMock(return_value={'course_id': 'A', 'session_id': 'session-A'})
        async def model(*args, **kwargs):
            host._state.study_course_id = 'B'
            host._study_session_id = 'session-B'
            return SimpleNamespace(reply='old picture explanation', payload={}, degraded=False)
        host._agent = SimpleNamespace(concept_explain=AsyncMock(side_effect=model))
        result = await explain(host, text='Explain A picture', vision_image_base64='image-A',
            _material_context={'course_id': 'A', 'session_id': 'session-A'})
        self.assertEqual(result['code'], 'course_context_changed')
        host._agent.concept_explain.assert_awaited_once()
        host._finalize_tutor_call.assert_not_awaited()

    async def test_old_session_record_does_not_pollute_new_live_progress(self):
        namespace = {'_plugin_lock': lambda lock: lock, 'time': time, 'utc_now_iso': lambda: 'now',
                     'material_context_current':materials.material_context_current,
                     'LLM_OPERATION_KNOWLEDGE_TRACK': 'knowledge_track', 'LLM_OPERATION_QUESTION_GENERATE': 'question_generate',
                     'LLM_OPERATION_ANSWER_EVALUATE': 'answer_evaluate', 'LLM_OPERATION_SUMMARIZE_SESSION': 'summarize_session'}
        record = product_method(SOURCE.with_name('entry_tutor_context_support.py'), '_record_tutor_result', namespace)
        state = SimpleNamespace(session_summary_seed={'current': 'B'}, recent_learning_events=[{'course': 'B'}],
                                last_screen_classification={})
        host = SimpleNamespace(_state=state, _study_session_id='session-B', _lock=asyncio.Lock(),
                               _merge_session_summary_seed=lambda operation, *, payload, seed: {**seed, 'reply': payload.get('summary')})
        reply = SimpleNamespace(payload={'summary': 'A old lesson'}, reply='A old reply', input_text='old material',
                                degraded=False, diagnostic='', created_at='then')
        before = deepcopy(state.__dict__)
        await record(host, 'concept_explain', reply, extra={'session_id': 'session-A'})
        self.assertEqual(state.__dict__, before)
        # A current result still updates progress; this guard must not disable all recording.
        await record(host, 'concept_explain', reply, extra={'session_id': 'session-B'})
        self.assertEqual(len(state.recent_learning_events), 2)
        self.assertEqual(state.session_summary_seed['reply'], 'A old lesson')


if __name__ == '__main__': unittest.main(verbosity=2)
