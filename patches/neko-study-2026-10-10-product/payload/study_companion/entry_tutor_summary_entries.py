from __future__ import annotations

from .study_materials import material_context, material_context_current, MaterialContextChanged
from .entry_common import (
    asyncio,
    Err,
    Ok,
    SdkError,
    plugin_entry,
    tr,
    ui,
    LLM_OPERATION_SUMMARIZE_SESSION,
)


class _TutorSummaryEntriesMixin:
    @ui.action()
    @plugin_entry(
        id="study_start_session",
        name=tr("entries.start_session.name", default="Start Study Session"),
        description=tr("entries.start_session.description", default="Start a new persistent study session."),
        input_schema={"type": "object", "properties": {"course_id": {"type": "string", "default": ""}}},
        llm_result_fields=["session_id", "started_at", "course_id"],
    )
    async def study_start_session(self, course_id: str = "", **_):
        course_id = str(course_id or "").strip()
        if len(course_id) > 80:
            return Err(SdkError("course_id must be at most 80 characters", code="INVALID_COURSE"))
        session_id = await self._restart_study_session(course_id=course_id)
        sessions = await asyncio.to_thread(self._store.list_sessions, 1)
        session = next(
            (row for row in sessions if row.get("id") == session_id), {}
        )
        return Ok({"session_id": session_id, "started_at": session.get("started_at", ""),
                   "course_id": self._state.study_course_id})

    @ui.action()
    @plugin_entry(
        id="study_set_course", name="Choose study course",
        description="Choose an explicit course and start a fresh session without mixing course history.",
        input_schema={"type": "object", "required": ["course_id"], "properties": {"course_id": {"type": "string"}}},
        llm_result_fields=["session_id", "course_id"],
    )
    async def study_set_course(self, course_id: str = "", **_):
        if not str(course_id or "").strip():
            return Err(SdkError("course_id is required", code="INVALID_COURSE"))
        return await self.study_start_session(course_id=course_id)

    @ui.action()
    @plugin_entry(
        id="study_end_session",
        name=tr("entries.end_session.name", default="End Study Session"),
        description=tr("entries.end_session.description", default="End the active study session."),
        input_schema={"type": "object", "properties": {}},
        llm_result_fields=["session_id", "ended_at"],
    )
    async def study_end_session(self, **_):
        session_id = await self._end_study_session()
        sessions = await asyncio.to_thread(self._store.list_sessions, 100)
        session = next((row for row in sessions if row.get("id") == session_id), {})
        return Ok({"session_id": session_id, "ended_at": session.get("ended_at", "")})

    @ui.action()
    @plugin_entry(
        id="study_get_session",
        name=tr("entries.get_session.name", default="Get Study Session"),
        description=tr("entries.get_session.description", default="Retrieve a saved study session and its interactions."),
        input_schema={"type": "object", "required": ["session_id"], "properties": {"session_id": {"type": "string"}}},
        llm_result_fields=["session", "interactions"],
    )
    async def study_get_session(self, session_id: str = "", **_):
        session = next(
            (row for row in await asyncio.to_thread(self._store.list_sessions, 500)
             if row.get("id") == str(session_id or "").strip()),
            None,
        )
        if session is None:
            return Err(SdkError("study session not found", code="SESSION_NOT_FOUND"))
        interactions = await asyncio.to_thread(
            self._store.list_interactions, 500, session_id=session["id"]
        )
        return Ok({"session": session, "interactions": interactions})

    @ui.action()
    @plugin_entry(
        id="study_summarize_session",
        name=tr("entries.summarize_session.name", default="Summarize Study Session"),
        description=tr(
            "entries.summarize_session.description",
            default="Summarize recent study interactions into compact study notes.",
        ),
        input_schema={
            "type": "object",
            "properties": {"focus": {"type": "string", "default": ""}},
        },
        timeout=85.0,
        llm_result_fields=[
            "summary",
            "markdown",
            "highlights",
            "weak_points",
            "next_actions",
        ],
    )
    async def study_summarize_session(self, focus: str = "", _material_context=None,
                                      _narration_target_lanlan="", **_):
        if self._agent is None:
            return Err(SdkError("study tutor agent is not initialized"))
        # Capture before the first await; a history summary follows its course
        # and session, not a picture submitted while the request is waiting.
        observed = material_context(self, include_material=False)
        narration_target = (_narration_target_lanlan.strip()
                            if isinstance(_narration_target_lanlan, str) and len(_narration_target_lanlan) <= 256 else "")
        expected = dict(_material_context) if isinstance(_material_context, dict) else observed
        try:
            if (_material_context is not None and not isinstance(_material_context, dict)
                    or set(expected) != {"course_id", "session_id"}
                    or any(not isinstance(value, str) for value in expected.values())
                    or not material_context_current(self, expected)):
                raise MaterialContextChanged("summary context is no longer current")
            session_id = await self._ensure_active_study_session()
            async with self._lock:
                current = material_context(self, include_material=False)
                if (current["course_id"] != expected["course_id"]
                        or expected["session_id"] and current["session_id"] != expected["session_id"]
                        or current["session_id"] != session_id):
                    raise MaterialContextChanged("summary session was replaced")
                expected = current
                active_mode = self._state.active_mode

            async def check_current():
                async with self._lock:
                    if not material_context_current(self, expected):
                        raise MaterialContextChanged("summary course or session was replaced")

            history = await asyncio.to_thread(self._store.list_interactions, 100, session_id=session_id)
            await check_current()
            tutor_context = await self._build_learning_context(
                LLM_OPERATION_SUMMARIZE_SESSION,
                input_text="session",
                extra={"focus": str(focus or "").strip(), "mode": active_mode,
                       "_material_context": dict(expected)},
                session_id=session_id,
            )
            await check_current()
            if (tutor_context.get("course_id") != expected["course_id"]
                    or tutor_context.get("session_id") != session_id):
                raise MaterialContextChanged("summary history and learning context do not match")
            tutor_context["history"] = history
            tutor_context["session_history"] = history
            tutor_context["vision_enabled"] = False
            tutor_context["vision_image_base64"] = ""
            tutor_context.pop("vision_snapshot", None)
            tutor_context["last_ocr_text"] = ""
            tutor_context["last_ocr_at"] = ""
            reply = await self._agent.summarize_session(history, mode=active_mode, context=tutor_context)
            await check_current()
            payload = await self._finalize_tutor_call(
                LLM_OPERATION_SUMMARIZE_SESSION,
                reply,
                history_kind=LLM_OPERATION_SUMMARIZE_SESSION,
                extra_context=tutor_context,
                metadata={"degraded": reply.degraded, "diagnostic": reply.diagnostic,
                          "payload": reply.payload,
                          "screen_classification": tutor_context.get("screen_classification") or {}},
            )
            await check_current()
            payload["screen_classification"] = tutor_context.get("screen_classification") or {}
            if not reply.degraded:
                # Preserve provenance for the narration consumer; its queue's
                # eventual delivery guard is separate from this entry check.
                narration = {**payload, "_material_context": dict(expected),
                             "_session_summary_seed": dict(tutor_context.get("session_summary_seed") or {}),
                             "_narration_target_lanlan": narration_target}
                try:
                    await self._emit_session_summarized_event(narration)
                except MaterialContextChanged:
                    raise
                except Exception as exc:
                    self.logger.warning("study session summarized event degraded: {}", exc)
                await check_current()
            return Ok(payload)
        except MaterialContextChanged:
            return Err(SdkError("课程或学习会话已切换，请重新总结当前课程。", code="course_context_changed"))
