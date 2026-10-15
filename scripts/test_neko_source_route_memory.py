"""Source teaching: routing input, stored history text and teacher provenance (offline, fresh DB)."""
import json
import logging
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from test_neko_product_course_memory import ProductHarness, Store, constants, context_module, models, prompts

EXPLAIN = constants.LLM_OPERATION_CONCEPT_EXPLAIN
CODE = 'Authorized CodeGraph evidence ... 17\tif allowed:\n18\t    run()'


class SourceRouteMemory(unittest.IsolatedAsyncioTestCase):
    async def test_router_classifies_route_text_not_source_body(self):
        seen = []
        async def route(query, *, context):
            seen.append(query)
            return None, 'routing_unavailable', 'timeout'
        host = SimpleNamespace(_knowledge_guidance_topics_cache={'all:5000': []}, _route_study_input_semantics=route)
        build = context_module._TutorContextSupportMixin._build_knowledge_guidance_context
        await build(host, EXPLAIN, input_text=CODE, context={'source_text': CODE, 'semantic_route_text': 'why guard?'})
        await build(host, EXPLAIN, input_text=CODE, context={'source_text': CODE})
        # Without the internal route key every other caller keeps its original query.
        self.assertEqual(seen, ['why guard?', CODE])

    async def test_explanation_row_and_event_store_question_with_provenance_not_code(self):
        with tempfile.TemporaryDirectory() as temp:
            store = Store(Path(temp) / 'study.db', Path(temp) / 'seed.json', logging.getLogger('source-memory'))
            store.open()
            try:
                h = ProductHarness(store)
                await h._restart_study_session(course_id='course-A')
                session = h._study_session_id
                stored = 'why guard?\n[Source evidence] Project@rev main.py:17-18'
                reply = models.TutorReply(operation=EXPLAIN, input_text=CODE, reply='It guards the call.')
                await h._finalize_tutor_call(EXPLAIN, reply, history_kind=EXPLAIN, metadata={},
                                             extra_context={'session_id': session, 'history_input_text': stored})
                plain = models.TutorReply(operation=EXPLAIN, input_text='plain question', reply='Plain answer.')
                await h._finalize_tutor_call(EXPLAIN, plain, history_kind=EXPLAIN, metadata={},
                                             extra_context={'session_id': session})
                rows = store.list_interactions(5, session_id=session)
                self.assertEqual([row['input_text'] for row in rows], ['plain question', stored])
                events = [event.get('input_text') for event in h._state.recent_learning_events]
                self.assertIn(stored, events)
                self.assertNotIn(CODE, events)
            finally:
                store.close()

    def test_teacher_sees_recent_source_provenance_beyond_the_four_row_window(self):
        history = [{'id': 1, 'kind': 'code_question', 'input_text': '[Project@rev] main.py',
                    'output_text': 'Returned authorized source evidence: main.py:17-30'}]
        history += [{'id': index, 'kind': EXPLAIN, 'input_text': f'q{index}', 'output_text': f'a{index}'}
                    for index in range(2, 8)]
        block = prompts.build_concept_recent_context({'history': history})
        memory = json.loads(block.split(':\n', 1)[1])
        self.assertEqual([item['input'] for item in memory['recent_interactions']], ['q4', 'q5', 'q6', 'q7'])
        self.assertEqual(memory['recent_source_reads_provenance_only'],
                         [{'request': '[Project@rev] main.py',
                           'provenance': 'Returned authorized source evidence: main.py:17-30'}])
        self.assertNotIn('recent_source_reads_provenance_only',
                         prompts.build_concept_recent_context({'history': history[1:]}))


if __name__ == '__main__': unittest.main(verbosity=2)
