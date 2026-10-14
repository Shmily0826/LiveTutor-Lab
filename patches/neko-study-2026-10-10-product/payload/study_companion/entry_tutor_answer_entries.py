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
    async def _resolve_learning_topic_binding(
        self, question_payload, selected_topic_id, expected_material,
        *, using_current_question, vision_image_payload,
    ):
        import hashlib
        import json

        course = expected_material["course_id"]
        prefix = course + "::"
        private = dict(question_payload.get("internal_private_payload") or {})
        origin = dict(private.get("source_material_context") or {})
        if origin.get("course_id") and origin["course_id"] != course:
            raise MaterialContextChanged("the held question belongs to another course")
        question = str(question_payload.get("question") or "").strip()
        reference = str(question_payload.get("answer") or "").strip()
        question_id = str(question_payload.get("question_id") or "") if using_current_question else ""
        material = str((origin if using_current_question else expected_material).get("material_identity") or "")
        provenance = {"course": course, "question": question, "reference": reference,
                      "question_id": question_id, "material": material,
                      "source": "held" if using_current_question else "supplied"}
        if vision_image_payload:
            provenance["image"] = hashlib.sha256(vision_image_payload.encode()).hexdigest()
        if not question_id and not reference:
            # Without a reference/artifact, only this session establishes sameness.
            provenance["session"] = expected_material["session_id"]
        key = hashlib.sha256(json.dumps(provenance, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        previous = private.get("learning_topic_binding")
        valid_previous = (isinstance(previous, dict) and type(previous.get("v")) is int and previous["v"] == 1
                          and previous.get("key") == key and str(previous.get("topic_id") or "").startswith(prefix))
        label_hint = question_payload.get("topic")
        label_hint = label_hint.strip() if isinstance(label_hint, str) else ""
        status = "explicit"
        if selected_topic_id:
            known = await asyncio.to_thread(self._store.get_topic, selected_topic_id)
            if ("::" in selected_topic_id and not selected_topic_id.startswith(prefix)
                    and not (known and known.get("source") == "seed"
                             and known.get("course_family") in (None, "", course))):
                raise MaterialContextChanged("selected topic belongs to another course")
            topic = selected_topic_id if selected_topic_id.startswith(prefix) else prefix + selected_topic_id
            if valid_previous:
                if previous["topic_id"] != topic:
                    raise MaterialContextChanged("selected topic conflicts with the held question binding")
                return dict(previous)
        elif valid_previous:
            return dict(previous)
        else:
            candidates = await asyncio.to_thread(
                self._store.question_topic_candidates, course_id=course, question=question,
                expected_answer=reference, question_id=question_id, material_identity=material,
                binding_key=key, allow_legacy=not vision_image_payload and bool(reference or question_id),
            )
            if len(candidates) == 1:
                topic, status = candidates[0], "unique_history"
            else:
                labels = [] if candidates else await asyncio.to_thread(
                    self._store.concept_label_candidates, course_id=course, label=label_hint)
                if len(labels) == 1:
                    topic, status = labels[0], "unique_concept_label"
                else:
                    topic = prefix + "question_" + key[:24]
                    status = ("ambiguous_history" if candidates else
                              "ambiguous_concept_label" if labels else "new_question")
            known = await asyncio.to_thread(self._store.get_topic, topic)
            if not known and status == "unique_concept_label":
                known = await asyncio.to_thread(self._store.get_topic, topic.removeprefix(prefix))
        label = str((known or {}).get("name") or label_hint or question)[:160]
        return {"v": 1, "key": key, "topic_id": topic, "label": label,
                "scope": "question" if topic == prefix + "question_" + key[:24] and status != "explicit" else "concept",
                "source": status}

    def _save_retry_question_checkpoint(self, snapshot) -> None:
        import json
        import time

        course_id = snapshot["study_course_id"]
        progress = {"version": 1, "course_id": course_id}
        for name in ("current_question", "last_answer_evaluation", "last_question_at", "last_answer_evaluated_at"):
            progress[name] = snapshot.get(name, {} if name in ("current_question", "last_answer_evaluation") else "")
        # The existing Store setters commit separately. Both existing kv records
        # must move together before a new attempt becomes visible in memory.
        with self._store.answer_write_lock():
            conn = self._store._require_conn()
            if conn.in_transaction:
                raise RuntimeError("retry checkpoint requires an idle SQLite transaction")
            conn.execute("BEGIN IMMEDIATE")
            try:
                for key, value in (("state", snapshot), ("course_teaching_progress:" + course_id, progress)):
                    conn.execute(
                        "INSERT INTO kv (key, value, updated_at) VALUES (?, ?, ?) "
                        "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                        (key, json.dumps(value, ensure_ascii=False, sort_keys=True), time.time()),
                    )
                conn.commit()
            except BaseException:
                conn.rollback()
                raise

    @plugin_entry(
        id="study_retry_question",
        name=tr("entries.retry_question.name", default="Retry the Same Study Question"),
        description="Explicitly retry the current wrong or partial question with a new attempt, preserving its original question and grades. Does not generate a question or call a model.",
        input_schema={
            "type": "object",
            "properties": {name: {"type": "string", "minLength": 1} for name in
                           ("question_id", "attempt_id", "course_id", "session_id")},
            "required": ["question_id", "attempt_id", "course_id", "session_id"],
            "additionalProperties": False,
        },
        timeout=20.0,
    )
    async def study_retry_question(
        self, question_id: str = "", attempt_id: str = "", course_id: str = "", session_id: str = "", **_
    ):
        from copy import deepcopy

        expected = {"question_id": question_id, "attempt_id": attempt_id,
                    "course_id": course_id, "session_id": session_id}
        if not all(isinstance(value, str) and value for value in expected.values()):
            return Err(SdkError("retry requires the exact current question, attempt, course and session", code="QUESTION_CONTEXT_CHANGED"))
        async with self._lock:
            context = material_context(self, include_material=False)
            held = self._state.current_question
            actual = {"question_id": held.get("question_id"), "attempt_id": held.get("attempt_id"), **context}
            if actual != expected or str(getattr(self, "_study_session_id", "") or "") != session_id:
                return Err(SdkError("question or course changed; no retry was created", code="QUESTION_CONTEXT_CHANGED"))
            if held.get("attempt_evaluation_pending") or held.get("attempt_evaluation_owner"):
                return Err(SdkError("the current attempt is still being evaluated", code="ATTEMPT_IN_PROGRESS"))
            cache = held.get("answer_evaluation_cache")
            if (held.get("attempt_evaluated") is not True or not isinstance(cache, dict)
                    or cache.get("question_id") != question_id or cache.get("attempt_id") != attempt_id
                    or cache.get("degraded") or cache.get("ok") is False
                    or cache.get("verdict") not in ("wrong", "partial")):
                return Err(SdkError("only a scored wrong or partial attempt can be explicitly retried", code="ATTEMPT_NOT_RETRYABLE"))
            origin = (held.get("internal_private_payload") or {}).get("source_material_context")
            if isinstance(origin, dict) and origin.get("course_id") and origin["course_id"] != course_id:
                return Err(SdkError("the held question belongs to another course", code="QUESTION_CONTEXT_CHANGED"))
            retried = deepcopy(held)
            retried["attempt_id"] = "a_" + uuid.uuid4().hex
            retried["attempt_evaluated"] = False
            for name in ("answer_evaluation_cache", "attempt_evaluation_pending", "attempt_evaluation_owner", "attempt_evaluation_recovery"):
                retried.pop(name, None)
            snapshot = self._state.to_dict()
            snapshot["current_question"] = retried
            worker = asyncio.create_task(asyncio.to_thread(self._save_retry_question_checkpoint, snapshot))
            cancelled = False
            try:
                while True:
                    try:
                        await asyncio.shield(worker)
                        break
                    except asyncio.CancelledError:
                        # A worker can commit after cancellation. Drain this short
                        # local transaction before releasing the state lock.
                        cancelled = True
                        if worker.cancelled():
                            raise
            except Exception:
                if cancelled:
                    raise asyncio.CancelledError()
                return Err(SdkError("could not save retry; the original attempt is unchanged", code="RETRY_PERSIST_FAILED"))
            self._state.current_question = retried
            if cancelled:
                raise asyncio.CancelledError()
            return Ok({"question_id": question_id, "attempt_id": retried["attempt_id"],
                       "previous_attempt_id": attempt_id, **context,
                       "current_question": public_current_question_payload(retried),
                       "question_state": "pending", "retried": True})

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
        selected_topic_id = question_topic_id or client_topic_id
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
            learning_binding = await self._resolve_learning_topic_binding(
                question_payload, selected_topic_id, expected_material,
                using_current_question=using_current_question, vision_image_payload=vision_image_payload,
            )
            private = dict(question_payload.get("internal_private_payload") or {})
            question_payload["internal_private_payload"] = {**private, "learning_topic_binding": learning_binding}
            async with self._lock:
                if not material_context_current(self, expected_material):
                    raise MaterialContextChanged("course/session changed while resolving topic")
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
                    "_learning_topic_binding": learning_binding,
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
                    payload["topic"] = learning_binding["topic_id"]
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
                        private = dict(self._state.current_question.get("internal_private_payload") or {})
                        self._state.current_question["internal_private_payload"] = {
                            **private, "learning_topic_binding": learning_binding,
                        }
                        self._state.current_question["answer_evaluation_cache"] = (
                            public_eval_cache
                        )
                        final_attempt_state_staged = True
                await self._persist_state()
            topic = str(
                learning_binding["topic_id"]
                or selected_topic_id
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
