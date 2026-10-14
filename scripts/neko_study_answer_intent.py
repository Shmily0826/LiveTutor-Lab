"""Conservative explicit quiz intent and readonly persisted question identity.

No ASR ownership, provider, audio, model, or grading side effects live here.
The caller must retain the original text and validate live ownership separately.
"""
from contextlib import closing
from pathlib import Path
import re
import sqlite3
import stat


_TARGET_ZH = re.compile(r"(?:当前|刚才|刚刚|上一)(?:的|那|这)?(?:一)?(?:道|个)?(?:题(?:目)?|问题)")
_PERSONAL_ZH = re.compile(r"我的(?:答案|回答|选择)|我(?:的)?(?:回答|答(?:案|复)?|选(?:择)?|认为|觉得)")
_CORRECTION_ZH = re.compile(r"我(?:要|想|现在)?(?:更正|纠正|修正|改答|改选|重新回答|重新作答)|(?:更正|纠正|修正)(?:一下)?我(?:的|刚才的)(?:答案|回答)|我(?:的|刚才的)(?:答案|回答).{0,24}(?:改成|改为|换成|更正为|修正为)")
_JUDGE_ZH = re.compile(r"(?:请|帮我|麻烦|能否|可以)(?:你|我)?(?:判断|评分|评判|批改|打分|核对|检查)|(?:我的(?:答案|回答|选择)|我(?:选的|答的))[^。！？]{0,30}(?:对不对|是否正确|正确吗|答对了吗)|(?:判断|评分|评判|批改|打分)(?:一下)?(?:我|当前|刚才)")
_TARGET_EN = re.compile(r"\b(?:the\s+)?(?:current|last|previous|just[- ]asked)\s+(?:quiz\s+)?question\b|\bthe question you (?:just asked|asked just now)\b")
_PERSONAL_EN = re.compile(r"\bmy (?:answer|response|choice)\b|\bi (?:answer(?:ed)?|choose|chose|pick(?:ed)?|select(?:ed)?|think|believe|am answering)\b")
_CORRECTION_EN = re.compile(r"\bi(?: (?:want to |would like to |will |am )?|'m )(?:correct(?:ing)?|revise|revising|change|changing|amend) (?:my (?:answer|response|choice)|the answer i gave)\b|\b(?:correct|revise|amend) my (?:answer|response)\b|\bmy (?:answer|response|choice) (?:is now|should be|changes to)\b")
_JUDGE_EN = re.compile(r"(?:^|[.!?;,:]\s*|\b(?:and|then)\s+)(?:(?:please\s+)?(?:grade|score|judge|check|evaluate|mark)\b|(?:can|could|would|will) you (?:please )?(?:grade|score|judge|check|evaluate|mark)\b)|\b(?:is|was) my (?:answer|response|choice) (?:right|correct|wrong)\b|\b(?:am|was) i (?:right|correct|wrong)\b")
_REFUSE = re.compile(
    r"不是我(?:的)?(?:最终|正式)?(?:答案|回答|作答)|(?:还|尚)?(?:没|未)(?:有)?提交|"
    r"(?:不要|别)[^。！？]{0,8}(?:当成|当作|算作)[^。！？]{0,8}(?:答案|回答|作答)|"
    r"(?:只是|仅是|仅仅是)(?:举个)?(?:例子|示例)|"
    r"\bnot my (?:final |submitted |formal )?(?:answer|response|choice)\b|"
    r"\bi (?:have not|haven't) submitted\b|\bas an example\b|"
    r"(?:不要|别|先别|暂不|不需要|无需)[^。！？]{0,12}(?:提交|确认|记录|计分)|"
    r"(?:撤回|撤销|取消)[^。！？]{0,12}(?:答案|回答|作答|提交|评分)|"
    r"我(?:还|仍|尚)?(?:没|未)(?:想好|确定|确认|准备好)|我(?:还|仍)?不确定|我再想(?:一)?想|"
    r"(?:^|[。！？,，;；]\s*)(?:等一下|等等|先等等|撤回|算了)(?:[。！?？,，\s]|$)|"
    r"\b(?:don't|do not|not yet)\b[^.!?]{0,24}\b(?:submit|confirm|record|finalize|count)\b|"
    r"\bi(?: want to)? (?:withdraw|retract|cancel)\b|\b(?:withdraw|retract|cancel) my (?:answer|response|choice|submission)\b|"
    r"\bi(?:'m| am) (?:not sure|not certain|still thinking|still deciding)\b|\bi (?:have not|haven't) (?:decided|finished)\b|"
    r"(?:不要|别|不用|不需要|无需|暂不|拒绝)[^。！？]{0,16}(?:评分|判断|评判|批改|打分|检查|核对)|不评分|"
    r"(?:假设|假如|如果|比如|例如|引用|转述|复述|原话|他说|她说|他们说|别人|同学的|老师的|老师说|同学说|旧答案|解释旧)|你(?:的)?(?:答案|回答)|(?:出题|生成题|再给.{0,6}题|再出.{0,6}题)|"
    r"\b(?:don't|do not|no need to|without)\b[^.!?]{0,24}\b(?:grade|score|judge|evaluate|mark|check)\b|"
    r"\b(?:suppose|assuming|hypothetical|if|quote|quoted|quoting|he said|she said|they said|the teacher said|someone else's|another student's|old answer|your answer|your response)\b|"
    r"\b(?:generate|create|give|ask)\b[^.!?]{0,24}\b(?:question|quiz)\b|"
    r"^(?:请)?(?:解释|翻译|分析|朗读|复述)|^(?:please )?(?:explain|translate|read aloud|paraphrase)\b"
)
_QUOTED = re.compile(r'''"(?:\\.|[^"\\])*"|“[^”]*”|‘[^’]*’|「[^」]*」|『[^』]*』|(?<!\w)'[^'\n]*'(?!\w)''')
_DECLARED_OWN_ZH = re.compile(r"^(?:当前(?:的|这)?(?:一)?(?:道|个)?题(?:目)?[，,:：\s]*)?(?:我的答案|我的回答)(?:是|为)\s*(.{1,400})$")
_DECLARED_OWN_EN = re.compile(r"^my (?:answer|response)(?: to (?:the )?(?:current|last|previous) (?:quiz )?question)? is\s+(.{1,400})$")
_CHOSEN_OPTION = re.compile(r"^(?:当前(?:的|这)?(?:一)?(?:道|个)?题(?:目)?[，,:：\s]*)?我(?:选择|选)(?:的是|为)?\s*(?:选项)?\s*([a-d1-9一二三四](?:$|[\s。.!！,，;；:：].{0,399}))$|^i (?:choose|chose|pick|select)\s+([a-d1-9](?:$|[\s.!?,;:].{0,399}))$")


def answer_intent(text, *, allow_declared_answer=False):
    """Return 'answer', 'correction', or None; never return a shortened answer.

    shortcut: explicit common phrases only; expand with reviewed real ASR examples,
    never promote ambiguous conversation to automatic grading.
    """
    if not isinstance(text, str) or not text.strip():
        return None
    match_text = re.sub(r"(?<=[\u3400-\u9fff])\s+(?=[\u3400-\u9fff])", "", text).casefold()
    match_text = re.sub(r"\s+", " ", match_text).strip()
    match_text = _QUOTED.sub(' ', match_text)  # Quoted requests cannot authorize grading.
    if _REFUSE.search(match_text):
        return None
    declared = next((match for pattern in (_DECLARED_OWN_ZH, _DECLARED_OWN_EN, _CHOSEN_OPTION)
                     if (match := pattern.fullmatch(match_text))), None) if allow_declared_answer is True else None
    body = next((value for value in declared.groups() if value is not None), "") if declared else ""
    if (body.strip(" 。.!！,，;；")
            and not re.search(r"[?？]|什么|多少|是否|哪(?:个|里|一)|\b(?:what|which|who|where|why|how|whether)\b", body)):
        return "answer"
    if _TARGET_ZH.search(match_text):
        if _CORRECTION_ZH.search(match_text):
            return "correction"
        if _PERSONAL_ZH.search(match_text) and _JUDGE_ZH.search(match_text):
            return "answer"
    if _TARGET_EN.search(match_text):
        if _CORRECTION_EN.search(match_text):
            return "correction"
        if _PERSONAL_EN.search(match_text) and _JUDGE_EN.search(match_text):
            return "answer"
    return None


def grade_request_tail(text):
    """Only redundant request words; attribution is the caller's responsibility."""
    if not isinstance(text, str):
        return False
    compact = re.sub(r"\s+", "", text).strip(" 。.!！,，;；")
    return compact in {"请评分", "点评分", "请打分", "评分", "打分"}


def _safe_db(runtime_root):
    root = Path(runtime_root)
    if not root.is_absolute() or not root.is_dir() or root.is_symlink() or getattr(root, 'is_junction', lambda: False)():
        raise ValueError('runtime root is not a plain absolute directory')
    resolved_root = root.resolve(strict=True)
    db = root / 'plugins/study_companion/data/study_companion.db'
    for path in (db, *tuple(db.parents)[:3]):
        info = path.lstat()
        if path.is_symlink() or getattr(info, 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0x400):
            raise ValueError('linked database path')
    resolved = db.resolve(strict=True)
    info = resolved.stat()
    if not resolved.is_relative_to(resolved_root) or not resolved.is_file() or info.st_nlink != 1:
        raise ValueError('database is outside or linked')
    return resolved, (info.st_dev, info.st_ino)


def read_question_pin(runtime_root, *, include_empty=False):
    """One readonly state projection; call once before first speech frame, not per frame.

    This persisted identity is not live host boot/ASR owner authority.
    """
    try:
        path, identity = _safe_db(runtime_root)
        with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=0)) as connection:
            connection.execute('PRAGMA query_only=ON')
            rows = connection.execute("""SELECT
                json_extract(value,'$.study_course_id'),
                json_extract(value,'$.study_session_id'),
                json_extract(value,'$.current_question.question_id'),
                json_extract(value,'$.current_question.attempt_id'),
                json_extract(value,'$.current_question.attempt_evaluated'),
                json_type(value,'$.current_question.attempt_evaluated'),
                CASE WHEN json_type(value,'$.current_question') = 'object'
                     AND NOT EXISTS (SELECT 1 FROM json_each(kv.value,'$.current_question'))
                     THEN 1 ELSE 0 END
                FROM kv WHERE key='state' LIMIT 2""").fetchall()
        # Refuse a detected path/file replacement instead of returning its pin.
        if _safe_db(runtime_root) != (path, identity):
            return None
        if len(rows) != 1:
            return None
        row = rows[0]
        if (include_empty is True and row[6] == 1
                and all(isinstance(v, str) and v.strip() and len(v) <= 1024 for v in row[:2])
                and all(value is None for value in row[2:6])):
            return {'_question_empty': True, 'course_id': row[0], 'session_id': row[1]}
        if any(not isinstance(v, str) or not v.strip() or len(v) > 1024 for v in row[:4]) or row[5] not in ('true', 'false'):
            return None
        return dict(zip(('course_id', 'session_id', 'question_id', 'attempt_id', 'attempt_evaluated'), (*row[:4], row[5] == 'true')))
    except (OSError, ValueError, TypeError, sqlite3.Error):
        return None
