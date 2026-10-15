"""R2: the eval set is well formed, its expected facts match the read-only source, and the scorer behaves."""
import json
from pathlib import Path
import re
import unittest

import teacher_eval_score as scorer

SKY = Path(r"D:\UoA\S2\COMPSCI 734\project\Sky Scout\sky_scout")
QUESTIONS = scorer.EVAL


class EvalSetShape(unittest.TestCase):
    def test_at_least_twelve_questions_with_required_kinds_and_files(self):
        self.assertGreaterEqual(len(QUESTIONS), 12)
        self.assertEqual(len({q["id"] for q in QUESTIONS}), len(QUESTIONS))
        kinds = {q["kind"] for q in QUESTIONS}
        for needed in ("line_meaning", "non200", "change_impact", "cross_file", "wrong_claim"):
            self.assertIn(needed, kinds)
        files = " ".join(r["file"] for q in QUESTIONS for r in q["code_requests"])
        for needed in ("weather_service.dart", "server/routes/weather.js", "server/src/weather.js", "api_config.dart", "sky_map"):
            self.assertIn(needed, files)
        for q in QUESTIONS:
            with self.subTest(q=q["id"]):
                self.assertTrue(q["expected_facts"])
                self.assertTrue(1 <= len(q["code_requests"]) <= 3)
                for pattern in [p for group in q["must_match"] for p in group] + [f["regex"] for f in q["forbidden"]]:
                    re.compile(pattern)

    def test_every_window_lies_inside_the_real_file_when_the_project_is_present(self):
        if not SKY.is_dir():
            self.skipTest("Sky Scout not present")
        for q in QUESTIONS:
            for request in q["code_requests"]:
                with self.subTest(q=q["id"], file=request["file"]):
                    path = SKY / request["file"]
                    self.assertTrue(path.is_file(), path)
                    count = len(path.read_text(encoding="utf-8").splitlines())
                    self.assertGreaterEqual(request["offset"], 1)
                    self.assertLessEqual(request["offset"], count)
                    self.assertLessEqual(request["offset"] + request["limit"] - 1, count + 1)

    def test_pinned_line_facts_are_true_in_the_source(self):
        if not SKY.is_dir():
            self.skipTest("Sky Scout not present")
        lines = (SKY / "app_sky_scout/lib/data/services/weather_service.dart").read_text(encoding="utf-8").splitlines()
        self.assertIn("statusCode != 200", lines[21])
        self.assertIn("throw Exception", lines[22])
        self.assertIn("timeout(const Duration(seconds: 10))", lines[20])
        self.assertIn("Weather.fromJson", lines[25])
        route = (SKY / "server/routes/weather.js").read_text(encoding="utf-8").splitlines()
        self.assertIn("status(400)", route[10])
        self.assertIn("status(502)", route[19])
        src = (SKY / "server/src/weather.js").read_text(encoding="utf-8").splitlines()
        self.assertIn("CACHE_TTL_MS", src[239])
        self.assertIn("inFlight.get", src[241])
        self.assertIn("staleUntil", src[271])
        overlay = (SKY / "app_sky_scout/lib/features/sky_map/sky_overlay_visibility.dart").read_text(encoding="utf-8").splitlines()
        self.assertIn("fadeStart = 0.45", overlay[9])
        self.assertIn("fadeEnd = 0.90", overlay[10])


class Scoring(unittest.TestCase):
    q = {item["id"]: item for item in QUESTIONS}
    sources = [{"shown": [{"file": "app_sky_scout/lib/data/services/weather_service.dart", "lines": list(range(13, 29))}]}]

    def test_the_known_failure_is_a_forbidden_statement(self):
        bad = scorer.score_reply(self.q["Q01"], "非 200 时第二十二行抛出异常，不会重试。", self.sources)
        self.assertEqual(bad["forbidden_hits"], ["throw_on_22"])
        good = scorer.score_reply(self.q["Q01"], "第 22 行判断非 200，第 23 行抛出异常，不会重试。", self.sources)
        self.assertEqual((good["forbidden_hits"], good["line_violations"], good["unmatched_points"]), ([], [], []))

    def test_window_violations_and_unmatched_points_are_reported(self):
        row = scorer.score_reply(self.q["Q02"], "第 40 行发请求。", self.sources)
        self.assertEqual(row["line_violations"], ["第 40 行"])
        self.assertEqual(row["unmatched_points"], [1])

    def test_agreeing_with_a_false_claim_is_caught(self):
        row = scorer.score_reply(self.q["Q09"], "对，会悄悄返回空数据。", self.sources)
        self.assertEqual(row["forbidden_hits"], ["agrees_empty"])


if __name__ == "__main__":
    unittest.main()
