"""Night teaching-experience validation for N.E.K.O + Study Companion.

Phases (run in order, each idempotent-safe and evidence-logging):
  prepare   render material A to the foreground and verify the window
  snapshot  DB baseline + process resource sample (also used as `observe` later)
  ocr       fullscreen OCR of the screen (watchdog kills stray overlays)
  phase-a   math scenario: explain(OCR) -> follow-up -> error exposure ->
            question -> wrong answer -> provided-question correct answer
  phase-b   programming scenario: explain -> question -> wrong answer
  phase-c   context-pollution check + teaching-mode check (restores mode)
  phase-d   knowledge map/guidance + session summary + DB delta
  restore   turn the plugin runtime flags back off (final step of the night)

Every phase writes benchmarks/raw/evidence/teach-<phase>.json and prints a
short summary. LLM-consuming entries are counted and printed as a running
total (budget: 50 for the whole night; scoring samples budget: 6-8).
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import json
import sqlite3
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from neko_lab_client import LabClient  # noqa: E402
from neko_lab_stage import DB  # noqa: E402

EVIDENCE = ROOT / "benchmarks/raw/evidence"
EVIDENCE.mkdir(parents=True, exist_ok=True)

client = LabClient()
LLM_CALLS = 0
SCORES = 0
LLM_ENTRIES = {
    "study_explain_text", "study_generate_question", "study_evaluate_answer",
    "study_generate_targeted_question", "study_summarize_session",
    "study_ocr_snapshot", "study_active_document_analysis",
}

u32 = ctypes.windll.user32
_stop = threading.Event()


def log(*a):
    print(time.strftime("[%H:%M:%S]"), *a, flush=True)


def save(name, payload):
    path = EVIDENCE / f"teach-{name}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    log("evidence ->", path.name)
    return path


def call(entry, args=None, phase="", note_llm=True):
    """One plugin entry call; counts LLM/scoring usage; returns full result."""
    global LLM_CALLS, SCORES
    log(f"call {entry} args={list((args or {}).keys())}")
    res = client.call(entry, args, timeout=180)
    if note_llm and entry in LLM_ENTRIES:
        LLM_CALLS += 1
    if entry == "study_evaluate_answer":
        SCORES += 1
    log(f"  ok run={res['run_id'][:8]} elapsed={res['elapsed_ms']}ms "
        f"llm_calls={LLM_CALLS} scores={SCORES}")
    return res


def db_counts():
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    cur = con.cursor()
    out = {}
    for t in ("interactions", "qa_records"):
        out[t] = cur.execute(f"select count(*) from {t}").fetchone()[0]
    out["interactions_max_id"] = cur.execute(
        "select coalesce(max(id),0) from interactions").fetchone()[0]
    con.close()
    return out


def proc_sample():
    try:
        import psutil
    except ImportError:
        return {"error": "psutil unavailable"}
    out = []
    for p in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            name = (p.info["name"] or "")
            cl = " ".join(p.info["cmdline"] or [])
            if "neko-app" in cl or name.lower().startswith("projectneko"):
                mem = p.memory_info()
                out.append({"pid": p.pid, "name": name,
                            "rss_mb": round(mem.rss / 1e6, 1),
                            "threads": p.num_threads(),
                            "cpu_total_s": round(p.cpu_times().user + p.cpu_times().system, 1),
                            "create_ts": p.create_time()})
        except Exception:
            continue
    return out


def phase_snapshot(name="snapshot"):
    payload = {"ts": time.time(), "db": db_counts(), "procs": proc_sample()}
    save(name, payload)
    return payload


# ---------------------------------------------------------------- prepare ---
MATERIAL_A = ROOT / "benchmarks/materials/study-substitution-20261009.html"


def _windows_with_title(part):
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
    def cb(hwnd, lp):
        if u32.IsWindowVisible(hwnd):
            buf = ctypes.create_unicode_buffer(256)
            u32.GetWindowTextW(hwnd, buf, 256)
            if part.lower() in buf.value.lower():
                r = wt.RECT()
                u32.GetWindowRect(hwnd, ctypes.byref(r))
                found.append((hwnd, buf.value, (r.left, r.top, r.right, r.bottom)))
        return True

    u32.EnumWindows(cb, 0)
    return found


def phase_prepare():
    subprocess.Popen(["cmd", "/c", "start", "", str(MATERIAL_A)],
                     shell=False, creationflags=subprocess.CREATE_NO_WINDOW)
    time.sleep(3.5)
    wins = _windows_with_title("NEKO-LAB-20261009")
    if not wins:
        # Chrome may title it with the page title; retry once after maximizing
        time.sleep(2)
        wins = _windows_with_title("NEKO-LAB-20261009")
    result = {"ts": time.time(), "windows_found": [(w[1], w[2]) for w in wins]}
    if wins:
        hwnd = wins[0][0]
        u32.ShowWindow(hwnd, 3)  # SW_MAXIMIZE
        time.sleep(0.6)
        u32.SetForegroundWindow(hwnd)
        time.sleep(0.8)
        fg = u32.GetForegroundWindow()
        buf = ctypes.create_unicode_buffer(256)
        u32.GetWindowTextW(fg, buf, 256)
        result["foreground_after_activate"] = buf.value
        result["foreground_is_material"] = "NEKO-LAB-20261009" in buf.value
    save("prepare", result)
    log("prepare:", json.dumps(result, ensure_ascii=False))
    return result


# ------------------------------------------------------------------- ocr ----
def _overlays():
    out = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
    def cb(hwnd, lparam):
        if not u32.IsWindowVisible(hwnd):
            return True
        buf = ctypes.create_unicode_buffer(256)
        u32.GetWindowTextW(hwnd, buf, 256)
        if "screenshot" in buf.value.lower():
            r = wt.RECT()
            u32.GetWindowRect(hwnd, ctypes.byref(r))
            out.append((hwnd, (r.left, r.top, r.right - r.left, r.bottom - r.top)))
        return True

    u32.EnumWindows(cb, 0)
    return out


def _watcher():
    while not _stop.is_set():
        for hwnd, rect in _overlays():
            left, top, w, _h = rect
            u32.SetForegroundWindow(hwnd)
            time.sleep(0.2)
            u32.SetCursorPos(int(left + w - 220), int(top + 82))
            time.sleep(0.1)
            u32.mouse_event(0x0002, 0, 0, 0, 0)
            u32.mouse_event(0x0004, 0, 0, 0, 0)
            time.sleep(0.4)
            u32.PostMessageW(hwnd, 0x0010, 0, 0)
        time.sleep(1.0)


def phase_ocr():
    _stop.clear()
    threading.Thread(target=_watcher, daemon=True).start()
    try:
        res = call("study_ocr_snapshot",
                   {"capture_mode": "fullscreen", "allow_fullscreen_fallback": True})
    finally:
        _stop.set()
    data = res["data"]
    data = data.get("data", data)
    text = str(data.get("ocr_text") or data.get("text") or "")
    checks = {
        "has_marker": "NEKO-LAB-20261009" in text,
        "has_substitution": ("换元" in text),
        "has_ex1": ("cos(x²)" in text or "cos(x2)" in text or "cos(x^2)" in text),
        "has_ex2": ("e" in text and "x²" in text),
        "has_warn": ("分部" in text or "cos(x)" in text),
        "chars": len(text),
    }
    payload = {"ts": time.time(), "run_id": res["run_id"],
               "elapsed_ms": res["elapsed_ms"], "checks": checks,
               "ocr_text_sample": text[:1200], "raw": data}
    save("ocr", payload)
    log("ocr checks:", checks)


# --------------------------------------------------------------- phase-a ----
def _reply(res):
    data = res["data"]
    data = data.get("data", data)
    return data


def phase_a():
    out = {}
    # A1: explain from the OCR snapshot (no text -> last_ocr_text fallback)
    a1 = _reply(call("study_explain_text", {}, note_llm=False))  # OCR fallback path
    out["a1_explain_reply"] = str(a1.get("reply") or a1.get("summary") or "")[:3000]
    out["a1_checks"] = {
        "mentions_sin": "sin" in out["a1_explain_reply"],
        "mentions_inner_derivative": ("2x" in out["a1_explain_reply"] or "2 x" in out["a1_explain_reply"]),
        "mentions_half": ("1/2" in out["a1_explain_reply"] or "½" in out["a1_explain_reply"]),
    }

    # A2: follow-up referring to example 2 without restating it
    a2 = _reply(call("study_explain_text", {
        "text": "继续刚才的材料：例题 2 里为什么会多出一个系数 1/2？请只针对例题 2 解释。"
    }))
    out["a2_followup_reply"] = str(a2.get("reply") or "")[:3000]
    out["a2_checks"] = {
        "mentions_half": ("1/2" in out["a2_followup_reply"] or "½" in out["a2_followup_reply"]),
        "mentions_e_x2": ("e" in out["a2_followup_reply"]),
        "mentions_example1_only": ("sin(x²)" in out["a2_followup_reply"] and "例题 2" not in out["a2_followup_reply"]),
    }

    # A3: expose a misconception, expect correction
    a3 = _reply(call("study_explain_text", {
        "text": "我想用换元法算 ∫ x·cos(x) dx：令 u = x，则 du = dx，"
                "于是 ∫ cos(u) du = sin(u) + C = sin(x) + C。这样做对吗？为什么？"
    }))
    out["a3_error_reply"] = str(a3.get("reply") or "")[:3000]
    out["a3_checks"] = {
        "rejects_or_corrects": any(k in out["a3_error_reply"] for k in ("不对", "不能", "不正确", "错误", "没有意义", "等于没换")),
        "suggests_integration_by_parts": ("分部" in out["a3_error_reply"]),
        "gives_correct_result": ("x·sin(x)" in out["a3_error_reply"] or "xsin(x)" in out["a3_error_reply"] or "x sin(x)" in out["a3_error_reply"]),
    }

    # A4: generate a question from material A summary
    mat_text = ("不定积分换元法：设 u=g(x)，∫f(g(x))g'(x)dx = ∫f(u)du。"
                "例题：∫ 2x·cos(x²) dx = sin(x²)+C；∫ x·e^(x²) dx = (1/2)e^(x²)+C。"
                "易错：∫ x·cos(x) dx 不适用换元法，需要分部积分。")
    a4 = _reply(call("study_generate_question", {"text": mat_text}))
    out["a4_question"] = {k: a4.get(k) for k in
                          ("question", "answer", "question_id", "attempt_id", "topic", "difficulty")}
    save("phase-a", out)
    log("phase-a checks:", {k: v for k, v in out.items() if k.endswith("checks")})
    return out


def _load_phase(name):
    path = EVIDENCE / f"teach-{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def phase_a2():
    """Scoring part of scenario A (kept separate so A4 state is intact)."""
    out = {}
    prev = _load_phase("phase-a")
    qid = str(prev.get("a4_question", {}).get("question_id") or "")
    aid = str(prev.get("a4_question", {}).get("attempt_id") or "")
    a5 = _reply(call("study_evaluate_answer", {
        "answer": "答案是 42。", "question_id": qid, "attempt_id": aid}))
    out["a5_wrong"] = {k: a5.get(k) for k in
                       ("verdict", "score", "feedback", "error_type", "next_action")}
    out["a5_checks"] = {
        "verdict_is_wrong": str(a5.get("verdict", "")).lower() in ("wrong", "incorrect", "false", "0"),
        "score_zeroish": float(a5.get("score") or 0) <= 20,
        "feedback_specific": len(str(a5.get("feedback") or "")) > 30,
    }

    # A6: provided question + full correct derivation (provided path)
    a6 = _reply(call("study_evaluate_answer", {
        "question": "计算不定积分 ∫ 3x²·cos(x³) dx。",
        "expected_answer": "sin(x³) + C。提示：令 u=x³，则 du=3x² dx，原式 = ∫ cos(u) du = sin(u)+C。",
        "answer": "令 u = x³，则 du = 3x² dx。原式 = ∫ cos(x³)·3x² dx = ∫ cos(u) du = "
                  "sin(u) + C = sin(x³) + C。最后回代并加常数 C。"
    }))
    out["a6_correct"] = {k: a6.get(k) for k in
                         ("verdict", "score", "feedback", "next_action")}
    out["a6_checks"] = {
        "verdict_is_correct": str(a6.get("verdict", "")).lower() in ("correct", "true", "right", "1"),
        "score_high": float(a6.get("score") or 0) >= 80,
    }
    save("phase-a2-scoring", out)
    log("phase-a2:", out["a5_checks"], out["a6_checks"])
    return out


def phase_b():
    out = {}
    b_material = (ROOT / "benchmarks/materials/study-asyncio-20261009.md").read_text(encoding="utf-8")
    b1 = _reply(call("study_explain_text", {"text": b_material}))
    out["b1_explain_reply"] = str(b1.get("reply") or "")[:3000]
    out["b1_checks"] = {
        "mentions_gather": "gather" in out["b1_explain_reply"],
        "mentions_blocking_pitfall": ("time.sleep" in out["b1_explain_reply"] or "阻塞" in out["b1_explain_reply"]),
    }
    b2 = _reply(call("study_generate_question", {
        "text": "Python asyncio：事件循环、async/await、asyncio.gather 并发、"
                "常见错误 time.sleep 阻塞事件循环。",
        "topic": "python asyncio"}))
    out["b2_question"] = {k: b2.get(k) for k in
                          ("question", "answer", "question_id", "attempt_id", "topic")}
    b3 = _reply(call("study_evaluate_answer", {
        "answer": "在协程里用 time.sleep(3) 等待 3 秒，效果和 asyncio.sleep(3) 完全一样。",
        "question_id": str(out["b2_question"].get("question_id") or ""),
        "attempt_id": str(out["b2_question"].get("attempt_id") or "")}))
    out["b3_wrong"] = {k: b3.get(k) for k in ("verdict", "score", "feedback", "error_type")}
    out["b3_checks"] = {
        "verdict_is_wrong": str(b3.get("verdict", "")).lower() in ("wrong", "incorrect", "false", "0"),
        "mentions_blocking": ("阻塞" in str(b3.get("feedback") or "") or "冻结" in str(b3.get("feedback") or "") or "block" in str(b3.get("feedback") or "").lower()),
    }
    save("phase-b", out)
    log("phase-b:", out["b1_checks"], out["b3_checks"])
    return out


def phase_c():
    out = {}
    c1 = _reply(call("study_explain_text", {
        "text": "回到之前的定积分换元材料：例题 1 的复合关系是什么？正确结果是什么？"
    }))
    out["c1_reply"] = str(c1.get("reply") or "")[:3000]
    out["c1_checks"] = {
        "recalls_material_a": ("cos(x²)" in out["c1_reply"] or "sin(x²)" in out["c1_reply"]
                               or "x²" in out["c1_reply"] or "x^2" in out["c1_reply"]),
        "no_asyncio_pollution": not any(k in out["c1_reply"].lower() for k in ("asyncio", "gather", "事件循环", "event loop")),
    }
    c2_mode = _reply(call("study_set_mode", {"mode": "teaching"}))
    out["c2_mode_switch"] = {k: c2_mode.get(k) for k in ("changed", "new_mode", "transition_phrase")}
    c2 = _reply(call("study_explain_text", {
        "text": "请用教学模式重新讲一遍：定积分换元法的使用步骤，一步一步来。"
    }))
    out["c2_reply"] = str(c2.get("reply") or "")[:3000]
    out["c2_active_mode"] = str(c2.get("mode") or "")
    out["c2_checks"] = {
        "mode_is_teaching": "teaching" in out["c2_active_mode"],
        "step_style": any(k in out["c2_reply"] for k in ("第一步", "第 1 步", "Step", "步骤", "①", "1.")),
        "ends_with_check_question": ("?" in out["c2_reply"][-120:] or "？" in out["c2_reply"][-120:]),
    }
    # restore companion mode
    c3 = _reply(call("study_set_mode", {"mode": "companion"}))
    out["mode_restored"] = str(c3.get("new_mode") or "")
    save("phase-c", out)
    log("phase-c:", out["c1_checks"], out["c2_checks"])
    return out


def phase_d():
    out = {}
    try:
        km = _reply(call("study_knowledge_map", {}, note_llm=False))
        out["knowledge_map_keys"] = sorted(km.keys())
        topics = km.get("topics") or km.get("nodes") or []
        out["topics_sample"] = [
            {k: t.get(k) for k in ("topic_id", "name", "mastery", "status") if isinstance(t, dict) and k in t}
            for t in (topics[:12] if isinstance(topics, list) else [])]
    except Exception as exc:
        out["knowledge_map_error"] = repr(exc)[:200]
    try:
        kg = _reply(call("study_knowledge_guidance", {}, note_llm=False))
        out["guidance_reply"] = str(kg.get("reply") or kg.get("guidance") or "")[:1500]
        out["guidance_weak_topics"] = kg.get("weak_topics") or kg.get("recommended_topics") or []
    except Exception as exc:
        out["guidance_error"] = repr(exc)[:200]
    try:
        s = _reply(call("study_summarize_session", {"focus": "今晚的换元法与 asyncio 学习"}))
        out["summary_reply"] = str(s.get("summary") or s.get("reply") or "")[:2500]
        out["summary_next_actions"] = s.get("next_actions") or []
    except Exception as exc:
        out["summary_error"] = repr(exc)[:200]
    out["db_after"] = db_counts()
    save("phase-d", out)
    log("phase-d db:", out.get("db_after"))
    return out


def phase_restore():
    import urllib.request
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def post(port, path, payload):
        req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", method="POST",
                                     data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"})
        with opener.open(req, timeout=10) as r:
            return r.status
    r1 = post(48915, "/agent/flags", {"user_plugin_enabled": False})
    r2 = post(48915, "/agent/command", {"command": "set_agent_enabled", "enabled": False})
    payload = {"ts": time.time(), "flags_off": r1, "master_off": r2,
               "llm_calls_total": LLM_CALLS, "score_samples_total": SCORES,
               "db_final": db_counts()}
    save("restore", payload)
    log("restore:", payload)


phase_a_state = {}


def main():
    global phase_a_state
    sys.stdout.reconfigure(encoding="utf-8")
    phases = sys.argv[1:] or ["snapshot"]
    for name in phases:
        log("=== phase:", name)
        if name in ("snapshot", "observe"):
            phase_snapshot(name)
        elif name == "prepare":
            phase_prepare()
        elif name == "ocr":
            phase_ocr()
        elif name == "phase-a":
            phase_a_state = phase_a()
        elif name == "phase-a2":
            phase_a2()
        elif name == "phase-b":
            phase_b()
        elif name == "phase-c":
            phase_c()
        elif name == "phase-d":
            phase_d()
        elif name == "restore":
            phase_restore()
        else:
            raise SystemExit(f"unknown phase {name}")
    log(f"done. llm_calls={LLM_CALLS} score_samples={SCORES}")


if __name__ == "__main__":
    main()
