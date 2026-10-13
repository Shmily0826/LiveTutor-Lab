"""Offline: actual StudyStore and product methods, only fresh temporary data."""
from __future__ import annotations

import ast
import importlib
import logging
from pathlib import Path
import sys
import tempfile
import unittest
import uuid

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_neko_product_course_memory import ProductHarness, Store, models, prompts, SOURCE

prefs = importlib.import_module("product_study.learning_preferences")

question_tree = ast.parse((SOURCE / "entry_tutor_question_entries.py").read_text(encoding="utf-8"))
question_class = next(node for node in question_tree.body if isinstance(node, ast.ClassDef))
question_method = next(node for node in question_class.body if getattr(node, "name", "") == "_generate_question_payload")
private_function = next(node for node in question_tree.body if getattr(node, "name", "") == "_question_private_payload")
namespace = {"Any": object, "uuid": uuid, "TutorReply": models.TutorReply,
             "LLM_OPERATION_QUESTION_GENERATE": "question_generate",
             "_targeted_public_payload": models.public_current_question_payload}
exec(compile(ast.fix_missing_locations(ast.Module(body=[private_function, question_method], type_ignores=[])),
             str(SOURCE / "entry_tutor_question_entries.py"), "exec"), namespace)


class PreferencesTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "study.db"
        self.seed = Path(self.temp.name) / "unused.json"
        self.store = Store(self.db, self.seed, logging.getLogger("learning-preferences"))
        self.store.open()

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    async def test_explicit_preferences_survive_restart_and_temporary_does_not(self):
        defaults = prefs.load_preferences(self.store)
        self.assertEqual(defaults["length"], "brief")
        self.assertFalse(defaults["proactive_quiz"])
        transient = prefs.update_preferences(self.store, {"length": "detailed", "language": "en-US"})
        self.assertEqual(transient["preferences"]["language"], "en-US")
        self.assertFalse(transient["persisted"])
        self.assertIsNone(self.store.get_raw(prefs.PREFERENCES_KEY))
        prefs.update_preferences(self.store, {"language": "en-US", "explanation_style": "example_first"}, remember=True)
        prefs.update_preferences(self.store, {"length": "detailed", "proactive_quiz": True}, remember=True)
        self.store.close()
        self.store = Store(self.db, self.seed, logging.getLogger("learning-preferences"))
        self.store.open()
        plugin = ProductHarness(self.store)
        await plugin._restart_study_session(course_id="flutter")
        first = await plugin._build_learning_context("concept_explain", input_text="read?", extra={"language": "zh-CN"})
        await plugin._restart_study_session(course_id="math")
        second = await plugin._build_learning_context("concept_explain", input_text="sum?")
        self.assertEqual(first["learning_preferences"], second["learning_preferences"])
        self.assertEqual(first["learning_preferences"]["explanation_style"], "example_first")
        self.assertEqual(first["language"], "zh-CN")
        prefs.update_preferences(self.store, {"length": "brief"}, remember=False)
        self.assertEqual(prefs.load_preferences(self.store)["length"], "detailed")

    def test_invalid_updates_never_overwrite_existing_preference(self):
        prefs.update_preferences(self.store, {"length": "brief"}, remember=True)
        for bad in ({"language": "invented"}, {"proactive_quiz": "false"}, {"proactive_quiz": 1},
                    {"unknown": "value"}, {"length": "brief", "explanation_style": "invented"}):
            with self.assertRaises(ValueError):
                prefs.update_preferences(self.store, bad, remember=True)
            self.assertEqual(self.store.get_raw(prefs.PREFERENCES_KEY), {"length": "brief"})
        prefs.update_preferences(self.store, {"length": "detailed"}, remember="true")
        self.assertEqual(prefs.load_preferences(self.store)["length"], "brief")
        self.store.set_raw(prefs.PREFERENCES_KEY, {"language": "en-US", "length": 42, "api_key": "UNTRUSTED_SECRET"})
        loaded = prefs.load_preferences(self.store)
        self.assertEqual(loaded["language"], "en-US")
        self.assertEqual(loaded["length"], "brief")
        self.assertNotIn("UNTRUSTED_SECRET", prefs.preference_prompt(loaded))

    def test_saved_defaults_enter_every_teaching_prompt(self):
        preferences = {"length": "balanced", "explanation_style": "example_first", "proactive_quiz": False}
        for operation in ("concept_explain", "question_generate", "answer_evaluate", "knowledge_track", "summarize_session"):
            messages = prompts.build_operation_messages(operation, {"learning_preferences": preferences,
                "language": "zh-CN", "source_text": "Explain Provider", "question": "What listens?",
                "answer": "read", "expected_answer": "watch"})
            self.assertIn('"explanation_style": "example_first"', messages[0]["content"])
            self.assertIn("do not append an unsolicited quiz", messages[0]["content"])
            self.assertIn("Explicit current requests", messages[0]["content"])

    async def test_pending_temporary_preferences_apply_once_without_saving(self):
        prefs.update_preferences(self.store, {"length": "detailed", "proactive_quiz": True}, remember=True)
        plugin = ProductHarness(self.store)
        await plugin._restart_study_session(course_id="flutter")
        plugin._study_turn_preferences = {"length": "brief", "proactive_quiz": False}
        current = await plugin._build_learning_context("concept_explain", input_text="Explain briefly")
        self.assertEqual(current["learning_preferences"]["length"], "brief")
        self.assertFalse(current["learning_preferences"]["proactive_quiz"])
        messages = prompts.build_operation_messages("concept_explain", current)
        self.assertIn("Current turn teaching preferences", messages[0]["content"])
        later = await plugin._build_learning_context("concept_explain", input_text="Follow up")
        self.assertEqual(later["learning_preferences"]["length"], "detailed")
        self.assertTrue(later["learning_preferences"]["proactive_quiz"])
        self.assertEqual(prefs.load_preferences(self.store)["length"], "detailed")

    async def test_selected_concept_survives_model_label_drift_and_restart(self):
        plugin = ProductHarness(self.store)
        session = await plugin._restart_study_session(course_id="flutter")
        for label, verdict in [("Provider read versus watch", "wrong"), ("Notification rebuild behavior", "correct")]:
            grade = models.TutorReply(operation="answer_evaluate", input_text=verdict, reply=verdict,
                                     payload={"topic": label, "verdict": verdict, "score": 0 if verdict == "wrong" else 100})
            tracked = models.TutorReply(operation="knowledge_track", input_text=verdict, reply=label, payload={"topic": label})
            await plugin._record_answer_knowledge(grade, tracked, extra_context={"session_id": session, "course_id": "flutter",
                "selected_topic_id": "flutter::Provider", "question": "Which call listens?", "answer": verdict,
                "question_payload": {"topic": label, "answer": "watch"}})
        rows = self.store.list_qa_records(course_id="flutter")
        self.assertEqual([row["topic_id"] for row in rows], ["flutter::Provider"] * 2)
        self.assertEqual(len(self.store.list_fsrs_cards(topic_ids=["flutter::Provider"])), 1)
        self.store.close()
        self.store = Store(self.db, self.seed, logging.getLogger("learning-preferences"))
        self.store.open()
        plugin = ProductHarness(self.store)
        await plugin._restart_study_session()
        context = await plugin._build_learning_context("concept_explain", input_text="What did I fix?")
        rendered = prompts.build_concept_recent_context(context)
        self.assertIn('"verdict": "wrong"', rendered)
        self.assertIn('"verdict": "correct"', rendered)

    async def test_manual_generation_keeps_explicit_existing_topic(self):
        plugin = ProductHarness(self.store)
        async def build(*args, **kwargs):
            return {"selected_topic_id": "flutter::Provider"}
        async def generate(*args, **kwargs):
            return models.TutorReply(operation="question_generate", input_text="material", reply="quiz",
                                    payload={"topic": "Model fresh label", "question": "Which call listens?", "answer": "watch"})
        async def finalize(operation, reply, **kwargs):
            return reply.payload
        plugin._build_learning_context = build
        plugin._agent = type("Agent", (), {"question_generate": staticmethod(generate)})()
        plugin._finalize_tutor_call = finalize
        result = await namespace["_generate_question_payload"](plugin, source_text="Provider material", topic="flutter::Provider")
        self.assertEqual(result["topic"], "flutter::Provider")
        self.assertEqual(result["question_topic_label"], "Model fresh label")
        self.assertFalse(result["attempt_evaluated"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
