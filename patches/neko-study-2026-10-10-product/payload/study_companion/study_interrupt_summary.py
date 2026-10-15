"""A learner who cuts in with "等一下 / 先说结论" wants the point of what was just said, not a new lesson.

Measured 2026-10-16 (codex-r2-p8-source-overlap): the speech recogniser split the interruption into
"等一下。" and "先说结论。"; the character then handed the bare phrase "先说结论" to study_explain, and the
teacher, holding only that phrase, described where the file lives. This module recognises exactly such
a request so study_explain can answer it from the explanation that is already stored, without a model
request and without a new source read. Pure functions, no I/O.
"""
from __future__ import annotations

import re

_LEAD = r"(?:(?:等一下|等等|等会儿?|停一下|停|先|那|好|好的|嗯|呃|哦|你|请|就|直接)[，,。.!！\s]*)*"
_ASK_ZH = re.compile(
    rf"^{_LEAD}(?:说|讲|给我|告诉我|来)?\s*(?:一下|个|一句话)?\s*(?:结论|重点|要点|大意|总结|一句话)(?:是什么|吧|就行|就好|即可|先)?[，,。.!！？?\s]*$")
_ASK_EN = re.compile(
    r"^(?:(?:wait|hold on|stop|ok|okay|so|well|just|first|please)[,.\s]*)*(?:give me |tell me |say )?(?:the )?"
    r"(?:conclusion|bottom line|short version|summary|main point|gist)(?: first)?[.!? ]*$", re.I)
_PAUSE_ONLY = re.compile(r"^(?:等一下|等等|等会儿?|停一下|停|先停|stop|wait|hold on)[，,。.!！？?\s]*$", re.I)
_CJK_GAP = re.compile(r"(?<=[一-鿿，。！？、])\s+(?=[一-鿿，。！？、])")
_SENTENCE = re.compile(r"(?<=[。！？；])|(?<=[.!?;])(?=\s|$)")


def classify(text: object) -> str:
    """'conclusion' for 先说结论-style requests, 'pause' for a bare 等一下, else ''."""
    if not isinstance(text, str):
        return ""
    sentence = _CJK_GAP.sub("", text.strip())  # the recogniser spaces Chinese characters: "先 说 结 论"
    if not sentence or len(sentence) > 40:
        return ""
    if _PAUSE_ONLY.match(sentence):
        return "pause"
    return "conclusion" if _ASK_ZH.match(sentence) or _ASK_EN.match(sentence) else ""


def conclusion_of(previous_reply: object) -> str:
    """The one-sentence point of an earlier explanation: its first sentence (two if the first is a stub)."""
    if not isinstance(previous_reply, str):
        return ""
    sentences = [s.strip() for s in _SENTENCE.split(previous_reply.strip()) if s.strip()]
    if not sentences:
        return ""
    return sentences[0] if len(sentences[0]) >= 12 or len(sentences) == 1 else sentences[0] + sentences[1]


def last_explanation(rows: list[dict]) -> str:
    """Newest stored teacher reply that is a real, non-degraded explanation (rows come newest first)."""
    for row in rows or []:
        if row.get("kind") != "concept_explain":
            continue
        metadata = row.get("metadata") or {}
        output = row.get("output_text")
        if metadata.get("degraded") or not isinstance(output, str) or not output.strip():
            continue
        if classify(str(row.get("input_text") or "").split("\n", 1)[0]):
            continue  # an earlier interruption phrase is not an explanation to summarise
        return output
    return ""
