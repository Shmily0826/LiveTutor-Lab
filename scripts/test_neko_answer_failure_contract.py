"""Failed grading must be speakable and must never invent a score."""
import importlib
import logging
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock

from test_neko_answer_material_guard import GradeHarness, Store
from test_neko_explanation_language import scope
from test_neko_quiz_material_guard import Harness as QuizHarness, materials, models


class PictureGradeHarness(GradeHarness, QuizHarness):
    pass


class AnswerFailureContract(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name)/"study.db", Path(self.temp.name)/"seed.json", logging.getLogger("answer-failure"))
        self.store.open()
        self.h = GradeHarness(self.store)
        await self.h._restart_study_session(course_id="legacy-picture-course")
        self.h._state.current_question = {"question":"Which node calls NUD?", "answer":"WEX",
            "question_id":"q-held", "attempt_id":"a-held", "internal_private_payload":{
                "source_material_context":{"course_id":"legacy-picture-course", "session_id":"old-session"}}}

    async def asyncTearDown(self):
        self.store.close()
        self.temp.cleanup()

    def assert_spoken_failure(self, result):
        self.assertFalse(result["ok"])
        self.assertTrue(result.get("reply"), result)
        self.assertEqual(result["status"], "unavailable")
        self.assertNotIn("score", result)
        self.assertNotIn("verdict", result)
        self.assertNotIn("_study_material_binding", result)

    async def test_sdk_error_code_survives_envelope_and_gets_spoken_reason(self):
        # Actual SDK Result, rather than the dict-shaped error used by older harnesses.
        results = importlib.import_module("plugin.sdk.shared.models.result")
        errors = importlib.import_module("plugin.sdk.shared.models.exceptions")
        raw = results.Err(errors.SdkError("current question identity does not match", code="QUESTION_MISMATCH"))
        self.assertEqual(scope["_envelope"](raw).get("code"), "QUESTION_MISMATCH")
        self.h.study_evaluate_answer = AsyncMock(return_value=raw)
        output = await self.h.study_answer_tool(answer="REZ")
        self.assert_spoken_failure(output)
        self.assertIn("题", output["reply"])
        self.assertEqual(self.store.list_qa_records(), [])

    async def test_empty_feedback_is_not_a_silent_success(self):
        self.h.study_evaluate_answer = AsyncMock(return_value={"ok":True})
        output = await self.h.study_answer_tool(answer="REZ")
        self.assert_spoken_failure(output)
        self.assertEqual(output["code"], "EMPTY_GRADE_FEEDBACK")
        self.assertEqual(self.store.list_qa_records(), [])

    async def test_invalid_correction_and_failed_retry_explain_without_grading(self):
        invalid = await self.h.study_answer_tool(answer="WEX", correction_of={"question_id":"other", "attempt_id":"a-held"})
        self.assert_spoken_failure(invalid)
        self.h._agent.answer_evaluate.assert_not_awaited()
        self.h.study_retry_question = AsyncMock(return_value={"ok":False,"code":"ATTEMPT_NOT_RETRYABLE","error":"not graded"})
        refused = await self.h.study_answer_tool(answer="WEX", correction_of={"question_id":"q-held", "attempt_id":"a-held"})
        self.assert_spoken_failure(refused)
        self.h._agent.answer_evaluate.assert_not_awaited()

    async def test_foreign_course_question_is_rejected_with_actionable_reply(self):
        self.h._state.current_question["internal_private_payload"]["source_material_context"]["course_id"] = "other-course"
        output = await self.h.study_answer_tool(answer="REZ")
        self.assert_spoken_failure(output)
        self.assertIn("重新出题", output["reply"])
        self.h._agent.answer_evaluate.assert_not_awaited()

    async def test_native_correction_pin_on_ungraded_current_attempt_grades_once_without_retry(self):
        # Native supplied correction_of even for the first answer. There is no
        # evaluated attempt to revise, but the exact current pin is still valid.
        self.h._state.current_question["attempt_evaluated"] = False
        original = {key:self.h._state.current_question[key] for key in ("question_id","attempt_id")}
        self.h.study_retry_question = AsyncMock(wraps=self.h.study_retry_question)
        output = await self.h.study_answer_tool(answer="REZ", correction_of=original)
        self.assertEqual(output.get("verdict"), "wrong", output)
        self.assertEqual(output["attempt_id"], original["attempt_id"])
        self.h.study_retry_question.assert_not_awaited()
        self.assertEqual(self.h._agent.answer_evaluate.await_count, 1)
        self.assertEqual(len(self.store.list_qa_records()), 1)

    async def test_matching_pending_pin_cannot_bypass_an_in_progress_grade(self):
        self.h._state.current_question.update(attempt_evaluated=False, attempt_evaluation_pending=True,
                                              attempt_evaluation_owner="existing-grade")
        pin = {key:self.h._state.current_question[key] for key in ("question_id","attempt_id")}
        output = await self.h.study_answer_tool(answer="REZ", correction_of=pin)
        self.assert_spoken_failure(output)
        self.assertEqual(output["code"], "ATTEMPT_IN_PROGRESS")
        self.h._agent.answer_evaluate.assert_not_awaited()
        self.assertEqual(self.store.list_qa_records(), [])

    async def test_legacy_course_picture_quiz_restart_wrong_answer_and_correction_append(self):
        h = PictureGradeHarness(self.store)
        materials.save_material(self.store, "legacy-picture-course", "fixture-picture", "fixture: A points to B")
        await h._restart_study_session(course_id="legacy-picture-course")
        h._cfg.llm_vision_enabled = True
        async def generate(text, **kwargs):
            return models.TutorReply(operation="question_generate", input_text=text, reply="Which node calls B?",
                payload={"question":"Which node calls B?", "answer":"A", "topic":"fixture-arrows"})
        h._agent.question_generate = AsyncMock(side_effect=generate)
        quiz = await h.study_quiz_tool(request="出一道当前图片的方向题，不公布答案。")
        self.assertTrue(quiz.get("question_id"), quiz)
        origin = dict(h._state.current_question["internal_private_payload"]["source_material_context"])
        self.assertEqual(origin["course_id"], "legacy-picture-course")
        restored = PictureGradeHarness(self.store)
        async def grade(**kwargs):
            right = kwargs["answer"] == "A"
            return models.TutorReply(operation="answer_evaluate", input_text=kwargs["answer"], reply="Fixture feedback.",
                payload={"feedback":"Fixture feedback.", "verdict":"correct" if right else "wrong", "score":100 if right else 0})
        restored._agent.answer_evaluate = AsyncMock(side_effect=grade)
        wrong = await restored.study_answer_tool(answer="B")
        self.assertEqual(wrong["verdict"], "wrong")
        old = self.store.list_qa_records()
        corrected = await restored.study_answer_tool(answer="A", correction_of={
            "question_id":wrong["question_id"], "attempt_id":wrong["attempt_id"]})
        self.assertEqual(corrected["verdict"], "correct")
        rows = self.store.list_qa_records()
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0], old[0])
        self.assertEqual(rows[0]["question"]["question_id"], rows[1]["question"]["question_id"])
        self.assertNotEqual(rows[0]["question"]["attempt_id"], rows[1]["question"]["attempt_id"])
        self.assertTrue(self.store._require_conn().execute("SELECT count(*) FROM wrong_questions").fetchone()[0])
        self.assertEqual(self.store._require_conn().execute("SELECT count(*) FROM mastery_snapshots").fetchone()[0], 2)


if __name__ == "__main__":
    unittest.main()
