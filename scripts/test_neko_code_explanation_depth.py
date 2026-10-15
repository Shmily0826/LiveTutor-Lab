"""Teacher prompt must trace shown control flow, without guessing unseen callers."""
import ast
import json
from pathlib import Path
import unittest
import test_neko_source_question_kinds as fixtures


class CodeExplanationDepth(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = fixtures.SourceQuestionKinds.asyncSetUp
    asyncTearDown = fixtures.SourceQuestionKinds.asyncTearDown
    read = fixtures.SourceQuestionKinds.read
    ask = fixtures.SourceQuestionKinds.ask
    teacher_text = fixtures.SourceQuestionKinds.teacher_text

    async def test_guard_explanation_traces_next_statement_and_keeps_uncertainty_conditional(self):
        await self.ask('非200响应怎么处理，两句话。', [{'mode':'file','file':fixtures.CLIENT,'offset':20,'limit':10}])
        text=self.teacher_text()
        self.assertIn('trace whether the next shown statement executes',text)
        self.assertIn('do not assume an unseen response body',text)
        self.assertNotIn('404 always',text)

    def test_relay_keeps_every_sentence_without_an_extra_transition(self):
        source=Path(__file__).resolve().parents[1]/'patches/neko-study-2026-10-10-product/payload/study_companion/study_avatar_tools.py'
        tree=ast.parse(source.read_text(encoding='utf-8'))
        relay=next(ast.literal_eval(node.value) for node in tree.body if isinstance(node,ast.Assign)
                   and any(isinstance(target,ast.Name) and target.id=='RELAY_NOTE' for target in node.targets))
        self.assertIn('every sentence',relay)
        self.assertNotIn('one short transition',relay)

    async def test_serialized_request_object_is_validated_and_read_as_a_real_window(self):
        request={'mode':'file','file':fixtures.CLIENT,'offset':20,'limit':10}
        await self.ask('非200怎么处理？',[json.dumps(request)])
        self.h.study_code_tool.assert_awaited_once_with(**request)

    async def test_bad_serialized_object_does_not_fall_back_to_an_old_window(self):
        for value in ('{broken',json.dumps({'file':fixtures.CLIENT,'extra':'not a source field'})):
            with self.subTest(value=value):
                result=await self.ask('讲这段',[value])
                self.assertEqual(result['error'],'invalid_code_requests')
        self.h.study_code_tool.assert_not_awaited()


if __name__ == '__main__':unittest.main(verbosity=2)
