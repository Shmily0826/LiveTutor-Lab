"""One explicitly submitted image per course, in the existing StudyStore kv."""
from __future__ import annotations
import hashlib
import asyncio
import inspect
import uuid


class MaterialContextChanged(ValueError):
    pass


def material_context(host, *, include_material=True):
    state = host._state
    context = {"course_id": str(getattr(state, "study_course_id", "") or ""),
               "session_id": str(getattr(host, "_study_session_id", "") or "")}
    if include_material:
        image = str(getattr(state, "last_vision_image_base64", "") or "")
        text = str(getattr(state, "last_ocr_text", "") or "")
        context["material_identity"] = hashlib.sha256((image + "\0" + text).encode("utf-8")).hexdigest()
    return context


def material_context_current(host, expected):
    if not expected:
        return True
    current = material_context(host, include_material="material_identity" in expected)
    return all(current.get(key) == value for key, value in expected.items())


def _material_control_state(host):
    if not getattr(host, "_study_material_boot_id", ""):
        host._study_material_boot_id = uuid.uuid4().hex
    if not hasattr(host, "_study_material_change_seq"):
        host._study_material_change_seq = 0
    if not hasattr(host, "_study_material_output_targets"):
        host._study_material_output_targets = {}


def material_output_target(host, extra):
    # An explicit but missing target must never fall back to broadcasting.
    if "_ctx" in extra:
        context = extra.get("_ctx")
        return str(context.get("lanlan_name") or "").strip() if isinstance(context, dict) else ""
    return str(getattr(getattr(host, "ctx", None), "_current_lanlan", "") or "").strip()


def bind_material_output(host, expected, target):
    """Called under the state lock after a successful, current native explanation."""
    _material_control_state(host)
    if not material_context_current(host, expected):
        raise MaterialContextChanged("material changed before output binding")
    binding = {"v": 1, "boot_id": host._study_material_boot_id,
               "change_seq": host._study_material_change_seq, "context": dict(expected)}
    if target:
        host._study_material_output_targets[target] = binding
    return binding


def material_changes(host, before, reason):
    """Prepare accepted changes under the setter's existing state lock; never send here."""
    _material_control_state(host)
    after = material_context(host)
    if before == after:
        return []
    host._study_material_change_seq += 1
    control = {"v": 1, "boot_id": host._study_material_boot_id,
               "change_seq": host._study_material_change_seq,
               "before": dict(before), "after": after, "reason": reason}
    changes = []
    for target, binding in host._study_material_output_targets.items():
        expected = binding["context"]
        after_matches = all(after.get(key) == value for key, value in expected.items())
        # A missed A→B submission must not strand A's bound output at B→C.
        if binding["boot_id"] == host._study_material_boot_id and not after_matches:
            changes.append({"target_lanlan": target, "control": dict(control)})
    return changes


async def submit_material_changes(host, changes):
    """SDK submission only, outside the state lock and independent of narration settings."""
    statuses = []
    for change in changes:
        status = {"target_lanlan": change["target_lanlan"],
                  "change_seq": change["control"]["change_seq"], "status": "unavailable"}
        push = getattr(host, "push_message", None)
        if not callable(push):
            push = getattr(getattr(host, "ctx", None), "push_message", None)
        if callable(push):
            try:
                result = push(parts=[{"type": "text", "text": "[study-material-control:v1]"}],
                    visibility=[], ai_behavior="blind", source="study_material_control",
                    target_lanlan=change["target_lanlan"],
                    metadata={"study_material_control": change["control"]})
                if inspect.isawaitable(result):
                    result = await asyncio.wait_for(result, timeout=5.0)
                status["status"] = ("not_submitted" if isinstance(result, dict)
                                    and (result.get("submitted") is False or result.get("ok") is False)
                                    else "submitted" if isinstance(result, dict) and result.get("submitted") is True
                                    else "submission_unknown")
            except asyncio.CancelledError:
                status.update(status="submission_unknown", error_type="CancelledError")
                statuses.append(status)
                host._study_material_control_submission = statuses
                if getattr(host, "logger", None) is not None:
                    host.logger.warning("Study material accepted; cancellation submission interrupted")
                raise
            except Exception as exc:
                status["status"] = "submission_unknown" if isinstance(exc, asyncio.TimeoutError) else "exception"
                status["error_type"] = type(exc).__name__
        if status["status"] != "submitted" and getattr(host, "logger", None) is not None:
            host.logger.warning(f"Study material accepted; cancellation submission {status['status']}")
        statuses.append(status)
    if statuses:
        host._study_material_control_submission = statuses
    return statuses


def _key(course):
    return "submitted_image:" + hashlib.sha256(str(course or "general").encode()).hexdigest()


def load_material(store, course):
    value = store.get_raw(_key(course))
    if not isinstance(value, dict) or value.get("course_id") != course:
        return {}
    image = value.get("image", "")
    if not isinstance(image, str) or len(image) > 16_000_000:
        return {}
    return value


def save_material(store, course, image, text):
    # Payload validation remains at study_submit_image's existing trust boundary.
    if not isinstance(image, str) or not image or len(image) > 16_000_000:
        raise ValueError("submitted image is too large or empty")
    store.set_raw(_key(course), {"course_id": course, "image": image, "text": str(text or "")[:12000]})
