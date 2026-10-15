"""Production error/quiz regression: loopback refusal only, no provider or host launch."""
from __future__ import annotations

import ast
import asyncio
from copy import deepcopy
from http import HTTPStatus
import json
from pathlib import Path
import re
import sys
from types import SimpleNamespace, MethodType, ModuleType
import unittest
import importlib.util

import httpx
from openai import APIConnectionError

ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = ROOT / "patches/neko-study-2026-10-10-product/payload/study_companion"
material_spec=importlib.util.spec_from_file_location('failure_materials',PAYLOAD/'study_materials.py')
materials=importlib.util.module_from_spec(material_spec);material_spec.loader.exec_module(materials)
failure_package=ModuleType('failure_product');failure_package.__path__=[str(PAYLOAD)]
sys.modules['failure_product']=failure_package
sys.modules['failure_product.study_materials']=materials
sys.path.insert(0, str(ROOT / "scripts"))
import neko_desktop_tutor_host as host


def definitions(path, names, namespace, *, method=""):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    selected = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names:
            selected.append(node)
        elif isinstance(node, ast.Assign) and any(getattr(target, "id", "") in names for target in node.targets):
            selected.append(node)
        elif method and isinstance(node, ast.ClassDef):
            for child in node.body:
                if getattr(child, "name", "") == method or getattr(child, "name", "") in names:
                    child.decorator_list = []
                    selected.append(child)
    module = ast.Module(body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0),
                             *selected], type_ignores=[])
    exec(compile(ast.fix_missing_locations(module), str(path), "exec"), namespace)
    return namespace


class TeachingFailureTest(unittest.TestCase):
    def test_submitted_picture_survives_first_session_and_replaces_old_material(self):
        ns = definitions(PAYLOAD / "entry_tutor_explain_entries.py", set(),
                         {"_normalize_submitted_image_payload": lambda raw: "validated:"+raw,
                          "_plugin_lock": lambda lock: lock,"material_context":materials.material_context,
                          "material_changes":materials.material_changes,
                          "submit_material_changes":materials.submit_material_changes}, method="study_submit_image")
        async def scenario():
            state = SimpleNamespace(last_vision_image_base64="old picture", last_ocr_text="old OCR", study_course_id="image-course")
            seen = []
            async def start_session():
                state.last_vision_image_base64 = ""
                state.last_ocr_text = ""
            async def explain(**kwargs):
                seen.append((state.last_vision_image_base64, state.last_ocr_text, kwargs))
                return {"reply": "actual model output"}
            plugin = SimpleNamespace(_cfg=SimpleNamespace(llm_vision_enabled=True, language="zh-CN"),
                                     _state=state, _lock=asyncio.Lock(), _study_session_id="image-session",
                                     _ensure_active_study_session=start_session, study_explain_text=explain)
            await ns["study_submit_image"](plugin, image_base64="first", text="新图问题")
            self.assertEqual(seen[-1][0:2], ("validated:first", "新图问题"))
            ns["_image_only_explain_prompt"] = lambda _: "只解释新图"
            await ns["study_submit_image"](plugin, image_base64="second", text="")
            self.assertEqual(seen[-1][0:2], ("validated:second", ""))
            self.assertEqual(seen[-1][2]["vision_image_base64"], "validated:second")
            self.assertEqual(seen[-1][2]["_material_context"], materials.material_context(plugin))
        asyncio.run(scenario())

    def test_fine_diagram_details_preserve_explicit_quality_and_source_messages(self):
        ns = definitions(PAYLOAD / "study_model_gateway.py", {"_high_detail_study_images"},
                         {"deepcopy": deepcopy})
        original = [{"role": "user", "content": [
            {"type": "text", "text": "读箭头"},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,example", "detail": "auto"}},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,other", "detail": "low"}}]}]
        before = deepcopy(original)
        result = ns["_high_detail_study_images"](original)
        self.assertEqual(original, before)
        self.assertEqual(result[0]["content"][1]["image_url"]["detail"], "high")
        self.assertEqual(result[0]["content"][2]["image_url"]["detail"], "low")
        self.assertEqual(result[0]["content"][0], original[0]["content"][0])

    def test_diagram_without_observed_relations_never_calls_text_model(self):
        names = {"RELAY_NOTE", "_FENCE_LINE", "_FENCE_MARK", "_CODE_SPAN", "_SPEAKABLE_FIELDS",
                 "_speakable", "_teaching_failure_wording", "_teaching", "_RANGE_MARK", "_ZH_LINE_RANGE", "_ZH_LINE_ONE", "_FILE_LINE", "_EN_LINE_RANGE", "_CJK", "_zh_number", "_spoken_line_refs"}
        ns = definitions(PAYLOAD / "study_avatar_tools.py", names,
                         {"json": json, "re": re, "_turn_language_request": lambda *_: "",
                          "__name__": "failure_product.avatar", "__package__": "failure_product"},
                         method="study_explain_tool")
        async def scenario():
            async def unexpected(**kwargs):
                self.fail("missing diagram material reached the text model")
            plugin = SimpleNamespace(_study_effective_language=lambda: "zh-CN",
                                     study_explain_text=unexpected)
            result = await ns["study_explain_tool"](plugin, question="这张架构图的箭头从哪里出发？")
            self.assertEqual(result["diagnostic"], "visual_context_missing")
            self.assertTrue(result["degraded"])
            self.assertIn("模块和箭头", result["reply"])
            self.assertNotIn("服务恢复", result["reply"])
        asyncio.run(scenario())

    def test_actual_proxy_refusal_is_quota_not_provider_failure(self):
        ns = definitions(PAYLOAD / "study_model_gateway.py", {
            "_nonnegative_int", "_generic_error_details", "_diagnostic_for_generic_error"},
            {"asyncio": asyncio, "HTTPStatus": HTTPStatus})
        classify = ns["_diagnostic_for_generic_error"]

        async def scenario():
            sink = host.Sink(0)  # In-memory cap: cannot reserve or contact any upstream.
            sink._tunnel = lambda *_: self.fail("exhausted request reached upstream")
            sink.start()
            try:
                async with httpx.AsyncClient(proxy=f"http://127.0.0.1:{sink.port}", timeout=3) as client:
                    with self.assertRaises(httpx.ProxyError) as caught:
                        await client.get("https://api.deepseek.com/")
                outer = APIConnectionError(request=httpx.Request("POST", "https://api.deepseek.com/v1/chat/completions"))
                outer.__cause__ = caught.exception
                self.assertEqual(classify(outer, has_image=False), "agent_quota_exceeded")
                self.assertEqual(sink.paid, 0)
                self.assertEqual(sink.snapshot()[0]["action"], "budget_exhausted")
                self.assertEqual(classify(httpx.ConnectError("unreachable"), has_image=False), "provider_unavailable")
                self.assertEqual(classify(httpx.ProxyError("403 Forbidden"), has_image=False), "llm_call_failed")
            finally:
                sink.stop = True
                sink._server.close()
        asyncio.run(scenario())

    def test_restarted_avatar_uses_persisted_current_course_question(self):
        names = {"RELAY_NOTE", "_FENCE_LINE", "_FENCE_MARK", "_CODE_SPAN", "_SPEAKABLE_FIELDS",
                 "_speakable", "_teaching_failure_wording", "_teaching", "_envelope", "_first_text", "_relay_for", "_RANGE_MARK", "_ZH_LINE_RANGE", "_ZH_LINE_ONE", "_FILE_LINE", "_EN_LINE_RANGE", "_CJK", "_zh_number", "_spoken_line_refs",
                 "_study_native_material_snapshot", "_study_changed_native_material_result", "_study_bind_native_teaching_result"}
        ns = definitions(PAYLOAD / "study_avatar_tools.py", names,
                         {"json": json, "re": re, "asyncio": asyncio, "__name__":"failure_product.avatar", "__package__":"failure_product"},
                         method="study_answer_tool")
        method = ns["study_answer_tool"]

        async def scenario():
            calls = []
            async def evaluate(**kwargs):
                calls.append(kwargs)
                return {"feedback": "参数是函数接收的输入。", "verdict": "correct", "score": 100}
            async def ensure():return "persisted-session"
            plugin = SimpleNamespace(_state=SimpleNamespace(study_course_id="course-B",current_question={"question_id": "course-B-question",
                "attempt_id": "persisted-attempt"}), _avatar_last_question={"question_id": "stale-course-A",
                "attempt_id": "stale-attempt"}, _study_effective_language=lambda: "zh-CN", study_evaluate_answer=evaluate,
                _lock=asyncio.Lock(),_study_session_id="persisted-session",_ensure_active_study_session=ensure)
            for name in ("_study_native_material_snapshot","_study_changed_native_material_result","_study_bind_native_teaching_result"):
                setattr(plugin,name,MethodType(ns[name],plugin))
            reply = await method(plugin, answer="参数是输入")
            self.assertEqual(calls, [{"answer": "参数是输入", "question_id": "course-B-question",
                                     "attempt_id": "persisted-attempt", "_material_context": {"course_id":"course-B","session_id":"persisted-session"}}])
            self.assertEqual(reply["score"], 100)
            # No cached question in a freshly re-created avatar is required.
            del plugin._avatar_last_question
            calls.clear()
            await method(plugin, answer="参数是输入")
            self.assertEqual(calls[0]["attempt_id"], "persisted-attempt")

            async def failed(**kwargs):
                return {"feedback": "local fallback", "degraded": True, "diagnostic": "agent_quota_exceeded",
                        "score": 0, "verdict": "wrong"}
            plugin.study_evaluate_answer = failed
            unavailable = await method(plugin, answer="参数是输入")
            self.assertEqual(unavailable["status"], "unavailable")
            self.assertNotIn("score", unavailable)
            self.assertNotIn("verdict", unavailable)
            self.assertEqual(plugin._state.current_question["attempt_id"], "persisted-attempt")
        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main(verbosity=2)
