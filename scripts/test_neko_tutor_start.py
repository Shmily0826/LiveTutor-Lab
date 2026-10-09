"""Offline status/launcher regression. Does not launch processes or read pixels."""
import ast
import copy
import json
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("tutor_start", ROOT / "scripts/neko_tutor_start.py")
start = importlib.util.module_from_spec(spec)
spec.loader.exec_module(start)


class ProductStartTest(unittest.TestCase):
    def test_waits_for_native_running_and_entry_registration(self):
        states = [
            {"status": "stopped", "entries": []},
            {"status": "running", "entries": []},
            {"status": "running", "entries": [{"id": name} for name in ("study_status", "study_explain_text", "study_ocr_snapshot")]},
        ]
        calls = []
        class Response:
            status = 200
            def __init__(self, payload): self.payload = payload
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self): return json.dumps(self.payload).encode()
        def open_url(url, timeout):
            calls.append(url)
            if url.endswith("/plugins/study_companion"):
                return Response({"plugin": states.pop(0)})
            self.assertEqual(len(states), 0, "Static UI must not open before native readiness")
            return Response({})
        opener = SimpleNamespace(open=open_url)
        launcher = SimpleNamespace(poll=lambda: None)
        with patch.object(start.urllib.request, "build_opener", return_value=opener), patch.object(start.time, "sleep") as sleep:
            self.assertEqual(start.plugin_server_ready(30, launcher), (True, ""))
        self.assertEqual(len(calls), 4)
        self.assertEqual(sleep.call_count, 2)

    def test_exited_launcher_never_opens_browser_ui(self):
        launcher = SimpleNamespace(poll=lambda: 1)
        with patch.object(start.urllib.request, "build_opener") as build:
            self.assertFalse(start.plugin_server_ready(30, launcher)[0])
            build.return_value.open.assert_not_called()

    def test_source_storage_and_budget(self):
        command = start.host_command(240, 30)
        self.assertEqual(command[0], str(start.host.SOURCE_PYTHON))
        self.assertIn("--source", command)
        self.assertEqual(command[command.index("--store") + 1], "neko-product-data")
        self.assertEqual(command[command.index("--api-budget") + 1], "30")
        self.assertEqual(command[command.index("--hold") + 1], "14520")

    def test_owned_flutter_lesson(self):
        command = start.lesson_command()
        self.assertEqual(command, [str(start.host.SOURCE_PYTHON), str(ROOT / "scripts/neko_flutter_lesson_window.py")])
        source = (ROOT / "scripts/neko_tutor_start.py").read_text(encoding="utf-8")
        self.assertIn("lesson = subprocess.Popen(lesson_command()", source)
        self.assertIn("lesson.terminate()", source)

    def test_task_browser_profile_and_mute(self):
        url = "http://127.0.0.1:48916/plugin/study_companion/ui/"
        command = start.chrome_command(url)
        profile = next(arg.split("=", 1)[1] for arg in command if arg.startswith("--user-data-dir="))
        self.assertTrue(Path(profile).is_relative_to(ROOT / "benchmarks/raw/neko-product-browser"))
        self.assertIn("--mute-audio", command)
        self.assertIn(f"--app={url}", command)
        self.assertEqual(profile, str(start.BROWSER_PROFILE))
        self.assertEqual(next(arg for arg in start.chrome_command(url) if arg.startswith("--user-data-dir=")), f"--user-data-dir={profile}")
        self.assertNotIn("webbrowser", (ROOT / "scripts/neko_tutor_start.py").read_text(encoding="utf-8"))

    def test_cleanup_checks_creation_time_and_only_owned_tree(self):
        terminated = []
        class Process:
            def __init__(self, pid): self.pid = pid
            def create_time(self): return {10: 1.0, 11: 2.0, 12: 9.0}[self.pid]
            def is_running(self): return True
            def terminate(self): terminated.append(self.pid)
        fake = SimpleNamespace(Process=Process, NoSuchProcess=ProcessLookupError,
                               wait_procs=lambda processes, timeout: (processes, []))
        record = [{"pid": 10, "created_at": 1.0}, {"pid": 11, "created_at": 2.0}, {"pid": 12, "created_at": 3.0}]
        owner = SimpleNamespace(unlink=lambda **kwargs: None)
        with patch.dict("sys.modules", {"psutil": fake}), patch.object(start, "BROWSER_OWNER_FILE", owner):
            start.stop_owned_browser(record)
        self.assertEqual(terminated, [11, 10], "A reused PID must never be stopped")

    def test_status_retains_course(self):
        source = ROOT / "patches/neko-study-2026-10-10-product/payload/study_companion/service.py"
        tree = ast.parse(source.read_text(encoding="utf-8"))
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "build_status_payload")
        fields = {n.attr for n in ast.walk(fn) if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == "state"}
        state = SimpleNamespace(**{field: None for field in fields})
        state.study_course_id = "flutter-provider"
        config = SimpleNamespace(mode="teaching", default_mode="teaching", to_dict=lambda: {})
        env = {"copy": copy, "StudyConfig": object, "StudyState": object, "Any": object}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[])), str(source), "exec"), env)
        payload = env["build_status_payload"](config=config, state=state)
        self.assertEqual(payload["study_course_id"], "flutter-provider")
        state.study_course_id = "networking"
        self.assertEqual(env["build_status_payload"](config=config, state=state)["study_course_id"], "networking")


if __name__ == "__main__":
    unittest.main()
