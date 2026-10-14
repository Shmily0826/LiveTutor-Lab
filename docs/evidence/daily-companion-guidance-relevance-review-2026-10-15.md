# Phase 30 — topic guidance relevance review

Status: **SOURCE / OFFLINE PASS for the bounded regression**, with no concrete P1/P2 found in the reviewed change. Independently read canonical `knowledge_graph_guidance.py`, the relevant `_build_knowledge_guidance_context` / outcome / publication code in `entry_tutor_context_support.py`, and the existing `test_knowledge_topic_routing.py`. No implementation, manifest, shared records, deployment, DB or budget was changed; no host/provider/audio/device was started.

## Reviewed behavior

The query tokenizer excludes a single CJK character extracted from a longer normalized query while retaining an actual single-character query. This removes the observed generic `从` fragment mechanism without disabling a legitimate exact topic such as `力`. Full topic names and aliases are compared against the original query with ASCII identifier boundaries; a source identifier `BFSx` cannot establish the alias `BFS`.

Public fuzzy ranking remains available: partial label, alias or search-text overlap can still have a nonzero total score and matched_terms. That ranking is deliberately distinct from `topic_specific_score`. Specific credit now comes from a complete supported name/alias/ID or a complete Latin label/alias word present in the original query, preserving the existing “图的 BFS 与 DFS” query. A generic extracted fragment no longer becomes specific evidence merely because it appeared among the explicit query terms. This is lexical relevance evidence, not a semantic theorem about every graph topic.

The non-explain automatic route now filters query matches by specific score >=10, before constructing guidance. When none qualify it returns empty guidance and a not_matched outcome. Outcome fields leave applied false, focus empty and related topics empty; the context/publication paths attach guidance only when its summary is matched. Thus the reviewed weak-query path does not leak a merely ranked topic into teaching metadata or the model payload.

For a qualifying automatic match, the caller passes its confirmed exact ID into `build_knowledge_guidance_payload`; the graph and subgraph therefore retain that focus rather than repeating an unrestricted query-only selection. The directly relevant existing graph-index callee was inspected narrowly: `KnowledgeGraphIndex.match` delegates to `match_topics`, and `build_relevant_subgraph` forwards that exact ID; an existing exact ID returns its single focus match. Related graph nodes/edges still follow the existing bounded graph traversal; this review does not declare every stored curriculum relation pedagogically correct.

Explicit learner-selected IDs retain the existing earlier branch, load/selection behavior and selected_topic source. The specific-score threshold is for automatic inference, not a new refusal to honor the learner's explicit selection. Summary and knowledge-track operations retain not_applicable behavior. Explain routing retains its existing semantic confidence/subject restrictions plus specific-score guard.

## Independent existing offline regression

Command: `.\benchmarks\raw\neko-product-host\.venv\Scripts\python.exe -X utf8 -B patches/neko-study-2026-10-10-product/test_knowledge_topic_routing.py`.

Result: `PASS_TOPIC_SPECIFIC_KNOWLEDGE_ROUTING`, exit0, elapsed approximately 1.51 s, **820 cross-subject seed topics loaded**, provider_calls=0, live_ui_retested=False. This is one existing assertion-based script, not 820 separately validated curriculum topics or a live model run.

The suite uses the actual canonical matcher/build methods, the existing seed JSON and historical round5 transcript fixture, with an offline supplied semantic classifier / cached-store fixture. It covers:

- Same-subject generic Flutter/dependency/state overlap rejected despite public fuzzy scores.
- Actual scene41 arrow query and generic `连接`, `从`, `input output boundary conditions` rejected on both answer and question paths, with no guidance.
- Full Chinese topic labels, complete English alias, `BFS` within its real label and explicit selected-topic behavior preserved.
- Confirmed topic equals subgraph's focus, preventing the reviewed second-selection regression.
- `BFS` versus `BFSx` boundary and exact `力` versus unrelated `能力培养`.

No previously passed phase29 language or phase28 voice batch was repeated. Main's reported prior reproduction of scene41's grammar-topic mismatch is separate historical evidence; this offline regression does not replace the forthcoming actual SDK/model check or retrospectively fix its original record. Main owns that bounded real text verification and any deployment after its own SHA guard.

## Frozen fingerprints and limits

- `knowledge_graph_guidance.py`: `31b103c512eca8c5ac2eeea8d50db6c63cb213ab74e81bf0ae43421192420f89`.
- `entry_tutor_context_support.py`: `08280ce2e8bf0077cce36b7764f9aef30b00c3c4818dba152f44509c2b512446`.
- `test_knowledge_topic_routing.py`: `70582bbe42347582125413926cb84df726b642417b4eae4838b070c3bb679b7a`.

The seed corpus and baseline graph-index code are readonly fixture dependencies, not modified source. The test does not establish universal multilingual relevance, every alias, concurrent index refresh, model compliance or physical/human experience. Source/offline review frozen.

## Scene44 original — independent readonly real-result review

Independently read Main's terminal original private `daily-companion-20261015-guidance44.json`; SHA256 `f4ec30fc5bea8926e76809e66658e2c49043e76e0a1a183f3d78cba88ecc19ba`. No JSON, DB or implementation was modified, no derived artifact was created, and no test/model/host/device scene was repeated.

All **10 recorded checks are literally True**. Independently compared their key source fields: grade output has guidance_applied=False, status=not_matched, empty focus and related list, source=query_match, and no knowledge_guidance payload. Exactly one new QA and formal answer record is added (**4→5**); every original four QA and formal hash is unchanged. Course and remembered course-English map are exactly unchanged. The artifact is finalized and has no failure entry; absent cleanup_errors is None, not a new cleanup success receipt. Main reports harness exit0, while the separate child host_exit field is1; these are distinct process fields.

**Narrow automatic-guidance chain: real SDK/model evidence passes for this recorded query.** It no longer injects the unrelated English grammar topic. The returned wrong/0 feedback correctly says WEX→NUD answers a different arrow from requested NUD→REZ; misconceptions correctly distinguish incoming versus outgoing.

**Overall teaching semantics remain PARTIAL.** A step_feedback sentence still concludes the two arrows' start/end are exactly reversed. They are adjacent different edges, not the same two endpoints in reverse order. Correct visible feedback does not excuse the contradictory diagnosis in a secondary field. The model has therefore not consistently complied with rule4b across all fields. Structural checks and absence of unwanted graph guidance cannot establish full semantic acceptance.

**Language scope remains unverified for this direct entry.** The returned natural-language fields are Chinese while the stored course map says English. This scene did not first use the same explicit set-course path as42, so persistence of the map does not prove that direct entry has applied it to output. This review does not infer provider randomness, change the mapping, or count this as phase29 language acceptance.

The new record also chooses a third topic identity (course-scoped `有向关系图中的起点与终点`), distinct from the preserved earlier `有向关系` / `directed relations` records. That is a separate confirmed C continuity gap, investigated in `daily-companion-concept-identity-investigation-2026-10-15.md`; the guidance fix does not repair identity merely by preserving hashes. The original record remains unchanged and is not relabelled a global PASS.

The artifact explicitly records audio/avatar/microphone/capture/loopback=False. This is a silent SDK/model observation, not Native playback, device listening or human acceptance. Scene44 review frozen with the source/offline conclusions above preserved.
