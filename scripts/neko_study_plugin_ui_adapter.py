"""Loopback-only adapter from the shipped Study UI /runs protocol to real plugin methods.

Run with the same project-local venv as neko_study_plugin_methods_fixture.py.
The UI page is served from the extracted resource bundle; all tutoring state
and SQLite writes stay in the fixture's ignored .tmp-uv-cache directory.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib
import io
import json
import mimetypes
import os
from pathlib import Path
import platform
import re
import sys
import subprocess
import threading
import time
import traceback
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from urllib.parse import unquote, urlparse
import uuid


ROOT = Path(__file__).resolve().parents[1]
STATIC_ROOT = ROOT / "benchmarks" / "raw" / "neko-app" / "resources" / "bin" / "plugins" / "study_companion" / "static"
PLUGIN_ROOT = STATIC_ROOT.parent
sys.path.insert(0, str(ROOT / "scripts"))
import neko_study_plugin_methods_fixture as core  # noqa: E402
import neko_study_real_model_fixture as real  # noqa: E402
import neko_study_synthetic_ocr_fixture as ocr_fixture  # noqa: E402


ALLOWED_ENTRYPOINTS = {
    "study_status",
    "study_set_mode",
    "study_ocr_snapshot",
    "study_get_practice_scope",
    "study_set_practice_scope",
    "study_question_context",
    "study_explain_text",
    "study_generate_targeted_question",
    "study_evaluate_answer",
    "study_summarize_session",
    "study_get_session",
    "study_get_settings_config",
    "study_memory_list_decks",
}
RUNS: dict[str, dict[str, object]] = {}
UI_EVENTS: list[dict[str, object]] = []
HTTP_DOWNSTREAM: dict[str, int] = {"external_fetch": 0, "websocket_upgrade": 0}
DENIED_ENTRY_IDS: list[str] = []
LOOP: asyncio.AbstractEventLoop | None = None
SERVER: ThreadingHTTPServer | None = None
SCOPE_TOPIC_ID = "fixture_u_substitution"
CORRELATION_ID = str(uuid.uuid4())
SYNTHETIC_SCREEN_IMAGE = None
SCREENSHOT_META: dict[str, object] = {}
OCR_EVIDENCE: dict[str, object] = {}
OCR_FAILURE_META: dict[str, object] = {}
OCR_CAPTURE_CALLS = 0
MASTERY_BEFORE = 0.0
# ``mock`` keeps the deterministic double and its exact accepted assertions.
# ``real`` drives the same shipped UI through the live provider.
MODEL_BACKEND = "mock"
REAL: object | None = None
MODEL_CALL_LOG: list[dict[str, object]] = []
PRIOR_MARKERS: list[str] = []
MODE_BANNER = "教学模式已开启"


def _scenario_rules() -> dict[str, object]:
    """Per-backend UI content rules, injected into the browser scenario."""
    if MODEL_BACKEND == "real":
        return {
            "backend": "real",
            "gradeStepName": "real_model_grade_visible",
            # A live model is not required to recite the previous question
            # verbatim; grounding is proven by the provider prompts and the
            # answers themselves, so only the subject matter is asserted here.
            "quotePreviousQuestion": False,
            "steps": {
                "explain_initial": [["1/2", "du/2", "二分之一"], ["x^2", "u=x^2"]],
                "followup_1": [["1/2", "du/2", "二分之一"], ["2x", "du", "微分"]],
                "followup_2": [["x^2", "u"], ["du", "微分", "导数", "differenti", "2x"]],
                "question": [["∫", "integral", "积分", "e^"], ["u", "du"]],
                "grade_regex": "(correct|partial|wrong|dont_know|正确|部分|错误|误|\\d{1,3})",
                "summary": [["summary", "总结", "highlights", "会话", "session"]],
            },
        }
    return {
        "backend": "mock",
        "gradeStepName": "mock_grade_visible",
        "quotePreviousQuestion": True,
        "steps": {
            "explain_initial": [["u=x^2"], ["1/2"]],
            "followup_1": [["例题2"], ["du=2x dx"], ["1/2"]],
            "followup_2": [["u=x^2"], ["du=2x dx"]],
            "question": [["x·e^(x^2)"], ["令 u"]],
            "grade_regex": "100",
            "summary": [["SQLite"]],
        },
    }


def _json_bytes(data: object) -> bytes:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _browser_gate_js() -> str:
    return r"""(() => {
      const counts = {audio_context_attempted:0,audio_context_blocked:0,speech_synthesis_attempted:0,speech_synthesis_blocked:0,media_play_attempted:0,media_play_blocked:0,microphone_attempted:0,microphone_blocked:0,websocket_attempted:0,websocket_blocked:0,external_fetch_attempted:0,external_fetch_blocked:0};
      const denied = (name) => Promise.reject(new DOMException('isolated Study UI blocked ' + name, 'NotAllowedError'));
      class BlockedAudioContext { constructor(){counts.audio_context_attempted++;counts.audio_context_blocked++;throw new Error('audio blocked by fixture');} }
      window.AudioContext=BlockedAudioContext; window.webkitAudioContext=BlockedAudioContext;
      if(window.speechSynthesis) window.speechSynthesis.speak=()=>{counts.speech_synthesis_attempted++;counts.speech_synthesis_blocked++;throw new Error('speech blocked by fixture');};
      if(typeof HTMLMediaElement!=='undefined') HTMLMediaElement.prototype.play=function(){counts.media_play_attempted++;counts.media_play_blocked++;return denied('media playback');};
      if(navigator.mediaDevices) navigator.mediaDevices.getUserMedia=()=>{counts.microphone_attempted++;counts.microphone_blocked++;return denied('microphone');};
      window.WebSocket=class {constructor(){counts.websocket_attempted++;counts.websocket_blocked++;throw new Error('websocket blocked by fixture');}};
      const realFetch=window.fetch.bind(window);
      const allowed=(url)=>url.origin===location.origin && (/^\/runs(?:\/|$)/.test(url.pathname) || url.pathname==='/__fixture-state' || /^\/plugin\/study_companion\/ui-api\/i18n\/[A-Za-z-]+\.json$/.test(url.pathname));
      window.fetch=(input,init)=>{const url=new URL(typeof input==='string'?input:input.url,location.href);if(!allowed(url)){counts.external_fetch_attempted++;counts.external_fetch_blocked++;return denied('non-fixture fetch');}return realFetch(input,init);};
      window.__nekoAudioGate=counts;
    })();"""


def _scenario_js() -> str:
    return r"""const RULES = __RULES_JSON__;
const norm = (value) => String(value || '').toLowerCase().replace(/[²]/g, '^2').replace(/\s+/g, '');
const hit = (value, groups) => (groups || []).every((group) => group.some((needle) => norm(value).includes(norm(needle))));
const RSTEP = (name) => (RULES.steps && RULES.steps[name]) || [];
await (async()=>{
      const events=[]; const sessionKey='neko-study-ocr-e2e';
      const persisted=JSON.parse(sessionStorage.getItem(sessionKey)||'{}');
      const runTrace=persisted.runTrace||[];
      const phaseTraceStart=runTrace.length;
      const mark=(step,entryId)=>{
        const selector=entryId==='study_generate_targeted_question'?'#questionText':entryId==='study_evaluate_answer'?'#evaluationStatus':entryId==='study_ocr_snapshot'?'#studyInput':'#replyText';
        const visible=!entryId||Boolean(document.querySelector(selector)?.checkVisibility())&&document.querySelector('#learningProfileModal')?.hidden!==false;
        if(!visible)throw new Error('result is obscured or hidden: '+step);
        events.push({step,at:new Date().toISOString(),run_id:entryId?latestRun(entryId):'',result_visible:visible,visible_reply:document.querySelector('#replyText')?.textContent||'',visible_question:document.querySelector('#questionText')?.textContent||'',visible_evaluation:document.querySelector('#evaluationStatus')?.textContent||''});
      };
      const waitFor=async(check,label)=>{const end=Date.now()+45000;while(Date.now()<end){if(check())return;await new Promise(r=>setTimeout(r,60));}throw new Error('UI step timed out: '+label);};
      const setText=(selector,value)=>{const el=document.querySelector(selector);if(!el)throw new Error('missing UI field '+selector);el.value=value;el.dispatchEvent(new Event('input',{bubbles:true}));};
      const latestRun=(entryId)=>{const hit=runTrace.filter(item=>item.entry_id===entryId).at(-1);return hit?.run_id||'';};
      const priorFetch=window.fetch.bind(window);
      window.fetch=async(input,init={})=>{
        const url=new URL(typeof input==='string'?input:input.url,location.href);
        const method=String(init.method||'GET').toUpperCase();
        let request=null; if(url.pathname==='/runs'&&method==='POST'){try{request=JSON.parse(init.body||'{}');}catch{}}
        const response=await priorFetch(input,init);
        if(request){const data=await response.clone().json().catch(()=>({}));if(data.run_id)runTrace.push({entry_id:String(request.entry_id||''),run_id:String(data.run_id),at:new Date().toISOString()});}
        return response;
      };
      const assertBlocked=async()=>{
        const g=window.__nekoAudioGate;
        try{new AudioContext();}catch{}
        try{window.speechSynthesis?.speak(new SpeechSynthesisUtterance('synthetic blocked audio'));}catch{}
        const media=document.createElement('audio');try{await media.play();}catch{}
        try{await navigator.mediaDevices?.getUserMedia({audio:true});}catch{}
        try{new WebSocket('ws://provider.invalid/audio');}catch{}
        try{await window.fetch('https://provider.invalid/tts');}catch{}
        if(!g||g.audio_context_blocked!==1||g.speech_synthesis_blocked!==1||g.media_play_blocked!==1||g.websocket_blocked!==1||g.external_fetch_blocked!==1)throw new Error('browser output gate failed');
        if(g.microphone_attempted&&g.microphone_blocked!==g.microphone_attempted)throw new Error('microphone guard failed');
        return {...g};
      };
      const state=async()=>{const response=await fetch('/__fixture-state');if(!response.ok)throw new Error('fixture state unavailable');return response.json();};
      const sendEvidence=async(value)=>{const response=await fetch('/__fixture-state',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(value)});if(!response.ok)throw new Error('UI evidence handoff failed');return response.json();};
      try{
        const browserGate=await assertBlocked(); mark('browser_output_gates_stimulated');
        const startState=await state();
        await waitFor(()=>document.querySelector('#studyInput')&&document.querySelector('#ocrBtn')&&runTrace.slice(phaseTraceStart).some(item=>item.entry_id==='study_question_context'),'study UI bootstrap completed');
        const setupModal=document.querySelector('#learningProfileModal');
        if(setupModal&&!setupModal.hidden)setupModal.querySelector('[data-stage="college"]').click();
        await waitFor(()=>document.querySelector('#learningProfileModal')?.hidden!==false,'learning stage selected through the shipped UI');
        mark('original_study_ui_ready');
        if(new URLSearchParams(location.search).get('scenario')==='reuse'){
          document.querySelector('#summarizeBtn').click();
          await waitFor(()=>hit(document.querySelector('#replyText')?.textContent,RSTEP('summary'))&&!document.querySelector('#summarizeBtn')?.disabled,'session reuse summary');
          mark('same_session_reused_after_reload','study_summarize_session');
          const after=await state();
          if(after.session_id!==persisted.session_id||after.correlation_id!==persisted.correlation_id)throw new Error('reload changed correlation or session');
          const evidence={events,browserGate,run_trace:runTrace,session_id:after.session_id,correlation_id:after.correlation_id,session_record_id_matches:after.session_record_id===after.session_id,interaction_session_ids_match:after.interaction_session_ids_match,interaction_count:after.interaction_count,mastery:after.mastery,mastery_before:Number(persisted.mastery_before||0)};
          const saved=await sendEvidence(evidence);
          document.querySelector('#replyText').setAttribute('data-fixture-complete',saved.proof||'true');
          return;
        }
        if(!startState.screenshot?.sha256||startState.screenshot.correlation_id!==startState.correlation_id)throw new Error('browser screenshot not loaded into the OCR fixture');
        if(RULES.backend==='real'){
          const teachingBtn=document.querySelector('#modeTeachingBtn');
          if(!teachingBtn)throw new Error('shipped teaching mode control is missing');
          teachingBtn.click();
          await waitFor(()=>runTrace.slice(phaseTraceStart).some(item=>item.entry_id==='study_set_mode'),'teaching mode switch sent');
          const modeState=await state();
          if(modeState.active_mode!=='teaching')throw new Error('teaching mode did not become active: '+modeState.active_mode);
          // The shipped control repaints its indicator shortly after the reply
          // arrives, so wait for it instead of judging the click instant.
          await waitFor(()=>teachingBtn.classList.contains('is-active')
            && /teach/i.test(String(document.querySelector('#modeSwitch')?.dataset?.active||'')),'shipped mode control shows teaching');
          const modeVisible=teachingBtn.checkVisibility()&&document.querySelector('#learningProfileModal')?.hidden!==false;
          if(!modeVisible)throw new Error('teaching mode control is obscured');
          events.push({step:'teaching_mode_selected',at:new Date().toISOString(),run_id:latestRun('study_set_mode'),result_visible:modeVisible,
            visible_reply:document.querySelector('#replyText')?.textContent||'',visible_question:'',
            visible_evaluation:String(document.querySelector('#statusLine')?.textContent||'').slice(0,200)});
        }
        const masteryBefore=Number(startState.mastery_before||0);
        const mode=document.querySelector('#ocrCaptureMode');if(mode){mode.value='interactive';mode.dispatchEvent(new Event('change',{bubbles:true}));}
        document.querySelector('#ocrBtn').click();
        await waitFor(()=>{const text=document.querySelector('#studyInput')?.value||'';return text.includes('Example 2')&&text.includes('du = 2x dx')&&text.includes('1/2')&&!document.querySelector('#ocrBtn')?.disabled;},'OCR button populated the lesson from browser screenshot');
        const afterOcr=await state();const ocr=afterOcr.ocr;
        if(!ocr||ocr.status!=='ok'||ocr.capture_mode!=='interactive'||!ocr.entrypoint_updated_state||ocr.session_id!==afterOcr.session_id||ocr.expected_token_recall!==1)throw new Error('normal OCR entrypoint proof did not match the UI text/session');
        const browserText=document.querySelector('#studyInput').value.trim();if(browserText!==ocr.text)throw new Error('visible input differs from genuine OCR text');
        mark('ocr_button_populated_from_headless_screenshot','study_ocr_snapshot');
        const followBox=document.querySelector('#usePreviousExplanation');if(followBox)followBox.checked=true;
        document.querySelector('#explainBtn').click();
        await waitFor(()=>{const t=document.querySelector('#replyText')?.textContent||'';return hit(t,RSTEP('explain_initial'))&&!document.querySelector('#explainBtn')?.disabled;},'OCR-grounded explanation');
        mark('ocr_grounded_explanation_visible','study_explain_text');
        const enabledFollowBox=document.querySelector('#usePreviousExplanation');if(enabledFollowBox&&!enabledFollowBox.disabled)enabledFollowBox.checked=true;
        setText('#studyInput','\u4e3a\u4ec0\u4e48\u4f8b\u98982\u67091/2\uff1f');document.querySelector('#explainBtn').click();
        await waitFor(()=>{const t=document.querySelector('#replyText')?.textContent||'';return hit(t,RSTEP('followup_1'))&&!document.querySelector('#explainBtn')?.disabled;},'contextual follow-up');
        mark('first_contextual_followup_visible','study_explain_text');
        const firstFollowup='\u4e3a\u4ec0\u4e48\u4f8b\u98982\u67091/2\uff1f';
        const enabledSecondFollowBox=document.querySelector('#usePreviousExplanation');if(enabledSecondFollowBox&&!enabledSecondFollowBox.disabled)enabledSecondFollowBox.checked=true;
        setText('#studyInput','\u4e3a\u4ec0\u4e48\u8981\u4ee4 u=x^2\uff1f');document.querySelector('#explainBtn').click();
        await waitFor(()=>{const t=document.querySelector('#replyText')?.textContent||'';return hit(t,RSTEP('followup_2'))&&(!RULES.quotePreviousQuestion||norm(t).includes(norm(firstFollowup)))&&!document.querySelector('#explainBtn')?.disabled;},'second contextual follow-up retained the previous question and example');
        mark('second_contextual_followup_visible','study_explain_text');
        document.querySelector('#generateQuestionBtn').click();
        await waitFor(()=>{const t=document.querySelector('#questionText')?.textContent||'';return hit(t,RSTEP('question'))&&!document.querySelector('#generateQuestionBtn')?.disabled;},'targeted question retained the u-substitution material');
        mark('question_visible','study_generate_targeted_question');
        setText('#answerInput','u=x^2, du=2x dx, so the integral is (1/2)e^(x^2)+C.');document.querySelector('#evaluateAnswerBtn').click();
        await waitFor(()=>new RegExp(RULES.steps.grade_regex).test(document.querySelector('#evaluationStatus')?.textContent||'')&&!document.querySelector('#evaluateAnswerBtn')?.disabled,'answer evaluation visible');
        mark(RULES.gradeStepName,'study_evaluate_answer');
        document.querySelector('#summarizeBtn').click();
        await waitFor(()=>hit(document.querySelector('#replyText')?.textContent,RSTEP('summary'))&&!document.querySelector('#summarizeBtn')?.disabled,'persisted session summary');
        mark('session_summary_visible','study_summarize_session');
        const current=await state();
        const savedState={runTrace,session_id:current.session_id,correlation_id:current.correlation_id,mastery_before:masteryBefore};
        sessionStorage.setItem(sessionKey,JSON.stringify(savedState));
        const evidence={events,browserGate,run_trace:runTrace,session_id:current.session_id,correlation_id:current.correlation_id,session_record_id_matches:current.session_record_id===current.session_id,interaction_session_ids_match:current.interaction_session_ids_match,interaction_count:current.interaction_count,mastery:current.mastery,mastery_before:masteryBefore};
        await sendEvidence(evidence);
        history.replaceState(null,'','/?scenario=reuse&locale=en');
        await new Promise(resolve=>{window.addEventListener('pagehide',resolve,{once:true});setTimeout(()=>location.reload(),150);});
      }catch(error){window.__nekoStudyUiError=String(error?.stack||error);const status=document.querySelector('#statusLine');if(status)status.textContent='Isolated fixture stopped';const reply=document.querySelector('#replyText');if(reply)reply.textContent=String(error?.message||error);console.error('Isolated Study UI fixture:',error);}
    })();"""

def _marker(text: object, limit: int = 40) -> str:
    return str(text or "").strip()[:limit]


def _real_lifecycle() -> dict[str, object]:
    return {} if REAL is None else dict(getattr(REAL, "LAST_LIFECYCLE", {}) or {})


def _record_model_calls(entry_id: str, run_id: str, calls_before: int, args: dict, value: object) -> None:
    """Attribute live provider calls to the UI action that triggered them."""
    if REAL is None:
        return
    REAL.PENDING_MARKERS = []
    calls = [
        dict(call, call_index=index)
        for index, call in enumerate(REAL.MODEL_CALLS[calls_before:], calls_before + 1)
    ]
    MODEL_CALL_LOG.append({
        "entry_id": entry_id,
        "run_id": run_id,
        "model_call_count": len(calls),
        "prompt_chars": [int(call.get("prompt_chars") or 0) for call in calls],
        "latency_ms": [call.get("latency_ms") for call in calls],
        "statuses": [str(call.get("status") or "") for call in calls],
        "input_tokens": [int(call.get("input_tokens") or 0) for call in calls],
        "output_tokens": [int(call.get("output_tokens") or 0) for call in calls],
        "context_flags": [call.get("context_flags") for call in calls],
        "message_heads": [call.get("message_heads") for call in calls],
    })
    if entry_id == "study_explain_text":
        reply = str((value or {}).get("reply") or "") if isinstance(value, dict) else ""
        if reply:
            PRIOR_MARKERS.append(_marker(reply))
        typed = _marker(args.get("text"))
        if typed:
            PRIOR_MARKERS.append(typed)
    if entry_id == "study_evaluate_answer" and isinstance(value, dict):
        # Lets the later summarize call prove whether the graded attempt was
        # actually in the prompt rather than only on screen.
        for field in ("answer", "question"):
            typed = _marker(args.get(field))
            if typed:
                PRIOR_MARKERS.append(typed)


async def _call_plugin(entry_id: str, args: dict[str, object], run_id: str) -> dict[str, object]:
    global OCR_CAPTURE_CALLS, OCR_EVIDENCE, OCR_FAILURE_META
    calls_before = len(REAL.MODEL_CALLS) if REAL is not None else 0
    if REAL is not None:
        REAL.PENDING_MARKERS = list(PRIOR_MARKERS)
    if entry_id not in ALLOWED_ENTRYPOINTS:
        raise ValueError("entrypoint is not allowlisted in this local fixture")
    plugin = core.PLUGIN_INSTANCE
    if plugin is None:
        raise RuntimeError("plugin fixture is not initialized")
    method = getattr(plugin, entry_id)
    payload = {k: v for k, v in args.items() if k != "locale"}
    if entry_id == "study_ocr_snapshot":
        if payload.get("capture_mode") != "interactive":
            OCR_FAILURE_META = {"stage": "capture_mode_guard", "capture_mode": str(payload.get("capture_mode") or "")[:40]}
            raise ValueError("fixture OCR accepts only interactive synthetic-image capture")
        payload["allow_fullscreen_fallback"] = False
        if SYNTHETIC_SCREEN_IMAGE is None:
            OCR_FAILURE_META = {"stage": "screenshot_not_loaded"}
            raise RuntimeError("synthetic browser screenshot has not been uploaded")
        if getattr(plugin, "_ocr_pipeline", None) is None:
            OCR_FAILURE_META = {"stage": "ocr_pipeline_missing"}
            raise RuntimeError("isolated RapidOCR pipeline is not installed")
        entry_module = importlib.import_module("plugins.study_companion.entry_ocr_entries")
        original_capture = entry_module.capture_interactive_region

        async def capture_synthetic_browser_png(**_kwargs):
            global OCR_CAPTURE_CALLS
            OCR_CAPTURE_CALLS += 1
            return SimpleNamespace(image=SYNTHETIC_SCREEN_IMAGE.copy(), canceled=False)

        entry_module.capture_interactive_region = capture_synthetic_browser_png
        OCR_FAILURE_META = {"stage": "normal_entrypoint_running"}
        started = time.perf_counter()
        try:
            result = await method(**payload)
        except Exception as exc:
            OCR_FAILURE_META = {"stage": "normal_entrypoint_exception", "error_type": type(exc).__name__}
            raise
        finally:
            entry_module.capture_interactive_region = original_capture
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        if type(result).__name__ == "Err":
            error = getattr(result, "error", None)
            OCR_FAILURE_META = {"stage": "normal_entrypoint_err", "error_type": type(error).__name__ if error is not None else "unknown"}
            return {"success": False, "error": {"message": str(getattr(error, "message", "OCR entrypoint failed"))[:180]}}
        value = core._result_payload(result)
        text = str(value.get("text") or "")
        normalized = " ".join(text.lower().split())
        formula_text = "".join(normalized.replace("²", "^2").split())
        tokens = {
            "Example 2": "example 2" in normalized,
            "u = x^2": "u=x^2" in formula_text,
            "du = 2x dx": "du=2xdx" in formula_text,
            "1/2": "1/2" in normalized or "1 / 2" in normalized,
        }
        OCR_EVIDENCE = {
            "run_id": run_id,
            "entrypoint": "StudyCompanionPlugin.study_ocr_snapshot",
            "capture_mode": str(value.get("capture_mode_used") or ""),
            "status": str(value.get("status") or ""),
            "latency_ms": elapsed_ms,
            "text": text[:2000],
            "expected_tokens": tokens,
            "expected_token_recall": sum(tokens.values()) / len(tokens),
            "entrypoint_updated_state": str(plugin._state.last_ocr_text or "") == text,
            "capture_calls": OCR_CAPTURE_CALLS,
            "session_id": core.ACTIVE_SESSION_ID,
            "screenshot": dict(SCREENSHOT_META),
            "pipeline_source_sha256": hashlib.sha256(ocr_fixture.OCR_SOURCE.read_bytes()).hexdigest(),
            "entrypoint_source_sha256": hashlib.sha256(ocr_fixture.OCR_ENTRY_SOURCE.read_bytes()).hexdigest(),
            "runtime_packages": {name: ocr_fixture.importlib.metadata.version(name) for name in ("rapidocr-pillow", "onnxruntime", "numpy", "Pillow")},
            "model_sha256": {name: hashlib.sha256((ocr_fixture._model_dir() / name).read_bytes()).hexdigest() for name in ocr_fixture.MODEL_NAMES},
        }
        OCR_FAILURE_META = {}
        if core.AGENT_INSTANCE is not None:
            core.AGENT_INSTANCE.lesson = text
        _record_model_calls(entry_id, run_id, calls_before, args, value)
        return value
    result = await method(**payload)
    if type(result).__name__ == "Err":
        error = getattr(result, "error", None)
        _record_model_calls(entry_id, run_id, calls_before, args, None)
        return {"success": False, "error": {"message": str(getattr(error, "message", "fixture method failed"))[:180]}}
    value = core._result_payload(result)
    _record_model_calls(entry_id, run_id, calls_before, args, value)
    return value


async def _fixture_state() -> dict[str, object]:
    plugin = core.PLUGIN_INSTANCE
    session_id = core.ACTIVE_SESSION_ID
    sessions = await asyncio.to_thread(plugin._store.list_sessions, 50)
    session = next((row for row in sessions if row.get("id") == session_id), {})
    interactions = await asyncio.to_thread(plugin._store.list_interactions, 500, session_id=session_id)
    mastery = await asyncio.to_thread(plugin._knowledge_tracker.get_mastery, SCOPE_TOPIC_ID)
    return {
        "correlation_id": CORRELATION_ID,
        "session_id": session_id,
        "active_mode": getattr(plugin._state, "active_mode", ""),
        "session_record_id": session.get("id"),
        "db_path": plugin._store.db_path.resolve().relative_to(ROOT).as_posix(),
        "agent_calls": [] if REAL is not None else list(core.AGENT_INSTANCE.calls),
        "model_calls": list(MODEL_CALL_LOG),
        "model_backend": MODEL_BACKEND,
        "interaction_count": len(interactions),
        "interaction_session_ids_match": all(row.get("session_id") == session_id for row in interactions),
        "interaction_rows": [{"id": str(row.get("id") or ""), "kind": str(row.get("kind") or ""), "session_id": str(row.get("session_id") or "")} for row in interactions],
        "mastery": mastery,
        "mastery_before": MASTERY_BEFORE,
        "screenshot": dict(SCREENSHOT_META),
        "ocr": dict(OCR_EVIDENCE),
        "ocr_failure": dict(OCR_FAILURE_META),
        "runs": [{"run_id": run_id, "entry_id": value.get("entry_id"), "correlation_id": value.get("correlation_id"), "session_id": value.get("session_id")} for run_id, value in RUNS.items()],
        "plugin_entrypoints_called": [run.get("entry_id") for run in RUNS.values()],
        "denied_entry_ids": list(DENIED_ENTRY_IDS),
        "ui_event_steps": [item.get("step") for group in UI_EVENTS for item in group.get("events", [])],
    }


def _persist_ui_proof() -> str:
    summary = asyncio.run_coroutine_threadsafe(_fixture_state(), LOOP).result(timeout=10)
    stamp = datetime.now(timezone.utc)
    source_file = core.RELEASE / "plugins" / "study_companion" / "__init__.py"
    observed_steps = {item.get("step") for group in UI_EVENTS for item in group.get("events", [])}
    required_steps = {
        "browser_output_gates_stimulated", "original_study_ui_ready",
        "ocr_button_populated_from_headless_screenshot", "ocr_grounded_explanation_visible",
        "first_contextual_followup_visible", "second_contextual_followup_visible", "question_visible",
        _scenario_rules()["gradeStepName"],
        "session_summary_visible", "same_session_reused_after_reload",
    }
    if MODEL_BACKEND == "real":
        required_steps.add("teaching_mode_selected")
    required_gate_counts = {
        "audio_context_attempted": 1, "audio_context_blocked": 1,
        "speech_synthesis_attempted": 1, "speech_synthesis_blocked": 1,
        "media_play_attempted": 1, "media_play_blocked": 1,
        "websocket_attempted": 1, "websocket_blocked": 1,
        "external_fetch_attempted": 1, "external_fetch_blocked": 1,
    }
    gates_pass = all(
        all((group.get("browserGate") or {}).get(key) == value for key, value in required_gate_counts.items())
        and (not (group.get("browserGate") or {}).get("microphone_attempted") or (group.get("browserGate") or {}).get("microphone_blocked") == (group.get("browserGate") or {}).get("microphone_attempted"))
        for group in UI_EVENTS
    )
    mastery_before = next((group.get("mastery_before") for group in UI_EVENTS if group.get("mastery_before") is not None), None)
    trace = UI_EVENTS[-1].get("run_trace", []) if UI_EVENTS else []
    traced_ids = {item.get("run_id") for item in trace if isinstance(item, dict)}
    trace_counts: dict[str, int] = {}
    for item in trace:
        if isinstance(item, dict):
            trace_counts[str(item.get("entry_id") or "")] = trace_counts.get(str(item.get("entry_id") or ""), 0) + 1
    trace_pass = (
        trace_counts.get("study_ocr_snapshot", 0) == 1
        and trace_counts.get("study_explain_text", 0) == 3
        and trace_counts.get("study_generate_targeted_question", 0) >= 1
        and trace_counts.get("study_evaluate_answer", 0) >= 1
        and trace_counts.get("study_summarize_session", 0) >= 2
        and (MODEL_BACKEND != "real" or trace_counts.get("study_set_mode", 0) == 1)
        and all(item.get("run_id") in RUNS and RUNS[item.get("run_id")].get("entry_id") == item.get("entry_id") for item in trace if isinstance(item, dict))
    )
    ocr_pass = (
        OCR_EVIDENCE.get("status") == "ok"
        and OCR_EVIDENCE.get("capture_mode") == "interactive"
        and OCR_EVIDENCE.get("entrypoint_updated_state") is True
        and OCR_EVIDENCE.get("expected_token_recall") == 1.0
        and OCR_EVIDENCE.get("session_id") == summary["session_id"]
        and OCR_EVIDENCE.get("run_id") in traced_ids
        and OCR_EVIDENCE.get("screenshot", {}).get("sha256") == SCREENSHOT_META.get("sha256")
    )
    screenshot_pass = bool(
        SCREENSHOT_META.get("sha256")
        and SCREENSHOT_META.get("correlation_id") == CORRELATION_ID
        and SCREENSHOT_META.get("inspector_artifact")
        and SYNTHETIC_SCREEN_IMAGE is not None
    )
    # Check actual plugin outcomes, not just browser milestone labels.
    explanations = [run for run in RUNS.values() if run["entry_id"] == "study_explain_text"]
    followups = [call for call in summary["agent_calls"] if call.get("follow_up")]
    evaluations = [run["data"] for run in RUNS.values() if run["entry_id"] == "study_evaluate_answer"]
    shared_outcome = (
        len(explanations) == 3
        and explanations[0]["args"].get("text") == OCR_EVIDENCE.get("text")
        and all(run["data"].get("reply") and run["data"].get("history_persisted") is not False and not run["data"].get("degraded") for run in explanations)
        and len(evaluations) == 1
    )
    if MODEL_BACKEND == "real":
        logged = summary["model_calls"]
        explain_groups = [group for group in logged if group["entry_id"] == "study_explain_text"]
        prompt_growth = [max(group["prompt_chars"] or [0]) for group in explain_groups]
        all_statuses = [status for group in logged for status in group["statuses"]]
        # UX regressions the previous round measured: the mode banner was
        # prepended to every explanation, and session text came back in English.
        prefix_replies = [run for run in explanations if MODE_BANNER in str(run["data"].get("reply") or "")]
        summaries = [run["data"] for run in RUNS.values() if run["entry_id"] == "study_summarize_session"]
        cjk = re.compile(r"[\u4e00-\u9fff]")
        ux_checks = {
            "mode_banner_replies": len(prefix_replies),
            "evaluation_feedback_has_cjk": bool(evaluations and cjk.search(str(evaluations[0].get("feedback") or ""))),
            "summaries_have_cjk": bool(summaries) and all(
                cjk.search(str(item.get("reply") or "")) for item in summaries
            ),
            "explanations_have_cjk": all(cjk.search(str(run["data"].get("reply") or "")) for run in explanations),
        }
        outcome_pass = (
            shared_outcome
            and core.AGENT_INSTANCE is None
            and len(logged) >= 6
            and sum(int(group["model_call_count"]) for group in logged) >= 7
            and all(int(group["model_call_count"]) >= 1 for group in explain_groups)
            and all(status == "ok" for status in all_statuses)
            and all(token > 0 for group in logged for token in group["input_tokens"])
            and len({str(run["data"].get("reply") or "")[:160] for run in explanations}) == 3
            and len(prompt_growth) == 3
            and prompt_growth[0] < prompt_growth[1] < prompt_growth[2]
            and evaluations[0].get("verdict") in {"correct", "partial", "wrong", "dont_know"}
            and isinstance(evaluations[0].get("score"), int)
            and 0 <= int(evaluations[0].get("score") or 0) <= 100
            and ux_checks["mode_banner_replies"] == 0
            and ux_checks["summaries_have_cjk"]
            and ux_checks["explanations_have_cjk"]
        )
    else:
        ux_checks = {}
        outcome_pass = (
            shared_outcome
            and [call.get("follow_up_index") for call in followups] == [1, 2]
            and all(call.get("prior_lesson_in_context") for call in followups)
            and followups[-1].get("previous_followup_question_in_context") is True
            and followups[-1].get("previous_followup_response_in_context") is True
            and evaluations[0].get("verdict") == "correct" and evaluations[0].get("score") == 100
            and all(call.get("context_session_id") == summary["session_id"] for call in summary["agent_calls"])
        )
    flow_pass = (
        required_steps.issubset(observed_steps)
        and all(event.get("result_visible") is True for group in UI_EVENTS for event in group.get("events", []))
        and len(UI_EVENTS) >= 2
        and all(group.get("correlation_id") == CORRELATION_ID and group.get("session_id") == summary["session_id"] and group.get("session_record_id_matches") and group.get("interaction_session_ids_match") for group in UI_EVENTS)
        and gates_pass
        and screenshot_pass and ocr_pass and trace_pass and outcome_pass
        and mastery_before is not None
        and float(summary["mastery"] or 0) > float(mastery_before)
        and summary["interaction_count"] >= 4
        and all(run.get("correlation_id") == CORRELATION_ID and run.get("session_id") == summary["session_id"] for run in RUNS.values())
        and not any((core._provider_downstream_calls, core._socket_downstream_calls, core._audio_downstream_calls, HTTP_DOWNSTREAM["websocket_upgrade"], HTTP_DOWNSTREAM["external_fetch"]))
    )
    proof = {
        "timestamp_utc": stamp.isoformat(),
        "result": (
            "PASS_SHIPPED_STATIC_UI_REAL_MODEL_LOOP"
            if flow_pass and MODEL_BACKEND == "real"
            else "PASS_SHIPPED_STATIC_UI_PLUGIN_LOOP" if flow_pass
            else "PARTIAL_SHIPPED_STATIC_UI_ADAPTER"
        ),
        "evidence_level": (
            "shipped static UI + isolated loopback adapter + real extracted plugin methods + live provider; no N.E.K.O host"
            if MODEL_BACKEND == "real"
            else "shipped static UI + isolated loopback adapter + real extracted plugin methods; no N.E.K.O host"
        ),
        "plugin_file_sha256": hashlib.sha256(source_file.read_bytes()).hexdigest(),
        "session_id": summary["session_id"],
        "db_path": summary["db_path"],
        "correlation_id": CORRELATION_ID,
        "session_record_id_matches": summary["session_record_id"] == summary["session_id"],
        "interaction_count": summary["interaction_count"],
        "sqlite_interactions": summary["interaction_rows"],
        "interaction_session_ids_match": summary["interaction_session_ids_match"],
        "mastery_before_ui_answer": mastery_before,
        "mastery": summary["mastery"],
        "required_flow_steps_present": sorted(required_steps.intersection(observed_steps)),
        "required_flow_steps_missing": sorted(required_steps.difference(observed_steps)),
        "browser_gate_pass": gates_pass,
        "screenshot": SCREENSHOT_META,
        "ocr": OCR_EVIDENCE,
        "runs": [{"run_id": run_id, "entry_id": run["entry_id"], "correlation_id": run["correlation_id"], "session_id": run["session_id"], "args": run["args"], "data": run["data"]} for run_id, run in RUNS.items()],
        "agent_double_calls": summary["agent_calls"],
        "model_backend": MODEL_BACKEND,
        "provider": _real_lifecycle().get("provider"),
        "lifecycle": _real_lifecycle(),
        "ui_ux_checks": ux_checks,
        "model_calls_by_ui_action": summary["model_calls"],
        "model_call_totals": {
            "actions": len(summary["model_calls"]),
            "calls": sum(int(group["model_call_count"]) for group in summary["model_calls"]),
            "input_tokens": sum(token for group in summary["model_calls"] for token in group["input_tokens"]),
            "output_tokens": sum(token for group in summary["model_calls"] for token in group["output_tokens"]),
            "max_call_ms": max((ms for group in summary["model_calls"] for ms in group["latency_ms"]), default=0),
        },
        "plugin_outcomes_pass": outcome_pass,
        "browser_run_trace": trace,
        "trace_pass": trace_pass,
        "ui_events": UI_EVENTS,
        "plugin_entrypoints_called": [run.get("entry_id") for run in RUNS.values()],
        "browser_gate_counts": UI_EVENTS[-1].get("browserGate") if UI_EVENTS and isinstance(UI_EVENTS[-1], dict) else None,
        "downstream_calls": {"provider": core._provider_downstream_calls, "socket": core._socket_downstream_calls, "audio": core._audio_downstream_calls, "websocket_upgrade": HTTP_DOWNSTREAM["websocket_upgrade"], "external_fetch_server_hits": HTTP_DOWNSTREAM["external_fetch"]},
        "runtime_guards": core.COUNTS,
        "config_data_read_safe_metadata": core.CONFIG_DATA_READS,
        "ocr_or_capture_used": True,
        "live_model_or_provider_used": MODEL_BACKEND == "real",
        "private_config_values_or_secrets_included": False,
    }
    path = core.EVIDENCE_ROOT / f"neko-study-plugin-ui-{stamp.strftime('%Y%m%dT%H%M%SZ')}.json"
    path.write_text(json.dumps(proof, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return path.relative_to(ROOT).as_posix()


class Handler(BaseHTTPRequestHandler):
    server_version = "LocalStudyFixture/1"

    def log_message(self, _fmt, *_args):
        return

    def _send(self, status: int, body: bytes, content_type: str = "application/json; charset=utf-8"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; style-src-attr 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self'; media-src 'none'; connect-src 'self'; object-src 'none'; base-uri 'none'")
        self.send_header("Permissions-Policy", "microphone=(), camera=(), speaker-selection=()")
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if self.headers.get("Upgrade", "").lower() == "websocket":
            HTTP_DOWNSTREAM["websocket_upgrade"] += 1
            return self._send(403, _json_bytes({"error": "websocket_upgrade_denied"}))
        if parsed.path.startswith("/runs/"):
            parts = parsed.path.strip("/").split("/")
            if len(parts) not in (2, 3) or (len(parts) == 3 and parts[2] != "export"):
                return self._send(403, _json_bytes({"error": "run_route_denied"}))
            run = RUNS.get(parts[1])
            if not run:
                return self._send(404, _json_bytes({"error": "unknown_run"}))
            if len(parts) == 3:
                data = run["data"]
                return self._send(200, _json_bytes({"items": [{"type": "json", "json": {"success": True, "data": data}}]}))
            return self._send(200, _json_bytes({"status": "succeeded"}))
        if parsed.path == "/__browser-gate.js":
            return self._send(200, _browser_gate_js().encode(), "text/javascript; charset=utf-8")
        if parsed.path == "/__study-scenario.js":
            script = _scenario_js().replace(
                "__RULES_JSON__", json.dumps(_scenario_rules(), ensure_ascii=False)
            )
            return self._send(200, script.encode("utf-8"), "text/javascript; charset=utf-8")
        if parsed.path == "/__synthetic-lesson":
            if parsed.query != f"correlation_id={CORRELATION_ID}":
                return self._send(404, _json_bytes({"error": "unknown_synthetic_lesson"}))
            lesson = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Synthetic Lesson Fixture</title><style>html,body{margin:0;background:#eaf0f4;color:#17242b;font-family:Arial,sans-serif}main{box-sizing:border-box;width:1120px;margin:70px auto;padding:52px 64px;background:#fff;border:2px solid #8da3b0;border-radius:18px;box-shadow:0 16px 40px #24374622}small{color:#536a76;font-size:18px;letter-spacing:.08em}h1{font-size:46px;margin:24px 0 38px}p{font-size:40px;line-height:1.55;margin:20px 0}.cid{font-size:13px;color:#627780}</style></head><body><main><small>SYNTHETIC STUDY MATERIAL · NO USER SCREEN</small><h1>Example 2: u-substitution</h1><p>Let u = x^2</p><p>Then du = 2x dx</p><p>So x dx = (1/2) du</p><p>Integrate exp(u) after substitution</p><div class="cid">Fixture correlation: """ + CORRELATION_ID + "</div></main></body></html>"
            return self._send(200, lesson.encode("utf-8"), "text/html; charset=utf-8")
        if parsed.path == "/__fixture-state":
            try:
                value = asyncio.run_coroutine_threadsafe(_fixture_state(), LOOP).result(timeout=20)
                return self._send(200, _json_bytes(value))
            except Exception:
                return self._send(500, _json_bytes({"error": "fixture_state_unavailable"}))
        if parsed.path.startswith("/plugin/study_companion/ui-api/i18n/"):
            return self._send(200, b"{}")
        if parsed.path == "/favicon.ico":
            return self._send(204, b"", "image/x-icon")
        relative = "index.html" if parsed.path == "/" else unquote(parsed.path.lstrip("/"))
        target = (STATIC_ROOT / relative).resolve()
        if STATIC_ROOT.resolve() not in target.parents and target != STATIC_ROOT.resolve():
            return self._send(403, _json_bytes({"error": "static_path_denied"}))
        if not target.is_file():
            return self._send(404, _json_bytes({"error": "static_asset_not_found"}))
        body = target.read_bytes()
        if relative == "index.html":
            html = body.decode("utf-8")
            html = html.replace("</head>", '<script src="/__browser-gate.js"></script>\n</head>')
            html = html.replace("</body>", '<script type="module" src="/__study-scenario.js"></script>\n</body>')
            body = html.encode("utf-8")
        ctype = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in {"application/javascript", "application/json"}:
            ctype += "; charset=utf-8"
        return self._send(200, body, ctype)

    def do_POST(self):
        global SYNTHETIC_SCREEN_IMAGE, SCREENSHOT_META, OCR_FAILURE_META
        parsed = urlparse(self.path)
        if parsed.path == f"/__fixture-stop/{CORRELATION_ID}":
            self._send(200, _json_bytes({"stopping": True}))
            LOOP.call_soon_threadsafe(LOOP.stop)
            return
        screenshot_prefix = f"/__fixture-screenshot/{CORRELATION_ID}"
        if parsed.path == screenshot_prefix:
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = 0
            if length < 64 or length > 6_000_000:
                return self._send(413, _json_bytes({"error": "screenshot_size_denied"}))
            if self.headers.get("Content-Type", "").split(";")[0].strip().lower() != "image/png":
                return self._send(415, _json_bytes({"error": "png_required"}))
            source = self.headers.get("X-Fixture-Capture-Source", "")
            artifact = self.headers.get("X-Fixture-Inspector-Artifact", "")
            if source != "web-inspector-headless-chromium" or not re.fullmatch(
                rf"neko-study-browser-pixels-{re.escape(CORRELATION_ID)}\.json", artifact
            ):
                return self._send(400, _json_bytes({"error": "screenshot_provenance_required"}))
            raw = self.rfile.read(length)
            try:
                from PIL import Image

                with Image.open(io.BytesIO(raw)) as source_image:
                    if source_image.format != "PNG" or source_image.width < 500 or source_image.height < 400:
                        raise ValueError("screenshot dimensions or format rejected")
                    source_image.load()
                    image = source_image.convert("RGB")
            except Exception:
                return self._send(400, _json_bytes({"error": "invalid_synthetic_png"}))
            if SYNTHETIC_SCREEN_IMAGE is not None:
                return self._send(409, _json_bytes({"error": "screenshot_already_loaded"}))
            SYNTHETIC_SCREEN_IMAGE = image
            SCREENSHOT_META = {
                "correlation_id": CORRELATION_ID,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "width": image.width,
                "height": image.height,
                "source": source,
                "inspector_artifact": artifact,
                "pixel_origin": "synthetic lesson HTML rendered in isolated headless Chromium",
            }
            return self._send(200, _json_bytes({"loaded": True, "screenshot": SCREENSHOT_META}))
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length < 0 or length > 200_000:
            return self._send(413, _json_bytes({"error": "request_too_large"}))
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
        except Exception:
            return self._send(400, _json_bytes({"error": "invalid_json"}))
        if parsed.path == "/__fixture-state":
            events = payload.get("events") if isinstance(payload, dict) else None
            if not isinstance(events, list) or len(events) > 20:
                return self._send(400, _json_bytes({"error": "invalid_ui_evidence"}))
            safe_events = []
            for item in events:
                if not isinstance(item, dict) or not isinstance(item.get("step"), str):
                    continue
                safe_events.append({
                    "step": item["step"][:80],
                    "at": str(item.get("at") or "")[:40],
                    "run_id": str(item.get("run_id") or "")[:80],
                    "result_visible": item.get("result_visible") is True,
                    "visible_reply": str(item.get("visible_reply") or "")[:500],
                    "visible_question": str(item.get("visible_question") or "")[:300],
                    "visible_evaluation": str(item.get("visible_evaluation") or "")[:300],
                })
            gate = payload.get("browserGate") if isinstance(payload.get("browserGate"), dict) else {}
            safe_group = {"events": safe_events, "browserGate": {k: int(v) for k, v in gate.items() if isinstance(v, (int, float))}}
            safe_group["correlation_id"] = str(payload.get("correlation_id") or "")[:80]
            safe_group["session_id"] = str(payload.get("session_id") or "")[:100]
            safe_group["session_record_id_matches"] = bool(payload.get("session_record_id_matches"))
            safe_group["interaction_session_ids_match"] = bool(payload.get("interaction_session_ids_match"))
            safe_group["interaction_count"] = int(payload.get("interaction_count") or 0)
            safe_group["mastery"] = float(payload.get("mastery") or 0)
            safe_group["mastery_before"] = float(payload["mastery_before"]) if isinstance(payload.get("mastery_before"), (int, float)) else None
            trace = payload.get("run_trace") if isinstance(payload.get("run_trace"), list) else []
            safe_group["run_trace"] = [
                {"entry_id": str(item.get("entry_id") or "")[:100], "run_id": str(item.get("run_id") or "")[:80], "at": str(item.get("at") or "")[:40]}
                for item in trace[:100] if isinstance(item, dict)
            ]
            UI_EVENTS.append(safe_group)
            if not any(item.get("step") == "same_session_reused_after_reload" for item in safe_events):
                return self._send(200, _json_bytes({"saved": True, "proof": "pending_reload"}))
            try:
                return self._send(200, _json_bytes({"saved": True, "proof": _persist_ui_proof()}))
            except Exception:
                return self._send(500, _json_bytes({"error": "proof_write_failed"}))
        if parsed.path != "/runs" or payload.get("plugin_id") != "study_companion":
            HTTP_DOWNSTREAM["external_fetch"] += 1
            return self._send(403, _json_bytes({"error": "route_denied"}))
        entry_id = str(payload.get("entry_id") or "")
        args = payload.get("args") if isinstance(payload.get("args"), dict) else {}
        if entry_id not in ALLOWED_ENTRYPOINTS:
            DENIED_ENTRY_IDS.append(entry_id[:100])
            return self._send(403, _json_bytes({"error": "entrypoint_denied"}))
        run_id = str(uuid.uuid4())
        try:
            result = asyncio.run_coroutine_threadsafe(_call_plugin(entry_id, args, run_id), LOOP).result(timeout=100)
        except Exception as exc:
            diagnostic = {
                "stage": OCR_FAILURE_META.get("stage", "adapter_dispatch") if entry_id == "study_ocr_snapshot" else "adapter_dispatch",
                "error_type": type(exc).__name__,
                "frames": [
                    {"module": frame.name.rsplit(".", 1)[0][:120], "function": frame.name[:120], "line": frame.lineno}
                    for frame in traceback.extract_tb(exc.__traceback__)[-8:]
                ] if entry_id == "study_ocr_snapshot" else [],
            }
            if entry_id == "study_ocr_snapshot":
                OCR_FAILURE_META = diagnostic
            result = {"success": False, "error": {"message": f"isolated plugin method failed: {type(exc).__name__}"}, "diagnostic": diagnostic}
        RUNS[run_id] = {
            "entry_id": entry_id,
            "args": args,
            "data": result,
            "correlation_id": CORRELATION_ID,
            "session_id": core.ACTIVE_SESSION_ID,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        return self._send(200, _json_bytes({"run_id": run_id}))

    def do_OPTIONS(self):
        return self._send(405, _json_bytes({"error": "method_not_allowed"}))

    def do_PUT(self):
        return self._send(405, _json_bytes({"error": "method_not_allowed"}))

    def do_DELETE(self):
        return self._send(405, _json_bytes({"error": "method_not_allowed"}))

    def do_PATCH(self):
        return self._send(405, _json_bytes({"error": "method_not_allowed"}))

    def do_HEAD(self):
        return self._send(405, b"")

    def handle_expect_100(self):
        return False


def main() -> None:
    global LOOP, SERVER, MASTERY_BEFORE, MODEL_BACKEND, REAL
    parser = argparse.ArgumentParser(description="Isolated Study UI adapter")
    parser.add_argument("--real-model", action="store_true",
                        help="drive the shipped UI with the authorized live provider")
    parser.add_argument("--key-file", default=str(real.DEFAULT_KEY_FILE))
    parser.add_argument("--base-url", default=real.DEFAULT_BASE_URL)
    parser.add_argument("--model", default=real.DEFAULT_MODEL)
    parser.add_argument("--thinking", choices=("host", "enabled", "disabled"), default="host")
    args = parser.parse_args()
    api_key = ""
    if args.real_model:
        MODEL_BACKEND = "real"
        REAL = real
        real.THINKING_MODE = args.thinking
        # Read the credential before the filesystem guard exists; never print it.
        api_key = real.read_credential(Path(args.key_file))
        real.KEY_MATERIAL = api_key
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    loop = asyncio.new_event_loop()
    # Create the only listener before the Python network guard; bind is explicit loopback.
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    SERVER = server
    core._deny_process = ocr_fixture._trace_blocked_process
    core._install_guards()
    ocr_fixture._install_ocr_runtime_guards()
    LOOP = loop
    stage = "plugin_methods_seed"
    safe_context_flags = None
    safe_topic_identity = None
    safe_error_code = None
    server_thread = None
    try:
        if MODEL_BACKEND == "real":
            plugin, lifecycle = loop.run_until_complete(REAL.bootstrap_live_plugin(
                model=args.model, base_url=args.base_url, api_key=api_key
            ))
            core.PLUGIN_INSTANCE = plugin
            stage = "live_session_start"
            started = core._result_payload(loop.run_until_complete(plugin.study_start_session()))
            core.ACTIVE_SESSION_ID = str(started.get("session_id") or "")
            if not core.ACTIVE_SESSION_ID:
                raise RuntimeError("live plugin did not create a session")
        else:
            loop.run_until_complete(core._run_loop())
        plugin = core.PLUGIN_INSTANCE
        stage = "isolated_rapidocr_pipeline"
        plugin._ocr_pipeline = ocr_fixture._build_ocr_pipeline()
        stage = "synthetic_practice_scope_seed"
        topic = {
            "id": SCOPE_TOPIC_ID,
            "name": "Synthetic u-substitution integration fixture",
            "subject": "math",
            "stage": "college",
            "course_family": "calculus",
            "chapter": "Synthetic integration",
            "unit": "u-substitution",
            "depth": 2,
            "difficulty": 0.5,
            "prerequisites": [],
            "related": [],
            "typical_misconceptions": [],
            "skills": ["substitution"],
            "question_types": ["short_answer"],
            "examples": ["例题2：计算 ∫x·e^(x^2) dx。令 u=x^2，则 du=2x dx。"],
            "source": "runtime",
        }
        plugin._store.upsert_topic(topic)
        safe_topic_identity = {key: str(topic.get(key) or "")[:100] for key in ("id", "stage", "subject", "course_family", "chapter", "unit")}
        scope = {
            "schema_version": 1,
            "mode": "explicit_topic",
            "topic_id": SCOPE_TOPIC_ID,
            "stage": str(topic.get("stage") or ""),
            "subject": str(topic.get("subject") or ""),
            "course_family": str(topic.get("course_family") or ""),
            "chapter": str(topic.get("chapter") or ""),
            "unit": str(topic.get("unit") or ""),
        }
        if not scope["chapter"]:
            scope.pop("chapter")
        if not scope["unit"]:
            scope.pop("unit")
        scope_result = loop.run_until_complete(
            plugin.study_set_practice_scope(scope=scope)
        )
        if type(scope_result).__name__ == "Err":
            scope_error = getattr(scope_result, "error", None)
            safe_error_code = str(getattr(scope_error, "code", "unknown"))[:80]
            raise RuntimeError("safe UI adapter preflight: synthetic topic scope rejected")
        stage = "question_context_preflight"
        context = loop.run_until_complete(plugin.study_question_context())
        context_payload = core._result_payload(context)
        safe_context_flags = {
            "no_data": bool(context_payload.get("no_data")),
            "selection_context_id_present": bool(context_payload.get("selection_context_id")),
        }
        if context_payload.get("no_data") or not context_payload.get("selection_context_id"):
            raise RuntimeError("safe UI adapter preflight: plugin has no persisted topic context for targeted UI question")
        # Prove the targeted question path the shipped UI uses can use this session.
        stage = "targeted_question_preflight"
        targeted = loop.run_until_complete(plugin.study_generate_targeted_question(selection_context_id=context_payload["selection_context_id"]))
        targeted_payload = core._result_payload(targeted)
        if not targeted_payload.get("question"):
            raise RuntimeError("safe UI adapter preflight: targeted plugin method returned no question")
        fresh_session = loop.run_until_complete(plugin.study_start_session())
        fresh_payload = core._result_payload(fresh_session)
        core.ACTIVE_SESSION_ID = str(fresh_payload.get("session_id") or "")
        if not core.ACTIVE_SESSION_ID:
            raise RuntimeError("isolated OCR UI session was not created")
        MASTERY_BEFORE = float(loop.run_until_complete(asyncio.to_thread(plugin._knowledge_tracker.get_mastery, SCOPE_TOPIC_ID)) or 0)
        RUNS.clear()
        UI_EVENTS.clear()
        MODEL_CALL_LOG.clear()
        if core.AGENT_INSTANCE is not None:
            core.AGENT_INSTANCE.calls.clear()
        print(json.dumps({
            "ready": True,
            "url": f"http://127.0.0.1:{server.server_port}/?locale=en&scenario=ocr",
            "synthetic_lesson_url": f"http://127.0.0.1:{server.server_port}/__synthetic-lesson?correlation_id={CORRELATION_ID}",
            "screenshot_upload_url": f"http://127.0.0.1:{server.server_port}/__fixture-screenshot/{CORRELATION_ID}",
            "correlation_id": CORRELATION_ID,
            "session_id": core.ACTIVE_SESSION_ID,
            "evidence_level": "shipped static Study UI + synthetic headless screenshot + genuine OCR entrypoint/plugin methods"
            + (" + live provider model calls" if MODEL_BACKEND == "real" else ""),
            "preflight_question_context": "PASS",
            "targeted_question_method": "PASS",
            "host_started": False,
            "real_provider_or_model_used": MODEL_BACKEND == "real",
            "lifecycle": _real_lifecycle().get("startup_result_type"),
            "ocr_or_capture_used": False,
        }, ensure_ascii=False))
        server_thread = threading.Thread(target=server.serve_forever, name="neko-study-ui-loopback", daemon=True)
        server_thread.start()
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    except BaseException as exc:
        safe = {"status": "BLOCKED_OR_FAILED_UI_ADAPTER", "stage": stage, "error_type": type(exc).__name__, "safe_error_code": safe_error_code, "safe_context_flags": safe_context_flags, "safe_topic_identity": safe_topic_identity, "plugin_instance_created": core.PLUGIN_INSTANCE_CREATED, "guards": core.COUNTS}
        print(json.dumps(safe, ensure_ascii=False))
    finally:
        if server_thread and server_thread.is_alive():
            server.shutdown()
        server.server_close()
        loop.close()


if __name__ == "__main__":
    main()
