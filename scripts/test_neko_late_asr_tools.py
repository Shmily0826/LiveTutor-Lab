"""Actual product tool lifecycle methods; offline late-ASR ordering repro only."""
from __future__ import annotations

import ast
import asyncio
from dataclasses import dataclass, field
import hashlib
import logging
from pathlib import Path
import sys
import time
import types
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "candidates/N.E.K.O/main_logic/omni_realtime_client/_tools.py"


@dataclass
class ToolResult:
    call_id: str
    name: str
    output: object
    is_error: bool = False
    error_message: str = ""


tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
module = types.ModuleType("late_asr_actual_tools")
sys.modules[module.__name__] = module
module.__dict__.update({"dataclass": dataclass, "field": field, "asyncio": asyncio,
                       "hashlib": hashlib, "logger": logging.getLogger("late-asr-repro"),
                       "time": time, "ToolResult": ToolResult})
# Compile the actual product's classes/constants/functions, excluding imports that
# initialize the desktop stack. No copied implementation of ownership or batching.
nodes = [node for node in tree.body if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef, ast.Assign))]
exec(compile(ast.fix_missing_locations(ast.Module(body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0), *nodes],
                                               type_ignores=[])), str(SOURCE), "exec"), module.__dict__)


class Harness(module._ToolingMixin):
    def __init__(self):
        self._connection_generation = 1
        self._tool_scope_generation = 1
        self._is_gemini = False
        self.ws = object()
        self._current_response_id = None
        self._current_turn_host_id = None
        self.release = asyncio.Event()
        self.entered = asyncio.Event()
        self.outputs = []

    def _read_host_turn_id(self):
        return None

    async def _execute_tool_call(self, call):
        self.entered.set()
        await self.release.wait()
        return ToolResult(call.call_id, call.name, {"ok": True})

    async def _send_tool_results_openai_realtime(self, results, **kwargs):
        self.outputs.extend(results)


class LateAsrToolsTest(unittest.IsolatedAsyncioTestCase):
    def call(self, identifier="call-one"):
        return types.SimpleNamespace(name="study_point", arguments={}, call_id=identifier)

    async def test_tool_then_matching_late_asr_cancels_its_own_task_and_collector(self):
        product = Harness()
        owner = product._capture_tool_task_owner(product.ws)
        task = product._start_raw_tool_call(self.call(), owner, response_id="function-response")
        await product.entered.wait()
        jobs = tuple(product._tool_tasks)
        self.assertEqual(len(jobs), 2)
        # Actual transport uses this on an unscoped completed transcript. Whether
        # it belongs to this tool cannot be recovered from that provider event.
        product.note_user_turn_started()
        await asyncio.gather(*jobs, return_exceptions=True)
        self.assertTrue(task.cancelled())
        self.assertEqual(product._tool_scope_generation, 2)
        self.assertEqual(product.outputs, [])

    async def test_mismatched_terminal_does_not_close_the_function_response_batch(self):
        product = Harness()
        owner = product._capture_tool_task_owner(product.ws)
        batch = product._open_raw_tool_batch(owner, "function-response")
        product.close_raw_tool_batch("terminal-other-response")
        self.assertFalse(batch.closed)
        product.close_raw_tool_batch("function-response")
        self.assertTrue(batch.closed)

    async def test_unannounced_response_can_collect_without_matching_terminal(self):
        product = Harness()
        owner = product._capture_tool_task_owner(product.ws)
        batch = product._open_raw_tool_batch(owner, "function-response")
        async def result(): return ToolResult("call-one", "study_point", {"ok": True})
        completed = asyncio.create_task(result())
        await completed
        product._register_tool_batch_entry(batch, self.call(), owner, completed)
        product.close_raw_tool_batch("terminal-other-response")
        self.assertFalse(batch.closed)
        self.assertFalse(product._raw_tool_batch_response_is_open(batch))
        collected = await asyncio.wait_for(product._collect_tool_batch(batch, owner), timeout=.2)
        self.assertEqual(len(collected), 1)
        # This route's no-announcement fallback seals the batch; a mismatched
        # terminal alone is therefore not proof of an indefinite collector stall.
        self.assertTrue(batch.sealed)

    async def test_current_scope_result_succeeds_but_old_connection_never_becomes_current(self):
        product = Harness()
        owner = product._capture_tool_task_owner(product.ws)
        task = product._start_raw_tool_call(self.call(), owner, response_id="function-response")
        await product.entered.wait()
        jobs = tuple(product._tool_tasks)
        product.release.set()
        await asyncio.gather(*jobs)
        self.assertFalse(task.cancelled())
        self.assertEqual(len(product.outputs), 1)
        product._connection_generation = 2
        product.ws = object()
        self.assertFalse(product._tool_task_owner_is_current(owner))
        self.assertFalse(product._tool_task_connection_is_current(owner))
        product.note_user_turn_started()
        self.assertFalse(product._tool_task_owner_is_current(owner))


if __name__ == "__main__": unittest.main(verbosity=2)
