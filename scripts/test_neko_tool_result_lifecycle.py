"""Offline reproduction: a tool result that goes stale must not vanish without a trace.

What the lifecycle does today, read from the runtime host tree
(`benchmarks/raw/neko-product-host/main_logic/omni_realtime_client/_tools.py`): when a new user
turn advances the tool scope while a call is still running, the batch collector reaches
`if not self._tool_task_owner_is_current(owner): return []` and the finished results are dropped.
Not injecting a stale result into somebody else's turn is right - the provider would see an
answer to a function call it already abandoned. What is wrong is the silence: nothing records
that N results were discarded and why, so the user sees a turn that simply never answers and
there is no way to tell "the tool was slow", "the tool failed" and "the result was thrown away"
apart. That is the same class of failure that cost a whole debugging round on the mute gate.

Two cases, because the fix must not break the good path:
* stale result -> nothing sent (correct today) AND a traceable log line (missing today);
* live result, nothing interrupts it -> output + continuation sent (must stay green).

No network, no model, no devices: the client talks to a queue socket.
"""
from __future__ import annotations

import asyncio
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOST = ROOT / "benchmarks" / "raw" / "neko-product-host"
sys.path.insert(0, str(HOST))

from main_logic.omni_realtime_client import OmniRealtimeClient  # noqa: E402
from main_logic.omni_realtime_client import _tools as tools_mod  # noqa: E402
from main_logic.tool_calling import ToolCall, ToolResult  # noqa: E402


class LogRecorder:
    """Stands in for the module logger so a drop is something we can look for."""

    def __init__(self) -> None:
        self.lines: list[tuple[str, str]] = []

    def _log(self, level, message, *args):
        self.lines.append((level, (message % args) if args else str(message)))

    def warning(self, message, *args):
        self._log("warning", message, *args)

    def error(self, message, *args):
        self._log("error", message, *args)

    def exception(self, message, *args):
        self._log("error", message, *args)

    def info(self, message, *args):
        self._log("info", message, *args)

    def debug(self, message, *args):
        self._log("debug", message, *args)

    def text(self) -> str:
        return "\n".join(f"{level}:{line}" for level, line in self.lines)


class QueueSocket:
    def __init__(self) -> None:
        self._messages: asyncio.Queue = asyncio.Queue()
        self.sent: list[dict] = []
        self.closed = False

    def __aiter__(self):
        return self

    async def __anext__(self):
        message = await self._messages.get()
        if message is None:
            raise StopAsyncIteration
        return json.dumps(message)

    def feed(self, event: dict) -> None:
        self._messages.put_nowait(event)

    async def send(self, payload: str) -> None:
        self.sent.append(json.loads(payload))

    async def close(self) -> None:
        self.closed = True


async def _drain(client: OmniRealtimeClient, limit: float = 2.0) -> None:
    deadline = asyncio.get_running_loop().time() + limit
    while asyncio.get_running_loop().time() < deadline:
        pending = [task for task in getattr(client, "_tool_tasks", set()) if not task.done()]
        if not pending:
            return
        await asyncio.wait(pending, timeout=0.05)


class ToolResultLifecycleTest(unittest.TestCase):
    def setUp(self) -> None:
        self.recorder = LogRecorder()
        self._real_logger = tools_mod.logger
        tools_mod.logger = self.recorder  # type: ignore[attr-defined]

    def tearDown(self) -> None:
        tools_mod.logger = self._real_logger  # type: ignore[attr-defined]

    def _client(self, handler) -> tuple[OmniRealtimeClient, QueueSocket]:
        client = OmniRealtimeClient("wss://example.invalid/realtime", "test-key",
                                     api_type="gpt", on_tool_call=handler)
        socket = QueueSocket()
        client.ws = socket
        client._on_connection_attached()
        return client, socket

    def _call(self, call_id: str = "call_alpha") -> ToolCall:
        return ToolCall(name="study_code", arguments={"query": "where is render"},
                        call_id=call_id, raw_arguments="{}", provider_meta=None)

    def _start(self, client: OmniRealtimeClient, socket: QueueSocket):
        owner = client._capture_tool_task_owner(socket)
        task = client._start_raw_tool_call(self._call(), owner, response_id="resp_1")
        return owner, task

    def test_live_result_is_still_delivered(self) -> None:
        async def scenario() -> None:
            client, socket = self._client(self._slow_handler(release_after=0.0))
            self._start(client, socket)
            await _drain(client)
            kinds = [event.get("type") for event in socket.sent]
            payloads = json.dumps(socket.sent, ensure_ascii=False)
            self.assertIn("conversation.item.create", kinds, f"nothing was sent at all: {kinds}")
            self.assertIn("function_call_output", payloads)
            self.assertIn("response.create", payloads)

        asyncio.run(scenario())

    def test_stale_result_is_dropped_and_leaves_a_trace(self) -> None:
        """The drop itself is correct; doing it invisibly is not."""
        release: asyncio.Event = asyncio.Event()

        async def scenario() -> None:
            client, socket = self._client(self._slow_handler(release_after=None, gate=release))
            owner, _task = self._start(client, socket)
            await asyncio.sleep(0.05)            # the tool is now running
            client.note_user_turn_started()      # a new user input retires its scope
            release.set()                        # ... and it finishes anyway
            await _drain(client)
            payloads = json.dumps(socket.sent, ensure_ascii=False)
            self.assertNotIn("call_alpha", payloads,
                             "a retired turn's result was injected into the new turn")
            trace = [line for _, line in self.recorder.lines
                     if "stale" in line or "dropped" in line]
            self.assertTrue(
                trace,
                "the tool result was discarded in silence - no log line says how many results "
                f"were dropped or why; sent={payloads[:120]} logs={self.recorder.text()[:400]}")
            self.assertTrue(any(("call_alpha" in line or "1" in line) for line in trace),
                            f"the trace does not identify what was dropped: {trace}")

        asyncio.run(scenario())

    def _slow_handler(self, *, release_after, gate: asyncio.Event | None = None):
        async def handler(call: ToolCall) -> ToolResult:
            if gate is not None:
                await gate.wait()
            elif release_after:
                await asyncio.sleep(release_after)
            return ToolResult(call_id=call.call_id, name=call.name,
                              output={"evidence": "note_store.dart:4"})
        return handler

    # ------------------------------------------------------------------
    # The turn the learner could not get back from (2026-10-11 23:12-23:24,
    # recorded: the last audible answer at 23:12:36, then four more learner
    # utterances and 11 minutes of complete silence).
    #
    # The state pair is not hypothetical -- the field log produced it four
    # times, each as `owner_scope=12 current_scope=12` with
    # `reason=provider_turn_snapshot_mismatch`. Scope did NOT move, the
    # connection did NOT move, the session did NOT move. Only the pair this
    # owner sampled at capture disagreed, because the host had minted a newer
    # speech id than the one stamped by the last `response.created` we were
    # allowed to see. The free proxy opens a response per transcript fragment
    # and does not announce them, so a function call can arrive carrying no
    # observable response anchor at all.
    #
    # Dropping on that evidence answers a call the provider is still waiting
    # for, which is the difference between "one turn went missing" and "the
    # character never speaks again until the app is restarted".
    # ------------------------------------------------------------------

    def _mismatched_owner(self, client, socket, *, host_turn_id: str, stamped: str):
        """Capture an owner whose pair disagrees, exactly as the field log shows."""
        client.get_host_turn_id = lambda: host_turn_id
        client._current_turn_host_id = stamped
        owner = client._capture_tool_task_owner(socket)
        self.assertEqual(owner.host_turn_id, host_turn_id)
        self.assertEqual(owner.provider_turn_host_id, stamped)
        self.assertEqual(owner.scope_generation, getattr(client, "_tool_scope_generation", 0))
        self.assertEqual(client._stale_fence(owner), "provider_turn_snapshot_mismatch")
        return owner

    def test_orphaned_call_is_still_answered(self) -> None:
        """A call the provider never announced must not be left unanswered.

        The other three fences still apply in full: same connection, same tool
        scope, same provider session. This only refuses to let a pair that was
        never comparable decide that the provider abandoned its own call.
        """
        async def scenario() -> None:
            client, socket = self._client(self._slow_handler(release_after=0.0))
            owner = self._mismatched_owner(client, socket,
                                           host_turn_id="speech_2", stamped="speech_1")
            client._start_raw_tool_call(self._call(), owner, response_id="resp_new")
            await _drain(client)
            payloads = json.dumps(socket.sent, ensure_ascii=False)
            self.assertIn("call_alpha", payloads,
                          "the learner is gone: the provider is still waiting for an output "
                          f"we chose to discard. sent={payloads[:200]} "
                          f"logs={self.recorder.text()[:300]}")
            self.assertIn("function_call_output", payloads)
            # Relaxing a fence has to be loud, or the next person re-derives it.
            self.assertTrue(any("provider_turn_snapshot_mismatch" in line
                                for _, line in self.recorder.lines),
                            f"nothing records why the pair fence was skipped: {self.recorder.text()[:300]}")

        asyncio.run(scenario())

    def test_a_retired_turn_does_not_wedge_the_next_one(self) -> None:
        """A turn the learner replaced must not cost them the session.

        The retired result stays withheld - that part is right, and by then the
        proxy has already opened a response for the new utterance, so nothing is
        left waiting on it. What has to be true is that the wedge does not
        outlive the turn: the next call, captured under the new scope, must still
        reach the provider. This is the shape that turned one lost answer into
        eleven silent minutes, and it is checked here rather than asserted.
        """
        release: asyncio.Event = asyncio.Event()

        async def scenario() -> None:
            client, socket = self._client(self._slow_handler(release_after=None, gate=release))
            client.get_host_turn_id = lambda: "speech_1"
            client._current_turn_host_id = "speech_1"
            owner = client._capture_tool_task_owner(socket)
            client._start_raw_tool_call(self._call("call_alpha"), owner, response_id="resp_1")
            await asyncio.sleep(0.05)
            client.note_user_turn_started()      # a real new user turn: scope DOES move
            release.set()
            await _drain(client)
            payloads = json.dumps(socket.sent, ensure_ascii=False)
            self.assertNotIn('"evidence"', payloads,
                             "a retired turn's real result leaked into the new turn")
            self.assertEqual(client._stale_fence(owner), "user_turn_replaced")
            self.assertTrue(any("dropped" in line for _, line in self.recorder.lines),
                            f"the retirement left no trace: {self.recorder.text()[:200]}")

            # And the conversation is not over: the next call must get through.
            client._current_turn_host_id = "speech_2"
            next_owner = client._capture_tool_task_owner(socket)
            client._start_raw_tool_call(self._call("call_beta"), next_owner, response_id="resp_2")
            await _drain(client)
            after = json.dumps(socket.sent, ensure_ascii=False)
            self.assertIn("call_beta", after,
                          "the session never recovered: nothing after the retired turn is "
                          f"answered either. sent={after[:220]} logs={self.recorder.text()[:200]}")

        asyncio.run(scenario())


    def test_the_repo_patch_reproduces_the_host_tree(self) -> None:
        """The patch is the deliverable; the gitignored tree is only where it runs.

        `benchmarks/` is ignored by this repository, so a fix left only there is invisible to
        review and gone on a fresh clone. This takes the current host file back to pristine by
        undoing every replacement, then replays the patch onto that pristine text and requires
        byte equality - which is what proves the repo copy can rebuild the fix from scratch.
        """
        import tempfile

        import neko_voice_host_patch as patch

        for host in patch.HOSTS:
            for relative, replacements in patch.TARGETS:
                path = host / relative
                self.assertTrue(path.is_file(), path)
                current = path.read_text(encoding="utf-8")
                pristine = current
                for old, new in reversed(replacements):
                    self.assertEqual(pristine.count(new), 1, f"{path}: a replacement is not unique")
                    pristine = pristine.replace(new, old)
                scratch = Path(tempfile.mkdtemp(prefix="neko-patch-roundtrip-")) / relative
                scratch.parent.mkdir(parents=True, exist_ok=True)
                scratch.write_text(pristine, encoding="utf-8", newline="\n")
                self.assertEqual(patch.state(scratch), "pristine", path.name)
                self.assertEqual(patch.apply_to(scratch), "patched")
                self.assertEqual(scratch.read_text(encoding="utf-8"), current, path.name)
                self.assertEqual(patch.state(path), "patched", f"{path} drifted from the repo patch")


if __name__ == "__main__":
    unittest.main(verbosity=2)
