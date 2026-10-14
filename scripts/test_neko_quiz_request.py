"""Actual avatar/entry -> prompt and temporary SQLite; no provider or audio."""
import json
import unittest
from unittest.mock import AsyncMock

import test_neko_quiz_material_guard as quiz
from test_neko_explanation_language import Harness as AvatarHarness
from test_neko_learning_preferences import prefs

class Harness(AvatarHarness, quiz.Harness):
    pass

class QuizRequest(unittest.IsolatedAsyncioTestCase):
    setUp=quiz.QuizMaterialGuard.setUp
    tearDown=quiz.QuizMaterialGuard.tearDown
    prepare=quiz.QuizMaterialGuard.prepare
    harness=Harness

    async def test_native_picture_request_reaches_model_prompt_and_current_identity(self):
        h=await self.prepare()
        request='只问箭头方向，给出从左向右或从右向左两个选项，不公布答案，最多一句话。'
        before=prefs.load_preferences(self.store)
        result=await h.study_quiz_tool(request=request)
        self.assertEqual(result['question'],'Which direction does the arrow point?')
        args=h._agent.question_generate.call_args
        self.assertIn(request,args.args[0])
        self.assertIn('source-A: arrows A to B',args.args[0])
        self.assertEqual(args.kwargs['context']['vision_image_base64'],'image-A')
        prompt=quiz.memory.prompts.build_question_generate_messages(text=args.args[0],language='zh-CN',context=args.kwargs['context'])
        self.assertIn(request,prompt[1]['content'])
        self.assertIn('must not also',prompt[1]['content'])
        public=json.dumps(result)
        self.assertNotIn('reference_answer',public)
        self.assertEqual(result['hint'],'')
        self.assertEqual(prefs.load_preferences(self.store),before)
        self.assertEqual(h._state.current_question['internal_private_payload']['source_material_context']['material_identity'],
                         quiz.materials.material_context(h)['material_identity'])

    async def test_topic_and_targeted_requests_keep_selected_subject_and_no_saved_picture(self):
        for targeted in (False,True):
            with self.subTest(targeted=targeted):
                h=await self.prepare()
                if targeted:h._cfg.llm_vision_enabled=False
                request='Ask one binary choice; do not give its answer.'
                await h.study_quiz_tool(topic='' if targeted else 'Arrows',request=request)
                args=h._agent.question_generate.call_args
                self.assertIn(request,args.args[0])
                self.assertIn('Arrows',args.args[0])
                self.assertEqual(args.kwargs['context']['vision_image_base64'],'')
                self.assertFalse(args.kwargs['context']['vision_enabled'])
                if targeted:self.assertEqual(args.kwargs['context']['selected_topic_id'],'course-A::Arrows')

    async def test_stale_picture_does_not_generate_or_replace_pending_question(self):
        h=await self.prepare()
        snapshot=await h._study_native_material_snapshot(include_material=True)
        h._study_native_material_snapshot=AsyncMock(return_value=snapshot)
        h._state.last_vision_image_base64='image-B'
        result=await h.study_quiz_tool(request='Only direction, two options.')
        self.assertIsInstance(result['result'],quiz.Err)
        self.assertEqual(result['result'].error.code,'course_context_changed')
        h._agent.question_generate.assert_not_awaited()
        self.assertEqual(h._state.current_question,{})
        self.assertEqual(self.store.list_interactions(10,session_id=h._study_session_id),[])

    async def test_format_request_cannot_replace_missing_source_material(self):
        for image in ('','image-A'):
            with self.subTest(image=image):
                h=await self.prepare()
                h._cfg.llm_vision_enabled=False
                h._state.last_ocr_text=''
                h._state.last_vision_image_base64=image
                result=await h.study_quiz_tool(request='Two options about this picture only.',target_weak=False)
                self.assertFalse(result['ok'])
                self.assertEqual(result['code'],'MISSING_TEXT')
                h._agent.question_generate.assert_not_awaited()
                self.assertEqual(h._state.current_question,{})
                self.assertEqual(self.store.list_interactions(10,session_id=h._study_session_id),[])

if __name__=='__main__':unittest.main(verbosity=2)
