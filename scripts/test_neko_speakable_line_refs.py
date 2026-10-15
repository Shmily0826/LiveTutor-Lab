"""Line references are respelled for speech; ids, codes and identifiers stay exact (offline)."""
import ast
import json
from pathlib import Path
import re
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'patches/neko-study-2026-10-10-product/payload/study_companion/study_avatar_tools.py'
NAMES = {'RELAY_NOTE', '_FENCE_LINE', '_FENCE_MARK', '_CODE_SPAN', '_SPEAKABLE_FIELDS', '_RANGE_MARK',
         '_ZH_LINE_RANGE', '_ZH_LINE_ONE', '_FILE_LINE', '_EN_LINE_RANGE', '_CJK', '_zh_number',
         '_spoken_line_refs', '_speakable', '_teaching', '_teaching_failure_wording'}


def helpers():
    tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
    body = [node for node in tree.body
            if (isinstance(node, ast.Assign) and {t.id for t in node.targets if isinstance(t, ast.Name)} & NAMES)
            or (isinstance(node, ast.FunctionDef) and node.name in NAMES)]
    namespace = {'json': json, 're': re, 'Any': object}
    exec(compile(ast.Module(body=body, type_ignores=[]), str(SOURCE), 'exec'), namespace)
    return namespace


class SpeakableLineRefs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ns = helpers()
        cls.say = staticmethod(cls.ns['_speakable'])

    def test_numbers_read_as_chinese(self):
        zh = self.ns['_zh_number']
        self.assertEqual([zh(str(n)) for n in (0, 5, 10, 13, 20, 22, 24, 26, 99)],
                         ['零', '五', '十', '十三', '二十', '二十二', '二十四', '二十六', '九十九'])
        self.assertEqual([zh(str(n)) for n in (100, 101, 110, 120, 205, 1005, 1050, 1234)],
                         ['一百', '一百零一', '一百一十', '一百二十', '二百零五', '一千零五', '一千零五十', '一千二百三十四'])

    def test_line_ranges_and_single_lines(self):
        cases = {
            '22–24 行抛出异常，26 行的解析不会执行。': '二十二到二十四行抛出异常，二十六行的解析不会执行。',
            '第22–24行抛出异常，第26行不会执行。': '第二十二到二十四行抛出异常，第二十六行不会执行。',
            '看第 22 行，再看第 22-24 行。': '看第二十二行，再看第二十二到二十四行。',
            '第22到24行和第105至110行': '第二十二到二十四行和第一百零五到一百一十行',
            '第22行到第24行': '第二十二行到第二十四行',
            '一共 3 行代码。': '一共 三行代码。',
        }
        for text, expected in cases.items():
            self.assertEqual(self.say(text), expected, text)

    def test_file_line_refs_follow_the_file_name(self):
        self.assertEqual(self.say('见 weather_service.dart:22-24，再看 server/routes/weather.js:17。'),
                         '见 weather_service.dart 的第二十二到二十四行，再看 server/routes/weather.js 的第十七行。')

    def test_numbers_that_are_not_line_references_stay_exact(self):
        text = ('返回 404，不是 200；statusCode >= 500 才抛出；端口 localhost:8080；版本 1.2.3；'
                '`Weather.fromJson` 在 abc22行 里；id q-0022 保持不变；他进行了 3 次尝试；行为不变。')
        flat = self.say(text)
        for kept in ('404', '200', 'statusCode >= 500', 'localhost:8080', '1.2.3', 'Weather.fromJson', 'q-0022', '3 次', '行为不变'):
            self.assertIn(kept, flat)
        self.assertIn('abc22行', flat)

    def test_english_ranges_say_to_and_single_lines_stay(self):
        self.assertEqual(self.say('See lines 22–24, then line 26 and weather.js:17-19.'),
                         'See lines 22 to 24, then line 26 and weather.js:17-19.')

    def test_code_survives_and_the_panel_text_is_not_touched(self):
        reply = '`statusCode != 200` 在第22–24行抛异常。\n```dart\nthrow Exception(\'Weather API returned ${response.statusCode}\');\n```'
        flat = self.say(reply)
        self.assertIn('statusCode != 200', flat)
        self.assertIn('第二十二到二十四行', flat)
        self.assertIn("throw Exception('Weather API returned ${response.statusCode}');", flat)
        self.assertIn('第22–24行', reply)  # the caller's string is the stored one; only the relay copy changes

    def test_only_the_relayed_fields_are_respelled(self):
        out = json.loads(self.ns['_teaching'](tool='study_explain', reply='第22–24行抛异常。', question='第26行呢？',
                                              source_lines='22-24', degraded=False))
        self.assertEqual(out['reply'], '第二十二到二十四行抛异常。')
        self.assertEqual(out['question'], '第二十六行呢？')
        self.assertEqual(out['source_lines'], '22-24')


if __name__ == '__main__':
    unittest.main()
