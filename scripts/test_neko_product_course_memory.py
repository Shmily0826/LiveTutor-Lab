"""Offline product regression: actual Store/Tracker, fresh temporary database only.

No host, capture, provider, microphone, or audio is imported or started.
"""
from __future__ import annotations

import ast
import asyncio
from contextlib import asynccontextmanager
import importlib
import logging
from pathlib import Path
import sys
import tempfile
import time
import types
import unittest
import uuid
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "patches/neko-study-2026-10-10-product/payload/study_companion"
BASE = ROOT / "benchmarks/raw/neko-app/resources/bin/plugins/study_companion"
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "candidates/N.E.K.O"))
package = types.ModuleType("product_study")
package.__path__ = [str(SOURCE), str(BASE)]
sys.modules[package.__name__] = package
models = importlib.import_module("product_study.models")
constants = importlib.import_module("product_study.constants")
Store = importlib.import_module("product_study.store").StudyStore
Tracker = importlib.import_module("product_study.knowledge_tracker").KnowledgeTracker

@asynccontextmanager
async def plugin_lock(lock):
    async with lock:
        yield

common = types.ModuleType("product_study.entry_common")
for name, value in {"Any": Any, "asyncio": asyncio, "time": time,
                    "StudyEvent": lambda **kwargs: kwargs,
                    "TutorReply": models.TutorReply, "utc_now_iso": models.utc_now_iso,
                    "build_tutor_payload": lambda reply: dict(reply.payload or {}),
                    "diagnostic_code_for_exception": lambda error: type(error).__name__,
                    "_detect_mastery_threshold_crossed": lambda before, after: None,
                    "_plugin_lock": plugin_lock}.items():
    setattr(common, name, value)
for name in dir(constants):
    if name.startswith("LLM_OPERATION_"):
        setattr(common, name, getattr(constants, name))
sys.modules[common.__name__] = common
context_module = importlib.import_module("product_study.entry_tutor_context_support")
prompts = importlib.import_module("product_study.llm_prompts")

# Execute the product's actual session lifecycle methods without importing the
# desktop host and its audio/config initialization.
tree = ast.parse((SOURCE / "__init__.py").read_text(encoding="utf-8"))
plugin_class = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "StudyCompanionPlugin")
names = {"_start_study_session_locked", "_end_study_session_locked", "_restart_study_session", "_ensure_active_study_session"}
methods = ast.Module(body=[node for node in plugin_class.body if isinstance(node, ast.AsyncFunctionDef) and node.name in names], type_ignores=[])
namespace = {"asyncio": asyncio, "uuid": uuid, "time": time}
exec(compile(ast.fix_missing_locations(methods), str(SOURCE / "__init__.py"), "exec"), namespace)
summary_tree = ast.parse((SOURCE / "entry_tutor_summary_entries.py").read_text(encoding="utf-8"))
summary_class = next(node for node in summary_tree.body if isinstance(node, ast.ClassDef))
summary_method = next(node for node in summary_class.body if isinstance(node, ast.AsyncFunctionDef) and node.name == "study_summarize_session")
summary_method.decorator_list = []
namespace.update({"LLM_OPERATION_SUMMARIZE_SESSION": "summarize_session", "Ok": lambda value: value})
exec(compile(ast.fix_missing_locations(ast.Module(body=[summary_method], type_ignores=[])), str(SOURCE / "entry_tutor_summary_entries.py"), "exec"), namespace)

class ProductHarness(context_module._TutorContextSupportMixin):
    def __init__(self, store):
        self._store = store
        self._knowledge_tracker = Tracker(store)
        self._state = store.load_state(models.StudyState(active_mode="teaching"))
        self._cfg = models.StudyConfig()
        self._lock = asyncio.Lock()
        self._study_session_lock = asyncio.Lock()
        self._study_session_id = ""
        self._study_session_last_activity = 0
        self._ocr_pipeline = None
        self._event_bus = None
        self.logger = logging.getLogger("course-memory-test")

    def _state_snapshot(self):
        return self._state.to_dict()

    async def _persist_state(self):
        self._store.save_state(self._state)

    async def _build_knowledge_guidance_context(self, *args, **kwargs):
        return {}, {}

    def _merge_session_summary_seed(self, operation, *, payload, seed):
        return dict(seed)

    async def _emit_session_summarized_event(self, payload):
        pass

for name in names:
    setattr(ProductHarness, name, namespace[name])
ProductHarness.study_summarize_session = namespace["study_summarize_session"]

class CourseMemoryTest(unittest.IsolatedAsyncioTestCase):
    async def test_restart_course_history_errors_and_isolation(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".tmp-uv-cache") as temp:
            db = Path(temp) / "study.db"
            seed = Path(temp) / "unused.json"
            store = Store(db, seed, logging.getLogger("course-memory-test"))
            store.open()
            plugin = ProductHarness(store)
            session_a = await plugin._restart_study_session(course_id="flutter-provider")
            store.append_interaction(kind="concept_explain", input_text="Flutter context.watch rebuild",
                                     output_text="A listening widget rebuilds.", metadata={}, session_id=session_a)
            for verdict, answer in [("wrong", "read rebuilds"), ("correct", "watch listens")]:
                reply = models.TutorReply(operation="answer_evaluate", input_text=answer, reply=verdict,
                                          payload={"verdict": verdict, "score": 0 if verdict == "wrong" else 100,
                                                   "error_type": "concept_confusion" if verdict == "wrong" else "none"})
                await plugin._record_answer_knowledge(reply, models.TutorReply(operation="knowledge_track", input_text=answer,
                                                     reply="Provider", payload={"topic": "Provider"}),
                    extra_context={"session_id": session_a, "course_id": "flutter-provider", "answer": answer,
                                   "question": "Flutter: which Provider call subscribes to rebuild?",
                                   "question_payload": {"topic": "Provider", "answer": "watch"}})
            self.assertEqual(len(store.list_qa_records(course_id="flutter-provider")), 2)
            self.assertEqual(store.get_topic("flutter-provider::Provider")["subject"], "computer_science")
            self.assertEqual(len(store.list_fsrs_cards(topic_ids=["flutter-provider::Provider"])), 1)
            await plugin._end_study_session_locked()
            store.close()

            store = Store(db, seed, logging.getLogger("course-memory-test"))
            store.open()
            plugin = ProductHarness(store)
            self.assertEqual(plugin._state.study_course_id, "flutter-provider")
            session_b = await plugin._restart_study_session()
            self.assertNotEqual(session_a, session_b)
            context = await plugin._build_learning_context("concept_explain", input_text="What did I get wrong?", session_id=session_b)
            prompt = prompts.build_concept_recent_context(context)
            self.assertIn("read rebuilds", prompt)
            self.assertIn("watch listens", prompt)
            self.assertIn("Flutter context.watch", prompt)
            self.assertEqual(len(context["course_learning_state"]["mastery_overview"]), 1)

            other = await plugin._restart_study_session(course_id="math-integrals")
            context = await plugin._build_learning_context("concept_explain", input_text="integration", session_id=other)
            prompt = prompts.build_concept_recent_context(context)
            self.assertNotIn("read rebuilds", prompt)
            self.assertNotIn("Flutter context.watch", prompt)
            self.assertEqual(context["course_learning_state"]["topic_ids"], [])
            self.assertEqual(store.list_interactions(50, course_id="math-integrals"), [])
            self.assertEqual(plugin._knowledge_tracker._resolve_topic_id("math-integrals::Provider"), "math-integrals::Provider")
            quiz_context = await plugin._build_learning_context("question_generate", input_text="math quiz",
                                                                extra={"topic_hint": "Provider"}, session_id=other)
            self.assertFalse(quiz_context["knowledge_question_params"]["weak_topics"])
            self.assertFalse(quiz_context["knowledge_question_params"]["retry_wrong_question"])

            # A full 15-round lesson summary must retain its first interaction.
            for index in range(15):
                store.append_interaction(kind="concept_explain", input_text=f"math lesson {index}",
                                         output_text=f"result {index}", metadata={}, session_id=other)
            context = await plugin._build_learning_context("summarize_session", session_id=other)
            self.assertEqual(len(context["session_history"]), 15)
            self.assertTrue(any(row["input_text"] == "math lesson 0" for row in context["session_history"]))
            reply = models.TutorReply(operation="summarize_session", input_text="session", reply="Math summary",
                                      payload={"summary": "Math summary"})
            class SummaryAgent:
                async def summarize_session(agent_self, history, **kwargs):
                    self.assertEqual(len(history), 15)
                    self.assertEqual(len(kwargs["context"]["session_history"]), 15)
                    return reply
            plugin._agent = SummaryAgent()
            await plugin.study_summarize_session()
            self.assertTrue(any(row["kind"] == "summarize_session" for row in store.list_interactions(50, session_id=other)))
            store.close()

    def test_latest_history_keeps_latest_and_chronological(self):
        rendered = prompts._recent_history_items([{"id": i, "input_text": f"turn {i}", "output_text": "reply"} for i in range(15, 0, -1)])
        self.assertEqual(rendered[-1]["input"], "turn 15")

    def test_summary_serialization_keeps_late_grades_and_early_lesson(self):
        rows = [{"id": index, "kind": "concept_explain",
                 "input_text": f"ROUND_{index} " + "学习对象和页面更新的区别。" * 100,
                 "output_text": "逐步解释通知与订阅的关系。" * 300,
                 "metadata": {"payload": {"reply": "NESTED_DUPLICATE" * 500}}}
                for index in range(1, 16)]
        for index, verdict, score in [(13, "wrong", 0), (14, "correct", 100)]:
            rows[index]["kind"] = "answer_evaluate"
            rows[index]["metadata"] = {"question": "Which operation subscribes?",
                                       "payload": {"verdict": verdict, "score": score,
                                                   "feedback": "Actual grader feedback",
                                                   "misconceptions": ["confusing mutation with notification"],
                                                   "reply": "NESTED_DUPLICATE" * 500}}
        messages = prompts.build_summarize_session_messages(language="zh-CN", context={
            "session_history": list(reversed(rows)), "history": list(reversed(rows)),
            "previous_course_history": [{"input_text": "OTHER_COURSE"}],
            "course_learning_state": {"recent_answers": [{"question": "OTHER_COURSE"}]},
        })
        user_prompt = messages[1]["content"]
        serialized = __import__("json").loads(user_prompt.split("\n\ncontext:\n", 1)[1])
        history = serialized["session_history"]
        self.assertEqual([row["id"] for row in history], list(range(1, 16)))
        self.assertEqual(history[13]["evaluation"]["verdict"], "wrong")
        self.assertEqual(history[13]["evaluation"]["score"], 0)
        self.assertEqual(history[14]["evaluation"]["verdict"], "correct")
        self.assertEqual(history[14]["evaluation"]["score"], 100)
        self.assertNotIn("NESTED_DUPLICATE", user_prompt)
        self.assertNotIn("OTHER_COURSE", user_prompt)
        self.assertNotIn("history", serialized)

    def test_question_serialization_preserves_current_material_and_four_choices_request(self):
        current = "最新要求：请生成四选一选择题，明确列出 A、B、C、D，不要透露答案。\n"
        current += (ROOT / "lessons/flutter_provider/lib/main.dart").read_text(encoding="utf-8")
        current += "\nLATEST_MATERIAL_END：考查删除 notifyListeners 后内部状态与屏幕的区别。"
        context = {
            "history": [{"input_text": "OLD_HISTORY_QUESTION " + "旧课程材料" * 400,
                         "output_text": "旧的回答" * 600, "metadata": {"nested": "旧的重复回答" * 600}}
                        for _ in range(30)],
            "source_text": current,
            "text": current,
            "input_text": current,
        }
        messages = prompts.build_question_generate_messages(text=current, language="zh-CN", context=context)
        serialized = __import__("json").loads(messages[1]["content"].split("\n\ncontext:\n", 1)[1])
        self.assertEqual(serialized["source_text"], current)
        self.assertIn("四选一", serialized["source_text"])
        self.assertIn("LATEST_MATERIAL_END", serialized["source_text"])
        self.assertNotIn("text", serialized)
        self.assertNotIn("input_text", serialized)
        self.assertTrue(serialized["_prompt_truncated"])
        short = "CURRENT_SHORT_MATERIAL：请生成四选一题。"
        messages = prompts.build_question_generate_messages(text=short, language="zh-CN")
        default_context = __import__("json").loads(messages[1]["content"].split("\n\ncontext:\n", 1)[1])
        self.assertEqual(default_context["source_text"], short)
        with self.assertRaisesRegex(ValueError, "question source exceeds prompt budget"):
            prompts.build_question_generate_messages(text="超长新材料" * 20000, language="zh-CN")

if __name__ == "__main__":
    unittest.main(verbosity=2)
