"""Offline launcher regression. No host, provider, microphone or screenshot."""
import ast
import copy
import json
import importlib.util
import sys
import types
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("tutor_start", ROOT / "scripts/neko_tutor_start.py")
start = importlib.util.module_from_spec(spec)
spec.loader.exec_module(start)


class ProductStartTest(unittest.TestCase):
    def test_native_restart_keeps_settings_and_never_overwrites_invalid_config(self):
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            store = Path(directory)
            path = start.avatar.write_surface_config(store, "compact")
            config = json.loads(path.read_text(encoding="utf-8"))
            config["retained_preference"] = {"enabled": True, "value": 7}
            path.write_text(json.dumps(config), encoding="utf-8")
            start.avatar.write_surface_config(store, "full")
            restored = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(restored["retained_preference"], config["retained_preference"])
            self.assertEqual(restored["chatSurfaceMode"], "full")
            path.write_text("broken config", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "已保留原文件"):
                start.avatar.write_surface_config(store)
            self.assertEqual(path.read_text(encoding="utf-8"), "broken config")

    def test_tutor_restart_does_not_reenter_automatic_tutorial(self):
        """Use upstream persistence and its actual frontend round selector."""
        import subprocess
        import tempfile

        selector = start.host.SOURCE_APP / "static/tutorial/core/seven-day-state.js"
        script = (
            "const fs=require('node:fs');const api=require(process.argv[1]);"
            "const state=JSON.parse(fs.readFileSync(0,'utf8'));"
            "process.stdout.write(JSON.stringify(['2026-10-13','2099-01-01']"
            ".map(day=>api.getNextAutoRound(state,day))));"
        )

        def next_rounds(state):
            result = subprocess.run(["node", "-e", script, str(selector)],
                                    input=json.dumps(state), capture_output=True,
                                    text=True, check=True, timeout=10)
            return json.loads(result.stdout)

        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory)
            self.assertEqual(next_rounds({}), [1, 1])
            start.host.prepare_tutor_onboarding(runtime)
            path = runtime / "config/seven_day_tutorial_state.json"
            first = path.read_bytes()
            state = json.loads(first)["state"]
            self.assertEqual(next_rounds(state), [None, None])
            self.assertEqual(state["completedRounds"], [])
            start.host.prepare_tutor_onboarding(runtime)
            self.assertEqual(path.read_bytes(), first)

            from utils.seven_day_tutorial_state import replace_seven_day_tutorial_state

            class Paths:
                def get_config_path(self, name):
                    return runtime / "config" / name

            state.update(completedRounds=[1], skippedRounds=[], manualResetRound=2)
            replace_seven_day_tutorial_state(state, expected_revision=json.loads(first)["revision"],
                                            config_manager=Paths())
            start.host.prepare_tutor_onboarding(runtime)
            restored = json.loads(path.read_bytes())["state"]
            self.assertEqual(restored["completedRounds"], [1])
            self.assertEqual(next_rounds(restored), [2, 2])

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
        command = start.host_command(240, 30, 80)
        self.assertEqual(command[0], str(start.host.SOURCE_PYTHON))
        self.assertIn("--source", command)
        self.assertEqual(command[command.index("--store") + 1], "neko-product-data")
        self.assertEqual(command[command.index("--api-budget") + 1], "30")
        self.assertEqual(command[command.index("--egress-budget") + 1], "80")
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

    def test_cleanup_stops_the_tree_it_owns_and_nothing_else(self):
        """Real pids on the shipped interpreter - the case the old fake-psutil test could not see.

        The previous version patched `psutil` into `sys.modules`, so it stayed green while the
        launcher's own interpreter (benchmarks/raw/goal-python) had no psutil and the session's
        `finally` raised ModuleNotFoundError instead of closing the browser. This one spawns an
        actual parent/child pair and asks whether both are gone afterwards.
        """
        import subprocess
        import tempfile
        from pathlib import Path

        tree = ("import subprocess, sys, time;"
                "p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)']);"
                "print(p.pid, flush=True); time.sleep(120)")
        parent = subprocess.Popen([sys.executable, "-c", tree], stdout=subprocess.PIPE, text=True)
        child_pid = int(parent.stdout.readline().strip())
        owner_file = Path(tempfile.mkdtemp()) / "browser-owner.json"
        record = [{"pid": parent.pid, "created_at": start.process_creation_time(parent.pid)}]
        with patch.object(start, "BROWSER_OWNER_FILE", owner_file):
            start.stop_owned_browser(record)
        self.assertIsNone(start.process_creation_time(parent.pid), "the recorded process survived")
        self.assertIsNone(start.process_creation_time(child_pid),
                          "taskkill /T must reach the child holding the fake microphone")
        parent.wait(timeout=10)
        parent.stdout.close()
        self.assertFalse(owner_file.exists(), "a cleared session must not leave an owner record")

        # A record whose start time disagrees is not ours to stop, however live the pid is.
        stranger = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"])
        try:
            with patch.object(start, "BROWSER_OWNER_FILE", owner_file):
                start.stop_owned_browser([{"pid": stranger.pid, "created_at": 1.0}])
            self.assertIsNotNone(start.process_creation_time(stranger.pid),
                                 "a stale record must never stop someone else's process")
        finally:
            stranger.kill()
            stranger.wait(timeout=10)

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


    def test_folder_picker_feeds_the_same_authorization_as_the_flag(self):
        """The desktop chooser must not become a second, softer authorization path."""
        destroyed = []
        seen = {}

        class FakeRoot:
            def withdraw(self): pass
            def attributes(self, *args): pass
            def destroy(self): destroyed.append(1)

        fake_tk = types.ModuleType("tkinter")
        fake_tk.Tk = lambda: FakeRoot()
        fake_dialog = types.ModuleType("tkinter.filedialog")
        # `tk_chooseDirectory` rejects any keyword outside this set with TclError. The stub used to
        # take **kwargs blindly and assert `must_exist`, which is the broken spelling that shipped:
        # the picker raised TclError before showing a window on the learner's machine, and this test
        # was green because it had copied the bug into its own expectation. An assertion written from
        # the code it is checking catches nothing - so the stub now refuses what Tk refuses.
        accepted = {"initialdir", "mustexist", "parent", "title"}

        class TclError(Exception):
            pass

        def askdirectory(**kw):
            unknown = sorted(set(kw) - accepted)
            if unknown:
                raise TclError(f"bad option {unknown[0]!r}: must be one of {sorted(accepted)}")
            seen.update(kw)
            return "D:/project/Sky Scout/sky_scout"

        fake_dialog.askdirectory = askdirectory
        fake_dialog.TclError = TclError
        fake_tk.TclError = TclError
        fake_tk.filedialog = fake_dialog
        with patch.dict(sys.modules, {"tkinter": fake_tk, "tkinter.filedialog": fake_dialog}):
            chosen = start.pick_code_root()
        self.assertEqual(chosen, "D:/project/Sky Scout/sky_scout")
        self.assertTrue(seen.get("mustexist"), "a picker that accepts a typo is worse than the flag")
        self.assertEqual(len(destroyed), 1, "the hidden Tk shell must be torn down")
        source = (ROOT / "scripts/neko_tutor_start.py").read_text(encoding="utf-8")
        self.assertIn("chosen = pick_code_root()", source)
        self.assertIn("authorize_code_project(Path(chosen).expanduser().resolve(), data_dir)", source)
        self.assertIn('held = data_dir / "plugins/study_companion/data/code_project.json"', source)


    def test_a_scripted_run_can_decline_the_dialog_without_losing_the_grant(self):
        """`keep` is how a run with nobody in front of the screen gets past a modal chooser.

        Measured twice this round: an agent-launched session still has a tty on stdin, the
        folder dialog opened, and the host never started. The sentinel must neither open a
        dialog nor be read as a directory - `authorize_code_project("keep")` would resolve to
        a path that does not exist and revoke the stored grant as it failed.
        """
        cases = {("", True): "picker", ("", False): "reuse", ("ask", False): "picker",
                 ("keep", True): "reuse", (" KEEP ", True): "reuse",
                 ("D:/project/x", True): "authorize", ("D:/project/x", False): "authorize"}
        for (chosen, interactive), action in cases.items():
            self.assertEqual(start.code_root_action(chosen, interactive), action,
                             f"--code-root {chosen!r} with interactive={interactive}")
        source = (ROOT / "scripts/neko_tutor_start.py").read_text(encoding="utf-8")
        self.assertIn("action = code_root_action(chosen, sys.stdin.isatty())", source,
                      "main() must branch on the same decision the test covers")


if __name__ == "__main__":
    unittest.main()
