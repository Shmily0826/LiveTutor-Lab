"""Reopen only a fixture SQLite file read-only after the UI adapter has stopped."""
from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import sys


ROOT = Path(__file__).resolve().parents[1]


def verify(proof_path: str) -> dict[str, object]:
    proof_file = (ROOT / proof_path).resolve()
    assert proof_file.is_relative_to(ROOT / "benchmarks/raw/evidence"), "fixture proof only"
    proof = json.loads(proof_file.read_text(encoding="utf-8"))
    database = (ROOT / proof["db_path"]).resolve()
    assert database.is_relative_to(ROOT / ".tmp-uv-cache/neko-study-method-fixture"), "temporary fixture database only"
    assert database.is_file(), "fixture database missing"
    session_id = proof["session_id"]
    # The deterministic double produced fixed strings; a live model does not, so
    # what must hold either way is that the persisted row equals what the UI showed.
    live_model = proof.get("model_backend") == "real"
    with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only=ON")
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        session = conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
        assert session is not None
        rows = [dict(row) for row in conn.execute(
            "SELECT * FROM interactions WHERE session_id=? ORDER BY id", (session_id,)
        )]
        assert len(rows) == proof["interaction_count"]
        assert {str(row["id"]) for row in rows} == {row["id"] for row in proof["sqlite_interactions"]}
        explanations = [run for run in proof["runs"] if run["entry_id"] == "study_explain_text"]
        assert len(explanations) == 3
        assert explanations[0]["args"]["text"] == proof["ocr"]["text"]
        matched = []
        for run in explanations:
            hits = [row for row in rows if row["input_text"] == run["args"]["text"] and row["output_text"] == run["data"]["reply"]]
            assert len(hits) == 1, "explanation/follow-up was not persisted exactly once"
            matched.append({"run_id": run["run_id"], "interaction_id": hits[0]["id"], "kind": hits[0]["kind"]})
        question = next(run for run in proof["runs"] if run["entry_id"] == "study_generate_targeted_question")
        question_rows = [row for row in rows if row["output_text"] == question["data"]["question"] and row["kind"] == "question_generate"]
        assert len(question_rows) == 1, "generated question missing from SQLite"
        grade = next(run for run in proof["runs"] if run["entry_id"] == "study_evaluate_answer")
        assert grade["args"].get("question_id") == question["data"].get("question_id")
        assert grade["args"].get("attempt_id") == question["data"].get("attempt_id")
        if live_model:
            assert grade["data"]["verdict"] in {"correct", "partial", "wrong", "dont_know"}
            assert isinstance(grade["data"]["score"], int) and 0 <= grade["data"]["score"] <= 100
        else:
            assert grade["data"]["verdict"] == "correct" and grade["data"]["score"] == 100
        grade_rows = [row for row in rows if row["input_text"] == grade["args"]["answer"]]
        assert len(grade_rows) == 1, "answer evaluation missing from SQLite"
        grade_metadata = json.loads(grade_rows[0]["metadata"])
        assert grade_metadata["question_id"] == question["data"]["question_id"]
        assert grade_metadata["attempt_id"] == question["data"]["attempt_id"]
        if live_model:
            assert grade_metadata["payload"]["score"] == grade["data"]["score"]
            assert grade_metadata["payload"]["verdict"] == grade["data"]["verdict"]
        else:
            assert grade_metadata["payload"]["score"] == 100 and grade_metadata["payload"]["verdict"] == "correct"
        mastery = conn.execute(
            "SELECT * FROM mastery_snapshots WHERE topic_id=? ORDER BY id DESC LIMIT 1",
            ("fixture_u_substitution",),
        ).fetchone()
        assert mastery and mastery["mastery"] == proof["mastery"]
        assert mastery["mastery"] > proof["mastery_before_ui_answer"]
        summaries = [run for run in proof["runs"] if run["entry_id"] == "study_summarize_session"]
        assert len(summaries) == 2
        if live_model:
            # A live model does not repeat itself verbatim: what must match is
            # the persisted history both calls were built from, not the wording.
            summary_actions = [group for group in proof.get("model_calls_by_ui_action", [])
                               if group["entry_id"] == "study_summarize_session"]
            assert len(summary_actions) == 2 and all(group["model_call_count"] >= 1 for group in summary_actions)
            assert all(str(item["data"].get("reply") or "").strip() for item in summaries)
            assert all(not item["data"].get("degraded") for item in summaries)
        else:
            summary_calls = [call for call in proof["agent_double_calls"] if call["method"] == "summarize_session"]
            assert len(summary_calls) == 2
            assert all(call["history_count"] == len(rows) and set(call["history_interaction_ids"]) == {str(row["id"]) for row in rows} for call in summary_calls)
            assert summaries[0]["data"]["summary"] == summaries[1]["data"]["summary"]
        assert session["question_count"] == 1 and "fixture_u_substitution" in json.loads(session["topics_touched"])
        return {
            "result": "PASS_REOPENED_TEMP_SQLITE", "read_only": True,
            "db_path": proof["db_path"], "session_id": session_id,
            "integrity_check": "ok", "interaction_count": len(rows),
            "explanation_run_to_sqlite_rows": matched,
            "question_id": question["data"]["question_id"], "attempt_id": question["data"]["attempt_id"],
            "grade_interaction_id": grade_rows[0]["id"],
            "question_interaction_id": question_rows[0]["id"],
            "mastery": mastery["mastery"], "mastery_snapshot_id": mastery["id"],
            "summary_count": len(summaries),
        }


if __name__ == "__main__":
    print(json.dumps(verify(sys.argv[1]), ensure_ascii=False))
