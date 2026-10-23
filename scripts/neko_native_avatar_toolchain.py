"""Run the avatar's teaching tool chain end to end against the real model.

``main_server`` invokes a plugin LLM tool by POSTing to the plugin server's
callback route. Calling that same route is the narrowest honest stand-in for
"the character picked a tool": it exercises registration, IPC dispatch into the
running plugin, the Study Companion teaching path and the real provider, while
the model-visible registration itself is asserted separately from
``GET /api/tools``. Every reply here is a genuine DeepSeek answer.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "benchmarks/raw/evidence"
PLUGIN = "http://127.0.0.1:48916"
MAIN = "http://127.0.0.1:48911"
PLUGIN_ID = "study_companion"
LESSON_TITLE = "Live Tutor Flutter Provider Lesson"

LESSON_SOURCE = '''import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

class Counter with ChangeNotifier {
  int _value = 0;
  int get value => _value;
  void increment() { _value++; notifyListeners(); }
}

class StatsBar extends StatelessWidget {
  const StatsBar({super.key});
  @override
  Widget build(BuildContext context) {
    final count = context.read<Counter>().value;
    return Text('count: $count');
  }
}

class LiveCounter extends StatelessWidget {
  const LiveCounter({super.key});
  @override
  Widget build(BuildContext context) {
    final count = context.watch<Counter>().value;
    return Text('live: $count');
  }
}
'''


def call(tool: str, arguments: dict, timeout: float = 180.0) -> dict:
    body = json.dumps({"name": tool, "arguments": arguments,
                       "call_id": f"acceptance_{tool}_{int(time.time()*1000)}",
                       "raw_arguments": json.dumps(arguments)}).encode()
    request = urllib.request.Request(f"{PLUGIN}/api/llm-tools/callback/{PLUGIN_ID}/{tool}",
                                     data=body, method="POST",
                                     headers={"Content-Type": "application/json"})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    started = time.monotonic()
    try:
        with opener.open(request, timeout=timeout) as response:
            payload = json.loads(response.read())
    except urllib.error.HTTPError as error:
        payload = {"is_error": True, "error": f"HTTP {error.code}: {error.read()[:200]!r}"}
    except Exception as error:  # noqa: BLE001 - a failed turn is evidence too
        payload = {"is_error": True, "error": f"{type(error).__name__}: {error}"}
    payload["_seconds"] = round(time.monotonic() - started, 2)
    return payload


def registered_tools() -> list[str]:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(f"{MAIN}/api/tools", timeout=10) as response:
        data = json.loads(response.read())
    tools = data.get("tools_by_role") or {}
    return sorted(item["name"] for group in tools.values() for item in group
                  if item.get("source") == f"plugin:{PLUGIN_ID}")


def plan() -> list[tuple[str, dict, str]]:
    return [
        ("study_session", {"action": "start", "course_id": "flutter-provider"},
         "角色开始 flutter-provider 课程"),
        ("study_read_window", {"window_title": LESSON_TITLE,
                               "expected_markers": ["ChangeNotifier", "provider.dart"]},
         "读取指定窗口：窗口不在前台时应被拒绝，不得回退全屏"),
        ("study_explain", {"text": LESSON_SOURCE,
                           "question": "read 和 watch 有什么区别？用两三句话讲重点"},
         "讲解屏幕上的真实代码"),
        ("study_explain", {"question": "我没听懂，换个生活化的比喻，短一点"},
         "听不懂时换一种讲法，并接住上一轮材料"),
        ("study_explain", {"question": "给我一个会出 bug 的反例，说明为什么会坏"},
         "要求反例"),
        ("study_language", {"language": "english", "scope": "course"},
         "把这门课的长期教学语言切成英文"),
        ("study_explain", {"question": "give me a counter-example that breaks rebuilds"},
         "英文临时指令 + 课程级英文偏好"),
        ("study_quiz", {}, "针对薄弱点出题"),
        ("study_answer", {"answer": "C"}, "故意答错，看纠错与记录"),
        ("study_summary", {}, "总结本次学习"),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry", action="store_true", help="assert registration only, no paid calls")
    args = parser.parse_args()

    tools = registered_tools()
    report: dict[str, object] = {"at": datetime.now(timezone.utc).isoformat(),
                                 "avatar_tools_registered": tools, "turns": []}
    print(json.dumps({"registered_avatar_tools": tools}, ensure_ascii=False))
    expected = {"study_session", "study_read_window", "study_explain", "study_quiz",
                "study_answer", "study_summary", "study_language"}
    missing = sorted(expected - set(tools))
    if missing:
        print(json.dumps({"fatal": "tools missing from the avatar registry", "missing": missing}))
        return 1
    if args.dry:
        return 0

    for tool, arguments, intent in plan():
        result = call(tool, arguments)
        output = result.get("output")
        brief = output if isinstance(output, (str, dict)) else json.dumps(output, ensure_ascii=False)
        record = {"tool": tool, "intent": intent, "seconds": result.get("_seconds"),
                  "is_error": bool(result.get("is_error")),
                  "arguments": {key: (value[:120] + "…" if isinstance(value, str) and len(value) > 120
                                      else value) for key, value in arguments.items()},
                  "output": brief}
        report["turns"] = report["turns"] if isinstance(report["turns"], list) else []
        report["turns"].append(record)
        preview = json.dumps(brief, ensure_ascii=False) if isinstance(brief, dict) else str(brief)
        print(f"\n[{tool}] {intent}  ({result.get('_seconds')}s, error={result.get('is_error')})")
        print(preview[:900], flush=True)

    EVIDENCE.mkdir(parents=True, exist_ok=True)
    out = EVIDENCE / f"native-avatar-toolchain-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"artifact": out.relative_to(ROOT).as_posix(),
                      "turns": len(report["turns"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
