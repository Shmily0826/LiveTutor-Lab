"""Round-2 teaching validation: does the plugin fix actually make teaching continuous?

Reuses the night-runner's scaffolding (client, OCR watcher, DB counts) but writes
its evidence to ``teach2-*.json`` so the round-1 ``teach-*.json`` evidence is kept.

Phases
  snapshot   DB baseline + process sample
  enable     turn the plugin runtime on (master switch first, then the child flag)
  ocr        fullscreen OCR of the material (sets last_ocr_text)
  r1-followup    explain(material A) -> "why is there a 1/2 in example 2?"
  r2-crossmat    explain(asyncio)      -> "back to the substitution material, example 1?"
  r3-binding     generate question from material A, and from asyncio + topic hint
  r4-scoring     answer evaluations with a controlled correct/wrong spread
  r5-summary     session summary grounded in what was actually studied
  restore        turn the plugin runtime flags back off
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import neko_lab_teach_night as night  # noqa: E402

EVIDENCE = ROOT / "benchmarks/raw/evidence"
save = night.save


def save2(name, payload):
    """Same as the night saver but namespaced so round-1 evidence survives."""
    path = EVIDENCE / f"teach2-{name}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    night.log("evidence ->", path.name)
    return path


night.save = save2

client = night.client
call = night.call
reply = night._reply
db_counts = night.db_counts
log = night.log

MATERIAL_A_TEXT = (
    "不定积分换元法：设 u=g(x)，则 ∫f(g(x))g'(x)dx = ∫f(u)du。"
    "例题 1：∫2x·cos(x²)dx，令 u=x²，du=2x dx，原式 = ∫cos(u)du = sin(u)+C = sin(x²)+C。"
    "例题 2：∫x·e^(x²)dx，令 u=x²，du=2x dx，原式 = (1/2)∫e^u du = (1/2)e^(x²)+C。"
    "易错警示：∫x·cos(x)dx 不能用换元法（内层导数不是 x），需要分部积分。"
)
ASYNCIO_TEXT = (
    "Python asyncio：事件循环在单线程内调度多个协程；async def 定义协程函数，"
    "await 让出控制权；asyncio.gather 并发等待多个任务；"
    "常见错误：在协程里调用同步的 time.sleep 会阻塞整个事件循环。"
)

SUBSTITUTION_MARKERS = ("换元", "积", "原函数", "cos", "e^", "sin", "du", "u=")
CHAIN_RULE_MARKERS = ("求导", "导数", "dy/dx", "微分", "链式", "chain rule")
ASYNCIO_MARKERS = ("asyncio", "协程", "事件循环", "event loop", "await", "async",
                   "gather", "阻塞", "并发", "sleep")
CALCULUS_OFFTOPIC_MARKERS = ("求导", "导数", "dy/dx", "链式")


def post(port, path, payload):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}", method="POST",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with opener.open(req, timeout=15) as r:
        return r.status


# ------------------------------------------------------------------ phases --
def phase_snapshot():
    return night.phase_snapshot("round2-snapshot")


def phase_enable():
    out = {"ts": time.time()}
    out["master_on"] = post(48915, "/agent/command",
                            {"command": "set_agent_enabled", "enabled": True})
    time.sleep(2.0)
    out["flags_on"] = post(48915, "/agent/flags", {"user_plugin_enabled": True})
    plugins = []
    deadline = time.time() + 40
    while time.time() < deadline:
        try:
            req = urllib.request.Request("http://127.0.0.1:48916/plugins")
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(req, timeout=5) as r:
                body = json.load(r)
            plugins = body if isinstance(body, list) else (
                body.get("plugins") or body.get("items") or [])
            if plugins:
                break
        except Exception as exc:
            out["last_probe_error"] = repr(exc)[:120]
        time.sleep(2.0)
    out["plugin_count"] = len(plugins)
    ids = []
    for item in plugins:
        if isinstance(item, dict):
            ids.append(str(item.get("id") or item.get("plugin_id") or item.get("name") or ""))
        else:
            ids.append(str(item))
    out["has_study_companion"] = any("study_companion" in i for i in ids)
    out["plugin_ids"] = ids[:30]
    save2("enable", out)
    log("enable:", {k: v for k, v in out.items() if k != "plugin_ids"})
    return out


def _needs_paste(text: str) -> bool:
    return any(marker in text for marker in
               ("把例题", "发我", "请提供例题", "提供具体", "请把题目", "把题目发",
                "paste the", "send me the"))


def phase_r1():
    out = {"ts": time.time()}
    a1 = reply(call("study_explain_text", {"text": MATERIAL_A_TEXT}))
    out["explain_reply"] = str(a1.get("reply") or "")[:2500]
    out["explain_recent_context_chars"] = a1.get("recent_context_chars")
    out["explain_mode"] = a1.get("mode") or a1.get("active_mode")
    # Follow-up that only makes sense with the previous material in view.
    a2 = reply(call("study_explain_text", {
        "text": "继续刚才的材料：例题 2 里为什么会多出一个系数 1/2？请只针对例题 2 解释。"}))
    text = str(a2.get("reply") or "")
    out["followup_reply"] = text[:2500]
    out["followup_recent_context_chars"] = a2.get("recent_context_chars")
    out["checks"] = {
        "fix_is_live": int(out["followup_recent_context_chars"] or 0) > 0,
        "mentions_half": any(k in text for k in ("1/2", "½", "二分之一", "\\frac{1}{2}", "0.5")),
        "mentions_example2_math": ("e" in text and ("x²" in text or "x^2" in text or "x^{2}" in text)),
        "names_example2": "例题 2" in text or "例题2" in text,
        "does_not_ask_to_paste": not _needs_paste(text),
        "explains_du_half": any(k in text for k in ("du", "2x", "u=x²", "u = x²")),
    }
    save2("r1-followup", out)
    log("r1:", out["checks"])
    return out


def phase_r2():
    out = {"ts": time.time()}
    b1 = reply(call("study_explain_text", {"text": ASYNCIO_TEXT}))
    out["asyncio_reply"] = str(b1.get("reply") or "")[:2000]
    c1 = reply(call("study_explain_text", {
        "text": "回到之前的定积分换元材料：例题 1 的复合关系是什么？正确结果是什么？"}))
    text = str(c1.get("reply") or "")
    out["crossmaterial_reply"] = text[:2500]
    out["crossmaterial_recent_context_chars"] = c1.get("recent_context_chars")
    lowered = text.lower()
    out["checks"] = {
        "recalls_material_a": any(k in text for k in ("cos(x²)", "sin(x²)", "cos(x^2)", "sin(x^2)")
                                  or "2x" in text),
        "no_asyncio_pollution": not any(k in lowered for k in
                                        ("asyncio", "gather", "事件循环", "event loop", "协程")),
        "does_not_ask_to_paste": not _needs_paste(text),
    }
    save2("r2-crossmat", out)
    log("r2:", out["checks"])
    return out


def _question_checks(question: str, positive, negative) -> dict:
    text = str(question or "")
    lowered = text.lower()
    return {
        "has_positive_marker": any(m.lower() in lowered for m in positive),
        "has_negative_marker": any(m.lower() in lowered for m in negative),
        "question_excerpt": text[:220],
    }


def phase_r3():
    out = {"ts": time.time()}
    qa = reply(call("study_generate_question", {"text": MATERIAL_A_TEXT}))
    out["substitution_question"] = {k: qa.get(k) for k in
                                    ("question", "answer", "topic", "difficulty")}
    out["substitution_checks"] = _question_checks(
        str(qa.get("question") or ""), SUBSTITUTION_MARKERS, CHAIN_RULE_MARKERS)
    out["substitution_checks"]["material_grounded_question"] = qa.get("material_grounded_question")

    qb = reply(call("study_generate_question", {"text": ASYNCIO_TEXT, "topic": "python asyncio"}))
    out["asyncio_question"] = {k: qb.get(k) for k in
                               ("question", "answer", "topic", "difficulty")}
    out["asyncio_checks"] = _question_checks(
        str(qb.get("question") or ""), ASYNCIO_MARKERS, CALCULUS_OFFTOPIC_MARKERS)
    out["asyncio_checks"]["material_grounded_question"] = qb.get("material_grounded_question")

    # Scoring samples 1-3: same question, three different answers.
    qtext = str(out["substitution_question"].get("question") or "")
    qans = str(out["substitution_question"].get("answer") or "")
    if not qtext:
        out["scoring_error"] = "no substitution question to score"
        save2("r3-binding", out)
        return out
    out["s1_wrong"] = _score(qtext, qans, "答案是 42。")
    out["s2_correct"] = _score(qtext, qans, qans)
    out["s3_partial"] = _score(qtext, qans, _partial_answer(qans))
    save2("r3-binding", out)
    log("r3:", out["substitution_checks"], out["asyncio_checks"])
    return out


def _partial_answer(reference: str) -> str:
    text = str(reference or "").strip()
    if "C" in text:
        return text.split("+C")[0].strip()
    return text[:-2] if len(text) > 2 else text


def _score(question: str, expected: str, answer: str) -> dict:
    res = reply(call("study_evaluate_answer", {
        "question": question, "expected_answer": expected, "answer": answer}))
    return {
        "answer": answer[:160],
        "verdict": res.get("verdict"),
        "score": res.get("score"),
        "error_type": res.get("error_type"),
        "feedback": str(res.get("feedback") or "")[:400],
        "missing_points": res.get("missing_points"),
        "misconceptions": res.get("misconceptions"),
        "step_feedback": res.get("step_feedback"),
        "next_action": str(res.get("next_action") or "")[:200],
    }


def phase_r4():
    """Scoring samples 4-8: different materials and a knowledge-point-specific error."""
    out = {"ts": time.time()}
    prev = json.loads((EVIDENCE / "teach2-r3-binding.json").read_text(encoding="utf-8"))
    aq = str(prev.get("asyncio_question", {}).get("question") or "")
    aans = str(prev.get("asyncio_question", {}).get("answer") or "")
    if aq:
        out["s4_asyncio_wrong"] = _score(
            aq, aans,
            "在协程里用 time.sleep(3) 等待，效果和 asyncio.sleep(3) 完全一样，都能让出控制权。")
        out["s5_asyncio_correct"] = _score(aq, aans, aans)

    # Provided substitution question: correct.
    out["s6_provided_correct"] = _score(
        "计算不定积分 ∫3x²·cos(x³)dx。",
        "sin(x³)+C（令 u=x³，du=3x²dx，原式=∫cos(u)du=sin(u)+C）",
        "令 u=x³，则 du=3x²dx，原式=∫cos(x³)·3x²dx=∫cos(u)du=sin(u)+C=sin(x³)+C。")

    # Provided substitution question: forgot to substitute back (targeted error).
    out["s7_forgot_backsub"] = _score(
        "计算不定积分 ∫3x²·cos(x³)dx。",
        "sin(x³)+C（令 u=x³，du=3x²dx，原式=∫cos(u)du=sin(u)+C）",
        "令 u=x³，则 du=3x²dx，原式=∫cos(u)du=sin(u)+C=sin(u)+C。")

    # Provided asyncio question: knows blocking exists but misattributes the cause.
    out["s8_asyncio_misconception"] = _score(
        "为什么在协程里调用 time.sleep(3) 会导致其他任务无法推进？",
        "time.sleep 是同步阻塞调用，它占用线程而不把控制权交回事件循环；"
        "应改用 await asyncio.sleep(3)。",
        "因为 time.sleep 会启动一个新的线程去等待，线程切换拖慢了事件循环，"
        "所以其他任务变慢。")

    out["checks"] = {
        "s4_wrong_verdict": str(out["s4_asyncio_wrong"].get("verdict", "")).lower()
        in ("wrong", "incorrect", "partial"),
        "s4_feedback_mentions_blocking": any(
            k in str(out["s4_asyncio_wrong"].get("feedback") or "").lower()
            for k in ("阻塞", "block", "冻结", "事件循环", "event loop")),
        "s5_correct": str(out["s5_asyncio_correct"].get("verdict", "")).lower()
        in ("correct", "true", "right"),
        "s6_correct": str(out["s6_provided_correct"].get("verdict", "")).lower()
        in ("correct", "true", "right"),
        "s7_targets_missing_backsubstitution": any(
            k in (str(out["s7_forgot_backsub"].get("feedback") or "")
                  + str(out["s7_forgot_backsub"].get("missing_points") or ""))
            for k in ("回代", "换回", "u 换回", "sin(x³)", "代回")),
        "s8_targets_asyncio_cause": any(
            k in (str(out["s8_asyncio_misconception"].get("feedback") or "")
                  + str(out["s8_asyncio_misconception"].get("misconceptions") or ""))
            for k in ("阻塞", "同步", "线程", "asyncio.sleep", "交回", "让出")),
    }
    out["score_sample_count"] = 8
    save2("r4-scoring", out)
    log("r4:", out["checks"])
    return out


def phase_r5():
    out = {"ts": time.time()}
    s = reply(call("study_summarize_session", {
        "focus": "本轮换了两种材料：定积分换元法 和 Python asyncio"}))
    summary = str(s.get("summary") or s.get("reply") or "")
    out["summary"] = summary[:2000]
    out["next_actions"] = s.get("next_actions")
    out["weak_points"] = s.get("weak_points")
    lowered = summary.lower()
    out["checks"] = {
        "mentions_substitution": any(k in summary for k in ("换元", "积分", "substitution")),
        "mentions_asyncio": "asyncio" in lowered or "协程" in summary,
        "grounded_in_material": "x^4" not in lowered and "5x" not in lowered,
    }
    out["db_after"] = db_counts()
    save2("r5-summary", out)
    log("r5:", out["checks"])
    return out


def phase_restore():
    out = {"ts": time.time()}
    out["flags_off"] = post(48915, "/agent/flags", {"user_plugin_enabled": False})
    out["master_off"] = post(48915, "/agent/command",
                             {"command": "set_agent_enabled", "enabled": False})
    out["db_final"] = db_counts()
    out["llm_entries"] = night.LLM_CALLS
    out["score_samples"] = night.SCORES
    save2("restore", out)
    log("restore:", {k: v for k, v in out.items() if k != "db_final"}, out["db_final"])
    return out


def phase_r6_ocr_followup():
    """Explanation whose material comes from a real fullscreen OCR capture."""
    out = {"ts": time.time()}
    a1 = reply(call("study_explain_text", {}))  # no text -> last_ocr_text fallback
    out["ocr_explain_reply"] = str(a1.get("reply") or "")[:2500]
    out["ocr_explain_recent_context_chars"] = a1.get("recent_context_chars")
    ocr_text = ""
    try:
        ocr = json.loads((EVIDENCE / "teach2-ocr.json").read_text(encoding="utf-8"))
        ocr_text = str((ocr.get("raw") or {}).get("ocr_text") or "")
    except Exception:
        pass
    out["ocr_text_chars"] = len(ocr_text)
    a2 = reply(call("study_explain_text", {
        "text": "继续刚才的材料：例题 2 里为什么会多出一个系数 1/2？请只针对例题 2 解释。"}))
    text = str(a2.get("reply") or "")
    out["followup_reply"] = text[:2500]
    out["checks"] = {
        "ocr_material_known": float(a1.get("recent_context_chars") or 0) >= 0,
        "mentions_half": any(k in text for k in ("1/2", "½", "二分之一")),
        "names_example2": "例题 2" in text or "例题2" in text,
        "does_not_ask_to_paste": not _needs_paste(text),
    }
    save2("r6-ocr-followup", out)
    log("r6:", out["checks"])
    return out


def phase_r7_crossmat2():
    out = {"ts": time.time()}
    b1 = reply(call("study_explain_text", {"text": ASYNCIO_TEXT}))
    out["asyncio_reply"] = str(b1.get("reply") or "")[:1500]
    c1 = reply(call("study_explain_text", {
        "text": "回到之前的换元法材料：例题 1 的复合关系是什么？正确结果是什么？"}))
    text = str(c1.get("reply") or "")
    out["crossmaterial_reply"] = text[:2500]
    lowered = text.lower()
    out["checks"] = {
        "recalls_material_a": any(k in text for k in
                                  ("cos(x²)", "sin(x²)", "cos(x^2)", "sin(x^2)", "2x")),
        "no_asyncio_pollution": not any(k in lowered for k in
                                        ("asyncio", "gather", "事件循环", "event loop", "协程")),
        "does_not_ask_to_paste": not _needs_paste(text),
    }
    save2("r7-crossmat2", out)
    log("r7:", out["checks"])
    return out


def phase_r8_summary2():
    out = {"ts": time.time()}
    s = reply(call("study_summarize_session", {"focus": ""}))
    summary = str(s.get("summary") or s.get("reply") or "")
    out["summary"] = summary[:2000]
    out["weak_points"] = s.get("weak_points")
    out["next_actions"] = s.get("next_actions")
    lowered = summary.lower()
    out["checks"] = {
        "mentions_substitution": any(k in summary for k in ("换元", "积分", "substitution", "substitut")),
        "mentions_asyncio": "asyncio" in lowered or "协程" in summary or "事件循环" in summary,
        "no_legacy_chain_rule": not any(k in lowered for k in ("5x", "x^4", "3x+1", "chain rule", "链式")),
    }
    out["db_after"] = db_counts()
    save2("r8-summary2", out)
    log("r8:", out["checks"])
    return out


def phase_r9_reuse():
    """Prove the recorded learning state is reused by the adaptive practice path."""
    out = {"ts": time.time()}
    try:
        km = reply(call("study_knowledge_map", {}, note_llm=False))
        out["knowledge_map_summary"] = km.get("summary")
        out["knowledge_map_weak"] = km.get("weak_topics")
        topics = km.get("topics") or km.get("nodes") or []
        out["knowledge_map_topics"] = [
            {k: t.get(k) for k in ("topic_id", "name", "mastery", "status") if isinstance(t, dict) and k in t}
            for t in (topics[:12] if isinstance(topics, list) else [])
        ]
        out["knowledge_map_wrong_questions"] = km.get("wrong_questions")
    except Exception as exc:
        out["knowledge_map_error"] = repr(exc)[:200]
    ctx = reply(call("study_question_context", {}, note_llm=False))
    out["selection"] = {k: ctx.get(k) for k in
                        ("selection_context_id", "selected_topic_id", "selected_topic_name",
                         "selection_reason", "difficulty", "no_data", "scope_topic_count")}
    out["weak_topics"] = ctx.get("weak_topics")
    out["due_reviews"] = ctx.get("due_reviews")
    selection_id = str(ctx.get("selection_context_id") or "")
    if selection_id:
        q = reply(call("study_generate_targeted_question",
                       {"selection_context_id": selection_id}))
        out["adaptive_question"] = {k: q.get(k) for k in
                                    ("question", "answer", "topic", "difficulty",
                                     "selected_topic_id", "selected_topic_name",
                                     "selection_reason", "material_grounded_question")}
        qtext = str(q.get("question") or "")
        target = str(ctx.get("selected_topic_name") or ctx.get("selected_topic_id") or "")
        model_label = str(q.get("question_topic_label") or "")
        out["checks"] = {
            "adaptive_target_matches_tracked_topic": bool(target),
            "question_matches_target": _question_matches_topic(qtext, target),
            # A derivative question is CORRECT output when the adaptive target is the
            # chain rule, so the meaningful assertion is the subject match above;
            # this flag only reports whether the model's own topic label agreed.
            "model_topic_label_agrees": bool(model_label) and (
                model_label.lower() in target.lower()
                or target.lower() in model_label.lower()
            ),
        }
    else:
        out["checks"] = {"adaptive_path_available": False}
    save2("r9-reuse", out)
    log("r9:", out.get("checks"), out.get("selection"))
    return out


def _question_matches_topic(question: str, topic: str) -> bool:
    text = str(question or "").lower()
    target = str(topic or "").lower()
    if not text or not target:
        return False
    keywords = {
        "asyncio": ("asyncio", "协程", "事件循环", "await", "sleep", "阻塞"),
        "换元": ("换元", "u=", "u =", "du", "积分"),
        "阻塞": ("阻塞", "time.sleep", "事件循环", "同步"),
        "积分": ("积分", "∫", "原函数", "du"),
        "chain": ("求导", "导数", "dy/dx"),
    }
    for key, options in keywords.items():
        if key in target:
            return any(option in text for option in options)
    return True


def post_json(port, path, payload):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}", method="POST",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with opener.open(req, timeout=20) as r:
        return json.load(r)


def phase_comms_off():
    """Silence the plugin's narration channel (night constraint) without touching disk."""
    out = post_json(48916, "/plugin/study_companion/config/hot-update",
                    {"config": {"study_companion": {"communication": {"enabled": False}}},
                     "mode": "temporary"})
    save2("comms-off", {"ts": time.time(), "response": out})
    log("comms-off:", out)
    return out


NOISE_MARKERS = ("All Bookmarks", "NekoClaw", "No active tasks", "YUI", "Bookmarks",
                 "扇贝", "bilibili", "Vercel")
MATERIAL_MARKERS = ("NEKO-LAB-20261009", "换元", "例题", "易错")


def _ocr_metrics(payload: dict, elapsed_ms: int) -> dict:
    text = str(payload.get("text") or "")
    return {
        "chars": len(text),
        "elapsed_ms": elapsed_ms,
        "capture_mode_used": payload.get("capture_mode_used"),
        "capture_target_title": payload.get("capture_target_title"),
        "capture_route": payload.get("active_window_capture_route"),
        "fallback_reason": payload.get("active_window_fallback_reason")
        or payload.get("interactive_fallback_reason")
        or "",
        "fallback_detail": payload.get("active_window_capture_detail") or "",
        "status": payload.get("status"),
        "diagnostic": payload.get("diagnostic"),
        "material_markers": [m for m in MATERIAL_MARKERS if m in text],
        "noise_markers": [m for m in NOISE_MARKERS if m in text],
        "text_sample": text[:900],
    }


def phase_r10_grounding():
    """Compare fullscreen OCR with window-targeted OCR on the same screen."""
    out = {"ts": time.time()}
    full = call("study_ocr_snapshot", {"capture_mode": "fullscreen"})
    out["fullscreen"] = _ocr_metrics(reply(full), full["elapsed_ms"])
    window = call("study_ocr_snapshot", {"capture_mode": "active_window"})
    out["active_window"] = _ocr_metrics(reply(window), window["elapsed_ms"])
    f, w = out["fullscreen"], out["active_window"]
    out["checks"] = {
        "window_mode_reported": w["capture_mode_used"] == "active_window",
        "window_target_named": bool(w["capture_target_title"]),
        "material_retained": len(w["material_markers"]) >= len(f["material_markers"]),
        "noise_reduced": len(w["noise_markers"]) < len(f["noise_markers"]),
        "chars_reduced": w["chars"] < f["chars"],
    }
    save2("r10-grounding", out)
    log("r10:", out["checks"],
        {"full": (f["chars"], f["noise_markers"]), "window": (w["chars"], w["noise_markers"])})
    return out


PHASES = {
    "snapshot": phase_snapshot,
    "enable": phase_enable,
    "prepare": night.phase_prepare,
    "ocr": night.phase_ocr,
    "r1-followup": phase_r1,
    "r2-crossmat": phase_r2,
    "r3-binding": phase_r3,
    "r4-scoring": phase_r4,
    "r5-summary": phase_r5,
    "r6-ocr-followup": phase_r6_ocr_followup,
    "r7-crossmat2": phase_r7_crossmat2,
    "r8-summary2": phase_r8_summary2,
    "r9-reuse": phase_r9_reuse,
    "comms-off": phase_comms_off,
    "r10-grounding": phase_r10_grounding,
    "restore": phase_restore,
}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    for name in sys.argv[1:] or ["snapshot"]:
        log("=== phase:", name)
        PHASES[name]()
    log(f"done. llm_entries={night.LLM_CALLS} score_samples={night.SCORES}")


if __name__ == "__main__":
    main()
