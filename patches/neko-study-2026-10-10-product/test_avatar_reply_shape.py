"""Check the avatar reply shape without network or credentials.

The desktop chat window renders an inline code span as a block-level chip and a
fenced block as a scrollable box with a language header, which cut identifiers off
mid-line at the window width (measured in /chat_full on 2026-10-10). The avatar
tool layer flattens that markup, so this pins the flattening and, more importantly,
that the code identifiers survive byte-for-byte.
"""
import ast
import json
from pathlib import Path
from typing import Any
import re
from types import SimpleNamespace

SOURCE = Path(__file__).parent / 'payload/study_companion/study_avatar_tools.py'
KEEP_NAMES = {'RELAY_NOTE', '_FENCE_LINE', '_FENCE_MARK', '_CODE_SPAN', '_SPEAKABLE_FIELDS',
              '_speakable', '_teaching', '_first_text', '_relay_for', '_relay_for_data',
              '_ack_wording', '_teaching_failure_wording'}


def load_shape_helpers():
    """Exec just the reply-shaping part of the tool module.

    Importing the real module needs the host's plugin SDK, which only exists
    inside the deployed plugin directory; the shaping code has no such dependency.
    """
    tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
    body = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = {t.id for t in node.targets if isinstance(t, ast.Name)}
            if names & KEEP_NAMES:
                body.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in KEEP_NAMES:
            body.append(node)
    assert len(body) >= 9, f'missing reply-shaping code in {SOURCE}: {[getattr(n, "name", None) for n in body]}'
    module = ast.Module(body=body, type_ignores=[])
    namespace: dict[str, Any] = {'json': json, 're': re, 'Any': Any}
    exec(compile(module, str(SOURCE), 'exec'), namespace)
    return namespace


def check():
    shape = load_shape_helpers()
    # Build the actual avatar request that previously carried three competing
    # length instructions; user limits must survive without numeric defaults.
    tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
    avatar = next(n for n in tree.body if isinstance(n, ast.ClassDef))
    keep = []
    for node in avatar.body:
        if isinstance(node, ast.Assign) and any(getattr(t, 'id', '') in
                {'LANGUAGE_DIRECTIVES', 'PACING_DIRECTIVE'} for t in node.targets):
            keep.append(node)
        elif getattr(node, 'name', '') == '_study_language_directive':
            keep.append(node)
    directive_class = ast.ClassDef(name='Directive', bases=[], keywords=[], body=keep, decorator_list=[])
    ns = {'Any': Any}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[directive_class], type_ignores=[])),
                 str(SOURCE), 'exec'), ns)
    directive = ns['Directive']()
    directive._cfg = SimpleNamespace(language='zh-CN')
    directive._study_effective_language = lambda: directive._cfg.language
    for language, question in [('zh-CN', '用中文两句话解释 return，不要出题。'),
                               ('en-US', 'Explain return in exactly two sentences, no quiz.')]:
        actual = directive._study_language_directive('add(2, 3)', question, turn_language=language)
        assert question in actual and 'add(2, 3)' in actual, actual
        defaults = actual.split('[Teaching constraints]', 1)[1]
        assert '2-4' not in defaults and '两三句' not in defaults and 'two or three' not in defaults, defaults
        assert 'explicit sentence limit' in defaults and 'no self-quiz' in defaults, defaults
    assert directive._cfg.language == 'zh-CN', 'one-turn language must not change course preference'
    speakable = shape['_speakable']
    reply = (
        "`context.watch` 给这个 widget 挂上订阅，`notifyListeners()` 一响它就重建。\n"
        "```dart\n"
        "onPressed: () => context.read<Counter>().increment(), // no subscription\n"
        "```\n"
        "一句话：watch 会跟着刷新，read 不会。"
    )
    flat = speakable(reply)

    assert '`' not in flat, f'backticks survived: {flat!r}'
    assert 'dart' not in flat.split('\n')[0].lower(), 'fence language tag leaked into prose'
    for token in ('context.watch', 'notifyListeners()', 'context.read<Counter>().increment()'):
        assert token in flat, f'identifier no longer exact: {token}'
    lines = flat.split('\n')
    assert '' in lines, 'dropping the fence welded the code onto the prose'
    assert lines[lines.index('') + 1].startswith('onPressed:'), flat

    # A closing fence glued onto the code line is what the model actually emits.
    assert '`' not in speakable('onPressed: () => read<Counter>().increment();```')

    teaching = json.loads(shape['_teaching'](tool='study_explain', reply=reply,
                                            mode='companion', degraded=False))
    assert '`' not in teaching['reply']
    assert teaching['relay'] == shape['RELAY_NOTE'], 'relay instruction must stay verbatim'
    assert teaching['mode'] == 'companion' and teaching['degraded'] is False

    for tool in ('study_explain', 'study_quiz', 'study_answer', 'study_summary'):
        failed = json.loads(shape['_teaching'](tool=tool, reply='stale content', question='fake quiz',
            score=1, verdict='correct', question_id='fake', attempt_id='fake', degraded=True,
            diagnostic='agent_quota_exceeded', failure_language='zh-CN', relay='keep teaching'))
        assert failed['status'] == 'unavailable' and '额度已用完' in failed['reply']
        assert not any(k in failed for k in ('question', 'score', 'verdict', 'question_id', 'attempt_id'))
        assert 'then stop' in failed['relay'] and 'stale content' not in failed['reply']
    failure_en = json.loads(shape['_teaching'](tool='study_explain', degraded=True,
        diagnostic='provider_unavailable', failure_language='en-US'))
    assert 'service did not return' in failure_en['reply'] and 'request limit' not in failure_en['reply']

    quiz = json.loads(shape['_teaching'](tool='study_quiz',
                                        question='用 `context.watch` 会怎样？',
                                        question_id='q_1', attempt_id='a_1'))
    assert quiz['question'] == '用 context.watch 会怎样？', quiz['question']
    assert quiz['question_id'] == 'q_1' and quiz['attempt_id'] == 'a_1', 'ids must pass through'

    # The relay instruction has to name the course language when the learner's own
    # words disagree with it; that is the defect seen in the native window.
    relay = shape['_relay_for']
    english = 'context.watch subscribes the widget, so notifyListeners() rebuilds it.'
    chinese = 'watch 就像在公告栏登记了名字，一贴新通知就喊你一声。'
    assert relay(english, 'en-US') == shape['RELAY_NOTE'], 'agreeing case must stay quiet'
    assert relay(chinese, 'zh-CN') == shape['RELAY_NOTE'], 'agreeing case must stay quiet'
    assert relay(chinese, '') == shape['RELAY_NOTE'], 'no preference set, nothing to pin'
    pinned_en = relay(chinese, 'en-US')
    assert pinned_en != shape['RELAY_NOTE'] and 'English' in pinned_en, pinned_en
    assert 'read it as written' in pinned_en
    pinned_zh = relay(english, 'zh-CN')
    assert '简体中文' in pinned_zh and pinned_zh != shape['RELAY_NOTE'], pinned_zh
    # The two no-cost tools hand back data, not wording, so the relay line is the only
    # thing that can pin the course language for them (08:29Z native turn answered in Chinese
    # while the course was pinned to English).
    data = shape['_relay_for_data']
    assert data('') == shape['RELAY_NOTE'], 'no preference set, nothing to pin'
    assert 'ANSWER IN ENGLISH' in data('en-US'), data('en-US')
    assert 'ANSWER IN 简体中文' in data('zh-CN'), data('zh-CN')
    assert '简体中文' in data('zh-CN'), data('zh-CN')

    # A course switch carries no teaching content, so the plugin writes the ack itself
    # rather than trusting an instruction (08:29Z: pinned en-US, window said 「已经换到…」).
    ack = shape['_ack_wording']
    state = {'course_id': 'flutter-provider', 'session_id': 'study-38ac',
             'started_at': '2026-10-09 22:25:24'}
    english_ack = ack('en-US', state)
    assert english_ack.startswith('Course switched to flutter-provider'), english_ack
    assert 'study-38ac' in english_ack and '2026-10-09 22:25:24' in english_ack
    assert not any('一' <= ch <= '鿿' for ch in english_ack), english_ack
    # The first live version of this read "Course switched to `x`., this session is ..."
    # (09:50Z, character's own tool route) - detail has to sit inside one sentence.
    assert '.,' not in english_ack and '..' not in english_ack, english_ack
    assert english_ack.count('.') == 1, english_ack
    chinese_ack = ack('zh-CN', state)
    assert '已经换到 flutter-provider' in chinese_ack and 'study-38ac' in chinese_ack
    # A backtick pair renders as a literal chip in the desktop chat and this string is
    # read aloud, so it ships without markdown (measured 09:53Z in the native window).
    assert '`' not in english_ack and '`' not in chinese_ack, (english_ack, chinese_ack)
    assert ack('', state) == '' and ack('ja-JP', state) == '', 'only languages we can write'
    assert ack('en-US', {'session_id': 'study-38ac'}) == '', 'no course, no ack'
    # An ack with only the course still reads as a sentence, not a comma-separated stub.
    assert ack('en-US', {'course_id': 'flutter-provider'}) == \
        'Course switched to flutter-provider.', ack('en-US', {'course_id': 'flutter-provider'})
    assert ack('zh-CN', {'course_id': 'flutter-provider'}) == '已经换到 flutter-provider 这门课。'

    print('PASS: avatar replies flatten to speakable text, identifiers and ids exact, '
          'relay pins the course language on mismatch, data-only tools get it too, no network')


if __name__ == '__main__':
    check()
