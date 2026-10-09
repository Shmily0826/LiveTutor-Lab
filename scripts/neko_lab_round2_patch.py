"""Rebuild the pre-round-2 images of the files this round changed, then emit a diff.

No pristine copy of prompt_templates.py / entry_tutor_*.py / the context-support
module exists in the repo (the 2026-10-08 backup only snapshots the files that
round touched), so the pre-image is reconstructed by inverting this round's edits.
Every replacement is asserted, so a mismatch fails loudly instead of producing a
quietly wrong patch.
"""
from __future__ import annotations

import difflib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / "benchmarks/raw/neko-app/resources/bin/plugin/plugins/study_companion"
OUT = ROOT / "patches/neko-study-2026-10-09-round2"
PRE = ROOT / "patches/neko-study-2026-10-09-round2/_pre"

# (filename, [(current_text, original_text), ...])
INVERSES: dict[str, list[tuple[str, str]]] = {}

INVERSES["prompt_templates.py"] = [
    (
        '''STUDY_CONCEPT_RESPONSE_MODE_SYSTEM_PROMPT = (
    "You are a concise study tutor. Explain the concept clearly, "
    "identify relevant prerequisite ideas, and follow the backend-provided "
    "response contract exactly. Do not infer a different response mode from "
    "keywords or from knowledge-graph labels. "
    "When the learner's message refers to earlier work in the session - for "
    "example \\"that example\\", \\"example 2\\", \\"the step before\\", \\"why is "
    "there a 1/2\\" - resolve the reference from the Recent study context block "
    "and answer that specific item directly. Do not ask the learner to paste "
    "material that is already present in the Recent study context, and do not "
    "fall back to a generic textbook derivation when the referenced item is "
    "visible there. "
    "If the Recent study context shows that the current material is a "
    "different subject from an earlier one, answer only about the subject the "
    "learner is now asking about. "
    "Do not invent source material beyond the supplied text."
)''',
        '''STUDY_CONCEPT_RESPONSE_MODE_SYSTEM_PROMPT = (
    "You are a concise study tutor. Explain the concept clearly, "
    "identify relevant prerequisite ideas, and follow the backend-provided "
    "response contract exactly. Do not infer a different response mode from "
    "keywords or from knowledge-graph labels. "
    "Do not invent source material beyond the supplied text."
)''',
    ),
    (
        '"Study text:\\n{text}{recent_context}"',
        '"Study text:\\n{text}"',
    ),
    (
        '''    "knowledge_track": 2500,
    # A session summary is only as good as the interactions it can see; the
    # session rows are compacted before rendering (see llm_prompts).
    "summarize_session": 6000,''',
        '''    "knowledge_track": 2500,
    "summarize_session": 2000,''',
    ),
    (
        '''    "13. Subject grounding, in this priority order: (a) when context.selected_topic_name "
    "or context.selected_topic_id is present, that adaptive practice topic is the "
    "target; (b) otherwise, when context.material_grounded_question is true, the "
    "subject taught by the supplied study material (context.source_text / context.text, "
    "refined by context.topic_hint) is the target.\\n"
    "14. context.knowledge_question_params, context.knowledge_guidance, context.history "
    "and context.last_ocr_text may inform difficulty, phrasing and distractor choice, "
    "but they must never move the question off the subject chosen in rule 13. When "
    "rule 13 names a topic, do not take the subject from the recent conversation or "
    "from the last captured material.\\n"
    "15. Output must match this JSON structure:\\n"''',
        '''    "13. Keep the output grounded in context.screen_classification when present.\\n"
    "14. Output must match this JSON structure:\\n"''',
    ),
    (
        '''    "7. Ground the summary in what was actually studied. When context.session_history "
    "is present it lists exactly the interactions of the current session: summarise "
    "those, and use context.history only to understand continuity. Do not report "
    "material that appears only in context.history and not in context.session_history. "
    "Use context.last_ocr_text for the material that was on screen and "
    "context.session_summary_seed for counts. Treat context.screen_classification as "
    "weak metadata and never let it define the study subject.\\n"
    "8. Name the subject and the specific material or mistakes only when they appear "
    "in the session interactions or material. If the session covered two different "
    "subjects, mention both instead of picking one.\\n"
    "9. Output must match this JSON structure:\\n"''',
        '''    "6. Use only the supplied context and keep the summary conservative.\\n"
    "7. Output must match this JSON structure:\\n"''',
    ),
]

INVERSES["llm_prompts.py"] = [
    ('        "knowledge_question_params",\n        "material_grounded_question",\n',
     '        "knowledge_question_params",\n'),
    ('        "history",\n        "session_history",\n', '        "history",\n'),
    (
        '''# Bounds for the session-memory block injected into concept_explain. They are kept
# deliberately small: the block travels with every explanation, so it must never
# crowd out the study text itself.
_RECENT_CONTEXT_OCR_CHARS = 1200''',
        "@@DELETE_RECENT_CONTEXT_HELPERS@@_RECENT_CONTEXT_OCR_CHARS = 1200",
    ),
    (
        '''                text=f"{text.strip()}{guidance_block}",
                recent_context=build_concept_recent_context(context),
''',
        '''                text=f"{text.strip()}{guidance_block}",
''',
    ),
    ('    "build_concept_recent_context",\n', ""),
    (
        '''_SUMMARY_HISTORY_LIMIT = 12''',
        "@@DELETE_SUMMARY_HELPERS@@_SUMMARY_HISTORY_LIMIT = 12",
    ),
]

# Block deletions (start marker -> end marker exclusive) applied after replacements.
DELETIONS = [
    ("llm_prompts.py", "@@DELETE_RECENT_CONTEXT_HELPERS@@", "def _build_structured_messages("),
    ("llm_prompts.py", "@@DELETE_SUMMARY_HELPERS@@", "def build_summarize_session_messages("),
]

# build_summarize_session_messages: restore the original body.
SUMMARIZE_ORIGINAL = (
    '''def build_summarize_session_messages(
    *,
    language: str,
    mode: str = MODE_COMPANION,
    context: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    context = dict(context or {})
    context.setdefault("language", language)
    context.setdefault("mode", normalize_mode(mode))
'''
)

INVERSES["entry_tutor_context_support.py"] = [
    (
        '''
# A supplied study material shorter than this is treated as an instruction
# ("generate a question from the image"), not as material to be grounded on.
_MATERIAL_GROUNDING_MIN_CHARS = 40
# Fields that pull a generated question toward a tracked topic. When an explicit
# study material decides the subject they are dropped, so an unrelated weak topic
# cannot hijack the question.
_CROSS_SUBJECT_QUESTION_PARAM_FIELDS = (
    "target_topic_id",
    "target_topic",
    "weak_topics",
    "due_reviews",
    "retry_wrong_question",
    "candidate_evidence",
)


def _drop_cross_subject_question_params(
    params: dict[str, Any] | None,
) -> dict[str, Any]:
    trimmed = dict(params or {})
    for field in _CROSS_SUBJECT_QUESTION_PARAM_FIELDS:
        if field in ("weak_topics", "due_reviews", "candidate_evidence"):
            trimmed[field] = []
        elif field == "retry_wrong_question":
            trimmed[field] = {}
        else:
            trimmed[field] = ""
    return trimmed
''',
        "",
    ),
    (
        '''        seed = dict(context or {})
        query = str(
            seed.get("topic_hint")
            or seed.get("source_text")''',
        '''        seed = dict(context or {})
        query = str(
            seed.get("source_text")
            or seed.get("question")
            or seed.get("topic_hint")''',
    ),
    (
        '''            if isinstance(supplied_params, dict):
                context["knowledge_question_params"] = dict(supplied_params)
            else:
                params = await asyncio.to_thread(
                    self._knowledge_tracker.get_next_question_params,
                    hint,
                )
                supplied_extra = extra if isinstance(extra, dict) else {}
                material_text = str(supplied_extra.get("source_text") or "").strip()
                source_kind = str(supplied_extra.get("source") or "").strip()
                material_grounded = bool(
                    material_text
                    and len(material_text) >= _MATERIAL_GROUNDING_MIN_CHARS
                    and source_kind != "targeted_question"
                )
                if material_grounded:
                    # The learner's own material decides the question subject.
                    context["material_grounded_question"] = True
                    resolved_target = str(
                        (params or {}).get("target_topic_id") or ""
                    ).strip()
                    if not (hint and resolved_target):
                        params = _drop_cross_subject_question_params(params)
                context["knowledge_question_params"] = params''',
        '''            if isinstance(supplied_params, dict):
                context["knowledge_question_params"] = dict(supplied_params)
            else:
                context["knowledge_question_params"] = await asyncio.to_thread(
                    self._knowledge_tracker.get_next_question_params,
                    hint,
                )''',
    ),
    ("            )[-64:]", "            )[-16:]"),
    (
        '''            # `history` is a rolling 50-row window that spans previous sessions.
            # A summary must describe what was actually studied in *this* one, so
            # the session boundary is derived from the in-memory event log.
            events = list(context.get("recent_learning_events") or [])
            async with _plugin_lock(self._lock):
                full_events = list(getattr(self._state, "recent_learning_events", []) or [])
            if len(full_events) > len(events):
                events = full_events
            session_start = min(
                (
                    float(event.get("at"))
                    for event in events
                    if isinstance(event, dict)
                    and isinstance(event.get("at"), (int, float))
                    and not isinstance(event.get("at"), bool)
                ),
                default=None,
            )
            if session_start is not None:
                session_history = [
                    item
                    for item in history
                    if isinstance(item, dict)
                    and float(item.get("created_at") or 0.0) >= session_start
                ]
                if session_history:
                    context["session_history"] = session_history
''',
        "",
    ),
    ('            "material_grounded_question",\n', ""),
]

INVERSES["entry_tutor_explain_entries.py"] = [
    ('from .entry_tutor_context_support import _TutorFinalizeProgress\n'
     'from .llm_prompts import build_concept_recent_context\n',
     'from .entry_tutor_context_support import _TutorFinalizeProgress\n'),
    (
        '''            payload["study_response_mode"] = response_mode
            payload["mode"] = active_mode
            payload["active_mode"] = active_mode
            payload["recent_context_chars"] = len(
                build_concept_recent_context(tutor_context)
            )''',
        '''            payload["study_response_mode"] = response_mode''',
    ),
]

INVERSES["entry_tutor_question_entries.py"] = [
    (
        '''        if targeted_context:
            # The stored topic is forced to the adaptive selection so mastery lands on
            # the intended topic; keep the model's own label visible so a mismatch
            # between the selected topic and the generated question is observable.
            model_topic_label = str((reply.payload or {}).get("topic") or "").strip()
            private_payload = _question_private_payload(''',
        '''        if targeted_context:
            private_payload = _question_private_payload(''',
    ),
    (
        '''            public_payload = _targeted_public_payload(private_payload)
            if model_topic_label:
                public_payload["question_topic_label"] = model_topic_label''',
        '''            public_payload = _targeted_public_payload(private_payload)''',
    ),
]


def apply_inverses(name: str, text: str) -> str:
    for new, old in INVERSES.get(name, []):
        if new not in text:
            raise AssertionError(f"{name}: inverse target not found:\n{new[:160]}")
        text = text.replace(new, old, 1)
    return text


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    PRE.mkdir(parents=True, exist_ok=True)
    diff_chunks: list[str] = []
    changed: list[str] = []
    for name in sorted(INVERSES):
        current = (LIVE / name).read_text(encoding="utf-8")
        pre_text = apply_inverses(name, current)
        # Structural block deletions for the helper functions added this round.
        for target, start_marker, end_marker in DELETIONS:
            if target != name:
                continue
            start = pre_text.index(start_marker)
            end = pre_text.index(end_marker, start)
            pre_text = pre_text[:start] + pre_text[end:]
        if name == "llm_prompts.py":
            marker = pre_text.index("def build_summarize_session_messages(")
            body_start = pre_text.index(") -> list[dict[str, str]]:", marker) + len(
                ") -> list[dict[str, str]]:"
            )
            body_end = pre_text.index("def build_operation_messages(", body_start)
            pre_text = (
                pre_text[:marker]
                + SUMMARIZE_ORIGINAL
                + "    return _build_structured_messages(\n"
                "        operation=LLM_OPERATION_SUMMARIZE_SESSION,\n"
                "        system_prompt=STUDY_SUMMARIZE_SESSION_SYSTEM_PROMPT,\n"
                "        requirements=STUDY_SUMMARIZE_SESSION_REQUIREMENTS,\n"
                "        context=context,\n"
                "        example=STUDY_SUMMARIZE_SESSION_EXAMPLE,\n"
                "        mode=mode,\n"
                "    )\n\n\n"
                + pre_text[body_end:]
            )
        (PRE / name).write_text(pre_text, encoding="utf-8")
        rel = f"plugin/plugins/study_companion/{name}"
        chunk = list(
            difflib.unified_diff(
                pre_text.splitlines(True),
                current.splitlines(True),
                fromfile=f"a/{rel}",
                tofile=f"b/{rel}",
            )
        )
        if len(chunk) > 4:
            changed.append(name)
        diff_chunks.extend(chunk)
    (OUT / "round2-teaching-context.patch").write_text(
        "".join(diff_chunks), encoding="utf-8"
    )
    print("changed files:", changed)
    print("added lines:", sum(1 for line in diff_chunks if line.startswith("+")
                              and not line.startswith("+++")))
    print("removed lines:", sum(1 for line in diff_chunks if line.startswith("-")
                                and not line.startswith("---")))


if __name__ == "__main__":
    main()
