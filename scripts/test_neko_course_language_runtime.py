"""Real lifecycle/context/grade entries and temporary SQLite; no host or providers."""
import asyncio
from copy import deepcopy
import unittest
from unittest.mock import AsyncMock, patch

import test_neko_answer_material_guard as grade
from test_neko_explanation_language import Harness as ExplanationHarness
from test_neko_product_course_memory import prompts
from test_neko_learning_preferences import prefs


class CourseLanguage(unittest.IsolatedAsyncioTestCase):
    setUp=grade.AnswerMaterial.setUp
    tearDown=grade.AnswerMaterial.tearDown

    async def seed_saved_english(self):
        self.h._state.study_course_id='course-A'
        self.h._state.teaching_language_by_course={'course-A':'en-US'}
        await self.h._persist_state()
        self.h=grade.GradeHarness(self.store)
        self.assertEqual(self.h._cfg.language,'zh-CN')
        return self.h

    async def test_startup_resume_applies_language_to_all_real_prompt_builders(self):
        h=await self.seed_saved_english()
        await h._start_study_session(h._state.active_mode,resume_current_progress=True)
        self.assertEqual(h._cfg.language,'en-US')
        for operation in ('concept_explain','question_generate','answer_evaluate','knowledge_track','summarize_session'):
            context=await h._build_learning_context(operation,input_text='Explain the route',extra={
                'source_text':'WEX points to NUD; NUD points to REZ.','question':'Which node follows NUD?',
                'answer':'REZ','expected_answer':'REZ'})
            self.assertEqual(context['language'],'en-US')
            user=prompts.build_operation_messages(operation,context)[1]['content']
            self.assertTrue('\nLanguage: en-US\n' in '\n'+user
                            or 'Write every natural-language field in en-US.' in user,operation)

    async def test_direct_grade_initializes_session_with_saved_language_without_avatar_tool(self):
        h=await self.seed_saved_english();before=deepcopy(h._state.teaching_language_by_course)
        result=await h.study_evaluate_answer(question='Which node follows NUD?',answer='WEX',expected_answer='REZ')
        self.assertEqual(result['verdict'],'wrong')
        context=h._agent.answer_evaluate.call_args.kwargs['context']
        self.assertEqual(context['language'],'en-US');self.assertEqual(h._cfg.language,'en-US')
        self.assertEqual(h._state.teaching_language_by_course,before)
        self.assertEqual(len(self.store.list_qa_records()),1)
        self.assertIsNone(self.store.get_raw(prefs.PREFERENCES_KEY))

    async def test_course_return_and_unconfigured_course_use_configured_default_not_prior_course(self):
        h=self.h;h._state.teaching_language_by_course={'course-A':'en-US','course-B':'zh-TW'}
        original=deepcopy(h._state.teaching_language_by_course)
        for course,wanted in (('course-A','en-US'),('course-B','zh-TW'),('no-preference','zh-CN'),('course-A','en-US')):
            await h.study_set_course(course_id=course)
            self.assertEqual(h._cfg.language,wanted)
            context=await h._build_learning_context('answer_evaluate',input_text='answer')
            self.assertEqual(context['language'],wanted)
        self.assertEqual(h._state.teaching_language_by_course,original)
        self.assertIsNone(self.store.get_raw(prefs.PREFERENCES_KEY))

    async def test_global_and_legacy_defaults_remain_below_course_choice(self):
        h=self.h;h._state.teaching_language='en-US'
        h._state.teaching_language_by_course={'course-A':'zh-TW'}
        await h.study_set_course(course_id='course-A');self.assertEqual(h._cfg.language,'zh-TW')
        await h.study_set_course(course_id='legacy-default');self.assertEqual(h._cfg.language,'en-US')
        prefs.update_preferences(self.store,{'language':'zh-CN'},remember=True)
        await h.study_set_course(course_id='global-default');self.assertEqual(h._cfg.language,'zh-CN')
        await h.study_set_course(course_id='course-A');self.assertEqual(h._cfg.language,'zh-TW')

    async def test_idle_rollover_reapplies_saved_course_and_keeps_real_prior_grade(self):
        h=await self.seed_saved_english()
        await h.study_evaluate_answer(question='Which node follows NUD?',answer='WEX',expected_answer='REZ')
        original=deepcopy(self.store.list_qa_records());session=h._study_session_id
        h._study_session_last_activity=1
        await h._ensure_active_study_session()
        self.assertNotEqual(h._study_session_id,session);self.assertEqual(h._cfg.language,'en-US')
        self.assertEqual(self.store.list_qa_records(),original)

    async def test_real_save_close_load_does_not_promote_course_language_to_config_default(self):
        h=await self.seed_saved_english();await h._start_study_session(resume_current_progress=True)
        self.assertEqual(h._cfg.language,'en-US');await h._persist_state()
        self.store.close()
        self.store=grade.Store(grade.Path(self.temporary.name)/'study.db',grade.Path(self.temporary.name)/'seed.json',
                               grade.logging.getLogger('course-language-reopen'))
        self.store.open();h=grade.GradeHarness(self.store);self.h=h
        h._cfg=self.store.load_config(grade.models.StudyConfig())
        self.assertEqual(h._cfg.language,'zh-CN')
        await h._start_study_session(resume_current_progress=True);self.assertEqual(h._cfg.language,'en-US')
        await h.study_set_course(course_id='no-preference');self.assertEqual(h._cfg.language,'zh-CN')
        await h.study_set_course(course_id='course-A');self.assertEqual(h._cfg.language,'en-US')

    async def test_temporary_explanation_does_not_change_next_direct_grade_or_saved_preference(self):
        h=await self.seed_saved_english()
        # Actual avatar explanation wrapper, context and direct grade entries;
        # only the explanation model backend is replaced.
        h.study_explain_text=ExplanationHarness.study_explain_text.__get__(h,type(h))
        h.calls=[];h.fail=False
        await h.study_explain_tool(question='This time answer in Chinese; do not save a preference.',
                                   text='WEX points to NUD; NUD points to REZ.',language='zh-CN')
        self.assertEqual(h.calls[-1][0],'zh-CN');self.assertEqual(h._cfg.language,'en-US')
        await h.study_evaluate_answer(question='Which node follows NUD?',answer='WEX',expected_answer='REZ')
        self.assertEqual(h._agent.answer_evaluate.call_args.kwargs['context']['language'],'en-US')
        self.assertEqual(h._state.teaching_language_by_course,{'course-A':'en-US'})
        self.assertIsNone(self.store.get_raw(prefs.PREFERENCES_KEY))

    async def test_course_change_during_temporary_call_restores_new_course_after_retired_result(self):
        h=self.h;h._state.teaching_language_by_course={'course-A':'en-US','course-B':'zh-TW'}
        await h.study_set_course(course_id='course-A')
        entered=asyncio.Event();release=asyncio.Event()
        async def explain(**kwargs):
            self.assertEqual(h._cfg.language,'zh-CN');entered.set();await release.wait()
            return {'reply':'旧课的临时中文回答。'}
        h.study_explain_text=AsyncMock(side_effect=explain)
        task=asyncio.create_task(h.study_explain_tool(question='Explain the notes this time in Chinese',
            text='WEX points to NUD; NUD points to REZ.',language='zh-CN'))
        await entered.wait();await h.study_set_course(course_id='course-B');release.set()
        result=await task
        self.assertFalse(result['ok']);self.assertEqual(result['error'],'course_context_changed')
        self.assertEqual(h._cfg.language,'zh-TW')
        context=await h._build_learning_context('answer_evaluate',input_text='next')
        self.assertEqual(context['language'],'zh-TW')

    async def test_explicit_same_course_language_change_is_not_undone_by_temporary_completion(self):
        h=await self.seed_saved_english();await h._start_study_session(resume_current_progress=True)
        entered=asyncio.Event();release=asyncio.Event()
        async def explain(**kwargs):
            entered.set();await release.wait();return {'reply':'临时中文回答。'}
        h.study_explain_text=AsyncMock(side_effect=explain)
        task=asyncio.create_task(h.study_explain_tool(question='Explain the notes in Chinese this time',
            text='WEX points to NUD; NUD points to REZ.',language='zh-CN'))
        await entered.wait()
        with patch.dict(h.study_language_tool.__func__.__globals__,
                        {'pin_character_language':AsyncMock(return_value={'ok':False,'reason':'offline seam'})}):
            result=await h.study_language_tool(language='zh-CN',scope='course')
        self.assertEqual(result['reply_language'],'zh-CN')
        release.set();await task
        self.assertEqual(h._state.teaching_language_by_course,{'course-A':'zh-CN'})
        self.assertEqual(h._cfg.language,'zh-CN')
        await h.study_evaluate_answer(question='Which node follows NUD?',answer='WEX',expected_answer='REZ')
        self.assertEqual(h._agent.answer_evaluate.call_args.kwargs['context']['language'],'zh-CN')


if __name__=='__main__':unittest.main(verbosity=2)
