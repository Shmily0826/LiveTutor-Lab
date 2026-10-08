import { createHash } from "node:crypto";
import { readFileSync, writeFileSync } from "node:fs";

const roots = [
  "benchmarks/raw/neko-app/resources/bin/plugin/plugins/study_companion",
  "benchmarks/raw/neko-app/resources/bin/plugins/study_companion",
  "benchmarks/raw/goal-isolated/study_companion",
];
const sharedFiles = [
  "models.py",
  "store_schema.py",
  "store.py",
  "store_qa.py",
  "entry_tutor_context_support.py",
  "entry_tutor_summary_entries.py",
  "entry_tutor_answer_entries.py",
  "entry_document_analysis_jobs.py",
  "prompt_templates.py",
  "tutor_llm_agent_answer_evaluate.py",
  "_event_bus.py",
  "entry_neko_commands.py",
];
const digest = (path) =>
  createHash("sha256").update(readFileSync(path)).digest("hex");
const checks = [];

for (const file of sharedFiles) {
  const hashes = roots.map((root) => digest(root + "/" + file));
  checks.push({
    check: "three_copy_identical:" + file,
    pass: hashes.every((hash) => hash === hashes[0]),
    sha256: hashes[0],
  });
}

const runtimeSources = [
  "benchmarks/raw/neko-app/resources/bin/plugin/plugins/study_companion/__init__.py",
  "benchmarks/raw/neko-app/resources/bin/plugin/plugins/study_companion/lab_entry.py",
  "benchmarks/raw/neko-app/resources/bin/plugins/study_companion/__init__.py",
  "benchmarks/raw/goal-isolated/study_companion/__init__.py",
];
const runtimeRoles = [
  "LIVE configured package entry",
  "LIVE split compatibility entry",
  "BRIDGE module entry",
  "goal-isolated module entry",
];
for (const path of runtimeSources) {
  const index = runtimeSources.indexOf(path);
  const source = readFileSync(path, "utf8");
  checks.push({
    check: "persistent_silence_gate:" + path,
    pass:
      source.includes("communication.silent_mode") &&
      source.includes("not self._cfg.communication.silent_mode"),
  });
  checks.push({
    check: "session_lifecycle:" + path,
    pass:
      source.includes("_start_study_session") &&
      source.includes("_end_study_session") &&
      source.includes("_study_session_lock = asyncio.Lock()") &&
      source.includes("_start_study_idle_task") &&
      source.includes("_run_study_session_idle_loop") &&
      source.includes("close_open_sessions") &&
      source.indexOf("self._store.load_state") < source.indexOf("self._store.close_open_sessions") &&
      source.includes("30 * 60"),
  });
  checks.push({
    check: "silence_blocks_awareness_push:" + path,
    pass: source.includes("if self._cfg.communication.silent_mode:\n            return\n        mode = self._cfg.awareness.push_to_llm_mode"),
  });
  checks.push({
    check: "event_bus_is_configured_fail_closed:" + path,
    pass:
      source.includes("StudyEventBus(") &&
      source.includes("silent_mode=self._cfg.communication.silent_mode") &&
      source.includes("self._cfg.communication.enabled") &&
      source.includes("and not self._cfg.communication.silent_mode"),
  });
}

const support = readFileSync(
  roots[0] + "/entry_tutor_context_support.py",
  "utf8",
);
checks.push({
  check: "scoped_session_history_and_topic_inference",
  pass:
    support.includes("session_id=session_id") &&
    support.includes("computer_science"),
});
const sessions = readFileSync(roots[0] + "/store_qa.py", "utf8");
checks.push({
  check: "restart_preserves_legacy_sessions",
  pass:
    sessions.includes("len(session_key) != 38") &&
    sessions.includes("char not in \"0123456789abcdef\"") &&
    sessions.includes("WHERE ended_at IS NULL AND id = ?"),
});
const schema = readFileSync(roots[0] + "/store_schema.py", "utf8");
checks.push({
  check: "session_id_schema_change_is_additive_nullable",
  pass:
    schema.includes('"interactions", "session_id", "TEXT"') &&
    !schema.includes("UPDATE interactions SET session_id"),
});
const sessionRuntime = readFileSync(runtimeSources[0], "utf8");
checks.push({
  check: "session_start_end_rollover_serialized",
  pass:
    sessionRuntime.includes("self._study_session_lock = asyncio.Lock()") &&
    sessionRuntime.includes("async with self._study_session_lock:") &&
    sessionRuntime.includes("_start_study_session_locked") &&
    sessionRuntime.includes("_end_study_session_locked") &&
    sessionRuntime.includes("async def _restart_study_session"),
});
const contextSupport = readFileSync(roots[0] + "/entry_tutor_context_support.py", "utf8");
checks.push({
  check: "request_session_id_reaches_both_persistence_paths",
  pass:
    contextSupport.includes('request_session_id = str((extra_context or {}).get("session_id") or "").strip()') &&
    contextSupport.includes("session_id=request_session_id") &&
    contextSupport.includes('session_id = str(context.get("session_id") or "").strip()') &&
    !contextSupport.includes("or self._study_session_id"),
});
const answerEntry = readFileSync(roots[0] + "/entry_tutor_answer_entries.py", "utf8");
const documentEntry = readFileSync(roots[0] + "/entry_document_analysis_jobs.py", "utf8");
checks.push({
  check: "answer_and_document_requests_pin_session_before_persistence",
  pass:
    answerEntry.includes("if not session_id:\n            session_id = await self._ensure_active_study_session()") &&
    answerEntry.includes("session_id=session_id") &&
    documentEntry.includes('runner_state["session_id"] = await self._ensure_active_study_session()') &&
    documentEntry.includes('extra_context={"session_id": runner_state["session_id"]}'),
});
const eventBus = readFileSync(roots[0] + "/_event_bus.py", "utf8");
checks.push({
  check: "event_bus_output_has_fail_closed_gate",
  pass:
    eventBus.includes("silent_mode: bool = True") &&
    eventBus.includes("if self._silent_mode:\n            self._block_count += 1\n            return"),
});
const commandOutput = readFileSync(roots[0] + "/entry_neko_commands.py", "utf8");
checks.push({
  check: "direct_command_output_has_silence_gate",
  pass:
    commandOutput.includes("getattr(communication, \"silent_mode\", True)") &&
    commandOutput.includes("self.ctx.push_message("),
});
const pluginToml = readFileSync(roots[0] + "/plugin.toml", "utf8");
checks.push({
  check: "silent_mode_is_persisted_in_source_config",
  pass: /\[study_companion\.communication\][\s\S]*?silent_mode\s*=\s*true/.test(pluginToml),
});
const liveBootstrap = readFileSync(
  "benchmarks/raw/neko-app/resources/bin/plugin/plugins/study_companion/lab_bootstrap_plane.py",
  "utf8",
);
checks.push({
  check: "LIVE_config_entry_resolves_package_init_class",
  pass:
    pluginToml.includes('entry = "plugins.study_companion.lab_bootstrap_plane:StudyCompanionPlugin"') &&
    liveBootstrap.includes("from . import StudyCompanionPlugin"),
});

const grader = readFileSync(
  roots[0] + "/tutor_llm_agent_answer_evaluate.py",
  "utf8",
);
const missingPointBranch = grader.match(
  /if missing_points and verdict == "correct":[\s\S]*?(?=\n    [a-zA-Z_][\w]* =|\n    return \{)/,
  )?.[0] ?? "";
const wrongMechanismBranch = grader.match(
  /if verdict == "wrong" and misconceptions and not covered_points:[\s\S]*?(?=\n    [a-zA-Z_][\w]* =|\n    return \{)/,
  )?.[0] ?? "";
checks.push({
  check: "grade_missing_points_and_wrong_mechanism_caps_are_separately_scoped",
  pass:
    missingPointBranch.includes('verdict = "partial"') &&
    missingPointBranch.includes("score = min(score, 80)") &&
    wrongMechanismBranch.includes("score = min(score, 10)"),
});

const evidence = {
  evidence_kind: "STATIC_SOURCE_CHECK",
  runtime_roots: runtimeSources.map((path, index) => ({
    path,
    entry_role: runtimeRoles[index],
    sha256: digest(path),
  })),
  runtime_exercised: false,
  tts_requests_observed: 0,
  meaning:
    "This check made no provider or runtime requests; it does not prove runtime silence.",
  checks,
};
writeFileSync(
  "benchmarks/raw/evidence/neko-goal-static-source-check.json",
  JSON.stringify(evidence, null, 2) + "\n",
);
console.log(JSON.stringify({ all_pass: checks.every((item) => item.pass), checks }, null, 2));
if (checks.some((item) => !item.pass)) process.exitCode = 1;
