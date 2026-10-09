"""Run the isolated source Tutor with its own muted Chrome learning window.

Default: a four-hour session, 30 model requests, persistent project learning data.
Double-click Start-Tutor.cmd or run this script with the source host's Python.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
import threading
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import neko_desktop_tutor_host as host  # noqa: E402

UI_PATH = "/plugin/study_companion/ui/"
HOST_SCRIPT = ROOT / "scripts/neko_desktop_tutor_host.py"
PRODUCT_STORE = "neko-product-data"
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


def chrome_command(url: str) -> list[str]:
    candidates = [Path(os.environ[name]) / "Google/Chrome/Application/chrome.exe"
                  for name in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA") if os.environ.get(name)]
    chrome = next((path for path in candidates if path.is_file()), None)
    if chrome is None:
        raise RuntimeError("找不到 Chrome；请安装 Chrome 后再启动 Tutor。")
    return [str(chrome), f"--user-data-dir={BROWSER_PROFILE}", f"--app={url}", "--mute-audio",
            "--no-first-run", "--no-default-browser-check", "--disable-sync",
            "--disable-background-networking", "--disable-component-update",
            "--disable-features=MediaRouter"]


def owned_browser_processes(record: list[dict]) -> list:
    import psutil
    owned = []
    for item in record:
        try:
            process = psutil.Process(item["pid"])
            if process.create_time() == item["created_at"] and process.is_running():
                owned.append(process)
        except psutil.NoSuchProcess:
            pass
    return owned


def remember_browser_tree(browser: subprocess.Popen, record: list[dict]) -> None:
    import psutil
    if browser.poll() is not None:
        return
    try:
        process = psutil.Process(browser.pid)
        processes = [process, *process.children(recursive=True)]
    except psutil.NoSuchProcess:
        return
    known = {(item["pid"], item["created_at"]) for item in record}
    for child in processes:
        try:
            identity = (child.pid, child.create_time())
            if identity not in known:
                record.append({"pid": identity[0], "created_at": identity[1]})
        except psutil.NoSuchProcess:
            pass
    BROWSER_OWNER_FILE.write_text(json.dumps(record), encoding="utf-8")


def stop_owned_browser(record: list[dict]) -> None:
    import psutil
    processes = owned_browser_processes(record)
    for process in reversed(processes):
        try:
            process.terminate()
        except psutil.NoSuchProcess:
            pass
    _, remaining = psutil.wait_procs(processes, timeout=5)
    for process in remaining:
        try:
            process.kill()
        except psutil.NoSuchProcess:
            pass
    _, remaining = psutil.wait_procs(remaining, timeout=5)
    if remaining:
        raise RuntimeError("项目 Chrome 进程尚未退出；保留所有权记录，请关闭学习窗口后重试。")
    BROWSER_OWNER_FILE.unlink(missing_ok=True)


def host_command(minutes: int, api_budget: int) -> list[str]:
    return [str(host.SOURCE_PYTHON), str(HOST_SCRIPT), "--source", "--store", PRODUCT_STORE,
            "--hold", str(minutes * 60 + 120), "--seconds", "220", "--api-budget", str(api_budget)]


def lesson_command() -> list[str]:
    return [str(host.SOURCE_PYTHON), str(LESSON_SCRIPT)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--minutes", type=int, default=240, help="session limit in minutes (default: 4 hours)")
    parser.add_argument("--api-budget", type=int, default=30, help="maximum model requests for this launch")
    parser.add_argument("--no-browser", action="store_true", help="print the address instead of opening it")
    args = parser.parse_args()
    if args.minutes <= 0 or args.api_budget <= 0:
        parser.error("minutes and api-budget must be positive")
    UI_URL = f"http://127.0.0.1:{host.PLUGIN_PORT}{UI_PATH}"

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
        host.verify_source_audio_gate()
        browser_args = chrome_command(UI_URL) if not args.no_browser else None
        if browser_args and BROWSER_OWNER_FILE.is_file():
            previous = json.loads(BROWSER_OWNER_FILE.read_text(encoding="utf-8"))
            if owned_browser_processes(previous):
                raise RuntimeError("项目专用 Chrome 窗口仍在运行；请先关闭该学习窗口再启动，不会接管或关闭其他 Chrome。")
    except Exception as error:
        print(f"启动检查失败：{error}")
        return 1

    print(f"正在启动隔离源码 Tutor：最长 {args.minutes} 分钟，最多 {args.api_budget} 次模型请求。")
    print("语音、麦克风与主动捕获已关闭；学习记录保存在本项目 neko-product-data。")
    print("学习阶段/表达偏好保存在项目专用 Chrome Profile；课程事实与答题记录保存在学习数据库。")
    launcher = subprocess.Popen(
        host_command(args.minutes, args.api_budget),
        cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    browser = None
    browser_record = []
    lesson = None
    try:
        ready, reason = plugin_server_ready(240, launcher)
        if not ready:
            print(f"Study UI 没有就绪：{reason}（详见 benchmarks/raw/neko-desktop-host.log）")
            return 1
        print(f"Study UI 已就绪：{UI_URL}")
        lesson = subprocess.Popen(lesson_command(), cwd=str(ROOT),
                                  stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        if browser_args:
            BROWSER_PROFILE.parent.mkdir(parents=True, exist_ok=True)
            browser = subprocess.Popen(browser_args, cwd=str(ROOT))
            remember_browser_tree(browser, browser_record)
        print("\n选择课程 ID并开始 Session；指定授权窗口完整标题和画面标记；")
        print("已打开 Flutter 演示窗口；UI 已预填演示标题和标记，可改为自己的授权学习窗口。")
        print("点击读取后在 5 秒内切换到学习窗口，检查文字，再点 Explain。")
        print("追问时勾选 Use previous explanation；展开面板可以做本次总结。")
        print("\n用完了按 Enter 关闭宿主（Ctrl+C 也可以）。")
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
        if launcher.poll() is None:
            subprocess.run([str(host.SOURCE_PYTHON), str(HOST_SCRIPT), "--stop"], cwd=str(ROOT),
                           capture_output=True, text=True)
            try:
                launcher.wait(timeout=20)
            except subprocess.TimeoutExpired:
                launcher.terminate()
        if browser is not None:
            remember_browser_tree(browser, browser_record)
            stop_owned_browser(browser_record)
        if lesson is not None and lesson.poll() is None:
            lesson.terminate()
        audit = sorted((ROOT / "benchmarks/raw/evidence").glob("neko-desktop-host-*.json"))
        summary = {}
        if audit:
            record = json.loads(audit[-1].read_text(encoding="utf-8"))
            summary = {"allowed": record.get("sink_allowed_hosts"), "denied": record.get("sink_denied_hosts"),
                       "direct": record.get("observed_external_connections")}
        print(json.dumps({"stopped": True, "egress_this_session": summary}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
