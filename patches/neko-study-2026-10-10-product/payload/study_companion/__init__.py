from __future__ import annotations

import asyncio
import base64
from collections.abc import Mapping
from dataclasses import replace
from datetime import datetime
import json
import math
from pathlib import Path
import threading
from types import SimpleNamespace
import time
import uuid
from typing import Any
from urllib.parse import quote
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from plugin.sdk.plugin import (
    Err,
    NekoPluginBase,
    Ok,
    OsActivitySnapshot,
    SdkError,
    custom_event,
    get_os_activity_snapshot,
    lifecycle,
    neko_plugin,
    plugin_entry,
    tr,
)

from .constants import (
    LLM_OPERATION_ANSWER_EVALUATE,
    LLM_OPERATION_CONCEPT_EXPLAIN,
    LLM_OPERATION_KNOWLEDGE_TRACK,
    LLM_OPERATION_QUESTION_GENERATE,
    LLM_OPERATION_SUMMARIZE_SESSION,
    MODE_COMPANION,
    MODE_INTERACTIVE,
    MODE_TEACHING,
)
from .doc_exporter import DocExporter, normalize_format
from .awareness_buffer import ActivityBuffer
from .checkin_manager import CheckinManager
from ._event_bus import StudyEvent, StudyEventBus
from .pomodoro_timer import PomodoroTimer
from .screen_classifier import classify_app_from_title, classify_screen_from_ocr
from .models import (
    MODE_CONCEPT_EXPLAIN,
    STATUS_ERROR,
    STATUS_READY,
    STATUS_STOPPED,
    ActivitySnapshot,
    ActivitySummary,
    StudyConfig,
    StudyState,
    TutorReply,
    build_config,
    utc_now_iso,
)
from .service import (
    build_dependency_status,
    build_explain_payload,
    build_ocr_payload,
    build_status_payload,
    build_tutor_payload,
)
from .mode_manager import (
    ModeManager,
    build_transition_phrase,
    handle_user_intent,
    normalize_mode,
)
from .knowledge_contribution import PublicGraphContributionBuilder
from .knowledge_tracker import KnowledgeTracker
from .memory_deck_store import MemoryDeckStore, MemoryItemNotFoundError
from .memory_habit_bridge import MemoryHabitBridge
from .state import build_initial_state
from .store import StudyStore
from .store_notebook import NotebookStore
from .study_habit_store import StudyHabitStore
from .study_ocr_pipeline import StudyOcrPipeline
from .study_avatar_tools import _StudyAvatarToolsMixin
from .study_code_tools import _StudyCodeToolsMixin
from .study_materials import load_material, material_context, material_changes, submit_material_changes
from .supervision import SupervisionController
from .tutor_llm_agent import TutorLLMAgent
from .tutor_llm_agent import diagnostic_code_for_exception
from .ui_api import STUDY_PANEL_SURFACE_ID, build_open_ui_payload
from .ui_api import build_contribution_settings_payload, build_knowledge_map_payload
from .ui_api import build_habit_dashboard_payload, build_pomodoro_status_payload
from .voice_contracts import (
    VOICE_TRANSCRIPT_EVENT_ID,
    VOICE_TRANSCRIPT_EVENT_TYPE,
    voice_transcript_cancel_response,
    voice_transcript_noop,
    voice_transcript_prime_context,
)
from .voice_filter import VoiceFilter, _derive_subject, build_context_for_catgirl


_OS_CATEGORY_TO_APP_TYPE: dict[str, str] = {
    "gaming": "game",
    "work": "work",
    "entertainment": "entertainment",
    "communication": "communication",
}


def _voice_session_key(lanlan_name: str, metadata: Mapping[str, Any] | None) -> str:
    for key in ("voice_session_id", "session_id", "conversation_id", "request_session_id"):
        value = metadata.get(key) if isinstance(metadata, Mapping) else None
        text = str(value or "").strip()
        if text:
            return f"session:{text}"
    name = str(lanlan_name or "").strip()
    return f"lanlan:{name}" if name else "__default__"


def _register_install_routes() -> None:
    from plugin.server.install_registry import (
        InstallKindRegistration,
        register_install_plugin,
    )

    register_install_plugin(
        "study_companion",
        install_kinds={
            "rapidocr_models": InstallKindRegistration(
                entry_id="study_download_rapidocr_models",
                label="RapidOCR Models",
                queued_message="RapidOCR model download queued",
            ),
            "tesseract": InstallKindRegistration(
                entry_id="study_install_tesseract",
                label="Tesseract",
                queued_message="Tesseract install queued",
            ),
        },
        ui_i18n_dir=Path(__file__).resolve().parent / "i18n",
        tutorial_enabled=True,
    )


try:
    _register_install_routes()
except Exception:  # noqa: BLE001 - route registration should not block package import.
    from plugin.logging_config import get_logger

    get_logger("study.install_routes").warning(
        "study install route registration failed",
        exc_info=True,
    )


_REVIEW_DUE_INTERVAL_SECONDS = 1800.0
_AWARENESS_OS_TIMEOUT_SECONDS = 2.0


from .entry_tutor_context_support import _TutorContextSupportMixin
from .entry_communication_pomodoro_events import _CommunicationPomodoroEventsMixin
from .entry_communication_review_events import _CommunicationReviewEventsMixin
from .entry_communication_tutor_events import _CommunicationTutorEventsMixin
from .entry_export_support import _ExportSupportMixin
from .entry_status_entries import _StatusEntriesMixin
from .entry_memory_card_entries import _MemoryCardEntriesMixin
from .entry_memory_deck_entries import _MemoryDeckEntriesMixin
from .entry_memory_import_entries import _MemoryImportEntriesMixin
from .entry_memory_review_entries import _MemoryReviewEntriesMixin
from .entry_pomodoro_entries import _PomodoroEntriesMixin
from .entry_goal_entries import _GoalEntriesMixin
from .entry_checkin_entries import _CheckinEntriesMixin
from .entry_supervision_entries import _SupervisionEntriesMixin
from .entry_knowledge_entries import _KnowledgeEntriesMixin
from .entry_practice_scope_entries import _PracticeScopeEntriesMixin
from .entry_mode_entries import _ModeEntriesMixin
from .entry_tutor_explain_entries import _TutorExplainEntriesMixin
from .entry_tutor_question_entries import _TutorQuestionEntriesMixin
from .entry_tutor_answer_entries import _TutorAnswerEntriesMixin
from .entry_tutor_summary_entries import _TutorSummaryEntriesMixin
from .entry_document_analysis_jobs import _DocumentAnalysisJobsEntriesMixin
from .entry_ocr_entries import _OcrEntriesMixin
from .entry_neko_commands import (
    _INTERRUPT_COMMANDS,
    _NEKO_COMMAND_HANDLERS,
    _NekoCommandsMixin,
    _QUEUE_COMMANDS,
)
from .entry_notebook import _NotebookEntriesMixin


@neko_plugin
# MRO notes:
# - _TutorContextSupportMixin owns tutor finalization and learning tracking.
# - Tutor entry mixins call context/finalization helpers from that support mixin.
# Keep the support mixin before tutor entry mixins unless those helpers move.
class StudyCompanionPlugin(
    _StudyAvatarToolsMixin,
    _StudyCodeToolsMixin,
    _TutorContextSupportMixin,
    _CommunicationPomodoroEventsMixin,
    _CommunicationReviewEventsMixin,
    _CommunicationTutorEventsMixin,
    _ExportSupportMixin,
    _StatusEntriesMixin,
    _MemoryCardEntriesMixin,
    _MemoryDeckEntriesMixin,
    _MemoryImportEntriesMixin,
    _MemoryReviewEntriesMixin,
    _PomodoroEntriesMixin,
    _GoalEntriesMixin,
    _CheckinEntriesMixin,
    _SupervisionEntriesMixin,
    _KnowledgeEntriesMixin,
    _PracticeScopeEntriesMixin,
    _ModeEntriesMixin,
    _TutorExplainEntriesMixin,
    _TutorQuestionEntriesMixin,
    _TutorAnswerEntriesMixin,
    _TutorSummaryEntriesMixin,
    _DocumentAnalysisJobsEntriesMixin,
    _OcrEntriesMixin,
    _NotebookEntriesMixin,
    _NekoCommandsMixin,
    NekoPluginBase,
):
    def __init__(self, ctx):
        super().__init__(ctx)
        self.file_logger = self.enable_file_logging(log_level="INFO")
        self.logger = self.file_logger
        self._lock = asyncio.Lock()
        self._study_material_boot_id = uuid.uuid4().hex
        self._study_material_change_seq = 0
        self._study_material_output_targets = {}
        self._study_material_control_submission = []
        self._communication_settings_lock = asyncio.Lock()
        self._targeted_context_lock = threading.Lock()
        self._install_in_progress = False
        self._rapidocr_models_in_progress = False
        self._cfg = StudyConfig()
        self._state = build_initial_state(mode=MODE_COMPANION)
        self._store = StudyStore(
            self.data_path("study_companion.db"),
            self.config_dir / "data" / "study_seed.json",
            self.logger,
            Path(__file__).resolve().parent / "static" / "knowledge_graph_seed.json",
        )
        self._notebook_store = NotebookStore(self._store)
        self._ocr_pipeline: StudyOcrPipeline | None = None
        self._agent: TutorLLMAgent | None = None
        self._mode_manager = ModeManager()
        self._knowledge_tracker = KnowledgeTracker(
            self._store,
            retention_target=self._cfg.fsrs_retention_target,
            logger=self.logger,
        )
        self._memory_deck_store = MemoryDeckStore(
            self._store,
            retention_target=self._cfg.fsrs_retention_target,
        )
        self._knowledge_tracker.set_memory_deck_summary_provider(
            self._memory_deck_store.status_summary
        )
        self._habit_store: StudyHabitStore | None = None
        self._checkin_manager: CheckinManager | None = None
        self._pomodoro_timer: PomodoroTimer | None = None
        self._pomodoro_lock = asyncio.Lock()
        self._pomodoro_wakeup = asyncio.Event()
        self._pomodoro_watcher_task: asyncio.Task[None] | None = None
        self._pomodoro_session_id = ""
        self._pomodoro_target_lanlan: str | None = None
        self._supervision: SupervisionController | None = None
        self._memory_habit_bridge: MemoryHabitBridge | None = None
        self._event_bus: StudyEventBus | None = None
        self._buffer: ActivityBuffer | None = None
        self._awareness_task: asyncio.Task[None] | None = None
        self._last_awareness_push_at = 0.0
        self._awareness_idle_ticks = 0
        self._consecutive_os_read_failures = 0
        self._voice_filter = VoiceFilter(logger=self.logger)
        self._review_due_task: asyncio.Task[None] | None = None
        self._study_idle_task: asyncio.Task[None] | None = None
        self._review_due_payload_future: asyncio.Future[dict[str, Any]] | None = None
        self._command_queue: asyncio.Queue[tuple[str, dict[str, Any]]] = asyncio.Queue()
        self._command_worker_task: asyncio.Task[None] | None = None
        self._interruptible_task: asyncio.Task[None] | None = None
        self._neko_command_transport: Any | None = None
        self._neko_command_handler: Any | None = None
        self._neko_command_watcher: Any | None = None
        self._worker_crash_count = 0
        self._worker_last_crash_time = 0.0
        self._study_session_id = ""
        self._study_session_last_activity = 0.0
        self._study_session_lock = asyncio.Lock()

    @lifecycle(id="startup")
    async def startup(self, **_):
        try:
            raw = await self.config.dump(timeout=5.0)
            self._cfg = build_config(raw if isinstance(raw, dict) else {})
            self._voice_filter = VoiceFilter(
                plugin_config=raw if isinstance(raw, dict) else {},
                logger=self.logger,
            )
            await asyncio.to_thread(self._store.open)
            self._cfg = await asyncio.to_thread(self._store.load_config, self._cfg)
            self._study_config_default_language = str(self._cfg.language or "")
            self._knowledge_tracker = KnowledgeTracker(
                self._store,
                retention_target=self._cfg.fsrs_retention_target,
                logger=self.logger,
            )
            self._memory_deck_store = MemoryDeckStore(
                self._store,
                retention_target=self._cfg.fsrs_retention_target,
            )
            self._knowledge_tracker.set_memory_deck_summary_provider(
                self._memory_deck_store.status_summary
            )
            self._habit_store = StudyHabitStore(self._store)
            self._checkin_manager = CheckinManager(
                self._habit_store,
                makeup_window_days=self._cfg.checkin.makeup_window_days,
            )
            self._pomodoro_timer = PomodoroTimer(
                self._habit_store,
                config=self._cfg.pomodoro,
                auto_derive_from_session=self._cfg.checkin.auto_derive_from_session,
                checkin_timezone=self._cfg.checkin.streak_timezone,
            )
            self._supervision = SupervisionController(self._cfg.supervision)
            self._memory_habit_bridge = MemoryHabitBridge(
                store=self._store,
                memory=self._memory_deck_store,
                habits=self._habit_store,
                checkin_timezone=self._cfg.checkin.streak_timezone,
            )
            self._event_bus = (
                StudyEventBus(
                    plugin_ctx=self.ctx,
                    silent_mode=self._cfg.communication.silent_mode,
                    material_validator=self._narration_material_is_current,
                )
                if self._cfg.communication.enabled and not self._cfg.communication.silent_mode
                else None
            )
            restored = await asyncio.to_thread(
                self._store.load_state, build_initial_state(mode=self._cfg.mode)
            )
            await asyncio.to_thread(
                self._store.close_open_sessions,
                str(getattr(restored, "study_session_id", "") or ""),
            )
            async with self._lock:
                self._state = restored
                self._state.study_session_id = ""
                self._state.status = STATUS_READY
                self._state.active_mode = normalize_mode(
                    self._state.active_mode or self._cfg.mode
                )
                self._state.mode_started_at = float(self._state.mode_started_at or 0.0)
                self._state.mode_lock_until = float(self._state.mode_lock_until or 0.0)
                self._cfg.mode = self._state.active_mode
                self._state.last_started_at = utc_now_iso()
                self._state.last_error = ""
                self._mode_manager.restore(
                    {
                        "current_mode": self._state.active_mode,
                        "mode_started_at": self._state.mode_started_at,
                        "recent_mode_switches": self._state.recent_mode_switches,
                        "suggestion_cooldowns": self._state.suggestion_cooldowns,
                        "session_suggestions": self._state.session_suggestions,
                        "mode_lock_until": self._state.mode_lock_until,
                    }
                )
            self._study_session_id = ""
            # A process restart preserves the latest held question and grade,
            # including corrections committed after an older course checkpoint.
            self._state.current_question.pop("attempt_evaluation_pending", None)
            self._state.current_question.pop("attempt_evaluation_owner", None)
            await self._start_study_session(self._state.active_mode, resume_current_progress=True)
            self._start_study_idle_task()
            self._ocr_pipeline = StudyOcrPipeline(logger=self.logger, config=self._cfg)
            # Build the OCR runtime here, once, while nothing is asking the plugin for anything,
            # so a learner's first screen read never pays that import inside a worker thread.
            self._ocr_warmup = self._ocr_pipeline.warmup()
            self.logger.info(f"[Study] OCR runtime warm-up: {self._ocr_warmup}")
            self._agent = TutorLLMAgent(logger=self.logger, config=self._cfg)
            self._assert_notebook_agent_methods(self._agent)
            await self._refresh_dependency_status()
            self.register_static_ui("static")
            self.set_list_actions(
                [
                    {
                        "id": "open_ui",
                        "kind": "ui",
                        "target": f"/plugin/{quote(self.plugin_id, safe='')}/ui/",
                        "open_in": "new_tab",
                    }
                ]
            )
            self._sync_doc_export_entry()
            await self._persist_state()
            self._start_review_due_task()
            if self._event_bus is not None:
                await self._subscribe_neko_commands()
                self._start_command_worker()
            if self._cfg.awareness.enabled:
                self.start_awareness_loop()
            status_payload = await asyncio.to_thread(self._status_payload)
            return Ok({"status": STATUS_READY, "result": status_payload})
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self.logger.warning("study plugin startup failed: {}", exc)
            await self._cleanup_after_failed_startup()
            async with self._lock:
                self._state.status = STATUS_ERROR
                self._state.last_error = "startup_failed"
            return Err(SdkError("failed to start study_companion"))

    async def _cleanup_after_failed_startup(self) -> None:
        document_jobs = getattr(self, "_document_jobs", None)
        if document_jobs is not None:
            try:
                await document_jobs.shutdown()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.logger.warning(
                    "study startup cleanup document jobs failed: {}", exc
                )
        self.stop_awareness_loop()
        await self._await_awareness_stop()
        await self._unsubscribe_neko_commands()
        await self._cancel_command_worker()
        await self._cancel_review_due_task()
        await self._cancel_study_idle_task()
        await self._cancel_pomodoro_watcher()
        event_bus = self._event_bus
        agent = self._agent
        ocr_pipeline = self._ocr_pipeline
        self._agent = None
        self._ocr_pipeline = None
        self._knowledge_tracker = None
        self._memory_deck_store = None
        self._habit_store = None
        self._checkin_manager = None
        self._pomodoro_timer = None
        self._supervision = None
        self._memory_habit_bridge = None
        self._event_bus = None
        if event_bus is not None:
            try:
                await event_bus.stop_worker()
            except Exception as exc:
                self.logger.warning("study startup cleanup event bus failed: {}", exc)
        try:
            self.clear_list_actions()
        except Exception as exc:
            self.logger.warning("study startup cleanup clear actions failed: {}", exc)
        try:
            self.unregister_dynamic_entry("study_export_notes")
        except Exception as exc:
            self.logger.warning("study startup cleanup dynamic entry failed: {}", exc)
        try:
            self._static_ui_config = None
        except Exception as exc:
            self.logger.warning("study startup cleanup static UI failed: {}", exc)
        if agent is not None:
            try:
                await agent.shutdown()
            except Exception as exc:
                self.logger.warning(
                    "study startup cleanup agent shutdown failed: {}", exc
                )
        if ocr_pipeline is not None:
            try:
                close_ocr = getattr(ocr_pipeline, "close", None)
                if callable(close_ocr):
                    close_ocr()
            except Exception as exc:
                self.logger.warning("study startup cleanup OCR pipeline failed: {}", exc)
        try:
            await asyncio.to_thread(self._store.close)
        except Exception as exc:
            self.logger.warning("study startup cleanup store close failed: {}", exc)

    @lifecycle(id="shutdown")
    async def shutdown(self, **_):
        await self._cancel_study_idle_task()
        if self._study_session_id:
            try:
                await self._end_study_session()
            except Exception as exc:
                self.logger.warning("study session finalization failed: {}", exc)
        document_jobs = getattr(self, "_document_jobs", None)
        if document_jobs is not None:
            try:
                await document_jobs.shutdown()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.logger.warning(
                    "study shutdown document jobs cleanup failed: {}", exc
                )
        self.stop_awareness_loop()
        await self._await_awareness_stop()
        await self._unsubscribe_neko_commands()
        await self._cancel_command_worker()
        await self._cancel_review_due_task()
        await self._cancel_pomodoro_watcher()
        event_bus = self._event_bus
        self._event_bus = None
        if event_bus is not None:
            try:
                await event_bus.stop_worker()
            except Exception as exc:
                self.logger.warning("study shutdown event bus cleanup failed: {}", exc)
        try:
            self.unregister_dynamic_entry("study_export_notes")
        except Exception as exc:
            self.logger.warning("study shutdown dynamic entry cleanup failed: {}", exc)
        if self._agent is not None:
            await self._agent.shutdown()
        ocr_pipeline = self._ocr_pipeline
        self._ocr_pipeline = None
        if ocr_pipeline is not None:
            try:
                close_ocr = getattr(ocr_pipeline, "close", None)
                if callable(close_ocr):
                    close_ocr()
            except Exception as exc:
                self.logger.warning(
                    "study shutdown OCR pipeline cleanup failed: {}", exc
                )
        async with self._lock:
            self._state.status = STATUS_STOPPED
        await asyncio.to_thread(self._store.save_state, self._state)
        await asyncio.to_thread(self._store.close)
        return Ok({"status": STATUS_STOPPED})

    def _start_review_due_task(self) -> None:
        if self._event_bus is None:
            return
        if self._review_due_task is not None and not self._review_due_task.done():
            return
        self._review_due_task = asyncio.create_task(self._run_review_due_loop())
        self._review_due_task.add_done_callback(self._on_review_due_task_done)

    def _start_study_idle_task(self) -> None:
        if self._study_idle_task is not None and not self._study_idle_task.done():
            return
        self._study_idle_task = asyncio.create_task(self._run_study_session_idle_loop())
        self._study_idle_task.add_done_callback(self._on_study_idle_task_done)

    def _on_study_idle_task_done(self, task: asyncio.Task[None]) -> None:
        if self._study_idle_task is task:
            self._study_idle_task = None
        if task.cancelled():
            return
        try:
            task.result()
        except Exception as exc:
            self.logger.warning("study session idle task failed: {}", exc)

    async def _cancel_study_idle_task(self) -> None:
        task = self._study_idle_task
        self._study_idle_task = None
        if task is None or task.done():
            return
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    def start_awareness_loop(self) -> None:
        if self.is_awareness_active():
            return
        if self._ocr_pipeline is None:
            self.logger.warning("awareness loop skipped: OCR pipeline not initialized")
            return
        self._buffer = ActivityBuffer(
            window_seconds=self._cfg.awareness.context_window_minutes * 60,
            snapshot_interval=self._cfg.awareness.snapshot_interval_seconds,
        )
        self._last_awareness_push_at = (
            time.monotonic() - float(self._cfg.awareness.push_to_llm_interval_seconds)
        )
        self._awareness_idle_ticks = 0
        self._consecutive_os_read_failures = 0
        self._awareness_task = asyncio.create_task(self._run_awareness_loop())
        self._awareness_task.add_done_callback(self._on_awareness_task_done)

    def stop_awareness_loop(self) -> None:
        task = self._awareness_task
        self._buffer = None
        self._last_awareness_push_at = 0.0
        self._awareness_idle_ticks = 0
        self._consecutive_os_read_failures = 0
        if task is not None and not task.done():
            task.cancel()

    async def _await_awareness_stop(self) -> None:
        task = self._awareness_task
        self._awareness_task = None
        if task is None:
            return
        try:
            await task
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            self.logger.warning("study awareness task cleanup failed: {}", exc)

    def is_awareness_active(self) -> bool:
        task = self._awareness_task
        return self._buffer is not None and task is not None and not task.done()

    def _start_command_worker(self) -> None:
        if self._event_bus is None:
            return
        if self._command_worker_task is not None and not self._command_worker_task.done():
            return
        if self._worker_crash_count >= 3:
            now = time.monotonic()
            if now - self._worker_last_crash_time < 10.0:
                self.logger.error(
                    "_command_worker auto-restart disabled after {} crashes",
                    self._worker_crash_count,
                )
                return
            self._worker_crash_count = 0
        self._command_worker_task = asyncio.create_task(self._run_command_worker())
        self._command_worker_task.add_done_callback(self._on_command_worker_done)

    async def _cancel_command_worker(self) -> None:
        worker = self._command_worker_task
        self._command_worker_task = None
        if worker is not None and not worker.done():
            worker.cancel()
            try:
                await worker
            except asyncio.CancelledError:
                pass
            except Exception as exc:
                self.logger.warning("study command worker cleanup failed: {}", exc)

        while True:
            try:
                self._command_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

        task = self._interruptible_task
        self._interruptible_task = None
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception as exc:
                self.logger.warning("study command task cleanup failed: {}", exc)

    def _on_command_worker_done(self, task: asyncio.Task[None]) -> None:
        if self._command_worker_task is task:
            self._command_worker_task = None
        if task.cancelled():
            return
        try:
            task.result()
        except asyncio.CancelledError:
            return
        except Exception:
            self.logger.exception("_command_worker exited with error")
            now = time.monotonic()
            if now - self._worker_last_crash_time < 10.0:
                self._worker_crash_count += 1
            else:
                self._worker_crash_count = 1
            self._worker_last_crash_time = now
            if self._worker_crash_count >= 3:
                self.logger.error(
                    "_command_worker crashed {} times in 10s; disabling auto-restart",
                    self._worker_crash_count,
                )

    def _on_command_task_done(self, task: asyncio.Task[None]) -> None:
        if self._interruptible_task is task:
            self._interruptible_task = None
        if task.cancelled():
            return
        try:
            task.result()
        except asyncio.CancelledError:
            return
        except Exception:
            self.logger.exception("command task failed")

    async def _run_command_worker(self) -> None:
        while True:
            try:
                cmd, payload = await self._command_queue.get()
            except asyncio.CancelledError:
                while True:
                    try:
                        self._command_queue.get_nowait()
                    except asyncio.QueueEmpty:
                        break
                raise

            try:
                await self._execute_command(cmd, payload)
            except asyncio.CancelledError:
                raise
            except Exception:
                self.logger.exception("_command_worker failed to execute: {}", cmd)

    async def _execute_command(self, cmd: str, payload: dict[str, Any]) -> None:
        if cmd not in _QUEUE_COMMANDS or cmd in _INTERRUPT_COMMANDS:
            return
        handler_name = _NEKO_COMMAND_HANDLERS.get(cmd)
        handler = getattr(self, handler_name or "", None)
        if handler is None:
            return

        worker_task = asyncio.current_task()
        while True:
            current = self._interruptible_task
            if current is None or current.done():
                break
            try:
                await current
                if worker_task is not None and worker_task.cancelling():
                    raise asyncio.CancelledError
            except asyncio.CancelledError:
                if worker_task is not None and worker_task.cancelling():
                    raise
            except Exception:
                pass

        async def _run() -> None:
            try:
                await handler(payload)
            except asyncio.CancelledError:
                pass

        task = asyncio.create_task(_run())
        self._interruptible_task = task
        task.add_done_callback(self._on_command_task_done)
        try:
            await task
            if worker_task is not None and worker_task.cancelling():
                raise asyncio.CancelledError
        except asyncio.CancelledError:
            if worker_task is not None and worker_task.cancelling():
                raise
        except Exception:
            pass

    async def _cancel_review_due_task(self) -> None:
        task = self._review_due_task
        self._review_due_task = None
        if task is None:
            return
        if task.done():
            try:
                task.result()
            except asyncio.CancelledError:
                return
            except Exception as exc:
                self.logger.warning("study review due task cleanup failed: {}", exc)
            return
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            self.logger.warning("study review due task cleanup failed: {}", exc)
        await self._await_review_due_payload_future()

    async def _await_review_due_payload_future(self) -> None:
        future = self._review_due_payload_future
        if future is None:
            return
        try:
            await asyncio.shield(future)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self.logger.warning("study review due payload cleanup failed: {}", exc)
        finally:
            if self._review_due_payload_future is future:
                self._review_due_payload_future = None

    async def _start_study_session(self, mode: str | None = None, *, resume_pending_question: bool = False, resume_current_progress: bool = False) -> str:
        async with self._study_session_lock:
            return await self._start_study_session_locked(mode, resume_pending_question=resume_pending_question,
                                                         resume_current_progress=resume_current_progress)

    async def _start_study_session_locked(self, mode: str | None = None, course_id: str = "", *, resume_pending_question: bool = False, resume_course_progress: bool = False, resume_current_progress: bool = False) -> str:
        session_id = f"study-{uuid.uuid4().hex}"
        selected_mode = str(mode or self._state.active_mode or self._cfg.mode)
        selected_course = str(course_id or self._state.study_course_id or "general").strip()
        await asyncio.to_thread(
            self._store.ensure_session, session_id=session_id, mode=selected_mode,
            course_id=selected_course,
        )
        material = await asyncio.to_thread(load_material, self._store, selected_course)
        progress = (await asyncio.to_thread(self._store.load_course_progress, selected_course)
                    if resume_course_progress else {})
        async with self._lock:
            before_material = material_context(self)
            if resume_current_progress and self._state.study_course_id == selected_course:
                # Persisted live state is newer than a retry/course checkpoint.
                # Empty live state is authoritative too: do not revive a quiz
                # the learner explicitly retired with a fresh session.
                progress = {name: getattr(self._state, name) for name in (
                    "current_question", "last_answer_evaluation",
                    "last_question_at", "last_answer_evaluated_at")}
            pending_question = dict(self._state.current_question)
            if not (resume_pending_question and self._state.study_course_id == selected_course
                    and pending_question.get("question_id") and pending_question.get("attempt_id")
                    and not pending_question.get("attempt_evaluated")):
                pending_question = {}
            if progress:
                saved_question = progress.get("current_question")
                if (isinstance(saved_question, dict) and saved_question.get("question_id")
                        and saved_question.get("attempt_id")):
                    pending_question = dict(saved_question)
            # A reservation from the departed session cannot remain live, also
            # when the same course resumes after an idle-session rollover.
            pending_question.pop("attempt_evaluation_pending", None)
            pending_question.pop("attempt_evaluation_owner", None)
            if self._state.study_course_id != selected_course:
                self._state.active_practice_scope = {}
                self._state.practice_scope_revision += 1
            self._study_session_id = session_id
            self._study_session_last_activity = time.time()
            self._state.study_session_id = session_id
            self._state.study_course_id = selected_course
            self._study_effective_language()
            self._state.session_summary_seed = {}
            self._state.recent_learning_events = []
            self._state.current_question = pending_question
            evaluation = progress.get("last_answer_evaluation")
            self._state.last_answer_evaluation = (dict(evaluation)
                if pending_question and isinstance(evaluation, dict) else {})
            self._state.last_question_at = (str(progress.get("last_question_at") or "")
                if progress and pending_question else self._state.last_question_at if pending_question else "")
            self._state.last_answer_evaluated_at = (str(progress.get("last_answer_evaluated_at") or "")
                if self._state.last_answer_evaluation else "")
            self._state.last_ocr_text = str(material.get("text") or "")
            self._state.last_vision_image_base64 = str(material.get("image") or "")
            self._state.last_ocr_at = ""
            self._state.last_session_summary = ""
            self._state.last_session_summary_at = ""
            if getattr(self, "_ocr_pipeline", None) is not None:
                self._ocr_pipeline._clear_vision_snapshot()
            material_notifications = material_changes(self, before_material, "session_started")
        await submit_material_changes(self, material_notifications)
        # Selecting a saved course resumes its artifact; an explicit fresh start
        # replaces that course's checkpoint, so it cannot resurrect an old quiz.
        await asyncio.to_thread(self._store.save_course_progress, self._state.to_dict())
        await self._persist_state()
        return session_id

    async def _end_study_session(self) -> str:
        async with self._study_session_lock:
            return await self._end_study_session_locked()

    async def _end_study_session_locked(self) -> str:
        session_id = self._study_session_id
        if session_id:
            await asyncio.to_thread(
                self._store.end_session,
                session_id=session_id,
                summary=self._state.last_session_summary,
            )
        async with self._lock:
            await asyncio.to_thread(self._store.save_course_progress, self._state.to_dict())
            before_material = material_context(self)
            self._study_session_id = ""
            self._study_session_last_activity = 0.0
            self._state.study_session_id = ""
            material_notifications = material_changes(self, before_material, "session_ended")
        await submit_material_changes(self, material_notifications)
        await self._persist_state()
        return session_id

    async def _restart_study_session(self, mode: str | None = None, course_id: str = "", *, resume_course_progress: bool = False) -> str:
        async with self._study_session_lock:
            if self._study_session_id:
                await self._end_study_session_locked()
            return await self._start_study_session_locked(mode, course_id=course_id,
                                                         resume_course_progress=resume_course_progress)

    async def _ensure_active_study_session(self) -> str:
        async with self._study_session_lock:
            now = time.time()
            if (
                self._study_session_id
                and self._study_session_last_activity
                and now - self._study_session_last_activity >= 30 * 60
            ):
                await self._end_study_session_locked()
            if not self._study_session_id:
                return await self._start_study_session_locked(resume_current_progress=True)
            self._study_session_last_activity = now
            return self._study_session_id

    def _on_review_due_task_done(self, task: asyncio.Task[None]) -> None:
        if self._review_due_task is task:
            self._review_due_task = None
        if task.cancelled():
            return
        try:
            task.result()
        except Exception as exc:
            self.logger.warning("study review due task failed: {}", exc)

    def _on_awareness_task_done(self, task: asyncio.Task[None]) -> None:
        if self._awareness_task is task:
            self._awareness_task = None
        if task.cancelled():
            return
        try:
            task.result()
        except Exception as exc:
            self._buffer = None
            self.logger.warning("study awareness task failed: {}", exc)

    async def _run_review_due_loop(self) -> None:
        while True:
            await self._emit_review_due_if_needed()
            await asyncio.sleep(max(0.0, _REVIEW_DUE_INTERVAL_SECONDS))

    async def _run_study_session_idle_loop(self) -> None:
        while True:
            await asyncio.sleep(60.0)
            if (
                self._study_session_id
                and self._study_session_last_activity
                and time.time() - self._study_session_last_activity >= 30 * 60
            ):
                await self._end_study_session()

    async def _run_awareness_loop(self) -> None:
        while self._buffer is not None:
            try:
                await self.awareness_tick()
            except Exception as exc:
                self._awareness_last_error_type = type(exc).__name__
                self.logger.warning("study awareness tick failed: {}", type(exc).__name__)
            else:
                self._awareness_tick_count = getattr(self, "_awareness_tick_count", 0) + 1
                self._awareness_last_tick_at = time.time()
                self._awareness_last_error_type = ""
            await asyncio.sleep(self._awareness_sleep_seconds())

    def _awareness_sleep_seconds(self) -> float:
        base = max(1.0, float(self._cfg.awareness.snapshot_interval_seconds))
        if self._awareness_idle_ticks >= 3:
            return max(base, 15.0)
        return base

    async def _read_awareness_activity_snapshot(
        self,
        *,
        now: float,
    ) -> OsActivitySnapshot | None:
        if not self._cfg.awareness.os_signals_enabled:
            return None
        return await asyncio.wait_for(
            get_os_activity_snapshot(self.plugin_id, now=now),
            timeout=_AWARENESS_OS_TIMEOUT_SECONDS,
        )

    async def _read_awareness_os_activity(self, *, now: float):
        activity_snap = None
        foreground_category = None
        os_signals_available = False
        if not self._cfg.awareness.os_signals_enabled:
            return activity_snap, foreground_category, os_signals_available
        try:
            activity_snap = await self._read_awareness_activity_snapshot(now=now)
            os_signals_available = activity_snap is not None and activity_snap.os_signals_available
            if os_signals_available:
                foreground_category = activity_snap.foreground_category
        except Exception:
            fails = self._consecutive_os_read_failures + 1
            self._consecutive_os_read_failures = fails
            log = self.logger.warning if fails <= 3 else self.logger.error
            log(
                "study awareness activity snapshot failed (consecutive={})",
                fails,
                exc_info=True,
            )
        else:
            self._consecutive_os_read_failures = 0
        return activity_snap, foreground_category, os_signals_available

    async def _record_private_awareness_activity(
        self,
        buffer: ActivityBuffer,
        *,
        timestamp: float,
    ) -> None:
        await buffer.add(
            ActivitySnapshot(
                timestamp=timestamp,
                first_seen_at=timestamp,
                app_type="private",
                activity_type="private",
                classify_method="os_signal",
                ocr_text_snippet="",
                window_title="",
                has_content_change=False,
            )
        )
        self._awareness_idle_ticks += 1

    async def _capture_awareness_lightweight(self, pipeline: Any):
        try:
            return await asyncio.to_thread(pipeline.capture_lightweight)
        except Exception:
            self.logger.warning("awareness_tick capture failed", exc_info=True)
            return None

    @staticmethod
    def _classify_awareness_snapshot(snapshot: Any, foreground_category: str | None):
        if not hasattr(snapshot, "app_type"):
            return snapshot
        mapped = _OS_CATEGORY_TO_APP_TYPE.get(str(foreground_category or ""))
        if mapped is not None:
            return replace(snapshot, app_type=mapped)
        if getattr(snapshot, "app_type", "") != "unknown":
            return snapshot
        return replace(
            snapshot,
            app_type=classify_app_from_title(
                getattr(snapshot, "window_title", ""),
                default="unknown",
            ),
        )

    def _observe_awareness_supervision(
        self,
        snapshot: Any,
        *,
        activity_snap: Any | None,
        os_signals_available: bool,
        foreground_category: str | None,
    ) -> None:
        if self._supervision is None:
            return
        supervision_category = foreground_category
        if supervision_category == "own_app" or not self._cfg.awareness.distraction_detection:
            supervision_category = None
        self._supervision.observe_activity(
            ocr_text=getattr(snapshot, "ocr_text_snippet", ""),
            sensor_available=getattr(snapshot, "status", "") in {"ok", "empty"},
            idle_seconds=(
                getattr(activity_snap, "system_idle_seconds", None)
                if activity_snap is not None and os_signals_available
                else None
            ),
            foreground_category=supervision_category,
        )

    async def _record_awareness_snapshot(
        self,
        buffer: ActivityBuffer,
        snapshot: Any,
    ) -> None:
        activity = snapshot.to_activity_snapshot()
        if activity is None:
            self._awareness_idle_ticks += 1
            return
        await buffer.add(activity)
        self._awareness_capture_count = getattr(self, "_awareness_capture_count", 0) + 1
        self._awareness_last_observation = {
            "app_type": activity.app_type,
            "activity_type": activity.activity_type,
            "classify_method": activity.classify_method,
            "window_title_available": bool(activity.window_title.strip()),
        }
        if activity.app_type in ("other", "unknown") and activity.activity_type in (
            "idle",
            "",
        ):
            self._awareness_idle_ticks += 1
        else:
            self._awareness_idle_ticks = 0

    async def awareness_tick(self) -> None:
        buffer = self._buffer
        pipeline = self._ocr_pipeline
        if buffer is None or pipeline is None:
            return

        ts = time.time()
        activity_snap, foreground_category, os_signals_available = (
            await self._read_awareness_os_activity(now=ts)
        )
        if activity_snap is not None and (
            getattr(activity_snap, "privacy_state", "") == "private"
            or foreground_category == "private"
        ):
            await self._record_private_awareness_activity(buffer, timestamp=ts)
            return

        snapshot = await self._capture_awareness_lightweight(pipeline)

        if snapshot is None or snapshot.status == "capture_failed":
            self._awareness_idle_ticks += 1
            return

        snapshot = self._classify_awareness_snapshot(snapshot, foreground_category)
        self._observe_awareness_supervision(
            snapshot,
            activity_snap=activity_snap,
            os_signals_available=os_signals_available,
            foreground_category=foreground_category,
        )
        await self._record_awareness_snapshot(buffer, snapshot)

        if self._should_push_context():
            summary = await buffer.summarize()
            await self._push_awareness_context(summary)

    def _should_push_context(self) -> bool:
        if self._cfg.awareness.push_to_llm_mode == "blind":
            return False
        interval = self._cfg.awareness.push_to_llm_interval_seconds
        now = time.monotonic()
        return now - self._last_awareness_push_at >= interval

    async def _push_awareness_context(self, summary: ActivitySummary) -> None:
        if self._cfg.communication.silent_mode:
            return
        mode = self._cfg.awareness.push_to_llm_mode
        try:
            # A local submission before the plane starts can be silently lost.
            # Bound readiness and retry on a later tick instead of advancing
            # the success clock while the message components are unavailable.
            await asyncio.wait_for(
                self.ctx.bus.messages.get(plugin_id=self.plugin_id, max_count=1),
                timeout=_AWARENESS_OS_TIMEOUT_SECONDS,
            )
        except Exception as exc:
            self._awareness_push_status = "message_plane_unavailable"
            self.logger.warning("study awareness delivery unavailable: {}", type(exc).__name__)
            return
        try:
            result = self.push_message(
                visibility=[],
                ai_behavior="read" if mode == "read" else "respond",
                parts=[
                    {
                        "type": "text",
                        "text": (
                            "[环境感知] "
                            + json.dumps(
                                self._summary_for_llm(summary),
                                ensure_ascii=False,
                            )
                        ),
                    }
                ],
                source="awareness",
                coalesce_key="study-awareness",
                priority=0,
            )
            if isinstance(result, dict) and (result.get("submitted") is False or result.get("ok") is False):
                self.logger.warning("study awareness context was not submitted")
                self._awareness_push_status = "rejected"
                return
        except Exception:
            self.logger.warning("study awareness context push failed", exc_info=True)
            return
        self._last_awareness_push_at = time.monotonic()
        self._awareness_push_status = "submitted" if isinstance(result, dict) and result.get("submitted") is True else "submission_unknown"

    @staticmethod
    def _summary_for_llm(
        summary: ActivitySummary,
    ) -> dict[str, str | float | list[str]]:
        return {
            key: value
            for key, value in summary.items()
            if key != "app_distribution"
        }

    @staticmethod
    def _assert_notebook_agent_methods(agent: TutorLLMAgent | None) -> None:
        if agent is None:
            raise RuntimeError("study tutor agent is not initialized")
        missing = [
            name
            for name in ("expand_note", "summarize_to_note")
            if not callable(getattr(agent, name, None))
        ]
        if missing:
            raise RuntimeError(
                f"study tutor agent missing notebook methods: {', '.join(missing)}"
            )

    async def _refresh_dependency_status(self) -> dict[str, Any]:
        status = await asyncio.to_thread(build_dependency_status, self._cfg)
        async with self._lock:
            self._state.dependency_status = status
        return status

    async def _persist_state(self) -> None:
        await asyncio.to_thread(self._store.save_config, self._cfg)
        await asyncio.to_thread(self._store.save_state, self._state)

    async def _apply_mode_switch(
        self, mode: str, reason: str, *, language: str | None = None
    ) -> dict[str, Any]:
        async with self._lock:
            self._mode_manager.restore(
                {
                    "current_mode": self._state.active_mode,
                    "mode_started_at": self._state.mode_started_at,
                    "recent_mode_switches": self._state.recent_mode_switches,
                    "suggestion_cooldowns": self._state.suggestion_cooldowns,
                    "session_suggestions": self._state.session_suggestions,
                    "mode_lock_until": self._state.mode_lock_until,
                }
            )
            result = self._mode_manager.switch_to(
                mode, reason, language=language or self._cfg.language
            )
            checkpoint = (
                result.get("checkpoint")
                if isinstance(result.get("checkpoint"), dict)
                else {}
            )
            self._state.active_mode = str(
                result.get("new_mode") or self._state.active_mode
            )
            if "mode_started_at" in checkpoint:
                self._state.mode_started_at = float(
                    checkpoint.get("mode_started_at") or 0.0
                )
            if isinstance(checkpoint.get("recent_mode_switches"), list):
                self._state.recent_mode_switches = checkpoint.get(
                    "recent_mode_switches"
                )
            if isinstance(checkpoint.get("suggestion_cooldowns"), dict):
                self._state.suggestion_cooldowns = checkpoint.get(
                    "suggestion_cooldowns"
                )
            if isinstance(checkpoint.get("session_suggestions"), list):
                self._state.session_suggestions = checkpoint.get("session_suggestions")
            if "mode_lock_until" in checkpoint:
                self._state.mode_lock_until = float(
                    checkpoint.get("mode_lock_until") or 0.0
                )
            self._state.checkpoint = {
                **checkpoint,
                "changed": bool(result.get("changed")),
                "old_mode": result.get("old_mode"),
                "new_mode": result.get("new_mode"),
                "reason": result.get("reason"),
                "transition_phrase": result.get("transition_phrase"),
                "locked": bool(result.get("locked")),
                "lock_reason": result.get("lock_reason"),
                "lock_until": float(result.get("lock_until") or 0.0),
            }
            if result.get("changed"):
                self._cfg.mode = self._state.active_mode
        if result.get("changed") and self._agent is not None:
            self._agent.update_config(self._cfg)
        await self._persist_state()
        return result

    def _status_payload(self) -> dict[str, Any]:
        history = self._store.list_interactions(limit=10)
        is_first_run = not bool(self._store.list_interactions(limit=1))
        today = self._today()
        habit_payload = self._habit_status_payload(today)
        knowledge = {
            "knowledge_summary": self._knowledge_tracker.get_status_summary(limit=8),
            "knowledge_quality_summary": self._knowledge_tracker.quality.status_summary(
                limit=8
            ),
            "anonymous_knowledge_stats_summary": self._store.anonymous_knowledge_stats_summary(),
            "review_queue": self._knowledge_tracker.get_review_queue(limit=8),
            "memory_deck": self._memory_deck_store.status_summary(limit=8),
            "weak_topics": self._knowledge_tracker.get_weak_topics(limit=8),
            "mastery_overview": self._store.list_mastery_overview(limit=8),
        }
        payload = build_status_payload(
            config=self._cfg,
            state=self._state,
            history=history,
            knowledge={**knowledge, "habit": habit_payload},
            is_first_run=is_first_run,
        )
        payload["awareness_runtime"] = {
            "active": self.is_awareness_active(),
            "completed_ticks": getattr(self, "_awareness_tick_count", 0),
            "captured_observations": getattr(self, "_awareness_capture_count", 0),
            "last_tick_at": getattr(self, "_awareness_last_tick_at", 0.0),
            "last_error_type": getattr(self, "_awareness_last_error_type", ""),
            "last_observation": getattr(self, "_awareness_last_observation", None),
            "push_status": getattr(self, "_awareness_push_status", "not_attempted"),
        }
        return payload

    def _habit_status_payload(self, today: str) -> dict[str, Any]:
        if (
            self._habit_store is None
            or self._checkin_manager is None
            or self._pomodoro_timer is None
        ):
            return {
                "available": False,
                "error": "study habit system is not initialized",
            }
        try:
            payload = build_habit_dashboard_payload(
                goals=self._habit_store.list_goals(date=today),
                checkin=self._checkin_manager.checkin_status(date=today, today=today),
                pomodoro=self._pomodoro_timer.status(),
                summary=self._checkin_manager.daily_summary(date=today),
                supervision=self._supervision.status()
                if self._supervision is not None
                else {},
            )
            if self._memory_habit_bridge is not None:
                payload["summary"]["memory_summary"] = (
                    self._memory_habit_bridge.memory_summary(date=today)
                )
            payload["available"] = True
            return payload
        except Exception as exc:
            self.logger.warning("study habit status payload degraded: {}", exc)
            return {"available": False, "error": str(exc)}

    def _today(self) -> str:
        timezone_name = str(self._cfg.checkin.streak_timezone or "local").strip()
        if timezone_name and timezone_name.lower() != "local":
            try:
                return datetime.now(ZoneInfo(timezone_name)).date().isoformat()
            except ZoneInfoNotFoundError:
                self.logger.warning(
                    "invalid study checkin timezone configured: {}",
                    timezone_name[:64],
                )
        return datetime.now().astimezone().date().isoformat()

    def _state_snapshot(self) -> dict[str, Any]:
        return self._state.to_dict()

    def _screen_classification_context(self) -> dict[str, Any]:
        return dict(self._state.last_screen_classification)

    @custom_event(
        event_type=VOICE_TRANSCRIPT_EVENT_TYPE,
        id=VOICE_TRANSCRIPT_EVENT_ID,
        name="Handle study voice transcript",
        description="Filter realtime study voice transcripts and return a voice-session action.",
        input_schema={
            "type": "object",
            "properties": {
                "transcript": {"type": "string"},
                "lanlan_name": {"type": "string"},
                "metadata": {"type": "object"},
            },
            "required": ["transcript"],
        },
        trigger_method="manual",
    )
    async def handle_voice_transcript(
        self,
        transcript: str = "",
        lanlan_name: str = "",
        metadata: dict[str, Any] | None = None,
        **_,
    ):
        def voice_noop(reason: str, filter_result: Mapping[str, Any] | None = None):
            filter_payload = dict(filter_result or {})
            original_method = str(filter_payload.get("method") or "")
            if original_method and original_method != reason:
                filter_payload["source_method"] = original_method
            filter_payload["method"] = reason
            return Ok(
                voice_transcript_noop(
                    reason,
                    filter=filter_payload,
                )
            )

        text = str(transcript or "").strip()
        if not text:
            return voice_noop("empty_transcript")
        metadata_payload = metadata if isinstance(metadata, dict) else {}
        session_key = _voice_session_key(lanlan_name, metadata_payload)

        async with self._lock:
            if self._state.status != STATUS_READY:
                return voice_noop("not_ready")
            state_snapshot_payload = self._state.to_dict()

        # Voice filtering only needs a point-in-time view; avoid holding the
        # plugin lock while building OCR context or applying filter rules.
        screen_text = str(state_snapshot_payload.get("last_ocr_text") or "")
        screen_classification = (
            state_snapshot_payload.get("last_screen_classification")
            if isinstance(
                state_snapshot_payload.get("last_screen_classification"), dict
            )
            else {}
        )
        screen_type = str(screen_classification.get("screen_type") or "")
        session_seed = (
            state_snapshot_payload.get("session_summary_seed")
            if isinstance(state_snapshot_payload.get("session_summary_seed"), dict)
            else {}
        )
        screen_context = {
            "topic": str(session_seed.get("last_topic") or "").strip(),
            "subject": _derive_subject(screen_text),
        }
        filter_result = self._voice_filter.filter(
            text,
            screen_text=screen_text,
            screen_type=screen_type,
            subject=screen_context["subject"],
            session_key=session_key,
            extra_names=[lanlan_name],
        )
        if filter_result is None:
            return voice_noop("not_matched")
        if not bool(filter_result.get("should_relay")):
            return Ok(
                voice_transcript_cancel_response(
                    filter_payload=filter_result,
                )
            )

        state_snapshot = SimpleNamespace(**state_snapshot_payload)
        context_text = build_context_for_catgirl(
            text,
            state_snapshot,
            screen_context,
            filter_result,
        ).strip()
        if not context_text:
            return voice_noop("empty_context", filter_result)
        return Ok(
            voice_transcript_prime_context(
                context_text,
                skipped=True,
                filter_payload=filter_result,
                lanlan_name=str(lanlan_name or ""),
            )
        )

    async def _update_screen_classification(
        self, text: str, *, window_title: str = "", update_empty: bool = True
    ) -> dict[str, Any]:
        normalized = str(text or "").strip()
        async with self._lock:
            if not normalized and not update_empty:
                return dict(self._state.last_screen_classification)
            recent = list(self._state.recent_screen_classifications)
            previous = dict(self._state.last_screen_classification)
            classification = classify_screen_from_ocr(
                normalized, window_title=window_title, recent_classifications=recent
            )
            payload = classification.to_payload()
            if normalized or update_empty:
                self._state.last_screen_classification = payload
                recent_classifications = list(self._state.recent_screen_classifications)
                recent_classifications.append(payload)
                self._state.recent_screen_classifications = recent_classifications[-8:]
                self._state.session_summary_seed = self._merge_session_summary_seed(
                    "screen_classification",
                    payload=payload,
                    seed=self._state.session_summary_seed,
                )
            previous_type = str(previous.get("screen_type") or "").strip()
            new_type = str(payload.get("screen_type") or "").strip()
            if (
                self._event_bus is not None
                and self._event_bus.should_schedule_screen_context(
                    new_type, previous_type
                )
            ):
                self._event_bus.schedule_emit(
                    StudyEvent(
                        name="screen_context_changed",
                        payload={
                            "screen_type": new_type,
                            "confidence": payload.get("confidence", 0.0),
                            "ocr_summary": normalized[:200],
                            "previous_type": previous_type,
                        },
                    )
                )
        return payload

    def _resolve_current_run_id(self, extra_args: dict[str, Any] | None = None) -> str:
        if isinstance(extra_args, dict):
            direct = str(extra_args.get("run_id") or "").strip()
            if direct:
                return direct
        current = str(getattr(self.ctx, "run_id", "") or "").strip()
        if current:
            return current
        if isinstance(extra_args, dict):
            ctx_obj = extra_args.get("_ctx")
            if isinstance(ctx_obj, dict):
                return str(ctx_obj.get("run_id") or "").strip()
        return ""

    def _resolve_install_progress_callback(self, current_run_id: str):
        async def _progress_update(event: dict[str, Any]) -> None:
            if not current_run_id:
                return
            try:
                await self.run_update(
                    run_id=current_run_id,
                    progress=float(event.get("progress") or 0.0),
                    stage=str(event.get("phase") or ""),
                    message=str(event.get("message") or ""),
                    metrics={
                        "phase": str(event.get("phase") or ""),
                        "downloaded_bytes": int(event.get("downloaded_bytes") or 0),
                        "total_bytes": int(event.get("total_bytes") or 0),
                        "resume_from": int(event.get("resume_from") or 0),
                        "asset_name": str(event.get("asset_name") or ""),
                        "release_name": str(event.get("release_name") or ""),
                    },
                )
            except Exception as exc:
                self.logger.warning("study install progress run_update failed: {}", exc)

        return _progress_update

    def _require_habit_components(
        self,
    ) -> tuple[StudyHabitStore, CheckinManager, PomodoroTimer, SupervisionController]:
        if (
            self._habit_store is None
            or self._checkin_manager is None
            or self._pomodoro_timer is None
            or self._supervision is None
        ):
            raise RuntimeError("study habit system is not initialized")
        return (
            self._habit_store,
            self._checkin_manager,
            self._pomodoro_timer,
            self._supervision,
        )

    def _require_memory_habit_bridge(self) -> MemoryHabitBridge:
        if self._memory_habit_bridge is None:
            raise RuntimeError("memory habit bridge is not initialized")
        return self._memory_habit_bridge


StudyCompanionBridgePlugin = StudyCompanionPlugin
