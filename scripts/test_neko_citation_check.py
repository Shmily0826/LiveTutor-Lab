"""R2: deterministic citation check for source explanations. Pure functions, no model, no I/O."""
import importlib.util
from pathlib import Path
import unittest

from test_neko_explanation_language import scope

SOURCE = Path(__file__).resolve().parents[1] / "patches/neko-study-2026-10-10-product/payload/study_companion"
spec = importlib.util.spec_from_file_location("citation_check_under_test", SOURCE / "study_citation_check.py")
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)

SHOWN = [{"shown": [{"file": "sky_scout/app_sky_scout/lib/data/services/weather_service.dart",
                     "lines": list(range(18, 30))}]}]
EVIDENCE = "18\t  final uri = baseUrl.resolve('/api/weather');\n22\t if (response.statusCode != 200) {\n23\t throw Exception('Weather API returned');\n26\t return Weather.fromJson(jsonDecode(response.body));"


class Numbers(unittest.TestCase):
    def test_round_trip_with_the_speakable_writer(self):
        for number in list(range(1, 400)) + [1000, 1005, 1234, 9999]:
            with self.subTest(number=number):
                self.assertEqual(check.zh_number(scope["_zh_number"](str(number))), number)
        self.assertEqual(check.zh_number("23"), 23)
        self.assertIsNone(check.zh_number("abc"))
        self.assertIsNone(check.zh_number(""))


class Lines(unittest.TestCase):
    def bad(self, text, sources=SHOWN):
        return [(v["text"], v["missing"]) for v in check.line_violations(text, sources)]

    def test_inside_window_and_boundaries(self):
        for text in ("第二十三行抛出异常。", "第 22 行判断状态码，第 23 行抛异常。", "第十八到二十九行是整个函数。",
                     "weather_service.dart 第二十二到二十三行检查状态码。", "weather_service.dart:23 抛异常。",
                     "Line 23 throws; lines 22 to 24 check the status.", "第二十二和二十三行。"):
            with self.subTest(text=text):
                self.assertEqual(self.bad(text), [])

    def test_outside_window_is_flagged_at_both_edges(self):
        self.assertEqual(self.bad("第十七行是导入。"), [("第十七行", [17])])
        self.assertEqual(self.bad("第三十行是结尾。"), [("第三十行", [30])])
        self.assertEqual(self.bad("第 22 到 31 行"), [("第 22 到 31 行", [31])])
        self.assertEqual(self.bad("see lines 28 to 40"), [("lines 28 to 40", [40])])
        self.assertEqual(self.bad("weather_service.dart:99"), [(":99", [99])])
        self.assertEqual(self.bad("第四十和二十三行")[0][1], [40])

    def test_file_named_but_not_shown_is_flagged_even_with_a_shown_number(self):
        self.assertEqual(self.bad("weather.js 第二十三行返回 502。"), [("第二十三行", [23])])

    def test_no_line_numbers_no_violations_and_nothing_shown_flags_everything(self):
        self.assertEqual(self.bad("它会抛出异常，不做重试。"), [])
        self.assertEqual(self.bad("它在第五行开始。", []), [("第五行", [5])])
        self.assertEqual(self.bad("它在第五行开始。", [{"shown": []}]), [("第五行", [5])])
        self.assertEqual(self.bad("", SHOWN), [])
        self.assertEqual(check.check_reply(None, SHOWN, EVIDENCE), [])

    def test_prose_that_only_looks_numeric_is_not_a_claim(self):
        for text in ("第一次请求会超时。", "这是第三方库，进行了封装。", "返回 200 表示成功。", "10 秒超时。"):
            with self.subTest(text=text):
                self.assertEqual(check.line_claims(text), [])


class Identifiers(unittest.TestCase):
    def test_named_identifier_must_be_in_evidence_or_question(self):
        self.assertEqual(check.identifier_violations("fetchWeather 里 statusCode 不等于 200 就抛异常。", "fetchWeather statusCode"), [])
        got = check.identifier_violations("它先查 cacheManager 再调用 fetchWeather。", EVIDENCE + " fetchWeather")
        self.assertEqual([v["text"] for v in got], ["cacheManager"])
        self.assertEqual(check.identifier_violations("cacheManager 是什么", "x", question="cacheManager 是什么"), [])
        self.assertEqual(check.identifier_violations("The response_body is parsed.", "response_body"), [])
        self.assertEqual([v["text"] for v in check.identifier_violations("see weather.js and weather_service.dart", "weather_service.dart")],
                         ["weather.js"])

    def test_ordinary_words_and_numbers_are_not_identifiers(self):
        self.assertEqual(check.identifier_violations("It throws an exception on HTTP 404 and JSON errors.", ""), [])
        self.assertEqual(check.identifier_violations("非 200 时直接抛异常。", ""), [])


class Strip(unittest.TestCase):
    def test_out_of_window_line_is_removed_and_the_rest_kept(self):
        reply = "第二十三行抛出异常，第四十行会重试。"
        got = check.strip_violations(reply, check.check_reply(reply, SHOWN, EVIDENCE))
        self.assertNotIn("四十", got)
        self.assertIn("第二十三行抛出异常", got)
        self.assertIn("会重试", got)

    def test_file_name_is_kept_when_only_its_line_is_wrong(self):
        reply = "weather_service.dart 的第九十行抛异常。"
        got = check.strip_violations(reply, check.check_reply(reply, SHOWN, EVIDENCE))
        self.assertIn("weather_service.dart", got)
        self.assertNotIn("九十", got)

    def test_unseen_identifier_drops_only_its_sentence(self):
        reply = "非 200 时抛 Exception。它会先查 cacheManager。最后返回结果。"
        got = check.strip_violations(reply, check.check_reply(reply, SHOWN, EVIDENCE))
        self.assertNotIn("cacheManager", got)
        self.assertIn("非 200", got)
        self.assertIn("最后返回结果", got)

    def test_nothing_usable_left_returns_empty(self):
        reply = "它会先查 cacheManager。"
        self.assertEqual(check.strip_violations(reply, check.check_reply(reply, SHOWN, EVIDENCE)), "")

    def test_clean_reply_is_untouched(self):
        reply = "第二十二行判断状态码，第二十三行抛异常。"
        self.assertEqual(check.check_reply(reply, SHOWN, EVIDENCE), [])
        self.assertEqual(check.strip_violations(reply, []), reply)

    def test_retry_note_states_the_real_windows(self):
        reply = "第四十行。"
        note = check.describe(check.check_reply(reply, SHOWN, EVIDENCE), SHOWN)
        self.assertIn("weather_service.dart lines 18-29", note)
        self.assertIn("第四十行", note)


REAL = """**`sky_scout/app_sky_scout/lib/data/services/weather_service.dart`**
```
21	    final response = await http.get(uri).timeout(const Duration(seconds: 10));
22	    if (response.statusCode != 200) {
23	      throw Exception('Weather API returned ${response.statusCode}');
24	    }
25
26	    return Weather.fromJson(jsonDecode(response.body));
```"""
REAL_SOURCES = [{"shown": [{"file": "sky_scout/app_sky_scout/lib/data/services/weather_service.dart", "lines": list(range(18, 30))}]}]


class Placement(unittest.TestCase):
    def kinds(self, text):
        return [(v["kind"], v["text"]) for v in check.check_reply(text, REAL_SOURCES, REAL)]

    def test_throw_pinned_on_the_guard_line_is_flagged_with_the_right_line(self):
        for text in ("第二十二行抛出异常。", "weather_service.dart 第 22 行 throw 一个 Exception。", "非 200 时在第二十二行抛异常。"):
            with self.subTest(text=text):
                got = check.check_reply(text, REAL_SOURCES, REAL)
                self.assertEqual([v["kind"] for v in got], ["placement"], got)
                self.assertEqual(got[0]["found_on"], [23])

    def test_correct_and_guard_wording_pass(self):
        for text in ("第二十三行抛出异常。", "第二十二到二十四行检查状态码并抛异常。", "第二十二行判断状态码，不是 200 就抛异常。",
                     "第 21 行发请求，第 26 行解析 JSON。", "第二十二行判断状态码。"):
            with self.subTest(text=text):
                self.assertEqual(self.kinds(text), [])

    def test_no_numbered_evidence_means_no_placement_claim(self):
        self.assertEqual(check.placement_violations("第二十二行抛出异常。", "no numbered text"), [])
        self.assertEqual(check.placement_violations("第二十二行抛出异常。", ""), [])

    def test_strip_removes_the_wrong_line_but_keeps_the_statement(self):
        reply = "非 200 时第二十二行抛出异常。"
        got = check.strip_violations(reply, check.check_reply(reply, REAL_SOURCES, REAL))
        self.assertNotIn("二十二", got)
        self.assertIn("抛出异常", got)
        note = check.describe(check.check_reply(reply, REAL_SOURCES, REAL), REAL_SOURCES)
        self.assertIn("[23]", note)

    def test_range_claim_with_the_word_inside_is_fine_and_english_works(self):
        self.assertEqual(self.kinds("Lines 22 to 24 check the status and throw."), [])
        self.assertEqual([k for k, _ in self.kinds("Line 22 throws an Exception.")], ["placement"])

    def test_the_recorded_wrong_reply_is_caught(self):
        # codex-r2-final-proof.json / codex-r2-p5-native-a.json: a real teacher reply said the throw is on line 22.
        reply = "改成只在 `response.statusCode >= 500`才抛后，404不满足条件，第二十二行的 `throw`不执行。 控制流继续走到第二十六行。"
        got = check.check_reply(reply, REAL_SOURCES, REAL)
        self.assertEqual([(v["kind"], v["found_on"]) for v in got], [("placement", [23])])
        self.assertNotIn("第二十二行", check.strip_violations(reply, got))


if __name__ == "__main__":
    unittest.main()
