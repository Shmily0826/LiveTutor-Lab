"""Actual local producer/event bus/material helpers; no host, SDK calls or audio."""
import ast
import asyncio
from copy import deepcopy
import importlib
import math
from pathlib import Path
import sys
import types
from typing import Any
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "patches/neko-study-2026-10-10-product/payload/study_companion"
BASE = ROOT / "benchmarks/raw/neko-app/resources/bin/plugins/study_companion"
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "candidates/N.E.K.O"))
package = types.ModuleType("_narration_guard_product")
package.__path__ = [str(SOURCE), str(BASE)]
sys.modules[package.__name__] = package
bus_module = importlib.import_module(package.__name__ + "._event_bus")
materials = importlib.import_module(package.__name__ + ".study_materials")
scope = {"Any": Any, "asyncio": asyncio, "math": math, "deepcopy": deepcopy,
         "StudyEvent": bus_module.StudyEvent,
         "_NARRATION_ORIGIN_KEY": bus_module._NARRATION_ORIGIN_KEY,
         "_valid_narration_origin": bus_module._valid_narration_origin,
         "bind_material_output": materials.bind_material_output,
         "material_context_current": materials.material_context_current}
common = ast.parse((BASE / "entry_common.py").read_text(encoding="utf-8"))
utilities = [node for node in common.body if getattr(node, "name", "") in
             {"_event_ratio", "_event_nonnegative_float"}]
exec(compile(ast.Module(body=utilities, type_ignores=[]), "actual entry_common helpers", "exec"), scope)
entry = ast.parse((SOURCE / "entry_communication_tutor_events.py").read_text(encoding="utf-8"))
entry_class = next(node for node in entry.body if isinstance(node, ast.ClassDef))
exec(compile(ast.Module(body=[entry_class], type_ignores=[]), "actual communication mixin", "exec"), scope)


class Sink:
    def __init__(self):
        self.messages = []

    def push_message(self, **fields):
        self.messages.append(deepcopy(fields))
        return {"ok": True}


class Harness(scope["_CommunicationTutorEventsMixin"]):
    def __init__(self):
        self._state = types.SimpleNamespace(study_course_id="course-A", last_vision_image_base64="old-image",
            last_ocr_text="old OCR", session_summary_seed={"answer_count": 99, "last_topic": "wrong live seed"})
        self._study_session_id = "session-A"
        self._study_material_boot_id = "a" * 32
        self._study_material_change_seq = 0
        self._study_material_output_targets = {}
        self._lock = asyncio.Lock()
        self.sink = Sink()
        self._event_bus = bus_module.StudyEventBus(plugin_ctx=self.sink, silent_mode=False,
                                                  material_validator=self._narration_material_is_current)

    def payload(self):
        return {"summary": "original session explanation", "_narration_target_lanlan": "LearnerRole",
            "_material_context": materials.material_context(self, include_material=False),
            "_session_summary_seed": {"answer_count": 2, "verdict_counts": {"correct": 1, "wrong": 1},
                                      "last_topic": "original topic"}}

    def event(self):
        origin = materials.bind_material_output(self, materials.material_context(self, include_material=False), "LearnerRole")
        origin["event"] = "session_summarized"
        return bus_module.StudyEvent("session_summarized", {
            bus_module._NARRATION_ORIGIN_KEY: origin, "target_lanlan": "LearnerRole", "key_insight": "original insight"})

    def replace_course(self):
        self._state.study_course_id = "course-B"
        self._study_session_id = "session-B"
        self._study_material_change_seq += 1


class NarrationGuard(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.h = Harness()
        self.bus = self.h._event_bus

    async def asyncTearDown(self):
        await self.bus.close()

    async def joined(self):
        await asyncio.wait_for(self.bus._queue.join(), timeout=2)

    async def test_summary_uses_captured_seed_metadata_and_exact_target(self):
        payload = self.h.payload()
        captured = []
        schedule = self.bus.schedule_emit
        self.bus.schedule_emit = lambda event: (captured.append(deepcopy(event)), schedule(event))[1]
        await self.h._emit_session_summarized_event(payload)
        await self.joined()
        self.assertEqual(captured[0].payload["questions_attempted"], 2)
        self.assertEqual(captured[0].payload["correct_rate"], .5)
        self.assertEqual(captured[0].payload["topics_studied"], ["original topic"])
        message = self.h.sink.messages[0]
        self.assertEqual(message["target_lanlan"], "LearnerRole")
        origin = message["metadata"]["study_narration_origin"]
        self.assertEqual(origin["context"], payload["_material_context"])
        self.assertNotIn("material_identity", origin["context"])
        text = message["parts"][0]["text"]
        for secret in ("study_narration_origin", "boot_id", "course-A", "session-A", "a" * 32, "wrong live seed"):
            self.assertNotIn(secret, text)
        self.assertEqual(self.bus.emit_count, 1)

    async def test_emitter_waiting_lock_drops_after_course_change(self):
        await self.h._lock.acquire()
        task = asyncio.create_task(self.h._emit_session_summarized_event(self.h.payload()))
        await asyncio.sleep(0)
        self.h.replace_course()
        self.h._lock.release()
        await task
        self.assertFalse(self.h.sink.messages)
        self.assertFalse(self.h._study_material_output_targets)
        self.assertEqual(self.bus.scheduled_emit_count, 0)

    async def test_payload_is_frozen_before_emitter_lock_wait(self):
        await self.h._lock.acquire()
        payload = self.h.payload()
        task = asyncio.create_task(self.h._emit_session_summarized_event(payload))
        await asyncio.sleep(0)
        payload["_session_summary_seed"]["answer_count"] = 200
        payload["_material_context"]["course_id"] = "mutated"
        payload["summary"] = "changed caller summary"
        self.h._lock.release()
        await task
        await self.joined()
        text = self.h.sink.messages[0]["parts"][0]["text"]
        self.assertIn("2 question(s)", text)
        self.assertIn("original session explanation", text)
        self.assertNotIn("changed caller", text)

    async def test_missing_or_unknown_private_context_target_seed_fail_closed(self):
        for key, value in (("_material_context", {}), ("_material_context", {"course_id": "course-A", "session_id": ""}),
                           ("_narration_target_lanlan", ""), ("_narration_target_lanlan", None),
                           ("_session_summary_seed", None)):
            with self.subTest(key=key, value=value):
                payload = self.h.payload()
                payload[key] = value
                await self.h._emit_session_summarized_event(payload)
        self.assertFalse(self.h.sink.messages)
        self.assertFalse(self.h._study_material_output_targets)

    async def test_summary_never_replaces_registered_image_notification_binding(self):
        full = materials.bind_material_output(self.h, materials.material_context(self.h), "LearnerRole")
        old = deepcopy(self.h._study_material_output_targets)
        await self.h._emit_session_summarized_event(self.h.payload())
        self.assertEqual(self.h._study_material_output_targets, old)
        before = materials.material_context(self.h)
        self.h._state.last_vision_image_base64 = "new-image"
        changes = materials.material_changes(self.h, before, "image")
        self.assertEqual([item["target_lanlan"] for item in changes], ["LearnerRole"])
        self.assertEqual(self.h._study_material_output_targets["LearnerRole"], full)
        await self.joined()
        self.assertEqual(len(self.h.sink.messages), 1)  # Summary ignores picture-only churn.

    async def test_schedule_freezes_entire_origin_and_text_during_semaphore_wait(self):
        self.bus._emit_semaphore = asyncio.Semaphore(0)
        event = self.h.event()
        self.bus.schedule_emit(event)
        await asyncio.sleep(0)
        event.payload[bus_module._NARRATION_ORIGIN_KEY]["context"]["course_id"] = "mutated"
        event.payload["key_insight"] = "mutated insight"
        self.bus._emit_semaphore.release()
        await self.joined()
        self.assertEqual(self.h.sink.messages[0]["metadata"]["study_narration_origin"]["context"]["course_id"], "course-A")
        self.assertIn("original insight", self.h.sink.messages[0]["parts"][0]["text"])

    async def test_stale_after_semaphore_wait_drops_without_worker_failure_and_recovers(self):
        self.bus._emit_semaphore = asyncio.Semaphore(0)
        self.bus.schedule_emit(self.h.event())
        await asyncio.sleep(0)
        self.h.replace_course()
        self.bus._emit_semaphore.release()
        await self.joined()
        self.assertFalse(self.h.sink.messages)
        self.assertEqual(self.bus.dropped_emit_count, 1)
        self.assertEqual(self.bus._worker_failure_count, 0)
        self.bus.schedule_emit(self.h.event())
        await self.joined()
        self.assertEqual(len(self.h.sink.messages), 1)
        self.assertEqual(self.bus.scheduled_emit_count, 0)

    async def test_direct_emit_lock_wait_rechecks_material(self):
        await self.bus._lock.acquire()
        task = asyncio.create_task(self.bus.emit(self.h.event()))
        await asyncio.sleep(0)
        self.h.replace_course()
        self.bus._lock.release()
        await task
        self.assertFalse(self.h.sink.messages)
        self.assertEqual(self.bus._in_flight_emit_count, 0)
        self.assertTrue(self.bus._emit_idle.is_set())

    async def test_final_pre_push_reject_releases_respond_and_throttle_without_commit(self):
        reserve = self.bus._reserve_emit
        def changed_after_reserve(decision, *, mark_respond=False):
            reserve(decision, mark_respond=mark_respond)
            self.h.replace_course()
        self.bus._reserve_emit = changed_after_reserve
        self.bus._emit_decision = lambda event, now: bus_module._EmitDecision(True, "test-throttle")
        with patch.dict(bus_module.BEHAVIOR_MAP, session_summarized="respond"):
            await self.bus.emit(self.h.event())
        self.assertFalse(self.h.sink.messages)
        self.assertFalse(self.bus._pending_throttle)
        self.assertFalse(self.bus._pending_respond_count_by_target)
        self.assertFalse(self.bus._throttle)
        self.assertFalse(self.bus._last_respond_at_by_target)
        self.assertEqual(self.bus.emit_count, 0)
        self.assertEqual(self.bus.dropped_emit_count, 1)

    async def test_unconfirmed_current_and_wrong_boot_sequence_target_rejected(self):
        for kind in ("boot", "future_seq", "missing_target", "unregistered", "empty_context", "bad_bool_seq", "wrong_event"):
            event = self.h.event()
            origin = event.payload[bus_module._NARRATION_ORIGIN_KEY]
            if kind == "boot": origin["boot_id"] = "b" * 32
            if kind == "future_seq": origin["change_seq"] = 99
            if kind == "missing_target": event.payload.pop("target_lanlan")
            if kind == "unregistered": event.payload["target_lanlan"] = "OtherRole"
            if kind == "empty_context": origin["context"] = {}
            if kind == "bad_bool_seq": origin["change_seq"] = True
            if kind == "wrong_event": origin["event"] = "general_response_completed"
            with self.subTest(kind=kind):
                self.assertIsNone(self.bus.schedule_emit(event))
        self.assertFalse(self.h.sink.messages)
        self.assertEqual(self.bus._worker_failure_count, 0)

    async def test_no_validator_legacy_summary_and_async_validator_are_drops(self):
        event = self.h.event()
        self.bus._material_validator = None
        self.assertIsNone(self.bus.schedule_emit(event))
        self.assertIsNone(self.bus.schedule_emit(bus_module.StudyEvent("session_summarized", {"key_insight": "legacy"})))
        async def not_sync(_): return True
        self.bus._material_validator = not_sync
        self.assertIsNone(self.bus.schedule_emit(event))
        def unavailable(_): raise RuntimeError("current unknown")
        self.bus._material_validator = unavailable
        self.assertIsNone(self.bus.schedule_emit(event))
        self.assertEqual(self.bus.dropped_emit_count, 4)
        self.assertFalse(self.h.sink.messages)

    async def test_origin_on_unsupported_event_never_leaks_fallback_payload_text(self):
        event = self.h.event()
        unsupported = bus_module.StudyEvent("unknown_narration", event.payload)
        self.assertIsNone(self.bus.schedule_emit(unsupported))
        await self.bus.emit(unsupported)
        self.assertFalse(self.h.sink.messages)

    async def test_unrelated_timer_behavior_unchanged_without_validator_or_target(self):
        self.bus._material_validator = None
        self.bus.schedule_emit(bus_module.StudyEvent("pomodoro_focus_completed", {"duration_minutes": 25}))
        await self.joined()
        self.assertEqual(len(self.h.sink.messages), 1)
        self.assertNotIn("metadata", self.h.sink.messages[0])
        self.assertEqual(self.h.sink.messages[0]["ai_behavior"], "respond")

    async def test_close_retains_existing_admission_behavior(self):
        await self.bus.close()
        self.assertIsNone(self.bus.schedule_emit(self.h.event()))
        self.assertEqual(self.bus.scheduled_emit_count, 0)
        self.assertFalse(self.h.sink.messages)


if __name__ == "__main__":
    unittest.main(verbosity=2)
