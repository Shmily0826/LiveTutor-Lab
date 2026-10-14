"""Actual avatar retry/grade and SQLite, local model; no Native or devices."""
import asyncio
from copy import deepcopy
import unittest
from unittest.mock import AsyncMock
import test_neko_answer_material_guard as grade

class NativeAnswerCorrection(unittest.IsolatedAsyncioTestCase):
    setUp=grade.AnswerMaterial.setUp
    tearDown=grade.AnswerMaterial.tearDown
    prepare=grade.AnswerMaterial.prepare

    async def wrong(self):
        h=await self.prepare()
        await h.study_answer_tool(answer='REZ')
        reference={key:h._state.current_question[key] for key in ('question_id','attempt_id')}
        pin={**reference,'course_id':h._state.study_course_id,'session_id':h._state.study_session_id}
        return h,reference,pin

    async def test_correction_keeps_same_question_and_original_wrong_history(self):
        h,reference,pin=await self.wrong()
        old=deepcopy(self.store.list_qa_records(course_id='course-A'))
        async def correct(**kwargs):
            return grade.models.TutorReply(operation='answer_evaluate',input_text=kwargs['answer'],reply='Correct.',
                payload={'feedback':'Correct.','verdict':'correct','score':100,'topic':'arrows','misconceptions':[]})
        h._agent.answer_evaluate=AsyncMock(side_effect=correct)
        output=await h.study_answer_tool(answer='我纠正刚才的答案，是 WEX。',correction_of=reference,_expected_question=pin)
        self.assertEqual(output['verdict'],'correct')
        self.assertEqual(h._state.current_question['question_id'],reference['question_id'])
        self.assertNotEqual(h._state.current_question['attempt_id'],reference['attempt_id'])
        qa=self.store.list_qa_records(course_id='course-A')
        self.assertEqual(len(qa),2)
        self.assertTrue(all(row in qa for row in old))
        h._agent.answer_evaluate.assert_awaited_once()
        again=await h.study_answer_tool(answer='WEX',correction_of=reference)
        self.assertEqual(again['code'],'QUESTION_CONTEXT_CHANGED')
        self.assertEqual(len(self.store.list_qa_records(course_id='course-A')),2)

    async def test_bad_reference_or_correct_attempt_never_creates_another_grade(self):
        for kind in ('other_question','missing_attempt','already_correct'):
            with self.subTest(kind=kind):
                h,reference,pin=await self.wrong()
                if kind=='other_question':reference['question_id']='other-question'
                elif kind=='missing_attempt':reference.pop('attempt_id')
                else:h._state.current_question['answer_evaluation_cache']['verdict']='correct'
                before=deepcopy(h._state.current_question)
                count=len(self.store.list_qa_records(course_id='course-A'))
                h._agent.answer_evaluate.reset_mock()
                result=await h.study_answer_tool(answer='WEX',correction_of=reference)
                self.assertIn(result.get('code'),('QUESTION_CONTEXT_CHANGED','ATTEMPT_NOT_RETRYABLE'))
                self.assertEqual(h._state.current_question,before)
                h._agent.answer_evaluate.assert_not_awaited()
                self.assertEqual(len(self.store.list_qa_records(course_id='course-A')),count)

    async def test_same_correction_inflight_is_graded_only_once(self):
        h,reference,pin=await self.wrong();h._agent.answer_evaluate.reset_mock()
        results=await asyncio.gather(*(h.study_answer_tool(answer='WEX',correction_of=reference,_expected_question=pin) for _ in range(2)))
        self.assertEqual(h._agent.answer_evaluate.await_count,1)
        self.assertEqual(sum(output.get('verdict')=='wrong' for output in results),1)
        self.assertEqual(len(self.store.list_qa_records(course_id='course-A')),2)

if __name__=='__main__':unittest.main(verbosity=2)
