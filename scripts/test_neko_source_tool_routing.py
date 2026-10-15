"""Tool discovery contract only; actual provider routing needs a Native scene."""
import ast
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "patches/neko-study-2026-10-10-product/payload/study_companion"


def schema(filename, name):
    tree = ast.parse((SOURCE / filename).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call) or getattr(decorator.func, "id", "") != "llm_tool":
                continue
            fields = {item.arg: item.value for item in decorator.keywords}
            if ast.literal_eval(fields["name"]) == name:
                return fields
    raise AssertionError(f"tool missing: {name}")


class SourceToolRouting(unittest.TestCase):
    def test_lookup_tool_defers_teaching_to_explain(self):
        fields = schema("study_code_tools.py", "study_code")
        description = ast.literal_eval(fields["description"])
        self.assertIn("Lookup source evidence only", description)
        self.assertIn("study_explain", description)
        self.assertIn("material_source=project_code", description)
        self.assertNotIn("Answer a question", description)
        self.assertNotIn("explore' takes a whole sentence", description)

    def test_teaching_tool_names_spoken_intents_and_optional_followup_requests(self):
        fields = schema("study_avatar_tools.py", "study_explain")
        description = ast.literal_eval(fields["description"])
        for intent in ("这段代码怎么处理", "这一行是什么意思", "如果改成", "再讲讲"):
            self.assertIn(intent, description)
        self.assertIn("material_source=project_code", description)
        self.assertIn("omit code_requests", description)
        parameters = ast.literal_eval(fields["parameters"])
        self.assertNotIn("code_requests", parameters.get("required", []))
        self.assertIn("project_code", parameters["properties"]["material_source"]["enum"])
        self.assertEqual(parameters["properties"]["code_requests"]["items"]["type"], "object")


if __name__ == "__main__":
    unittest.main()
