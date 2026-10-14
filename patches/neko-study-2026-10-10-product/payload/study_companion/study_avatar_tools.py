"""Model-callable teaching tools for the native desktop character.

Every ability here already exists as a Study Companion plugin entry, which the
web panel drives by clicking Explain / Quiz / Evaluate. Declaring them with
``@llm_tool`` is the one missing link for the avatar: ``NekoPluginBase.__init__``
auto-registers them, the host forwards them to ``main_server``, and the
character's own conversation can then decide to call them. Nothing here
re-implements teaching logic; each handler delegates to an existing entry.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
from typing import Any
from urllib.parse import quote

import httpx
from plugin.sdk.plugin import llm_tool

RELAY_NOTE = (
    "Pass the reply text on to the learner as spoken by you. Keep its wording, "
    "language and code identifiers unchanged; do not translate, lengthen or "
    "summarize it. Add nothing except, at most, one short transition."
)

_OBJECT = {"type": "object", "properties": {}}

_FENCE_LINE = re.compile(r"^\s*(?:```|~~~)[a-zA-Z0-9+#._-]*\s*$")
_FENCE_MARK = re.compile(r"(?:```|~~~)[a-zA-Z0-9+#._-]*")
_CODE_SPAN = re.compile(r"`{1,3}([^`\n]+)`{1,3}")

# The desktop chat renders inline code as a block-level chip and a fenced block as
# a scrollable box with a language header, which cuts identifiers off mid-line at
# the window's width. A spoken tutor needs the characters exact rather than
# highlighted, so the markup comes out and the code keeps its own lines.
_SPEAKABLE_FIELDS = ("reply", "question", "hint", "summary")


def _speakable(text: Any) -> str:
    out: list[str] = []
    for line in str(text or "").splitlines():
        if _FENCE_LINE.match(line):
            # The fence was a paragraph break as much as markup; dropping it
            # without one would weld the code onto the prose above it.
            if out and out[-1].strip():
                out.append("")
            continue
        out.append(_FENCE_MARK.sub("", _CODE_SPAN.sub(r"\1", line)).rstrip())
    return "\n".join(out).strip()


def _envelope(result: Any) -> dict[str, Any]:
    """Turn an SDK ``Ok``/``Err`` into a plain dict for the model."""
    if hasattr(result, "is_ok"):
        if result.is_ok():
            value = result.value
            if isinstance(value, dict):
                return {"ok": True, **value}
            return {"ok": True, "result": value}
        return {"ok": False, "error": str(getattr(result, "error", result))[:400]}
    if isinstance(result, dict):
        return {"ok": True, **result}
    return {"ok": True, "result": result}


def _first_text(payload: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _relay_for_data(language: str) -> str:
    """Say this payload, don't read it out.

    The two tools that cost no model request hand back data (course state, OCR text),
    so the character composes the sentence itself and answered in whatever language the
    learner typed - a Chinese reply landed between two English ones while the course was
    pinned to English (2026-10-10 08:29Z, native window). Naming the course language is
    the only thing that reaches that path.
    """
    if not language:
        return RELAY_NOTE
    wanted = {"en-US": "English", "zh-CN": "简体中文"}.get(language, language)
    return (f"ANSWER IN {wanted.upper()}: these fields are data, not wording, so you are "
            f"composing the sentence yourself. This course is set to {wanted}, so compose it "
            f"in {wanted} even though the learner wrote in another language, and keep "
            "identifiers like watch/notifyListeners exactly as written.")


def _ack_wording(language: str, state: dict[str, Any]) -> str:
    """Write the course-switch acknowledgement in the course language.

    An ack carries no teaching content, so letting the model compose it only reproduced
    the bug the instruction above is meant to fix: with the course pinned to English the
    character said 「已经换到 flutter-provider 这门课」 (2026-10-10 08:29Z, native window).
    Handing it finished wording is what the model paths already do, and those were
    measured to keep the language they arrive in.
    """
    if language not in {"en-US", "zh-CN"}:
        return ""
    course = str(state.get("course_id") or "").strip()
    if not course:
        return ""
    session = str(state.get("session_id") or "").strip()
    started = str(state.get("started_at") or "").strip()
    # No code spans here on purpose: the chat window renders a backtick pair as a literal
    # chip boundary and this string is meant to be read out (measured 09:53Z, native window).
    detail = ", ".join(x for x in ((f"session {session}" if session else ""),
                                   (f"started {started}" if started else "")) if x)
    if language == "en-US":
        return f"Course switched to {course}" + (f" ({detail})." if detail else ".")
    zh_detail = "，".join(x for x in ((f"本次会话是 {session}" if session else ""),
                                    (f"开始于 {started}" if started else "")) if x)
    return f"已经换到 {course} 这门课" + (f"（{zh_detail}）。" if zh_detail else "。")


def _teaching_failure_wording(tool: str, diagnostic: str, language: str) -> str:
    if diagnostic == "visual_context_missing":
        if str(language).lower().startswith("zh"):
            return "我还没有这张图的模块和箭头信息，不能凭空解释。请先提供当前图中可确认的连接关系，再继续教学。"
        return "I do not have this diagram's modules and arrows yet. I need its current visible connections before I can teach it accurately."
    if str(language).lower().startswith("zh"):
        reason = ("这一轮教学请求额度已用完" if diagnostic == "agent_quota_exceeded"
                  else "教学服务这次没有返回可用结果")
        pending = {"study_quiz": "还没有生成题目", "study_answer": "还没有判定你的答案，不会给这次回答记分",
                   "study_summary": "还没有完成学习总结"}.get(tool, "还没有完成这段讲解")
        return f"{reason}，所以我{pending}。先暂停这一步，服务恢复后再继续。"
    reason = ("This learning run has reached its request limit" if diagnostic == "agent_quota_exceeded"
              else "The teaching service did not return a usable result")
    pending = {"study_quiz": "generated a question", "study_answer": "graded or scored your answer",
               "study_summary": "completed the learning summary"}.get(tool, "completed this explanation")
    return f"{reason}, so I have not {pending}. We will pause this step until the service is available."


def _teaching(*, failure_language: str = "", **fields: Any) -> str:
    """Compact, model-facing tool output: the answer plus how to deliver it."""
    fields.setdefault("relay", RELAY_NOTE)
    if fields.get("degraded"):
        fields["status"] = "unavailable"
        fields["reply"] = _teaching_failure_wording(fields.get("tool", ""), fields.get("diagnostic", ""), failure_language)
        for key in ("question", "hint", "verdict", "score", "question_id", "attempt_id"):
            fields.pop(key, None)
        fields["relay"] = ("This teaching operation failed. Say only reply exactly as written, then stop. "
                           "Do not invent an explanation, question or grade, or claim the learner's requested example is impossible.")
    for key in _SPEAKABLE_FIELDS:
        value = fields.get(key)
        if isinstance(value, str) and value:
            fields[key] = _speakable(value)
    return json.dumps(fields, ensure_ascii=False)


def _relay_for(reply: str, language: str) -> str:
    """Name the course language when it disagrees with the learner's own words.

    Seen in the native window: the course was pinned to English, the tutor answered
    in English, and the character translated that back to Chinese because the
    learner had asked in Chinese. ``RELAY_NOTE`` on its own did not hold, and the
    learner's request was "以后这门课用英文", which is supposed to outlive the
    language of any single message.
    """
    if not language:
        return RELAY_NOTE
    chinese = any("一" <= char <= "鿿" for char in str(reply or ""))
    if chinese == (language == "zh-CN"):
        return RELAY_NOTE
    wanted = "English" if language == "en-US" else "简体中文"
    return (RELAY_NOTE + f" The learner wrote in another language, but this course is set to "
            f"{wanted}, so the text above is already right - read it as written.")


# A language request inside one message ("用中文解释这段代码") changes that reply and
# nothing else, which is why it has to be separated from the remembered preference.
# Without it the course pin wins three times over - the [Teaching constraints]
# directive, the `Language:` line the prompt builder takes from cfg.language, and the
# relay note - so study_explain's promise that a language request can travel inside
# the question was a promise nothing in the code kept.
_COURSE_LEVEL_REQUEST = re.compile(
    r"以后|今后|长期|一直|总是|每次|from now on|always|every time|permanently|going forward", re.IGNORECASE)

_TURN_LANGUAGE = (
    ("zh-CN", re.compile(r"(?:用|换成|换为|改成|改为|使用|请用)\s*(?:(?:[一二两三四五六七八九十\d]+)\s*句(?:话)?\s*)?(?:中文|汉语|普通话|简体)")),
    ("en-US", re.compile(r"(?:用|换成|换为|改成|改为|使用|请用)\s*(?:(?:[一二两三四五六七八九十\d]+)\s*句(?:话)?\s*)?(?:英文|英语|美语)")),
    ("zh-CN", re.compile(r"\bin\s+(?:chinese|mandarin)\b", re.IGNORECASE)),
    ("en-US", re.compile(r"\bin\s+(?:english|en-us)\b", re.IGNORECASE)),
    ("en-US", re.compile(r"\b(?:use|using|speak)\s+english\b|\benglish\s+(?:sentences?|answers?|explanations?)\b|\benglish\s+please\b", re.IGNORECASE)),
    ("zh-CN", re.compile(r"\b(?:use|using|speak)\s+(?:chinese|mandarin)\b|\b(?:chinese|mandarin)\s+(?:sentences?|answers?|explanations?)\b", re.IGNORECASE)),
)


def _turn_language_request(*texts: Any) -> str:
    """The language asked for in this message, or "" when nothing was asked.

    A sentence that also says "以后/always" belongs to ``study_language`` with
    scope='course', not here: honouring it as a one-off would answer this turn in the
    new language while the preference itself never gets saved.
    """
    body = "\n".join(str(text or "") for text in texts)
    if not body.strip() or _COURSE_LEVEL_REQUEST.search(body):
        return ""
    for language, pattern in _TURN_LANGUAGE:
        for match in pattern.finditer(body):
            prefix = body[max(0,match.start()-40):match.start()]
            if re.search(r"(?:不要|别|不用|不|do not|don't|not)\s*(?:(?:answer|reply|respond|teach|speak|解释|讲|回答)\s*)?(?:in\s+)?$", prefix, re.I):
                continue
            return language
    return ""



# The isolated host listens here; NEKO_MAIN_BASE_URL only exists if a caller moved it.
_MAIN_BASE = (os.environ.get("NEKO_MAIN_BASE_URL") or "http://127.0.0.1:48911").rstrip("/")


async def pin_character_language(language: str) -> dict[str, Any]:
    """Hand the course language to the character itself, not just to one tool reply.

    The native window showed why the relay note alone loses: no per-character locale
    was ever stored, so the host seeded the conversation from the app-wide language
    and the character translated the English explanation back into Chinese.
    ``PUT /character/{name}/language-preference`` is the product's own control - it
    applies the locale to the live session and drops the recent text that was
    steering the old one. That route is CSRF-guarded against browser pages, so this
    first-party local client presents the token the launcher minted for this
    process instead of guessing an Origin it does not own.
    """
    token = os.environ.get("NEKO_AUTOSTART_CSRF_TOKEN", "")
    if not token:
        return {"ok": False, "reason": "launcher set no local csrf token"}
    try:
        async with httpx.AsyncClient(timeout=20.0, trust_env=False) as client:
            active = (await client.get(f"{_MAIN_BASE}/api/characters/current_catgirl")).json()
            name = str(active.get("current_catgirl") or "").strip()
            if not name:
                return {"ok": False, "reason": "no active character"}
            response = await client.put(
                f"{_MAIN_BASE}/api/characters/character/{quote(name, safe='')}/language-preference",
                json={"language": language, "_csrf_token": token},
                headers={"Origin": _MAIN_BASE},
            )
            body = response.json()
    except Exception as exc:
        return {"ok": False, "reason": f"{type(exc).__name__}: {str(exc)[:140]}"}
    if not isinstance(body, dict):
        return {"ok": False, "reason": f"HTTP {response.status_code}: {str(body)[:140]}"}
    return {
        "ok": bool(body.get("success")),
        "character": name,
        "previous": body.get("previous_language"),
        "context_reset": bool(body.get("recent_history_cleared") or body.get("session_reset")),
        "reason": str(body.get("error") or "")[:140] or None,
    }


def _screen_identifiers(text: Any) -> list[str]:
    """Dotted and camelCase names inside captured code, first-seen order, capped.

    These are exactly the forms the speech route loses: `context.watch` reaches us as
    bare `watch`, and the model then explains the English verb. Prose yields nothing
    here, so a notes window adds no noise.
    """
    found: list[str] = []
    for token in re.findall(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*",
                            str(text or "")):
        dotted = "." in token
        cased = len(token) >= 6 and bool(re.search(r"[a-z0-9][A-Z]", token))
        if (dotted or cased) and token not in found:
            found.append(token)
    return found[:8]


def _with_screen_identifiers(question: str, material: str) -> str:
    """Name the on-screen identifiers the learner referred to without saying them.

    Fires only on the ASR signature - a bare word in the question that is the tail of a
    captured identifier (`watch` while `context.watch` is on screen). A question that
    already spells the name, or a window with no such symbols, is passed through.
    """
    wanted = []
    lowered = str(question or "").lower()
    words = set(re.findall(r"[a-z]+", lowered))
    compact = "".join(lowered.split())
    for name in _screen_identifiers(material):
        if name.lower() in compact:
            continue
        tail = name.split(".")[-1].lower()
        if len(tail) >= 3 and tail in words:
            wanted.append(name)
    if not wanted:
        return question
    listed = ", ".join(f"`{name}`" for name in wanted[:4])
    return (f"{question}\n[On-screen code] The learner means these identifiers from the "
            f"captured window ({listed}), not the everyday English words - "
            "explain them as code.")


class _StudyAvatarToolsMixin:
    """LLM-facing wrappers over the tutor entries, tuned for voice pacing."""

    LANGUAGE_ALIASES = {
        "zh": "zh-CN", "zh-cn": "zh-CN", "chinese": "zh-CN", "中文": "zh-CN",
        "en": "en-US", "en-us": "en-US", "english": "en-US", "英文": "en-US", "英语": "en-US",
    }
    LANGUAGE_DIRECTIVES = {
        "zh-CN": ("请用简体中文教学，代码标识符与技术术语保持原文。"
                  "先讲重点，细节留给追问，不要一次念完整篇。"),
        "en-US": ("Teach this in English, keeping code identifiers and technical terms exact. "
                  "Use English for natural-language labels too: translate diagram labels by "
                  "meaning while retaining literal code identifiers. Quote a non-English "
                  "label only if the learner explicitly requests its original wording; "
                  "an English-only request forbids even that quotation. "
                  "Lead with the main point and leave detail for follow-up; "
                  "do not read out an essay."),
    }
    # The teaching templates emit 题目解析/解题过程/答案/举一反三 sections, which is right
    # for the web panel but unreadable aloud. The avatar path asks for one spoken turn.
    PACING_DIRECTIVE = (
        "Keep the spoken answer brief by default. Include a code block "
        "only if the learner requests code. The learner's explicit sentence limit "
        "or no-code request overrides these defaults for the whole reply. "
        "No section headings, no worked-solution template, no self-quiz at the end."
    )

    def _study_normalize_language(self, raw: Any) -> str:
        token = str(raw or "").strip().lower()
        return self.LANGUAGE_ALIASES.get(token, "")

    def _study_effective_language(self) -> str:
        """Course preference, then the learner's global default, then plugin config.

        Applying it here as well is what makes a remembered "teach this course in
        English" reach the quiz, grading and summary paths, not just explanation -
        the plugin reads ``cfg.language`` when it builds any of those prompts.
        """
        state = getattr(self, "_state", None)
        by_course = getattr(state, "teaching_language_by_course", None) or {}
        course = str(getattr(state, "study_course_id", "") or "")
        preferences = {}
        if getattr(self, "_store", None):
            from .learning_preferences import load_preferences
            preferences = load_preferences(self._store)
            if not hasattr(self, "_study_config_default_language"):
                self._study_config_default_language = str(getattr(self._cfg, "language", "") or "")
        language = (by_course.get(course) or preferences.get("language")
                    or getattr(state, "teaching_language", "")
                    or str(getattr(self._cfg, "language", "") or ""))
        if language and language != str(getattr(self._cfg, "language", "") or ""):
            self._cfg.language = language
        return language

    def _study_language_directive(self, text: str, question: str,
                                  turn_language: str = "") -> str:
        """Pin the reply language for this turn and keep the answer speakable.

        The learner's own wording is not enough on its own: the prompt builder
        forces the reply language from ``cfg.language``, so an override has to
        travel inside the material, and the pinned language has to be updated to
        match the preference they voiced earlier.

        ``turn_language`` is that earlier case in reverse - a request for this one
        message. It supplies the directive but never touches ``cfg.language``, which
        is the caller's to set and put back; writing it here would leave the
        one-off request as the stored behaviour.
        """
        body = "\n\n".join(part for part in (str(question or "").strip(),
                                             str(text or "").strip()) if part)
        if turn_language:
            language = turn_language
        else:
            language = self._study_effective_language()
            if language and language != str(getattr(self._cfg, "language", "") or ""):
                self._cfg.language = language
        directive = self.LANGUAGE_DIRECTIVES.get(language, "")
        preferences, preference_text = {}, ""
        if getattr(self, "_store", None):
            from .learning_preferences import load_preferences, preference_prompt
            preferences = load_preferences(self._store)
            preference_text = preference_prompt(preferences)
            turn_preferences = getattr(self, "_study_turn_preferences", None)
            if turn_preferences:
                preferences.update(turn_preferences)
                preference_text = preference_prompt(preferences, temporary=True)
        pacing = self.PACING_DIRECTIVE
        if preferences.get("proactive_quiz"):
            pacing = pacing.replace("no self-quiz at the end.", "a short check question is permitted if appropriate.")
        if preferences.get("length") in {"balanced", "detailed"}:
            pacing = pacing.replace("Keep the spoken answer brief by default.", "Follow the saved reply length when no length is requested.")
        constraints = " ".join(part for part in (directive, pacing, preference_text) if part)
        if constraints and body:
            return f"{body}\n\n[Teaching constraints] {constraints}"
        return body or constraints

    @llm_tool(
        name="study_preferences",
        description=("Read or change teaching preferences in the existing learning database. "
                     "Set remember=true only when the learner explicitly asks for an ongoing "
                     "preference. A request for this answer only must stay temporary and must "
                     "not change course language. Omit preferences to read current defaults."),
        parameters={"type": "object", "properties": {
            "preferences": {"type": "object", "properties": {
                "language": {"type": "string", "enum": ["zh-CN", "zh-TW", "en-US"]},
                "length": {"type": "string", "enum": ["brief", "balanced", "detailed"]},
                "explanation_style": {"type": "string", "enum": ["step_by_step", "example_first", "direct"]},
                "proactive_quiz": {"type": "boolean"}}, "additionalProperties": False},
            "remember": {"type": "boolean", "default": False}}},
        timeout=20.0,
    )
    async def study_preferences_tool(self, *, preferences=None, remember=False, **_):
        from .learning_preferences import load_preferences, update_preferences
        if preferences is None:
            return {"ok": True, "preferences": load_preferences(self._store), "persisted": False}
        try:
            async with self._lock:
                result = await asyncio.to_thread(update_preferences, self._store, preferences, remember=remember)
                if not remember:
                    self._study_turn_preferences = dict(preferences)
        except (ValueError, TypeError) as exc:
            return {"ok": False, "error": str(exc)}
        return {"ok": True, **result,
                "relay": "Confirm briefly. Temporary preferences apply to this answer only; pass them to the teaching tool's question."}

    @llm_tool(
        name="study_material",
        description=("Check which explicitly submitted picture is currently available to Study. "
                     "Call before explaining 'the submitted image', or after a picture/course "
                     "change. This is a source identity check, not an interpretation of pixels. "
                     "Use study_explain for the reliable configured vision model."),
        parameters={"type": "object", "properties": {}}, timeout=20.0,
    )
    async def study_material_tool(self, **_):
        image = str(getattr(self._state, "last_vision_image_base64", "") or "")
        return {"ok": True, "course_id": str(self._state.study_course_id or "general"),
                "material_control_submission": list(getattr(self, "_study_material_control_submission", [])),
                "picture_available": bool(image and self._cfg.llm_vision_enabled),
                "material_id": hashlib.sha256(image.encode()).hexdigest()[:20] if image else "",
                "vision_enabled": bool(self._cfg.llm_vision_enabled),
                "next": "Call study_explain with the learner's question and omit text to inspect this picture. "
                        "If unavailable, ask for a clear PNG/JPEG submission in Study; do not guess."}

    @llm_tool(
        name="study_point",
        description=("Point within the controlled learning surface only; the learner selects and scrolls. "
                     "For displayed source use kind='source', the original source_line and symbol "
                     "(and source_file if ambiguous). The tool resolves the actual original file line "
                     "from current filtered evidence; no CSS or opaque material ID is needed. "
                     "For diagrams inspect kind='status' first, copy a returned selector/material_id, "
                     "or provide an evidence-based normalized image rectangle. Never invent CSS "
                     "like .code-line:nth-child or desktop coordinates. This only highlights."),
        parameters={"type": "object", "properties": {
            "kind": {"type": "string", "enum": ["source", "selector", "rect", "clear", "status"], "default": "status"},
            "material_id": {"type": "string"}, "selector": {"type": "string"},
            "source_line": {"type": "integer", "minimum": 1}, "source_file": {"type": "string"},
            "symbol": {"type": "string"},
            "language": {"type": "string", "enum": ["zh-CN", "en-US"], "description": "Language of this confirmation only; not remembered."},
            "x": {"type": "number"}, "y": {"type": "number"},
            "width": {"type": "number"}, "height": {"type": "number"},
            "label": {"type": "string"}}}, timeout=10.0,
    )
    async def study_point_tool(self, *, kind="status", material_id="", **kwargs):
        base = os.environ.get("NEKO_LEARNING_SURFACE_URL", "")
        token = os.environ.get("NEKO_LEARNING_SURFACE_TOKEN", "")
        if not base or not token:
            return {"ok": False, "error": "learning_surface_not_open", "next": "Open Start-Daily-Tutor with its learning surface."}
        # The launcher owns this loopback endpoint and per-process token.
        if not re.fullmatch(r"http://127\.0\.0\.1:\d+", base):
            return {"ok": False, "error": "invalid_learning_surface"}
        if "source_line" in kwargs and kind in {"status", "selector"}:
            kind = "source"
        if kind == "source" and (type(kwargs.get("source_line")) is not int or kwargs["source_line"] < 1):
            return {"ok": False, "error": "invalid_source_line", "next": "Use an original file line number from the shown source evidence."}
        try:
            async with httpx.AsyncClient(timeout=5, trust_env=False) as client:
                headers = {"X-Learning-Surface-Token": token}
                if kind == "status":
                    response = await client.get(base + "/api/state", headers=headers)
                else:
                    if kind == "source":
                        snapshot = await client.get(base + "/api/state", headers=headers)
                        snapshot.raise_for_status()
                        state = snapshot.json()
                        active = state.get("active_material_id")
                        material = next((m for m in state.get("materials", []) if m.get("id") == active), None)
                        if not material or material.get("source") != "filtered_codegraph_evidence":
                            return {"ok": False, "error": "source_evidence_not_selected", "next": "Ask the learner to select the source evidence returned by study_code."}
                        if material_id and material_id != active:
                            return {"ok": False, "error": "stale_material", "next": "The learner changed material; inspect current source before pointing."}
                        file_hint = str(kwargs.get("source_file") or "").replace("\\", "/")
                        symbol = re.sub(r"\s+", "", str(kwargs.get("symbol") or "")).casefold()
                        candidates = [target for target in material.get("targets_for_pointing", [])
                                      if target.get("source_line") == kwargs["source_line"]
                                      and (not file_hint or file_hint in {target.get("source_file"), str(target.get("source_file", "")).rsplit("/", 1)[-1]})
                                      and (not symbol or symbol in re.sub(r"\s+", "", str(target.get("label") or "")).casefold())]
                        if len(candidates) != 1:
                            return {"ok": False, "error": "source_line_not_unique_or_not_shown", "next": "The locator could not resolve a unique target. This does not mean the function is absent. Verify the shown file/line/symbol; do not guess CSS or claim absent source."}
                        material_id, kind = active, "selector"
                        kwargs["selector"] = candidates[0]["selector"]
                        kwargs["label"] = f'{candidates[0]["source_file"]}:{kwargs["source_line"]}'
                    elif not material_id:
                        return {"ok": False, "error": "missing_material_identity", "next": "For source lines use kind='source' with source_line and symbol. For diagrams first inspect kind='status' and copy its exact selector and material_id; never invent CSS."}
                    command = {"kind": kind, "material_id": material_id,
                               **{key: kwargs[key] for key in ("selector", "x", "y", "width", "height", "label") if key in kwargs}}
                    response = await client.post(base + "/api/guidance", json=command, headers=headers)
                payload = response.json()
                if response.is_success:
                    active = payload.get("active_material_id")
                    payload = {"active_material_id": active,
                               **({"material": next((item for item in payload.get("materials", []) if item.get("id") == active), None)} if kind == "status" else {}),
                               "command": payload.get("command"), "revision": payload.get("revision")}
                result = {"ok": response.is_success, **payload,
                        "proof": "locator metadata only; guidance is queued until the open surface renders it, and is not vision evidence"}
                if response.is_success and kind != "status":
                    language = kwargs.get("language") or getattr(self, "_study_effective_language", lambda: "zh-CN")()
                    line = kwargs.get("source_line")
                    if kind == "clear":
                        result["say_this"] = "Highlight cleared." if str(language).startswith("en") else "已清除高亮。"
                    elif type(line) is int:
                        result["say_this"] = f"Requested a highlight on source line {line}." if str(language).startswith("en") else f"已请求高亮当前源码第{line}行。"
                    else:
                        result["say_this"] = "Requested a highlight on that area." if str(language).startswith("en") else "已请求高亮这个区域。"
                    result["relay"] = "Say only say_this in its language, then stop. You did not move an editor cursor, scroll, edit source, or verify that it rendered; the learner scrolls."
                return result
        except (httpx.HTTPError, ValueError):
            return {"ok": False, "error": "learning_surface_unavailable", "next": "Reopen the learning surface and inspect its current material; do not reuse old coordinates."}

    @llm_tool(
        name="study_scope",
        description=(
            "Report what this tutor is actually allowed to see, read from the running state "
            "rather than from impression: the single authorized project directory, the commit "
            "it is pinned to, how many files were indexed inside it versus refused outside it, "
            "what the read-only filter drops before anything is sent, how screen reading is "
            "gated, and how to revoke or change the grant. Call this whenever the learner asks "
            "what you can read, which files are in scope, whether you can see the whole "
            "computer, or how to change the authorization. Never answer those from memory."
        ),
        parameters={"type": "object", "properties": {}, "required": []},
        timeout=20.0,
    )
    async def study_scope_tool(self, **_):
        """One read-only snapshot of the boundaries, taken from the files that enforce them.

        Every field here is a value the gates themselves already write. This tool deliberately
        opens no directory and widens nothing: on 2026-10-12 the character told the learner "我
        能看到你整个项目的代码", which is not what the authorization file says, and the learner
        had no way to tell a guess from a fact.
        """
        authorized = self._code_authorization()
        counts: dict[str, Any] = {}
        try:
            with open(str(self.data_path("code_project.json")), encoding="utf-8") as handle:
                stored = json.load(handle)
            if isinstance(stored, dict):
                counts = {key: stored[key] for key in
                          ("indexed_at", "indexed_files_inside", "indexed_files_outside", "cli")
                          if key in stored}
        except (OSError, ValueError):
            counts = {}
        if not authorized:
            return {
                "ok": True, "code_access": "none",
                "scope": "No project is authorized, so no file on this machine can be read. "
                         "Say that plainly; do not describe files.",
                "screen": ("Screen reading happens only when the learner names an open window "
                           "title; there is no background or proactive capture."),
                "how_to_grant": ("Start with --code-root <项目目录>, or accept the folder picker "
                                 "the double-click entry opens."),
                "relay": ("State this in one short sentence in the teaching language, then ask "
                          "the learner to pick one file or screen they want understood - do not "
                          "continue describing capabilities."),
            }
        return {
            "ok": True,
            "code_access": "one authorized project",
            "project": {"name": authorized["name"], "root": authorized["root"],
                        "paths_may_be_read_from": authorized["prefix"],
                        "pinned_commit": authorized["commit"], **counts},
            "limits": (
                "Only paths inside that root are ever read; anything outside is dropped before "
                "it reaches the model (dropped_outside_root), a denied path is dropped "
                "(dropped_denied_path), and secrets are redacted (redacted) - those counters are "
                "written per question into the study log. The index is read-only: no file is "
                "opened for writing and no command other than the indexer runs against it."
            ),
            "screen": ("Screen reading happens only when the learner names an open window title "
                       "(target_window); there is no background or proactive capture, and a "
                       "missing window is refused rather than guessed at."),
            "revoke": ("Delete code_project.json under this plugin's data directory to end code "
                       "access at once, or pass a different --code-root to change project."),
            "relay": ("Answer the learner's boundary question in one short sentence, then bring "
                      "them into the material: pick one concrete thread from the authorized "
                      "project (for a Flutter app, e.g. how one module feeds another) and offer "
                      "to explain it with real functions. Do not keep describing yourself."),
        }

    @llm_tool(
        name="study_language",
        description=(
            "Set the language used for teaching. scope='course' remembers it for the "
            "current course across future sessions ('以后这门课用英文'); scope='default' "
            "applies it to every course; scope='clear' forgets a remembered choice so the "
            "plugin default returns. A one-off request in the same sentence as a question "
            "needs no call here - pass it through study_explain instead."
        ),
        parameters={
            "type": "object",
            "properties": {
                "language": {"type": "string",
                             "description": "zh-CN / en-US, or 'chinese' / 'english'."},
                "scope": {"type": "string", "enum": ["course", "default", "clear"],
                          "default": "course"},
            },
            "required": ["language"],
        },
        timeout=30.0,
    )
    async def study_language_tool(self, *, language: str = "", scope: str = "course", **_):
        resolved = self._study_normalize_language(language)
        if not resolved:
            return {"ok": False,
                    "error": f"unsupported teaching language {language!r}",
                    "supported": sorted(set(self.LANGUAGE_ALIASES.values()))}
        scope = str(scope or "course").strip().lower()
        if scope not in {"clear", "default", "course"}:
            return {"ok": False, "error": "scope must be course, default or clear"}
        async with self._lock:
            if scope == "clear":
                self._state.teaching_language = ""
                course = str(self._state.study_course_id or "")
                self._state.teaching_language_by_course.pop(course, None)
                if getattr(self, "_store", None):
                    preferences = self._store.get_raw("learning_preferences") or {}
                    if isinstance(preferences, dict):
                        preferences.pop("language", None)
                        self._store.set_raw("learning_preferences", preferences)
                self._cfg.language = getattr(self, "_study_config_default_language", "zh-CN")
            elif scope == "default":
                self._state.teaching_language = resolved
                if getattr(self, "_store", None):
                    from .learning_preferences import update_preferences
                    update_preferences(self._store, {"language": resolved}, remember=True)
            else:
                course = str(self._state.study_course_id or "general")
                self._state.teaching_language_by_course[course] = resolved
            self._cfg.language = self._study_effective_language()
            await self._persist_state()
        # A course-level preference is the only one that outlives this message, so it
        # is the only one promoted to the character. A temporary "in English" request
        # must not silently change how the character speaks outside the lesson.
        pinned = await pin_character_language(resolved) if scope == "course" else {
            "ok": False,
            "reason": ("cleared the course preference only; the character's own "
                       "language stays as the learner set it" if scope == "clear"
                       else "not a course-level preference"),
        }
        return {
            "ok": True,
            "reply_language": self._cfg.language,
            "scope": scope,
            "character_language": pinned,
            "course_id": str(self._state.study_course_id or ""),
            "remembered": (f"{scope}:{self._cfg.language}" if scope != "clear"
                           else "cleared"),
            "relay": "Confirm in one short sentence, in the language just set.",
        }

    @llm_tool(
        name="study_session",
        description=(
            "Report or change the study session. Call with action='status' to see "
            "the active course, session, mode and recent mistakes; action='start' "
            "with a course_id to begin a new session for that course (this also "
            "restores that course's earlier history); action='set_course' to switch "
            "courses without resetting progress. Use this before teaching when the "
            "learner names a subject, and whenever they ask about their own progress."
        ),
        parameters={
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["status", "start", "set_course"],
                           "default": "status"},
                "course_id": {"type": "string", "default": "",
                              "description": "Stable course identifier, e.g. flutter-provider."},
            },
        },
        timeout=60.0,
    )
    async def study_session_tool(self, *, action: str = "status", course_id: str = "", **_):
        action = str(action or "status").strip().lower()
        if action == "start":
            raw = await self.study_start_session(course_id=course_id)
        elif action == "set_course":
            raw = await self.study_set_course(course_id=course_id)
        else:
            raw = await self.study_status()
        payload = _envelope(raw)
        if not payload.get("ok", True):
            return payload
        keep = ("course_id", "session_id", "active_mode", "mode", "started_at",
                "wrong_answers", "recent_answer_records", "weak_topics", "last_question",
                "last_answer_evaluation")
        state = {key: payload[key] for key in keep if key in payload} or payload
        active_course = str(self._state.study_course_id or "")
        state["course_id"] = active_course
        state["session_id"] = str(self._state.study_session_id or "")
        state["material_control_submission"] = list(getattr(self, "_study_material_control_submission", []))
        if active_course:
            learning = await asyncio.to_thread(self._course_learning_state, active_course)
            state["recent_answer_records"] = learning["recent_answers"]
            state["weak_topics"] = learning["weak_topics"]
        language = self._study_effective_language()
        # Only an ack has nothing to teach, so only an ack gets pre-worded: a status read
        # also carries course_id, and calling it "Course switched to ..." would be false.
        wording = _ack_wording(language, state) if action in {"start", "set_course"} else ""
        if wording:
            return {"ok": True, **state, "say_this": wording, "relay": RELAY_NOTE}
        return state | {"relay": _relay_for_data(language)}

    @llm_tool(
        name="study_read_window",
        description=(
            "Read code or notes from ONE learning window the learner explicitly names. "
            "Requires the window's exact title plus at least one text marker that must be "
            "visible inside it; anything else is refused and nothing is captured. Call "
            "this before explaining on-screen material. Costs no model request, and the "
            "captured text stays local until an explain/quiz call uses it."
        ),
        parameters={
            "type": "object",
            "properties": {
                "window_title": {"type": "string",
                                 "description": "Exact full title of the authorized window."},
                "expected_markers": {
                    "type": "array", "items": {"type": "string"},
                    "description": "Strings that must be readable in that window, proving the capture.",
                },
            },
            "required": ["window_title", "expected_markers"],
        },
        timeout=120.0,
    )
    async def study_read_window_tool(self, *, window_title: str = "",
                                     expected_markers: Any = None, **_):
        markers = expected_markers if isinstance(expected_markers, list) else []
        raw = await self.study_ocr_snapshot(
            capture_mode="target_window",
            window_title=str(window_title or ""),
            expected_markers=[str(item) for item in markers],
            allow_fullscreen_fallback=False,
        )
        payload = _envelope(raw)
        if not payload.get("ok", True):
            reason = str(payload.get("error", "capture refused"))
            log = getattr(self, "logger", None)
            if log is not None:
                # Nothing else on this machine records the string the model actually
                # asked for, and on the speech route that string is the whole diagnosis.
                log.info(f"read_window refused title={str(window_title)!r} reason={reason[:140]}")
            # Each refusal has one doable fix, and the learner can only do it if the
            # character names it: "not_found"/"title_mismatch" wants the exact title bar
            # text, "content_mismatch" wants a marker that is really on screen,
            # "not_renderable" is the one case where the window has to be brought in front, and
            # "not_responding" means that window's own thread is too busy to paint at all.
            hint = ("Ask the learner for the window's exact title bar text."
                    if "not_found" in reason or "title_mismatch" in reason else
                    "Ask the learner to name something visible in that window."
                    if "content_mismatch" in reason else
                    "Ask the learner to click that window and wait until it stops being busy, then retry it."
                    if "not_responding" in reason else
                    "Say that window did not answer in time; ask the learner to click it once, then retry it."
                    if "stalled" in reason else
                    "Ask the learner to click that window so it is in front, then retry it."
                    if "not_renderable" in reason else
                    "Tell the learner which window or marker failed; do not retry another window.")
            if "not_found" in reason and self._code_authorization():
                # Measured 2026-10-12 11:40:51: the learner named a file that is in the
                # authorized project, the window they meant was not open, and the turn died on
                # "not_found". The code they asked about was reachable the whole time.
                hint += (" Say that window is not on screen right now - do not imply the content "
                         "does not exist. If what the learner wants is in the authorized project, "
                         "answer it with study_code; reaching outside that project is not an "
                         "option, and neither is asking for a wider grant to get one.")
            return {"ok": False, "error": reason, "next": hint}
        text = _first_text(payload, "text", "ocr_text", "raw_text")
        return {"ok": True, "characters": len(text), "excerpt": text[:1200],
                "captured_window": payload.get("window_title", window_title),
                "relay": _relay_for_data(self._study_effective_language()),
                "next": "Now call study_explain; the captured text is used automatically."}

    @llm_tool(
        name="study_explain",
        description=(
            "Explain a concept, a piece of code, or the last window the learner had you "
            "read. Leave text empty to explain the material already captured by "
            "study_read_window. Put the learner's own words in question, including "
            "follow-ups such as 'why?', 'simpler', 'give me a counter-example', or a "
            "language request like 'in English' - that request changes this answer only, "
            "and the optional language argument makes that one-answer choice explicit. "
            "so do not save it with study_language unless the learner wants it to stick. "
            "When the learner asks about the current Study picture, omit text: the "
            "tool must inspect the latest submitted image, not a remembered summary "
            "or your guessed module names and arrows. Put literal learner-supplied "
            "code/notes in text only when those are the requested source. "
            "For a correction/recheck of the current picture set material_source=current_picture; "
            "for supplied code/notes use literal_text. Auto only resumes an unchanged, "
            "previously bound picture explanation; if the correction target is unclear, ask. "
            "This tool has no live Realtime screen feed; OCR words alone do not "
            "establish arrows. This is the main teaching tool."
        ),
        parameters={
            "type": "object",
            "properties": {
                "question": {"type": "string", "default": "",
                             "description": "What the learner wants explained, in their words."},
                "text": {"type": "string", "default": "",
                         "description": "Literal source code or notes requested by the learner. Omit for the current Study picture/diagram or captured window. Never fill with an earlier picture summary or guessed arrows."},
                "material_source": {"type":"string", "enum":["auto","current_picture","literal_text"], "default":"auto",
                                    "description":"Use current_picture to recheck submitted pixels, ignoring an old summary in text. Use literal_text only for learner-supplied code/notes; never override a learner who rejects pictures."},
                "language": {"type":"string", "enum":["zh-CN","en-US"],
                             "description":"Explicit reply language for this explanation only. Set it for a one-time language switch; does not save or pin a course preference."},
            },
        },
        timeout=150.0,
    )
    async def study_explain_tool(self, *, question: str = "", text: str = "", language: str = "",
                                 material_source: str = "auto", **_):
        if not isinstance(language, str) or language not in {"", "zh-CN", "en-US"}:
            return {"ok":False,"error":"unsupported_one_turn_language"}
        if not isinstance(material_source, str) or material_source not in {"auto","current_picture","literal_text"}:
            return {"ok":False,"error":"unsupported_material_source"}
        if material_source == "literal_text" and not str(text or "").strip():
            return {"ok":False,"error":"literal_source_missing"}
        from .study_materials import material_context, material_output_target, material_context_current
        output_target = material_output_target(self, _)
        current_picture = bool(
            re.search(r"架构图|流程图|关系图|图片|截图|图中|图上|这张图|这个图|箭头|\b(?:diagram|picture|image|screenshot|arrows?)\b", question, re.I)
            and re.search(r"这|图中|图上|当前|刚|屏幕|this|that|current|screen|latest|submitted|shown", question, re.I))
        literal_source_request = bool(str(text or "").strip() and re.search(
            r"代码|源码|函数|变量|标识符|笔记|这段文字|\b(?:source\s+(?:code|line)|code|function|variable|identifier|notes?)\b", question, re.I))
        explicit_picture_reference = bool(re.search(
            r"(?:当前|刚换|刚交|最新|这张|这个)[^。!?？\n]{0,20}(?:图片|截图|图|箭头)|图中|图上|\b(?:this|that|current|latest|submitted|shown)\s+(?:study\s+)?(?:diagram|picture|image|screenshot)\b", question, re.I))
        rejected_picture = bool(re.search(
            r"(?:不要|别|不用)(?:再)?(?:查看|看|使用|用)?\s*(?:当前|刚换|刚交|最新|这张|这个|任何|旧)?(?:的)?(?:图片|截图|图)|"
            r"\b(?:do not|don't)\s+(?:look at|use|inspect|read)\s+(?:(?:the|current|this|that|old|any|latest|submitted|shown|study)\s+){0,4}(?:image|picture|diagram|screenshot)\b", question, re.I))
        if literal_source_request and (rejected_picture or not explicit_picture_reference):
            current_picture = False
        if rejected_picture:
            current_picture = False
        if material_source == "current_picture":
            if rejected_picture:
                return {"ok":False,"error":"material_source_conflict"}
            current_picture = True
        elif material_source == "literal_text":
            if explicit_picture_reference and not rejected_picture:
                return {"ok":False,"error":"material_source_conflict"}
            current_picture = False
        correction = bool(re.search(
            r"你(?:读|看|讲|说|理解|解释)(?:错|反)|请(?:重新|再)(?:检查|核对)|"
            r"\b(?:you (?:misread|got .* wrong)|that(?:'s| is) wrong|recheck|misread)\b", question, re.I))
        recheck_context = None
        recheck_binding = None
        recheck_row_id = None
        def ambiguous_correction():
            wanted = language or _turn_language_request(question, "") or self._study_effective_language()
            reply = ("Please specify the current picture or the source code to recheck; I cannot confirm the correction target."
                     if wanted == "en-US" else "请明确要核对当前图片还是某段代码；我无法确认这次纠正的对象。")
            return {"ok":False,"error":"correction_source_ambiguous","reply":reply,
                    "relay":RELAY_NOTE + " Ask only this clarification; do not invent a correction."}
        if (material_source == "auto" and correction and not current_picture
                and not literal_source_request and not rejected_picture):
            async with self._lock:
                binding = (getattr(self, "_study_material_output_targets", {}) or {}).get(output_target, {})
                expected = dict(binding.get("context") or {})
                bound_current = bool(binding.get("boot_id") == getattr(self, "_study_material_boot_id", None)
                    and "material_identity" in expected and material_context_current(self, expected))
            rows = []
            if bound_current:
                # One existing row validates the previous source; no new memory store.
                rows = await asyncio.to_thread(self._store.list_interactions, 1, session_id=expected["session_id"])
            async with self._lock:
                if (bound_current and rows and rows[0]["kind"] == "concept_explain"
                        and (rows[0].get("metadata") or {}).get("material_context") == expected
                        and (getattr(self, "_study_material_output_targets", {}) or {}).get(output_target) is binding
                        and material_context_current(self, expected)):
                    current_picture = True
                    recheck_context = expected
                    recheck_binding = binding
                    recheck_row_id = rows[0]["id"]
                else:
                    return ambiguous_correction()
        if current_picture:
            # A native model can pass an OLD picture summary as `text` even
            # while asking to verify the latest image. The learner's current
            # picture request must keep vision and image identity binding.
            # Literal code/notes questions remain independent of saved images.
            text = ""
        # Discarded picture summaries cannot supply this turn's language request.
        requested = language or _turn_language_request(question, text) or str((getattr(self, "_study_turn_preferences", None) or {}).get("language") or "")
        cached_image = str(getattr(getattr(self, "_state", None), "last_vision_image_base64", "") or "").strip()
        has_image_context = bool(getattr(getattr(self, "_cfg", None), "llm_vision_enabled", False) and cached_image)
        if current_picture and not has_image_context:
            # OCR material does not establish the current diagram's relations.
            # Never ask the text model to invent a missing visual source.
            return json.loads(_teaching(
                tool="study_explain", degraded=True, diagnostic="visual_context_missing",
                failure_language=requested or self._study_effective_language()))
        # A proxy may issue overlapping explanations. Serialize their temporary
        # cfg overrides so one cannot restore another's temporary language.
        include_material = not str(text or "").strip() and not rejected_picture
        observed = recheck_context or material_context(self, include_material=include_material)
        await self._ensure_active_study_session()
        async with self._lock:
            # Snapshot before waiting behind another explanation. Never adopt a
            # different course/image when this queued request finally starts.
            context = material_context(self, include_material=include_material)
            # Only an initially absent session may be initialized here. A
            # replaced or expired existing session requires a fresh question.
            if any(context.get(key) != value for key, value in observed.items()
                   if key != "session_id" or value):
                return {"ok":False,"error":"course_context_changed","reply":"课程已切换或材料已更新，请使用当前材料重新提问。"}
            image = str(getattr(self._state, "last_vision_image_base64", "") or "") if has_image_context and include_material else ""
            captured_text = str(getattr(self._state, "last_ocr_text", "") or "")
        lock = getattr(self, "_study_explanation_language_lock", None)
        if lock is None:
            lock = self._study_explanation_language_lock = asyncio.Lock()
        async with lock:
            if recheck_context:
                # Recheck after SQL and language-lock waits, coordinating with short
                # history commits under the existing state lock, never across model IO.
                async with self._lock:
                    rows = await asyncio.to_thread(self._store.list_interactions, 1,
                                                   session_id=recheck_context["session_id"])
                    if ((getattr(self, "_study_material_output_targets", {}) or {}).get(output_target) is not recheck_binding
                            or not material_context_current(self, recheck_context)
                            or not rows or rows[0]["id"] != recheck_row_id
                            or rows[0]["kind"] != "concept_explain"
                            or (rows[0].get("metadata") or {}).get("material_context") != recheck_context):
                        return ambiguous_correction()
            return await self._study_explain_for_turn(question=question, text=text, requested=requested,
                                                     context=context, image=image, captured_text=captured_text,
                                                     output_target=output_target)

    async def _study_explain_for_turn(self, *, question: str, text: str, requested: str,
                                    context: dict, image: str, captured_text: str, output_target: str = ""):
        # previous first: the directive below writes the remembered course preference
        # into cfg.language, and that is the value a one-off request has to go back to.
        previous = str(getattr(self._cfg, "language", "") or "")
        try:
            body = self._study_language_directive(
                str(text or ""),
                _with_screen_identifiers(str(question or ""),
                                         str(text or "")
                                         or captured_text),
                requested)
            # Only cfg.language reaches the prompt builder's `Language:` line, so the
            # override has to be applied there for the call and undone after it.
            if requested:
                self._cfg.language = requested
            payload = _envelope(await self.study_explain_text(text=body, vision_image_base64=image,
                                                            _material_context=context))
            reply = _first_text(payload, "reply", "summary", "answer", "explanation")
            if not reply:
                return payload
            result = json.loads(_teaching(
                tool="study_explain",
                reply=reply,
                mode=payload.get("active_mode") or payload.get("mode") or "",
                degraded=bool(payload.get("degraded")),
                diagnostic=payload.get("diagnostic", ""),
                failure_language=requested or self._study_effective_language(),
                relay=_relay_for(reply, requested or self._study_effective_language()),
            ))
            if payload.get("ok", True) and not payload.get("degraded"):
                from .study_materials import bind_material_output, material_context_current
                async with self._lock:
                    if not material_context_current(self, context):
                        return {"ok": False, "error": "course_context_changed", "reply": "材料已更新，请使用当前材料重新提问。"}
                    result["_study_material_binding"] = bind_material_output(self, context, output_target)
            return result
        finally:
            if requested:
                self._cfg.language = previous


    def _study_changed_native_material_result(self):
        return {"ok": False, "code": "course_context_changed", "error": "course_context_changed",
                "reply": "课程、会话或题目已切换，请确认当前材料后重新提问。"}

    async def _study_native_material_snapshot(self, *, include_material=False):
        from .study_materials import material_context
        observed = material_context(self, include_material=include_material)
        await self._ensure_active_study_session()
        async with self._lock:
            current = material_context(self, include_material=include_material)
            if any(current.get(key) != value for key, value in observed.items()
                   if key != "session_id" or value):
                return None
            return {"context": current,
                    "image": str(getattr(self._state, "last_vision_image_base64", "") or "") if include_material else "",
                    "text": str(getattr(self._state, "last_ocr_text", "") or "") if include_material else ""}

    async def _study_bind_native_teaching_result(self, payload, result, context, target, *, question_identity=None):
        from .study_materials import material_context_current, bind_material_output
        async with self._lock:
            if not material_context_current(self, context):
                return self._study_changed_native_material_result()
            if question_identity is not None:
                current = self._state.current_question
                if any(str(current.get(key) or "") != value for key, value in question_identity.items()):
                    return self._study_changed_native_material_result()
            if payload.get("ok", True) and not payload.get("degraded") and not result.get("degraded"):
                result["_study_material_binding"] = bind_material_output(self, context, target)
        return result

    @llm_tool(
        name="study_quiz",
        description=(
            "Give the learner a practice question. With topic set it targets that topic; "
            "with topic empty it uses the current submitted Study picture when available; "
            "otherwise it can target their weakest tracked topic in the current course. "
            "Ask the question and then stop and wait for their answer."
        ),
        parameters={
            "type": "object",
            "properties": {
                "topic": {"type": "string", "default": ""},
                "target_weak": {"type": "boolean", "default": True},
            },
        },
        timeout=150.0,
    )
    async def study_quiz_tool(self, *, topic: str = "", target_weak: bool = True, **_):
        self._study_effective_language()
        topic = str(topic or "").strip()
        from .study_materials import material_output_target
        target = material_output_target(self, _)
        picture_quiz = bool(not topic and self._cfg.llm_vision_enabled
                            and getattr(self._state, "last_vision_image_base64", ""))
        snapshot = await self._study_native_material_snapshot(include_material=picture_quiz)
        if snapshot is None:
            return self._study_changed_native_material_result()
        context = snapshot["context"]
        if picture_quiz:
            raw = await self.study_generate_question(text=snapshot["text"], vision_image_base64=snapshot["image"],
                                                     _material_context=context)
        elif topic or not target_weak:
            raw = await self.study_generate_question(
                text=self._study_language_directive("", topic) if topic else "",
                topic=topic, _material_context=context)
        else:
            raw = await self.study_generate_targeted_question(_material_context=context)
        payload = _envelope(raw)
        question = _first_text(payload, "question", "prompt", "reply")
        if not question:
            return payload
        result = json.loads(_teaching(
            tool="study_quiz",
            question=question,
            hint=_first_text(payload, "hint"),
            topic=_first_text(payload, "topic"),
            question_id=payload.get("question_id", ""),
            attempt_id=payload.get("attempt_id", ""),
            degraded=bool(payload.get("degraded")),
            diagnostic=payload.get("diagnostic", ""),
            failure_language=self._study_effective_language(),
            relay=_relay_for(question, self._study_effective_language()),
        ))
        identity = {key: str(payload.get(key) or "") for key in ("question_id", "attempt_id")}
        return await self._study_bind_native_teaching_result(payload, result, context, target, question_identity=identity)

    @llm_tool(
        name="study_answer",
        description=(
            "Grade the learner's answer to the question currently on the table and record "
            "it in their learning history. Returns the verdict, score and the correction to "
            "give them. Call it as soon as they answer a quiz."
        ),
        parameters={
            "type": "object",
            "properties": {"answer": {"type": "string"}},
            "required": ["answer"],
        },
        timeout=150.0,
    )
    async def study_answer_tool(self, *, answer: str = "", **_):
        self._study_effective_language()
        from .study_materials import material_output_target, material_context_current
        target = material_output_target(self, _)
        snapshot = await self._study_native_material_snapshot()
        if snapshot is None:
            return self._study_changed_native_material_result()
        context = snapshot["context"]
        # The persisted current-course question survives restart; an avatar-only cache does not.
        async with self._lock:
            if not material_context_current(self, context):
                return self._study_changed_native_material_result()
            held = dict(self._state.current_question)
        origin = (held.get("internal_private_payload") or {}).get("source_material_context")
        if isinstance(origin, dict) and origin.get("course_id") and origin["course_id"] != context["course_id"]:
            return self._study_changed_native_material_result()
        # A generated question carries an identity, and the entry refuses to grade
        # it without both ids echoed back - so the tool has to hold on to them.
        kwargs: dict[str, Any] = {"answer": str(answer or ""), "_material_context": context}
        if held.get("question_id"):
            kwargs["question_id"] = held["question_id"]
        if held.get("attempt_id"):
            kwargs["attempt_id"] = held["attempt_id"]
        payload = _envelope(await self.study_evaluate_answer(**kwargs))
        feedback = _first_text(payload, "feedback", "reply", "summary", "explanation")
        if not feedback:
            return payload
        result = json.loads(_teaching(
            tool="study_answer",
            reply=feedback,
            verdict=payload.get("verdict", ""),
            score=payload.get("score", ""),
            error_type=payload.get("error_type", ""),
            degraded=bool(payload.get("degraded")),
            diagnostic=payload.get("diagnostic", ""),
            failure_language=self._study_effective_language(),
            relay=_relay_for(feedback, self._study_effective_language()),
        ))
        identity = {key: str(held.get(key) or "") for key in ("question_id", "attempt_id")}
        return await self._study_bind_native_teaching_result(payload, result, context, target, question_identity=identity)

    @llm_tool(
        name="study_summary",
        description=(
            "Summarize the current study session: what was covered, which answers were "
            "wrong, and what to practise next. Call when the learner wraps up or asks how "
            "they are doing. The summary is saved to their learning record."
        ),
        parameters={
            "type": "object",
            "properties": {"focus": {"type": "string", "default": ""}},
        },
        timeout=150.0,
    )
    async def study_summary_tool(self, *, focus: str = "", **_):
        self._study_effective_language()
        from .study_materials import material_output_target
        target = material_output_target(self, _)
        snapshot = await self._study_native_material_snapshot()
        if snapshot is None:
            return self._study_changed_native_material_result()
        context = snapshot["context"]
        payload = _envelope(await self.study_summarize_session(focus=str(focus or ""), _material_context=context,
                                                             _narration_target_lanlan=target))
        summary = _first_text(payload, "summary", "reply", "text")
        if not summary:
            return payload
        result = json.loads(_teaching(tool="study_summary", reply=summary,
                                    degraded=bool(payload.get("degraded")),
                                    diagnostic=payload.get("diagnostic", ""),
                                    failure_language=self._study_effective_language(),
                                    relay=_relay_for(summary, self._study_effective_language())))
        return await self._study_bind_native_teaching_result(payload, result, context, target)
