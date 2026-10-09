"""One command to run the desktop text tutor: start, use, stop.

Everything the user has to know is in this file's output: no ports, no config keys,
no test scripts. It reuses the existing launcher (which owns the disposable store,
the text-only safety settings and the egress sink) and stops it again on exit.

  python scripts/neko_tutor_start.py            # start, open the UI, wait, then stop
  python scripts/neko_tutor_start.py --minutes 90
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import neko_desktop_tutor_host as host  # noqa: E402

UI_PATH = "/plugin/study_companion/ui/"
HOST_SCRIPT = ROOT / "scripts/neko_desktop_tutor_host.py"


def plugin_server_ready(timeout: float) -> tuple[bool, str]:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    deadline = time.monotonic() + timeout
    reason = "timed out"
    while time.monotonic() < deadline:
        try:
            with opener.open(f"http://127.0.0.1:{host.PLUGIN_PORT}{UI_PATH}", timeout=5) as response:
                if response.status == 200:
                    return True, ""
                reason = f"HTTP {response.status}"
        except Exception as error:
            reason = f"{type(error).__name__}: {str(error)[:80]}"
        time.sleep(2)
    return False, reason


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--minutes", type=int, default=40, help="how long the session may stay open")
    parser.add_argument("--no-browser", action="store_true", help="print the address instead of opening it")
    parser.add_argument("--port", type=int, default=host.PLUGIN_PORT)
    args = parser.parse_args()
    UI_URL = f"http://127.0.0.1:{args.port}{UI_PATH}"

    if not host.SERVER.is_file():
        print(f"找不到宿主程序：{host.SERVER}")
        return 1
    try:
        host.read_key()
    except Exception as error:
        print(f"读取模型凭据失败：{error}")
        print(f"请把 DeepSeek 的 sk- 开头密钥单独写在一行里，文件位置：{host.KEY_FILE}")
        return 1

    hold = max(120, args.minutes * 60 + 120)
    print("正在启动一次性学习宿主（关闭语音合成、麦克风、主动提醒；出口只允许 api.deepseek.com）…")
    launcher = subprocess.Popen(
        [sys.executable, str(HOST_SCRIPT), "--hold", str(hold), "--seconds", "220"],
        cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    try:
        ready, reason = plugin_server_ready(240)
        if not ready:
            print(f"Study UI 没有就绪：{reason}（详见 benchmarks/raw/neko-desktop-host.log）")
            return 1
        print(f"Study UI 已就绪：{UI_URL}")
        if not args.no_browser:
            webbrowser.open(UI_URL)
        print("\n在浏览器里就能用：第一次会让你选学习阶段（可以按 Skip），然后选 Teaching 模式，")
        print("把课本内容粘进输入框点 Explain，追问同一页继续问，展开面板可以做本次总结。")
        print("\n用完了按 Enter 关闭宿主（Ctrl+C 也可以）。")
        try:
            input()
        except (EOFError, KeyboardInterrupt):
            pass
    finally:
        subprocess.run([sys.executable, str(HOST_SCRIPT), "--stop"], cwd=str(ROOT),
                       capture_output=True, text=True)
        if launcher.poll() is None:
            launcher.terminate()
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
