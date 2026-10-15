"""R1: a plain statement spoken while a quiz question waits is graded as the answer.

Offline: the real classifier, real study_explain/study_answer wrappers and a fresh SQLite store,
with a local fake grading model. No Native, no model request, no audio device.
"""
import importlib
import json
from pathlib import Path
import unittest
from unittest.mock import AsyncMock

import test_neko_answer_material_guard as grade

routing = importlib.import_module("product_study.study_answer_routing")
CORPUS = json.loads((Path(__file__).with_name("natural_answer_corpus.json")).read_text(encoding="utf-8"))["samples"]


class Classifier(unittest.TestCase):
    def test_corpus_classes(self):
        wrong = []
        for sample in CORPUS:
            got = routing.classify_pending_turn(sample["text"])
            if got != sample["expect"]:
                wrong.append((sample["id"], sample["text"], got))
        self.assertEqual(wrong, [])

    def test_recogniser_spacing_between_chinese_characters_changes_nothing(self):
        import re
        for sample in CORPUS:
            spaced = re.sub(r"(?<=[一-鿿，。！？])(?=[一-鿿，。！？])", " ", sample["text"])
            with self.subTest(sample=sample["id"], spaced=spaced):
                self.assertEqual(routing.classify_pending_turn(spaced), sample["expect"])

    def test_corpus_shape_matches_the_round_goal(self):
        kinds = {s["kind"] for s in CORPUS if s["expect"] == "answer"}
        self.assertGreaterEqual(sum(s["expect"] == "answer" for s in CORPUS), 12)
        self.assertEqual(sum(s["expect"] == "material_correction" for s in CORPUS), 4)
        for needed in ("explicit", "wrong_direct", "negation", "vague", "partial", "mid_revision"):
            self.assertIn(needed, kinds)

    def test_junk_and_questions_never_become_answers(self):
        for value in (None, 5, "", "   ", "。", "x" * 500, "你能再讲一遍吗？", "Why does it throw?", "出一道新题",
                      "这是什么", "请评分", "解释一下第 23 行"):
            with self.subTest(value=value):
                self.assertNotEqual(routing.classify_pending_turn(value), routing.ANSWER)

    def test_correction_wins_over_negation_words(self):
        for text in ("你读错了，这张图根本有箭头", "不对，你看错了，再看一遍", "图换了，没有那个箭头了",
                     "你说得不对"):
            with self.subTest(text=text):
                self.assertEqual(routing.classify_pending_turn(text), routing.MATERIAL_CORRECTION)

    def test_pending_state_needs_ids_and_no_grader(self):
        base = {"question_id": "q", "attempt_id": "a", "attempt_evaluated": False}
        self.assertTrue(routing.has_pending_question(base))
        for patch in ({"attempt_evaluated": True}, {"attempt_evaluated": None}, {"attempt_evaluation_pending": True},
                      {"attempt_evaluation_owner": "x"}, {"question_id": ""}, {"attempt_id": ""}):
            with self.subTest(patch=patch):
                self.assertFalse(routing.has_pending_question({**base, **patch}))
        self.assertFalse(routing.has_pending_question(None))
        self.assertFalse(routing.has_pending_question({}))


class Routed(unittest.IsolatedAsyncioTestCase):
    setUp = grade.AnswerMaterial.setUp
    tearDown = grade.AnswerMaterial.tearDown
    prepare = grade.AnswerMaterial.prepare

    async def ready(self):
        h = await self.prepare()
        h._state.current_question["attempt_evaluated"] = False
        h.calls.clear()
        return h

    async def test_every_answer_sample_is_graded_once_and_stored(self):
        for sample in (s for s in CORPUS if s["expect"] == "answer"):
            with self.subTest(sample=sample["id"]):
                self.tearDown()
                self.setUp()
                h = await self.ready()
                result = await h.study_explain_tool(question=sample["text"], material_source="current_picture")
                self.assertEqual(result.get("tool"), "study_answer", result)
                self.assertEqual(result["routed_from"], "study_explain")
                self.assertEqual(h._agent.answer_evaluate.await_count, 1)
                self.assertEqual(h._agent.answer_evaluate.call_args.kwargs["answer"], sample["text"])
                self.assertEqual(h.calls, [])
                self.assertEqual(len(self.store.list_qa_records(course_id="course-A")), 1)
                self.assertTrue(h._state.current_question["attempt_evaluated"])

    async def test_material_corrections_and_questions_are_never_graded(self):
        for sample in (s for s in CORPUS if s["expect"] != "answer"):
            with self.subTest(sample=sample["id"]):
                h = await self.ready()
                h._agent.answer_evaluate.reset_mock()
                try:
                    await h.study_explain_tool(question=sample["text"], material_source="current_picture")
                except Exception:
                    pass  # the picture path may need a fixture this harness lacks; only grading matters here
                h._agent.answer_evaluate.assert_not_awaited()
                self.assertEqual(self.store.list_qa_records(course_id="course-A"), [])
                self.assertFalse(h._state.current_question["attempt_evaluated"])

    async def test_without_a_pending_question_a_statement_still_explains(self):
        h = await self.ready()
        h._state.current_question["attempt_evaluated"] = True
        before = len(self.store.list_qa_records(course_id="course-A"))
        result = await h.study_explain_tool(question="这张图根本没有箭头", material_source="literal_text", text="WEX -> NUD")
        self.assertNotEqual(result.get("tool"), "study_answer")
        self.assertEqual(len(self.store.list_qa_records(course_id="course-A")), before)
        h._agent.answer_evaluate.assert_not_awaited()

    async def test_no_held_question_at_all_explains(self):
        h = await self.prepare()
        h._state.current_question = {}
        result = await h.study_explain_tool(question="WEX 指向 REZ", material_source="literal_text", text="WEX -> NUD")
        self.assertNotEqual(result.get("tool"), "study_answer")
        h._agent.answer_evaluate.assert_not_awaited()

    async def test_literal_notes_request_is_never_hijacked(self):
        h = await self.ready()
        await h.study_explain_tool(question="我的答案是这段笔记", material_source="literal_text", text="notes")
        h._agent.answer_evaluate.assert_not_awaited()

    async def test_repeated_statement_after_grade_does_not_regrade(self):
        h = await self.ready()
        await h.study_explain_tool(question="WEX 指向 REZ")
        again = await h.study_explain_tool(question="WEX 指向 REZ", material_source="literal_text", text="WEX -> NUD")
        self.assertNotEqual(again.get("tool"), "study_answer")
        self.assertEqual(h._agent.answer_evaluate.await_count, 1)
        self.assertEqual(len(self.store.list_qa_records(course_id="course-A")), 1)

    async def test_grading_failure_is_reported_not_scored(self):
        h = await self.ready()
        h._agent.answer_evaluate = AsyncMock(side_effect=RuntimeError("controlled failure"))
        try:
            result = await h.study_explain_tool(question="这张图根本没有箭头")
        except RuntimeError:
            result = {"ok": False}
        self.assertFalse(result.get("ok", True) and result.get("verdict"))
        self.assertEqual(self.store.list_qa_records(course_id="course-A"), [])


if __name__ == "__main__":
    unittest.main()
