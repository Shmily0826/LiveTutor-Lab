"""Start the isolated tutor host and open the real N.E.K.O desktop avatar.

Default: a four-hour session, 30 Study teaching requests inside a hard cap of 200
paid requests that also counts the character's own calls. Double-click
Start-Avatar.cmd (Start-Tutor.cmd is the same entry) or run this script with the
source host's Python. The learner talks to the Live2D character; ``--study-ui``
additionally opens the web panel as an auxiliary tool.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import threading
from contextlib import contextmanager
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import neko_desktop_tutor_host as host  # noqa: E402
import neko_native_shell as avatar  # noqa: E402

UI_PATH = "/plugin/study_companion/ui/"
HOST_SCRIPT = ROOT / "scripts/neko_desktop_tutor_host.py"
PRODUCT_STORE = "neko-product-data"

# Every status line this prints is Chinese; Start-Avatar.cmd sets the console to UTF-8, but
# running the script straight from a shell that defaults to cp1252 used to kill it on print
# #1, before the avatar ever appeared.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            pass
LESSON_SCRIPT = ROOT / "scripts/neko_flutter_lesson_window.py"
BROWSER_PROFILE = ROOT / "benchmarks/raw/neko-product-browser/profile"
BROWSER_OWNER_FILE = BROWSER_PROFILE.parent / "browser-owner.json"


def plugin_server_ready(timeout: float, launcher: subprocess.Popen) -> tuple[bool, str]:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    deadline = time.monotonic() + timeout
    reason = "timed out"
    while time.monotonic() < deadline and launcher.poll() is None:
        try:
            # Static assets are mounted at registration, before the native worker starts.
            with opener.open(f"http://127.0.0.1:{host.PLUGIN_PORT}/plugins/study_companion", timeout=5) as response:
                plugin = json.loads(response.read()).get("plugin", {})
            entry_ids = {entry.get("id") for entry in plugin.get("entries", [])}
            if plugin.get("status") != "running":
                reason = f"Study plugin {plugin.get('status', 'not registered')}"
            elif not {"study_status", "study_explain_text", "study_ocr_snapshot"}.issubset(entry_ids):
                reason = "Study entries not ready"
            else:
                with opener.open(f"http://127.0.0.1:{host.PLUGIN_PORT}{UI_PATH}", timeout=5) as response:
                    if response.status == 200:
                        return True, ""
                    reason = f"UI HTTP {response.status}"
        except Exception as error:
            reason = f"{type(error).__name__}: {str(error)[:80]}"
        time.sleep(2)
    return False, reason


def chrome_command(url: str, *, text_only: bool = False) -> list[str]:
    if not text_only:
        host.require_task_audio_allowed("product browser with audio capabilities")
    candidates = [Path(os.environ[name]) / "Google/Chrome/Application/chrome.exe"
                  for name in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA") if os.environ.get(name)]
    chrome = next((path for path in candidates if path.is_file()), None)
    if chrome is None:
        raise RuntimeError("找不到 Chrome；请安装 Chrome 后再启动 Tutor。")
    return [str(chrome), f"--user-data-dir={BROWSER_PROFILE}", f"--app={url}", "--mute-audio",
            "--no-first-run", "--no-default-browser-check", "--disable-sync",
            "--disable-background-networking", "--disable-component-update",
            "--disable-features=MediaRouter"]


# Ownership of the browser tree is proved with kernel32 and killed with `taskkill /T`, with no
# third-party import in the exit path. That is a measured reason, not a style choice: the launcher
# runs on the vendored Python under `benchmarks/raw/goal-python`, which has **no psutil**, so
# `stop_owned_browser` raised `ModuleNotFoundError` from inside the session's `finally` and the
# browser - holding a fake microphone that replays its wav forever - outlived the teardown. That is
# how a paid allowance emptied while nobody was driving it. The guard test for this path injected a
# fake `psutil` into `sys.modules` and stayed green, the same failure as the folder chooser: an
# assertion written from the implementation cannot see the machine it runs on.
_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
_FILETIME_EPOCH_OFFSET = 11644473600.0
_STILL_ACTIVE = 259
# A pid reused by an unrelated program is off by minutes or hours; the same process agrees to well
# under a second. The tolerance keeps the check honest across two implementations of the clock.
PID_CLOCK_TOLERANCE_SECONDS = 1.0


def process_identity(pid: int) -> tuple[float | None, bool]:
    """(start time, still running) for one pid.

    `OpenProcess` alone cannot answer "is it alive": a terminated child that nobody has waited on
    keeps its kernel object - and its creation time - readable, which is exactly the state a killed
    browser is left in when the launcher is still holding the handle. The exit code is the truth.
    """
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
    if not handle:
        return None, False
    try:
        created, exited, kernel_time, user_time = (wintypes.FILETIME() for _ in range(4))
        if not kernel32.GetProcessTimes(handle, ctypes.byref(created), ctypes.byref(exited),
                                        ctypes.byref(kernel_time), ctypes.byref(user_time)):
            return None, False
        code = wintypes.DWORD()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
            return None, False
        stamp = (created.dwHighDateTime << 32) | created.dwLowDateTime
        return stamp / 1e7 - _FILETIME_EPOCH_OFFSET, code.value == _STILL_ACTIVE
    finally:
        kernel32.CloseHandle(handle)


def process_creation_time(pid: int) -> float | None:
    """When this pid started, or None when it is gone or has exited and not been waited on."""
    started, alive = process_identity(pid)
    return started if alive else None


def owned_browser_pids(record: list[dict]) -> list[int]:
    """The recorded pids that are still the same process - a reused pid is never stopped."""
    owned = []
    for item in record:
        try:
            pid, started = int(item["pid"]), float(item["created_at"])
        except (TypeError, ValueError, KeyError):
            continue
        live = process_creation_time(pid)
        if live is not None and abs(live - started) <= PID_CLOCK_TOLERANCE_SECONDS:
            owned.append(pid)
    return owned


def remember_browser_tree(browser: subprocess.Popen, record: list[dict]) -> None:
    """Record the root identity; `taskkill /T` reaches its children without enumerating them."""
    if browser.poll() is not None:
        return
    started = process_creation_time(browser.pid)
    if started is None or any(int(item.get("pid", -1)) == browser.pid for item in record):
        return
    record.append({"pid": int(browser.pid), "created_at": started})
    BROWSER_OWNER_FILE.write_text(json.dumps(record), encoding="utf-8")


def stop_owned_browser(record: list[dict]) -> None:
    stop_owned_tree(record)
    BROWSER_OWNER_FILE.unlink(missing_ok=True)


def stop_owned_tree(record: list[dict]) -> None:
    """Stop only recorded live instances, without consulting a shared PID file."""
    for pid in owned_browser_pids(record):
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                       capture_output=True, text=True, timeout=30)
    deadline = time.monotonic() + 10.0
    left = owned_browser_pids(record)
    while left and time.monotonic() < deadline:
        time.sleep(0.5)
        left = owned_browser_pids(record)
    if left:
        raise RuntimeError(f"本次任务进程尚未退出（pid {left}）；"
                           "保留所有权记录，请关闭学习窗口后重试。")


def speech_input_note() -> str:
    """Say up front whether the microphone can reach a recogniser at all.

    Pressing the mic and getting a toast that vanishes is the worst outcome for a
    learner, and the reason is not something they can see: the product routes speech
    by the character's Core provider, and that table only lists providers owning a
    speech worker.
    """
    try:
        import neko_local_asr_probe as speech
        status = speech.speech_route_status()
    except Exception as error:  # a status line must never stop the avatar from opening
        return f"语音输入状态没查成（{type(error).__name__}），按麦克风前先看宿主日志。"
    if not status["local_asr_available"]:
        return "语音输入：这台环境的宿主里没装本地识别（faster_whisper），按麦克风不会识别。"
    if status["core_route_known"]:
        return f"语音输入：本地识别已装好，麦克风路由（Core={status['core_effective']}）可用。"
    return (f"语音输入：本地识别（faster_whisper）这台机器已装好，但角色的服务商 Core={status['core_effective']} "
            "在产品自己的识别路由表里没有条目，所以现在按麦克风不会识别——不是缺安装。"
            "要接上得把 Core/realtime 槽换成带识别路由的服务商（qwen/openai/step/grok/glm/gemini），"
            "那会动到计费主体，得你决定；文本教学不受影响。")


def language_pin_note(store_root: Path) -> str:
    """Report the durable per-character teaching locale before the learner speaks.

    ``study_language`` writes this through the product's own language preference, and it
    silently survives restarts, so an avatar replying in English for no visible reason is
    a stored preference rather than a defect.
    """
    pins = {}
    for path in sorted(store_root.glob("memory/*/prompt_locale.json")):
        try:
            pins[path.parent.name] = json.loads(path.read_text(encoding="utf-8")).get("language")
        except Exception:  # unreadable preference is the same as no preference
            continue
    if not pins:
        return "教学语言：还没给任何角色钉过课程语言，第一次说「以后这门课用英文教学」才会写入。"
    # The hint has to name the *other* language: telling someone already pinned to Chinese
    # to "say 用中文教学 to change it back" is a sentence that does nothing.
    english = {str(value or "") for value in pins.values()} & {"en", "en-US"}
    hint = ("要改回来说「以后这门课用中文教学」即可" if english
            else "想换成英文就说「以后这门课用英文教学」")
    return "教学语言：已钉住 " + "、".join(f"{name}={value}" for name, value in pins.items()) + \
           f"（存在本项目隔离存储里，重启仍生效；{hint}）。"


def host_command(minutes: int, api_budget: int, egress_budget: int,
                 extra: list[str] | None = None, store: str = PRODUCT_STORE) -> list[str]:
    return [str(host.SOURCE_PYTHON), str(HOST_SCRIPT), "--source", "--store", store,
            "--hold", str(minutes * 60 + 120), "--seconds", "220", "--api-budget", str(api_budget),
            "--egress-budget", str(egress_budget), *(extra or [])]


def host_options(args, voice_hosts: list[str]) -> list[str]:
    options = []
    if args.text_only:
        options += ['--text-only']
    if args.offline_egress:
        options += ['--offline-egress']
    if args.voice:
        options += ['--voice', '--core-provider', 'free']
        options += sum([['--allow-host', f'{h}:{args.voice_connects}'] for h in voice_hosts], [])
    if args.budget_round:
        options += ['--budget-round', args.budget_round]
    if args.learning_surface:
        options += ['--study-vision']
    return options


class CoreProviderOverride:
    """Restore only the daily entry's temporary provider choice after its host stops."""
    def __init__(self, store: Path, runtime_provider: str):
        self.path = store / 'N.E.K.O/config/core_config.json'
        self.runtime_provider = runtime_provider
        if self.path.is_symlink() or not self.path.resolve().is_relative_to(store.resolve()):
            raise RuntimeError('日常 provider 配置路径已改变，保留当前文件。')
        self.existed = self.path.exists()
        self.present = False
        self.value = None
        if self.existed:
            saved = self._read()[1]
            self.present = 'coreApi' in saved
            self.value = saved.get('coreApi')

    def _read(self):
        if self.path.is_symlink() or not self.path.resolve().is_relative_to(self.path.parents[2].resolve()):
            raise RuntimeError('日常 provider 配置路径已改变，保留当前文件。')
        raw = self.path.read_bytes()
        saved = json.loads(raw.decode('utf-8'))
        if not isinstance(saved, dict):
            raise ValueError('日常 provider 配置必须是对象，保留当前文件。')
        return raw, saved

    def restore(self):
        # A new store retains its initial defaults. Never roll back all settings:
        # the learner may have changed unrelated keys while this host was open.
        if not self.existed:
            return
        with self._locked_config() as handle:
            saved = json.loads(handle.read().decode('utf-8'))
            if not isinstance(saved, dict):
                raise ValueError('日常 provider 配置必须是对象，保留当前文件。')
            if ('coreApi' in saved) == self.present and saved.get('coreApi') == self.value:
                return
            if saved.get('coreApi') != self.runtime_provider:
                raise RuntimeError('provider 已被另行更改，保留当前配置，不覆盖。')
            if self.present:
                saved['coreApi'] = self.value
            else:
                saved.pop('coreApi', None)
            # One deny-write/delete Windows handle covers read through flush. This
            # is an in-place update, not a crash-atomic replacement; abnormal exit
            # is reported as a limitation, never as preserved-setting proof.
            payload = json.dumps(saved, ensure_ascii=False, indent=2).encode('utf-8')
            handle.seek(0)
            handle.write(payload)
            handle.truncate()
            handle.flush()
            os.fsync(handle.fileno())

    @contextmanager
    def _locked_config(self):
        if os.name != 'nt':
            raise RuntimeError('provider 恢复需要 Windows 文件保护，保留当前配置。')
        import ctypes
        from ctypes import wintypes
        import msvcrt
        import stat
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        create = kernel.CreateFileW
        create.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                           wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        create.restype = wintypes.HANDLE
        close = kernel.CloseHandle
        close.argtypes = [wintypes.HANDLE]
        close.restype = wintypes.BOOL
        final_path = kernel.GetFinalPathNameByHandleW
        final_path.argtypes = [wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD]
        final_path.restype = wintypes.DWORD
        self._read()  # Reject an invalid/redirected target before requesting access.
        owned = create(str(self.path), 0xC0000000, 1, None, 3, 0x00200000, None)
        if owned == ctypes.c_void_p(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        fd = None
        try:
            buffer = ctypes.create_unicode_buffer(32768)
            length = final_path(owned, buffer, len(buffer), 0)
            if not length or length >= len(buffer):
                raise RuntimeError('无法核对锁定配置路径，保留当前文件。')
            resolved = buffer.value
            if resolved.startswith('\\\\?\\UNC\\'):
                resolved = '\\\\' + resolved[8:]
            elif resolved.startswith('\\\\?\\'):
                resolved = resolved[4:]
            if Path(resolved).resolve() != self.path.absolute():
                raise RuntimeError('锁定配置指向不同路径，保留当前文件。')
            fd = msvcrt.open_osfhandle(owned, os.O_RDWR | os.O_BINARY)
            owned = None  # fd now owns the Windows handle.
            info = os.fstat(fd)
            if info.st_nlink != 1 or getattr(info, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                raise RuntimeError('配置包含链接，保留当前文件。')
            with os.fdopen(fd, 'r+b') as stream:
                fd = None
                yield stream
        finally:
            if fd is not None:
                os.close(fd)
            if owned is not None:
                close(owned)


def cleanup_resources(surface, shell, launcher, launcher_owner, browser, browser_record, lesson):
    """One failing resource must never prevent the other owned resources from closing."""
    errors = []
    def attempt(name, action):
        try:
            action()
        except Exception as error:
            errors.append(f'{name}: {type(error).__name__}: {error}')
    if surface is not None:
        attempt('learning surface shutdown', surface.shutdown)
        attempt('learning surface close', surface.server_close)
    if shell is not None:
        attempt('avatar', lambda: avatar.shutdown(shell))
    if launcher.poll() is None:
        attempt('host tree', lambda: stop_owned_tree(launcher_owner))
        attempt('host wait', lambda: launcher.wait(timeout=20))
    if browser is not None:
        attempt('browser ownership', lambda: remember_browser_tree(browser, browser_record))
        attempt('browser tree', lambda: stop_owned_browser(browser_record))
    if lesson is not None and lesson.poll() is None:
        attempt('lesson', lesson.terminate)
    return errors


def round_balance_note(path: Path, round_id: str | None) -> str:
    """Say what is left in this round before the learner opens their mouth.

    The host owns the ledger; this only reads it. A round that is already spent looks
    exactly like a broken host from inside the character window (no reply, no error),
    so the entry has to name the difference up front.
    """
    if round_id is None:
        round_id = datetime.now(timezone.utc).strftime("round-%Y-%m-%d")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return f"轮次 {round_id}：账本还不存在，宿主启动时按限额新建。"
    spent = {str(k): int(v) for k, v in (data.get("spent") or {}).items()}
    if data.get("round") != round_id:
        return (f"轮次 {round_id}：账本里是上一轮 {data.get('round')}"
                f"（已用 {json.dumps(spent, ensure_ascii=False)}），本次按限额重新发额度。")
    parts = []
    for name, limit in (data.get("budgets") or {}).items():
        if limit is None:
            continue
        parts.append(f"{name} 剩 {max(0, int(limit) - spent.get(name, 0))} / {int(limit)}")
    return f"轮次 {round_id}（续用同一轮，不重新发额度）：" + "、".join(parts)


def lesson_command() -> list[str]:
    return [str(host.SOURCE_PYTHON), str(LESSON_SCRIPT)]


def code_cli() -> list[str]:
    """How to start CodeGraph without a shell, resolved once here for the whole session."""
    override = os.environ.get("LIVETUTOR_CODEGRAPH", "").strip()
    if override:
        return [override]
    found = (shutil.which("codegraph") or shutil.which("codegraph.cmd")
             or shutil.which("codegraph.CMD"))
    return [found] if found else []


def pick_code_root() -> str:
    """Ask the learner which project to authorize, from the desktop - no command line.

    Only the chooser is new: the directory goes through the same `authorize_code_project` path
    as `--code-root`, so the index location, the evidence prefix and the printed boundary notice
    stay identical however the project was named.
    """
    try:
        import tkinter
        from tkinter import filedialog
    except ImportError:
        print("代码问答：这个 Python 没有 tkinter，选不了目录；要授权项目就用 --code-root <目录>。")
        return ""
    root = tkinter.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        chosen = filedialog.askdirectory(
            parent=root, title="选择要授权给 Tutor 阅读源码的项目目录（取消 = 不改授权）",
            mustexist=True)
    finally:
        root.destroy()
    return str(chosen or "")


def code_root_action(chosen: str, interactive: bool) -> str:
    """Which of the three code-project entries this start should take.

    `keep` exists because a tty is not the same thing as a person: measured twice, an
    agent-launched run had a tty on stdin, so the modal chooser opened with nobody in front of
    the screen and the session never booted. A run that cannot answer a dialog has to be able to
    say "reuse the stored grant" and get past it - and `keep` must never be read as a path,
    because feeding it to `authorize_code_project` would revoke the very grant it keeps.
    """
    value = (chosen or "").strip()
    if value.lower() == "ask":
        return "picker"
    if value:
        return "reuse" if value.lower() == "keep" else "authorize"
    return "picker" if interactive else "reuse"


def authorize_code_project(root: Path, store: Path) -> dict:
    """Write the one project this session may read, after proving the index can serve it.

    The index is kept in the project's PARENT (`Sky Scout\\.codegraph\\`) on purpose: indexing
    the repository itself would drop a 38 MB directory inside the team's working tree. That is
    also why evidence paths arrive as `sky_scout/...` - the prefix the tool filters on is the
    authorized directory's own name, and everything the parent indexes besides it is what the
    read-only filter is there to keep out.
    """
    index_root = root.parent
    record_file = store / "plugins/study_companion/data/code_project.json"

    def revoke(reason: str) -> dict:
        """An authorization the learner asked for and did not get must not inherit the old one.

        Measured on the real UI: with `--code-root` pointing at a project that failed to index,
        the character went on answering from the previously authorized repository - so the
        learner's "stop reading that one" was silently ignored. Any explicit request that fails
        therefore clears the stored grant before it returns.
        """
        try:
            if record_file.is_file():
                record_file.unlink()
                print(f"代码问答：{reason}；已撤销上一次授权（旧项目不再可读）。")
            else:
                print(f"代码问答：{reason}；本轮没有授权任何项目。")
        except OSError as error:
            print(f"代码问答：{reason}，而且撤销旧授权也失败了（{error}）——"
                  f"请手动删除 {record_file}。")
        return {}

    cli = code_cli()
    if not cli:
        print("代码问答：没找到 CodeGraph CLI（PATH 里没有 codegraph），本轮角色不会读代码。"
              "要装它就跑 `npm i -g @codegraph/cli`，或用 LIVETUTOR_CODEGRAPH 指到可执行文件。")
        return {}
    if not root.is_dir():
        return revoke(f"--code-root 指向的目录不存在：{root}")
    status = subprocess.run([*cli, "status", str(index_root)], capture_output=True,
                            text=True, encoding="utf-8", errors="replace", timeout=120)
    # `codegraph status` prints "Not initialized" and still exits 0, so the return code alone
    # never reached the init branch: authorizing a project for the first time failed, and then
    # revoked the grant the learner already had. Measured through the real folder picker.
    if status.returncode != 0 or not (index_root / ".codegraph").is_dir():
        print(f"代码问答：{index_root.name} 还没有索引，正在初始化（只写 .codegraph，不碰你的代码）…")
        # `index` refuses an uninitialized project ("Run codegraph init first"), so a brand-new
        # directory used to fail first-time authorization every time. `init` is what builds it.
        built = subprocess.run([*cli, "init", str(index_root)], capture_output=True,
                               text=True, encoding="utf-8", errors="replace", timeout=1800)
        if built.returncode != 0:
            return revoke(f"索引初始化失败（{str(built.stderr or built.stdout)[:120]}）")
    else:
        synced = subprocess.run([*cli, "sync", str(index_root)], capture_output=True,
                                text=True, encoding="utf-8", errors="replace", timeout=900)
        if synced.returncode != 0:
            print(f"代码问答：索引没能同步到最新改动（{str(synced.stderr or synced.stdout)[:120]}），"
                  "角色仍会读到上次索引的内容。")
    listed = subprocess.run([*cli, "files", "-p", str(root), "--json"], capture_output=True,
                            text=True, encoding="utf-8", errors="replace", timeout=300)
    prefix = root.name + "/"
    try:
        paths = [entry.get("path", "") for entry in json.loads(listed.stdout or "[]")]
    except ValueError:
        paths = []
    inside = [path for path in paths if path.startswith(prefix)]
    commit = subprocess.run(["git", "-C", str(root), "rev-parse", "--short", "HEAD"],
                            capture_output=True, text=True, timeout=60).stdout.strip()
    record = {"root": str(root), "evidence_prefix": prefix, "name": root.name,
              "commit": commit, "indexed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
              "indexed_files_inside": len(inside), "indexed_files_outside": len(paths) - len(inside),
              "cli": cli[0]}
    if not inside:
        return revoke(f"索引里找不到 {prefix} 下的任何文件"
                      "（确认这个目录里有源码；.gitignore 也可能把它排除了）")
    data_dir = store / "plugins/study_companion/data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "code_project.json").write_text(json.dumps(record, ensure_ascii=False, indent=2),
                                                encoding="utf-8")
    os.environ["LIVETUTOR_CODEGRAPH"] = cli[0]
    evidence = ROOT / "benchmarks/raw/evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / f"neko-code-authorize-{record['indexed_at'].replace(':', '').replace('-', '')}.json"
     ).write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    siblings = sorted({path.split("/", 1)[0] for path in paths if not path.startswith(prefix)})
    named = f"（{', '.join(siblings[:6])}{'…' if len(siblings) > 6 else ''}）" if siblings else ""
    print(f"代码授权：{root}（git {commit or '非 git 目录'}），索引 {len(inside)} 个文件可作证据。")
    print(f"出境边界：只有 {prefix} 前缀内的路径会发给模型；索引里同级还有 "
          f"{len(siblings)} 个目录{named}"
          f"命中即丢弃，密钥形状的行会被就地涂掉。查询本身不花钱，也不走网络。")
    print(f"授权记录：{data_dir / 'code_project.json'}（删掉它角色就再也读不到代码）")
    return record


def main() -> int:
    global BROWSER_PROFILE, BROWSER_OWNER_FILE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--minutes", type=int, default=240, help="session limit in minutes (default: 4 hours)")
    parser.add_argument("--store", default=PRODUCT_STORE,
                        help="app-data directory under benchmarks/raw; use a fresh directory for acceptance")
    parser.add_argument("--api-budget", type=int, default=30, help="maximum model requests for this launch")
    parser.add_argument("--study-ui", action="store_true",
                        help="also open the Study web panel in a dedicated Chrome window")
    parser.add_argument("--learning-surface", action="store_true",
                        help="open controlled read-only diagrams with role highlighting")
    parser.add_argument("--egress-budget", type=int, default=200,
                        help="hard cap on every paid model request, character chat included; "
                             "0 opens the character with no paid call allowed at all")
    parser.add_argument("--cdp-port", type=int, default=0,
                        help="acceptance only: open a DevTools port on the native windows so "
                             "neko_native_avatar_tour.py can type into the character's own box")
    parser.add_argument("--voice", action="store_true",
                        help="run the avatar on the app-supplied free realtime Core and name the "
                             "native realtime audio events as the only exception to the mute")
    parser.add_argument('--text-only', action='store_true',
                        help='visible avatar and Study, muted and capture-free; use the text box')
    parser.add_argument('--offline-egress', action='store_true',
                        help='deny external model calls while inspecting the existing UI and records')
    parser.add_argument("--voice-host", default="www.lanlan.tech,www.lanlan.app",
                        help="realtime hosts to allow, comma-separated. Both are listed because the "
                             "app rewrites the mainland endpoint lanlan.tech to lanlan.app once its "
                             "own GeoIP lookup calls this machine overseas (core_config.py:795-821); "
                             "allowing only the configured name strands the run on a 403")
    parser.add_argument("--voice-connects", default="20",
                        help="CONNECT cap or 'unlimited' (connections, not turns); existing round ledger wins")
    parser.add_argument("--budget-round", default=None,
                        help="spending round label; restarts in the same round keep the balance")
    parser.add_argument("--chat-surface", choices=("full", "compact"), default=None,
                        help="which chat surface the avatar gets; the floating microphone is only "
                             "built when the pet page hosts #chat-container, i.e. compact, so a "
                             "voice run has to ask for it (default: full, compact with --voice)")
    parser.add_argument("--audio-input", default=None,
                        help="acceptance only: feed this wav to the renderer instead of the "
                             "microphone (Chromium --use-file-for-fake-audio-capture)")
    parser.add_argument("--code-root", default=None,
                        help="the one project directory the character may read source from; it "
                             "is indexed with the CodeGraph CLI (index written in the parent, "
                             "never inside the project) and only paths under this directory are "
                             "ever sent to the model. Pass 'ask' to get a folder picker even from "
                             "a script; pass 'keep' from a script to re-use the stored grant and "
                             "never open a dialog (a driver that cannot answer one hangs); with no "
                             "--code-root at all, a console gets the picker.")
    args = parser.parse_args()
    if args.text_only and (args.voice or args.audio_input is not None):
        parser.error('文字模式不能同时启用语音或真实/模拟音频输入。')
    if not args.text_only:
        host.require_task_audio_allowed("avatar/product UI startup")
    if not (args.voice_connects.isdigit() or args.voice_connects == "unlimited"):
        parser.error("voice-connects must be a nonnegative number or unlimited")
    if args.minutes <= 0 or args.api_budget < 0 or args.egress_budget < 0:
        parser.error("minutes must be positive; api-budget and egress-budget may be 0")
    store = (ROOT / "benchmarks/raw" / args.store).resolve()
    if not store.is_relative_to(ROOT / "benchmarks/raw"):
        parser.error("store must remain inside benchmarks/raw")
    if args.learning_surface or args.text_only:
        BROWSER_PROFILE = store / ("browser/text-profile" if args.text_only else "browser/profile")
        BROWSER_OWNER_FILE = BROWSER_PROFILE.parent / "browser-owner.json"
    UI_URL = f"http://127.0.0.1:{host.PLUGIN_PORT}{UI_PATH}"
    voice_hosts = [h.strip().lower() for h in args.voice_host.split(",") if h.strip()]
    chat_surface = args.chat_surface or ("compact" if args.voice else "full")

    if not host.SOURCE_PYTHON.is_file():
        print(f"找不到源码宿主 Python：{host.SOURCE_PYTHON}")
        return 1
    for port in (host.MAIN_PORT, host.PLUGIN_PORT):
        with socket.socket() as probe:
            if probe.connect_ex(("127.0.0.1", port)) == 0:
                print("Tutor 宿主端口已被占用。请先结束现有开发实例，再双击 Start-Tutor.cmd。")
                return 1
    try:
        host.read_key()
        print(f"宿主侧可靠性补丁：{host.apply_voice_host_patch()}")
        host.verify_source_audio_gate()
        browser_args = chrome_command(UI_URL, text_only=args.text_only) if args.study_ui else None
        if browser_args and BROWSER_OWNER_FILE.is_file():
            previous = json.loads(BROWSER_OWNER_FILE.read_text(encoding="utf-8"))
            if owned_browser_pids(previous):
                raise RuntimeError("项目专用 Chrome 窗口仍在运行；请先关闭该学习窗口再启动，不会接管或关闭其他 Chrome。")
    except Exception as error:
        print(f"启动检查失败：{error}")
        return 1

    print(f"正在启动隔离源码 Tutor 宿主：最长 {args.minutes} 分钟。")
    print(f"付费调用硬顶 {args.egress_budget} 次（角色大脑和教学网关一起算，到数直接 403），"
          f"其中 Study 教学 {args.api_budget} 次。")
    if args.egress_budget == 0:
        print("这一趟是「零付费」模式：角色窗、聊天界面、历史学习记录和读屏工具都照常，"
              "但你发问不会得到讲解（模型请求会被硬顶直接拒掉），适合先确认界面与记录。")
    else:
        print("注意：角色开着就会自己消耗额度——实测一次 3.7 分钟、全程没人说话的宿主，"
              "仍走掉 13 次付费调用。")
    print(("语音：原生 Realtime 已放开；主动捕获仍关闭。" if args.voice else
           "语音、麦克风与主动捕获已关闭。") + f"学习记录与配置：{store}")
    if args.voice:
        print(f"放行域名：{', '.join(voice_hosts)}（各 {args.voice_connects} 条 CONNECT）。"
              "两个都在名单里是因为应用会先做一次 GeoIP 自查（utils/config_manager/core_config.py:330 "
              "那条请求显式绕开代理，所以出口闸门看不见它），判海外后把 "
              "wss://www.lanlan.tech/core 改写成 www.lanlan.app（core_config.py:820）。"
              "只放行配置里那个名字，realtime 就连到 403 为止。")
    print(language_pin_note(store / "N.E.K.O"))
    # Say what the character rule did before the learner opens their mouth: the host writes
    # it again right before spawn (idempotent), and the audit records the same status.
    guidance = host.apply_tutor_role_guidance(store / "N.E.K.O")
    print({
        "set": "角色人设已补上「工具给的讲解按原语言说、不要翻译」这条（只写在本项目的角色卡里）。",
        "already set": "角色人设里那条「不要翻译」的规则已在位。",
        "upgraded": "角色人设里那条规则是本项目早期版本写的，已升级成本轮的版本（你自己写的人设不会被动）。",
        "kept the learner's own guidance": "角色卡里已有你自己写的人设指令，本轮不动它——教学语言只靠课程偏好和工具转述。",
        "a persona preset already owns the guidance": "角色选了 persona preset，人设指令位归 preset 管，这条不写入；要控语言就换回自定义人设。",
    }.get(guidance, f"角色人设指令未写入（{guidance}），教学语言仍由课程偏好控制。"))
    # The host's idle memory loops are paid model calls the learner never asked for; they
    # default to on, so a session that nobody talks in still spends its request budget.
    quiet = host.apply_quiet_brain_config(store / "N.E.K.O")
    print("宿主后台付费自转的调用：" + (
        "记忆复盘两路本来就是关的。" if quiet == "already quiet" else
        "情绪分析没有开关，每次回复后仍会跑两次；" if quiet.startswith("kept") else "")
        + f"[{quiet}]")
    # /chat_full resolves its GalGame toggle from localStorage, and the getter returns True
    # when the key was never written — so quick replies cost one paid request per turn out
    # of the box. It is the learner's switch to flip, not ours to seed.
    print("一条能自己省的：聊天窗工具条上的「快捷回复 A/B/C」出厂就是开的，"
          "每轮多要一次模型调用（实测稳态一轮 7 次，关掉它是 6 次）。"
          "在窗口里把它关一次就会记住，重启仍是关的；注意别去删配置里的键——没有键就等于开。")
    # The two keys above are not equivalent in cost: switching powerful memory off also
    # moves fact extraction back onto every turn (post_turn's OFF-mode fallback), which
    # measurably costs one paid request per learner question.
    print("这条 trade 已经量过了：powerful_memory 关掉停的是 evidence/refine 那几路，"
          "代价是事实提取退回「每个用户轮跑一次」。你 11:35 那场的逐笔账（"
          "scripts/neko_request_attribution.py）显示 80 次里有 30 次紧跟着一次记忆写入，"
          "所以这一笔是我们自己写错的开关——启动时会把它放回产品默认（批处理：每累积 10 轮一次）。"
          "只想关掉空转反思循环（recent_memory_auto_review），那个才是纯后台自转。")
    print(f"原生桌面角色即将出现（聊天界面 {chat_surface}），请直接在它的聊天窗口里提问。"
          if chat_surface == "full" else
          "原生桌面角色即将出现（聊天界面 compact——悬浮麦克风只在这一面被创建），"
          "点角色旁的小麦克风开始说话。")
    # The host already keeps its own log; naming it here is what makes a turn that produced
    # no reply diagnosable, because the character shows nothing when the model call fails.
    print(f"角色不回话时看宿主日志：{ROOT / 'benchmarks/raw/neko-desktop-host.log'}")
    # The character spends requests on its own before you ask anything, so telling the
    # learner where the number lives is what makes `--egress-budget` usable mid-session.
    print(f"本次付费请求上限 {args.egress_budget}，想中途改就编辑这个文件（不用重启）："
          f"{ROOT / 'benchmarks/raw/neko-desktop-egress-cap'}")
    print(round_balance_note(ROOT / "benchmarks/raw/neko-desktop-egress-cap", args.budget_round))
    print("文字模式：声音和麦克风均关闭，请使用聊天输入框。" if args.text_only else speech_input_note())
    data_dir = store / "N.E.K.O"
    chosen = (args.code_root or "").strip()
    # 双击入口（真控制台、没带 --code-root）就弹一次目录选择框；命令行传了就用传的，脚本运行不受影响。
    action = code_root_action(chosen, sys.stdin.isatty())
    if action == "picker":
        print("代码问答：正在弹出项目选择框（取消 = 本轮不改授权，保持上一次批准的目录）。"
              "第一次选一个新项目要先建索引，可能几十秒。")
        chosen = pick_code_root()
        if not chosen:
            # Measured: cancelling leaves the stored grant in force, so saying "this round reads
            # no code" here contradicted the next line and the tool's own behaviour.
            print("代码问答：已取消，没有改动授权；要停掉代码阅读就删 code_project.json。")
        action = code_root_action(chosen, False)
    if action == "authorize":
        authorize_code_project(Path(chosen).expanduser().resolve(), data_dir)
    else:
        held = data_dir / "plugins/study_companion/data/code_project.json"
        previous = ""
        try:
            previous = str(json.loads(held.read_text(encoding="utf-8")).get("root") or "")
        except (OSError, ValueError):
            if held.is_file():
                print("代码问答：旧的授权文件无法读取，已保留；本轮不使用这份不可信授权。")
        print("代码问答：" + (f"沿用上次授权的项目 {previous}（要换就再给一次 --code-root，"
                              "要停就删 code_project.json）。" if previous else
                              "这一轮没有授权任何项目，角色不会读代码；"
                              "需要就用 --code-root <项目目录> 启动。"))
    voice_extra = host_options(args, voice_hosts)
    surface = None
    launch_env = os.environ.copy()
    launch_env["PYTHONIOENCODING"] = "utf-8"
    if args.text_only:
        launch_env['NEKO_TASK_SILENT'] = '1'
    if args.learning_surface:
        from neko_learning_surface import LearningSurface, DEFAULT_MATERIALS
        materials = [path for path in DEFAULT_MATERIALS if path.is_file()]
        surface = LearningSurface(materials, port=0)
        threading.Thread(target=surface.serve_forever, daemon=True).start()
        surface_url = f"http://127.0.0.1:{surface.server_port}"
        launch_env.update(NEKO_LEARNING_SURFACE_URL=surface_url,
                          NEKO_LEARNING_SURFACE_TOKEN=surface.token)
        print(f"只读学习材料与指示：{surface_url}")
        if browser_args:
            browser_args = [arg for arg in browser_args if not arg.startswith("--app=")] + ["--new-window", UI_URL, surface_url]
    store.mkdir(parents=True, exist_ok=True)
    provider_override = CoreProviderOverride(store, 'free' if args.voice else 'deepseek')
    launcher_log = store / "launcher.log"
    launcher_output = launcher_log.open("ab")
    launcher = subprocess.Popen(
        host_command(args.minutes, args.api_budget, args.egress_budget, voice_extra, args.store),
        cwd=str(ROOT), env=launch_env, stdout=launcher_output, stderr=subprocess.STDOUT)
    launcher_owner = [{"pid": launcher.pid, "created_at": process_creation_time(launcher.pid)}]
    browser = None
    browser_record = []
    lesson = None
    shell = None
    try:
        ready, reason = plugin_server_ready(240, launcher)
        if not ready:
            print(f"Study UI 没有就绪：{reason}（启动错误：{launcher_log}；运行日志：benchmarks/raw/neko-desktop-host.log）")
            return 1
        print(f"Study UI 已就绪：{UI_URL}")
        if surface is not None:
            surface.attach_study_store(store)
        if args.text_only:
            avatar.verify_output_only_host('text-only')
        if not args.learning_surface:
            lesson = subprocess.Popen(lesson_command(), cwd=str(ROOT),
                                      stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        try:
            shell = avatar.launch(store, 150,
                                  chat_surface=chat_surface, cdp_port=args.cdp_port or None,
                                  audio_input=args.audio_input, text_only=args.text_only)
        except RuntimeError as error:
            print(f"原生角色启动失败：{error}")
            print(f"可退回辅助网页面板：{UI_URL}（重新启动时加 --study-ui）")
            return 1
        print(f"原生角色已就绪：pid {shell['pid']}，可见窗口 {len(shell.get('windows', []))} 个。")
        if browser_args:
            BROWSER_PROFILE.parent.mkdir(parents=True, exist_ok=True)
            browser = subprocess.Popen(browser_args, cwd=str(ROOT))
            remember_browser_tree(browser, browser_record)
        print("\n在角色聊天窗口输入文字，例如：" if args.text_only else "\n直接在角色的聊天窗口里说话，例如：")
        if args.learning_surface:
            print("  先在 Study 选择图片，再说：讲讲我交给 Study 的这张图，用两句话。")
            print("  查询授权项目里的 fetchWeather，讲讲天气请求怎样发出。")
            print("  在学习材料窗口选当前源码证据，再说：指向刚刚解释的代码行。")
        else:
            print("  读取「Live Tutor Flutter Provider Lesson」里的代码，用中文讲讲 read 和 watch 的区别。")
        print("  我没听懂，换个简单点的例子。 / 给我一个反例。 / 给我一题。")
        print("  Explain that in English. / 以后这门课主要用英文教学。")
        print("角色会自己调用读屏、讲解、出题、评分与总结；学习记录保存在项目学习数据库。")
        print(f"辅助面板（可选，不是主入口）：{UI_URL}")
        print("\n用完了按 Enter 关闭角色与宿主（Ctrl+C 也可以）。")
        finished = threading.Event()

        def wait_for_enter():
            try:
                input()
            except EOFError:
                return
            finished.set()

        threading.Thread(target=wait_for_enter, daemon=True).start()
        deadline = time.monotonic() + args.minutes * 60
        while not finished.wait(1) and time.monotonic() < deadline and launcher.poll() is None:
            if browser is not None:
                remember_browser_tree(browser, browser_record)
    except KeyboardInterrupt:
        pass
    finally:
        cleanup_errors = cleanup_resources(surface, shell, launcher, launcher_owner,
                                           browser, browser_record, lesson)
        if not cleanup_errors and launcher.poll() is not None:
            try:
                provider_override.restore()
            except (OSError, ValueError, RuntimeError) as error:
                cleanup_errors.append(f'provider settings: {type(error).__name__}: {error}')
        launcher_output.close()
        audit = sorted((ROOT / "benchmarks/raw/evidence").glob("neko-desktop-host-*.json"))
        summary = {}
        if audit:
            record = json.loads(audit[-1].read_text(encoding="utf-8"))
            summary = {"allowed": record.get("sink_allowed_hosts"), "denied": record.get("sink_denied_hosts"),
                       "direct": record.get("observed_external_connections")}
        print(json.dumps({"stopped": not cleanup_errors, "cleanup_errors": cleanup_errors,
                          "egress_this_session": summary}, ensure_ascii=False))
    return 1 if cleanup_errors else 0


if __name__ == "__main__":
    sys.exit(main())
