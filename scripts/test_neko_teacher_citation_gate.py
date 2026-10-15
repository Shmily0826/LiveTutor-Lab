"""R2: the source teacher's reply is held to the evidence it was shown (one retry, then strip).

Real avatar wrapper, real source-teaching bridge and SQLite store; CodeGraph and the teacher model are fakes.
"""
import json
import unittest
import unittest.mock
from unittest.mock import AsyncMock

import test_neko_project_code_teaching as base

EVIDENCE = """**`project/weather_service.dart`**
```
21	    final response = await http.get(uri).timeout(const Duration(seconds: 10));
22	    if (response.statusCode != 200) {
23	      throw Exception('Weather API returned ${response.statusCode}');
24	    }
25
26	    return Weather.fromJson(jsonDecode(response.body));
```"""


class CitationGate(base.ProjectCodeTeaching):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.h.study_code_tool = AsyncMock(return_value={
            'ok': True, 'mode': 'file', 'project': 'Project', 'repo_commit': 'revision-A',
            'shown': [{'file': 'project/weather_service.dart', 'lines': list(range(21, 27))}],
            'index_sync': 'throttled', 'note': 'Only shown lines were read.', 'evidence': EVIDENCE})

    def replies(self, *texts):
        self.h.study_explain_text = AsyncMock(side_effect=[{'ok': True, 'reply': text} for text in texts])

    async def ask(self, **kwargs):
        return await self.h.study_explain_tool(
            question='非 200 的时候怎么处理？只用两句。', material_source='project_code',
            code_requests=[{'file': 'weather_service.dart', 'offset': 21, 'limit': 6}],
            _ctx={'lanlan_name': 'Role-A'}, **kwargs)

    async def test_clean_reply_costs_one_teacher_call(self):
        self.replies('第二十二行判断状态码，第二十三行抛出异常。')
        result = await self.ask()
        self.assertEqual(self.h.study_explain_text.await_count, 1)
        self.assertNotIn('citation_check', result)
        self.assertIn('二十三行抛出异常', result['reply'])

    async def test_out_of_window_line_is_retried_once_with_the_real_windows(self):
        self.replies('第四十行会重试。', '第二十三行抛出异常，不做重试。')
        result = await self.ask()
        self.assertEqual(self.h.study_explain_text.await_count, 2)
        retry_text = self.h.study_explain_text.await_args_list[1].kwargs['text']
        self.assertIn('[Citation check]', retry_text)
        self.assertIn('weather_service.dart lines 21-26', retry_text)
        self.assertIn('第二十三行抛出异常', result['reply'])
        self.assertNotIn('四十', result['reply'])
        self.assertEqual(result['citation_check']['result'], 'clean_after_retry')

    async def test_throw_on_the_guard_line_is_retried_with_the_correct_line(self):
        self.replies('第二十二行抛出异常。', '第二十三行抛出异常。')
        result = await self.ask()
        self.assertEqual(self.h.study_explain_text.await_count, 2)
        self.assertIn('[23]', self.h.study_explain_text.await_args_list[1].kwargs['text'])
        self.assertIn('二十三行', result['reply'])

    async def test_second_violation_is_stripped_not_retried_again(self):
        self.replies('非 200 时第二十二行抛出异常。', '非 200 时第九十行抛出异常。')
        result = await self.ask()
        self.assertEqual(self.h.study_explain_text.await_count, 2)
        self.assertEqual(result['citation_check']['result'], 'stripped')
        self.assertNotIn('九十', result['reply'])
        self.assertNotIn('二十二', result['reply'])
        self.assertIn('抛出异常', result['reply'])
        self.assertIn('Read every sentence', result['relay'])  # relay rebuilt, still the delivery note

    async def test_unseen_identifier_sentence_is_dropped_and_empty_result_is_withheld(self):
        self.replies('它先查 cacheManager。', '它先查 cacheManager。')
        result = await self.ask()
        self.assertEqual(result['citation_check']['result'], 'withheld')
        self.assertNotIn('cacheManager', result['reply'])
        self.assertIn('不下结论', result['reply'])

    async def test_failed_retry_keeps_the_original_answer_stripped(self):
        self.h.study_explain_text = AsyncMock(side_effect=[{'ok': True, 'reply': '抛出异常。第九十行重试。'}, RuntimeError('boom')])
        result = await self.ask()
        self.assertEqual(result['citation_check']['retry_error'], 'RuntimeError')
        self.assertIn('抛出异常', result['reply'])
        self.assertNotIn('九十', result['reply'])

    async def test_english_withheld_wording(self):
        self.replies('It checks cacheManager first.', 'It checks cacheManager first.')
        result = await self.ask(language='en-US')
        self.assertIn('could not support', result['reply'])

    async def test_degraded_or_failed_answers_are_not_checked(self):
        self.h.study_explain_text = AsyncMock(return_value={'ok': True, 'degraded': True, 'reply': '第九十行', 'diagnostic': 'x'})
        result = await self.ask()
        self.assertEqual(self.h.study_explain_text.await_count, 1)
        self.assertNotIn('citation_check', result)

    async def test_observe_mode_records_findings_and_changes_nothing(self):
        import os
        self.replies('第二十二行抛出异常。')
        with unittest.mock.patch.dict(os.environ, {'NEKO_CITATION_GATE': 'observe'}):
            result = await self.ask()
        self.assertEqual(self.h.study_explain_text.await_count, 1)
        self.assertIn('二十二行抛出异常', result['reply'])
        self.assertEqual(result['citation_check']['mode'], 'observe')
        self.assertEqual(result['citation_check']['violations'], 1)

    async def test_off_mode_skips_the_gate(self):
        import os
        self.replies('第九十行抛出异常。')
        with unittest.mock.patch.dict(os.environ, {'NEKO_CITATION_GATE': 'off'}):
            result = await self.ask()
        self.assertEqual(self.h.study_explain_text.await_count, 1)
        self.assertNotIn('citation_check', result)
        self.assertIn('九十行', result['reply'])

    async def test_result_is_json_serialisable(self):
        self.replies('第九十行抛出异常。', '第九十行抛出异常。')
        json.dumps(await self.ask(), ensure_ascii=False)


# The inherited tests belong to the base module; run only this module's own gate tests here.
for _name in [n for n in dir(base.ProjectCodeTeaching) if n.startswith('test_')]:
    setattr(CitationGate, _name, None)

if __name__ == '__main__':
    unittest.main()
