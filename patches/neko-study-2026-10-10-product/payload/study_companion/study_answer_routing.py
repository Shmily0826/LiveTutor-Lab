"""Decide whether a learner's sentence, spoken while a quiz question waits, is an answer.

A pending, ungraded quiz question changes what an ordinary statement means: "这张图根本没有箭头"
is the learner's answer, not a complaint about the material. Only an explicit request to look at
the material again, or a question/request/control phrase, keeps the normal explain path.
Pure functions, no I/O, no model: the rule is meant to be predictable and testable.
"""
from __future__ import annotations

import re

ANSWER = "answer"
MATERIAL_CORRECTION = "material_correction"
OTHER = "other"

_LEADING_FILLER = re.compile(r"^[\s，,。.、…~～-]*(?:(?:嗯+|啊+|哦+|呃+|额+|那个|那|好|好的|对|um+|uh+|well|so|ok(?:ay)?)[\s，,。.、…]*)*", re.I)

# The learner asks to look at the material again, or says the material changed.
_MATERIAL_CORRECTION = re.compile(
    r"你(?:刚才|刚刚|之前)?(?:读|看|讲|说|理解|解释)(?:错|反)|"
    r"你(?:刚才|刚刚|之前)?(?:说|讲|解释)得?(?:的)?(?:不对|不准确|有误|有问题)|"
    r"(?:重新|再)(?:检查|核对|看|读)|再(?:看|读|检查)\s*(?:一|1)?\s*(?:遍|次|下)|"
    r"(?:图|图片|截图)(?:已经)?(?:换|更新|变)了|换(?:了|成)(?:新的?)?(?:一张)?(?:图|图片|截图)|"
    r"\b(?:you (?:misread|got .{0,30}wrong)|misread|recheck|look (?:at (?:it|that|this) )?again|"
    r"(?:i|we) (?:changed|replaced|updated) the (?:picture|image|diagram|screenshot))\b",
    re.I)

# Questions, requests and control phrases are never an answer.
_INTERROGATIVE = re.compile(
    r"吗\s*[？?。.]?\s*$|什么|怎么|怎样|为什么|为啥|如何|哪(?:个|里|儿|些|一)|多少|是否|能不能|可不可以|是不是|对不对|"
    r"\b(?:what|why|how|which|where|when|who|whose|is it|are they|does it|do you|can you|could you|would you)\b", re.I)
_REQUEST_START = re.compile(
    r"^(?:请|麻烦|帮我|给我|再(?:讲|说|解释|读|来|出)|讲(?:讲|一下|解)|解释|说明|说说|看一下|看看|"
    r"出(?:一|下一|另一)?(?:道|个)?题|下一(?:题|道)|换(?:一|个)(?:题|道)|总结|继续|等一下|等等|等会|先别|先说|停|"
    r"please\b|can you\b|could you\b|explain\b|tell me\b|show me\b|next question\b|wait\b|stop\b|hold on\b|give me\b)", re.I)

_EXPLICIT = re.compile(
    r"(?:我的)?(?:答案|回答|选择)\s*(?:是|为|:|：)|我(?:选|答|认为|觉得|想(?:是|应该|会|它|这|选)|猜|以为|记得|感觉|看是)|应该是|是[^，。,.]{0,6}吧|"
    r"\b(?:my answer|the answer is|i (?:think|guess|believe|choose|chose|pick|would say)|it(?:'s| is))\b", re.I)
_NEGATION_OR_DOUBT = re.compile(
    r"根本|没有|没连|不连|不是|不对|不会|不存在|并没|并不|不知道|不清楚|不确定|不太确定|不太清楚|不记得|不懂|想不起|"
    r"好像|大概|可能|也许|或许|应该|"
    r"\b(?:don't know|do not know|not sure|no[,.]|nope|maybe|probably|perhaps|not really|there (?:is|are) no)\b", re.I)
_BARE_VERDICT = re.compile(r"^(?:是的?|对的?|没错|正确|错的?|不对|不是|yes|no|true|false|right|wrong)[\s。.!！]*$", re.I)
_CODE_STATEMENT = re.compile(
    r"指向|调用|返回|抛出|抛|连接|依赖|读取|传给|先[^，。,.]{0,12}再|->|→|\b(?:calls?|points? to|returns?|throws?|depends on)\b", re.I)
_IDENTIFIER = re.compile(r"\b[A-Z]{2,}[A-Za-z0-9_]*\b|\b[a-z_]+\.(?:dart|js|py|ts|json)\b|第\s*\d+\s*行|\b\d{3}\b|\bnull\b", re.I)


_CJK_GAP = re.compile(r"(?<=[一-鿿，。！？、])\s+(?=[一-鿿，。！？、])")


def classify_pending_turn(text: object) -> str:
    """Return ANSWER, MATERIAL_CORRECTION or OTHER for a sentence heard during a pending question."""
    if not isinstance(text, str):
        return OTHER
    # The recogniser writes Chinese with a space between characters ("这 张 图"); the model may pass it on as is.
    sentence = _LEADING_FILLER.sub("", _CJK_GAP.sub("", text)).strip()
    if not sentence or len(sentence) > 400:
        return OTHER
    if _MATERIAL_CORRECTION.search(sentence):
        return MATERIAL_CORRECTION
    if _INTERROGATIVE.search(sentence) or _REQUEST_START.search(sentence):
        return OTHER
    if _BARE_VERDICT.match(sentence):
        return ANSWER
    if _EXPLICIT.search(sentence) or _NEGATION_OR_DOUBT.search(sentence):
        return ANSWER
    if _CODE_STATEMENT.search(sentence) and _IDENTIFIER.search(sentence):
        return ANSWER
    if _CODE_STATEMENT.search(sentence) and len(sentence) <= 60:
        return ANSWER
    return OTHER


def has_pending_question(held: object) -> bool:
    """True when a generated question is waiting for its first grade and nothing is grading it."""
    if not isinstance(held, dict) or not held.get("question_id") or not held.get("attempt_id"):
        return False
    return (held.get("attempt_evaluated") is False
            and not held.get("attempt_evaluation_pending")
            and not held.get("attempt_evaluation_owner"))
