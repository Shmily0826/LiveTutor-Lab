"""Daily image/voice tool checks with actual SQLite; no host, model or audio."""
from __future__ import annotations
import asyncio
import importlib
import logging
from pathlib import Path
import tempfile
import unittest

from test_neko_product_course_memory import Store, ProductHarness
materials = importlib.import_module("product_study.study_materials")
preferences = importlib.import_module("product_study.learning_preferences")
avatar = importlib.import_module("product_study.study_avatar_tools")


class DailyHarness(ProductHarness, avatar._StudyAvatarToolsMixin):
    _study_effective_language = avatar._StudyAvatarToolsMixin._study_effective_language


def new_store(path):
    return Store(path, path.with_suffix(".seed.json"), logging.getLogger("daily-material-test"))


class DailyMaterialTest(unittest.TestCase):
    def test_natural_single_turn_language_requests_are_detected_without_saving(self):
        for text in ("Explain in exactly two English sentences, no quiz.", "Use English please.", "Speak English"):
            self.assertEqual(avatar._turn_language_request(text), "en-US")
        self.assertEqual(avatar._turn_language_request("Two Chinese sentences please"), "zh-CN")
        self.assertEqual(avatar._turn_language_request("From now on use English"), "")

    def test_latest_image_survives_restart_and_course_return(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "study.db"
            store = new_store(path); store.open()
            materials.save_material(store, "diagrams", "image-one", "forward")
            materials.save_material(store, "diagrams", "image-two", "reverse")
            store.close(); store = new_store(path); store.open()
            try:
                plugin = DailyHarness(store)
                asyncio.run(plugin._start_study_session_locked(course_id="diagrams"))
                self.assertEqual(plugin._state.last_vision_image_base64, "image-two")
                self.assertEqual(plugin._state.last_ocr_text, "reverse")
                asyncio.run(plugin._start_study_session_locked(course_id="new-course"))
                self.assertEqual(plugin._state.last_vision_image_base64, "")
                asyncio.run(plugin._start_study_session_locked(course_id="diagrams"))
                self.assertEqual(plugin._state.last_vision_image_base64, "image-two")
            finally: store.close()

    def test_preferences_course_override_and_current_material_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = new_store(Path(temporary) / "study.db"); store.open()
            try:
                plugin = DailyHarness(store)
                asyncio.run(plugin._start_study_session_locked(course_id="diagrams"))
                result = asyncio.run(plugin.study_preferences_tool(preferences={"language": "en-US", "length": "detailed", "proactive_quiz": True}, remember=True))
                self.assertTrue(result["persisted"])
                self.assertEqual(plugin._study_effective_language(), "en-US")
                plugin._state.teaching_language_by_course["diagrams"] = "zh-CN"
                self.assertEqual(plugin._study_effective_language(), "zh-CN")
                body = plugin._study_language_directive("current source", "Explain, no quiz this time", "en-US")
                self.assertIn("no quiz this time", body)
                self.assertNotIn("Keep the spoken answer brief by default.", body)
                self.assertNotIn("no self-quiz at the end.", body)
                self.assertEqual(plugin._cfg.language, "zh-CN")
                plugin._cfg.llm_vision_enabled = True
                plugin._state.last_vision_image_base64 = "image-one"
                first = asyncio.run(plugin.study_material_tool())
                plugin._state.last_vision_image_base64 = "image-two"
                second = asyncio.run(plugin.study_material_tool())
                self.assertNotEqual(first["material_id"], second["material_id"])
                self.assertNotIn("image-two", str(second))
                temporary_result = asyncio.run(plugin.study_preferences_tool(preferences={"length": "brief"}))
                self.assertFalse(temporary_result["persisted"])
                self.assertEqual(preferences.load_preferences(store)["length"], "detailed")
            finally: store.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
