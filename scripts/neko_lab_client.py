"""Bounded loopback client for lab acceptance; never fetch provider credentials."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time
import urllib.request


class LabClient:
    def __init__(self, port: int = 48916, plugin: str = "study_companion"):
        self.base = f"http://127.0.0.1:{port}"
        self.plugin = plugin
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def request(self, path: str, method="GET", data=None, timeout=10):
        request = urllib.request.Request(
            self.base + path, method=method,
            data=None if data is None else json.dumps(data).encode(),
            headers={"Content-Type": "application/json"},
        )
        with self.opener.open(request, timeout=timeout) as response:
            return json.load(response)

    def call(self, entry: str, args=None, timeout=150):
        started = time.monotonic()
        run = self.request("/runs", "POST", {
            "plugin_id": self.plugin, "entry_id": entry,
            "args": {"locale": "zh-CN", **(args or {})},
        })
        run_id = run.get("run_id") or run.get("id")
        if not run_id:
            raise RuntimeError("run submission returned no id")
        deadline = started + timeout
        while time.monotonic() < deadline:
            state = self.request(f"/runs/{run_id}")
            if state.get("status") in {"succeeded", "failed", "canceled", "timeout"}:
                if state["status"] != "succeeded":
                    raise RuntimeError(f"run {run_id}: {state['status']}")
                export = self.request(f"/runs/{run_id}/export")
                for item in export.get("items", []):
                    if item.get("type") == "json":
                        result = item["json"]
                        if result.get("success") is False:
                            raise RuntimeError(f"plugin entry {entry} failed")
                        data = result.get("data", result)
                        return {"run_id": run_id, "elapsed_ms": round(
                            (time.monotonic() - started) * 1000), "data": data}
                raise RuntimeError("successful run has no JSON export")
            time.sleep(0.5)
        # An expired observation does not mean that the underlying run stopped.
        raise TimeoutError(f"observation expired; inspect existing run {run_id}")


def status_summary(result):
    data = result["data"]
    data = data.get("data", data)
    dependencies = data.get("dependencies") or {}
    return {"run_id": result["run_id"], "elapsed_ms": result["elapsed_ms"],
            "status": data.get("status"),
            "awareness": (data.get("config") or {}).get("awareness"),
            "awareness_runtime": data.get("awareness_runtime"),
            "supervision": (data.get("habit") or {}).get("supervision"),
            "dependencies": {"ocr_ready":(dependencies.get("ocr_readiness") or {}).get("ready"),
                             **{name+"_installed":(dependencies.get(name) or {}).get("installed")
                                for name in ("rapidocr","tesseract","dxcam")}},
            "event_count": len(data.get("recent_learning_events") or []),
            "classification_count": len(data.get("recent_classifications") or [])}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("entry", nargs="?", default="study_status")
    parser.add_argument("--args", default="{}")
    parser.add_argument("--output", type=Path)
    options = parser.parse_args()
    result = LabClient().call(options.entry, json.loads(options.args))
    if options.entry == "study_status":
        result = status_summary(result)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if options.output:
        options.output.parent.mkdir(parents=True, exist_ok=True)
        options.output.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
