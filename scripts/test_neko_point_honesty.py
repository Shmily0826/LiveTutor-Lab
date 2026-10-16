"""R4: study_point only ever licenses "I highlighted it" after an accepted request.

The real tool method over a real local learning surface (including the real forward diagram HTML);
no model, no Native, no audio.
"""
import ast
import os
from pathlib import Path
import re
import tempfile
import threading
import types
import unittest
from unittest.mock import patch

import httpx

from neko_learning_surface import LearningSurface

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "patches/neko-study-2026-10-10-product/payload/study_companion/study_avatar_tools.py"
tree = ast.parse(PATH.read_text(encoding="utf-8"))
method = next(n for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef) and n.name == "study_point_tool")
method.decorator_list = []
scope = {"os": os, "re": re, "httpx": httpx}
exec(compile(ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])), str(PATH), "exec"), scope)
POINT = scope["study_point_tool"]
FORWARD = ROOT / ".archify/architecture-relations-20261013-230748/forward/forward.html"
SOURCE = "**`lib/weather_service.dart`**\n```dart\n13\tFuture<Weather> fetchWeather(AppLocation location) async {\n14\t  final uri = Uri.parse(\"/api/weather\");\n```"


class Honesty(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        plain = Path(self.temp.name) / "plain.html"
        plain.write_text("<p>no targets here</p>", encoding="utf-8")
        self.materials = [plain] + ([FORWARD] if FORWARD.is_file() else [])
        self.surface = LearningSurface(self.materials, port=0)
        threading.Thread(target=self.surface.serve_forever, daemon=True).start()
        self.env = patch.dict(os.environ, {"NEKO_LEARNING_SURFACE_URL": f"http://127.0.0.1:{self.surface.server_port}",
                                           "NEKO_LEARNING_SURFACE_TOKEN": self.surface.token})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.surface.shutdown()
        self.surface.server_close()
        self.temp.cleanup()

    async def point(self, **kwargs):
        return await POINT(types.SimpleNamespace(), **kwargs)

    def assert_nothing_highlighted(self, result, *needles):
        self.assertFalse(result["ok"], result)
        self.assertIs(result["highlighted"], False)
        self.assertIn("Nothing was highlighted", result["relay"])
        self.assertTrue(result["say_this"])
        for needle in needles:
            self.assertIn(needle, result["say_this"])
        for claim in ("标出来了", "指给你", "已经高亮", "highlighted it"):
            self.assertNotIn(claim, result["say_this"])
        self.assertIsNone(self.surface.command)

    async def test_surface_not_open(self):
        with patch.dict(os.environ, {"NEKO_LEARNING_SURFACE_URL": "", "NEKO_LEARNING_SURFACE_TOKEN": ""}):
            result = await self.point(kind="selector", selector="[data-node-id=\"x\"]", material_id="m")
        self.assert_nothing_highlighted(result, "没有打开")

    async def test_unreachable_surface(self):
        with patch.dict(os.environ, {"NEKO_LEARNING_SURFACE_URL": "http://127.0.0.1:9"}):
            result = await self.point(kind="status")
        self.assert_nothing_highlighted(result, "没有响应")

    async def test_source_not_selected_stale_and_missing_identity(self):
        self.assert_nothing_highlighted(await self.point(kind="source", source_line=13), "没有选中源码")
        self.assert_nothing_highlighted(await self.point(kind="source", source_line=0), "有效的行号")
        self.assert_nothing_highlighted(await self.point(kind="selector", selector="[data-line=\"x\"]"), "还没确认")
        active = self.surface.active_material_id
        self.assert_nothing_highlighted(await self.point(kind="selector", selector="[data-line=\"x\"]", material_id="old-" + active))
        self.assertIsNone(self.surface.command)

    async def test_english_wording(self):
        result = await self.point(kind="source", source_line=13, language="en-US")
        self.assert_nothing_highlighted(result, "No source material")

    async def test_rejected_by_the_surface_is_not_a_highlight(self):
        active = self.surface.active_material_id
        result = await self.point(kind="rect", material_id=active, x=0.1, y=0.1, width=0.2, height=0.2)
        self.assertFalse(result["ok"])
        self.assertIs(result["highlighted"], False)
        self.assertTrue(result["say_this"])
        self.assertIsNone(self.surface.command)

    async def test_status_alone_highlights_nothing(self):
        result = await self.point(kind="status")
        self.assertTrue(result["ok"])
        self.assertIs(result["highlighted"], False)
        self.assertIn("nothing is highlighted yet", result["relay"])
        self.assertNotIn("say_this", result)
        self.assertIsNone(self.surface.command)

    async def test_accepted_source_request_is_the_only_success_wording(self):
        shown = self.surface.show_code_evidence({"evidence": SOURCE, "project": "fixture", "repo_commit": "sha1"})
        self.surface.select(shown["material_id"])
        result = await self.point(kind="source", source_line=13, symbol="fetchWeather")
        self.assertTrue(result["ok"], result)
        self.assertIs(result["highlighted"], True)
        self.assertEqual(result["say_this"], "已请求高亮当前源码第13行。")
        self.assertIsNotNone(self.surface.command)


    async def test_rejected_selector_returns_the_open_material_and_its_targets(self):
        shown = self.surface.show_code_evidence({"evidence": SOURCE, "project": "fixture", "repo_commit": "sha1"})
        self.surface.select(shown["material_id"])
        result = await self.point(kind="selector", material_id="study_picture", selector=".arrow.invented")
        self.assertFalse(result["ok"])
        self.assertIs(result["highlighted"], False)
        current = result["current_material"]
        self.assertEqual(current["material_id"], shown["material_id"])
        self.assertTrue(current["targets"] and all(t["selector"] for t in current["targets"]))
        self.assertIn("Nothing was highlighted", result["next"])
        self.assertIn("single retry", result["relay"])
        self.assertIsNone(self.surface.command)  # nothing substituted on the learner's behalf

    async def test_rejection_without_a_retry_path_has_no_retry_wording(self):
        result = await self.point(kind="source", source_line=13)
        self.assertNotIn("single retry", result["relay"])

    @unittest.skipUnless(FORWARD.is_file(), "forward diagram HTML not present")
    async def test_html_edge_can_be_found_by_status_and_accepted(self):
        forward = next(m for m in self.surface.materials.values() if m.get("source_path") == str(FORWARD)
                       or str(m.get("title", "")).lower().startswith("forward") or m is not None and "link0" in str(m.get("targets_for_pointing")))
        self.surface.select(forward["id"])
        status = await self.point(kind="status")
        targets = status["material"]["targets_for_pointing"]
        edge = next(t for t in targets if "wex" in t["label"].lower() and "nud" in t["label"].lower())
        self.assertEqual(edge["selector"], '[data-edge-id="link0"]')
        result = await self.point(kind="selector", material_id=status["active_material_id"], selector=edge["selector"],
                                  label="WEX → NUD")
        self.assertTrue(result["ok"], result)
        self.assertIs(result["highlighted"], True)
        self.assertEqual(self.surface.command["selector"], '[data-edge-id="link0"]')


if __name__ == "__main__":
    unittest.main()
