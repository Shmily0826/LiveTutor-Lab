from __future__ import annotations

from .entry_common import (
    asyncio,
    Err,
    Ok,
    SdkError,
    plugin_entry,
    tr,
    build_ocr_payload,
    tesseract_support,
    rapidocr_support,
    update_install_task_state,
    _entry_exception_error,
)


def _ocr_request_lanlan(kwargs: dict[str, object]) -> str | None:
    context = kwargs.get("_ctx")
    if isinstance(context, dict):
        return str(context.get("lanlan_name") or "").strip() or None
    return None


# N.E.K.O's own surfaces are never the study material, so they are not valid
# "active window" capture targets.
_ACTIVE_WINDOW_SELF_MARKERS = ("N.E.K.O", "NekoClaw")
_ACTIVE_WINDOW_TITLE_LIMIT = 240
_ACTIVE_WINDOW_MIN_SIDE = 64


def _foreground_window_target() -> dict[str, object] | None:
    """Resolve the foreground window into a rect target for the OCR pipeline.

    Legacy resolver for `active_window`: it crops whatever happens to be in
    front, so on a live desktop an unrelated personal window can be captured and
    sent to the model. `target_window` requires an explicit title instead and is
    what the desktop tutor uses.
    """
    return _window_target_for_hwnd(_foreground_hwnd())


def _foreground_hwnd() -> int:
    import sys

    if sys.platform != "win32":
        return 0
    try:
        import ctypes

        return int(ctypes.windll.user32.GetForegroundWindow() or 0)
    except Exception:
        return 0


def _window_title(hwnd: int) -> str:
    import sys

    if sys.platform != "win32" or not hwnd:
        return ""
    try:
        import ctypes

        user32 = ctypes.windll.user32
        length = int(user32.GetWindowTextLengthW(hwnd) or 0)
        buffer = ctypes.create_unicode_buffer(length + 2)
        user32.GetWindowTextW(hwnd, buffer, length + 2)
        return str(buffer.value or "").strip()
    except Exception:
        return ""


def _hwnd_for_title(title: str) -> int:
    """Handle of a visible, non-minimised window with exactly this title, else 0."""
    import sys

    wanted = str(title or "").strip()
    if sys.platform != "win32" or not wanted:
        return 0
    try:
        import ctypes

        user32 = ctypes.windll.user32
        hwnd = int(user32.FindWindowW(None, wanted) or 0)
        if not hwnd or not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd):
            return 0
        return hwnd
    except Exception:
        return 0


def _named_window_target(title: str) -> tuple[dict[str, object] | None, str, int]:
    """Resolve an explicit capture target as (target, refusal_reason, hwnd).

    There is no fallback path here on purpose. Cropping the screen rectangle of a
    window that is not frontmost would capture whatever is painted on top of it,
    so a target that is not the current foreground window is refused rather than
    captured, and an obscured window is never substituted by the whole desktop.
    """
    wanted = str(title or "").strip()
    if not wanted:
        return None, "target_window_title_required", 0
    hwnd = _hwnd_for_title(wanted)
    if not hwnd:
        return None, "target_window_not_found", 0
    if _window_title(hwnd) != wanted:
        return None, "target_window_title_mismatch", hwnd
    if _foreground_hwnd() != hwnd:
        return None, "target_window_not_foreground", hwnd
    target = _window_target_for_hwnd(hwnd)
    if target is None:
        return None, "target_window_geometry_unusable", hwnd
    return target, "", hwnd


def _marker_list(value: object) -> list[str]:
    if value is None:
        return []
    items = value if isinstance(value, (list, tuple)) else [value]
    return [str(item).strip() for item in items if str(item or "").strip()][:12]


def _markers_matched(text: str, markers: list[str]) -> int:
    """Count markers present in OCR text, ignoring whitespace and casing.

    OCR inserts its own spaces and line breaks, so the two sides are compared as
    compacted strings rather than as literal substrings.
    """
    compact = "".join(str(text or "").lower().split())
    return sum(1 for marker in markers if "".join(marker.lower().split()) in compact)


def _window_target_for_hwnd(hwnd: int) -> dict[str, object] | None:
    """Measure one window into a bounded PIL capture rectangle.

    The rect is clamped to the primary monitor and returned as explicit
    left/top/right/bottom instead of an hwnd: a maximized window reports an
    origin of about (-7, -7) for its invisible resize border, and the dxcam
    backend answers a region outside the screen with an empty frame. Clamping is
    therefore what makes a maximized study window capturable at all.

    Returns None when there is no usable study surface to capture, so the caller
    refuses or falls back instead of OCR-ing the plugin's own UI.
    """
    import sys

    if sys.platform != "win32":
        return None
    try:
        import ctypes

        class _Rect(ctypes.Structure):
            _fields_ = [
                ("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long),
            ]

        user32 = ctypes.windll.user32
        if not hwnd or not user32.IsWindowVisible(hwnd):
            return None
        if user32.IsIconic(hwnd):
            return None
        length = int(user32.GetWindowTextLengthW(hwnd) or 0)
        buffer = ctypes.create_unicode_buffer(length + 2)
        user32.GetWindowTextW(hwnd, buffer, length + 2)
        title = str(buffer.value or "").strip()
        if not title:
            return None
        if any(marker in title for marker in _ACTIVE_WINDOW_SELF_MARKERS):
            return None
        rect = _Rect()
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return None
        primary_w = int(user32.GetSystemMetrics(0) or 0)
        primary_h = int(user32.GetSystemMetrics(1) or 0)
        if primary_w <= 0 or primary_h <= 0:
            return None
        if int(rect.right) <= 0 or int(rect.bottom) <= 0:
            return None
        if int(rect.left) >= primary_w or int(rect.top) >= primary_h:
            return None
        left = max(0, int(rect.left))
        top = max(0, int(rect.top))
        right = min(primary_w, int(rect.right))
        bottom = min(primary_h, int(rect.bottom))
        if right - left < _ACTIVE_WINDOW_MIN_SIDE or bottom - top < _ACTIVE_WINDOW_MIN_SIDE:
            return None
        return {
            "title": title[:_ACTIVE_WINDOW_TITLE_LIMIT],
            "left": left,
            "top": top,
            "right": right,
            "bottom": bottom,
            # Named capture measures this rectangle under thread DPI awareness.
            "screen_width": primary_w,
            "screen_height": primary_h,
        }
    except Exception:
        return None


def _capture_named_window_image(title: str):
    from PIL import ImageGrab
    from .study_capture_backends import _run_with_thread_dpi_awareness

    def capture():
        target, refusal, hwnd = _named_window_target(title)
        if refusal or target is None:
            raise RuntimeError(refusal or "target_window_not_found")
        box = tuple(int(target[key]) for key in ("left", "top", "right", "bottom"))
        verified, refusal, verified_hwnd = _named_window_target(title)
        if refusal or verified_hwnd != hwnd or verified != target:
            raise RuntimeError(refusal or "target_window_changed_before_capture")
        frame = ImageGrab.grab(bbox=box)
        if _foreground_hwnd() != hwnd or _window_title(hwnd) != title:
            raise RuntimeError("target_window_changed_during_capture")
        return frame, target, hwnd

    # Measure and grab in one physical-pixel coordinate space, then restore the thread.
    return _run_with_thread_dpi_awareness(capture)


class _OcrEntriesMixin:
    @plugin_entry(
        id="study_dependency_status",
        name=tr(
            "entries.dependency_status.name", default="Study OCR Dependency Status"
        ),
        description=tr(
            "entries.dependency_status.description",
            default="Inspect RapidOCR, Tesseract, and capture dependencies used by study_companion.",
        ),
        input_schema={"type": "object", "properties": {}},
        llm_result_fields=["missing_installable"],
    )
    async def study_dependency_status(self, **_):
        status = await self._refresh_dependency_status()
        await self._persist_state()
        return Ok(status)

    @plugin_entry(
        id="study_ocr_snapshot",
        name=tr("entries.ocr_snapshot.name", default="Study OCR Snapshot"),
        description=tr(
            "entries.ocr_snapshot.description",
            default="Read only an explicitly named foreground learning window with required content markers.",
        ),
        input_schema={
            "type": "object",
            "required": ["capture_mode", "window_title", "expected_markers"],
            "properties": {
                "capture_mode": {
                    "type": "string",
                    "enum": ["target_window"],
                },
                "window_title": {
                    "type": "string",
                    "default": "",
                    "description": "target_window only: exact title of the window to capture.",
                },
                "expected_markers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": [],
                    "description": (
                        "target_window only: text that must be readable in the captured "
                        "region, proving the target really was the captured source."
                    ),
                },
                "min_marker_matches": {"type": "integer", "default": 1},
                "allow_fullscreen_fallback": {"type": "boolean", "enum": [False], "default": False},
            },
        },
        timeout=90.0,
        llm_result_fields=[
            "summary",
            "status",
            "diagnostic",
            "capture_mode_requested",
            "capture_mode_used",
            "interactive_fallback_reason",
            "active_window_fallback_reason",
            "active_window_capture_detail",
            "active_window_capture_route",
            "capture_target_title",
            "target_window_markers_matched",
            "target_window_title",
        ],
    )
    async def study_ocr_snapshot(self, capture_mode: str = "", allow_fullscreen_fallback: bool = False, **kwargs):
        if capture_mode != "target_window":
            return Err(SdkError("TARGET_WINDOW_REFUSED: explicit target_window mode is required", code="TARGET_WINDOW_REFUSED"))
        if self._ocr_pipeline is None:
            return Err(SdkError("study OCR pipeline is not initialized"))
        title = str(kwargs.get("window_title") or "").strip()
        target_markers = _marker_list(kwargs.get("expected_markers"))
        if not title or not target_markers:
            return Err(SdkError("TARGET_WINDOW_REFUSED: window_title and expected_markers are required", code="TARGET_WINDOW_REFUSED"))
        try:
            frame, target, target_hwnd = await asyncio.to_thread(_capture_named_window_image, title)
            from .study_capture_backends import _crop_image_to_profile
            from .study_ocr_pipeline import StudyCaptureProfile

            profile = StudyCaptureProfile(
                left_inset_ratio=self._cfg.ocr_left_inset_ratio,
                right_inset_ratio=self._cfg.ocr_right_inset_ratio,
                top_ratio=self._cfg.ocr_top_ratio,
                bottom_inset_ratio=self._cfg.ocr_bottom_inset_ratio,
            )
            target_frame = _crop_image_to_profile(frame, profile)
            snapshot = await asyncio.to_thread(self._ocr_pipeline.snapshot_from_image, target_frame)
        except Exception as exc:
            return Err(SdkError(f"TARGET_WINDOW_REFUSED: target_window_capture: {exc}", code="TARGET_WINDOW_REFUSED"))
        if str(getattr(snapshot, "status", "")) not in {"ok", "empty"}:
            return Err(SdkError("TARGET_WINDOW_REFUSED: target_window OCR failed", code="TARGET_WINDOW_REFUSED"))
        capture_mode_used = "target_window"
        target_markers_matched = 0
        if capture_mode == "target_window":
            # A window can be covered between the identity check and the grab, so the
            # foreground owner is read again and the captured text itself has to prove
            # which window was really OCR-ed before anything leaves this process.
            if await asyncio.to_thread(_foreground_hwnd) != target_hwnd:
                return Err(
                    SdkError(
                        "TARGET_WINDOW_REFUSED: target_window_capture: target_lost_foreground",
                        code="TARGET_WINDOW_REFUSED",
                    )
                )
            minimum = max(1, int(kwargs.get("min_marker_matches") or 1))
            target_markers_matched = _markers_matched(snapshot.text, target_markers)
            if target_markers_matched < minimum:
                # Refusing here is what keeps an unexpected window's content out of both
                # the payload and the persisted last-OCR state.
                return Err(
                    SdkError(
                        "TARGET_WINDOW_CONTENT_MISMATCH: target_window_capture: content_mismatch "
                        f"({target_markers_matched} of {minimum} required markers)",
                        code="TARGET_WINDOW_CONTENT_MISMATCH",
                    )
                )
        payload = build_ocr_payload(snapshot)
        payload["capture_mode_requested"] = capture_mode
        payload["capture_mode_used"] = capture_mode_used
        payload["capture_target_title"] = title
        payload["active_window_capture_route"] = "pil_bbox_crop"
        payload["target_window_markers_matched"] = target_markers_matched
        payload["target_window_title"] = title
        if self._supervision is not None:
            sensor_available = snapshot.status in {"ok", "empty"}
            payload["supervision"] = self._supervision.observe_activity(
                ocr_text=snapshot.text,
                sensor_available=sensor_available,
            )
        if snapshot.text.strip():
            async with self._lock:
                self._state.last_ocr_text = snapshot.text
                self._state.last_ocr_at = snapshot.captured_at
            payload["screen_classification"] = await self._update_screen_classification(
                snapshot.text, update_empty=False
            )
        elif snapshot.status == "empty":
            payload["screen_classification"] = await self._update_screen_classification(
                "", update_empty=True
            )
        await self._persist_state()
        return Ok(payload)

    @plugin_entry(
        id="study_install_tesseract",
        name=tr(
            "entries.install_tesseract.name", default="Install Tesseract for Study OCR"
        ),
        description=tr(
            "entries.install_tesseract.description",
            default="Install local Tesseract OCR for study_companion and refresh dependency status.",
        ),
        input_schema={
            "type": "object",
            "properties": {"force": {"type": "boolean", "default": False}},
        },
        timeout=300.0,
        llm_result_fields=["summary"],
    )
    async def study_install_tesseract(self, force: bool = False, **kwargs):
        async with self._lock:
            if self._install_in_progress:
                return Err(SdkError("Tesseract install is already running"))
            self._install_in_progress = True
        try:
            run_id = self._resolve_current_run_id(kwargs)
            result = await tesseract_support.install_tesseract(
                logger=self.logger,
                configured_path=self._cfg.ocr_tesseract_path,
                install_target_dir_raw=self._cfg.ocr_install_target_dir,
                manifest_url=self._cfg.ocr_install_manifest_url,
                timeout_seconds=self._cfg.ocr_install_timeout_seconds,
                languages=self._cfg.ocr_languages,
                force=bool(force),
                task_id=run_id or None,
                plugin_id=self.plugin_id,
                progress_callback=self._resolve_install_progress_callback(run_id),
            )
            await self._refresh_dependency_status()
            await self._persist_state()
            return Ok(
                {
                    "summary": str(result.get("summary") or "Tesseract is ready"),
                    "install_result": result,
                }
            )
        except Exception as exc:
            return _entry_exception_error(
                self,
                exc,
                operation="study_install_tesseract",
                message=f"Tesseract install failed: {exc}",
            )
        finally:
            async with self._lock:
                self._install_in_progress = False

    @plugin_entry(
        id="study_download_rapidocr_models",
        name=tr(
            "entries.download_rapidocr_models.name",
            default="Download RapidOCR Models for Study OCR",
        ),
        description=tr(
            "entries.download_rapidocr_models.description",
            default="Download missing RapidOCR model files for the configured study_companion OCR language.",
        ),
        input_schema={
            "type": "object",
            "properties": {"force": {"type": "boolean", "default": False}},
        },
        timeout=600.0,
        llm_result_fields=["summary"],
    )
    async def study_download_rapidocr_models(self, force: bool = False, **kwargs):
        async with self._lock:
            if self._rapidocr_models_in_progress:
                return Err(SdkError("RapidOCR model download is already running"))
            self._rapidocr_models_in_progress = True
        try:
            run_id = self._resolve_current_run_id(kwargs)
            result = await rapidocr_support.download_rapidocr_models(
                logger=self.logger,
                install_target_dir_raw=self._cfg.rapidocr_install_target_dir,
                ocr_version=self._cfg.rapidocr_ocr_version,
                lang_type=self._cfg.rapidocr_lang_type,
                timeout_seconds=float(self._cfg.ocr_install_timeout_seconds or 180.0),
                force=bool(force),
                task_id=run_id or None,
                plugin_id=self.plugin_id,
                progress_callback=self._resolve_install_progress_callback(run_id),
                before_completed_callback=lambda: None,
                install_state_updater=update_install_task_state,
            )
            await self._refresh_dependency_status()
            await self._persist_state()
            downloaded = result.get("downloaded") or []
            return Ok(
                {
                    "summary": (
                        f"RapidOCR models ready ({len(downloaded)} file(s) downloaded)"
                        if downloaded
                        else "RapidOCR models already present"
                    ),
                    "download_result": result,
                }
            )
        except Exception as exc:
            return _entry_exception_error(
                self,
                exc,
                operation="study_download_rapidocr_models",
                message=f"RapidOCR model download failed: {exc}",
            )
        finally:
            async with self._lock:
                self._rapidocr_models_in_progress = False
