"""Offline regression for the Session Summary scope fix. No provider call, no browser.

The summarize context used to derive a session boundary from the bounded in-memory
learning-event ring, which dropped the session's earliest interactions because a row
is stamped before the event that records it. It must now use the rows' own session id.
"""
from __future__ import annotations

import asyncio
import importlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import neko_study_plugin_methods_fixture as core  # noqa: E402

LESSON = "例题2：计算 ∫x·e^(x^2) dx。令 u=x^2，则 du=2x dx。"
FOLLOW_UP = "为什么例题2有1/2？"
ANSWER = "u=x^2, du=2x dx, so the integral is (1/2)e^(x^2)+C."


class SummaryScopeTest(unittest.TestCase):
    def test_graded_answer_stays_in_its_own_session_summary_context(self) -> None:
        # Windows' proactor loop needs its internal loopback pair created before
        # the network guard is installed, exactly like the method fixture's main().
        loop = asyncio.new_event_loop()
        core._install_guards()
        try:
            seen = loop.run_until_complete(self._run(loop))
        finally:
            loop.close()
        self.assertEqual(
            seen["session_history_count"],
            seen["interaction_count"],
            f"summary context dropped interactions: {seen}",
        )
        self.assertTrue(seen["answer_in_prompt"], "graded answer missing from summarize prompt")
        self.assertTrue(seen["lesson_in_prompt"], "first explanation missing from summarize prompt")

    async def _run(self, loop: asyncio.AbstractEventLoop) -> dict[str, object]:
        plugin_module, plugin, _gates = await core.bootstrap_plugin()
        plugin._agent = core.LocalAgentDouble(plugin_module.TutorReply, LESSON)
        session_id = str(
            core._result_payload(await plugin.study_start_session()).get("session_id") or ""
        )
        self.assertTrue(session_id)
        await plugin.study_explain_text(text=LESSON, session_id=session_id)
        await plugin.study_explain_text(text=FOLLOW_UP, session_id=session_id)
        asked = core._result_payload(
            await plugin.study_generate_question(text=LESSON, topic="u-substitution", session_id=session_id)
        )
        await plugin.study_evaluate_answer(
            answer=ANSWER,
            question=asked["question"],
            expected_answer=asked["answer"],
            question_id=asked.get("question_id"),
            attempt_id=asked.get("attempt_id"),
            selected_topic_id="u-substitution",
            session_id=session_id,
        )
        context = await plugin._build_learning_context(
            "summarize_session", input_text="session", session_id=session_id
        )
        messages = importlib.import_module(
            "plugins.study_companion.llm_prompts"
        ).build_summarize_session_messages(
            language=str(plugin._cfg.language), mode="teaching", context=context
        )
        prompt = json.dumps(messages, ensure_ascii=False)
        rows = await asyncio.to_thread(plugin._store.list_interactions, 50, session_id=session_id)
        # Show the mechanism the old code used, so the regression stays meaningful:
        # the ring boundary is the earliest event time, which is stamped after the
        # row that produced it, so that first row fell below it.
        ring_start = min(
            (
                float(event.get("at"))
                for event in (plugin._state.recent_learning_events or [])
                if isinstance(event, dict) and isinstance(event.get("at"), (int, float))
            ),
            default=None,
        )
        self.assertIsNotNone(ring_start)
        self.assertTrue(
            any(
                float(row.get("created_at") or 0.0) < float(ring_start or 0.0)
                for row in rows
            ),
            "expected the earliest session row to predate the event ring boundary",
        )
        return {
            "interaction_count": len(rows),
            "session_history_count": len(context.get("session_history") or []),
            "answer_in_prompt": ANSWER in prompt,
            "lesson_in_prompt": LESSON in prompt,
            "kinds": sorted({str(row.get("kind") or "") for row in rows}),
        }


if __name__ == "__main__":
    unittest.main(verbosity=2)
