"""Actual retry/grade entries, checkpoint and fresh SQLite; no external model or devices."""
import asyncio
from copy import deepcopy
import threading
import unittest
from unittest.mock import AsyncMock

import test_neko_answer_material_guard as grade


class CorrectionAttempt(unittest.IsolatedAsyncioTestCase):
    setUp = grade.AnswerMaterial.setUp
    tearDown = grade.AnswerMaterial.tearDown
    prepare = grade.AnswerMaterial.prepare

    def pin(self, h):
        return {"question_id": h._state.current_question["question_id"],
                "attempt_id": h._state.current_question["attempt_id"],
                "course_id": h._state.study_course_id, "session_id": h._state.study_session_id}

    def set_model(self, h, verdict):
        async def local_model(**kwargs):
            return grade.models.TutorReply(operation="answer_evaluate", input_text=kwargs["answer"],
                reply="Local grading feedback.", payload={"feedback": "Local grading feedback.",
                    "verdict": verdict, "score": 100 if verdict == "correct" else 50,
                    "topic": "arrows", "misconceptions": []})
        h._agent.answer_evaluate = AsyncMock(side_effect=local_model)

    async def wrong(self):
        h = await self.prepare()
        result = await h.study_answer_tool(answer="REZ")
        self.assertEqual(result["verdict"], "wrong")
        return h

    def assert_error(self, result, code):
        self.assertEqual(result["code"], code)

    async def test_wrong_retry_correct_preserves_question_two_qa_and_restart(self):
        h = await self.wrong()
        pin = self.pin(h)
        before = deepcopy(h._state.current_question)
        old_qa = deepcopy(self.store.list_qa_records(course_id="course-A"))
        old_history = deepcopy(self.store.list_interactions(20, session_id=h._study_session_id))
        result = await h.study_retry_question(**pin)
        new_attempt = result["attempt_id"]
        self.assertNotEqual(new_attempt, pin["attempt_id"])
        self.assertEqual(result["question_id"], pin["question_id"])
        for name in ("question", "answer", "reference_answer", "topic", "internal_private_payload"):
            self.assertEqual(h._state.current_question.get(name), before.get(name))
        self.assertNotIn("answer", result["current_question"])
        self.assertNotIn("reference_answer", result["current_question"])
        self.assertNotIn("internal_private_payload", result["current_question"])
        self.assertEqual(self.store.list_qa_records(course_id="course-A"), old_qa)
        self.assertEqual(self.store.list_interactions(20, session_id=h._study_session_id), old_history)
        self.assertEqual(self.store.load_course_progress("course-A")["current_question"]["attempt_id"], new_attempt)
        self.assertEqual(self.store.get_raw("state")["current_question"]["attempt_id"], new_attempt)
        await h.study_set_course(course_id="course-B")
        await h.study_set_course(course_id="course-A")
        self.assertEqual(h._state.current_question["attempt_id"], new_attempt)
        self.assertFalse(h._state.current_question["attempt_evaluated"])

        restored = grade.GradeHarness(self.store)
        await restored._start_study_session_locked(resume_pending_question=True)
        self.assertEqual(restored._state.current_question["attempt_id"], new_attempt)
        self.set_model(restored, "correct")
        corrected = await restored.study_answer_tool(answer="WEX")
        self.assertEqual(corrected["verdict"], "correct")
        rows = self.store.list_qa_records(course_id="course-A")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0], old_qa[0])
        self.assertEqual(rows[0]["topic_id"], rows[1]["topic_id"])
        self.assertEqual([row["eval_result"]["verdict"] for row in rows], ["wrong", "correct"])
        self.assertEqual([row["question"]["question_id"] for row in rows], [pin["question_id"]] * 2)
        self.assertEqual([row["question"]["attempt_id"] for row in rows], [pin["attempt_id"], new_attempt])
        self.assertEqual(restored._state.last_answer_evaluation["verdict"], "correct")

    async def test_partial_can_retry_but_correct_cannot(self):
        h = await self.prepare()
        self.set_model(h, "partial")
        await h.study_answer_tool(answer="partial answer")
        result = await h.study_retry_question(**self.pin(h))
        self.assertTrue(result["retried"])
        self.set_model(h, "correct")
        await h.study_answer_tool(answer="WEX")
        before = deepcopy(h._state.current_question)
        result = await h.study_retry_question(**self.pin(h))
        self.assert_error(result, "ATTEMPT_NOT_RETRYABLE")
        self.assertEqual(h._state.current_question, before)
        self.assertEqual(len(self.store.list_qa_records()), 2)

    async def test_ordinary_grade_and_old_retry_identity_cannot_replay(self):
        h = await self.wrong()
        pin = self.pin(h)
        ordinary = await h.study_answer_tool(answer="WEX")
        self.assert_error(ordinary, "ATTEMPT_ALREADY_EVALUATED")
        retried = await h.study_retry_question(**pin)
        repeated = await h.study_retry_question(**pin)
        self.assert_error(repeated, "QUESTION_CONTEXT_CHANGED")
        self.assertEqual(h._state.current_question["attempt_id"], retried["attempt_id"])
        self.assertEqual(h._agent.answer_evaluate.await_count, 1)
        self.assertEqual(len(self.store.list_qa_records()), 1)

    async def test_false_unknown_foreign_or_busy_attempts_never_write(self):
        h = await self.wrong()
        original = deepcopy(h._state.current_question)
        pin = self.pin(h)
        cases = ["unscored", "cache_missing", "cache_unknown", "cache_wrong_id", "degraded",
                 "pending", "owner", "foreign_origin", "wrong_q", "wrong_attempt", "wrong_course",
                 "wrong_session", "missing", "false"]
        for case in cases:
            with self.subTest(case=case):
                h._state.current_question = deepcopy(original)
                supplied = dict(pin)
                held = h._state.current_question
                expected = "ATTEMPT_NOT_RETRYABLE"
                if case == "unscored": held["attempt_evaluated"] = False
                elif case == "cache_missing": held.pop("answer_evaluation_cache")
                elif case == "cache_unknown": held["answer_evaluation_cache"]["verdict"] = "unknown"
                elif case == "cache_wrong_id": held["answer_evaluation_cache"]["attempt_id"] = "not-this-attempt"
                elif case == "degraded": held["answer_evaluation_cache"]["degraded"] = True
                elif case in ("pending", "owner"):
                    held["attempt_evaluation_pending" if case == "pending" else "attempt_evaluation_owner"] = True
                    expected = "ATTEMPT_IN_PROGRESS"
                elif case == "foreign_origin":
                    held["internal_private_payload"]["source_material_context"]["course_id"] = "course-B"
                    expected = "QUESTION_CONTEXT_CHANGED"
                elif case.startswith("wrong_"):
                    field = {"wrong_q": "question_id", "wrong_attempt": "attempt_id", "wrong_course": "course_id", "wrong_session": "session_id"}[case]
                    supplied[field] = "foreign"
                    expected = "QUESTION_CONTEXT_CHANGED"
                else:
                    supplied["attempt_id"] = "" if case == "missing" else False
                    expected = "QUESTION_CONTEXT_CHANGED"
                before = deepcopy(held)
                count = self.store._require_conn().total_changes
                result = await h.study_retry_question(**supplied)
                self.assert_error(result, expected)
                self.assertEqual(h._state.current_question, before)
                self.assertEqual(self.store._require_conn().total_changes, count)
                self.assertEqual(h._agent.answer_evaluate.await_count, 1)

    async def test_two_concurrent_explicit_retries_create_only_one_attempt(self):
        h = await self.wrong()
        pin = self.pin(h)
        results = await asyncio.gather(h.study_retry_question(**pin), h.study_retry_question(**pin))
        self.assertEqual(sum(bool(result.get("retried")) for result in results), 1)
        self.assertEqual(sum(result.get("code") == "QUESTION_CONTEXT_CHANGED" for result in results), 1)
        self.assertEqual(len(self.store.list_qa_records()), 1)

    async def test_retry_does_not_require_a_model_agent(self):
        h = await self.wrong()
        h._agent = None
        result = await h.study_retry_question(**self.pin(h))
        self.assertTrue(result["retried"])
        self.assertEqual(len(self.store.list_qa_records()), 1)

    async def test_real_grade_staging_owner_blocks_retry_until_grade_finishes(self):
        h = await self.prepare()
        entered = threading.Event()
        release = threading.Event()
        original = h._knowledge_tracker.get_mastery
        def delayed(topic):
            if h._state.current_question.get("attempt_evaluated"):
                entered.set()
                if not release.wait(3): raise AssertionError("local test did not release mastery read")
            return original(topic)
        h._knowledge_tracker.get_mastery = delayed
        task = asyncio.create_task(h.study_answer_tool(answer="REZ"))
        try:
            self.assertTrue(await asyncio.to_thread(entered.wait, 2))
            self.assertTrue(h._state.current_question["attempt_evaluated"])
            self.assertTrue(h._state.current_question.get("attempt_evaluation_owner"))
            result = await h.study_retry_question(**self.pin(h))
            self.assert_error(result, "ATTEMPT_IN_PROGRESS")
            release.set()
            await task
            retried = await h.study_retry_question(**self.pin(h))
            self.assertTrue(retried["retried"])
            self.assertEqual(len(self.store.list_qa_records()), 1)
        finally:
            release.set()
            await asyncio.gather(task, return_exceptions=True)

    async def test_second_checkpoint_write_failure_rolls_back_state_and_progress(self):
        h = await self.wrong()
        before = deepcopy(h._state.current_question)
        state = self.store.get_raw("state")
        progress = self.store.load_course_progress("course-A")
        conn = self.store._require_conn()
        conn.execute("CREATE TEMP TRIGGER fail_retry_checkpoint BEFORE INSERT ON kv "
                     "WHEN NEW.key='course_teaching_progress:course-A' BEGIN SELECT RAISE(ABORT,'checkpoint failed'); END")
        conn.commit()
        result = await h.study_retry_question(**self.pin(h))
        self.assert_error(result, "RETRY_PERSIST_FAILED")
        self.assertEqual(h._state.current_question, before)
        self.assertEqual(self.store.get_raw("state"), state)
        self.assertEqual(self.store.load_course_progress("course-A"), progress)
        self.assertEqual(len(self.store.list_qa_records()), 1)

    async def test_failed_save_cannot_restore_over_a_following_course_switch(self):
        h = await self.wrong()
        entered = threading.Event()
        release = threading.Event()
        def failed(snapshot):
            entered.set()
            if not release.wait(3): raise AssertionError("local test did not release save")
            raise OSError("local save failure")
        h._save_retry_question_checkpoint = failed
        retry = asyncio.create_task(h.study_retry_question(**self.pin(h)))
        switched = None
        try:
            self.assertTrue(await asyncio.to_thread(entered.wait, 2))
            switched = asyncio.create_task(h.study_set_course(course_id="course-B"))
            await asyncio.sleep(0)
            release.set()
            result = await retry
            await switched
            self.assert_error(result, "RETRY_PERSIST_FAILED")
            self.assertEqual(h._state.study_course_id, "course-B")
            self.assertEqual(h._state.current_question, {})
            self.assertEqual(len(self.store.list_qa_records(course_id="course-A")), 1)
        finally:
            release.set()
            await asyncio.gather(retry, *([switched] if switched else []), return_exceptions=True)

    async def test_cancelled_save_drains_before_publishing_or_unlocking(self):
        h = await self.wrong()
        pin = self.pin(h)
        original = h._save_retry_question_checkpoint
        entered = threading.Event()
        release = threading.Event()
        def delayed(snapshot):
            entered.set()
            if not release.wait(3): raise AssertionError("local test did not release save")
            original(snapshot)
        h._save_retry_question_checkpoint = delayed
        task = asyncio.create_task(h.study_retry_question(**pin))
        try:
            self.assertTrue(await asyncio.to_thread(entered.wait, 2))
            task.cancel()
            await asyncio.sleep(0)
            self.assertTrue(h._lock.locked())
            release.set()
            with self.assertRaises(asyncio.CancelledError): await task
            self.assertNotEqual(h._state.current_question["attempt_id"], pin["attempt_id"])
            self.assertEqual(self.store.get_raw("state")["current_question"], h._state.current_question)
            self.assertEqual(self.store.load_course_progress("course-A")["current_question"], h._state.current_question)
            self.assertEqual(len(self.store.list_qa_records()), 1)
        finally:
            release.set()
            await asyncio.gather(task, return_exceptions=True)


if __name__ == "__main__": unittest.main(verbosity=2)
