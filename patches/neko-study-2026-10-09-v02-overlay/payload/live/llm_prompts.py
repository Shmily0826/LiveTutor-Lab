from __future__ import annotations

import json
from typing import Any

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
        "input_text",
        "language",
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
    if operation == LLM_OPERATION_ANSWER_EVALUATE:
        required = {key: safe_context[key] for key in
                    ("question", "answer", "expected_answer") if key in safe_context}
        if count_tokens(_json_dump(required)) > limit:
            raise ValueError("evaluation question and answer exceed prompt budget")
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
        "\n\nRecent study context (this session's memory; use it to resolve "
        "references to earlier material):\n" + _json_dump(memory)
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
    if mode:
        prompt = STUDY_STRUCTURED_MODE_PREFIX_TEMPLATE.format(mode=normalize_mode(mode), prompt=prompt)
    return [
        {"role": "system", "content": system_prompt},
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
                response_guidance=STUDY_CONCEPT_RESPONSE_MODE_GUIDANCE[response_mode],
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


_SUMMARY_HISTORY_LIMIT = 12
_SUMMARY_HISTORY_INPUT_CHARS = 200
_SUMMARY_HISTORY_OUTPUT_CHARS = 320


def _summary_interaction_rows(rows: Any) -> list[dict[str, str]]:
    if not isinstance(rows, list):
        return []
    compact: list[dict[str, str]] = []
    for item in [row for row in rows if isinstance(row, dict)][-_SUMMARY_HISTORY_LIMIT:]:
        input_text = _bounded_text(
            item.get("input_text"), _SUMMARY_HISTORY_INPUT_CHARS
        )
        output_text = _bounded_text(
            item.get("output_text"), _SUMMARY_HISTORY_OUTPUT_CHARS
        )
        if not input_text and not output_text:
            continue
        compact.append(
            {
                "kind": str(item.get("kind") or ""),
                "input": input_text,
                "output": output_text,
            }
        )
    return compact


def _summarize_context(context: dict[str, Any]) -> dict[str, Any]:
    """Project the summary context onto this session's interactions.

    The raw ``history`` window spans earlier sessions, so it is replaced by the
    (much smaller) ``session_history`` derived by the caller. Without that
    projection the 2000-token budget used to be spent on unrelated rows and the
    model reported the session as "limited".
    """
    compact = dict(context)
    session_rows = _summary_interaction_rows(compact.pop("session_history", None))
    history_rows = _summary_interaction_rows(compact.pop("history", None))
    if session_rows:
        compact["session_history"] = session_rows
    elif history_rows:
        # No session boundary available (fresh state): fall back to the window.
        compact["history"] = history_rows
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
