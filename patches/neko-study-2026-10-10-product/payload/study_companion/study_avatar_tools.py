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
    r"以后|今后|长期|一直|总是|每次|from now on|always|every time|permanently|going forward")

_TURN_LANGUAGE = (
    ("zh-CN", re.compile(r"(?:用|换成|换为|改成|改为|使用|请用)\s*(?:中文|汉语|普通话|简体)")),
    ("en-US", re.compile(r"(?:用|换成|换为|改成|改为|使用|请用)\s*(?:英文|英语|美语)")),
    ("zh-CN", re.compile(r"\bin\s+(?:chinese|mandarin)\b", re.IGNORECASE)),
    ("en-US", re.compile(r"\bin\s+(?:english|en-us)\b", re.IGNORECASE)),
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
        if pattern.search(body):
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
        language = (by_course.get(course) or getattr(state, "teaching_language", "")
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
        constraints = " ".join(part for part in (directive, self.PACING_DIRECTIVE) if part)
        if constraints and body:
            return f"{body}\n\n[Teaching constraints] {constraints}"
        return body or constraints

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
        async with self._lock:
            if scope == "clear":
                self._state.teaching_language = ""
                course = str(self._state.study_course_id or "")
                self._state.teaching_language_by_course.pop(course, None)
            elif scope == "default":
                self._state.teaching_language = resolved
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
            "so do not save it with study_language unless the learner wants it to stick. "
            "This is the main teaching tool."
        ),
        parameters={
            "type": "object",
            "properties": {
                "question": {"type": "string", "default": "",
                             "description": "What the learner wants explained, in their words."},
                "text": {"type": "string", "default": "",
                         "description": "Source code or notes to explain; omit to reuse captured material."},
            },
        },
        timeout=150.0,
    )
    async def study_explain_tool(self, *, question: str = "", text: str = "", **_):
        requested = _turn_language_request(question, text)
        # previous first: the directive below writes the remembered course preference
        # into cfg.language, and that is the value a one-off request has to go back to.
        previous = str(getattr(self._cfg, "language", "") or "")
        try:
            body = self._study_language_directive(
                str(text or ""),
                _with_screen_identifiers(str(question or ""),
                                         str(text or "")
                                         or str(getattr(self._state, "last_ocr_text", "") or "")),
                requested)
            # Only cfg.language reaches the prompt builder's `Language:` line, so the
            # override has to be applied there for the call and undone after it.
            if requested:
                self._cfg.language = requested
            payload = _envelope(await self.study_explain_text(text=body))
            reply = _first_text(payload, "reply", "summary", "answer", "explanation")
            if not reply:
                return payload
            return json.loads(_teaching(
                tool="study_explain",
                reply=reply,
                mode=payload.get("active_mode") or payload.get("mode") or "",
                degraded=bool(payload.get("degraded")),
                diagnostic=payload.get("diagnostic", ""),
                failure_language=requested or self._study_effective_language(),
                relay=_relay_for(reply, requested or self._study_effective_language()),
            ))
        finally:
            if requested:
                self._cfg.language = previous


    @llm_tool(
        name="study_quiz",
        description=(
            "Give the learner a practice question. With topic set it targets that topic; "
            "with topic empty it targets their weakest tracked topic in the current course. "
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
        if topic or not target_weak:
            raw = await self.study_generate_question(
                text=self._study_language_directive("", topic) if topic else "",
                topic=topic)
        else:
            raw = await self.study_generate_targeted_question()
        payload = _envelope(raw)
        question = _first_text(payload, "question", "prompt", "reply")
        if not question:
            return payload
        return json.loads(_teaching(
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
        # The persisted current-course question survives restart; an avatar-only cache does not.
        held = dict(self._state.current_question)
        # A generated question carries an identity, and the entry refuses to grade
        # it without both ids echoed back - so the tool has to hold on to them.
        kwargs: dict[str, str] = {"answer": str(answer or "")}
        if held.get("question_id"):
            kwargs["question_id"] = held["question_id"]
        if held.get("attempt_id"):
            kwargs["attempt_id"] = held["attempt_id"]
        payload = _envelope(await self.study_evaluate_answer(**kwargs))
        feedback = _first_text(payload, "feedback", "reply", "summary", "explanation")
        if not feedback:
            return payload
        return json.loads(_teaching(
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
        payload = _envelope(await self.study_summarize_session(focus=str(focus or "")))
        summary = _first_text(payload, "summary", "reply", "text")
        if not summary:
            return payload
        return json.loads(_teaching(tool="study_summary", reply=summary,
                                    degraded=bool(payload.get("degraded")),
                                    diagnostic=payload.get("diagnostic", ""),
                                    failure_language=self._study_effective_language(),
                                    relay=_relay_for(summary, self._study_effective_language())))
