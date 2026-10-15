"""R3: an interruption phrase gets the stored point of the last explanation, never a new lesson.

Real study_explain wrapper and a fresh SQLite store; no model, no Native, no audio.
"""
import importlib
import logging
from pathlib import Path
import tempfile
import unittest

from test_neko_explanation_language import Harness, Store, prefs

interrupt = importlib.import_module("product_study.study_interrupt_summary")

EXPLANATION = ("weather_service.dart 第二十二到二十三行检查 response.statusCode != 200，非 200 就直接抛 Exception。"
               "第二十六行的解析只有在 200 时才会执行。")


class Classifier(unittest.TestCase):
    def test_conclusion_requests_including_the_recogniser_split_form(self):
        for text in ("先说结论", "先说结论。", "先 说 结 论", "等一下，先说结论", "直接说结论", "结论是什么", "先讲重点",
                     "说一下重点吧", "一句话总结", "Just give me the conclusion.", "Wait, the bottom line first"):
            with self.subTest(text=text):
                self.assertEqual(interrupt.classify(text), "conclusion")

    def test_spaced_recogniser_output_is_understood(self):
        for text, expected in (("先 说 结 论 。", "conclusion"), ("等 一 下 。", "pause"), ("结 论 是 什 么", "conclusion")):
            with self.subTest(text=text):
                self.assertEqual(interrupt.classify(text), expected)

    def test_pause_only(self):
        for text in ("等一下。", "等等", "停一下", "Wait.", "hold on"):
            with self.subTest(text=text):
                self.assertEqual(interrupt.classify(text), "pause")

    def test_real_questions_are_not_interruptions(self):
        for text in ("先说结论，再解释第 23 行为什么抛异常", "结论里的 throw 是哪一行？", "讲一下非 200 的处理", "总结一下这节课学了什么，三句话",
                     "等一下，我想问 fetchWeather 的返回值", "", None, 7, "x" * 80):
            with self.subTest(text=text):
                self.assertEqual(interrupt.classify(text), "")

    def test_conclusion_is_the_first_sentence_and_stubs_are_extended(self):
        self.assertEqual(interrupt.conclusion_of(EXPLANATION), "weather_service.dart 第二十二到二十三行检查 response.statusCode != 200，非 200 就直接抛 Exception。")
        self.assertEqual(interrupt.conclusion_of("好。非 200 会直接抛异常，不会重试。第三句。"), "好。非 200 会直接抛异常，不会重试。")
        self.assertEqual(interrupt.conclusion_of("只有一句"), "只有一句")
        self.assertEqual(interrupt.conclusion_of(""), "")
        self.assertEqual(interrupt.conclusion_of(None), "")

    def test_last_explanation_skips_degraded_empty_and_interruption_rows(self):
        rows = [{"kind": "concept_explain", "input_text": "先说结论\n[Source evidence] x", "output_text": "文件概览。", "metadata": {}},
                {"kind": "concept_explain", "input_text": "q", "output_text": "坏的", "metadata": {"degraded": True}},
                {"kind": "quiz", "input_text": "q", "output_text": "题目", "metadata": {}},
                {"kind": "concept_explain", "input_text": "q", "output_text": "  ", "metadata": {}},
                {"kind": "concept_explain", "input_text": "非 200 怎么处理\n[Source evidence] x", "output_text": EXPLANATION, "metadata": {}}]
        self.assertEqual(interrupt.last_explanation(rows), EXPLANATION)
        self.assertEqual(interrupt.last_explanation([]), "")
        self.assertEqual(interrupt.last_explanation(None), "")


class Wrapped(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / "study.db", Path(self.temp.name) / "seed.json", logging.getLogger("interrupt"))
        self.store.open()
        prefs.update_preferences(self.store, {"language": "zh-CN"}, remember=True)
        self.h = Harness(self.store)
        await self.h._restart_study_session(course_id="course-A")
        self.session = self.h._state.study_session_id

    async def asyncTearDown(self):
        self.store.close()
        self.temp.cleanup()

    def remember(self, question, reply):
        self.store.append_interaction(kind="concept_explain", input_text=question + "\n[Source evidence] x",
                                      output_text=reply, metadata={"degraded": False}, session_id=self.session)

    async def test_interruption_answers_from_the_last_explanation_without_a_model_call(self):
        self.remember("非 200 怎么处理", EXPLANATION)
        result = await self.h.study_explain_tool(question="先说结论", material_source="project_code")
        self.assertEqual(self.h.calls, [])
        self.assertEqual(result["mode"], "interrupt")
        self.assertIn("非 200 就直接抛 Exception", result["reply"])
        self.assertNotIn("第二十六行", result["reply"])
        self.assertIn("then stop", result["relay"])

    async def test_the_interruption_itself_is_not_the_next_conclusion(self):
        self.remember("非 200 怎么处理", EXPLANATION)
        self.remember("先说结论", "文件概览。")
        result = await self.h.study_explain_tool(question="先说结论")
        self.assertIn("非 200 就直接抛 Exception", result["reply"])

    async def test_bare_pause_stops_in_the_course_language(self):
        result = await self.h.study_explain_tool(question="等一下")
        self.assertEqual(result["reply"], "好，我先停下来，你说。")
        self.assertEqual(self.h.calls, [])
        english = await self.h.study_explain_tool(question="Wait.", language="en-US")
        self.assertIn("stop here", english["reply"])

    async def test_without_a_stored_explanation_the_normal_path_runs(self):
        result = await self.h.study_explain_tool(question="先说结论")
        self.assertEqual(len(self.h.calls), 1)
        self.assertNotEqual(result.get("mode"), "interrupt")

    async def test_real_questions_and_literal_text_still_reach_the_teacher(self):
        self.remember("非 200 怎么处理", EXPLANATION)
        await self.h.study_explain_tool(question="先说结论，再解释第 23 行为什么抛异常")
        await self.h.study_explain_tool(question="先说结论", material_source="literal_text", text="notes")
        self.assertEqual(len(self.h.calls), 2)


if __name__ == "__main__":
    unittest.main()
