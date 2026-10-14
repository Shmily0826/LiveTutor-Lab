from __future__ import annotations

import contextlib
import uuid

from .entry_common import (
    asyncio,
    Err,
    Ok,
    SdkError,
    _entry_exception_error,
    _validate_optional_vision_image_payload,
    plugin_entry,
    tr,
    ui,
    LLM_OPERATION_ANSWER_EVALUATE,
)
from .models import public_current_question_payload
from .study_materials import material_context, material_context_current, MaterialContextChanged


class _TutorAnswerEntriesMixin:
    async def _clear_attempt_evaluation_reservation(
        self, attempt_id: str, *, reservation_owner: str, recover_cached: bool = False
    ) -> None:
        if not attempt_id:
            return
        async with self._lock:
            if (str(self._state.current_question.get("attempt_id") or "") == attempt_id
                    and self._state.current_question.get("attempt_evaluation_owner") == reservation_owner):
                self._state.current_question.pop("attempt_evaluation_pending", None)
                self._state.current_question.pop("attempt_evaluation_owner", None)
                if (
                    recover_cached
                    and self._state.current_question.get("attempt_evaluated")
                    and isinstance(
                        self._state.current_question.get("answer_evaluation_cache"),
                        dict,
                    )
                ):
                    self._state.current_question["attempt_evaluation_recovery"] = True

    @ui.action()
    @plugin_entry(
        id="study_evaluate_answer",
        name=tr("entries.evaluate_answer.name", default="Evaluate Study Answer"),
        description=tr(
            "entries.evaluate_answer.description",
            default="Evaluate an answer against the current generated question or a supplied question.",
        ),
        input_schema={
            "type": "object",
            "properties": {
                "answer": {"type": "string", "default": ""},
                "question": {"type": "string", "default": ""},
                "expected_answer": {"type": "string", "default": ""},
                "question_id": {"type": "string", "default": ""},
                "attempt_id": {"type": "string", "default": ""},
                "selected_topic_id": {"type": "string", "default": ""},
                "vision_image_base64": {"type": "string", "default": ""},
            },
        },
        timeout=70.0,
        llm_result_fields=[
            "summary",
            "verdict",
            "score",
            "error_type",
            "feedback",
            "next_action",
        ],
    )
    async def study_evaluate_answer(
        self, answer: str = "", question: str = "", expected_answer: str = "", **kwargs
    ):
        if self._agent is None:
            return Err(SdkError("study tutor agent is not initialized"))
        # The held question is an immutable artifact. Ordinary grading does
        # not silently consult a newly selected picture; course/session still
        # fence its asynchronous result. Explicit vision callers may supply a
        # full material context separately.
        expected_material = dict(kwargs.get("_material_context") or material_context(self, include_material=False))
        target_lanlan = self._resolve_study_target_lanlan(kwargs)
        async with self._lock:
            if not material_context_current(self, expected_material):
                return Err(SdkError("课程已切换，请重新确认当前题目。", code="course_context_changed"))
            current_question = dict(self._state.current_question)
            active_mode = self._state.active_mode
        supplied_question = str(question or "").strip()
        supplied_expected = str(expected_answer or "").strip()
        state_question = str(current_question.get("question") or "").strip()
        state_expected = str(current_question.get("answer") or "").strip()
        supplied_question_id = str(kwargs.get("question_id") or "").strip()
        supplied_attempt_id = str(kwargs.get("attempt_id") or "").strip()
        state_question_id = str(current_question.get("question_id") or "").strip()
        state_attempt_id = str(current_question.get("attempt_id") or "").strip()
        current_question_requires_identity = bool(state_question_id or state_attempt_id)
        supplied_current_identity = bool(
            current_question_requires_identity
            and (
                (
                    supplied_question_id
                    and state_question_id
                    and supplied_question_id == state_question_id
                )
                or (
                    supplied_attempt_id
                    and state_attempt_id
                    and supplied_attempt_id == state_attempt_id
                )
            )
        )
        using_current_question = (
            not supplied_question
            or supplied_question == state_question
            or supplied_current_identity
        )
        if current_question_requires_identity and using_current_question:
            if (
                not supplied_question_id
                or not supplied_attempt_id
                or supplied_question_id != state_question_id
                or supplied_attempt_id != state_attempt_id
            ):
                return Err(
                    SdkError(
                        "current question identity does not match",
                        code="QUESTION_MISMATCH",
                    )
                )
            if current_question.get("attempt_evaluated"):
                cached_evaluation = current_question.get("answer_evaluation_cache")
                if current_question.get("attempt_evaluation_recovery") and isinstance(
                    cached_evaluation, dict
                ):
                    return Ok(dict(cached_evaluation))
                return Err(
                    SdkError(
                        "attempt has already been evaluated",
                        code="ATTEMPT_ALREADY_EVALUATED",
                    )
                )
        resolved_question = state_question if using_current_question else supplied_question
        if not resolved_question:
            return Err(SdkError("study tutor requires a question to evaluate against"))
        vision_image_payload = str(kwargs.get("vision_image_base64") or "").strip()
        validated_vision_image = _validate_optional_vision_image_payload(
            self, vision_image_payload, operation="study_evaluate_answer"
        )
        if isinstance(validated_vision_image, Err):
            return validated_vision_image
        vision_image_payload = validated_vision_image
        if using_current_question:
            if supplied_expected and supplied_expected != state_expected:
                return Err(
                    SdkError(
                        "expected answer does not match the current question",
                        code="QUESTION_MISMATCH",
                    )
                )
            resolved_expected = state_expected
        else:
            resolved_expected = supplied_expected
        answer_text = str(answer or "").strip()
        question_payload = dict(current_question) if using_current_question else {}
        question_payload.update(
            {
                "question": resolved_question,
                "answer": resolved_expected,
            }
        )
        client_topic_id = str(kwargs.get("selected_topic_id") or "").strip()
        question_topic_id = str(
            question_payload.get("selected_topic_id")
            or question_payload.get("topic_id")
            or question_payload.get("topic")
            or ""
        ).strip()
        if (
            using_current_question
            and client_topic_id
            and question_topic_id
            and client_topic_id != question_topic_id
        ):
            return Err(
                SdkError(
                    "selected topic does not match the current question",
                    code="QUESTION_MISMATCH",
                )
            )
        selected_topic_id = (
            question_topic_id if using_current_question else client_topic_id or question_topic_id
        )
        if selected_topic_id:
            question_payload["selected_topic_id"] = selected_topic_id
        reserved_attempt = False
        reservation_owner = uuid.uuid4().hex
        final_attempt_state_staged = False
        run_id = self._resolve_current_run_id(kwargs)
        session_id = str(kwargs.get("session_id") or "").strip()
        try:
            if not session_id:
                session_id = await self._ensure_active_study_session()
            async with self._lock:
                current = material_context(self, include_material="material_identity" in expected_material)
                if (any(current.get(key) != value for key, value in expected_material.items()
                        if key != "session_id" or value)
                        or current["session_id"] != session_id):
                    raise MaterialContextChanged("course/session changed before grading context")
                expected_material = current
                # Reserve only after an empty session has resumed the held quiz;
                # that session startup correctly clears departed reservations.
                if using_current_question and state_attempt_id:
                    live_question = self._state.current_question
                    if (str(live_question.get("question_id") or "") != state_question_id
                            or str(live_question.get("attempt_id") or "") != state_attempt_id):
                        return Err(SdkError("current question identity does not match", code="QUESTION_MISMATCH"))
                    if live_question.get("attempt_evaluated") or live_question.get("attempt_evaluation_pending"):
                        return Err(SdkError("attempt has already been evaluated", code="ATTEMPT_ALREADY_EVALUATED"))
                    live_question["attempt_evaluation_pending"] = True
                    live_question["attempt_evaluation_owner"] = reservation_owner
                    reserved_attempt = True
            tutor_context = await self._build_learning_context(
                LLM_OPERATION_ANSWER_EVALUATE,
                input_text=answer_text,
                extra={
                    "question": resolved_question,
                    "expected_answer": resolved_expected,
                    "answer": answer_text,
                    "current_question": current_question
                    if using_current_question
                    else {},
                    "public_current_question": public_current_question_payload(
                        current_question
                    )
                    if using_current_question
                    else {},
                    "question_payload": question_payload,
                    "question_source": "current_question"
                    if using_current_question
                    else "supplied",
                    "run_id": run_id,
                    "session_id": session_id,
                    "question_id": supplied_question_id or state_question_id,
                    "attempt_id": supplied_attempt_id or state_attempt_id,
                    "selected_topic_id": selected_topic_id,
                    "mode": active_mode,
                    "_material_context": expected_material,
                    **(
                        {
                            "vision_enabled": True,
                            "vision_image_base64": vision_image_payload,
                        }
                        if vision_image_payload
                        else {"vision_enabled": False, "vision_image_base64": "", "vision_snapshot": {},
                              "last_ocr_text": "", "last_ocr_at": ""}
                    ),
                },
                session_id=session_id,
            )
            if not material_context_current(self, expected_material):
                raise MaterialContextChanged("course/session changed while building grading context")
            tutor_context["_material_context"] = expected_material
            reply = await self._agent.answer_evaluate(
                question=resolved_question,
                answer=answer_text,
                expected_answer=resolved_expected,
                mode=active_mode,
                context=tutor_context,
            )
            if not material_context_current(self, expected_material):
                raise MaterialContextChanged("course/session changed during grading")
            payload = await self._finalize_tutor_call(
                LLM_OPERATION_ANSWER_EVALUATE,
                reply,
                history_kind=LLM_OPERATION_ANSWER_EVALUATE,
                metadata={
                    "question": resolved_question,
                    "question_id": supplied_question_id or state_question_id,
                    "attempt_id": supplied_attempt_id or state_attempt_id,
                    "source_material_context": (question_payload.get("internal_private_payload") or {}).get("source_material_context", {}),
                    "degraded": reply.degraded,
                    "diagnostic": reply.diagnostic,
                    "payload": reply.payload,
                    "screen_classification": tutor_context.get(
                        "screen_classification"
                    )
                    or {},
                },
                extra_context=tutor_context,
            )
            if not material_context_current(self, expected_material):
                raise MaterialContextChanged("course/session changed after grading commit")
            if reply.degraded:
                if reserved_attempt:
                    await self._clear_attempt_evaluation_reservation(state_attempt_id, reservation_owner=reservation_owner)
                    await self._persist_state()
                return Ok(payload)
            payload["question"] = resolved_question
            if supplied_question_id or state_question_id:
                payload["question_id"] = supplied_question_id or state_question_id
            if supplied_attempt_id or state_attempt_id:
                payload["attempt_id"] = supplied_attempt_id or state_attempt_id
            if selected_topic_id:
                payload["selected_topic_id"] = selected_topic_id
                if using_current_question:
                    payload["topic"] = selected_topic_id
            scope_key = str(question_payload.get("scope_key") or "").strip()
            if scope_key:
                payload["scope_key"] = scope_key
                payload["scope_revision"] = int(
                    question_payload.get("scope_revision") or 0
                )
                if (
                    str(payload.get("verdict") or "").strip().lower() == "correct"
                    and int(question_payload.get("scope_topic_count") or 0) == 1
                ):
                    payload["practice_scope_status"] = "completed"
                    payload["can_continue_review"] = True
            payload["screen_classification"] = (
                tutor_context.get("screen_classification") or {}
            )
            if using_current_question and state_attempt_id:
                public_eval_cache = {
                    key: value
                    for key, value in payload.items()
                    if key
                    not in {
                        "answer",
                        "accepted_answers",
                        "key_points",
                        "rubric",
                        "solution_steps",
                        "internal_private_payload",
                        "current_question_private",
                    }
                }
                async with self._lock:
                    if (not material_context_current(self, expected_material)
                            or self._state.current_question.get("attempt_evaluation_owner") != reservation_owner):
                        raise MaterialContextChanged("the grading reservation or session was replaced before staging")
                    if (
                        str(self._state.current_question.get("attempt_id") or "")
                        == state_attempt_id
                    ):
                        self._state.current_question.pop(
                            "attempt_evaluation_pending", None
                        )
                        self._state.current_question["attempt_evaluated"] = True
                        self._state.current_question["answer_evaluation_cache"] = (
                            public_eval_cache
                        )
                        final_attempt_state_staged = True
                await self._persist_state()
            topic = str(
                selected_topic_id
                or question_payload.get("selected_topic_id")
                or question_payload.get("topic")
                or payload.get("selected_topic_id")
                or payload.get("topic")
                or tutor_context.get("topic")
                or ""
            ).strip()
            try:
                mastery_after = (
                    await asyncio.to_thread(self._knowledge_tracker.get_mastery, topic)
                    if topic
                    else -1.0
                )
            except Exception as exc:
                self.logger.warning("study answer mastery enrichment failed: {}", exc)
                mastery_after = -1.0
            if not material_context_current(self, expected_material):
                raise MaterialContextChanged("course/session changed before grading feedback")
            if using_current_question and (state_question_id or state_attempt_id):
                async with self._lock:
                    if (not material_context_current(self, expected_material)
                            or self._state.current_question.get("attempt_evaluation_owner") != reservation_owner
                            or str(self._state.current_question.get("question_id") or "") != state_question_id
                            or str(self._state.current_question.get("attempt_id") or "") != state_attempt_id):
                        raise MaterialContextChanged("the held question was replaced before grading feedback")
            await self._emit_answer_evaluated_event(
                verdict=str(payload.get("verdict") or ""),
                score=payload.get("score", 0.0),
                question_summary=resolved_question,
                user_answer_summary=answer_text,
                correction_hint=str(
                    payload.get("correction_hint")
                    or payload.get("feedback")
                    or payload.get("next_action")
                    or ""
                ),
                topic=topic,
                mastery_after=mastery_after,
                target_lanlan=target_lanlan,
            )
            if not material_context_current(self, expected_material):
                raise MaterialContextChanged("course/session changed before grading return")
            if using_current_question and (state_question_id or state_attempt_id):
                async with self._lock:
                    if (not material_context_current(self, expected_material)
                            or self._state.current_question.get("attempt_evaluation_owner") != reservation_owner
                            or str(self._state.current_question.get("question_id") or "") != state_question_id
                            or str(self._state.current_question.get("attempt_id") or "") != state_attempt_id):
                        raise MaterialContextChanged("the held question was replaced before grading return")
            if reserved_attempt:
                await self._clear_attempt_evaluation_reservation(state_attempt_id, reservation_owner=reservation_owner)
                await self._persist_state()
                if (not material_context_current(self, expected_material)
                        or str(self._state.current_question.get("question_id") or "") != state_question_id
                        or str(self._state.current_question.get("attempt_id") or "") != state_attempt_id):
                    raise MaterialContextChanged("the grading context changed during reservation cleanup")
            return Ok(payload)
        except asyncio.CancelledError:
            if reserved_attempt:
                await self._clear_attempt_evaluation_reservation(
                    state_attempt_id,
                    reservation_owner=reservation_owner,
                    recover_cached=final_attempt_state_staged,
                )
                with contextlib.suppress(Exception):
                    await self._persist_state()
            raise
        except Exception as exc:
            if reserved_attempt:
                await self._clear_attempt_evaluation_reservation(
                    state_attempt_id,
                    reservation_owner=reservation_owner,
                    recover_cached=final_attempt_state_staged,
                )
                with contextlib.suppress(Exception):
                    await self._persist_state()
            if isinstance(exc, MaterialContextChanged):
                return Err(SdkError("课程、会话或题目已切换，请重新确认当前题目。", code="course_context_changed"))
            return _entry_exception_error(
                self, exc, operation="study_evaluate_answer"
            )
