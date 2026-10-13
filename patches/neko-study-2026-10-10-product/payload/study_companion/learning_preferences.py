"""Explicit learner preferences in the existing StudyStore kv table."""
from __future__ import annotations

import json
from typing import Any

PREFERENCES_KEY = "learning_preferences"
DEFAULT_PREFERENCES = {"length": "brief", "explanation_style": "step_by_step", "proactive_quiz": False}
_CHOICES = {
    "language": {"zh-CN", "zh-TW", "en-US"},
    "length": {"brief", "balanced", "detailed"},
    "explanation_style": {"step_by_step", "example_first", "direct"},
}


def validate_preferences(preferences: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(preferences, dict):
        raise ValueError("preferences must be an object")
    for key, value in preferences.items():
        if key == "proactive_quiz":
            if type(value) is not bool:
                raise ValueError("proactive_quiz must be a boolean")
        elif key not in _CHOICES or not isinstance(value, str) or value not in _CHOICES[key]:
            raise ValueError(f"unsupported learning preference {key!r}: {value!r}")
    return dict(preferences)


def load_preferences(store: Any) -> dict[str, Any]:
    stored = store.get_raw(PREFERENCES_KEY) or {}
    # A damaged optional preference must not prevent teaching or erase history.
    valid = {}
    for key, value in stored.items():
        try:
            valid.update(validate_preferences({key: value}))
        except ValueError:
            continue
    return {**DEFAULT_PREFERENCES, **valid}


def update_preferences(store: Any, preferences: dict[str, Any], *, remember: bool = False) -> dict[str, Any]:
    updates = validate_preferences(preferences)
    effective = {**load_preferences(store), **updates}
    if remember is True and updates:
        # Save only explicit fields, never values inferred from a transient turn.
        stored = store.get_raw(PREFERENCES_KEY) or {}
        valid = {key: value for key, value in load_preferences(store).items() if key in stored}
        store.set_raw(PREFERENCES_KEY, {**valid, **updates})
    return {"preferences": effective, "persisted": remember is True and bool(updates)}


def preference_prompt(preferences: dict[str, Any] | None, *, temporary: bool = False) -> str:
    effective = {**DEFAULT_PREFERENCES, **validate_preferences(preferences or {})}
    return (
        ("\nCurrent turn teaching preferences (override saved defaults for this answer only): "
         if temporary else "\nSaved learner teaching defaults: ") + json.dumps(effective, ensure_ascii=False)
        + ". Follow these when the current learner request is silent. Explicit current "
        "requests and the course/turn response language override these defaults. "
        "These preferences override the default response-mode headings and check questions. "
        "Be patient, concise by default, and willing to correct yourself. With "
        "proactive_quiz=false, do not append an unsolicited quiz or check question; "
        "still generate a question when the learner explicitly asks. For brief replies, "
        "explain one idea in short spoken prose and allow follow-ups. Temporary "
        "instructions are not durable preferences and must not be reported as saved."
    )
