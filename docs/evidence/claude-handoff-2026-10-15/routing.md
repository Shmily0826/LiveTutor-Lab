# Routing latency: missing implementation context

This is a bounded source snapshot for Claude, not a product change or a completed optimization. Goal remains paused. Main branch for existing product files: codex/daily-learning-companion, baseline 94a1f02. Read only this packet plus the linked existing files; do not audit the repository.

## Correction to the proposed solution

On a metered free-agent route, host reserve_agent_daily_quota already increments and persists used at reservation time. AgentQuotaReservation.consume only uses the in-memory entitlement to avoid charging twice. On non-metered routes the host returns limited=false. These are distinct from the task's cumulative DeepSeek egress ledger, which counts external requests. Do not add reservations to actual request counts as if they were separate bills. No automatic refund method was found in this quota module. Cancellation of asyncio.to_thread does not guarantee cancellation of the underlying quota write.

Do not implement concurrency yet. First propose per-call timing and a small input-equivalence evaluation. Caller request ranges are requested ranges, not verified read evidence. A file/line hint may not identify the concept in a deictic question; exact stochastic output equality on five examples is not proof of general equivalence. Retain topic/course/history protections.

Questions to settle in ONE answer: where to measure the existing 4.690-second source/context window; whether there is a smaller optimization than speculative routing; if routing prefetch is justified, specify cancellation/deadline/reservation ownership and how exactly one routing result reaches the existing final context. No live tests or paid calls. Give an implementable minimal plan, distinguish confirmed facts from hypotheses, and list any truly missing runtime observations once.

## Existing public files (read only needed functions)

All paths below are in patches/neko-study-2026-10-10-product/payload/study_companion/ on codex/daily-learning-companion:
- study_code_teaching.py (entire 98-line adapter)
- study_code_tools.py (_code_sync, _code_head, study_code_tool)
- entry_tutor_context_support.py (_route_study_input_semantics, _build_knowledge_guidance_context, _build_learning_context)
- study_avatar_tools.py (_study_explain_for_turn)
- entry_tutor_explain_entries.py (study_explain_text)
- study_model_gateway.py (AgentQuotaReservation, reserve_optional_agent_call, _reserve_agent_quota)
- tutor_llm_agent_concept_explain.py (reservation propagation around line375)
- tutor_llm_agent.py (exists publicly; relevant delegation reproduced below)
- study_materials.py (also exists publicly)

Measured timing and boundaries: ../daily-companion-phase57-native-source-2026-10-15.md. The private/local originals are intentionally not required. Do not ask the user to paste these public files.

### patches/neko-study-2026-10-10-product/payload/study_companion/tutor_llm_agent.py:76-80

Snapshot SHA256 `618e3dc5d3def47bcfa644fa280799233fac9b84969c8dde0e85c4ea80c04257`; current local source, not a claim of the historical run source.

```python
0076     async def reserve_optional_agent_call(
0077         self, operation: str
0078     ) -> tuple[bool, AgentQuotaReservation | None]:
0079         return await self._model_gateway.reserve_optional_agent_call(operation)
0080
```

### patches/neko-study-2026-10-10-product/payload/study_companion/tutor_llm_agent.py:341-389

Snapshot SHA256 `618e3dc5d3def47bcfa644fa280799233fac9b84969c8dde0e85c4ea80c04257`; current local source, not a claim of the historical run source.

```python
0341     async def _call_model(
0342         self,
0343         messages: list[dict[str, Any]],
0344         *,
0345         operation: str = LLM_OPERATION_CONCEPT_EXPLAIN,
0346         deadline: float | None = None,
0347         quota_reservation: AgentQuotaReservation | None = None,
0348     ) -> str:
0349         call_kwargs: dict[str, Any] = {
0350             "operation": operation,
0351             "deadline": deadline,
0352         }
0353         if quota_reservation is not None:
0354             call_kwargs["quota_reservation"] = quota_reservation
0355         result = await self._call_model_result(messages, **call_kwargs)
0356         return result.text
0357
0358     async def _call_model_result(
0359         self,
0360         messages: list[dict[str, Any]],
0361         *,
0362         operation: str = LLM_OPERATION_CONCEPT_EXPLAIN,
0363         deadline: float | None = None,
0364         runtime: StudyModelRuntimeSnapshot | None = None,
0365         quota_reservation: AgentQuotaReservation | None = None,
0366     ) -> StudyModelResult | QwenNativeResult:
0367         effective_deadline = deadline or self._new_operation_deadline(
0368             operation, messages
0369         )
0370         # Preserve instance-level replacement used by older integrations without
0371         # making the production router depend on a Qwen-specific client.
0372         if self._qwen_client is not self._model_gateway.native_client:
0373             return await self._qwen_client.call(
0374                 messages,
0375                 operation=operation,
0376                 deadline=effective_deadline,
0377             )
0378         runtime = runtime or _bound_model_runtime.get()
0379         call_kwargs: dict[str, Any] = {
0380             "operation": operation,
0381             "deadline": effective_deadline,
0382             "runtime": runtime,
0383         }
0384         if quota_reservation is not None:
0385             call_kwargs["quota_reservation"] = quota_reservation
0386         return await self._model_gateway.call(messages, **call_kwargs)
0387
0388     def _new_operation_deadline(
0389         self, operation: str, messages: list[dict[str, Any]]
```

### benchmarks/raw/neko-product-host/utils/config_manager/quota.py:74-191

Snapshot SHA256 `a2d229e2527f4706fc61eb82d962f61542eb9f44ecaf71c459bf2e2ad9d7f530`; current local source, not a claim of the historical run source.

```python
0074     def reserve_agent_daily_quota(
0075         self,
0076         source: str = "",
0077         units: int = 1,
0078         minimum_units: int = 1,
0079     ) -> tuple[int, dict]:
0080         """Atomically reserve up to ``units`` while preserving a required minimum.
0081
0082         When the preferred amount is unavailable but ``minimum_units`` still fits,
0083         only the minimum is consumed. This lets optional model work reserve the
0084         required primary call without a check-then-consume race.
0085         """
0086         requested_units = max(1, int(units or 1))
0087         required_units = max(0, min(requested_units, int(minimum_units or 0)))
0088
0089         from utils.config_manager import ConfigManager
0090
0091         is_metered = self.is_agent_free()
0092         today = date.today().isoformat()
0093         limit = int(self._free_agent_daily_limit)
0094         if not is_metered:
0095             return requested_units, {
0096                 "limited": False,
0097                 "date": today,
0098                 "used": 0,
0099                 "limit": None,
0100                 "remaining": None,
0101                 "source": source or "",
0102             }
0103
0104         self.ensure_config_directory()
0105         quota_path = self._get_agent_quota_path()
0106         with ConfigManager._agent_quota_lock:
0107             data = {"date": today, "used": 0}
0108             try:
0109                 if quota_path.exists():
0110                     with open(quota_path, "r", encoding="utf-8") as f:
0111                         loaded = json.load(f)
0112                     if isinstance(loaded, dict):
0113                         loaded_date = str(loaded.get("date") or today)
0114                         loaded_used = int(loaded.get("used", 0) or 0)
0115                         if loaded_date == today:
0116                             data = {"date": today, "used": max(0, loaded_used)}
0117             except Exception:
0118                 data = {"date": today, "used": 0}
0119
0120             used = int(data.get("used", 0))
0121             available = max(0, limit - used)
0122             if available >= requested_units:
0123                 reserved = requested_units
0124             elif required_units and available >= required_units:
0125                 reserved = required_units
0126             else:
0127                 reserved = 0
0128             if reserved == 0 and required_units:
0129                 self._maybe_notify_quota_exceeded(used, limit)
0130             if reserved:
0131                 used += reserved
0132                 try:
0133                     atomic_write_json(
0134                         quota_path,
0135                         {"date": today, "used": used},
0136                         ensure_ascii=False,
0137                         indent=2,
0138                     )
0139                 except Exception as e:
0140                     logger.warning("保存 Agent 配额计数失败: %s", e)
0141             return reserved, {
0142                 "limited": True,
0143                 "date": today,
0144                 "used": used,
0145                 "limit": limit,
0146                 "remaining": max(0, limit - used),
0147                 "source": source or "",
0148             }
0149
0150     def consume_agent_daily_quota(self, source: str = "", units: int = 1) -> tuple[bool, dict]:
0151         """Consume the Agent model daily quota (only effective when the actual Agent model is free-agent-model). The quota is not enforced locally alone; local counting just reduces useless requests and saves network bandwidth.
0152
0153         Returns:
0154             (ok, info)
0155             info:
0156               - limited: bool
0157               - date: YYYY-MM-DD
0158               - used: int
0159               - limit: int | None
0160               - remaining: int | None
0161               - source: str
0162         """
0163         if units <= 0:
0164             units = 1
0165         reserved, info = self.reserve_agent_daily_quota(
0166             source=source,
0167             units=units,
0168             minimum_units=units,
0169         )
0170         return reserved == units, info
0171
0172     async def areserve_agent_daily_quota(
0173         self,
0174         source: str = "",
0175         units: int = 1,
0176         minimum_units: int = 1,
0177     ) -> tuple[int, dict]:
0178         """Async wrapper of ``reserve_agent_daily_quota``."""
0179         return await asyncio.to_thread(
0180             self.reserve_agent_daily_quota,
0181             source,
0182             units,
0183             minimum_units,
0184         )
0185
0186     async def aconsume_agent_daily_quota(self, source: str = "", units: int = 1) -> tuple[bool, dict]:
0187         """Async wrapper of ``consume_agent_daily_quota``.
0188
0189         The sync version must not run directly on the event loop (open+fsync blocks).
0190         """
0191         return await asyncio.to_thread(self.consume_agent_daily_quota, source, units)
```

### benchmarks/raw/neko-app/resources/bin/plugins/study_companion/_semantic_routing.py:1-190

Snapshot SHA256 `3a5343d94353c91327ad5857830509a48d67dcbf6361138b2a104e0307075d1c`; current local source, not a claim of the historical run source.

```python
0001 from __future__ import annotations
0002
0003 from collections.abc import Mapping
0004 from dataclasses import dataclass
0005 import json
0006 import math
0007 import re
0008 from typing import Literal, TypeAlias, cast
0009
0010
0011 Subject: TypeAlias = Literal[
0012     "math", "chinese", "english", "physics", "chemistry", "biology",
0013     "history", "geography", "politics", "economics", "computer_science",
0014     "unknown",
0015 ]
0016 KnowledgeGuidanceStatus: TypeAlias = Literal[
0017     "applied", "not_matched", "low_confidence", "routing_unavailable",
0018     "not_applicable",
0019 ]
0020 ResponseMode: TypeAlias = Literal[
0021     "problem_solving", "general_explanation", "general_discussion", "unknown"
0022 ]
0023
0024 ALLOWED_SUBJECTS = frozenset(
0025     {
0026         "math", "chinese", "english", "physics", "chemistry", "biology",
0027         "history", "geography", "politics", "economics", "computer_science",
0028         "unknown",
0029     }
0030 )
0031 KNOWLEDGE_GUIDANCE_STATUSES = frozenset(
0032     {"applied", "not_matched", "low_confidence", "routing_unavailable", "not_applicable"}
0033 )
0034 RESPONSE_MODES = frozenset(
0035     {"problem_solving", "general_explanation", "general_discussion", "unknown"}
0036 )
0037 MAX_RETRIEVAL_CONCEPTS = 6
0038 MAX_RETRIEVAL_CONCEPT_LENGTH = 64
0039 MAX_CLASSIFICATION_LENGTH = 64
0040 MAX_ENTITY_LENGTH = 120
0041 _SEMANTIC_FIELDS = frozenset(
0042     {
0043         "subject", "content_type", "intent", "response_mode", "entity",
0044         "retrieval_concepts", "confidence",
0045     }
0046 )
0047 _JSON_FENCE_RE = re.compile(r"\A```(?:json)?\s*\n(?P<body>.*)\n```\s*\Z", re.DOTALL)
0048
0049
0050 @dataclass(frozen=True, slots=True)
0051 class StudyInputSemantics:
0052     subject: Subject
0053     content_type: str
0054     intent: str
0055     response_mode: ResponseMode
0056     entity: str
0057     retrieval_concepts: tuple[str, ...]
0058     confidence: float
0059
0060
0061 def _mapping_from_payload(payload: object) -> Mapping[str, object] | None:
0062     if isinstance(payload, Mapping):
0063         return payload
0064     if not isinstance(payload, str):
0065         return None
0066     raw = payload.strip()
0067     fenced = _JSON_FENCE_RE.fullmatch(raw)
0068     if fenced is not None:
0069         raw = fenced.group("body").strip()
0070     try:
0071         decoded = json.loads(raw)
0072     except (TypeError, ValueError, json.JSONDecodeError):
0073         return None
0074     return decoded if isinstance(decoded, Mapping) else None
0075
0076
0077 def _bounded_text(value: object, *, limit: int, allow_empty: bool) -> str | None:
0078     if not isinstance(value, str):
0079         return None
0080     normalized = value.strip()
0081     if (not normalized and not allow_empty) or len(normalized) > limit:
0082         return None
0083     return normalized
0084
0085
0086 def parse_study_input_semantics(payload: object) -> StudyInputSemantics | None:
0087     """Validate a semantic-routing result without accepting graph node claims."""
0088     values = _mapping_from_payload(payload)
0089     if values is None or frozenset(values) != _SEMANTIC_FIELDS:
0090         return None
0091     subject_value = values.get("subject")
0092     if not isinstance(subject_value, str):
0093         return None
0094     subject = subject_value.strip().lower()
0095     if subject not in ALLOWED_SUBJECTS:
0096         return None
0097     content_type = _bounded_text(
0098         values.get("content_type"), limit=MAX_CLASSIFICATION_LENGTH, allow_empty=False
0099     )
0100     intent = _bounded_text(
0101         values.get("intent"), limit=MAX_CLASSIFICATION_LENGTH, allow_empty=False
0102     )
0103     response_mode_value = values.get("response_mode")
0104     if not isinstance(response_mode_value, str):
0105         return None
0106     response_mode = response_mode_value.strip().lower()
0107     if response_mode not in RESPONSE_MODES:
0108         return None
0109     entity = _bounded_text(values.get("entity"), limit=MAX_ENTITY_LENGTH, allow_empty=True)
0110     if content_type is None or intent is None or entity is None:
0111         return None
0112     raw_concepts = values.get("retrieval_concepts")
0113     if not isinstance(raw_concepts, (list, tuple)) or len(raw_concepts) > MAX_RETRIEVAL_CONCEPTS:
0114         return None
0115     concepts: list[str] = []
0116     for item in raw_concepts:
0117         concept = _bounded_text(item, limit=MAX_RETRIEVAL_CONCEPT_LENGTH, allow_empty=False)
0118         if concept is None:
0119             return None
0120         if concept not in concepts:
0121             concepts.append(concept)
0122     if subject == "unknown" and concepts:
0123         return None
0124     confidence_value = values.get("confidence")
0125     if isinstance(confidence_value, bool) or not isinstance(confidence_value, (int, float)):
0126         return None
0127     confidence = float(confidence_value)
0128     if not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
0129         return None
0130     return StudyInputSemantics(
0131         subject=cast(Subject, subject),
0132         content_type=content_type,
0133         intent=intent,
0134         response_mode=cast(ResponseMode, response_mode),
0135         entity=entity,
0136         retrieval_concepts=tuple(concepts),
0137         confidence=confidence,
0138     )
0139
0140
0141 def build_semantic_routing_messages(
0142     *, text: str, language: str, has_images: bool = False
0143 ) -> list[dict[str, str]]:
0144     """Build a classification-only prompt; image bytes are attached by the caller."""
0145     schema = {
0146         "subject": sorted(ALLOWED_SUBJECTS),
0147         "content_type": "string, max 64 chars",
0148         "intent": "string, max 64 chars",
0149         "response_mode": sorted(RESPONSE_MODES),
0150         "entity": "string, max 120 chars; empty when absent",
0151         "retrieval_concepts": "array of up to 6 strings, each max 64 chars",
0152         "confidence": "number from 0 to 1",
0153     }
0154     request = {
0155         "language": str(language or "").strip() or "unknown",
0156         "image_present": bool(has_images),
0157         "study_input": str(text or "").strip(),
0158         "response_schema": schema,
0159     }
0160     system = (
0161         "You route study inputs by their complete semantic meaning, discussion "
0162         "object, and task intent. Never choose a subject from keyword overlap alone. "
0163         "Return exactly one JSON object matching the supplied schema. Do not answer "
0164         "the study question, explain your classification, or reveal chain of thought. "
0165         "retrieval_concepts must contain only short concepts for searching the local "
0166         "knowledge graph. Never return graph node IDs or claim that any graph node "
0167         "was matched. When the subject cannot be determined reliably, set subject to "
0168         "unknown and retrieval_concepts to an empty array."
0169         " Classify response_mode from the complete request: use problem_solving only "
0170         "for a concrete calculation, proof, option judgement, verification, or exercise; "
0171         "use general_explanation for explaining a concept or mechanism; use "
0172         "general_discussion for discussing a work, person, event, viewpoint, or value "
0173         "judgement. The same literary work can be general_discussion when discussing "
0174         "its meaning and problem_solving when answering a specific exam question. "
0175         "When task intent is uncertain, set response_mode to unknown."
0176     )
0177     return [
0178         {"role": "system", "content": system},
0179         {
0180             "role": "user",
0181             "content": json.dumps(request, ensure_ascii=False, separators=(",", ": ")),
0182         },
0183     ]
0184
0185
0186 __all__ = [
0187     "ALLOWED_SUBJECTS", "KNOWLEDGE_GUIDANCE_STATUSES", "KnowledgeGuidanceStatus",
0188     "RESPONSE_MODES", "ResponseMode", "StudyInputSemantics", "Subject", "build_semantic_routing_messages",
0189     "parse_study_input_semantics",
0190 ]
```
