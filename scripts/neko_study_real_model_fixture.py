"""Study Companion teaching loop driven by a real, authorized chat model.

Run with the project-local venv:
  .tmp-uv-cache/neko-study-venv/Scripts/python.exe -I -B scripts/neko_study_real_model_fixture.py --probe
  .tmp-uv-cache/neko-study-venv/Scripts/python.exe -I -B scripts/neko_study_real_model_fixture.py

Everything else in this file reuses the isolated Study Companion runtime:
the same guards, the same extracted ``StudyCompanionPlugin``, the same SQLite
fixture store, and the same genuine teaching entrypoints as the deterministic
double. The only added capability is one auditable network exception: outbound
TLS to a single provider hostname, plus an OpenAI-compatible transport that
satisfies the host ``utils.llm_client`` contract the plugin's own
``StudyModelGateway`` already expects.

The API key is read before the filesystem guard is installed, is never printed,
and is checked against the emitted evidence.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib
import importlib.util
import json
import logging
from pathlib import Path
import ssl
import sys
import time
import traceback
import types
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import neko_study_plugin_methods_fixture as core  # noqa: E402

EVIDENCE_ROOT = ROOT / "benchmarks" / "raw" / "evidence"
PROVIDERS_SOURCE = ROOT / "candidates" / "N.E.K.O" / "config" / "providers.py"

DEFAULT_KEY_FILE = Path(r"D:\CODE\API\new api.txt")
DEFAULT_BASE_URL = "https://api.deepseek.com/v1"
DEFAULT_MODEL = "deepseek-flash"

MODEL_CALLS: list[dict[str, object]] = []
FACTORY_CALLS: list[dict[str, object]] = []
LAST_LIFECYCLE: dict[str, object] = {}
PENDING_MARKERS: list[str] = []
AGENT_LOGS: list[str] = []
KEY_MATERIAL = ""
# ``host`` sends exactly the dialect N.E.K.O's provider table resolves for this
# model; the other two values measure the thinking/latency tradeoff explicitly.
THINKING_MODE = "host"


def read_credential(key_file: Path) -> str:
    """Return the sk- credential the user left locally, before guards exist."""
    text = key_file.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        candidate = line.strip()
        if candidate.startswith("sk-") and len(candidate) > 20:
            return candidate
    raise RuntimeError("no local chat-model credential found")


def _load_extra_body(model: str) -> dict[str, object]:
    """Reuse N.E.K.O's own provider dialect table instead of inventing one."""
    name = "neko_providers_for_fixture"
    try:
        spec = importlib.util.spec_from_file_location(name, PROVIDERS_SOURCE)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return dict(module.get_extra_body(model) or {})
    except Exception:
        return {}


class ProviderHTTPError(RuntimeError):
    def __init__(self, message: str, *, status_code: int, request_id: str, body: object):
        super().__init__(message)
        self.status_code = status_code
        self.request_id = request_id
        self.body = body if isinstance(body, dict) else None


class StudyChatResponse:
    __slots__ = ("content", "response_metadata")

    def __init__(self, content: str, response_metadata: dict[str, object]) -> None:
        self.content = content
        self.response_metadata = response_metadata


class StudyChatClient:
    """Minimal OpenAI-compatible transport behind the host client contract."""

    def __init__(self, *, model: str, base_url: str, api_key: str, provider_type: str,
                 max_completion_tokens: int, timeout: float) -> None:
        parsed = urllib.parse.urlsplit(base_url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise RuntimeError("provider base_url must be https")
        self.model = model
        self.host = parsed.hostname
        self.endpoint = base_url.rstrip("/") + "/chat/completions"
        self.api_key = api_key
        self.max_completion_tokens = int(max_completion_tokens or 2048)
        self.timeout = float(timeout or 60.0)
        self.extra_body = _load_extra_body(model)
        if THINKING_MODE == "enabled":
            self.extra_body = {"thinking": {"type": "enabled"}}
        elif THINKING_MODE == "disabled":
            self.extra_body = {"thinking": {"type": "disabled"}}
        self.context = ssl.create_default_context()

    def _post(self, payload: dict[str, object]) -> tuple[dict[str, object], str, int]:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            self.endpoint,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            urllib.request.HTTPSHandler(context=self.context),
        )
        try:
            with opener.open(request, timeout=self.timeout) as response:
                raw = response.read()
                request_id = str(
                    response.headers.get("x-request-id")
                    or response.headers.get("request-id")
                    or ""
                )
                status = int(getattr(response, "status", 200) or 200)
        except urllib.error.HTTPError as exc:
            raw = exc.read()[:4000]
            request_id = str(exc.headers.get("x-request-id") or "")
            try:
                detail = json.loads(raw.decode("utf-8", "replace"))
            except Exception:
                detail = None
            raise ProviderHTTPError(
                f"provider returned http {exc.code}",
                status_code=int(exc.code),
                request_id=request_id,
                body=detail,
            ) from exc
        return json.loads(raw.decode("utf-8", "replace")), request_id, status

    async def ainvoke(self, messages: list[dict[str, object]]) -> StudyChatResponse:
        payload: dict[str, object] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "max_completion_tokens": self.max_completion_tokens,
        }
        payload.update(self.extra_body)
        started = time.perf_counter()
        record: dict[str, object] = {
            "model": self.model,
            "host": self.host,
            "endpoint_transport": "openai_compatible",
            "extra_body": dict(self.extra_body),
            "requested_max_output_tokens": self.max_completion_tokens,
            "message_count": len(messages),
            "status": "preparing",
            "started_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        # Append before anything can fail so a broken request is still visible.
        MODEL_CALLS.append(record)
        try:
            serialized = json.dumps(messages, ensure_ascii=False, sort_keys=True)
            # Providers receive JSON-escaped text, so match markers against a
            # whitespace- and escape-insensitive view of the same prompt.
            comparable = "".join(serialized.replace("\\", "").split())
            record.update(
                {
                    "roles": [str(item.get("role") or "") for item in messages],
                    # Which internal operation a call belongs to is only visible
                    # from its prompt, so keep a short head per message block.
                    "message_heads": [
                        f"{item.get('role')}: "
                        + "".join(
                            str(block.get("text", block) if isinstance(block, dict) else block).split()
                        )[:140]
                        for item in messages
                        for block in (
                            item.get("content")
                            if isinstance(item.get("content"), list)
                            else [item.get("content")]
                        )
                    ],
                    "prompt_chars": len(serialized),
                    "prompt_sha256": hashlib.sha256(serialized.encode("utf-8")).hexdigest(),
                    "context_flags": {
                        marker: {
                            "raw": marker in serialized,
                            "carried": "".join(marker.replace("\\", "").split()) in comparable,
                        }
                        for marker in PENDING_MARKERS
                    },
                }
            )
        except Exception as exc:
            record.update({
                "status": "prompt_recording_failed",
                "error_type": type(exc).__name__,
                "error": str(exc)[:240],
            })
            raise
        status = 0
        try:
            body, request_id, status = await asyncio.to_thread(self._post, payload)
        except Exception as exc:
            record.update(
                {
                    "status": "error",
                    "http_status": getattr(exc, "status_code", 0),
                    "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                    "error_type": type(exc).__name__,
                    "request_id": getattr(exc, "request_id", ""),
                }
            )
            raise
        choices = list(body.get("choices") or [])
        choice = dict(choices[0]) if choices else {}
        message = dict(choice.get("message") or {})
        content = message.get("content")
        if not isinstance(content, str):
            content = str(content or "")
        usage = dict(body.get("usage") or {})
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        record.update(
            {
                "status": "ok",
                "http_status": status,
                "latency_ms": latency_ms,
                "request_id": request_id,
                "finish_reason": str(choice.get("finish_reason") or ""),
                "input_tokens": int(usage.get("prompt_tokens") or 0),
                "output_tokens": int(usage.get("completion_tokens") or 0),
                "reasoning_tokens": int(
                    (usage.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0
                ),
                "returned_model": str(body.get("model") or ""),
                "answer_chars": len(content),
            }
        )
        metadata = {
            "token_usage": usage,
            "finish_reason": str(choice.get("finish_reason") or ""),
            "model_name": str(body.get("model") or self.model),
            "request_id": request_id,
        }
        return StudyChatResponse(content, metadata)

    async def aclose(self) -> None:
        return None


async def create_chat_llm_async(*, model: str = "", base_url: str = "", api_key: str = "",
                               provider_type: str = "openai_compatible", max_retries: int = 0,
                               max_completion_tokens: int | None = None,
                               timeout: float | None = None, **_: object) -> StudyChatClient:
    FACTORY_CALLS.append({
        "model": model,
        "provider_type": provider_type,
        "max_retries": max_retries,
        "max_completion_tokens": max_completion_tokens,
        "timeout": timeout,
        "extra_kwargs": sorted(str(key) for key in _),
    })
    try:
        if int(max_retries or 0) != 0:
            raise RuntimeError("fixture transport performs no retries")
        return StudyChatClient(
            model=model,
            base_url=base_url,
            api_key=api_key,
            provider_type=provider_type,
            max_completion_tokens=int(max_completion_tokens or 2048),
            timeout=float(timeout or 60.0),
        )
    except Exception as exc:
        MODEL_CALLS.append({
            "status": "client_construction_failed",
            "model": model,
            "host": urllib.parse.urlsplit(base_url).hostname,
            "error_type": type(exc).__name__,
            "error": str(exc)[:300],
            "traceback": "".join(traceback.format_exception(exc)[-4:])[:900],
            "input_tokens": 0,
            "output_tokens": 0,
            "reasoning_tokens": 0,
            "latency_ms": 0,
            "answer_chars": 0,
        })
        raise


class AgentLogCapture(logging.Handler):
    """Keep the agent's own degradation warning so a failure stays diagnosable."""

    def emit(self, record: logging.LogRecord) -> None:
        message = str(record.msg)
        args = record.args
        if args:
            values = list(args) if isinstance(args, tuple) else [args]
            try:
                message = message.format(*[str(value) for value in values])
            except Exception:
                message = f"{message} {values}"
        AGENT_LOGS.append(f"{record.levelname} {message}"[:400])


class RealConfigManager:
    """Stand-in for the host config manager with one real model group."""

    def __init__(self, api_config: dict[str, str]) -> None:
        self._api_config = dict(api_config)
        # Host path services the plugin uses to resolve runtime install
        # locations. Pointed into the fixture's ignored temp tree, never at the
        # user's real documents directory.
        self.app_docs_dir = Path(core.TEMP_ROOT) / "app-docs"
        self.app_docs_dir.mkdir(parents=True, exist_ok=True)

    def get_core_config(self, *_a, **_k) -> dict[str, object]:
        return {}

    def get_config(self, *_a, **_k) -> dict[str, object]:
        return {}

    def get_model_api_config(self, model_type: str = "", *_a, **_k) -> dict[str, str]:
        if str(model_type or "").lower() in {"agent", "vision"}:
            return dict(self._api_config)
        return {}

    def consume_agent_daily_quota(self, *_a, **_k) -> tuple[bool, dict[str, object]]:
        return True, {}

    def reserve_agent_daily_quota(self, *_a, **_k) -> tuple[int, dict[str, object]]:
        return 2, {}


def install_real_runtime(*, model: str, base_url: str, api_key: str) -> dict[str, object]:
    """Swap the fixture's offline provider seams for the authorized real ones."""
    host = str(urllib.parse.urlsplit(base_url).hostname or "")
    if not host:
        raise RuntimeError("provider host could not be resolved")
    core.NETWORK_ALLOW_HOSTS.add(host)

    config_manager = sys.modules["utils.config_manager"]
    api_config = {
        "model": model,
        "base_url": base_url,
        "api_key": api_key,
        "provider_type": "openai_compatible",
    }
    manager = RealConfigManager(api_config)
    config_manager.get_config_manager = lambda: manager

    llm_client = types.ModuleType("utils.llm_client")
    llm_client.create_chat_llm_async = create_chat_llm_async
    llm_client.create_chat_llm = create_chat_llm_async
    sys.modules["utils.llm_client"] = llm_client
    import utils

    utils.llm_client = llm_client
    return {"provider_host": host, "model": model, "transport": "openai_compatible",
            "thinking_mode": THINKING_MODE}


async def _call(plugin, method: str, *, label: str, markers: list[str], **kwargs):
    global PENDING_MARKERS
    PENDING_MARKERS = [marker for marker in markers if marker]
    before = len(MODEL_CALLS)
    started = time.perf_counter()
    try:
        result = await getattr(plugin, method)(**kwargs)
    finally:
        PENDING_MARKERS = []
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    payload = core._result_payload(result)
    calls = [
        dict(call, call_index=index)
        for index, call in enumerate(MODEL_CALLS[before:], start=before + 1)
    ]
    return {
        "label": label,
        "method": method,
        "entrypoint_ms": elapsed_ms,
        "result_type": type(result).__name__,
        "degraded": bool(payload.get("degraded")),
        "diagnostic": str(payload.get("diagnostic") or ""),
        "payload": payload,
        "model_calls": calls,
    }


def allow_dependency_probes(names: tuple[str, ...] = ("dxcam", "mss")) -> list[str]:
    """Answer capture/audio dependency probes as "absent", like this environment is.

    ``_refresh_dependency_status()`` uses ``importlib.util.find_spec`` to report
    what the host can capture. The fail-closed import guard raises instead of
    returning None, which aborts ``startup()``. Returning None is the truthful
    answer here and still blocks the import itself.
    """
    blocker = next(
        (finder for finder in sys.meta_path if type(finder).__name__ == "ImportBlocker"),
        None,
    )
    if blocker is None:
        raise RuntimeError("existing fail-closed import guard was not installed")
    original = blocker.find_spec
    probed: list[str] = []

    def find_spec(fullname, path=None, target=None):
        if fullname in names:
            probed.append(fullname)
            return None
        return original(fullname, path, target)

    blocker.find_spec = find_spec
    return probed


async def bootstrap_live_plugin(
    *, model: str, base_url: str, api_key: str
) -> tuple[object, dict[str, object]]:
    """Install the real provider seams, then run the plugin's genuine lifecycle."""
    install_info = install_real_runtime(model=model, base_url=base_url, api_key=api_key)
    probed = allow_dependency_probes()
    _plugin_module, plugin, gates = await core.bootstrap_plugin()
    # The lifecycle swallows its own exception into a warning log, so listen
    # before startup() runs.
    plugin.logger.addHandler(AgentLogCapture(level=logging.WARNING))

    startup_result = await plugin.startup()
    payload = core._result_payload(startup_result)
    lifecycle: dict[str, object] = {
        "startup_result_type": type(startup_result).__name__,
        "startup_status": str(payload.get("status") or ""),
        "agent_from_startup": plugin._agent is not None,
        "knowledge_tracker_from_startup": getattr(plugin, "_knowledge_tracker", None) is not None,
        "capture_dependency_probes_answered_absent": probed,
        "offline_gate_stimulus": gates,
        "provider": install_info,
    }
    if plugin._agent is None or getattr(plugin, "_knowledge_tracker", None) is None:
        # Documented fallback: the isolated context still refuses some host
        # service. Build the same production agent so teaching can proceed,
        # and say plainly that the lifecycle was not completed.
        from plugins.study_companion.tutor_llm_agent import TutorLLMAgent

        plugin._agent = TutorLLMAgent(logger=plugin.logger, config=plugin._cfg)
        plugin._assert_notebook_agent_methods(plugin._agent)
        lifecycle["fallback"] = (
            "startup() did not yield an agent/tracker; built the genuine "
            "TutorLLMAgent instead. SafeContext refusals: "
            + json.dumps({key: value for key, value in core.COUNTS.items() if "blocked" in key})
        )
    lifecycle["language"] = getattr(plugin._cfg, "language", None)
    lifecycle["active_mode"] = getattr(plugin._state, "active_mode", None)
    lifecycle["llm_call_timeout_seconds"] = getattr(plugin._cfg, "llm_call_timeout_seconds", None)
    lifecycle["awareness_enabled"] = getattr(
        getattr(plugin._cfg, "awareness", None), "enabled", None
    )
    lifecycle["communication_silent_mode"] = getattr(
        getattr(plugin._cfg, "communication", None), "silent_mode", None
    )
    lifecycle["event_bus_present"] = getattr(plugin, "_event_bus", None) is not None
    globals()["LAST_LIFECYCLE"] = lifecycle
    return plugin, lifecycle


def _digest(text: str, limit: int = 900) -> str:
    clean = str(text or "").strip()
    return clean if len(clean) <= limit else clean[:limit] + f"...[+{len(clean) - limit} chars]"


def _reply_of(turn: dict[str, object]) -> str:
    payload = turn["payload"]
    return str(payload.get("reply") or payload.get("summary") or "")


async def run_case(plugin, *, case_id: str, lesson: str, followups: list[str],
                   topic: str, weak_answer: str, ocr_ms: float | None) -> dict[str, object]:
    session = core._result_payload(await plugin.study_start_session())
    session_id = str(session.get("session_id") or "")
    steps: list[dict[str, object]] = []

    first = await _call(plugin, "study_explain_text", label="explain_initial",
                        markers=[_digest(lesson, 70)],
                        text=lesson, session_id=session_id)
    steps.append(first)
    reply = _reply_of(first)
    marker_pool = [_digest(reply, 70)]
    for index, question in enumerate(followups, start=1):
        turn = await _call(plugin, "study_explain_text", label=f"explain_followup_{index}",
                           markers=list(marker_pool), text=question, session_id=session_id)
        steps.append(turn)
        marker_pool.append(_digest(_reply_of(turn), 70))

    asked = await _call(plugin, "study_generate_question", label="generate_question",
                        markers=list(marker_pool), text=lesson, topic=topic, session_id=session_id)
    steps.append(asked)
    question = str(asked["payload"].get("question") or "")
    expected = str(asked["payload"].get("answer") or "")
    question_id = str(asked["payload"].get("question_id") or "")
    attempt_id = str(asked["payload"].get("attempt_id") or "")
    resolved_topic = str(asked["payload"].get("topic") or topic)

    mastery_before = await asyncio.to_thread(plugin._knowledge_tracker.get_mastery, resolved_topic)
    graded = await _call(plugin, "study_evaluate_answer", label="evaluate_answer",
                         markers=[_digest(question, 70)] if question else [],
                         answer=weak_answer, question=question, expected_answer=expected,
                         question_id=question_id, attempt_id=attempt_id,
                         selected_topic_id=resolved_topic, session_id=session_id)
    steps.append(graded)
    mastery_after = await asyncio.to_thread(plugin._knowledge_tracker.get_mastery, resolved_topic)
    feedback = _digest(_reply_of(graded), 70)

    reused = await _call(plugin, "study_explain_text", label="explain_after_error",
                         markers=[marker for marker in (feedback,) if marker],
                         text="结合我刚才这道题答错的地方，再针对最薄弱的这一步讲清楚一次。",
                         session_id=session_id)
    steps.append(reused)

    # A second attempt with the reference answer, to see whether grading credits
    # it and whether the learning state actually moves.
    retry_ask = await _call(plugin, "study_generate_question", label="generate_second_question",
                            markers=[feedback], text=lesson, topic=resolved_topic,
                            session_id=session_id)
    steps.append(retry_ask)
    second_question = str(retry_ask["payload"].get("question") or "")
    second_expected = str(retry_ask["payload"].get("answer") or "")
    graded_retry = await _call(
        plugin, "study_evaluate_answer", label="evaluate_reference_answer",
        markers=[_digest(second_question, 70)],
        answer=second_expected, question=second_question, expected_answer=second_expected,
        question_id=str(retry_ask["payload"].get("question_id") or ""),
        attempt_id=str(retry_ask["payload"].get("attempt_id") or ""),
        selected_topic_id=str(retry_ask["payload"].get("topic") or resolved_topic),
        session_id=session_id,
    )
    steps.append(graded_retry)
    mastery_after_correct = await asyncio.to_thread(
        plugin._knowledge_tracker.get_mastery,
        str(retry_ask["payload"].get("topic") or resolved_topic),
    )

    summary = await _call(plugin, "study_summarize_session", label="summarize_session",
                          markers=[marker for marker in (feedback,) if marker],
                          focus="", session_id=session_id)
    steps.append(summary)

    persisted = core._result_payload(await plugin.study_get_session(session_id=session_id))
    interactions = list(persisted.get("interactions") or [])

    return {
        "case_id": case_id,
        "session_id": session_id,
        "ocr_ms": ocr_ms,
        "topic": resolved_topic,
        "generated_question": question,
        "generated_expected_answer": expected,
        "submitted_weak_answer": weak_answer,
        "evaluation": {
            "verdict": graded["payload"].get("verdict"),
            "score": graded["payload"].get("score"),
            "error_type": graded["payload"].get("error_type"),
            "weak_points": graded["payload"].get("weak_points"),
            "feedback": _reply_of(graded),
            "degraded": graded["degraded"],
            "diagnostic": graded["diagnostic"],
        },
        "mastery": {
            "before_evaluation": mastery_before,
            "after_wrong_answer": mastery_after,
            "after_reference_answer": mastery_after_correct,
        },
        "second_question": second_question,
        "reference_answer_evaluation": {
            "verdict": graded_retry["payload"].get("verdict"),
            "score": graded_retry["payload"].get("score"),
            "error_type": graded_retry["payload"].get("error_type"),
            "feedback": _reply_of(graded_retry),
            "degraded": graded_retry["degraded"],
            "diagnostic": graded_retry["diagnostic"],
        },
        "persisted_interaction_count": len(interactions),
        "persisted_interaction_kinds": [str(row.get("kind") or row.get("type") or "") for row in interactions],
        "session_summary": _reply_of(summary),
        "turns": [
            {
                "label": step["label"],
                "entrypoint_ms": step["entrypoint_ms"],
                "degraded": step["degraded"],
                "diagnostic": step["diagnostic"],
                "reply": _digest(_reply_of(step)),
                "model_calls": step["model_calls"],
                "payload_keys": sorted(str(key) for key in step["payload"]),
            }
            for step in steps
        ],
    }


async def probe_only(api_config: dict[str, str]) -> dict[str, object]:
    client = await create_chat_llm_async(
        model=api_config["model"], base_url=api_config["base_url"],
        api_key=api_config["api_key"], provider_type=api_config["provider_type"],
        max_retries=0, max_completion_tokens=16, timeout=30.0,
    )
    response = await client.ainvoke(
        [{"role": "user", "content": "Reply with exactly: OK"}]
    )
    return {
        "status": "PROBE_OK",
        "content": response.content[:80],
        "finish_reason": response.response_metadata.get("finish_reason"),
        "model_call": MODEL_CALLS[-1] if MODEL_CALLS else {},
    }


async def run(args, api_key: str) -> dict[str, object]:
    api_config = {
        "model": args.model,
        "base_url": args.base_url,
        "api_key": api_key,
        "provider_type": "openai_compatible",
    }

    if args.probe:
        core.NETWORK_ALLOW_HOSTS.add(str(urllib.parse.urlsplit(args.base_url).hostname or ""))
        try:
            return await probe_only(api_config)
        except Exception as exc:
            return {
                "status": "PROBE_FAILED",
                "error_type": type(exc).__name__,
                "http_status": getattr(exc, "status_code", 0),
                "request_id": getattr(exc, "request_id", ""),
                "provider_message": _digest(str(getattr(exc, "body", "") or exc), 300),
            }

    install_info = install_real_runtime(
        model=args.model, base_url=args.base_url, api_key=api_key
    )

    plugin, lifecycle = await bootstrap_live_plugin(
        model=args.model, base_url=args.base_url, api_key=api_key
    )
    runtime = await plugin._agent.describe_model_runtimes()
    import plugins.study_companion.study_model_gateway as gateway_module

    transport_wired = {
        "gateway_factory_is_fixture": gateway_module.create_chat_llm_async is create_chat_llm_async,
        "gateway_factory_module": getattr(gateway_module.create_chat_llm_async, "__module__", "?"),
        "llm_client_sys_module": str(sys.modules.get("utils.llm_client")),
    }
    mode = core._result_payload(await plugin.study_set_mode(mode="teaching", reason="fixture"))

    ocr_evidence: dict[str, object] = {}
    math_lesson = ""
    if args.with_ocr:
        import neko_study_synthetic_ocr_fixture as ocr_fixture

        ocr_fixture._install_ocr_runtime_guards()
        image_path = core.TEMP_ROOT / f"real-run-{uuid.uuid4().hex}.png"
        image = ocr_fixture._synthetic_image(image_path)
        plugin._ocr_pipeline = ocr_fixture._build_ocr_pipeline()
        ocr_entries = importlib.import_module("plugins.study_companion.entry_ocr_entries")
        capture_calls = 0

        async def synthetic_capture(**_kwargs):
            nonlocal capture_calls
            capture_calls += 1
            return types.SimpleNamespace(image=image.copy(), canceled=False)

        ocr_entries.capture_interactive_region = synthetic_capture
        started = time.perf_counter()
        ocr_result = await plugin.study_ocr_snapshot(
            capture_mode="interactive", allow_fullscreen_fallback=False
        )
        ocr_ms = round((time.perf_counter() - started) * 1000, 2)
        ocr_payload = core._result_payload(ocr_result)
        math_lesson = str(ocr_payload.get("text") or "")
        ocr_evidence = {
            "entrypoint": "study_ocr_snapshot(interactive)",
            "capture_calls": capture_calls,
            "ocr_ms": ocr_ms,
            "text": _digest(math_lesson, 500),
            "image_sha256": hashlib.sha256(image_path.read_bytes()).hexdigest(),
            "state_matches": str(plugin._state.last_ocr_text or "") == math_lesson,
        }
        if not math_lesson or type(ocr_result).__name__ == "Err":
            raise RuntimeError("synthetic OCR did not return lesson text")

    followups_math = [
        "为什么这里会出现 1/2 这个系数？直接把 e^(x^2) 积分不行吗？",
        "为什么要令 u=x^2，而不是令 u=x 或 u=e^(x^2)？",
        "如果把题目换成 ∫x²·e^(x²)dx，同样的代换还成立吗？为什么？",
    ]
    asyncio_lesson = (
        "阅读这段 Python 代码，先说明它的实际执行顺序和总耗时，再解释原因：\n"
        "```python\n"
        "import asyncio\n\n"
        "async def bake(name, secs):\n"
        '    print("start", name)\n'
        "    await asyncio.sleep(secs)\n"
        '    print("done", name)\n'
        "    return name\n\n"
        "async def main():\n"
        '    await bake("bread", 2)\n'
        '    await bake("cake", 3)\n\n'
        'asyncio.run(main())\n'
        "```"
    )
    followups_asyncio = [
        "如果我把两个 bake 改成 asyncio.gather(bake(...), bake(...))，输出顺序和总时间会变成什么？",
        "把 await asyncio.sleep(secs) 换成 time.sleep(secs) 会怎样？请具体说输出会怎么变。",
        "这里真的并发吗？asyncio 的多任务和我们平时说的多线程/多进程有什么本质区别？",
    ]

    cases = []
    specs = [
        dict(
            case_id="math_u_substitution_from_ocr" if args.with_ocr else "math_u_substitution_from_text",
            lesson=math_lesson if args.with_ocr else
            "例题2：计算 ∫x·e^(x^2) dx。令 u=x^2，则 du=2x dx，所以 x dx=du/2。",
            followups=followups_math, topic="u-substitution",
            weak_answer="令 u=x^2，那么 du=x dx，所以 ∫x·e^(x^2)dx = e^(x^2)+C。",
            ocr_ms=float(ocr_evidence.get("ocr_ms") or 0.0) if args.with_ocr else None,
        ),
        dict(
            case_id="python_asyncio", lesson=asyncio_lesson, followups=followups_asyncio,
            topic="python-asyncio",
            weak_answer="两个 bake 会同时开始，总耗时大约 3 秒，因为 asyncio 是多线程并行的。",
            ocr_ms=None,
        ),
    ]
    for spec in specs:
        try:
            cases.append(await run_case(plugin, **spec))
        except Exception as exc:
            # Keep the other case's paid real calls instead of losing the run.
            cases.append({
                "case_id": spec["case_id"],
                "case_error": f"{type(exc).__name__}: {_digest(str(exc), 300)}",
                "turns": [],
                "topic": spec["topic"],
                "evaluation": {},
                "mastery": {},
            })

    totals = [
        call
        for case in cases
        for turn in case["turns"]
        for call in turn["model_calls"]
    ]
    return {
        "status": "REAL_MODEL_TEACHING_RUN",
        "plugin_fingerprint": hashlib.sha256(
            (core.RELEASE / "plugins" / "study_companion" / "__init__.py").read_bytes()
        ).hexdigest(),
        "runtime": lifecycle["provider"],
        "lifecycle": lifecycle,
        "transport_wired": transport_wired,
        "factory_calls": FACTORY_CALLS[:6],
        "resolved_model_runtimes": runtime,
        "mode_switch": {key: mode.get(key) for key in ("active_mode", "previous_mode", "changed")},
        "ocr": ocr_evidence,
        "agent_logs": AGENT_LOGS[-24:],
        "cases": cases,
        "totals": {
            "model_calls": len(totals),
            "failed_model_calls": sum(1 for call in totals if call.get("status") != "ok"),
            "degraded_entries": sum(
                1 for case in cases for turn in case["turns"] if turn["degraded"]
            ),
            "input_tokens": sum(int(call.get("input_tokens") or 0) for call in totals),
            "output_tokens": sum(int(call.get("output_tokens") or 0) for call in totals),
            "reasoning_tokens": sum(int(call.get("reasoning_tokens") or 0) for call in totals),
            "model_call_ms_max": max((float(call.get("latency_ms") or 0) for call in totals), default=0.0),
            "model_call_ms_median": (
                sorted(float(call.get("latency_ms") or 0) for call in totals)[len(totals) // 2]
                if totals else 0.0
            ),
            "answer_chars_total": sum(int(call.get("answer_chars") or 0) for call in totals),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--key-file", default=str(DEFAULT_KEY_FILE))
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--probe", action="store_true", help="one 16-token request, no plugin")
    parser.add_argument("--no-ocr", dest="with_ocr", action="store_false",
                        help="feed the math lesson as text instead of synthetic screen OCR")
    parser.add_argument("--thinking", choices=("host", "enabled", "disabled"), default="host",
                        help="thinking dialect sent to the provider (host = N.E.K.O provider table)")
    args = parser.parse_args()

    globals()["THINKING_MODE"] = args.thinking

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    # Read the local credential before the filesystem guard exists, so no
    # out-of-root read is performed (or faked) inside the guarded runtime.
    api_key = read_credential(Path(args.key_file))
    globals()["KEY_MATERIAL"] = api_key
    loop = asyncio.new_event_loop()
    core._install_guards()
    try:
        result = loop.run_until_complete(run(args, api_key))
    except BaseException as exc:
        result = {
            "status": "REAL_MODEL_RUN_FAILED",
            "error_type": type(exc).__name__,
            "error": _digest(str(exc), 400),
            "agent_logs": AGENT_LOGS[-12:],
            "plugin_instance_created": core.PLUGIN_INSTANCE_CREATED,
        }
    finally:
        loop.close()

    serialized = json.dumps(result, sort_keys=True, ensure_ascii=False)
    if KEY_MATERIAL and KEY_MATERIAL in serialized:
        raise RuntimeError("refusing to write evidence containing the credential")
    result["guards"] = dict(core.COUNTS)
    result["run_utc"] = datetime.now(timezone.utc).isoformat()

    if args.probe:
        print(json.dumps(result, sort_keys=True, ensure_ascii=False))
        return

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    # The fixture's write guard only allows evidence named neko-study-plugin-*.
    path = EVIDENCE_ROOT / f"neko-study-plugin-real-{stamp}.json"
    try:
        path.write_text(json.dumps(result, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
        result["proof_artifact"] = path.relative_to(ROOT).as_posix()
    except Exception as exc:
        result["proof_artifact"] = ""
        result["proof_write_error"] = f"{type(exc).__name__}: {exc}"
        print(json.dumps(result, sort_keys=True, ensure_ascii=False))
        return
    compact = {
        "status": result.get("status"),
        "totals": result.get("totals"),
        "runtime": result.get("runtime"),
        "resolved_model_runtimes": result.get("resolved_model_runtimes"),
        "guards": result.get("guards"),
        "error": result.get("error"),
        "agent_logs": result.get("agent_logs") or AGENT_LOGS[-8:],
        "proof_artifact": result.get("proof_artifact", ""),
    }
    print(json.dumps(compact, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
