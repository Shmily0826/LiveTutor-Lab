r"""Launch the real N.E.K.O host for the desktop Study tutor, text-only.

Usage (isolated source-host Python, including psutil):
  python scripts/neko_desktop_tutor_host.py            # start, health-check, leave running
  python scripts/neko_desktop_tutor_host.py --probe    # same, then stop the host again
  python scripts/neko_desktop_tutor_host.py --stop     # stop the host this script started

Safety boundary, three independent layers, because a talking host is not acceptable
until audio is proven blocked:

1. Disposable storage root. The host reads `NEKO_STORAGE_SELECTED_ROOT`; nothing here
   touches the user's real config, characters or learning database.
2. Text-only configuration written into that store before launch: DISABLE_TTS=true, no
   speech/native-realtime provider credentials, proactive and wake word disabled.
   `DISABLE_TTS` alone is only a worker-selection gate in the source, so it is not the
   whole boundary.
3. Loopback egress sink. HTTP(S)_PROXY point at a local sink that tunnels only
   api.deepseek.com and denies plus records every other destination. A netstat poll runs
   beside it for independent runtime evidence. This sampling may miss short-lived
   connections; it is observation, not an operating-system network restriction.

The DeepSeek credential is read from the local key file the user left for this project,
is never printed, and is refused if it ever appears in an output artefact.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "benchmarks/raw/neko-app/resources/bin"
SERVER = APP / "projectneko_server.exe"
EVIDENCE = ROOT / "benchmarks/raw/evidence"
KEY_FILE = Path(r"D:\CODE\API\new api.txt")
ALLOWED_HOST = "api.deepseek.com"
MODEL = "deepseek-flash"
MODEL_URL = f"https://{ALLOWED_HOST}/v1"
SOURCE_APP = ROOT / "benchmarks/raw/neko-product-host"
SOURCE_PYTHON = SOURCE_APP / ".venv/Scripts/python.exe"
PRODUCT = ROOT / "patches/neko-study-2026-10-10-product"
MAIN_PORT = 48911
PLUGIN_PORT = 48916


def read_key() -> str:
    for line in KEY_FILE.read_text(encoding="utf-8", errors="replace").splitlines():
        value = line.strip()
        if value.startswith("sk-") and len(value) > 20:
            return value
    raise RuntimeError("no chat credential found")


def prepare_store(key: str, store: Path) -> Path:
    """Merge the text-only safety settings into a disposable host store.

    The host's ConfigManager resolves core_config.json from %LOCALAPPDATA%, which
    is *not* covered by NEKO_STORAGE_SELECTED_ROOT, so the caller redirects that
    variable at this tree as well. Without that redirection the host reads the
    user's real settings, and the tutor's `agent` slot silently resolves to the
    user's provider instead of the disposable one.
    """
    config_file = store / "N.E.K.O/config/core_config.json"
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config: dict[str, object] = {}
    if config_file.is_file():
        try:
            loaded = json.loads(config_file.read_text(encoding="utf-8"))
            config = loaded if isinstance(loaded, dict) else {}
        except ValueError:
            config = {}
    before = {"DISABLE_TTS": config.get("DISABLE_TTS"), "coreApi": config.get("coreApi"),
              "ttsProvider": config.get("ttsProvider"), "assistApi": config.get("assistApi")}
    config.update({
        "DISABLE_TTS": True,
        "enableCustomApi": True,
        "coreApi": "deepseek",
        "assistApi": "deepseek",
        "assistApiKeyDeepseek": key,
        "coreApiKeyDeepseek": key,
        "ttsProvider": "",
        "proactive_enabled": False,
        "voice_wake_word_enabled": False,
        # The tutor asks for the `agent` slot, which resolves through the custom
        # fields when enableCustomApi is on; assist alone is not enough. The file
        # schema is camelCase (config/api_profiles.py), not UPPER_SNAKE.
        "agentModelId": MODEL,
        "agentModelUrl": MODEL_URL,
        "agentModelApiKey": key,
    })
    config_file.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"store": store.name, "config_before": before}, ensure_ascii=False))
    return store


def prepare_product_plugin(store: Path) -> None:
    """Deploy only source/assets into the new isolated store; never copy learning data."""
    source = APP / "plugins/study_companion"
    target = store / "plugin-code/study_companion"
    target.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        if item.is_file() and item.suffix in {".py", ".toml", ".md"}:
            shutil.copy2(item, target / item.name)
        elif item.is_dir() and item.name in {"static", "surfaces", "i18n"}:
            shutil.copytree(item, target / item.name, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns("__pycache__", "*.db", "*.sqlite*"))
    for overlay, destination in ((PRODUCT / "payload/study_companion", target),
                                 (PRODUCT / "static", target / "static")):
        if overlay.is_dir():
            for item in overlay.rglob("*"):
                if item.is_file() and item.suffix != ".cjs":
                    output = destination / item.relative_to(overlay)
                    output.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, output)
    manifest = (target / "plugin.toml").read_text(encoding="utf-8")
    manifest = manifest.replace('plugins.study_companion.lab_bootstrap_plane:StudyCompanionPlugin',
                                'plugins.study_companion:StudyCompanionPlugin')
    manifest = manifest.replace('expose_legacy_static_panel = false', 'expose_legacy_static_panel = true')
    # Keep all teaching responses in Study UI; no character messaging or narration.
    manifest = manifest.replace('[study_companion.communication]\nenabled = true',
                                '[study_companion.communication]\nenabled = false')
    manifest = manifest.replace('solution_narration_enabled = true', 'solution_narration_enabled = false')
    manifest = manifest.replace('general_narration_enabled = true', 'general_narration_enabled = false')
    manifest = manifest.replace('os_signals_enabled = true', 'os_signals_enabled = false')
    manifest = manifest.replace('[study.supervision]\nenabled = true', '[study.supervision]\nenabled = false')
    (target / "plugin.toml").write_text(manifest, encoding="utf-8")


def verify_source_audio_gate() -> None:
    manifest = json.loads((ROOT / "patches/neko-study-2026-10-10-host/manifest.json").read_text(encoding="utf-8"))
    for item in manifest["files"]:
        path = SOURCE_APP / item["path"]
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != item["patched_sha256"]:
            raise RuntimeError(f"text-only host source fingerprint differs: {item['path']}")


class Sink(threading.Thread):
    """Allow-listed CONNECT/HTTP relay that records every denial."""

    def __init__(self) -> None:
        super().__init__(daemon=True)
        self.decisions: list[dict[str, object]] = []
        self._lock = threading.Lock()
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind(("127.0.0.1", 0))
        self._server.listen(32)
        self.port = self._server.getsockname()[1]
        self.stop = False

    def _record(self, host: str, action: str) -> bool:
        with self._lock:
            self.decisions.append({"host": host[:120], "action": action,
                                   "at": datetime.now(timezone.utc).isoformat()})
        return action == "allowed"

    def _handle(self, conn: socket.socket) -> None:
        try:
            conn.settimeout(20)
            head = conn.recv(65536)
            if not head:
                return
            first = head.split(b"\r\n")[0].decode("latin-1", "replace")
            parts = first.split()
            target = ""
            if parts and parts[0].upper() == "CONNECT":
                target = parts[1] if len(parts) > 1 else ""
                conn.sendall(b"HTTP/1.1 200 Connection established\r\n\r\n")
                self._tunnel(conn, target)
                return
            if len(parts) > 1 and "//" in parts[1]:
                target = re.sub(r"^https?://", "", parts[1]).split("/")[0]
            host = target.split(":")[0].lower()
            if host == ALLOWED_HOST:
                self._forward(conn, head, host)
                self._record(host, "allowed")
            else:
                self._record(host or "unknown", "denied")
                conn.sendall(b"HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
        except OSError:
            pass
        finally:
            try:
                conn.close()
            except OSError:
                pass

    def _upstream(self, host: str, port: int) -> socket.socket:
        sock = socket.create_connection((host, port), timeout=20)
        self._record(host, "direct_connect")
        return sock

    def _tunnel(self, conn: socket.socket, target: str) -> None:
        host = target.split(":")[0].lower()
        if host != ALLOWED_HOST:
            self._record(host or "unknown", "denied")
            conn.close()
            return
        self._record(host, "allowed_connect")
        try:
            up = socket.create_connection((host, 443), timeout=20)
        except OSError:
            return
        threading.Thread(target=self._pump, args=(conn, up), daemon=True).start()
        self._pump(up, conn)

    @staticmethod
    def _pump(source: socket.socket, dest: socket.socket) -> None:
        try:
            while True:
                data = source.recv(65536)
                if not data:
                    break
                dest.sendall(data)
        except OSError:
            pass
        finally:
            for sock in (source, dest):
                try:
                    sock.close()
                except OSError:
                    pass

    def _forward(self, conn: socket.socket, head: bytes, host: str) -> None:
        try:
            up = socket.create_connection((host, 443 if host == ALLOWED_HOST else 80), timeout=20)
        except OSError:
            return
        # Absolute-URI requests already carry the path; keep them as sent.
        up.sendall(head)
        threading.Thread(target=self._pump, args=(conn, up), daemon=True).start()
        self._pump(up, conn)

    def run(self) -> None:
        while not self.stop:
            try:
                conn, _ = self._server.accept()
            except OSError:
                return
            threading.Thread(target=self._handle, args=(conn,), daemon=True).start()

    def snapshot(self) -> list[dict[str, object]]:
        with self._lock:
            return list(self.decisions)


def egress_audit(stop: threading.Event, pid: int, seen: set[str]) -> None:
    import psutil
    while not stop.is_set():
        try:
            descendants = {pid, *(child.pid for child in psutil.Process(pid).children(recursive=True))}
            out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, timeout=20).stdout
        except (OSError, subprocess.SubprocessError, psutil.Error):
            return
        for line in out.splitlines():
            if "ESTABLISHING" in line.upper():
                continue
            cols = line.split()
            if len(cols) >= 5 and cols[-1].isdigit() and int(cols[-1]) in descendants and cols[2].startswith(("127.", "[::")) is False:
                remote = cols[2]
                if not remote.startswith(("127.", "0.0.0.0", "[::1]", "::1")):
                    seen.add(remote)
        stop.wait(2.0)


def get(path: str, timeout: float = 8.0, method: str = "GET") -> tuple[int, str]:
    request = urllib.request.Request(
        path, method=method,
        data=b"{}" if method == "POST" else None,
        headers={"Content-Type": "application/json"},
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(request, timeout=timeout) as response:
            return int(response.status), response.read(4000).decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        return int(error.code), ""
    except Exception as exc:  # noqa: BLE001 - health probe reports the failure type only
        return 0, type(exc).__name__


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", action="store_true", help="stop the host after health checks")
    parser.add_argument("--stop", action="store_true", help="stop the previously started host")
    parser.add_argument("--seconds", type=int, default=120, help="health wait budget")
    parser.add_argument("--hold", type=int, default=1800,
                        help="seconds to keep the host alive after health checks (0 = --probe)")
    parser.add_argument("--store", default="neko-appdata",
                        help="disposable LOCALAPPDATA tree under benchmarks/raw holding the plugin")
    parser.add_argument("--source", action="store_true", help="run pinned source host with verified text-only audio gates")
    parser.add_argument("--api-budget", type=int, default=30, help="maximum Study model requests in this launch")
    args = parser.parse_args()

    pid_file = ROOT / "benchmarks/raw/neko-desktop-host.pid"
    if args.stop:
        if not pid_file.is_file():
            print(json.dumps({"stopped": False, "reason": "no pid file"}))
            return 1
        pid = int(pid_file.read_text().strip())
        get(f"http://127.0.0.1:{PLUGIN_PORT}/plugin/study_companion/stop", timeout=30, method="POST")
        result = subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, text=True)
        pid_file.unlink(missing_ok=True)
        print(json.dumps({"stopped": result.returncode == 0, "pid": pid,
                          "detail": result.stdout.strip()[:200] or result.stderr.strip()[:200]}))
        return 0

    executable = SOURCE_PYTHON if args.source else SERVER
    try:
        __import__("psutil")
    except ImportError:
        raise SystemExit(f"Run this launcher with {SOURCE_PYTHON} (psutil is required for the process audit).")
    if not executable.is_file():
        print(json.dumps({"status": "MISSING_HOST_BINARY", "path": str(SERVER)}))
        return 1

    key = read_key()
    if args.source:
        verify_source_audio_gate()
    store = (ROOT / "benchmarks/raw" / args.store).resolve()
    if not store.is_relative_to(ROOT / "benchmarks/raw"):
        raise SystemExit("store must remain inside benchmarks/raw")
    store = prepare_store(key, store)
    if args.source:
        prepare_product_plugin(store)
        runtime_root = store / "N.E.K.O"
        policy = runtime_root / "state/storage_policy.json"
        policy.parent.mkdir(parents=True, exist_ok=True)
        policy.write_text(json.dumps({"version": 1, "anchor_root": str(runtime_root),
            "selected_root": str(runtime_root), "selection_source": "default",
            "cloudsave_strategy": "fixed_anchor", "first_run_completed": True,
            "updated_at": datetime.now(timezone.utc).isoformat()}, indent=2), encoding="utf-8")
    sink = Sink()
    sink.start()

    env = dict(os.environ)
    env.update({
        "NEKO_STORAGE_SELECTED_ROOT": str(store),
        "NEKO_STORAGE_ANCHOR_ROOT": str(store),
        "NEKO_STORAGE_CLOUDSAVE_ROOT": str(store),
        # Own the whole app-data tree so the host never reads the user's real
        # core_config.json (whose provider is `free` with no key at all).
        "LOCALAPPDATA": str(store),
        "APPDATA": str(store),
        "PYTHONIOENCODING": "utf-8",
        "HTTP_PROXY": f"http://127.0.0.1:{sink.port}",
        "HTTPS_PROXY": f"http://127.0.0.1:{sink.port}",
        "NO_PROXY": "127.0.0.1,localhost",
    })
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    if args.source:
        env.update({"NEKO_MERGED": "1", "NEKO_CLOUDSAVE_DISABLED": "livetutor-isolated",
                    "NEKO_STORAGE_SELECTED_ROOT": str(runtime_root),
                    "NEKO_STORAGE_ANCHOR_ROOT": str(runtime_root),
                    "NEKO_STORAGE_CLOUDSAVE_ROOT": str(runtime_root),
                    "NEKO_DO_NOT_TRACK": "1", "PLUGIN_CONFIG_ROOT": str(store / "plugin-code"),
                    "NEKO_DEV_TEXT_ONLY": "1",
                    "NEKO_DEV_AUDIO_AUDIT": str(EVIDENCE / f"neko-product-audio-{stamp}.jsonl"),
                    "NEKO_STUDY_API_BUDGET": str(max(0, args.api_budget)),
                    "NEKO_STUDY_API_AUDIT": str(EVIDENCE / f"neko-product-api-{stamp}.jsonl")})
    log_path = ROOT / "benchmarks/raw/neko-desktop-host.log"
    handle = log_path.open("wb")
    started = time.monotonic()
    command = [str(SOURCE_PYTHON), "launcher.py"] if args.source else [str(SERVER)]
    process = subprocess.Popen(command, cwd=str(SOURCE_APP if args.source else APP), env=env,
                               stdout=handle, stderr=subprocess.STDOUT)
    pid_file.write_text(str(process.pid), encoding="utf-8")

    stop = threading.Event()
    remote: set[str] = set()
    threading.Thread(target=egress_audit, args=(stop, process.pid, remote), daemon=True).start()

    base = f"http://127.0.0.1:{MAIN_PORT}"
    health: dict[str, object] = {}
    deadline = started + args.seconds
    ready_seconds = 0.0
    while time.monotonic() < deadline:
        status, _ = get(f"{base}/api/agent/user_plugin/availability")
        if status in (200, 409):  # 409 means the API is up but awaiting a storage choice
            ready_seconds = round(time.monotonic() - started, 1)
            break
        if process.poll() is not None:
            break
        time.sleep(2)

    # A host start does not re-scan the plugin directory on its own; without this
    # the Study UI answers 404 until something asks for a refresh.
    refresh_status, refresh_body = get(
        f"http://127.0.0.1:{PLUGIN_PORT}/plugins/refresh", timeout=30.0, method="POST"
    )
    registered = "study_companion" in refresh_body
    start_status, start_body = get(
        f"http://127.0.0.1:{PLUGIN_PORT}/plugin/study_companion/start", timeout=90.0, method="POST"
    )
    time.sleep(2)
    plugin_running = start_status == 200 and '"success":true' in start_body.replace(" ", "")

    for name, url in (
        ("plugin_availability", f"{base}/api/agent/user_plugin/availability"),
        ("plugin_dashboard", f"{base}/api/agent/user_plugin/dashboard"),
        ("study_ui", f"http://127.0.0.1:{PLUGIN_PORT}/plugin/study_companion/ui/"),
        ("study_ui_index", f"http://127.0.0.1:{PLUGIN_PORT}/plugin/study_companion/ui/index.html"),
        ("study_ui_main", f"{base}/plugin/study_companion/ui/"),
    ):
        status, body = get(url)
        health[name] = {"status": status, "study_companion": "study_companion" in body,
                        "html": "<html" in body.lower(), "bytes": len(body),
                        "note": "" if status == 200 else body[:120]}

    time.sleep(6)

    # The launcher ties its lifetime to its parent process ("foreground
    # residency via parent_handle"), so this script must stay alive for the host
    # to keep serving. `--stop` or deleting the pid file ends the session.
    hold = 0 if args.probe else max(30, args.hold)
    deadline_hold = time.monotonic() + hold
    while hold and time.monotonic() < deadline_hold:
        if not pid_file.is_file() or process.poll() is not None:
            break
        time.sleep(2)

    stop.set()
    sink_decisions = sink.snapshot()
    allowed = sorted({d["host"] for d in sink_decisions if str(d["action"]).startswith("allowed")})
    denied = sorted({d["host"] for d in sink_decisions if d["action"] == "denied"})
    if args.source and process.poll() is None:
        get(f"http://127.0.0.1:{PLUGIN_PORT}/plugin/study_companion/stop", timeout=30, method="POST")
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True)
        pid_file.unlink(missing_ok=True)

    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "host_binary": "pinned_source_launcher" if args.source else SERVER.name,
        "host_pid": process.pid,
        "host_running": process.poll() is None,
        "host_ready_seconds": ready_seconds,
        "storage_root": store.relative_to(ROOT).as_posix(),
        "safety_config": {"DISABLE_TTS": True, "ttsProvider": "empty",
                          "proactive": False, "wake_word": False,
                          "proxy_sink_port": sink.port},
        "source_text_only_gate": args.source,
        "api_budget": args.api_budget if args.source else None,
        "plugin_refresh": {"status": refresh_status, "study_companion_registered": registered},
        "plugin_start": {"status": start_status, "running": plugin_running},
        "health": health,
        "sink_allowed_hosts": allowed,
        "sink_denied_hosts": denied,
        "observed_external_connections": sorted(remote),
    }
    serialised = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if key in serialised:
        raise SystemExit("refusing to write a report containing the credential")
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    out = EVIDENCE / f"neko-desktop-host-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    out.write_text(serialised + "\n", encoding="utf-8")
    handle.close()

    if args.probe and process.poll() is None:
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True)
        pid_file.unlink(missing_ok=True)
        report["host_running"] = False

    print(json.dumps({"status": "DESKTOP_HOST_PROBE", "artifact": out.relative_to(ROOT).as_posix(),
                      "host_running": report["host_running"],
                      "sink_allowed": allowed, "sink_denied": denied,
                      "external_connections": report["observed_external_connections"],
                      "health": {k: v["status"] for k, v in health.items()}},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
