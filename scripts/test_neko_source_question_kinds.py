"""The five source-teaching question kinds reach the teacher with the right evidence (fake CodeGraph/model IO)."""
from copy import deepcopy
import logging
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock

from test_neko_explanation_language import Harness, Store, prefs

CLIENT, SERVER = 'app/lib/weather_service.dart', 'server/routes/weather.js'
SOURCES = {
    CLIENT: {20: 'final response = await http.get(uri);', 21: 'if (response.statusCode != 200) {',
             22: "  throw Exception('Weather API returned ${response.statusCode}');", 23: '}'},
    SERVER: {7: 'router.get("/", async (req, res) => {', 10: 'if (!areValidCoordinates(lat, lon)) {',
             11: '  return res.status(400).json({ error: "lat and lon are required" });'},
}
TREE = 'sky_scout/\n  app_sky_scout/\n  server/\n    routes/\n'


class SourceQuestionKinds(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name)/'study.db', Path(self.temp.name)/'seed.json', logging.getLogger('kinds'))
        self.store.open()
        prefs.update_preferences(self.store, {'language': 'zh-CN'}, remember=True)
        self.h = Harness(self.store)
        await self.h._restart_study_session(course_id='course-A')
        self.grant = {'name': 'Project', 'root': 'authorized-root', 'prefix': 'project/', 'commit': 'initial'}
        self.h._code_authorization = lambda: deepcopy(self.grant)
        self.h.study_code_tool = AsyncMock(side_effect=lambda **request: self.read(request))
        self.h.study_explain_text = AsyncMock(return_value={'ok': True, 'reply': '第22到24行抛出异常。'})

    async def asyncTearDown(self):
        self.store.close()
        self.temp.cleanup()

    def read(self, request):
        if request['mode'] == 'structure':
            return {'ok': True, 'mode': 'files', 'project': 'Project', 'repo_commit': 'rev-A', 'shown': [],
                    'evidence': TREE, 'index_sync': 'unchanged', 'note': 'A file tree, not source.'}
        rows = SOURCES[request['file']]
        low, high = request['offset'], request['offset'] + request['limit']
        lines = sorted(number for number in rows if low <= number < high)
        return {'ok': True, 'mode': 'node', 'project': 'Project', 'repo_commit': 'rev-A', 'index_sync': 'throttled',
                'shown': [{'file': request['file'], 'lines': lines}], 'note': 'Only shown lines were read.',
                'evidence': '\n'.join(f'{number}\t{rows[number]}' for number in lines)}

    async def ask(self, question, requests):
        return await self.h.study_explain_tool(question=question, material_source='project_code',
                                               code_requests=requests, _ctx={'lanlan_name': 'Role-A'})

    def teacher_text(self):
        return self.h.study_explain_text.call_args.kwargs['text']

    async def test_project_structure_needs_no_query_and_keeps_the_tree_without_line_numbers(self):
        result = await self.ask('这个项目分成哪几部分？', [{'mode': 'structure'}])
        self.h.study_code_tool.assert_awaited_once_with(mode='structure', offset=1, limit=60)
        self.assertIn('server/', self.teacher_text())
        self.assertEqual(result['source_evidence'][0]['shown'], [])
        self.assertIn('A file tree, not source.', self.teacher_text())

    async def test_cross_file_flow_reads_both_ends_in_order_and_keeps_each_citation(self):
        result = await self.ask('天气请求怎么从客户端到服务端？', [
            {'mode': 'file', 'file': CLIENT, 'offset': 20, 'limit': 4},
            {'mode': 'file', 'file': SERVER, 'offset': 7, 'limit': 5}])
        files = [call.kwargs['file'] for call in self.h.study_code_tool.await_args_list]
        self.assertEqual(files, [CLIENT, SERVER])
        text = self.teacher_text()
        self.assertLess(text.index('statusCode != 200'), text.index('areValidCoordinates'))
        self.assertEqual([(item['shown'][0]['file'], item['shown'][0]['lines'][0]) for item in result['source_evidence']],
                         [(CLIENT, 20), (SERVER, 7)])

    async def test_a_single_line_question_reads_a_narrow_window_around_that_line(self):
        await self.ask('第22行是什么意思？', [{'mode': 'file', 'file': CLIENT, 'offset': 20, 'limit': 4}])
        self.h.study_code_tool.assert_awaited_once_with(mode='file', file=CLIENT, offset=20, limit=4)
        text = self.teacher_text()
        self.assertIn('22\\t  throw Exception', text)
        self.assertNotIn('areValidCoordinates', text)

    async def test_change_impact_gets_the_changed_line_and_its_consumer(self):
        await self.ask('把服务端的 400 改成 404，客户端会怎样？', [
            {'mode': 'file', 'file': SERVER, 'offset': 10, 'limit': 3},
            {'mode': 'file', 'file': CLIENT, 'offset': 20, 'limit': 4}])
        text = self.teacher_text()
        self.assertIn('status(400)', text)
        self.assertIn('statusCode != 200', text)
        self.assertIn('label inferences', text)

    def remember(self, file, lines, call=None):
        # study_code_tool records each read itself; the fake does not.
        metadata = {'project': 'Project', 'commit': 'rev-A', 'shown': [{'file': file, 'lines': lines}]}
        if call:
            metadata['call'] = call
        self.store.append_interaction(kind='code_question', input_text='[Project@rev-A] ' + file, output_text='read',
                                      metadata=metadata, session_id=self.h._study_session_id)

    async def test_a_wrong_claim_is_rechecked_against_every_window_of_the_last_explanation(self):
        self.remember(SERVER, [7, 8, 9, 10, 11], call='older-call')
        self.remember(SERVER, [10, 11, 12], call='last-call')
        self.remember(CLIENT, [20, 21, 22, 23], call='last-call')
        claim = '我觉得非200时它还是会先解析 body，对吗？请按源码核对。'
        result = await self.h.study_explain_tool(question=claim, material_source='project_code', _ctx={'lanlan_name': 'Role-A'})
        reads = [(call.kwargs['file'], call.kwargs['offset'], call.kwargs['limit']) for call in self.h.study_code_tool.await_args_list]
        self.assertEqual(reads, [(SERVER, 10, 3), (CLIENT, 20, 4)])  # reading order, other calls excluded
        text = self.teacher_text()
        self.assertIn('This is a follow-up', text)
        self.assertIn(claim, text)
        self.assertLess(text.index('areValidCoordinates'), text.index('throw Exception'))
        self.assertTrue(result['reply'])

    async def test_rows_without_a_call_id_keep_the_single_newest_window(self):
        self.remember(SERVER, [10, 11, 12])
        self.remember(CLIENT, [20, 21, 22, 23])
        await self.h.study_explain_tool(question='那这一行呢？', material_source='project_code', _ctx={'lanlan_name': 'Role-A'})
        self.h.study_code_tool.assert_awaited_once_with(mode='file', file=CLIENT, offset=20, limit=4)

    async def test_a_followup_never_adds_windows_from_other_projects(self):
        self.remember(CLIENT, [20, 21], call='same')
        self.store.append_interaction(kind='code_question', input_text='x', output_text='read',
            metadata={'project': 'Other', 'commit': 'r', 'shown': [{'file': 'other/secret.py', 'lines': [1, 2]}], 'call': 'same'},
            session_id=self.h._study_session_id)
        self.remember(SERVER, [10, 11], call='same')
        await self.h.study_explain_tool(question='继续', material_source='project_code', _ctx={'lanlan_name': 'Role-A'})
        files = [call.kwargs['file'] for call in self.h.study_code_tool.await_args_list]
        self.assertEqual(files, [CLIENT, SERVER])


if __name__ == '__main__':
    unittest.main(verbosity=2)
