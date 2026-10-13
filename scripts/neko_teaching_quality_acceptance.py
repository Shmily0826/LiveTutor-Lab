"""Bounded real Study /runs checks; run prepare, restart the host, then resume.

Uses the existing LabClient and an isolated course. Does not launch hosts/devices,
read credentials, reset quota, or retry a failed run. Outputs are retained for review.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from neko_lab_client import LabClient

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "benchmarks/raw/evidence/teaching-quality-20261013-results.json"
COURSE = "python-functions-quality-20261013"
LESSON = """用中文教零基础学生，用计算器加法解释函数、参数、返回值和接收结果的变量。
def add(a, b):
    total = a + b
    return total
result = add(2, 3)
print(result)
请准确说明：a/b 是参数，2/3 是实参，total 是局部变量，return 把结果交给调用者，result 接收返回值，打印 5。
一次讲一个概念，使用上面的代码，不引入类或异步，不用反问代替讲解，控制在约 250 个中文字。"""
QUESTION = """基于刚才的计算器 add 函数，只出一道开放题：
如果删掉 return total，result = add(2, 3) 后 print(result) 会输出什么？为什么？
请使用题目明确的代码，不改成其他主题。只提问，暂时不要向学生透露答案。"""


def ledger():
    return json.loads((ROOT / "benchmarks/raw/neko-desktop-egress-cap").read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "resume", "continuity"))
    args = parser.parse_args()
    before = ledger()
    assert before["round"] == "bargein-autocheck-20261012"
    assert before["budgets"] == {"api.deepseek.com": 120.0, "www.lanlan.app": 16.0, "www.lanlan.tech": 0.0}
    report = json.loads(REPORT.read_text(encoding="utf-8")) if REPORT.exists() else {"course": COURSE, "steps": []}
    client = LabClient()

    def call(entry, **arguments):
        assert ledger()["spent"].get("api.deepseek.com", 0) < 120, "stop: cumulative cap reached"
        result = client.call(entry, arguments)
        data = result["data"]
        row = {"at": datetime.now(timezone.utc).isoformat(), "entry": entry, "args": arguments,
               "result": result, "ledger": ledger()}
        report["steps"].append(row)
        REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        print(json.dumps({"entry": entry, "run_id": result["run_id"], "degraded": data.get("degraded"),
            "reply": str(data.get("reply") or data.get("question") or data.get("summary") or "")[:1800],
            "verdict": data.get("verdict"), "score": data.get("score"),
            "reply_chars": len(str(data.get("reply") or "")),
            "paid_spent": row["ledger"]["spent"].get("api.deepseek.com")}, ensure_ascii=False), flush=True)
        assert not data.get("degraded"), f"stop: {entry} degraded ({data.get('diagnostic')})"
        return data

    if args.phase == "prepare":
        assert not report["steps"], "prepare already recorded; do not repeat paid work"
        session = call("study_start_session", course_id=COURSE)
        report["first_session_id"] = session["session_id"]
        call("study_set_mode", mode="teaching", reason="bounded teaching-quality acceptance")
        call("study_explain_text", text=LESSON)
        question = call("study_generate_question", text=QUESTION, topic="python-functions-return")
        assert question.get("question_id") and question.get("attempt_id")
        report["pending_question"] = {key: question[key] for key in ("question", "question_id", "attempt_id")}
    elif args.phase == "resume":
        assert report.get("pending_question"), "prepare has no pending question"
        assert not report.get("resume_complete"), "resume already completed; do not repeat paid work"
        pending = report["pending_question"]
        evaluation = call("study_evaluate_answer", answer="会输出 5；即使不写 return，Python 也会自动返回函数里最后算出的数。",
                          **pending)
        assert evaluation["verdict"] == "wrong", "the known misconception was not graded wrong"
        call("study_explain_text", text="结合我刚才关于没写 return 仍输出 5 的错误，解释为什么实际是 None，帮我分清计算结果和返回值。")
        second = call("study_generate_question", text=QUESTION, topic="python-functions-return")
        correct = call("study_evaluate_answer", answer="输出 None。a+b 仍然算出 5 并存进局部变量 total，但没有 return 把它传给调用者，函数默认返回 None，所以 result 是 None。",
                       **{key: second[key] for key in ("question", "question_id", "attempt_id")})
        assert correct["verdict"] == "correct", "the correct explanation was not graded correct"
        summary = call("study_summarize_session", focus="记录这门课解释过的函数、参数和返回值，以及我把计算结果误当返回值的错题、后来的正确回答和下一步练习。")
        report["summary"] = summary
        report["resume_complete"] = True
    else:
        assert report.get("resume_complete"), "complete grading before continuity check"
        assert not report.get("continuity_complete"), "continuity already recorded; do not repeat paid work"
        call("study_explain_text", text="重启前我哪一点答错了？用四句话回顾那道题、我的错误和正确规则，不要出新题。")
        call("study_explain_text", text=LESSON)
        report["continuity_complete"] = True
    report["after"] = ledger()
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"phase": args.phase, "artifact": str(REPORT), "ledger": ledger()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
