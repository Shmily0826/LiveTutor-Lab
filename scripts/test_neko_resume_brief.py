"""Course-scoped SQLite resume facts; no model or audio, no schema migration."""
import logging
from pathlib import Path
import tempfile
import unittest
from test_neko_product_course_memory import Store, ProductHarness


class ResumeBrief(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.store=Store(Path(self.temp.name)/'study.db',Path(self.temp.name)/'seed.json',logging.getLogger('brief'))
        self.store.open()

    async def asyncTearDown(self):
        self.store.close();self.temp.cleanup()

    def session(self,name,course):
        self.store.ensure_session(session_id=name,mode='teaching',course_id=course)

    def source(self,session,file,lines,call=None):
        metadata={'project':'project','commit':'rev','shown':[{'file':file,'lines':lines}]}
        if call:metadata['call']=call
        self.store.append_interaction(kind='code_question',input_text=file,output_text='source read',metadata=metadata,session_id=session)

    async def test_multiple_sessions_same_course_exclude_other_course_and_empty_restart(self):
        self.session('a1','A');self.source('a1','older.py',[1,2])
        self.session('a2','A');self.source('a2','guard.py',[20,21,26],'call-a')
        self.source('a2','consumer.py',[8,9],'call-a')
        self.session('b','B');self.source('b','OTHER_COURSE_SECRET.py',[90,91])
        self.session('a3','A')
        rows=self.store.list_interactions(30)
        brief=self.store.resume_brief('A')
        self.assertTrue(brief['available'])
        self.assertEqual({w['file'] for w in brief['source_windows']},{'guard.py','consumer.py'})
        self.assertEqual(next(w for w in brief['source_windows'] if w['file']=='guard.py')['end_line'],26)
        self.assertNotIn('OTHER_COURSE_SECRET',str(brief))
        self.assertEqual(self.store.list_interactions(30),rows)

    async def test_legacy_no_call_is_not_combined_with_unrelated_earlier_read(self):
        self.session('old','A');self.source('old','before.py',[1,2]);self.source('old','latest.py',[7,8])
        brief=self.store.resume_brief('A')
        self.assertEqual([w['file'] for w in brief['source_windows']],['latest.py'])

    async def test_latest_grade_keeps_zero_and_does_not_use_another_course(self):
        for course,score in [('A',0),('B',100)]:
            self.session(course,course)
            self.store.add_qa_record(session_id=course,topic_id='',question={'question':'What happens?','question_id':course,'attempt_id':course+'-a','answer':'PRIVATE_REFERENCE'},user_answer='answer',eval_result={'score':score,'verdict':'wrong' if score==0 else 'correct'},mode='teaching')
        brief=self.store.resume_brief('A')
        self.assertEqual(brief['last_grade']['score'],0)
        self.assertEqual(brief['last_grade']['question_id'],'A')
        self.assertEqual(brief['next_step'],'review_last_answer')
        self.assertNotIn('PRIVATE_REFERENCE',str(brief))

    async def test_no_history_is_explicit_and_status_includes_the_readonly_brief(self):
        self.session('empty','A')
        brief=self.store.resume_brief('A')
        self.assertFalse(brief['available'])
        self.assertEqual(brief['source_windows'],[])
        self.assertEqual(brief['last_grade'],{})
        self.assertEqual(brief['next_step'],'choose_learning_material')
        plugin=ProductHarness(self.store)
        await plugin.study_set_course(course_id='A')
        status=await plugin.study_session_tool()
        self.assertFalse(status['resume_brief']['available'])

    async def test_pending_question_is_not_given_an_earlier_questions_grade(self):
        plugin=ProductHarness(self.store)
        await plugin.study_set_course(course_id='A')
        self.store.add_qa_record(session_id=plugin._study_session_id,topic_id='',question={'question_id':'old','question':'Old?'},user_answer='wrong',eval_result={'score':0,'verdict':'wrong'},mode='teaching')
        plugin._state.current_question={'question_id':'new','attempt_id':'new-a','question':'New?','answer':'PRIVATE_REFERENCE'}
        status=await plugin.study_session_tool()
        brief=status['resume_brief']
        self.assertEqual(brief['last_quiz']['question_id'],'new')
        self.assertEqual(brief['last_quiz']['grade_status'],'not_graded')
        self.assertEqual(brief['last_grade']['question_id'],'old')
        self.assertEqual(brief['next_step'],'answer_pending_question')
        self.assertNotIn('PRIVATE_REFERENCE',str(brief))

    async def test_old_malformed_source_metadata_cannot_crash_status(self):
        self.session('old','A')
        self.store.append_interaction(kind='code_question',input_text='',output_text='',metadata={'shown':[{'file':'old.py','lines':None}]},session_id='old')
        self.assertEqual(self.store.resume_brief('A')['source_windows'],[])

    async def test_spoken_recap_formats_saved_facts_without_a_teacher(self):
        plugin=ProductHarness(self.store)
        await plugin.study_set_course(course_id='course-A')
        self.source(plugin._study_session_id,'project/weather_service.dart',[18,26,29])
        self.store.add_qa_record(session_id=plugin._study_session_id,topic_id='',question={'question_id':'q','question':'Will parsing run?'},user_answer='wrong',eval_result={'score':0,'verdict':'wrong'},mode='teaching')
        status=await plugin.study_session_tool()
        spoken=status['resume_brief']['spoken_recap']
        for fact in ('course-A','weather_service.dart','十八','二十九','Will parsing run?','0分','复习'):
            self.assertIn(fact,spoken)
        self.source(plugin._study_session_id,'large.dart',[10000,10002])
        spoken=(await plugin.study_session_tool())['resume_brief']['spoken_recap']
        self.assertIn('10000',spoken)
        self.assertIn('10002',spoken)


if __name__=='__main__':unittest.main(verbosity=2)
