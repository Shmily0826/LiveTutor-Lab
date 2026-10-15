# Claude one-pass problem handoff (2026-10-15)

Review target: codex/daily-learning-companion; product baseline94a1f02. This handoff adds documentation only. Goal remains paused. Do not read the whole repository or history.

Read [routing.md](routing.md) first; [voice.md](voice.md) is the second independent problem. Each packet lists the necessary public files and embeds the otherwise missing local runtime snippets with provenance hashes. Answer both in one response if budget allows, prioritize routing timing if not. Give minimal actionable solutions; no repository-wide audit, no live calls, no microphone/audio operations. If information is still insufficient, separate a conditional plan from the exact runtime evidence only local execution can obtain. Do not ask the human to relay public source one file at a time.

## Why some files were unavailable

|Requested material|Actual status|
|---|---|
|tutor_llm_agent.py, study_materials.py|Already public in the product payload directory; previous narrowed read scope did not include all of them.|
|_semantic_routing.py|Base runtime dependency, not product overlay; relevant source snapshot included in routing.md.|
|utils/config_manager.py|Actual current implementation is a PACKAGE: utils/config_manager/quota.py; ignored local host source, included in routing.md.|
|Native _transport.py / _response_arbiter.py|Ignored local source host, not remotely tracked; relevant excerpts included in voice.md.|
|neko_phrase_input_transport.py / buffer / daily_voice_probe.py|Already public under scripts/ on the feature branch.|
|continuous51 raw JSON / WAV / SQLite|Deliberately untracked; bounded metadata-only historical projection included, no full private artifacts.|

Current source snapshots may postdate run51. A comment is not provider acknowledgment. No runtime reproduction or new acceptance was performed for this handoff. Never assume Claude can access the local machine or reconstruct unrecorded provider events.

Local runtime excerpts: Copyright2025-2026 Project N.E.K.O. Team; Apache License2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE). Paths and SHA hashes identify excerpt origins; excerpts are reference material, not an additional deployed code tree.
