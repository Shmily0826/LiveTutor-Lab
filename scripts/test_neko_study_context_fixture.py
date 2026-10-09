"""Focused assertions for the local Study Companion context double.

These tests import only the fixture class. They do not construct a plugin,
start a browser, or touch the plugin's temporary database.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest


FIXTURE_PATH = Path(__file__).with_name("neko_study_plugin_methods_fixture.py")
SPEC = importlib.util.spec_from_file_location("neko_study_plugin_methods_fixture", FIXTURE_PATH)
FIXTURE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(FIXTURE)


class Reply:
    def __init__(self, **values):
        self.__dict__.update(values)


FIRST_FOLLOW_UP = "为什么例题2有1/2？"
SECOND_FOLLOW_UP = "为什么要令 u=x^2？"


def new_agent(lesson: str):
    return FIXTURE.LocalAgentDouble(Reply, lesson)


class StudyContextFixtureTests(unittest.TestCase):
    def call_explain(self, agent, text, context):
        coroutine = agent.concept_explain(text, mode="study", context=context)
        try:
            coroutine.send(None)
        except StopIteration as completed:
            return completed.value
        self.fail("LocalAgentDouble.concept_explain unexpectedly suspended")

    def test_known_ocr_formula_variants_are_accepted(self):
        for lesson in (
            "Example 2: u =x²; du = 2x dx",
            "Example 2: u = x^2; du=2x dx",
            "Example 2: u=x^2; du = 2 x dx",
        ):
            with self.subTest(lesson=lesson):
                agent = new_agent(lesson)
                reply = self.call_explain(agent, FIRST_FOLLOW_UP, {"lesson": lesson})
                self.assertIn("1/2", reply.reply)

    def test_wrong_substitution_or_derivative_is_rejected(self):
        for lesson in (
            "Example 2: u=x^3; du=2x dx",
            "Example 2: u=x^2; du=3x dx",
        ):
            with self.subTest(lesson=lesson):
                agent = new_agent(lesson)
                with self.assertRaisesRegex(RuntimeError, "exact prior example"):
                    self.call_explain(agent, FIRST_FOLLOW_UP, {"lesson": lesson})

    def test_first_follow_up_accepts_original_material(self):
        lesson = "Example 2: u =x²; du = 2x dx"
        agent = new_agent(lesson)
        reply = self.call_explain(agent, FIRST_FOLLOW_UP, {"lesson": lesson})
        self.assertIn("Example 2", reply.reply)
        self.assertIn("du=2x dx", reply.reply)

    def _first_reply(self, lesson: str):
        agent = new_agent(lesson)
        first = self.call_explain(agent, FIRST_FOLLOW_UP, {"lesson": lesson})
        return agent, first.reply

    def test_second_follow_up_requires_previous_question_and_response(self):
        lesson = "Example 2: u =x²; du = 2x dx"
        agent, first_reply = self._first_reply(lesson)
        missing_question = {"lesson": lesson, "previous_response": first_reply}
        missing_response = {"lesson": lesson, "previous_question": FIRST_FOLLOW_UP}
        for context in (missing_question, missing_response):
            with self.subTest(context_keys=tuple(context)):
                with self.assertRaisesRegex(RuntimeError, "previous question or response"):
                    self.call_explain(agent, SECOND_FOLLOW_UP, context)

    def test_second_follow_up_accepts_json_contained_prior_turn(self):
        lesson = "Example 2: u =x²; du = 2x dx"
        agent, first_reply = self._first_reply(lesson)
        context = {
            "history": json.dumps({
                "original_ocr": lesson,
                "question": FIRST_FOLLOW_UP,
                "response": first_reply,
            }, ensure_ascii=False),
        }
        request = json.dumps({"current_followup": SECOND_FOLLOW_UP}, ensure_ascii=False)
        reply = self.call_explain(agent, request, context)
        self.assertIn(FIRST_FOLLOW_UP, reply.reply)
        self.assertIn("u=x^2", reply.reply)


if __name__ == "__main__":
    unittest.main()
