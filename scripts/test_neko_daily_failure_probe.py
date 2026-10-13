"""Offline checks only; no real host, SDK worker, model provider or audio."""
import json
from contextlib import closing
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import types
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

import neko_daily_failure_probe as probe


class StubTest(unittest.TestCase):
    def setUp(self):
        self.server = probe.FailureStub(maximum_requests=2)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.opener = build_opener(ProxyHandler({}))

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def call_model(self, key=probe.DUMMY_KEY):
        request = Request(self.server.base_url + "/v1/chat/completions", data=json.dumps({
            "model": "local-fixture", "messages": [{"role": "user", "content": "protocol fixture"}]}).encode(),
            headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
        with self.opener.open(request, timeout=3) as response:
            return json.load(response)

    def test_http_failure_recovery_and_request_limit(self):
        with self.assertRaises(HTTPError) as caught:
            self.call_model()
        self.assertEqual(caught.exception.code, 503)
        caught.exception.close()
        probe.json_request(self.server.base_url + "/control/mode", data={"mode": "question"}, token=self.server.token)
        result = self.call_model()
        self.assertIn("本地故障量具", result["choices"][0]["message"]["content"])
        with self.assertRaises(HTTPError) as caught:
            self.call_model()
        self.assertEqual(caught.exception.code, 429)
        self.assertEqual(caught.exception.headers.get("Retry-After"), "3600")
        caught.exception.close()
        self.assertEqual(len(self.server.records), 2)

    def test_non_dummy_credential_refused_and_never_recorded(self):
        with self.assertRaises(HTTPError) as caught:
            self.call_model("not-a-provider-credential")
        self.assertEqual(caught.exception.code, 401)
        caught.exception.close()
        self.assertTrue(self.server.unexpected_credential)
        self.assertEqual(self.server.records, [])
        self.assertNotIn("not-a-provider-credential", json.dumps(self.server.state()))

    def test_control_auth_and_external_urls_refused(self):
        with self.assertRaises(HTTPError) as caught:
            probe.json_request(self.server.base_url + "/control/state")
        self.assertEqual(caught.exception.code, 403)
        caught.exception.close()
        with self.assertRaises(HTTPError) as caught:
            probe.json_request(self.server.base_url + "/control/mode", data={"mode": "answer"})
        self.assertEqual(caught.exception.code, 403)
        caught.exception.close()
        self.assertEqual(self.server.mode, "http503")
        for url in ("https://api.deepseek.com/v1", "http://localhost:1234", "http://key@127.0.0.1:1234", "http://127.0.0.1:1234?key=value"):
            with self.assertRaises(ValueError):
                probe.local_url(url)


class IsolationAndAssertionsTest(unittest.TestCase):
    def test_owned_manifest_and_output_boundary_before_any_host_call(self):
        with tempfile.TemporaryDirectory(prefix="neko-failure-unit-", dir=probe.RAW) as folder:
            store = Path(folder)
            manifest = store / "failure-stub-manifest.json"
            value = {"kind": probe.KIND, "nonce": "unit-owner", "store": str(store), "stub_url": "http://127.0.0.1:12345"}
            manifest.write_text(json.dumps(value), encoding="utf-8")
            marker = store / "failure-fixture-owner.json"
            marker.write_text(json.dumps({"kind": probe.KIND, "nonce": "wrong-owner"}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "ownership"):
                probe.load_manifest(manifest)
            marker.write_text(json.dumps({"kind": probe.KIND, "nonce": "unit-owner"}), encoding="utf-8")
            db = store / "study_companion.db"
            db.touch()
            options = types.SimpleNamespace(manifest=manifest, db=db, output=probe.ROOT / "unapproved-evidence-output.json")
            with patch("neko_lab_client.LabClient") as client:
                with self.assertRaisesRegex(ValueError, "evidence output"):
                    probe.run_probe(options)
                client.assert_not_called()

    def test_failure_cannot_expose_grade_or_question(self):
        honest = {"degraded": True, "status": "unavailable", "diagnostic": "provider_unavailable", "reply": "No usable teaching result"}
        probe.assert_failed_teaching(honest, operation="answer")
        for extra in ({"score": 0}, {"verdict": "wrong"}, {"question": "fallback question"}, {"attempt_id": "consumed"}, {"degraded": False}):
            with self.assertRaises(AssertionError):
                probe.assert_failed_teaching({**honest, **extra}, operation="answer")

    def test_readonly_db_snapshot_keeps_attempt_and_counts(self):
        with tempfile.TemporaryDirectory(prefix="neko-failure-unit-", dir=probe.RAW) as folder:
            db = Path(folder) / "study_companion.db"
            with closing(sqlite3.connect(db)) as connection:
                connection.executescript("CREATE TABLE kv(key TEXT PRIMARY KEY,value TEXT); CREATE TABLE interactions(id INTEGER); CREATE TABLE qa_records(id INTEGER);")
                connection.execute("INSERT INTO kv VALUES('state', ?)", (json.dumps({"study_course_id": "fixture", "current_question": {"attempt_id": "a1", "attempt_evaluated": False}}),))
                connection.commit()
            before = probe.file_sha256(db)
            snapshot = probe.database_snapshot(db)
            self.assertEqual(snapshot["counts"], {"interactions": 0, "qa_records": 0})
            self.assertEqual(snapshot["current_question"]["attempt_id"], "a1")
            self.assertEqual(probe.file_sha256(db), before)

    def test_launch_plan_uses_dummy_key_and_separate_deny_sink_without_real_host(self):
        with tempfile.TemporaryDirectory(prefix="neko-failure-unit-", dir=probe.RAW) as folder:
            store = Path(folder)
            manifest = {"store": str(store), "stub_url": "http://127.0.0.1:12345", "global_ledger_sha256": "unchanged"}
            plan = probe.launch_plan(manifest)
            fake = types.ModuleType("neko_desktop_tutor_host")
            captured = []
            fake.Sink = lambda *args, **kwargs: captured.append((args, kwargs))
            def fake_main():
                self.assertEqual(fake.MODEL_URL, manifest["stub_url"] + "/v1")
                self.assertEqual(fake.read_key(), probe.DUMMY_KEY)
                fake.Sink(2000, extra={"www.lanlan.app": None}, cap_file=probe.GLOBAL_LEDGER, round_id="bargein-autocheck-20261012")
                return 0
            fake.main = fake_main
            original_argv, original_path = sys.argv[:], sys.path[:]
            try:
                with patch.dict(sys.modules, {"neko_desktop_tutor_host": fake}):
                    with self.assertRaises(SystemExit) as exited:
                        exec(compile(plan["argv"][-1], "reviewed local fixture launch plan", "exec"), {})
                    self.assertEqual(exited.exception.code, 0)
            finally:
                sys.argv[:], sys.path[:] = original_argv, original_path
            self.assertEqual(captured[0][0], (0,))
            self.assertEqual(captured[0][1]["extra"], {})
            self.assertEqual(captured[0][1]["cap_file"], store / "local-deny-egress.json")
            self.assertNotEqual(captured[0][1]["round_id"], "bargein-autocheck-20261012")


if __name__ == "__main__":
    unittest.main()
