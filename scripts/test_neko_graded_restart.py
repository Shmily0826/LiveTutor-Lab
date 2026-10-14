"""Actual bootstrap/session methods and SQLite; no services, providers or devices."""
import ast
import asyncio
import logging
from pathlib import Path
import tempfile
import time
import unittest
from test_neko_product_course_memory import SOURCE,Store,ProductHarness

tree=ast.parse((SOURCE/'__init__.py').read_text(encoding='utf-8'))
plugin=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='StudyCompanionPlugin')
startup=next(n for n in plugin.body if getattr(n,'name',None)=='startup')
calls=[n for n in ast.walk(startup) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='_start_study_session']
assert len(calls)==1
bootstrap_kwargs={k.arg:ast.literal_eval(k.value) for k in calls[0].keywords}


class GradedRestart(unittest.IsolatedAsyncioTestCase):
    def open(self,folder):
        store=Store(Path(folder)/'study.db',Path(folder)/'unused.json',logging.getLogger('graded-restart'))
        store.open();return store,ProductHarness(store)

    async def set_grade(self,plugin,score=100,attempt='new-correction'):
        plugin._state.current_question={
            'question_id':'same-question','attempt_id':attempt,'question':'Which way?',
            'attempt_evaluated':True,'answer_evaluation_cache':{
                'question_id':'same-question','attempt_id':attempt,'score':score,
                'verdict':'correct' if score==100 else 'wrong'},
            'attempt_evaluation_pending':True,'attempt_evaluation_owner':'departed-worker'}
        plugin._state.last_answer_evaluation={'score':score,'verdict':'correct' if score==100 else 'wrong','feedback':'saved feedback'}
        plugin._state.last_question_at='original-question-time'
        plugin._state.last_answer_evaluated_at='latest-grade-time'
        await plugin._persist_state()

    def assert_grade(self,plugin,attempt,score):
        q=plugin._state.current_question
        self.assertEqual((q['question_id'],q['attempt_id']),('same-question',attempt))
        self.assertTrue(q['attempt_evaluated'])
        self.assertEqual(q['answer_evaluation_cache']['score'],score)
        self.assertEqual(plugin._state.last_answer_evaluation['score'],score)
        self.assertEqual(plugin._state.last_answer_evaluated_at,'latest-grade-time')
        self.assertNotIn('attempt_evaluation_pending',q)
        self.assertNotIn('attempt_evaluation_owner',q)

    async def test_real_bootstrap_arguments_preserve_latest_graded_state_over_stale_checkpoint(self):
        self.assertEqual(bootstrap_kwargs,{'resume_current_progress':True})
        for score in (0,100):
            with self.subTest(score=score),tempfile.TemporaryDirectory() as folder:
                store,p= self.open(folder)
                await p.study_set_course(course_id='course-a')
                p._state.current_question={'question_id':'old-question','attempt_id':'old-attempt','question':'stale checkpoint'}
                store.save_course_progress(p._state.to_dict())
                await self.set_grade(p,score)
                store.append_interaction(kind='answer_evaluate',input_text='old wrong answer',output_text='historical verdict',metadata={},session_id=p._study_session_id)
                old_rows=store.list_interactions(50);store.close()
                store,p=self.open(folder)
                try:
                    await p._start_study_session(p._state.active_mode,**bootstrap_kwargs)
                    self.assert_grade(p,'new-correction',score)
                    self.assertEqual(store.list_interactions(50),old_rows)
                    status=await p.study_session_tool()
                    self.assertEqual(status['question_state'],'evaluated')
                    self.assertEqual(status['current_question']['attempt_id'],'new-correction')
                    self.assertNotIn('answer_evaluation_cache',status['current_question'])
                finally:store.close()

    async def test_idle_rollover_and_empty_runtime_session_keep_grade_but_retire_old_reservation(self):
        for idle in (False,True):
            with self.subTest(idle=idle),tempfile.TemporaryDirectory() as folder:
                store,p=self.open(folder)
                try:
                    await p.study_set_course(course_id='course-a')
                    await self.set_grade(p,0,'wrong-attempt')
                    previous=p._study_session_id
                    if idle:p._study_session_last_activity=time.time()-31*60
                    else:p._study_session_id=''
                    await p._ensure_active_study_session()
                    self.assertNotEqual(p._study_session_id,previous)
                    self.assert_grade(p,'wrong-attempt',0)
                    self.assertEqual(store.list_qa_records(),[])
                finally:store.close()

    async def test_fresh_start_stays_retired_across_restart_and_course_return(self):
        with tempfile.TemporaryDirectory() as folder:
            store,p=self.open(folder)
            await p.study_set_course(course_id='course-a');await self.set_grade(p)
            await p.study_start_session(course_id='course-a')
            self.assertEqual(p._state.current_question,{})
            # Even a stale old checkpoint must not override fresh persisted state.
            store.set_raw('course_teaching_progress:course-a',{'version':1,'course_id':'course-a',
                'current_question':{'question_id':'retired','attempt_id':'retired','question':'not current'}})
            await p._persist_state();store.close()
            store,p=self.open(folder)
            try:
                await p._start_study_session(p._state.active_mode,**bootstrap_kwargs)
                self.assertEqual(p._state.current_question,{})
                self.assertEqual(p._state.last_answer_evaluation,{})
                await p.study_set_course(course_id='course-b')
                await p.study_set_course(course_id='course-a')
                self.assertEqual(p._state.current_question,{})
            finally:store.close()


if __name__=='__main__':unittest.main(verbosity=2)
