"""Explicit-language and synthetic SQLite tests; no services, devices, or models."""
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from neko_study_answer_intent import answer_intent, read_question_pin, grade_request_tail


class AnswerIntentTests(unittest.TestCase):
    def test_pending_own_declarations_need_literal_trusted_permission(self):
        for text in ('我的答案是 WEX 指向 NUD。','我的回答为 return "one"。','我选 B。','当前题，我选二。',
                     'My answer is B.','My response to the current question is REZ.','I choose B.'):
            with self.subTest(text=text):
                self.assertIsNone(answer_intent(text))
                self.assertIsNone(answer_intent(text,allow_declared_answer=1))
                self.assertEqual(answer_intent(text,allow_declared_answer=True),'answer')
        for text in ('B','REZ','我认为是B','I think B','我的答案是什么？','My answer is what should I do',
                     '我选择用英文解释。','I choose to change course.'):
            self.assertIsNone(answer_intent(text,allow_declared_answer=True))

    def test_withdrawal_uncertainty_and_no_submit_win_over_explicit_grading(self):
        for text in ('当前题，我的答案是B。撤回刚才的答案。','当前题，我的答案是B，请评分，我还没确定。',
                     '当前题，我选B，请评分，不要提交。','我的答案是B，先别记录。','我的答案是B。我再想想。',
                     'My answer to the current question is B. Please grade it. Do not submit it.',
                     'My answer is B. I withdraw my answer.',"My answer is B. I'm not sure.",
                     'I choose B. I have not decided.'):
            with self.subTest(text=text):
                self.assertIsNone(answer_intent(text))
                self.assertIsNone(answer_intent(text,allow_declared_answer=True))

    def test_real_short_declaration_needs_explicit_pending_caller_permission(self):
        for text in ('当 前 题 , 我 的 答 案 是 WEX 指 向 NUD 。',
                     '当前这道题，我的回答为 return "one"。'):
            self.assertIsNone(answer_intent(text))
            self.assertEqual(answer_intent(text, allow_declared_answer=True), 'answer')
        for text in ('当前题，我的答案是什么？', '当前题，我的答案是 。',
                     '当前题，我的答案是WEX，不要评分。', '假设当前题，我的答案是WEX。',
                     '他说当前题，我的答案是WEX。', '“当前题，我的答案是WEX。”',
                     '当前题，我觉得WEX。', '上一题，我的答案是WEX。',
                     '解释当前题，我的答案是WEX。', '当前题，我的答案是WEX，请再出一题。'):
            with self.subTest(text=text):
                self.assertIsNone(answer_intent(text, allow_declared_answer=True))

    def test_explicit_non_submission_and_non_final_declarations_are_refused(self):
        for text in ('我的答案是B，但这不是我的最终答案。',
                     '我的答案是B，只是举个例子，不要当成作答。',
                     '我选B，这只是示例，不是我的答案。',
                     '我的答案是B，但尚未提交。',
                     'My answer is B, but this is not my final answer.',
                     'I choose B as an example, not my answer.',
                     'My answer is B; I have not submitted it yet.'):
            with self.subTest(text=text):
                self.assertIsNone(answer_intent(text))
                self.assertIsNone(answer_intent(text, allow_declared_answer=True))

    def test_tail_policy_is_exact_request_only_without_authority_or_text_merging(self):
        for text in ('请 评 分 。', '点 评 分 。', '请打分', '评分', '打分。'):
            self.assertTrue(grade_request_tail(text))
        for text in ('不要评分', '请评分，我改为REZ', '点评分不是我的答案', '“请评分”',
                     '请评分？', '改成REZ', '如果请评分', '', None, True):
            self.assertFalse(grade_request_tail(text))

    def test_explicit_chinese_answers_and_spacing_original_kept(self):
        texts = ['当前这道题我的答案是一，请评分。',
                 '刚才那道题我选二，帮我判断对不对。',
                 '请判断当前题，我认为 WEX 调用 NUD，然后调用 REZ。',
                 '上一道题我的回答是 404，请打分。',
                 '刚 才 那 道 题 我 选 一， 请 判 断 我 的 答 案 对 不 对。',
                 '回答当前题：我的答案是 return "one"; 请评分。']
        for text in texts:
            with self.subTest(text=text):
                before = text.encode()
                self.assertEqual(answer_intent(text), 'answer')
                self.assertEqual(text.encode(), before)

    def test_explicit_english_answers(self):
        for text in ['My answer to the current question is A. Please grade my answer.',
                     'For the last question, I chose 404. Can you check my answer?',
                     'Grade my answer to the previous question: return "one";',
                     'I think the answer to the question you just asked is 2. Am I right?',
                     'My choice for the just-asked question is false. Please score it.']:
            with self.subTest(text=text):
                self.assertEqual(answer_intent(text), 'answer')

    def test_explicit_own_same_question_corrections(self):
        for text in ['我更正刚才那道题，答案是 REZ 先调用 NUD，再调用 WEX。',
                     '更正我的回答，当前题我的答案改为二。',
                     '刚才那道题我的答案改成二。',
                     'I want to correct my answer to the current question: A.',
                     'For the previous question, my answer should be 404.',
                     "I'm changing my answer to the current question: B.",
                     'Revise my answer to the last question: false.']:
            with self.subTest(text=text):
                self.assertEqual(answer_intent(text), 'correction')

    def test_chinese_refusals(self):
        for text in ['这张图对不对？', '你说的那个对不对？', '我觉得是一，帮我判断。',
                     '当前题我的答案是二，不要评分。', '当前题我选一，别判断对错。',
                     '解释旧答案：当前题我选一，请评分。',
                     '他说当前题我的答案是一，请评分。',
                     '引用：当前题我的答案是一，请评分。',
                     '假设当前题我的答案是一，请评分。',
                     '如果当前题我的答案是一，请评分会怎样？',
                     '当前题我选一，请再给我一题。',
                     '当前题我觉得你的答案需要更正。',
                     '当前题我认为你的答案是一，请评分。',
                     '老师说当前题我的答案是一，请评分。',
                     '请判断“当前题我的答案是一，请评分”这句话的语法。',
                     '“当前题我的答案是一，请评分。”',
                     '当前题的正确答案是什么？', '我更正一下，应该是一。']:
            with self.subTest(text=text):
                self.assertIsNone(answer_intent(text))

    def test_english_refusals(self):
        for text in ['Is the picture correct?', 'Is that right?', 'My answer is A. Please grade it.',
                     "My answer to the current question is A. Don't grade it.",
                     'My answer to the last question is A, do not score it.',
                     'Explain the old answer: my answer to the current question is A. Please grade it.',
                     'He said my answer to the current question is A. Please grade it.',
                     'Quote: my answer to the current question is A. Please grade it.',
                     'Suppose my answer to the current question is A. Please grade it.',
                     'If my answer to the current question is A, please grade it.',
                     'My answer to the current question is A. Give me another question.',
                     'Please correct the answer to the current question.',
                     'My answer to the current question is score = 3;',
                     'I think your answer to the current question is A. Please grade it.',
                     'The teacher said my answer to the current question is A. Please grade it.',
                     'Check the sentence "My answer to the current question is A. Please grade it."',
                     '"My answer to the current question is A. Please grade it."',
                     'The current question is hard; please grade the student.',
                     'I want to correct my answer: B.', '', None, 42]:
            with self.subTest(text=text):
                self.assertIsNone(answer_intent(text))
        self.assertIsNone(answer_intent('I want to change my course because the current question is hard.'))
        self.assertIsNone(answer_intent('I want to correct my pronunciation of the current question.'))


class QuestionPinTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='neko-question-pin-')
        self.root = Path(self.temp.name) / 'N.E.K.O'
        self.db = self.root / 'plugins/study_companion/data/study_companion.db'
        self.db.parent.mkdir(parents=True)
        self.state = {'study_course_id':'course-A', 'study_session_id':'session-A',
                      'current_question': {'question_id':'q-A', 'attempt_id':'a-A',
                          'attempt_evaluated':False, 'answer':'private-answer', 'rubric':'private-rubric'},
                      'recent_learning_events':['private-history']}
        with closing(sqlite3.connect(self.db)) as connection, connection:
            connection.execute('CREATE TABLE kv (key TEXT PRIMARY KEY, value TEXT)')
            connection.execute('CREATE TABLE interactions (private TEXT)')
            connection.execute("INSERT INTO interactions VALUES ('private-history')")
        self.save(self.state)

    def tearDown(self):
        self.temp.cleanup()

    def save(self, state):
        value = json.dumps(state) if not isinstance(state, str) else state
        with closing(sqlite3.connect(self.db)) as connection, connection:
            connection.execute('INSERT OR REPLACE INTO kv VALUES (?,?)', ('state', value))

    def test_exact_projection_no_history_and_byte_preservation(self):
        before = self.db.read_bytes()
        queries = []
        connect = sqlite3.connect
        def traced(*args, **kwargs):
            self.assertTrue(kwargs['uri'])
            self.assertEqual(kwargs['timeout'], 0)
            self.assertIn('?mode=ro', args[0])
            connection = connect(*args, **kwargs)
            connection.set_trace_callback(queries.append)
            return connection
        with patch('neko_study_answer_intent.sqlite3.connect', side_effect=traced):
            pin = read_question_pin(self.root)
        self.assertEqual(pin, {'course_id':'course-A','session_id':'session-A','question_id':'q-A','attempt_id':'a-A','attempt_evaluated':False})
        self.assertEqual(self.db.read_bytes(), before)
        self.assertNotIn('private', json.dumps(pin))
        self.assertEqual(sum(q.lstrip().upper().startswith('SELECT') for q in queries), 1)
        self.assertFalse(any('interactions' in q or 'SELECT value' in q for q in queries))
        self.assertTrue(any('query_only=ON' in q for q in queries))
        # Explicit close matters on Windows; no delayed connection GC required.
        self.db.rename(self.db.with_suffix('.closed'))

    def test_evaluated_true_is_boolean_and_context_changes_return_new_pin(self):
        self.state['current_question']['attempt_evaluated'] = True
        self.state['study_course_id'] = 'course-B'
        self.state['current_question']['question_id'] = 'q-B'
        self.save(self.state)
        pin = read_question_pin(self.root)
        self.assertIs(pin['attempt_evaluated'], True)
        self.assertEqual(pin['course_id'], 'course-B')
        self.assertEqual(pin['question_id'], 'q-B')

    def test_only_explicit_healthy_empty_object_can_report_no_question(self):
        self.state['current_question']={};self.save(self.state);before=self.db.read_bytes()
        self.assertIsNone(read_question_pin(self.root))
        self.assertEqual(read_question_pin(self.root,include_empty=True),
                         {'_question_empty':True,'course_id':'course-A','session_id':'session-A'})
        self.assertEqual(before,self.db.read_bytes())
        for value in (None,'{}',[],{'question':'legacy no identities'},{'attempt_evaluated':False}):
            self.state['current_question']=value;self.save(self.state)
            self.assertIsNone(read_question_pin(self.root,include_empty=True))
        self.state.pop('current_question');self.save(self.state)
        self.assertIsNone(read_question_pin(self.root,include_empty=True))

    def test_invalid_state_or_id_or_boolean_refused(self):
        invalid = ['broken', '[]', '{}']
        for key in ('study_course_id','study_session_id'):
            for value in ('', '  ', 4, None):
                state = json.loads(json.dumps(self.state)); state[key] = value; invalid.append(state)
        for key in ('question_id','attempt_id','attempt_evaluated'):
            state = json.loads(json.dumps(self.state)); state['current_question'].pop(key); invalid.append(state)
        for value in (1, 0, 'false', None):
            state = json.loads(json.dumps(self.state)); state['current_question']['attempt_evaluated'] = value; invalid.append(state)
        for state in invalid:
            with self.subTest(state=state):
                self.save(state)
                self.assertIsNone(read_question_pin(self.root))

    def test_missing_db_is_not_created_and_relative_root_refused(self):
        self.assertIsNone(read_question_pin(Path('relative-N.E.K.O')))
        missing = Path(self.temp.name) / 'missing'
        self.assertIsNone(read_question_pin(missing))
        self.assertFalse(missing.exists())
        self.db.unlink()
        self.assertIsNone(read_question_pin(self.root))
        self.assertFalse(self.db.exists())

    def test_exclusive_lock_fails_without_wait_or_writes(self):
        with closing(sqlite3.connect(self.db)) as writer:
            writer.execute('BEGIN EXCLUSIVE')
            self.assertIsNone(read_question_pin(self.root))
            writer.rollback()

    def test_symlink_outside_refused(self):
        target = Path(self.temp.name) / 'outside.db'
        self.db.rename(target)
        try:
            self.db.symlink_to(target)
        except OSError as error:
            target.rename(self.db)
            self.skipTest('Windows symbolic-link privilege unavailable: ' + str(error.winerror))
        else:
            self.assertIsNone(read_question_pin(self.root))
            self.db.unlink(); target.rename(self.db)

    def test_hardlink_refused(self):
        target = Path(self.temp.name) / 'outside.db'
        os.link(self.db, target)
        before = target.read_bytes()
        self.assertIsNone(read_question_pin(self.root))
        self.assertEqual(target.read_bytes(), before)

    def test_unknown_schema_refused(self):
        with closing(sqlite3.connect(self.db)) as connection, connection:
            connection.execute('DROP TABLE kv')
        self.assertIsNone(read_question_pin(self.root))

    def test_detected_file_replacement_before_return_refused(self):
        import neko_study_answer_intent as helper
        replacement = self.db.with_suffix('.replacement')
        with closing(sqlite3.connect(replacement)) as connection, connection:
            connection.execute('CREATE TABLE kv (key TEXT PRIMARY KEY, value TEXT)')
            connection.execute('INSERT INTO kv VALUES (?,?)', ('state', json.dumps(self.state)))
        safe = helper._safe_db
        calls = 0
        def replacing(root):
            nonlocal calls
            calls += 1
            if calls == 2:
                os.replace(replacement, self.db)
            return safe(root)
        with patch('neko_study_answer_intent._safe_db', side_effect=replacing):
            self.assertIsNone(read_question_pin(self.root))


if __name__ == '__main__':
    unittest.main(verbosity=2)
