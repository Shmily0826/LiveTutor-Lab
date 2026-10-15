"""Deterministic check of a source explanation against the evidence the teacher was actually shown.

Three things are checked and nothing else:
  line       a cited line number must be one of the lines the evidence printed for that file
             (or, when no file is named, for any shown file);
  placement  "第二十二行抛出异常" must not pin throw/catch on a line whose text lacks it while the
             evidence holds that word on another line;
  identifier a code-shaped identifier the reply names must appear in the evidence or the question.
No model, no I/O. The reply may already be in spoken form ("第二十三行"), so Chinese numerals work.
"""
from __future__ import annotations

import re
from typing import Any

_DIGIT = {c: i for i, c in enumerate("零一二三四五六七八九")} | {"两": 2}
_UNIT = {"十": 10, "百": 100, "千": 1000}
_NUM = r"(?:\d{1,5}|[零一二两三四五六七八九十百千]{1,8})"
_SEP = r"(?:到|至|~|～|[-–—])"
_LIST_SEP = r"(?:、|，|,|和|及|与|跟)"
_FILE = r"[\w./\\-]+\.(?:dart|jsx?|tsx?|py|java|kt|swift|cc?|cpp|h|cs|go|rs|rb|php|json|ya?ml|md|html|css|xml)"

_ZH_LINES = re.compile(
    rf"(?:(?P<file>{_FILE})\s*(?:的|中的|里的)?\s*)?第\s*(?P<a>{_NUM})\s*(?:(?P<sep>{_SEP}|{_LIST_SEP})\s*(?:第\s*)?(?P<b>{_NUM}))?\s*行")
_ZH_BARE_RANGE = re.compile(rf"(?<![\w第])(?P<a>\d{{1,5}})\s*{_SEP}\s*(?P<b>\d{{1,5}})\s*行")
_EN_LINES = re.compile(
    rf"(?:(?P<file>{_FILE})[\s,:]*)?\blines?\s+(?P<a>\d{{1,5}})(?:\s*(?P<sep>to|and|-|–|—|through)\s*(?P<b>\d{{1,5}}))?\b", re.I)
_FILE_COLON = re.compile(rf"(?P<file>{_FILE}):(?P<a>\d{{1,5}})(?:\s*(?P<sep>[-–—])\s*(?P<b>\d{{1,5}}))?(?![\d])")

# Code-shaped words only: ordinary prose words are never "named identifiers".
_IDENT = re.compile(
    r"\b[a-z][a-z0-9]*(?:[A-Z][a-z0-9]*)+\b|"              # camelCase
    r"\b[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+\b|"          # snake_case / UPPER_SNAKE
    rf"\b{_FILE}\b|"                                         # file names
    r"\b[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]+)+\b")               # PascalCase

_BASENAME = re.compile(r"[\\/]")
_HEADER = re.compile(r"`([^`\n]+\.\w+)`")
_NUMBERED = re.compile(r"^\s*(\d+)\t(.*)$")
_PUNCT = re.compile(r"[，,。；;！!？?\n：:]")
# (what the reply says in words, what the cited line must then contain)
_PLACEMENT = (
    (re.compile(r"抛出?|\bthrows?\b|\bthrown\b", re.I), re.compile(r"\bthrow\b")),
    (re.compile(r"捕获|\bcatch(?:es)?\b", re.I), re.compile(r"\bcatch\b")),
)


def zh_number(token: str) -> int | None:
    """Digits or the spoken Chinese form produced for line numbers (0-9999)."""
    token = token.strip()
    if token.isdigit():
        return int(token)
    if not token or any(c not in _DIGIT and c not in _UNIT for c in token):
        return None
    total, current = 0, 0
    for char in token:
        if char in _DIGIT:
            current = _DIGIT[char]
        else:
            total += (current or 1) * _UNIT[char]
            current = 0
    return total + current


def shown_lines(sources: list[dict[str, Any]] | None) -> dict[str, set[int]]:
    """{file basename: lines the evidence printed}. Paths are matched by their last component."""
    shown: dict[str, set[int]] = {}
    for source in sources or []:
        for item in (source or {}).get("shown") or []:
            if not isinstance(item, dict) or not isinstance(item.get("file"), str):
                continue
            name = _BASENAME.split(item["file"])[-1]
            shown.setdefault(name, set()).update(n for n in item.get("lines") or [] if type(n) is int)
    return shown


def line_claims(text: str) -> list[dict[str, Any]]:
    """Every line citation in the reply: {span, file, numbers, text}. Overlapping matches keep the first.

    The span covers the line phrase only ("第二十三行"); a file name in front of it stays outside it.
    """
    claims: list[dict[str, Any]] = []
    for pattern in (_FILE_COLON, _ZH_LINES, _EN_LINES, _ZH_BARE_RANGE):
        for match in pattern.finditer(text):
            span = match.span()
            if any(span[0] < other["span"][1] and other["span"][0] < span[1] for other in claims):
                continue
            groups = match.groupdict()
            first = zh_number(match.group("a"))
            second = zh_number(groups["b"]) if groups.get("b") else None
            if first is None or (groups.get("b") and second is None):
                continue
            file = groups.get("file") or ""
            start = span[0]
            if file:  # the file name stays in the reply; only the line phrase is the claim
                if pattern is _FILE_COLON:
                    start = match.start("a") - 1
                else:
                    rest = match.group(0)[match.group(0).find(file) + len(file):]
                    phrase = re.search(r"第|\blines?\b", rest, re.I)
                    start = span[1] - len(rest) + (phrase.start() if phrase else 0)
            is_range = bool(groups.get("b")) and (groups.get("sep") or "") in ("到", "至", "~", "～", "-", "–", "—", "to", "through")
            claims.append({"span": (start, span[1]), "file": _BASENAME.split(file)[-1] if file else "",
                           "numbers": [n for n in (first, second) if n is not None],
                           "range": is_range, "text": text[start:span[1]]})
    return sorted(claims, key=lambda claim: claim["span"])


def line_violations(text: str, sources: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    shown = shown_lines(sources)
    everywhere = set().union(*shown.values()) if shown else set()
    bad = []
    for claim in line_claims(text):
        allowed = shown.get(claim["file"], set()) if claim["file"] else everywhere
        missing = [n for n in claim["numbers"] if n not in allowed]
        if missing:
            bad.append({**claim, "missing": missing, "kind": "line"})
    return bad


def evidence_lines(evidence: str) -> dict[str, dict[int, str]]:
    """{file basename: {line number: text}} from the numbered code blocks the evidence prints."""
    found: dict[str, dict[int, str]] = {}
    current = ""
    for line in str(evidence or "").splitlines():
        numbered = _NUMBERED.match(line)
        if numbered:
            if current:
                found[current][int(numbered.group(1))] = numbered.group(2)
            continue
        header = _HEADER.search(line)
        if header:
            current = _BASENAME.split(header.group(1))[-1]
            found.setdefault(current, {})
    return found


def placement_violations(text: str, evidence: str) -> list[dict[str, Any]]:
    """A reply that pins throw/catch on a line the evidence shows without it.

    Only the tight form counts: the anchor word within a few characters of the line phrase and no
    punctuation between ("第二十二行抛出异常"). "第22行判断状态码，不是200就抛异常" describes a guard
    and stays legal. Skipped when the evidence has no numbered text for the file.
    """
    table = evidence_lines(evidence)
    if not table:
        return []
    bad = []
    for claim in line_claims(text):
        if claim["file"] and claim["file"] not in table:
            continue
        files = [claim["file"]] if claim["file"] else list(table)
        numbers = claim["numbers"]
        wanted = list(range(numbers[0], numbers[-1] + 1)) if claim["range"] and len(numbers) == 2 and numbers[1] >= numbers[0] else numbers
        tail = _PUNCT.split(text[claim["span"][1]:claim["span"][1] + 10])[0]
        head = _PUNCT.split(text[max(0, claim["span"][0] - 10):claim["span"][0]])[-1]
        for said, must in _PLACEMENT:
            if not (said.search(tail[:8]) or said.search(head[-8:])):
                continue
            if any(must.search(table[name].get(number, "")) for name in files for number in wanted):
                continue
            elsewhere = sorted({n for name in files for n, code in table[name].items() if must.search(code)})
            if elsewhere:  # only when the evidence really holds the word on some other line
                bad.append({**claim, "kind": "placement", "missing": list(numbers), "found_on": elsewhere[:4]})
    return bad


def identifier_violations(text: str, evidence: str, question: str = "") -> list[dict[str, Any]]:
    haystack = f"{evidence}\n{question}"
    lowered = haystack.lower()
    bad, seen = [], set()
    for match in _IDENT.finditer(text):
        word = match.group(0)
        if word in seen:
            continue
        seen.add(word)
        base = _BASENAME.split(word)[-1]
        if word in haystack or (base != word and base in haystack) or (word.lower() in lowered and "." in word):
            continue
        bad.append({"span": match.span(), "text": word, "kind": "identifier"})
    return bad


def check_reply(text: str, sources: list[dict[str, Any]] | None, evidence: str, question: str = "") -> list[dict[str, Any]]:
    if not isinstance(text, str) or not text.strip():
        return []
    names = " ".join(shown_lines(sources))  # a shown file's own name is evidence too
    lines = line_violations(text, sources)
    flagged = {item["span"] for item in lines}  # an out-of-window line needs no second finding
    return (lines + [item for item in placement_violations(text, evidence) if item["span"] not in flagged]
            + identifier_violations(text, evidence + " " + names, question))


def describe(violations: list[dict[str, Any]], sources: list[dict[str, Any]] | None) -> str:
    """The retry note: what was wrong and what the evidence really contains."""
    shown = shown_lines(sources)
    windows = "; ".join(f"{name} lines {min(lines)}-{max(lines)}" for name, lines in sorted(shown.items()) if lines) \
        or "no numbered source lines"
    parts = []
    for item in violations:
        if item["kind"] == "line":
            parts.append(f"'{item['text']}' cites line(s) {item['missing']} that were not shown")
        elif item["kind"] == "placement":
            parts.append(f"'{item['text']}' puts the statement on line(s) {item['missing']}, "
                         f"but the evidence has it on line(s) {item['found_on']}")
        else:
            parts.append(f"'{item['text']}' does not appear in the evidence")
    return ("Your previous answer failed a citation check: " + "; ".join(parts[:6]) + f". The evidence shows only: {windows}. "
            "Answer again. Cite only line numbers printed in the evidence, name only identifiers that appear in it, "
            "and say plainly when something is an inference or is not shown.")


_SENTENCE_END = re.compile(r"(?<=[。！？；])|(?<=[.!?;])(?=\s|$)")


def _drop_claim(text: str, span: tuple[int, int]) -> str:
    start, end = span
    head, tail = text[:start], text[end:]
    head = re.sub(r"(?:在|于|从|见|看)\s*$", "", head)
    head = re.sub(r"(\.(?:dart|jsx?|tsx?|py|json|ya?ml|html|css))\s*(?:的|中的|里的)\s*$", r"\1 ", head)
    tail = re.sub(r"^\s*(?:的|处|里|中)(?=[^\w]|[一-鿿])", "", tail)
    return (head + tail).replace("，，", "，").replace("  ", " ")


def strip_violations(text: str, violations: list[dict[str, Any]]) -> str:
    """Remove unsupported line citations, and sentences naming an unseen identifier.

    What is left is the rest of the reply, unchanged. Returns "" when nothing usable remains.
    """
    result = text
    for item in sorted((v for v in violations if v["kind"] in ("line", "placement")), key=lambda v: -v["span"][0]):
        result = _drop_claim(result, item["span"])
    names = [v["text"] for v in violations if v["kind"] == "identifier"]
    if names:
        kept = [s for s in _SENTENCE_END.split(result) if s and not any(name in s for name in names)]
        result = "".join(kept)
    return re.sub(r"\s{2,}", " ", result).strip()
