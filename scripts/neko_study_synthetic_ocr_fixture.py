"""Exercise the extracted Study OCR pipeline on synthetic pixels and feed the
result through the genuine Study Companion explain/session methods.

Run with the project-local venv:
  .tmp-uv-cache/neko-study-venv/Scripts/python.exe -I -B scripts/neko_study_synthetic_ocr_fixture.py

The normal plugin OCR entrypoint receives one synthetic image from an injected
interactive-capture provider. No host, desktop capture, live model, audio,
microphone, or external provider is started.
"""
from __future__ import annotations

import asyncio
import hashlib
import importlib
import importlib.metadata
import importlib.util
import json
import logging
import os
import platform
import subprocess
from pathlib import Path
import sys
import time
import traceback
from types import SimpleNamespace
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import neko_study_plugin_methods_fixture as core


RELEASE = core.RELEASE
OCR_SOURCE = RELEASE / "plugins" / "study_companion" / "study_ocr_pipeline.py"
OCR_ENTRY_SOURCE = RELEASE / "plugins" / "study_companion" / "entry_ocr_entries.py"
MODEL_NAMES = (
    "ch_PP-OCRv4_det_infer.onnx",
    "ch_PP-OCRv4_rec_infer.onnx",
    "ch_ppocr_mobile_v2.0_cls_infer.onnx",
)
PROCESS_STACKS: list[list[dict[str, str]]] = []
PLATFORM_VER_PROBE_ATTEMPTS = 0
OPTIONAL_PROCESS_PROBES: list[str] = []


def _relative_import_origin(name: str) -> str | None:
    spec = importlib.util.find_spec(name)
    if spec is None or not spec.origin:
        return None
    try:
        return Path(spec.origin).resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return "outside_project"


def _record_process_stack() -> None:
    frame = sys._getframe(1)
    stack: list[dict[str, str]] = []
    while frame is not None and len(stack) < 12:
        stack.append({
            "module": str(frame.f_globals.get("__name__", "unknown"))[:120],
            "function": frame.f_code.co_name[:120],
        })
        frame = frame.f_back
    PROCESS_STACKS.append(stack)


def _trace_blocked_process(*_args, **_kwargs):
    core.COUNTS["process_attempts_blocked"] += 1
    _record_process_stack()
    raise RuntimeError("process creation blocked by isolated OCR fixture")


def _block_platform_ver_probe(*_args, **_kwargs):
    """Avoid platform._syscmd_ver's optional shell call; use sys version fallback."""
    global PLATFORM_VER_PROBE_ATTEMPTS
    PLATFORM_VER_PROBE_ATTEMPTS += 1
    return "", "", ""


def _block_known_optional_process_probe(args, *positional, **kwargs):
    """Return empty output only for NumPy's Linux-only SVE lscpu probe."""
    command = args[0] if isinstance(args, (list, tuple)) and args else args
    if command == "lscpu":
        core.COUNTS["process_attempts_blocked"] += 1
        _record_process_stack()
        OPTIONAL_PROCESS_PROBES.append("numpy.testing.check_support_sve:lscpu")
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
    return _trace_blocked_process(args, *positional, **kwargs)


def _allow_only_local_ocr_imports() -> None:
    """Lift only the old import blocker's two OCR-package denies."""
    blocker = next(
        (finder for finder in sys.meta_path if type(finder).__name__ == "ImportBlocker"),
        None,
    )
    if blocker is None:
        raise RuntimeError("existing fail-closed import guard was not installed")
    original = blocker.find_spec
    allowed = ("rapidocr_onnxruntime", "onnxruntime")

    def find_spec(fullname, path=None, target=None):
        if any(fullname == name or fullname.startswith(name + ".") for name in allowed):
            return None
        return original(fullname, path, target)

    blocker.find_spec = find_spec


def _install_ocr_runtime_guards() -> None:
    _allow_only_local_ocr_imports()
    # NumPy requests these exact optional platform probes during OCR import.
    platform._syscmd_ver = _block_platform_ver_probe
    subprocess.run = _block_known_optional_process_probe


def _model_dir() -> Path:
    spec = importlib.util.find_spec("rapidocr_onnxruntime")
    if spec is None or not spec.origin:
        raise RuntimeError("project-local RapidOCR package is unavailable")
    return Path(spec.origin).resolve().parent / "models"


def _build_ocr_pipeline():
    from plugins.study_companion.models import StudyConfig
    from plugins.study_companion.study_ocr_pipeline import StudyOcrPipeline
    from plugin.plugins._shared.rapidocr.ocr_backends import RapidOcrBackend

    config = StudyConfig(
        rapidocr_install_target_dir=str(core.TEMP_ROOT / "rapidocr-runtime"),
        rapidocr_engine_type="onnxruntime",
        rapidocr_lang_type="ch",
        rapidocr_model_type="mobile",
        rapidocr_ocr_version="PP-OCRv4",
    )
    return StudyOcrPipeline(
        logger=logging.getLogger("neko.study.ocr.fixture"),
        config=config,
        ocr_backend=RapidOcrBackend(
            install_target_dir_raw=config.rapidocr_install_target_dir,
            engine_type=config.rapidocr_engine_type,
            lang_type=config.rapidocr_lang_type,
            model_type=config.rapidocr_model_type,
            ocr_version=config.rapidocr_ocr_version,
            plugin_id="study_companion",
        ),
    )


def _synthetic_image(path: Path):
    from PIL import Image, ImageDraw, ImageFont

    image = Image.new("RGB", (1500, 760), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=58)
    draw.rounded_rectangle((36, 34, 1464, 726), radius=18, outline="#777777", width=3, fill="#fbfbfb")
    draw.text((78, 86), "Example 2: u-substitution", fill="#111111", font=font)
    draw.text((78, 224), "Let u = x^2", fill="#111111", font=font)
    draw.text((78, 360), "Then du = 2x dx", fill="#111111", font=font)
    draw.text((78, 496), "So x dx = (1/2) du", fill="#111111", font=font)
    draw.text((78, 632), "Integrate exp(u) after substitution", fill="#111111", font=font)
    image.save(path, format="PNG", optimize=True)
    return image


class _OcrContextAgent:
    """Deterministic recorder; it makes no model/provider request."""

    def __init__(self, reply_type, expected_ocr: str):
        self.reply_type = reply_type
        self.expected_ocr = expected_ocr
        self.calls: list[dict[str, object]] = []

    async def concept_explain(self, text, *, mode, context):
        self.calls.append({
            "input_equals_ocr": text == self.expected_ocr,
            "input_equals_followup": text == "Why does Example 2 have a 1/2 factor?",
            "context_source": str(context.get("source") or ""),
            "context_input_text_equals_input": context.get("input_text") == text,
            "context_last_ocr_text_equals_ocr": context.get("last_ocr_text") == self.expected_ocr,
            "context_session_id": str(context.get("session_id") or ""),
        })
        reply = "Deterministic fixture received the synthetic lesson text; no model reasoning was run."
        return self.reply_type(
            operation="concept_explain",
            input_text=text,
            reply=reply,
            payload={"summary": reply, "diagnostic": "synthetic_ocr_fixture"},
        )


class _SafeContext:
    plugin_id = "study_companion"
    metadata = {"id": "study_companion", "i18n": {"default_locale": "en"}}
    logger = logging.getLogger("neko.study.ocr.fixture")
    bus = None
    config_path = RELEASE / "plugins" / "study_companion" / "plugin.toml"
    _effective_config = {
        "plugin": {"store": {"enabled": False}, "database": {"enabled": False}},
        "plugin_state": {"backend": "off"},
    }
    images = SimpleNamespace()

    async def finish(self, **_kwargs):
        core.COUNTS["host_output_attempts_blocked"] += 1
        raise RuntimeError("host output blocked in isolated OCR fixture")

    def push_message(self, **_kwargs):
        core.COUNTS["host_output_attempts_blocked"] += 1
        raise RuntimeError("host output blocked in isolated OCR fixture")

    def __getattr__(self, name):
        if name.startswith(("get_", "update_", "replace_", "upsert_", "delete_", "set_", "trigger_", "export_", "create_", "run_")):
            async def blocked_host_method(*_a, **_k):
                core.COUNTS["host_output_attempts_blocked"] += 1
                raise RuntimeError("host service access blocked in isolated OCR fixture")
            return blocked_host_method
        raise AttributeError(name)


class _PluginCheckFailure(RuntimeError):
    def __init__(self, details: dict[str, object]):
        super().__init__("safe plugin context/persistence assertions failed")
        self.details = details


async def _plugin_roundtrip(image, pipeline):
    plugin_module = importlib.import_module("plugins.study_companion")
    ocr_entries = importlib.import_module("plugins.study_companion.entry_ocr_entries")
    from plugin.sdk.shared.core.base import NekoPluginBase

    def inert_file_logger(self, **_kwargs):
        logger = logging.getLogger("neko.study.ocr.fixture")
        logger.handlers.clear()
        logger.addHandler(logging.NullHandler())
        logger.propagate = False
        return logger

    capture_calls = 0

    async def synthetic_capture_interactive_region(**_kwargs):
        nonlocal capture_calls
        capture_calls += 1
        return SimpleNamespace(image=image.copy(), canceled=False)

    # study_ocr_snapshot imports this provider into entry_ocr_entries. Replace
    # that one seam before plugin construction; no desktop capture is reachable.
    ocr_entries.capture_interactive_region = synthetic_capture_interactive_region
    NekoPluginBase.enable_file_logging = inert_file_logger
    plugin = plugin_module.StudyCompanionPlugin(_SafeContext())
    plugin._ocr_pipeline = pipeline

    started = await plugin.study_start_session()
    start_payload = core._result_payload(started)
    session_id = str(start_payload.get("session_id") or "")
    if not session_id:
        raise RuntimeError("real plugin did not create the synthetic session")
    core.ACTIVE_SESSION_ID = session_id

    started_at = time.perf_counter()
    ocr_entry_result = await plugin.study_ocr_snapshot(
        capture_mode="interactive", allow_fullscreen_fallback=False
    )
    ocr_entry_ms = round((time.perf_counter() - started_at) * 1000, 2)
    ocr_entry_payload = core._result_payload(ocr_entry_result)
    ocr_text = str(ocr_entry_payload.get("text") or "")
    state_ocr_text = str(plugin._state.last_ocr_text or "")
    if (
        type(ocr_entry_result).__name__ == "Err"
        or capture_calls != 1
        or not ocr_text
        or str(ocr_entry_payload.get("status") or "") != "ok"
        or str(ocr_entry_payload.get("capture_mode_used") or "") != "interactive"
    ):
        raise RuntimeError("normal Study OCR entrypoint did not return synthetic OCR text")
    if state_ocr_text != ocr_text:
        raise RuntimeError("Study OCR entrypoint did not update last_ocr_text")
    agent = _OcrContextAgent(plugin_module.TutorReply, ocr_text)
    plugin._agent = agent

    normalized = " ".join(ocr_text.lower().split())
    expected = {
        "Example 2": "example 2" in normalized,
        "u = x^2": "u = x^2" in normalized or "u=x^2" in normalized or "u = x2" in normalized or "u=x2" in normalized,
        "du = 2x dx": "du = 2x dx" in normalized or "du=2x dx" in normalized or "du = 2 x dx" in normalized,
        "1/2": "1/2" in normalized or "1 / 2" in normalized,
    }
    recall = sum(expected.values()) / len(expected)

    started_at = time.perf_counter()
    explanation = await plugin.study_explain_text(text="", session_id=session_id)
    explanation_ms = round((time.perf_counter() - started_at) * 1000, 2)
    explanation_payload = core._result_payload(explanation)

    followup_text = "Why does Example 2 have a 1/2 factor?"
    started_at = time.perf_counter()
    followup = await plugin.study_explain_text(text=followup_text, session_id=session_id)
    followup_ms = round((time.perf_counter() - started_at) * 1000, 2)
    followup_payload = core._result_payload(followup)

    reused = await plugin.study_get_session(session_id=session_id)
    reused_payload = core._result_payload(reused)
    session_record = reused_payload.get("session") if isinstance(reused_payload.get("session"), dict) else {}
    interactions = reused_payload.get("interactions") if isinstance(reused_payload.get("interactions"), list) else []
    session_matches = bool(session_record.get("id") == session_id)
    interaction_matches = bool(interactions) and all(str(row.get("session_id") or "") == session_id for row in interactions)
    context_grounded = (
        len(agent.calls) == 2
        and agent.calls[0]["input_equals_ocr"]
        and agent.calls[0]["context_source"] == "ocr_snapshot"
        and agent.calls[0]["context_input_text_equals_input"]
        and agent.calls[0]["context_last_ocr_text_equals_ocr"]
        and agent.calls[1]["input_equals_followup"]
        and agent.calls[1]["context_input_text_equals_input"]
        and agent.calls[1]["context_last_ocr_text_equals_ocr"]
        and all(call["context_session_id"] == session_id for call in agent.calls)
    )
    consistency = {
        "entrypoint": "StudyCompanionPlugin.study_ocr_snapshot",
        "capture_mode": str(ocr_entry_payload.get("capture_mode_used") or ""),
        "synthetic_capture_provider_calls": capture_calls,
        "entrypoint_updated_last_ocr_text": state_ocr_text == ocr_text,
        "entrypoint_returned_text_equals_state": ocr_text == state_ocr_text,
        "session_record_id_matches": session_matches,
        "interaction_session_ids_match": interaction_matches,
        "interaction_count": len(interactions),
        "agent_call_count": len(agent.calls),
        "agent_context_checks": agent.calls,
        "plugin_context_grounded_in_ocr": context_grounded,
    }
    if type(explanation).__name__ == "Err" or type(followup).__name__ == "Err":
        raise _PluginCheckFailure({**consistency, "plugin_returned_error": True})
    if not (session_matches and interaction_matches and context_grounded):
        raise _PluginCheckFailure({**consistency, "plugin_returned_error": False})
    return {
        "ocr": {
            "status": str(ocr_entry_payload.get("status") or ""),
            "backend": str(ocr_entry_payload.get("backend") or ""),
            "text": ocr_text[:2000],
            "expected_tokens": expected,
            "expected_token_recall": recall,
            "entrypoint_latency_ms": ocr_entry_ms,
            "entrypoint": "StudyCompanionPlugin.study_ocr_snapshot",
            "capture_injection": "plugins.study_companion.entry_ocr_entries.capture_interactive_region",
            "capture_mode_requested": str(ocr_entry_payload.get("capture_mode_requested") or ""),
            "capture_mode_used": str(ocr_entry_payload.get("capture_mode_used") or ""),
            "synthetic_capture_provider_calls": capture_calls,
            "last_ocr_text_updated_by_entrypoint": state_ocr_text == ocr_text,
        },
        "session_id": session_id,
        "session_record_id_matches": session_matches,
        "interaction_session_ids_match": interaction_matches,
        "interaction_count": len(interactions),
        "plugin_context_grounded_in_ocr": context_grounded,
        "agent_double_calls": agent.calls,
        "explanation": str(explanation_payload.get("reply") or explanation_payload.get("summary") or "")[:220],
        "followup": str(followup_payload.get("reply") or followup_payload.get("summary") or "")[:220],
        "method_latency_ms": {"ocr_fallback_explanation": explanation_ms, "contextual_followup": followup_ms},
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    core._deny_process = _trace_blocked_process
    core._install_guards()
    _install_ocr_runtime_guards()
    result: dict[str, object] = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "result": "GAP",
        "evidence_level": "synthetic Pillow pixels + extracted StudyOcrPipeline + local RapidOCR + real extracted plugin methods + deterministic agent double",
        "process_attempt_stacks": PROCESS_STACKS,
        "process_guard_downstream_calls": 0,
        "platform_ver_probe_stub_calls": 0,
        "optional_process_probes_substituted": OPTIONAL_PROCESS_PROBES,
        "guards": core.COUNTS,
        "downstream_calls": {"provider": 0, "socket": 0, "audio": 0},
        "host_started": False,
        "real_model_or_provider_used": False,
        "desktop_capture_used": False,
        "audio_or_microphone_used": False,
        "ocr_pipeline_invoked": False,
    }
    try:
        gate = core._exercise_gates()
        # Generate only synthetic pixels after network/process/file guards are active.
        image_path = core.TEMP_ROOT / "synthetic-example2.png"
        image = _synthetic_image(image_path)
        image_sha256 = hashlib.sha256(image_path.read_bytes()).hexdigest()

        rapidocr_spec = importlib.util.find_spec("rapidocr_onnxruntime")
        onnx_spec = importlib.util.find_spec("onnxruntime")
        numpy_spec = importlib.util.find_spec("numpy")
        if not rapidocr_spec or not onnx_spec or not numpy_spec:
            raise RuntimeError("pinned local OCR module import is unavailable")
        pipeline = _build_ocr_pipeline()
        plugin_result = loop.run_until_complete(_plugin_roundtrip(image, pipeline))
        ocr_result = plugin_result.pop("ocr")
        recall = float(ocr_result["expected_token_recall"])
        ocr_status = str(ocr_result["status"])
        result.update({
            "result": "PASS_NORMAL_OCR_ENTRYPOINT_AND_PLUGIN_CONTEXT" if ocr_status == "ok" and recall >= 0.75 else "PARTIAL_OCR_RECALL_PLUGIN_CONTEXT_REACHED",
            "ocr": {
                **ocr_result,
                "inference_completed": ocr_status in {"ok", "empty"},
                "image_size": list(image.size),
                "synthetic_image_sha256": image_sha256,
                "synthetic_image_path_class": "project_ignored_fixture_temp",
            },
            "runtime": {
                "rapidocr_distribution_version": importlib.metadata.version("rapidocr-pillow"),
                "rapidocr_module": _relative_import_origin("rapidocr_onnxruntime"),
                "onnxruntime_version": importlib.metadata.version("onnxruntime"),
                "onnxruntime_module": _relative_import_origin("onnxruntime"),
                "numpy_version": importlib.metadata.version("numpy"),
                "numpy_module": _relative_import_origin("numpy"),
                "pillow_version": importlib.metadata.version("Pillow"),
                "pillow_module": _relative_import_origin("PIL"),
                "rapidocr_source": "extracted plugin.plugins._shared.rapidocr.ocr_backends.RapidOcrBackend",
                "pipeline_source_sha256": hashlib.sha256(OCR_SOURCE.read_bytes()).hexdigest(),
                "entrypoint_source_sha256": hashlib.sha256(OCR_ENTRY_SOURCE.read_bytes()).hexdigest(),
                "model_sha256": {
                    name: hashlib.sha256((_model_dir() / name).read_bytes()).hexdigest()
                    for name in MODEL_NAMES
                },
            },
            "guard_stimulus": gate,
            "ocr_pipeline_invoked": True,
            "ocr_inference_completed": ocr_status in {"ok", "empty"},
            "process_guard_downstream_calls": 0,
            "platform_ver_probe_stub_calls": PLATFORM_VER_PROBE_ATTEMPTS,
            "optional_process_probes_substituted": OPTIONAL_PROCESS_PROBES,
            "downstream_calls": {
                "provider": core._provider_downstream_calls,
                "socket": core._socket_downstream_calls,
                "audio": core._audio_downstream_calls,
            },
            "live_model_or_provider_used": False,
            "private_config_values_or_secrets_included": False,
        })
        result["plugin"] = plugin_result
        pipeline.close()
    except BaseException as exc:
        ocr_completed = bool((result.get("ocr") or {}).get("inference_completed"))
        result.update({
            "result": "BLOCKED_PLUGIN_CONTEXT" if ocr_completed else "BLOCKED_OCR_OR_PLUGIN_FIXTURE",
            "error_type": type(exc).__name__,
            "error": str(exc)[:240],
            "plugin_check_details": getattr(exc, "details", None),
            "process_attempt_stacks": PROCESS_STACKS,
            "ocr_pipeline_invoked": bool(core.COUNTS.get("process_attempts_blocked") or core.COUNTS.get("outside_reads_blocked")),
            "live_model_or_provider_used": False,
            "downstream_calls": {
                "provider": core._provider_downstream_calls,
                "socket": core._socket_downstream_calls,
                "audio": core._audio_downstream_calls,
            },
        })
    finally:
        loop.close()
    result["guards"] = core.COUNTS
    result["process_guard_downstream_calls"] = 0
    result["platform_ver_probe_stub_calls"] = PLATFORM_VER_PROBE_ATTEMPTS
    result["optional_process_probes_substituted"] = OPTIONAL_PROCESS_PROBES
    result["blocked_imports"] = core.BLOCKED_IMPORTS
    result["config_data_read_safe_metadata"] = core.CONFIG_DATA_READS
    result["outside_file_attempts_safe_metadata"] = core.OUTSIDE_FILE_METADATA
    stamp = datetime.now(timezone.utc)
    proof_path = core.EVIDENCE_ROOT / f"neko-study-plugin-ocr-{stamp.strftime('%Y%m%dT%H%M%SZ')}.json"
    proof_path.write_text(json.dumps(result, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    result["proof_artifact"] = proof_path.relative_to(ROOT).as_posix()
    print(json.dumps(result, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
