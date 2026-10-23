"""Real image -> follow-up -> quiz -> grading through existing Study entries.

Needs the guarded disposable host. No host, hardware, credentials or retry here.
The provided directory contains captures of existing diagrams, not generated ones.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path

from neko_lab_client import LabClient

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "benchmarks/raw/neko-desktop-egress-cap"


def main(args):
    def ledger():
        return json.loads(LEDGER.read_text(encoding="utf-8"))
    before = ledger()
    assert before["round"] == "bargein-autocheck-20261012"
    assert before["budgets"] == {"api.deepseek.com": 300.0, "www.lanlan.app": 30.0,
                                 "www.lanlan.tech": 0.0}
    assert not args.output.exists(), "do not repeat a recorded real scene"
    client = LabClient()
    report = {"before": before, "steps": [], "microphone": False, "playback": False,
              "route": "existing Study image entry and model-callable teaching tools"}

    def call(entry, **kwargs):
        assert ledger()["spent"].get("api.deepseek.com", 0) < 300
        result = client.call(entry, kwargs, timeout=160)
        data = result["data"]
        evidence_args = {k: v for k, v in kwargs.items() if k != "image_base64"}
        if "image_base64" in kwargs:
            encoded = kwargs["image_base64"].split(",", 1)[-1]
            pixels = base64.b64decode(encoded)
            evidence_args.update(image_sha256=hashlib.sha256(pixels).hexdigest(), image_bytes=len(pixels))
        report["steps"].append({"entry": entry, "args": evidence_args, "result": result, "ledger": ledger()})
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        print(json.dumps({"entry": entry, "reply": data.get("reply", data.get("question", data.get("feedback", ""))),
                          "degraded": data.get("degraded"), "verdict": data.get("verdict"),
                          "score": data.get("score"), "spent": ledger()["spent"]}, ensure_ascii=False), flush=True)
        assert not data.get("degraded"), f"stop on degraded {entry}: {data.get('diagnostic')}"
        return data

    def image(name, prompt):
        pixels = (args.images / f"diagram-input-{name}.png").read_bytes()
        return call("study_submit_image", image_base64=base64.b64encode(pixels).decode(), text=prompt)

    call("study_update_settings_config", config={"llm": {"llm_vision_enabled": True, "llm_vision_max_image_px": 2048}})
    call("study_start_session", course_id="sky-scout-vision-closure-20261014")
    call("study_set_mode", mode="teaching", reason="real image teaching acceptance")
    image("forward", "只看当前图，按箭头尖端列出起点→终点，不按排版猜，不出题。")
    # This call has no image argument: it must retain the explicitly submitted pixels.
    call("__llm_tool__study_explain", question="这张关系图的两个箭头从哪里指向哪里？只用两句话，不出题。")
    image("reverse", "已经换图，按当前图的箭头尖端列出起点→终点，不按旧图或排版猜，不出题。")
    call("__llm_tool__study_explain", question="这张新关系图的两个箭头方向是什么？只用两句话，不出题。")
    image("sky-dark", "只看这张 Sky Scout 图，用中文讲解本地星图和网络请求两条路径。逐一说明模块与连接；区分图中读取请求方向和推断的数据返回方向；不猜小字标注，不出题。")
    call("__llm_tool__study_explain", question="结合当前图，用三句话解释星表是从哪里读取、计算绘制在哪里完成，以及 Express 是否负责星图计算。不要出题。")
    quiz = call("study_generate_question", topic="sky-scout-client-local-computation", text="根据当前图只出一道开放题：判断星图坐标计算和绘制是在客户端还是 Express 后端，并解释理由。题目必须相关于这张图，不给答案。")
    pending = {k: quiz[k] for k in ("question", "question_id", "attempt_id")}
    wrong = call("study_evaluate_answer", answer="是在 Express 后端计算和绘制，然后客户端只显示服务端生成的图片。", **pending)
    assert wrong.get("verdict") == "wrong", "known misconception was not rejected"
    call("__llm_tool__study_explain", question="根据当前图纠正我刚才把星图计算绘制放在 Express 的错误，用三句话，不出新题。")
    second = call("study_generate_question", topic="sky-scout-client-local-computation", text="根据当前图再出一道等价的开放题，检验星图计算和绘制在客户端还是 Express，并要求解释理由，不给答案。")
    pending = {k: second[k] for k in ("question", "question_id", "attempt_id")}
    correct = call("study_evaluate_answer", answer="星图坐标计算和绘制在客户端本地观测流水线完成，读取随 App 打包的星表，并根据地点和时间重算。Express 负责天气和百科接口，不负责星图计算绘制。", **pending)
    assert correct.get("verdict") == "correct", "correct diagram explanation was not accepted"
    call("study_summarize_session", focus="总结这张 Sky Scout 图的两条路径，保留我把星图计算绘制误放到 Express 的错题和后来改正的记录。")
    report["after"] = ledger()
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    main(parser.parse_args())
