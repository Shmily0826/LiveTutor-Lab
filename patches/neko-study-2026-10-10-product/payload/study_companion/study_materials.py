"""One explicitly submitted image per course, in the existing StudyStore kv."""
from __future__ import annotations
import hashlib


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
