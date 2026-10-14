"""Run the real N.E.K.O desktop avatar against the isolated tutor host.

The packaged ``N.E.K.O.exe`` is the product surface the learner should meet: an
always-on-top Live2D pet with its own chat window. It normally spawns its own
frozen backend, so this launcher attaches it to the source host that is already
listening on the default port triplet instead.

Two environment facts make the difference between a working avatar and a silent
failure, both measured rather than inferred:

* ``ELECTRON_RUN_AS_NODE=1`` is exported by the ambient shell. Left in place the
  binary degrades to bare Node, creates no window and looks like a hang.
* This machine's GPU path crashes Chromium (``0xC0000005`` in the GPU process),
  so software rendering flags are required.

The shell is launched with ``LOCALAPPDATA``/``APPDATA`` pointed at the project's
disposable store, so it reads the tutor's configuration and never the user's own.
"""
from __future__ import annotations

import argparse
import ctypes
import json
import os
import subprocess
import sys
import time
import urllib.request
from ctypes import wintypes
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "benchmarks/raw/neko-app"
EXE = APP / "N.E.K.O.exe"
EVIDENCE = ROOT / "benchmarks/raw/evidence"
PID_FILE = ROOT / "benchmarks/raw/neko-avatar-shell.pid"
MAIN_PORT = 48911
FLAGS = ["--disable-gpu", "--disable-gpu-sandbox", "--no-sandbox"]
FROZEN_BACKEND = "projectneko_server.exe"
USERDATA_DIRNAME = "electron-userdata"

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
u32 = ctypes.WinDLL("user32", use_last_error=True)
EnumProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


class _Entry(ctypes.Structure):
    _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                ("th32ProcessID", wintypes.DWORD),
                ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
                ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", ctypes.c_long),
                ("dwFlags", wintypes.DWORD), ("szExeFile", wintypes.WCHAR * 260)]


def processes() -> list[tuple[int, str]]:
    handle = k32.CreateToolhelp32Snapshot(0x00000002, 0)
    found: list[tuple[int, str]] = []
    if handle != -1:
        entry = _Entry()
        entry.dwSize = ctypes.sizeof(entry)
        ok = k32.Process32FirstW(handle, ctypes.byref(entry))
        while ok:
            found.append((int(entry.th32ProcessID), entry.szExeFile))
            ok = k32.Process32NextW(handle, ctypes.byref(entry))
        k32.CloseHandle(handle)
    return found


def windows_of(pid: int) -> list[dict]:
    found: list[dict] = []

    def callback(hwnd, _param):
        owner = wintypes.DWORD()
        u32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid:
            length = u32.GetWindowTextLengthW(hwnd)
            title = ctypes.create_unicode_buffer(length + 1)
            u32.GetWindowTextW(hwnd, title, length + 1)
            box = wintypes.RECT()
            u32.GetWindowRect(hwnd, ctypes.byref(box))
            found.append({"visible": bool(u32.IsWindowVisible(hwnd)),
                          "title": title.value,
                          "width": box.right - box.left,
                          "height": box.bottom - box.top})
        return True

    u32.EnumWindows(EnumProc(callback), 0)
    return found


def host_ready() -> bool:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(f"http://127.0.0.1:{MAIN_PORT}/health", timeout=5) as response:
            return json.loads(response.read()).get("status") == "ok"
    except Exception:  # noqa: BLE001 - a missing host simply is not ready
        return False


def write_surface_config(store: Path, chat_surface: str = "full") -> Path:
    """Ask the shell for the standalone full chat window through its own setting.

    ``/chat`` is a compact-only host: ``coerceChatSurfaceModeForHost`` in
    ``app-react-chat-window/bootstrap-state-and-geometry.js`` maps ``full`` back
    to ``compact`` there, so no renderer call can widen the capsule. The product
    answer is a second window that loads ``/chat_full``, and the shell creates it
    at startup when ``core_config.txt`` says ``chatSurfaceMode: "full"``
    (``storage-gate.js`` ``maybeCreateStartupReactChat``) - the same state the tray
    menu "聊天窗口形态" writes.

    The shell reads this file verbatim instead of merging it over the packaged
    defaults. On first launch the shipped ``resources/core_config.txt`` is the
    starting point; later launches keep the persisted configuration and update
    only the fields required for this tutor attachment.
    """
    userdata = store / USERDATA_DIRNAME
    userdata.mkdir(parents=True, exist_ok=True)
    bundled = APP / "resources/core_config.txt"
    path = userdata / "core_config.txt"
    source = path if path.is_file() else bundled
    try:
        config = json.loads(source.read_text(encoding="utf-8-sig"))
        if not isinstance(config, dict):
            raise ValueError("configuration must be an object")
    except (OSError, ValueError) as error:
        raise RuntimeError(f"原生壳配置无法读取，已保留原文件：{source}") from error
    config["apiBaseUrl"] = f"http://localhost:{MAIN_PORT}/"
    config["chatSurfaceMode"] = chat_surface
    config["startupDefaultForm"] = "model"
    config["portableUpdateAutoCheck"] = False
    path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    return path


def shell_environment(store: Path) -> dict[str, str]:
    env = dict(os.environ)
    env.pop("ELECTRON_RUN_AS_NODE", None)
    env.update({
        "NEKO_STORAGE_SELECTED_ROOT": str(store),
        "NEKO_STORAGE_ANCHOR_ROOT": str(store),
        "NEKO_STORAGE_CLOUDSAVE_ROOT": str(store),
        "NEKO_USER_DATA_DIR": str(store / USERDATA_DIRNAME),
        "LOCALAPPDATA": str(store),
        "APPDATA": str(store),
        "PYTHONIOENCODING": "utf-8",
    })
    return env


def launch(store: Path, wait_seconds: int = 150, chat_surface: str = "full",
           cdp_port: int | None = None, audio_input: str | None = None) -> dict:
    """Start the avatar shell and prove it attached to the host we control."""
    from neko_desktop_tutor_host import require_task_audio_allowed
    require_task_audio_allowed("Native avatar shell")
    if not EXE.is_file():
        raise RuntimeError(f"找不到 N.E.K.O 桌面程序：{EXE}")
    if not host_ready():
        raise RuntimeError("教学宿主还没就绪，原生角色会自己去启动冻结后端，拒绝这样打开。")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    log_path = EVIDENCE / f"neko-avatar-shell-{stamp}.log"
    config_path = write_surface_config(store, chat_surface)
    backend_pids = {pid for pid, name in processes() if name.lower() == FROZEN_BACKEND}
    handle = log_path.open("wb")
    # The debugging port is only ever passed by the acceptance probes; the
    # learner-facing launcher runs without it so no local process can drive the
    # avatar window.
    flags = [*FLAGS] + ([f"--remote-debugging-port={cdp_port}"] if cdp_port else [])
    if audio_input:
        # Feed a recorded wav in place of the microphone and skip the permission prompt,
        # so a voice acceptance run never leaves the room open to listen all night. The
        # product path is unchanged: the renderer still calls getUserMedia.
        #
        # The fake *device* flag is not decoration. The app hides its mic button when
        # enumerateDevices() reports no audio input at all, so without it the file alone
        # leaves the voice entry invisible and the run proves nothing.
        #
        # Resolve before passing it on: the shell starts with cwd=neko-app, so a relative
        # path is accepted by Chromium and then yields a silent stream. The host still
        # reports 200 chunks per 2s with rnnoise probability 0.0, which looks like a
        # working microphone and a quiet room rather than a missing file.
        wav = Path(audio_input).resolve()
        if not wav.is_file():
            raise RuntimeError(f"测试音频不存在：{audio_input}")
        flags += [f"--use-file-for-fake-audio-capture={wav.as_posix()}",
                  "--use-fake-device-for-media-stream",
                  "--use-fake-ui-for-media-stream"]
    process = subprocess.Popen([str(EXE), *flags], cwd=str(APP), env=shell_environment(store),
                               stdout=handle, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
    started = time.monotonic()
    seen: list[dict] = []
    frozen: list[int] = []
    outcome: dict[str, object] = {"pid": process.pid, "status": "starting"}
    try:
        while time.monotonic() - started < wait_seconds:
            time.sleep(3)
            frozen = [pid for pid, name in processes()
                      if name.lower() == FROZEN_BACKEND and pid not in backend_pids]
            if frozen:
                break
            seen = [item for item in windows_of(process.pid) if item["visible"] and item["width"] > 60]
            pet = [item for item in seen if "Terminal" in item["title"] or "N.E.K.O" in item["title"]]
            if pet and host_ready():
                outcome.update({"status": "attached", "windows": seen, "ready_seconds":
                                round(time.monotonic() - started, 1),
                                "chat_surface": chat_surface, "config": str(config_path)})
                break
            if process.poll() is not None:
                outcome.update({"status": "exited", "returncode": process.poll(), "windows": seen})
                break
    finally:
        handle.close()
    if frozen:
        # The frozen backend carries no text-only audio gate and would read the
        # user's own provider settings: never leave it running.
        for pid in frozen:
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
        shutdown(outcome)
        raise RuntimeError(
            "原生壳没有 attach，而是自己拉起了冻结后端 "
            f"{frozen}，已终止并关闭角色。请确认教学宿主占用 {MAIN_PORT} 后重试。")
    if outcome.get("status") != "attached":
        shutdown(outcome)
        raise RuntimeError(f"原生角色窗口未就绪：{outcome.get('status')}（日志 {log_path.name}）")
    PID_FILE.write_text(json.dumps({"pid": process.pid, "log": str(log_path)}), encoding="utf-8")
    outcome["log"] = str(log_path)
    return outcome


def shutdown(outcome: dict | None = None) -> None:
    pid = (outcome or {}).get("pid")
    if not pid and PID_FILE.is_file():
        try:
            pid = json.loads(PID_FILE.read_text(encoding="utf-8")).get("pid")
        except ValueError:
            pid = None
    if pid:
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
    PID_FILE.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", required=True, help="disposable app-data root for the shell")
    parser.add_argument("--wait", type=int, default=150)
    parser.add_argument("--chat-surface", choices=("full", "compact"), default="full",
                        help="聊天窗口形态：full 是独立完整聊天窗（有真正输入框）")
    parser.add_argument("--cdp-port", type=int, default=None,
                        help="仅验收脚本使用：给原生窗口开 DevTools 调试端口")
    parser.add_argument("--stop", action="store_true")
    parser.add_argument("--audio-input", default=None,
                        help="acceptance only: feed this wav to the renderer as the "
                             "microphone instead of leaving the room open to listen")
    args = parser.parse_args()
    if args.stop:
        shutdown()
        print(json.dumps({"stopped": True}))
        return 0
    try:
        outcome = launch(Path(args.store).resolve(), args.wait, args.chat_surface,
                         args.cdp_port, args.audio_input)
    except RuntimeError as error:
        print(f"原生角色启动失败：{error}", file=sys.stderr)
        return 1
    print(json.dumps(outcome, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
