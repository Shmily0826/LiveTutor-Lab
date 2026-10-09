"""Offline native manual-question identity/privacy/grading lifecycle regression.

Uses the actual Store, finalizer and entry methods; model replies are local stubs.
No provider, host, capture or audio is started.
"""
import ast
import asyncio
import contextlib
from pathlib import Path
import tempfile
import unittest
import uuid
from typing import Any

import test_neko_product_course_memory as memory

ROOT, SOURCE, BASE = memory.ROOT, memory.SOURCE, memory.BASE
models = memory.models

class SdkError(Exception):
    def __init__(self, message, code=""):
        super().__init__(message)
        self.code = code

class Err:
    def __init__(self, error):
        self.error = error

env = {"asyncio": asyncio, "contextlib": contextlib, "uuid": uuid, "Any": Any,
       "TARGETED_HINT_MAX_CHARS": 240,
       "TutorReply": models.TutorReply, "public_current_question_payload": models.public_current_question_payload,
       "SdkError": SdkError, "Err": Err, "Ok": lambda payload: payload,
       "LLM_OPERATION_QUESTION_GENERATE": "question_generate", "LLM_OPERATION_ANSWER_EVALUATE": "answer_evaluate",
       "_validate_optional_vision_image_payload": lambda *args, **kwargs: "",
       "_entry_exception_error": lambda _self, error, **kwargs: Err(error)}
tree = ast.parse((SOURCE / "entry_tutor_question_entries.py").read_text(encoding="utf-8"))
helpers = {"_question_private_payload", "_compact_text", "_safe_hint", "_targeted_public_payload"}
nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in helpers]
question_class = next(n for n in tree.body if isinstance(n, ast.ClassDef))
nodes += [n for n in question_class.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "_generate_question_payload"]
answer_tree = ast.parse((BASE / "entry_tutor_answer_entries.py").read_text(encoding="utf-8"))
answer_class = next(n for n in answer_tree.body if isinstance(n, ast.ClassDef))
for node in answer_class.body:
    if isinstance(node, ast.AsyncFunctionDef) and node.name in {"study_evaluate_answer", "_clear_attempt_evaluation_reservation"}:
        node.decorator_list = []
        nodes.append(node)
exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])), "native-question-entries", "exec"), env)

class Harness(memory.ProductHarness):
    _generate_question_payload = env["_generate_question_payload"]
    study_evaluate_answer = env["study_evaluate_answer"]
    _clear_attempt_evaluation_reservation = env["_clear_attempt_evaluation_reservation"]
    _resolve_study_target_lanlan = lambda self, kwargs: None
    _resolve_current_run_id = lambda self, kwargs: "offline"
    _screen_classification_context = lambda self: {}

    async def _emit_answer_evaluated_event(self, **kwargs):
        pass

class LocalModel:
    def __init__(self):
        self.grades = []

    async def question_generate(self, text, **kwargs):
        return models.TutorReply(operation="question_generate", input_text=text,
            reply="Which call subscribes? A: read B: watch", payload={
                "question": "Which call subscribes? A: read B: watch", "answer": "B",
                "reference_answer": "B", "topic": "Provider", "hint": "B",
                "key_points": ["watch subscribes"], "rubric": {"correct": "B"}})

    async def answer_evaluate(self, **kwargs):
        assert kwargs["expected_answer"] == "B"
        assert kwargs["context"]["question_payload"]["internal_private_payload"]["answer"] == "B"
        self.grades.append(kwargs)
        correct = kwargs["answer"] == kwargs["expected_answer"]
        return models.TutorReply(operation="answer_evaluate", input_text=kwargs["answer"], reply="feedback",
            payload={"verdict": "correct" if correct else "wrong", "score": 100 if correct else 0,
                     "feedback": "watch subscribes", "error_type": "none" if correct else "concept_confusion"})

class ManualQuestionTest(unittest.IsolatedAsyncioTestCase):
    async def test_manual_ids_private_answer_native_grading(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".tmp-uv-cache") as temp:
            store = memory.Store(Path(temp) / "study.db", Path(temp) / "unused.json", memory.logging.getLogger("manual-question-test"))
            store.open()
            try:
                plugin = Harness(store)
                plugin._agent = LocalModel()
                await plugin._restart_study_session(course_id="flutter-provider")
                for answer, expected_score in [("A", 0), ("B", 100)]:
                    public = await plugin._generate_question_payload(source_text="COMPSCI734 Provider MCQ", topic="")
                    self.assertTrue(public["question_id"])
                    self.assertTrue(public["attempt_id"])
                    self.assertEqual(public["topic"], "Provider")
                    for key in models.PRIVATE_CURRENT_QUESTION_FIELDS:
                        self.assertNotIn(key, public)
                    self.assertEqual(public["hint"], "")
                    self.assertEqual(plugin._state.current_question["answer"], "B")
                    history = store.list_interactions(1)[0]["metadata"]["payload"]
                    self.assertNotIn("answer", history)
                    self.assertNotIn("internal_private_payload", history)
                    wrong_id = await plugin.study_evaluate_answer(answer=answer, question_id="stale", attempt_id=public["attempt_id"])
                    self.assertIsInstance(wrong_id, Err)
                    self.assertEqual(wrong_id.error.code, "QUESTION_MISMATCH")
                    grade = await plugin.study_evaluate_answer(answer=answer, question_id=public["question_id"], attempt_id=public["attempt_id"])
                    self.assertEqual(grade["score"], expected_score)
                    self.assertTrue(plugin._state.current_question["attempt_evaluated"])
                    repeat = await plugin.study_evaluate_answer(answer=answer, question_id=public["question_id"], attempt_id=public["attempt_id"])
                    self.assertIsInstance(repeat, Err)
                    self.assertEqual(repeat.error.code, "ATTEMPT_ALREADY_EVALUATED")
                self.assertEqual(len(plugin._agent.grades), 2)
                self.assertEqual(len(store.list_qa_records(course_id="flutter-provider")), 2)
            finally:
                store.close()

if __name__ == "__main__":
    unittest.main(verbosity=2)
