from __future__ import annotations

import json
from typing import Any
from .learning_preferences import preference_prompt

from .prompt_templates import (
    STUDY_ANSWER_EVALUATE_EXAMPLE,
    STUDY_ANSWER_EVALUATE_REQUIREMENTS,
    STUDY_ANSWER_EVALUATE_SYSTEM_PROMPT,
    STUDY_CONCEPT_EXPLAIN_SYSTEM_WITH_MODE_TEMPLATE,
    STUDY_CONCEPT_RESPONSE_MODE_SYSTEM_PROMPT,
    STUDY_CONCEPT_RESPONSE_MODE_USER_TEMPLATE,
    STUDY_CONCEPT_RESPONSE_MODE_GUIDANCE,
    STUDY_KNOWLEDGE_TRACK_EXAMPLE,
    STUDY_KNOWLEDGE_TRACK_REQUIREMENTS,
    STUDY_KNOWLEDGE_TRACK_SYSTEM_PROMPT,
    STUDY_MODE_SYSTEM_GUIDANCE,
    STUDY_PROMPT_CONTEXT_MAX_TOKENS,
    STUDY_QUESTION_GENERATE_EXAMPLE,
    STUDY_QUESTION_GENERATE_REQUIREMENTS,
    STUDY_QUESTION_GENERATE_SYSTEM_PROMPT,
    STUDY_STRUCTURED_MODE_PREFIX_TEMPLATE,
    STUDY_STRUCTURED_LANGUAGE_TEMPLATE,
    STUDY_STRUCTURED_USER_TEMPLATE,
    STUDY_SUMMARIZE_SESSION_EXAMPLE,
    STUDY_SUMMARIZE_SESSION_REQUIREMENTS,
    STUDY_SUMMARIZE_SESSION_SYSTEM_PROMPT,
)
from utils.tokenize import count_tokens, truncate_to_tokens

from .constants import (
    LLM_OPERATION_ANSWER_EVALUATE,
    LLM_OPERATION_CONCEPT_EXPLAIN,
    LLM_OPERATION_KNOWLEDGE_TRACK,
    LLM_OPERATION_QUESTION_GENERATE,
    LLM_OPERATION_SUMMARIZE_SESSION,
    MODE_COMPANION,
    SUPPORTED_LLM_OPERATIONS,
)
from .mode_manager import normalize_mode


_PROMPT_CONTEXT_ALLOWED_FIELDS = frozenset(
    {
        "operation",
        "course_id",
        "previous_course_history",
        "previous_answer_records",
        "course_learning_state",
        "input_text",
        "language",
        "learning_preferences",
        "learning_preferences_scope",
        "mode",
        "source",
        "source_text",
        "text",
        "question",
        "answer",
        "expected_answer",
        "question_payload",
        "current_question",
        "public_current_question",
        "last_answer_evaluation",
        "session_summary_seed",
        "screen_classification",
        "recent_screen_classifications",
        "recent_learning_events",
        "last_ocr_text",
        "last_ocr_at",
        "history",
        "session_history",
        "knowledge_summary",
        "knowledge_session_summary",
        "knowledge_guidance",
        "knowledge_question_params",
        "material_grounded_question",
        "topic_hint",
        "topic",
        "selected_topic_id",
        "selected_topic_name",
        "selection_reason",
        "selection_reason_payload",
        "targeted_question",
        "result",
        "reply",
        "focus",
        "screen_type",
        "weak_points",
        "next_steps",
    }
)
_PROMPT_PRIVATE_FIELDS = frozenset(
    {
        "material_context",
        "source_material_context",
        "_material_context",
        "_study_material_binding",
        "_narration_target_lanlan",
        "_session_summary_seed",
        "_study_narration_origin",
        "study_narration_origin",
        "vision_image_base64",
        "last_vision_image_base64",
        "image_base64",
        "deadline",
        "deadline_monotonic",
        "correlation_id",
        "request_id",
        "api_key",
        "base_url",
        "internal_private_payload",
        "current_question_private",
    }
)


def _sanitize_nested_prompt_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _sanitize_nested_prompt_value(item)
            for key, item in value.items()
            if str(key) not in _PROMPT_PRIVATE_FIELDS
        }
    if isinstance(value, list):
        return [_sanitize_nested_prompt_value(item) for item in value]
    return value


def _prompt_context(context: dict[str, Any]) -> dict[str, Any]:
    return {
        str(key): _sanitize_nested_prompt_value(value)
        for key, value in context.items()
        if str(key) in _PROMPT_CONTEXT_ALLOWED_FIELDS
    }


def _json_dump(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


def _compact_prompt_value(
    value: Any,
    *,
    list_limit: int,
    string_limit: int,
    dict_key_limit: int = 0,
    max_depth: int = 10,
) -> Any:
    if max_depth <= 0:
        return "...[max depth reached]"
    if isinstance(value, str):
        if len(value) <= string_limit:
            return value
        omitted = len(value) - string_limit
        return f"{value[:string_limit]}\n...[truncated {omitted} chars]"
    if isinstance(value, list):
        items = value[-list_limit:] if len(value) > list_limit else value
        return [
            _compact_prompt_value(
                item,
                list_limit=list_limit,
                string_limit=string_limit,
                dict_key_limit=dict_key_limit,
                max_depth=max_depth - 1,
            )
            for item in items
        ]
    if isinstance(value, dict):
        items = list(value.items())
        if dict_key_limit > 0 and len(items) > dict_key_limit:
            omitted = len(items) - dict_key_limit
            items = items[:dict_key_limit]
            truncated = {
                str(key): _compact_prompt_value(
                    item,
                    list_limit=list_limit,
                    string_limit=string_limit,
                    dict_key_limit=dict_key_limit,
                    max_depth=max_depth - 1,
                )
                for key, item in items
            }
            truncated["__truncated_keys__"] = f"...{omitted} keys omitted"
            return truncated
        return {
            str(key): _compact_prompt_value(
                item,
                list_limit=list_limit,
                string_limit=string_limit,
                dict_key_limit=dict_key_limit,
                max_depth=max_depth - 1,
            )
            for key, item in items
        }
    return value


def _context_json_for_prompt(operation: str, context: dict[str, Any]) -> str:
    limit = STUDY_PROMPT_CONTEXT_MAX_TOKENS.get(operation, 4000)
    safe_context = _prompt_context(context)
    # A grade must never be computed from a reference after dropping the answer.
    required = {}
    if operation == LLM_OPERATION_QUESTION_GENERATE:
        # Current material and the learner's format request must survive long
        # course history; otherwise the model repeats an earlier question.
        required = {"source_text": safe_context.get("source_text")
                    or safe_context.get("text") or safe_context.get("input_text") or ""}
        if count_tokens(_json_dump(required)) > limit:
            raise ValueError("question source exceeds prompt budget")
        safe_context["source_text"] = required["source_text"]
        safe_context.pop("input_text", None)
        safe_context.pop("text", None)
    elif operation == LLM_OPERATION_ANSWER_EVALUATE:
        required = {key: safe_context[key] for key in
                    ("question", "answer", "expected_answer") if key in safe_context}
        if count_tokens(_json_dump(required)) > limit:
            raise ValueError("evaluation question and answer exceed prompt budget")
    elif operation == LLM_OPERATION_SUMMARIZE_SESSION and safe_context.get("session_history"):
        required = {"session_history": safe_context["session_history"]}
        # Keep every retained session interaction and numeric grade. Shrink prose
        # before shrinking history, which can otherwise discard the final quiz.
        for string_limit in (240, 160, 80):
            if count_tokens(_json_dump(required)) <= limit - 400:
                break
            required = _compact_prompt_value(required, list_limit=_SUMMARY_HISTORY_LIMIT,
                                             string_limit=string_limit)
    auxiliary = {key: value for key, value in safe_context.items() if key not in required}
    raw = _json_dump(safe_context)
    if count_tokens(raw) <= limit:
        return raw
    for list_limit, string_limit, dict_key_limit in (
        (16, 1000, 64),
        (8, 500, 32),
        (4, 240, 16),
    ):
        compact = _compact_prompt_value(
            auxiliary,
            list_limit=list_limit,
            string_limit=string_limit,
            dict_key_limit=dict_key_limit,
        )
        if isinstance(compact, dict):
            compact = {"_prompt_truncated": True, **required, **compact}
        rendered = _json_dump(compact)
        if count_tokens(rendered) <= limit:
            return rendered
    excerpt = truncate_to_tokens(_json_dump(auxiliary), max(0, limit - count_tokens(_json_dump(required)) - 100))
    fallback = {
        "_prompt_truncated": True,
        **required,
        "context_excerpt": f"{excerpt}\n...[truncated {len(raw) - len(excerpt)} chars]",
    }
    while count_tokens(_json_dump(fallback)) > limit and excerpt:
        excerpt = excerpt[:-1]
        fallback["context_excerpt"] = f"{excerpt}\n...[truncated {len(raw) - len(excerpt)} chars]"
    return _json_dump(
        fallback
    )


def _mode_guidance(mode: str) -> str:
    selected_mode = normalize_mode(mode)
    return STUDY_MODE_SYSTEM_GUIDANCE.get(selected_mode, STUDY_MODE_SYSTEM_GUIDANCE[MODE_COMPANION])


# Bounds for the session-memory block injected into concept_explain. They are kept
# deliberately small: the block travels with every explanation, so it must never
# crowd out the study text itself.
_RECENT_CONTEXT_OCR_CHARS = 1200
_RECENT_CONTEXT_HISTORY_ITEMS = 4
_RECENT_CONTEXT_HISTORY_INPUT_CHARS = 240
_RECENT_CONTEXT_HISTORY_OUTPUT_CHARS = 560
_RECENT_CONTEXT_EVENT_ITEMS = 6
_RECENT_CONTEXT_TEXT_CHARS = 300


def _bounded_text(value: Any, limit: int) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return f"{text[:limit].rstrip()}..."


def _recent_history_items(history: Any) -> list[dict[str, str]]:
    if not isinstance(history, list):
        return []
    rows = [item for item in history if isinstance(item, dict)]
    if rows and all(isinstance(item.get("id"), int) for item in rows):
        rows.sort(key=lambda item: item["id"])
    return [
        {
            "kind": str(item.get("kind") or ""),
            "input": _bounded_text(
                item.get("input_text"), _RECENT_CONTEXT_HISTORY_INPUT_CHARS
            ),
            "output": _bounded_text(
                item.get("output_text"), _RECENT_CONTEXT_HISTORY_OUTPUT_CHARS
            ),
        }
        for item in rows[-_RECENT_CONTEXT_HISTORY_ITEMS:]
        if str(item.get("input_text") or "").strip()
        or str(item.get("output_text") or "").strip()
    ]


def _recent_learning_events(events: Any) -> list[dict[str, str]]:
    if not isinstance(events, list):
        return []
    rows = [item for item in events if isinstance(item, dict)]
    compact: list[dict[str, str]] = []
    for item in rows[-_RECENT_CONTEXT_EVENT_ITEMS:]:
        entry = {
            "operation": str(item.get("operation") or item.get("kind") or ""),
            "topic": _bounded_text(item.get("topic"), 80),
            "screen_type": str(item.get("screen_type") or ""),
        }
        compact.append({key: value for key, value in entry.items() if value})
    return compact


def build_concept_recent_context(context: dict[str, Any] | None) -> str:
    """Render the session-memory block for concept_explain prompts.

    Only fields needed to resolve ``that example`` / ``the previous step`` style
    references are included, and every string is bounded. Private fields never
    reach this function's output because only named public fields are read.
    """
    context = context if isinstance(context, dict) else {}
    memory: dict[str, Any] = {}
    history = _recent_history_items(context.get("history"))
    if history:
        memory["recent_interactions"] = history
    previous = _recent_history_items(context.get("previous_course_history"))
    if previous:
        memory["previous_sessions_same_course"] = previous
    learning = context.get("course_learning_state")
    if isinstance(learning, dict):
        memory["course_id"] = str(learning.get("course_id") or "")
        memory["weak_topics"] = learning.get("weak_topics") or []
        memory["previous_answers"] = [
            {"question": _bounded_text((row.get("question") or {}).get("question"), 300),
             "user_answer": _bounded_text(row.get("user_answer"), 200),
             "evaluation": {key: (row.get("eval_result") or {}).get(key)
                            for key in ("verdict", "score", "feedback", "misconceptions")}}
            for row in (learning.get("recent_answers") or [])[-5:]
        ]
    ocr_text = _bounded_text(context.get("last_ocr_text"), _RECENT_CONTEXT_OCR_CHARS)
    if ocr_text:
        memory["last_captured_material"] = ocr_text
        ocr_at = str(context.get("last_ocr_at") or "").strip()
        if ocr_at:
            memory["last_captured_at"] = ocr_at
    question = context.get("current_question")
    if isinstance(question, dict) and str(question.get("question") or "").strip():
        memory["current_practice_question"] = {
            "question": _bounded_text(
                question.get("question"), _RECENT_CONTEXT_TEXT_CHARS
            ),
            "topic": str(question.get("topic") or question.get("selected_topic_id") or ""),
        }
    evaluation = context.get("last_answer_evaluation")
    if isinstance(evaluation, dict) and evaluation:
        memory["last_answer_evaluation"] = {
            key: evaluation.get(key)
            for key in ("verdict", "score", "error_type")
            if evaluation.get(key) not in (None, "")
        }
        feedback = _bounded_text(
            evaluation.get("feedback"), _RECENT_CONTEXT_TEXT_CHARS
        )
        if feedback:
            memory["last_answer_evaluation"]["feedback"] = feedback
    events = _recent_learning_events(context.get("recent_learning_events"))
    if events:
        memory["recent_learning_events"] = events
    if not memory:
        return ""
    return (
        "\n\nStudy context for the selected course (current session and explicitly "
        "labelled previous sessions; use actual recorded answers for mistakes and "
        "resolve references to earlier material):\n" + _json_dump(memory)
    )


def _build_structured_messages(
    *,
    operation: str,
    system_prompt: str,
    requirements: str,
    context: dict[str, Any],
    example: dict[str, Any],
    mode: str = MODE_COMPANION,
) -> list[dict[str, str]]:
    prompt = STUDY_STRUCTURED_USER_TEMPLATE.format(
        requirements=requirements,
        example_json=_json_dump(example),
        context_json=_context_json_for_prompt(operation, context),
    )
    language = str(context.get("language") or "").strip()
    if language:
        prompt = STUDY_STRUCTURED_LANGUAGE_TEMPLATE.format(language=language, prompt=prompt)
    if mode:
        prompt = STUDY_STRUCTURED_MODE_PREFIX_TEMPLATE.format(mode=normalize_mode(mode), prompt=prompt)
    return [
        {"role": "system", "content": system_prompt + preference_prompt(context.get("learning_preferences"), temporary=context.get("learning_preferences_scope") == "turn")},
        {"role": "user", "content": prompt},
    ]


def build_concept_explain_messages(
    *,
    text: str,
    language: str,
    mode: str = MODE_COMPANION,
    context: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    context = context if isinstance(context, dict) else {}
    source = str(context.get("source") or "manual").strip() or "manual"
    selected_mode = normalize_mode(context.get("mode") or mode)
    response_mode = str(context.get("study_response_mode") or "unknown").strip().lower()
    if response_mode not in STUDY_CONCEPT_RESPONSE_MODE_GUIDANCE:
        response_mode = "unknown"
    response_guidance = STUDY_CONCEPT_RESPONSE_MODE_GUIDANCE[response_mode]
    # Avatar requests already supply a spoken contract; a second full-solution
    # contract reintroduced headings and a quiz in actual course-history replies.
    if "\n\n[Teaching constraints]" in text and "No section headings" in text:
        response_guidance = (
            "Answer the learner's current request in brief spoken prose, following "
            "the supplied Teaching constraints and explicit length/no-quiz/no-code "
            "requests. Do not add response-mode headings or a transfer exercise. "
            "For a problem, give the essential reasoning and answer within those limits."
        )
    guidance = context.get("knowledge_guidance")
    guidance_block = ""
    if isinstance(guidance, dict) and guidance:
        prompt_guidance = (
            guidance.get("model_context")
            if isinstance(guidance.get("model_context"), dict)
            else guidance
        )
        guidance_block = (
            "\n\nKnowledge graph guidance:\n"
            f"{_context_json_for_prompt(LLM_OPERATION_CONCEPT_EXPLAIN, {'knowledge_guidance': prompt_guidance})}"
        )
    return [
        {
            "role": "system",
            "content": STUDY_CONCEPT_EXPLAIN_SYSTEM_WITH_MODE_TEMPLATE.format(
                system_prompt=STUDY_CONCEPT_RESPONSE_MODE_SYSTEM_PROMPT,
                mode_guidance=_mode_guidance(selected_mode),
            ) + preference_prompt(context.get("learning_preferences"), temporary=context.get("learning_preferences_scope") == "turn") + (
                "\nWhen a learner challenges an earlier claim, re-evaluate it from the "
                "supplied evidence. If it was wrong, say plainly what was wrong and "
                "replace it; do not invent a justification to defend it. Treat OCR as "
                "a lossy observation, not authoritative source code. Missing or garbled "
                "punctuation is uncertainty: do not assert a syntax error or recommend "
                "an edit unless the evidence establishes it. Check scope, nesting, and "
                "API lifecycle restrictions before giving code advice. Follow requested "
                "brevity and explain only what the current follow-up asks. Explicit "
                "learner length and scope requests take precedence over the default "
                "response-mode section format; a brief clarification or correction "
                "does not need a full lesson or problem-solving template. Evaluate the "
                "learner's specific correction instead of agreeing just because it is "
                "confidently stated. For reversed conditions (hit/miss, enabled/disabled, "
                "true/false), state the supported polarity and explicitly reject the "
                "opposite. Say 'you are right' only when that specific claim is supported."
            ) + (
                "\nKeep a diagram label's qualifiers scoped to its named operation or "
                "branch. A shared arrow or slash-separated label is not evidence that "
                "every qualifier applies to every operation. Separate visible facts "
                "from interpretations; an unshown cache, trigger, protocol or ordering "
                "rule remains unknown until the relevant source evidence establishes it."
                if context.get("vision_enabled") else ""
            ),
        },
        {
            "role": "user",
            "content": STUDY_CONCEPT_RESPONSE_MODE_USER_TEMPLATE.format(
                language=language,
                source=source,
                mode=selected_mode,
                response_mode=response_mode,
                content_type=str(context.get("study_semantic_content_type") or "unknown"),
                intent=str(context.get("study_semantic_intent") or "unknown"),
                response_guidance=response_guidance,
                text=f"{text.strip()}{guidance_block}",
                recent_context=build_concept_recent_context(context),
            ),
        },
    ]


def build_question_generate_messages(
    *,
    text: str,
    language: str,
    mode: str = MODE_COMPANION,
    context: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    context = dict(context or {})
    context.setdefault("text", text)
    context.setdefault("language", language)
    context.setdefault("mode", normalize_mode(mode))
    return _build_structured_messages(
        operation=LLM_OPERATION_QUESTION_GENERATE,
        system_prompt=STUDY_QUESTION_GENERATE_SYSTEM_PROMPT,
        requirements=STUDY_QUESTION_GENERATE_REQUIREMENTS,
        context=context,
        example=STUDY_QUESTION_GENERATE_EXAMPLE,
        mode=mode,
    )


def build_answer_evaluate_messages(
    *,
    question: str,
    answer: str,
    expected_answer: str,
    language: str,
    mode: str = MODE_COMPANION,
    context: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    context = dict(context or {})
    context.setdefault("question", question)
    context.setdefault("answer", answer)
    context.setdefault("expected_answer", expected_answer)
    context.setdefault("language", language)
    context.setdefault("mode", normalize_mode(mode))
    return _build_structured_messages(
        operation=LLM_OPERATION_ANSWER_EVALUATE,
        system_prompt=STUDY_ANSWER_EVALUATE_SYSTEM_PROMPT,
        requirements=STUDY_ANSWER_EVALUATE_REQUIREMENTS,
        context=context,
        example=STUDY_ANSWER_EVALUATE_EXAMPLE,
        mode=mode,
    )


def build_knowledge_track_messages(
    *,
    language: str,
    mode: str = MODE_COMPANION,
    context: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    context = dict(context or {})
    context.setdefault("language", language)
    context.setdefault("mode", normalize_mode(mode))
    return _build_structured_messages(
        operation=LLM_OPERATION_KNOWLEDGE_TRACK,
        system_prompt=STUDY_KNOWLEDGE_TRACK_SYSTEM_PROMPT,
        requirements=STUDY_KNOWLEDGE_TRACK_REQUIREMENTS,
        context=context,
        example=STUDY_KNOWLEDGE_TRACK_EXAMPLE,
        mode=mode,
    )


_SUMMARY_HISTORY_LIMIT = 40
_SUMMARY_PREVIOUS_COURSE_LIMIT = 8
_SUMMARY_PREVIOUS_ANSWER_LIMIT = 3
_SUMMARY_HISTORY_INPUT_CHARS = 200
_SUMMARY_HISTORY_OUTPUT_CHARS = 320


def _summary_interaction_rows(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        return []
    compact: list[dict[str, Any]] = []
    ordered = [row for row in rows if isinstance(row, dict)]
    if ordered and all(isinstance(item.get("id"), int) for item in ordered):
        ordered.sort(key=lambda item: item["id"])
    for item in ordered[-_SUMMARY_HISTORY_LIMIT:]:
        input_text = _bounded_text(
            item.get("input_text"), _SUMMARY_HISTORY_INPUT_CHARS
        )
        output_text = _bounded_text(
            item.get("output_text"), _SUMMARY_HISTORY_OUTPUT_CHARS
        )
        if not input_text and not output_text:
            continue
        if item.get("kind") == LLM_OPERATION_QUESTION_GENERATE and not output_text:
            continue
        record = {
                "id": item.get("id"),
                "kind": str(item.get("kind") or ""),
                "output": output_text,
                "output_role": "tutor",
            }
        # Quiz input is source material or a generation request, not evidence
        # that the learner explained it. Keep the actual tutor question instead.
        if item.get("kind") != LLM_OPERATION_QUESTION_GENERATE:
            record["input"] = input_text
            record["input_role"] = (
                "learner_answer"
                if item.get("kind") == LLM_OPERATION_ANSWER_EVALUATE
                else "request_or_material"
            )
        metadata = item.get("metadata") or {}
        result = (metadata.get("payload") or {}) if isinstance(metadata, dict) else {}
        if isinstance(result, dict) and item.get("kind") == LLM_OPERATION_ANSWER_EVALUATE:
            record["evaluation"] = {
                key: _compact_prompt_value(result[key], list_limit=3, string_limit=160)
                for key in ("verdict", "score", "error_type", "feedback", "missing_points", "misconceptions", "next_action")
                if key in result
            }
            record["question"] = _bounded_text(metadata.get("question"), 240)
        compact.append(record)
    return compact


def _summary_previous_answers(context: dict[str, Any]) -> list[dict[str, Any]]:
    """Project already course-filtered QA, keeping persistent IDs local only."""
    course_id = context.get("course_id")
    session_id = context.get("session_id")
    learning_state = context.get("course_learning_state")
    if (
        not isinstance(course_id, str) or not course_id.strip()
        or not isinstance(session_id, str) or not session_id.strip()
        or session_id in {"default", "unknown"}
        or not isinstance(learning_state, dict)
        or learning_state.get("course_id") != course_id
        or not isinstance(learning_state.get("recent_answers"), list)
    ):
        return []
    answers: list[dict[str, Any]] = []
    seen_records: set[int] = set()
    seen_attempts: set[tuple[str, str]] = set()
    # Store returns ascending QA IDs; the caller supplies its latest eight.
    for row in reversed(learning_state["recent_answers"][-8:]):
        if not isinstance(row, dict):
            continue
        record_id = row.get("id")
        previous_session = row.get("session_id")
        question = row.get("question")
        evaluation = row.get("eval_result")
        if (
            not isinstance(record_id, int) or isinstance(record_id, bool) or record_id <= 0
            or not isinstance(previous_session, str) or not previous_session.strip()
            or previous_session in {session_id, "default", "unknown"}
            or not isinstance(question, dict)
            or (question.get("course_family") and question.get("course_family") != course_id)
            or not isinstance(question.get("question"), str) or not question["question"].strip()
            or not isinstance(row.get("user_answer"), str)
            or not isinstance(evaluation, dict)
            or not isinstance(evaluation.get("verdict"), str)
            or evaluation.get("verdict") not in {"correct", "partial", "wrong", "dont_know"}
            or not isinstance(evaluation.get("score"), (int, float))
            or isinstance(evaluation.get("score"), bool)
            or not 0 <= evaluation["score"] <= 100
            or any(key in evaluation and not isinstance(evaluation[key], str)
                   for key in ("feedback", "next_action"))
        ):
            continue
        question_id = question.get("question_id")
        attempt_id = question.get("attempt_id")
        if any(value is not None and not isinstance(value, str) for value in (question_id, attempt_id)):
            continue
        attempt_key = (question_id, attempt_id) if question_id and attempt_id else None
        if record_id in seen_records or (attempt_key is not None and attempt_key in seen_attempts):
            continue
        seen_records.add(record_id)
        if attempt_key is not None:
            seen_attempts.add(attempt_key)
        answers.append({
            "source_scope": "previous_session_same_course",
            "question": _bounded_text(question["question"], 240),
            "user_answer": _bounded_text(row["user_answer"], _SUMMARY_HISTORY_INPUT_CHARS),
            "input_role": "learner_answer",
            "evaluation_role": "tutor",
            "evaluation": {
                key: _compact_prompt_value(evaluation[key], list_limit=3, string_limit=160)
                for key in ("verdict", "score", "feedback", "next_action") if key in evaluation
            },
        })
        if len(answers) == _SUMMARY_PREVIOUS_ANSWER_LIMIT:
            break
    return list(reversed(answers))


def _summarize_context(context: dict[str, Any]) -> dict[str, Any]:
    """Separate current interactions from bounded prior same-course evidence.

    The raw ``history`` window spans earlier sessions, so it is replaced by the
    (much smaller) ``session_history`` derived by the caller. Without that
    projection the 2000-token budget used to be spent on unrelated rows and the
    model reported the session as "limited".
    """
    compact = {key: context[key] for key in
               ("operation", "input_text", "language", "learning_preferences", "learning_preferences_scope", "mode", "course_id", "focus", "session_summary_seed")
               if key in context}
    raw_session_rows = context.get("session_history")
    session_rows = _summary_interaction_rows(raw_session_rows)
    history_rows = _summary_interaction_rows(context.get("history"))
    # Filtering material-only attempts must not revive another session's rows.
    if session_rows or (isinstance(raw_session_rows, list) and raw_session_rows):
        compact["session_history"] = session_rows
    elif history_rows:
        # No session boundary available (fresh state): fall back to the window.
        compact["history"] = history_rows
    # The caller already filters these rows by course and excludes this session.
    # Keep them separate so a restart can resume without claiming new progress.
    raw_previous_rows = context.get("previous_course_history")
    if isinstance(raw_previous_rows, list):
        previous_rows = _summary_interaction_rows([
            row for row in raw_previous_rows[:_SUMMARY_PREVIOUS_COURSE_LIMIT]
            if isinstance(row, dict) and row.get("kind") in SUPPORTED_LLM_OPERATIONS
        ])
        if previous_rows:
            for row in previous_rows:
                row["source_scope"] = "previous_session_same_course"
            compact["previous_course_history"] = previous_rows
    previous_answers = _summary_previous_answers(context)
    if previous_answers:
        compact["previous_answer_records"] = previous_answers
    return compact


def build_summarize_session_messages(
    *,
    language: str,
    mode: str = MODE_COMPANION,
    context: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    context = _summarize_context(dict(context or {}))
    context.setdefault("language", language)
    context.setdefault("mode", normalize_mode(mode))
    return _build_structured_messages(
        operation=LLM_OPERATION_SUMMARIZE_SESSION,
        system_prompt=STUDY_SUMMARIZE_SESSION_SYSTEM_PROMPT,
        requirements=STUDY_SUMMARIZE_SESSION_REQUIREMENTS,
        context=context,
        example=STUDY_SUMMARIZE_SESSION_EXAMPLE,
        mode=mode,
    )


def build_operation_messages(operation: str, context: dict[str, Any]) -> list[dict[str, str]]:
    if operation not in SUPPORTED_LLM_OPERATIONS:
        raise ValueError(f"unsupported study llm operation: {operation}")
    normalized_operation = operation
    if normalized_operation == LLM_OPERATION_QUESTION_GENERATE:
        return build_question_generate_messages(
            text=str(context.get("text") or context.get("source_text") or ""),
            language=str(context.get("language") or "zh-CN"),
            mode=str(context.get("mode") or MODE_COMPANION),
            context=context,
        )
    if normalized_operation == LLM_OPERATION_ANSWER_EVALUATE:
        return build_answer_evaluate_messages(
            question=str(context.get("question") or ""),
            answer=str(context.get("answer") or ""),
            expected_answer=str(context.get("expected_answer") or ""),
            language=str(context.get("language") or "zh-CN"),
            mode=str(context.get("mode") or MODE_COMPANION),
            context=context,
        )
    if normalized_operation == LLM_OPERATION_KNOWLEDGE_TRACK:
        return build_knowledge_track_messages(
            language=str(context.get("language") or "zh-CN"),
            mode=str(context.get("mode") or MODE_COMPANION),
            context=context,
        )
    if normalized_operation == LLM_OPERATION_SUMMARIZE_SESSION:
        return build_summarize_session_messages(
            language=str(context.get("language") or "zh-CN"),
            mode=str(context.get("mode") or MODE_COMPANION),
            context=context,
        )
    return build_concept_explain_messages(
        text=str(context.get("text") or context.get("source_text") or ""),
        language=str(context.get("language") or "zh-CN"),
        mode=str(context.get("mode") or MODE_COMPANION),
        context=context,
    )


__all__ = [
    "build_answer_evaluate_messages",
    "build_concept_explain_messages",
    "build_concept_recent_context",
    "build_knowledge_track_messages",
    "build_operation_messages",
    "build_question_generate_messages",
    "build_summarize_session_messages",
]
