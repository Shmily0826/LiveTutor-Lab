"""Offline guard for the code-grounded tool's boundaries. No network, no model, no devices.

What has to hold, and what each check below pins:

* a sibling copy of the same repository never reaches the model - including the source
  lines inside its block, which carry no path of their own;
* a credential-named path is dropped, and a credential-shaped *line* is redacted rather
  than removed silently, so the tutor can say it withheld something;
* nothing is sent when no project is authorized, and the CLI is never handed a shell
  string - only an argument list with one of five fixed sub-commands.
"""
import asyncio
import importlib.util
import json
import re
import sys
import tempfile
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAYLOAD = Path(__file__).with_name("payload") / "study_companion"

for name in ("plugin", "plugin.sdk", "plugin.sdk.plugin"):
    if name not in sys.modules:
        stub = types.ModuleType(name)
        stub.llm_tool = lambda **kwargs: (lambda func: func)
        sys.modules[name] = stub

spec = importlib.util.spec_from_file_location("study_code_tools", PAYLOAD / "study_code_tools.py")
code_tools = importlib.util.module_from_spec(spec)
spec.loader.exec_module(code_tools)

AUTHORIZED = {"root": r"D:\project\Sky Scout\sky_scout", "prefix": "sky_scout/",
              "name": "sky_scout", "commit": "cc40962"}

CLI_OUTPUT = "\n".join([
    "**Exploration: how does location change update the sky map**",
    "",
    "**Blast radius**",
    "- `LocationMapPage` (sky_scout/app_sky_scout/lib/features/location/location_map.dart:15)",
    "- `SkyMapPage` (sky_scout/app_sky_scout/lib/features/sky_map/sky_map_page.dart:31)",
    "- `LocationMapPage` (sky_scout_web_integrated/app_sky_scout/lib/features/location/location_map.dart:15)",
    "- save: 3 callers in sky_scout/app_sky_scout/lib/a.dart, sky_scout_web_latest/app_sky_scout/lib/b.dart",
    "",
    "**`sky_scout/app_sky_scout/lib/features/location/location_map.dart`**",
    "```dart",
    "12\timport '../../data/services/location_geocoding.dart';",
    "13\timport 'package:flutter/material.dart';",
    "14\t",
    "111\t  Future<void> _confirm() async {",
    "112\t    final n = Colors.white.withOpacity(0.5);",
    "117\t    await LocationStorage.save(location);",
    "123\t    Navigator.pushAndRemoveUntil(route, (route) => false);",
    "124\t  }",
    "```",
    "",
    "**`sky_scout_remote_install/app_sky_scout/lib/features/location/location_map.dart`**",
    "```dart",
    "Future<void> _confirm() async {",
    "  // a different copy, on a different commit",
    "}",
    "```",
    "",
    "**`sky_scout/app_sky_scout/lib/data/services/api_keys.dart`**",
    "```dart",
    "const apiKey = 'sk-abcdefghijklmnopqrstuvwx';",
    "const bearer = 'Bearer abcdefghijklmnopqrst';",
    "```",
    "",
    "**`sky_scout/.env`**",
    "```",
    "DATABASE_PASSWORD=sup3rs3cr3t",
    "```",
])

TREE_OUTPUT = json.dumps([
    {"path": "sky_scout/lib/main.dart", "language": "dart", "nodeCount": 4, "size": 812},
    {"path": "sky_scout/lib/app.dart", "language": "dart", "nodeCount": 9, "size": 1200},
    {"path": "sky_scout/pubspec.yaml", "language": "yaml", "nodeCount": 0, "size": 900},
    {"path": "sky_scout/lib/features/location/location_map.dart", "language": "dart",
     "nodeCount": 31, "size": 5000},
    {"path": "sky_scout/lib/features/location/location_storage.dart", "language": "dart",
     "nodeCount": 12, "size": 1400},
    {"path": "sky_scout/lib/features/sky_map/sky_map_page.dart", "language": "dart",
     "nodeCount": 24, "size": 4100},
    {"path": "sky_scout/lib/data/services/location_geocoding.dart", "language": "dart",
     "nodeCount": 9, "size": 900},
    {"path": "sky_scout/.env", "language": "dotenv", "nodeCount": 0, "size": 60},
    {"path": "sky_scout_web_integrated/lib/main.dart", "language": "dart",
     "nodeCount": 3, "size": 700},
])

checks: dict[str, object] = {}


class Host(code_tools._StudyCodeToolsMixin):
    def __init__(self, authorization: dict | None = None) -> None:
        self.authorization = authorization
        self.data_dir = Path(tempfile.mkdtemp(prefix="neko-code-guard-"))
        self.log: list[str] = []

    def data_path(self, name: str) -> str:
        return str(self.data_dir / name) if name else str(self.data_dir)

    class _Logger:
        def info(self, message):  # noqa: ANN001 - matches the plugin logger surface
            print(f"  log: {message[:120]}")

        def warning(self, message):  # the SDK logger has both; the receipt path uses warning
            print(f"  warn: {message[:120]}")

    logger = _Logger()


kept, stats = Host()._code_filter(CLI_OUTPUT, AUTHORIZED)
evidence = "\n".join(kept)

checks["sibling_paths_never_survive"] = "sky_scout_web_integrated" not in evidence \
    and "sky_scout_remote_install" not in evidence
# the code lines under the sibling header carry no path of their own; they must go with it
checks["sibling_block_body_dropped"] = "a different copy, on a different commit" not in evidence
checks["authorized_source_kept"] = "LocationStorage.save" in evidence and "pushAndRemoveUntil" in evidence
# The real reason an earlier version dropped whole authorized files: Dart's own syntax is full
# of things that look like paths. These three must survive inside a block.
checks["member_chains_and_import_specs_are_not_paths"] = (
    "../../data/services/location_geocoding.dart" in evidence
    and "package:flutter/material.dart" in evidence
    and "Colors.white.withOpacity(0.5)" in evidence)
# impact/blast-radius rows name our file and a copy in the same breath: keep the row, blank the copy.
checks["mixed_row_scrubbed_not_dropped"] = (
    code_tools._WITHHELD in evidence and "sky_scout_web_latest" not in evidence
    and "sky_scout/app_sky_scout/lib/a.dart" in evidence)
checks["credential_line_redacted_not_sent"] = "sk-abcdefghijklmnopqrstuvwx" not in evidence \
    and "sup3rs3cr3t" not in evidence and "[redacted:" in evidence
checks["env_path_dropped"] = ".env" not in evidence
checks["leak_net_stops_a_sibling_that_slipped_through"] = bool(
    Host()._code_leak(["- see sky_scout_remote_install/app_sky_scout/lib/x.dart:4"], AUTHORIZED))
checks["stats_counted"] = stats["dropped_outside_root"] >= 2 and stats["dropped_denied_path"] >= 1 \
    and stats["redacted"] >= 1 and stats["kept_lines"] > 0

empty = Host()
try:
    refusal = asyncio.run(empty.study_code_tool(query="anything"))
except Exception as error:  # data_path points at nothing, so the authorization lookup must fail soft
    refusal = {"error": f"raised {type(error).__name__}"}
checks["no_authorization_refuses_without_reading"] = refusal.get("error") == "NO_AUTHORIZED_PROJECT"

imported = Path(PAYLOAD / "study_code_tools.py").read_text(encoding="utf-8")
checks["no_shell_string_invocation"] = "shell=True" not in imported and "subprocess.run(command" in imported
checks["fixed_subcommands_only"] = set(code_tools._SUBCOMMANDS.values()) == {
    "explore", "node", "impact", "query", "files"}
checks["size_capped_before_leaving_the_machine"] = "_MAX_CHARS" in imported and stats["chars"] <= 12000

receipted = Host()
shown = code_tools._shown(kept, AUTHORIZED["root"], AUTHORIZED["prefix"])
receipted._code_receipt("explore", "how does location reach the sky map", AUTHORIZED, stats,
                        evidence, shown)
written = (receipted.data_dir / "code_evidence.jsonl").read_text(encoding="utf-8").strip()
receipt = json.loads(written)
# Boundary 3 is only auditable if the product keeps its own record of what it handed the model.
checks["receipt_records_what_left_the_machine"] = (
    receipt["evidence"] == evidence and receipt["filtered"] == stats
    and receipt["prefix"] == "sky_scout/" and receipt["mode"] == "explore"
    and receipt["commit"] == "cc40962" and receipt["chars"] == len(evidence))
checks["receipt_carries_no_sibling_path"] = "sky_scout_web_integrated" not in written \
    and "sky_scout_remote_install" not in written

refused = Host()
asyncio.run(refused.study_code_tool(query="anything"))
checks["refusal_writes_no_receipt_and_reads_nothing"] = not (
    refused.data_dir / "code_evidence.jsonl").exists()

checks["shown_lists_only_the_lines_it_was_given"] = shown == [
    {"file": "sky_scout/app_sky_scout/lib/features/location/location_map.dart",
     "lines": [12, 13, 14, 15, 111, 112, 117, 123, 124]},
    {"file": "sky_scout/app_sky_scout/lib/features/sky_map/sky_map_page.dart", "lines": [31]},
]


class FakeStore:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def append_interaction(self, **kwargs) -> bool:
        self.rows.append(kwargs)
        return True


async def _full_run() -> tuple[dict, FakeStore, list, list[str], dict]:
    import subprocess

    host = Host(AUTHORIZED)
    host._store = FakeStore()
    host._study_session_id = "study-guard"
    host._cfg = types.SimpleNamespace(history_limit=50)
    host._state = types.SimpleNamespace(session_summary_seed={})
    host._code_authorization = lambda: AUTHORIZED
    host._code_cli = lambda: ["codegraph"]
    calls: list[list[str]] = []
    stdout = {"text": CLI_OUTPUT, "fixable": False, "tree": TREE_OUTPUT}
    head = {"commit": "cc40962"}
    original = code_tools._run
    BARREN = "Search Results:\n\nNo results found for that sentence.\n"

    async def fake_run(command, timeout=None):
        calls.append(list(command))
        if command[0] == "git":
            return subprocess.CompletedProcess(command, 0, stdout=head["commit"] + "\n", stderr="")
        if command[1] == "sync":
            # A forced re-sync is what makes a just-added file visible; mirror that, because the
            # retry path is only worth having if it actually finds the thing.
            if stdout["fixable"]:
                stdout["text"], stdout["fixable"] = CLI_OUTPUT, False
            return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")
        assert command[1] in ("explore", "query", "node", "impact", "files"), command
        if command[1] == "files":
            return subprocess.CompletedProcess(command, 0, stdout=stdout["tree"], stderr="")
        return subprocess.CompletedProcess(command, 0, stdout=stdout["text"], stderr="")

    code_tools._run = fake_run
    try:
        result = await host.study_code_tool(mode="explore", query="how does it work")
        again = await host.study_code_tool(mode="find", query="LocationStorage")
        stdout["text"], stdout["fixable"] = BARREN, True
        recovered = await host.study_code_tool(mode="find", query="a sentence about the map")
        stdout["text"], stdout["fixable"] = BARREN, False
        still_missing = await host.study_code_tool(mode="find", query="a sentence about the map")
        stdout["text"] = CLI_OUTPUT
        head["commit"] = "7aae20f"          # the team branch moved during the session
        moved = await host.study_code_tool(mode="explore", query="and now?")
        structure = await host.study_code_tool(mode="structure")
    finally:
        code_tools._run = original
    return result, host._store, calls, [again, recovered, still_missing, moved, structure], dict(
        host._state.session_summary_seed)


ran, store, calls, extra, seed = asyncio.run(_full_run())
empty, moved_call = extra[2], extra[3]
row = (store.rows or [{}])[0]
raw_source = (PAYLOAD / "study_code_tools.py").read_text(encoding="utf-8")
# The rules live in adjacent string literals, so rejoin them the way Python does before
# looking for them - otherwise this guard would be testing where a line was wrapped.
code_source = re.sub(r'"\s*\n\s*"', "", raw_source)
sync_calls = [c for c in calls if len(c) > 1 and c[1] == "sync"]
query_calls = [c for c in calls if c[0] == "codegraph" and len(c) > 1 and c[1] != "sync"]
checks["index_is_synced_before_the_question"] = (
    calls.index(sync_calls[0]) < calls.index(query_calls[0])
    and query_calls[0][:3] == ["codegraph", "explore", "how does it work"]
    and ran.get("index_sync") == "synced")
checks["sync_is_throttled_not_repeated_per_turn"] = (
    len(sync_calls) == 3 and extra[0].get("index_sync") == "throttled")
checks["empty_after_throttle_forces_one_resync_and_retries"] = (
    extra[1].get("index_sync") == "synced-after-empty" and extra[1].get("shown") == shown
    and sync_calls[1] == sync_calls[0])
checks["a_real_miss_says_so_instead_of_blaming_the_mode"] = (
    empty.get("shown") == [] and "re-synced just for this question" in str(empty.get("note")))
checks["empty_result_points_at_the_wrong_mode"] = (
    extra[0].get("shown") and "lines 12-124" in str(ran.get("note")))
checks["moved_result_names_the_revision_it_read"] = (
    moved_call.get("repo_commit") == "7aae20f"
    and "has moved since the learner authorized it" in str(moved_call.get("note"))
    and "cc40962 -> 7aae20f" in str(moved_call.get("note"))
    and ran.get("repo_commit") == "cc40962"
    and "has moved since" not in str(ran.get("note")))
checks["description_routes_sentences_to_explore"] = (
    "only accept an exact name" in code_source and "Sending a sentence to symbol/find returns"
    in code_source and "mode='explore' is the default for a reason" in code_source)
checks["tool_returns_the_shown_ranges"] = ran.get("shown") == shown and "lines 12-124" in str(
    ran.get("note"))
# The sentence that started this: "we read that earlier" about a line never handed over.
checks["note_forbids_claiming_to_have_read_more"] = (
    "never tell the learner you had already read" in code_source
    and "something already read ('we saw earlier'" in code_source)
tree_call = [c for c in calls if c[0] == "codegraph" and c[1] == "files"]
tree = extra[4]
checks["structure_asks_the_indexer_not_a_directory_walk"] = (
    tree_call == [["codegraph", "files", "--path", AUTHORIZED["root"], "-j"]]
    and tree.get("mode") == "files"
    and "sky_scout/lib/features/location - 2 files, 43 indexed symbols" in str(tree.get("evidence"))
    and "sky_scout/lib/main.dart" in str(tree.get("evidence")))
# The learner asked for the layout, not for a re-index: the tree is answered from the index the
# earlier questions already synced, and it must not spend a forced resync of its own.
checks["the_file_tree_question_reuses_the_throttled_index"] = (
    tree.get("index_sync") == "throttled"
    and calls.index(tree_call[0]) > max(i for i, call in enumerate(calls) if call[1] == "sync"))
# Folding the list must not become a second, weaker filter: a bare directory name is not a
# file-shaped token, so the line filter lets a sibling copy through untouched. The fold filters
# by the authorized prefix itself, and this is the check that says so.
checks["structure_evidence_never_names_a_sibling_copy"] = (
    "sky_scout_web_integrated" not in json.dumps(tree, ensure_ascii=False, default=str)
    and ".env" not in str(tree.get("evidence")))
# A tree has no line numbers. If this mode can be made to sound like a read file, the tutor will
# cite a line nobody opened, which is the failure this project has already paid for once.
checks["structure_refuses_to_fake_line_numbers"] = (
    tree.get("shown") == [] and "no line numbers" in str(tree.get("note"))
    and "take the learner into the material" in str(tree.get("note")))
checks["code_question_lands_in_the_study_history"] = (
    len(store.rows) == 6 and row.get("kind") == "code_question"
    and row.get("session_id") == "study-guard"
    and "sky_scout@cc40962" in str(row.get("input_text"))
    and "location_map.dart:12-124" in str(row.get("output_text"))
    and row.get("metadata", {}).get("shown") == shown)
checks["history_row_carries_no_sibling_path"] = all(
    marker not in json.dumps(store.rows, ensure_ascii=False, default=str)
    for marker in ("sky_scout_web_integrated", "sky_scout_remote_install"))
# The session summary prompt is told to read its numbers out of `session_summary_seed`,
# which no code question used to touch: a session spent entirely inside the learner's own
# project summarised itself as having never happened.
checks["code_questions_reach_the_summary_seed"] = (
    int(seed.get("code_question_count") or 0) == len(store.rows) > 0
    and seed.get("last_code_project") == AUTHORIZED["name"]
    and seed.get("last_code_commit") in ("cc40962", "7aae20f"))
# Counting them twice - once as a code question, once as a gateway operation - would make
# the summary's own numbers wrong.
checks["gateway_operation_counts_keep_their_meaning"] = all(
    key not in seed for key in ("event_count", "question_count", "answer_count",
                                "explain_count", "last_operation"))

failures = {k: v for k, v in checks.items() if v is not True}
if failures:
    print(f"FAIL: {failures}")
    raise SystemExit(1)
print("PASS: sibling copies and their source bodies dropped, credential-shaped lines redacted, "
      f"authorized source kept (kept={stats['kept_lines']} dropped={stats['dropped_outside_root']} "
      f"denied={stats['dropped_denied_path']} redacted={stats['redacted']}); "
      "argv-only CLI with five fixed sub-commands; no authorization means no read.")
