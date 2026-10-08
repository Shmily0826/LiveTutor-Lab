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
from .interactive_screenshot import (
    InteractiveCaptureError,
    capture_interactive_region,
)
from .models import OcrSnapshot


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

    The pipeline already knows how to crop to a target (`capture_snapshot` with a
    target + the capture backends' profile insets); this only supplies the target.

    The rect is clamped to the primary monitor and returned as explicit
    left/top/right/bottom instead of an hwnd: a maximized window reports an
    origin of about (-7, -7) for its invisible resize border, and the dxcam
    backend answers a region outside the screen with an empty frame. Clamping is
    therefore what makes a maximized study window capturable at all.

    Returns None when there is no usable study surface in front, so the caller
    falls back to fullscreen instead of OCR-ing the plugin's own UI.
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
        hwnd = int(user32.GetForegroundWindow() or 0)
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
        left = max(0, min(int(rect.left), primary_w - _ACTIVE_WINDOW_MIN_SIDE))
        top = max(0, min(int(rect.top), primary_h - _ACTIVE_WINDOW_MIN_SIDE))
        right = min(primary_w, max(int(rect.right), left + _ACTIVE_WINDOW_MIN_SIDE))
        bottom = min(primary_h, max(int(rect.bottom), top + _ACTIVE_WINDOW_MIN_SIDE))
        return {
            "title": title[:_ACTIVE_WINDOW_TITLE_LIMIT],
            "left": left,
            "top": top,
            "right": right,
            "bottom": bottom,
            # The measurement space above follows this process's DPI awareness,
            # which is not necessarily the space PIL's screen grab uses; the
            # caller rescales against these to crop deterministically.
            "screen_width": primary_w,
            "screen_height": primary_h,
        }
    except Exception:
        return None


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
            default="Run a lightweight OCR snapshot. Phase 1 attempts fullscreen capture and returns diagnostics on failure.",
        ),
        input_schema={
            "type": "object",
            "properties": {
                "capture_mode": {
                    "type": "string",
                    "enum": ["fullscreen", "interactive", "active_window"],
                    "default": "fullscreen",
                },
                "allow_fullscreen_fallback": {"type": "boolean", "default": True},
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
        ],
    )
    async def study_ocr_snapshot(self, capture_mode: str = "fullscreen", allow_fullscreen_fallback: bool = True, **kwargs):
        if self._ocr_pipeline is None:
            return Err(SdkError("study OCR pipeline is not initialized"))
        if capture_mode not in {"fullscreen", "interactive", "active_window"}:
            return Err(SdkError("invalid capture_mode"))
        capture_mode_used = capture_mode
        interactive_fallback_reason = ""
        active_window_fallback_reason = ""
        active_window_capture_detail = ""
        active_window_capture_route = ""
        capture_target_title = ""
        if capture_mode == "active_window":
            target = await asyncio.to_thread(_foreground_window_target)
            snapshot = None
            if target is None:
                active_window_capture_detail = "no_usable_foreground_window"
            else:
                snapshot = await asyncio.to_thread(
                    self._ocr_pipeline.capture_snapshot, target
                )
                if str(getattr(snapshot, "status", "")) == "capture_failed":
                    active_window_capture_detail = str(
                        getattr(snapshot, "diagnostic", "") or "capture failed"
                    )[:200]
                    snapshot = None
                else:
                    capture_target_title = str(target.get("title") or "")
                    active_window_capture_route = "pipeline_target"
                if snapshot is None:
                    # The region-aware capture backends (dxcam/mss/pyautogui) are not
                    # guaranteed to be present in the packaged runtime, while the
                    # fullscreen path works through PIL. Take one PIL grab and crop it
                    # to the target rect instead of failing the whole capture.
                    try:
                        from PIL import ImageGrab

                        frame = await asyncio.to_thread(lambda: ImageGrab.grab())
                        width, height = frame.size
                        screen_w = int(target.get("screen_width") or 0)
                        screen_h = int(target.get("screen_height") or 0)
                        scale_x = (width / screen_w) if screen_w and width else 1.0
                        scale_y = (height / screen_h) if screen_h and height else 1.0
                        box = (
                            max(0, int(int(target["left"]) * scale_x)),
                            max(0, int(int(target["top"]) * scale_y)),
                            min(width, int(int(target["right"]) * scale_x)),
                            min(height, int(int(target["bottom"]) * scale_y)),
                        )
                        if (
                            box[2] - box[0] < _ACTIVE_WINDOW_MIN_SIDE
                            or box[3] - box[1] < _ACTIVE_WINDOW_MIN_SIDE
                        ):
                            raise RuntimeError(f"cropped region too small: {box}")
                        # Honour the same configured insets the pipeline's own
                        # target path applies, so the two routes are equivalent.
                        from .study_capture_backends import _crop_image_to_profile
                        from .study_ocr_pipeline import StudyCaptureProfile

                        config = self._cfg
                        profile = StudyCaptureProfile(
                            left_inset_ratio=config.ocr_left_inset_ratio,
                            right_inset_ratio=config.ocr_right_inset_ratio,
                            top_ratio=config.ocr_top_ratio,
                            bottom_inset_ratio=config.ocr_bottom_inset_ratio,
                        )
                        target_frame = _crop_image_to_profile(frame.crop(box), profile)
                        cropped = await asyncio.to_thread(
                            self._ocr_pipeline.snapshot_from_image, target_frame
                        )
                        if str(getattr(cropped, "status", "")) != "capture_failed":
                            snapshot = cropped
                            capture_target_title = str(target.get("title") or "")
                            active_window_capture_route = "pil_bbox_crop"
                        else:
                            active_window_capture_detail = (
                                active_window_capture_detail
                                + " | pil_bbox_crop: "
                                + str(getattr(cropped, "diagnostic", "") or "capture failed")
                            )[:240]
                    except Exception as exc:
                        active_window_capture_detail = (
                            active_window_capture_detail + " | pil_bbox_crop: " + str(exc)
                        )[:240]
            if snapshot is None:
                if not allow_fullscreen_fallback:
                    return Err(
                        SdkError(
                            "active_window_capture: "
                            + (active_window_capture_detail or "capture failed"),
                            code="ACTIVE_WINDOW_CAPTURE_FAILED",
                        )
                    )
                capture_mode_used = "fullscreen"
                active_window_fallback_reason = (
                    "no_usable_foreground_window"
                    if target is None
                    else "active_window_capture_failed"
                )
                snapshot = await asyncio.to_thread(self._ocr_pipeline.capture_snapshot)
        elif capture_mode == "interactive":
            try:
                capture = await capture_interactive_region(
                    lanlan_name=_ocr_request_lanlan(kwargs)
                )
            except InteractiveCaptureError as exc:
                if not allow_fullscreen_fallback:
                    return _entry_exception_error(self, exc, operation="study_ocr_snapshot")
                exc_text = str(exc)
                interactive_fallback_reason = next(
                    (
                        code
                        for code in (
                            "no_renderer",
                            "main_server_unavailable",
                            "interactive_unavailable",
                            "capture_busy",
                        )
                        if code in exc_text
                    ),
                    "",
                )
                if not interactive_fallback_reason:
                    return _entry_exception_error(
                        self,
                        exc,
                        operation="study_ocr_snapshot",
                    )
                capture_mode_used = "fullscreen"
                snapshot = await asyncio.to_thread(self._ocr_pipeline.capture_snapshot)
            else:
                if capture.canceled:
                    payload = build_ocr_payload(OcrSnapshot(status="canceled"))
                    payload["capture_mode_requested"] = "interactive"
                    payload["capture_mode_used"] = "interactive"
                    return Ok(payload)
                if capture.image is None:
                    return Err(SdkError("interactive_capture: missing_image_data"))
                snapshot = await asyncio.to_thread(
                    self._ocr_pipeline.snapshot_from_image,
                    capture.image,
                )
        else:
            snapshot = await asyncio.to_thread(self._ocr_pipeline.capture_snapshot)
        payload = build_ocr_payload(snapshot)
        payload["capture_mode_requested"] = capture_mode
        payload["capture_mode_used"] = capture_mode_used
        if capture_mode == "interactive":
            payload["capture_mode_requested"] = "interactive"
            payload["capture_mode_used"] = capture_mode_used
            if interactive_fallback_reason:
                payload["interactive_fallback_reason"] = interactive_fallback_reason
        elif capture_mode == "active_window":
            payload["capture_mode_requested"] = "active_window"
            payload["capture_mode_used"] = capture_mode_used
            if active_window_fallback_reason:
                payload["active_window_fallback_reason"] = (
                    active_window_fallback_reason
                )
                if active_window_capture_detail:
                    payload["active_window_capture_detail"] = (
                        active_window_capture_detail
                    )
            elif capture_target_title:
                payload["capture_target_title"] = capture_target_title
                if active_window_capture_route:
                    payload["active_window_capture_route"] = (
                        active_window_capture_route
                    )
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
