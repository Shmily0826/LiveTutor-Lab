"""Share only an identical in-flight explanation for the same completed voice input.

Each provider call retains its own id, owner and response batch. No completed
answer cache or side-effecting quiz/grade/preference deduplication is introduced.
"""
from neko_native_barge_in_patch import _upgrade_targets

HELPER = '''    async def _execute_raw_study_call(self, call, owner):
        route = getattr(getattr(self, "_realtime_protocol_capabilities", None), "route_key", None)
        received = getattr(self, "_late_raw_transcript_at", 0.0)
        eligible = (call.name == "study_explain" and route == "lanlan_app_gemini"
                    and getattr(self, "_is_free_proxy", False)
                    and not getattr(self, "_has_server_vad", False)
                    and __import__("os").environ.get("NEKO_STUDY_SPEECH_GATE") == "1"
                    and received > 0 and received >= getattr(self, "_last_local_loud_time", 0.0)
                    and getattr(self, "_late_raw_transcript_ready_scope", None) == owner.scope_generation
                    and self._tool_task_owner_is_current(owner)
                    and not getattr(self, "_native_barge_in_pending", False)
                    and not getattr(self, "_fatal_error_occurred", False))
        if not eligible or not isinstance(call.arguments, dict):
            return await self._execute_tool_call(call)
        try:
            arguments = __import__("json").dumps(call.arguments, sort_keys=True, ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError):
            return await self._execute_tool_call(call)
        key = (owner.connection_generation, owner.scope_generation, received, call.name, arguments)
        registry = getattr(self, "_study_explanation_inflight", None)
        if registry is None:
            registry = self._study_explanation_inflight = {}
        existing = registry.get(key)
        if existing is not None and existing["provider_session"] is owner.provider_session:
            logger.info("study voice identical inflight explanation joined scope=%s", owner.scope_generation)
            # Cancelling a duplicate must not cancel the original explanation.
            result = await asyncio.shield(existing["future"])
            if not self._tool_task_owner_is_current(owner):
                return None
            return ToolResult(call_id=call.call_id, name=call.name,
                              output=__import__("copy").deepcopy(result.output),
                              is_error=result.is_error, error_message=result.error_message)
        if len(registry) >= 16:
            return await self._execute_tool_call(call)
        future = asyncio.get_running_loop().create_future()
        record = {"future": future, "provider_session": owner.provider_session}
        registry[key] = record
        try:
            result = await self._execute_tool_call(call)
            if not future.done():
                future.set_result(result)
            return result
        except asyncio.CancelledError:
            future.cancel()
            raise
        except Exception as error:
            if not future.done():
                future.set_exception(error)
                future.exception() # no unhandled future when there were no duplicates
            raise
        finally:
            # No finished-result cache: a later call must recheck current material.
            if registry.get(key) is record:
                registry.pop(key, None)

'''

_RUN = '''        async def _run() -> ToolResult | None:
            if not self._tool_task_owner_is_current(owner):
                self._log_stale_tool_drop("not_started", owner, [call])
                return None
            return await self._execute_tool_call(call)'''

UPGRADES = {'main_logic/omni_realtime_client/_tools.py': (
    (_RUN, _RUN.replace('self._execute_tool_call(call)', 'self._execute_raw_study_call(call, owner)')),
    ('    async def _execute_tool_call(self, call: ToolCall) -> ToolResult:\n',
     HELPER + '    async def _execute_tool_call(self, call: ToolCall) -> ToolResult:\n'),
)}

def upgrade_targets(targets):
    return _upgrade_targets(targets, UPGRADES, [])
