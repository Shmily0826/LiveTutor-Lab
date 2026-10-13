"""One explicitly submitted image per course, in the existing StudyStore kv."""
from __future__ import annotations
import hashlib


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
