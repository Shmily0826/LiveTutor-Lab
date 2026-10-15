"""Code-grounded teaching tools over the CodeGraph CLI.

One model-callable tool, four modes. The point of this file is not the wrapper - it is the
three boundaries that make a wrapper safe to hand to a teaching model:

* the CLI is only ever started as an argument list with a fixed sub-command, so a learner's
  question can never become shell;
* only evidence inside the learner-authorized root survives, which is what stops the
  neighbouring copies of the same project being cited as if they were the real one;
* credential-shaped content is removed by looking at the line, not the file name, because
  keys get pasted into ordinary source files.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import httpx
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from plugin.sdk.plugin import llm_tool
from .study_call_trace import current_call_id, phase

# A path is dropped if it names a credential store, or if it does not live under the
# authorized prefix. Sibling copies of the same repository fail the second test.
_DENIED_PATH = re.compile(
    r"(^|/)\.env(\.|$)|(^|/)(\.npmrc|\.pypirc|\.netrc|id_rsa\d*|authorized_keys|known_hosts)$|"
    r"(^|/)(secrets?|credentials?|\.aws|\.ssh|gcp-keys?)[/]|[-.](pem|p12|pfx|crt|key)$",
    re.I)
# Content check: names lie, pasted tokens do not.
_SECRET_CONTENT = re.compile(
    r"api[_-]?key|secret[_-]?token|access[_-]?token|auth[_-]?token|private[_-]?key|"
    r"pass(word|wd)\s*[:=]|BEGIN [A-Z ]*PRIVATE KEY|Bearer\s+\S{12,}|AKIA[0-9A-Z]{16}|"
    r"gh[pousr]_[A-Za-z0-9]{16,}|xox[baprs]-[A-Za-z0-9-]{10,}|sk-[A-Za-z0-9]{20,}",
    re.IGNORECASE)
# What CodeGraph prints for a location: parent-relative (`sky_scout/app_sky_scout/lib/x.dart:15`)
# or, on other platforms, absolute. Requiring a separator plus an extension is what keeps
# `Colors.withOpacity` and other Dart member chains out of this pattern entirely; the two
# exclusions in the relative branch keep `package:flutter/widgets.dart` and
# `../../data/x.dart` (an import spec, not a place on disk) from being read as paths.
_PATH_CLAIM = re.compile(
    r"(?P<absolute>[A-Za-z]:[/\\](?:[\w +-]*[/\\])*[\w +-]*\.[A-Za-z][A-Za-z0-9]{0,9})"
    r"|(?<![\w:./\\-])(?!\.\.?/)"
    r"(?P<relative>(?:[\w.+-]+[/\\]){1,}[\w.+-]*\.[A-Za-z][A-Za-z0-9]{0,9})(?::\d+)?")
_MAX_CHARS = 12000
_TIMEOUT_SECONDS = 120
# Measured on this machine with the CLI (not the MCP server, which has its own watcher):
# editing an already-indexed file is visible immediately, but a NEW file stays in
# `status -> Pending Changes: Added` and returns nothing until `sync`, which costs about a
# second. So one throttled sync per question is the cheap correct answer - no file watcher of
# our own, no resident daemon to babysit.
_SYNC_THROTTLE_SECONDS = 45.0
# A sync of the indexed parent cost 2-3 s per question once turns were more than the throttle
# apart; a stat walk of the authorized tree costs ~20 ms. Directories the index never serves
# are skipped so build output cannot force a sync.
_FINGERPRINT_SKIP_DIRS = frozenset({".git", "build", ".dart_tool", "node_modules"})
_SUBCOMMANDS = {"explore": "explore", "symbol": "node", "impact": "impact", "find": "query",
                # "这个项目结构什么样 / 模块怎么划分" was unanswerable: three questions on 2026-10-12
                # all came back `kept=6 shown_files=0`, because every mode here wants a symbol or a
                # sentence about behaviour, and none of them describes the shape of a repository.
                # The indexer already answers that - `codegraph files` prints the tree from the
                # same index, so no traversal and no new reader.
                "structure": "files", "file": "node"}
OURS, OUTSIDE, DENIED = "ours", "outside", "denied"
_WITHHELD = "[path outside the authorized project, withheld]"
_FENCED_LINE = re.compile(r"^\s*(\d+)\t")


def _slashes(text: str) -> str:
    return str(text).replace("\\", "/")


def _code_file_request(authorized, requested, offset, limit):
    """Validate before CLI reads; use its existing indexed file/window mode."""
    if type(offset) is not int or offset < 1 or type(limit) is not int or not 1 <= limit <= 120:
        raise ValueError("Use a positive original offset and a limit of 1 to 120 lines.")
    requested = _slashes(str(requested or "").strip())
    prefix = authorized["prefix"]
    if requested.casefold().startswith(prefix.casefold()):
        requested = requested[len(prefix):]
    if not requested or _DENIED_PATH.search(requested) or _DENIED_PATH.search(requested + "/"):
        raise ValueError("Choose an authorized source file, not a credential path.")
    root = Path(authorized["root"]).resolve(strict=True)
    lexical = Path(os.path.abspath(root / requested))
    if not lexical.is_relative_to(root):
        raise ValueError("The file path must stay inside the authorized project.")
    target = lexical.resolve(strict=True)
    if not target.is_relative_to(root) or not target.is_file():
        raise ValueError("The file must stay inside the authorized project, including symlinks.")
    relative = target.relative_to(root).as_posix()
    if _DENIED_PATH.search(relative) or _DENIED_PATH.search(relative + "/"):
        raise ValueError("Credential paths are excluded.")
    return prefix + relative


def _code_file_window(raw, index_file, offset, limit):
    """Only requested numbered rows; discard node's unrelated dependents/header paths."""
    if not raw.startswith(f"**{index_file}**"):
        return ""
    rows = []
    for index, line in enumerate(raw.splitlines()):
        if index and line.lstrip().startswith(("**", "#", "```")):
            break
        hit = _FENCED_LINE.match(line)
        if hit and offset <= int(hit.group(1)) < offset + limit:
            rows.append(line)
    if not rows:
        return ""
    return f"**`{index_file}`**\n```\n" + "\n".join(rows) + "\n```"


def _indexed_file_candidates(payload, authorized, requested, offset, limit):
    """Resolve a missing path from the existing index, never from a repository scan."""
    rows = json.loads(payload)
    if not isinstance(rows, list):
        raise ValueError("The index did not return a file list.")
    requested = _slashes(str(requested).strip())
    prefix = authorized["prefix"]
    if requested.casefold().startswith(prefix.casefold()):
        requested = requested[len(prefix):]
    suffix = "/" + requested.casefold()
    candidates = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        path = _slashes(str(row.get("path") or ""))
        if not path.casefold().startswith(prefix.casefold()) or not path.casefold().endswith(suffix):
            continue
        try:
            candidates.add(_code_file_request(authorized, path, offset, limit))
        except (ValueError, OSError):
            continue
    return sorted(candidates)


def _shown(kept: list[str], root: str, prefix: str) -> list[dict[str, Any]]:
    """Which files, and which line numbers of them, the evidence actually contains.

    The tutor once told a learner that `_confirm` was wired to a button "as we read earlier";
    the claim was true in the repository and false about what it had been shown, because the
    button line was never in the evidence. A model cannot police that sentence unless it is
    told where its own seeing ends, so the tool states it explicitly and the acceptance script
    can check citations against it.
    """
    files: dict[str, list[int]] = {}
    current = ""
    for line in kept:
        for span, verdict in _scan(line, root, prefix):
            if verdict != OURS:
                continue
            path = _slashes(span)
            hit = re.search(r":(\d+)$", path)
            if hit:
                path = path[:hit.start()]
                files.setdefault(path, []).append(int(hit.group(1)))
            if not hit:
                current = path
                files.setdefault(path, [])
        fenced = _FENCED_LINE.match(line)
        if fenced and current:
            files[current].append(int(fenced.group(1)))
    return [{"file": name, "lines": sorted(set(lines))}
            for name, lines in sorted(files.items()) if lines]


def _classify(claim: str, root: str, prefix: str) -> str:
    """Where one path-shaped claim points: inside the root, on a credential, or elsewhere.

    Anything that is not the authorized prefix is OUTSIDE by default - that is the direction
    the boundary needs, because the neighbouring copies of this project are exactly the
    "looks like a real path" case. A claim with no known prefix still counts as ours when the
    file really exists under the root, which is what keeps root-relative paths inside a
    source block from being read as a foreign copy.
    """
    path = re.sub(r":\d+$", "", _slashes(claim)).rstrip("/")
    if _DENIED_PATH.search(path) or _DENIED_PATH.search(path + "/"):
        return DENIED
    if path.casefold() == prefix.rstrip("/").casefold() or path.casefold().startswith(prefix.casefold()):
        return OURS
    if re.match(r"^[A-Za-z]:/", path) or path.startswith("/"):
        root_slashed = (_slashes(root).rstrip("/") + "/").casefold()
        return OURS if path.casefold().startswith(root_slashed) else OUTSIDE
    return OURS if Path(root, path).is_file() else OUTSIDE


def _scan(line: str, root: str, prefix: str) -> list[tuple[str, str]]:
    """Every location the line asserts, as (span, verdict), one pass so spans cannot overlap."""
    return [(match.group(0), _classify(match.group(0), root, prefix))
            for match in _PATH_CLAIM.finditer(line)]


def _scrub(line: str, pairs: list[tuple[str, str]]) -> str:
    """Blank out the foreign paths on a line worth keeping.

    `impact` prints rows that name the authorized file and a sibling copy in the same breath;
    dropping the row would throw away the relationship, keeping it would cite a copy the
    learner never authorized.
    """
    for span, verdict in pairs:
        if verdict != OURS:
            line = line.replace(span, _WITHHELD, 1)
    return line


def _siblings(root: str) -> list[str]:
    """Directory names next to the authorized root.

    Read only to prove a path is NOT one of them: the enumeration of copies is the whole
    point of boundary 2, and it must not be a hardcoded list that goes stale when the team
    checks out another one.
    """
    try:
        return [p.name for p in Path(root).parent.iterdir()
                if p.is_dir() and _slashes(p) != _slashes(root).rstrip("/")]
    except OSError:
        return []


def _structure_lines(payload: str, prefix: str) -> str:
    """The indexer's file list, folded into a shape instead of a listing.

    Raw it is 221 paths, which is the "只罗列文件名" answer the learner complained about; folded
    it is which folders hold how much code, plus the entry points the index recognises.

    The fold filters by the authorized prefix itself, before anything is assembled. Measured on
    this very change: a folder line like `sky_scout_web_integrated/lib - 1 files` passed the
    line-level filter untouched, because the filter looks for file-shaped tokens and a bare
    directory is not one. A sibling copy of the repository must not reach the model in any shape,
    including a tidy one.
    """
    try:
        rows = json.loads(payload)
    except ValueError:
        return ""
    if not isinstance(rows, list):
        return ""
    folders: dict[str, dict[str, int]] = {}
    tops: dict[str, int] = {}
    entries: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        path = _slashes(str(row.get("path") or "")).strip("/")
        if not path or not path.startswith(prefix):
            continue
        name = path.rsplit("/", 1)[-1]
        if name in {"main.dart", "app.dart", "pubspec.yaml", "index.ts", "main.py"}:
            entries.append(path)
        folder = "/".join(path.split("/")[:-1]) or path
        tally = folders.setdefault(folder, {"files": 0, "symbols": 0})
        tally["files"] += 1
        tally["symbols"] += int(row.get("nodeCount") or 0)
        rest = path[len(prefix):]
        top = prefix + rest.split("/", 1)[0] if "/" in rest else prefix.rstrip("/")
        tops[top] = tops.get(top, 0) + 1
    if not folders:
        return ""
    # The cap used to cut alphabetically, so a late top-level folder (here: server/) could vanish
    # while ten deep Flutter folders stayed, and the model then nested what it could not see.
    # Keep the shallowest folders, and say outright which folders sit directly under the project.
    shown = sorted(sorted(folders), key=lambda folder: folder.count("/"))[:40]
    lines = [f"{folder} - {folders[folder]['files']} files, {folders[folder]['symbols']} indexed symbols"
             for folder in sorted(shown)]
    lines.insert(0, "top-level entries of the project (siblings, none inside another): "
                 + ", ".join(f"{top} ({count} files)" for top, count in sorted(tops.items())))
    if entries:
        lines.insert(0, "entry points in the index: " + ", ".join(sorted(set(entries))[:5]))
    omitted = len(folders) - len(shown)
    lines.append(f"({len(folders)} folders of {sum(t['files'] for t in folders.values())} files"
                 + (f"; {omitted} deeper folders not listed" if omitted else "") + ")")
    return "\n".join(lines)


class _StudyCodeToolsMixin:
    """Ask CodeGraph about a project the learner authorized, with the filters applied."""

    def _code_authorization(self) -> dict[str, Any]:
        """The authorized project, as written by the native entry. Missing means no code access."""
        try:
            data = json.loads(Path(self.data_path("code_project.json")).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        if not isinstance(data, dict):
            return {}
        root = str(data.get("root") or "")
        prefix = str(data.get("evidence_prefix") or "").replace("\\", "/").strip("/")
        if not root or not Path(root).is_dir() or not prefix:
            return {}
        return {"root": root, "prefix": prefix + "/", "name": str(data.get("name") or ""),
                "commit": str(data.get("commit") or ""), "indexed_at": str(data.get("indexed_at") or "")}

    def _code_cli(self) -> list[str]:
        """How to start CodeGraph without a shell: an explicit path, or the npm shim."""
        override = os.environ.get("LIVETUTOR_CODEGRAPH", "").strip()
        if override:
            return [override]
        found = shutil.which("codegraph") or shutil.which("codegraph.cmd")
        return [found] if found else []

    def _code_filter(self, output: str, authorized: dict[str, Any]) -> tuple[list[str], dict[str, int]]:
        """Keep only the authorized tree's evidence, then redact and cap.

        A source block's code lines carry no path, so judging each line alone would let a
        sibling copy's source slip through under an authorized header. Ownership is therefore
        carried across a block: the path-bearing line that introduces it decides for every line
        until the fence closes. Outside a block the same test is applied line by line, because
        `query` and `impact` interleave the copies one row at a time.
        """
        root, prefix = authorized["root"], authorized["prefix"]
        stats = {"kept_lines": 0, "dropped_outside_root": 0, "dropped_denied_path": 0,
                 "dropped_block_lines": 0, "paths_scrubbed": 0, "redacted": 0, "chars": 0}
        kept: list[str] = []
        owner, inside = OURS, False
        for line in str(output or "").splitlines():
            fence = line.lstrip().startswith("```")
            pairs = _scan(line, root, prefix)
            if pairs:
                verdicts = [verdict for _, verdict in pairs]
                if OURS not in verdicts:
                    owner = DENIED if DENIED in verdicts else OUTSIDE
                    stats["dropped_denied_path" if owner == DENIED else "dropped_outside_root"] += 1
                    if fence:
                        inside = not inside
                    continue
                stats["paths_scrubbed"] += len([v for v in verdicts if v != OURS])
                line = _scrub(line, pairs)
                owner = OURS
            if owner is not OURS and (fence or inside):
                stats["dropped_block_lines"] += 1
                if fence:
                    inside = not inside
                continue
            if fence:
                inside = not inside
            if _SECRET_CONTENT.search(line):
                line = "[redacted: this line looked credential-shaped and was not sent]"
                stats["redacted"] += 1
            kept.append(line)
            stats["kept_lines"] += 1
            stats["chars"] += len(line) + 1
            if stats["chars"] >= _MAX_CHARS:
                break
        return kept, stats

    def _code_leak(self, kept: list[str], authorized: dict[str, Any]) -> str:
        """Re-read the filtered evidence for anything the boundary should have removed.

        The filter decides what goes to the model, so it gets audited by an independent pass
        over its own output rather than by its internal counters: a leftover path claim, or a
        sibling directory name, stops the request instead of being reported as filtered.
        """
        text = "\n".join(kept)
        for line in text.splitlines():
            for span, verdict in _scan(line, authorized["root"], authorized["prefix"]):
                if verdict != OURS:
                    return f"a path verdict of {verdict!r} survived in {line[:80]!r}"
        for name in _siblings(authorized["root"]):
            if name and re.search(rf"(?<![\w.-]){re.escape(name)}(?=[/\\])", text):
                return f"a sibling directory name ({name}) survived in the evidence"
        return ""

    def _code_receipt(self, sub: str, query: str, authorized: dict[str, Any],
                      stats: dict[str, int], evidence: str,
                      shown: list[dict[str, Any]], synced: str = "",
                      repo_commit: str = "") -> None:
        """Record exactly what the next model request will be shown.

        The filtered text otherwise disappears into TLS, where nobody on the learner's side can
        read it back; this file is what the acceptance checks against - the citations in the
        answer and the boundary claims both come from it.
        """
        record = {"at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                  "mode": sub, "query": query, "project": authorized["name"],
                  "commit": authorized["commit"], "prefix": authorized["prefix"],
                  "filtered": stats, "chars": len(evidence), "shown": shown,
                  "index_sync": synced, "repo_commit": repo_commit or authorized["commit"],
                  "evidence": evidence}
        try:
            path = Path(self.data_path("code_evidence.jsonl"))
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        except (OSError, TypeError, ValueError) as exc:
            log = getattr(self, "logger", None)
            if log is not None:
                log.warning(f"study_code receipt unwritable: {type(exc).__name__}: {str(exc)[:120]}")

    async def _code_record(self, sub: str, query: str, authorized: dict[str, Any],
                           shown: list[dict[str, Any]], stats: dict[str, int],
                           *, repo_commit: str = "") -> str:
        """Write the question into the learner's own study history.

        A code question used to leave no trace at all: the tool is not a gateway call, so the
        row every other study tool appends was never written, and after a restart nothing knew
        the learner had asked about their project. The answer itself is the character's, not
        this tool's, so the row records the question plus the exact files it was grounded in.
        """
        session_id = str(getattr(self, "_study_session_id", "")
                         or getattr(getattr(self, "_state", None), "study_session_id", "") or "")
        if not session_id:
            return ""
        citations = ", ".join(f"{item['file']}:{item['lines'][0]}-{item['lines'][-1]}"
                              for item in shown[:4]) or "no source lines returned"
        store = getattr(self, "_store", None)
        if store is None:
            return ""
        import asyncio
        evidence_commit = repo_commit or authorized["commit"]

        try:
            await asyncio.to_thread(
                store.append_interaction,
                kind="code_question",
                input_text=f"[{authorized['name']}@{evidence_commit}] {query}",
                output_text=f"Returned authorized source evidence: {citations}",
                metadata={"mode": sub, "project": authorized["name"],
                          "commit": evidence_commit, "authorized_commit": authorized["commit"], "shown": shown,
                          "evidence_chars": stats.get("chars", 0), "filtered": stats,
                          **({"call": current_call_id()} if current_call_id() else {})},
                session_id=session_id,
                history_limit=int(getattr(getattr(self, "_cfg", None), "history_limit", 50) or 50),
            )
        except Exception as exc:  # a missing history row must not cost the learner the answer
            log = getattr(self, "logger", None)
            if log is not None:
                log.warning(f"study_code history row failed: {type(exc).__name__}: {str(exc)[:120]}")
            return ""
        # The session summary prompt is told to take its numbers from this seed
        # ("use context.session_summary_seed for counts"), and a code question is not a
        # gateway operation, so nothing ever wrote into it: a whole session of reading
        # the learner's own project summarised itself as if it had never happened.
        # Only the dedicated keys move. `event_count` / `last_operation` keep meaning
        # "gateway operations", because every consumer of those two already reads them
        # with that definition and the summary would otherwise start counting twice.
        state = getattr(self, "_state", None)
        if state is not None:
            seed = dict(getattr(state, "session_summary_seed", None) or {})
            seed["code_question_count"] = int(seed.get("code_question_count") or 0) + 1
            seed["last_code_project"] = authorized["name"]
            seed["last_code_commit"] = evidence_commit
            state.session_summary_seed = seed
        return session_id

    async def _code_sync(self, cli: list[str], authorized: dict[str, Any],
                         force: bool = False) -> str:
        """Bring the index up to date before answering, at most once per throttle window.

        The answer is a short word for the receipt: `synced` / `throttled` / `failed:...`.
        Failing to sync never blocks a question - the previous index still answers it, and the
        learner is told the freshness state rather than the tool refusing to read.
        """
        import asyncio
        import time

        root = authorized["root"]
        seen = getattr(self, "_code_sync_at", None) or {}
        now = time.monotonic()
        if not force and now - float(seen.get(root, 0.0) or 0.0) < _SYNC_THROTTLE_SECONDS:
            return "throttled"
        self._code_sync_at = {**seen, root: now}
        # Skip the sync only when the tree is byte-for-byte the one the last successful sync
        # saw (paths, sizes, mtimes); an unreadable tree or saved state means sync as before.
        try:
            fingerprint = await asyncio.to_thread(_code_tree_fingerprint, root)
        except Exception:
            fingerprint = ""
        # Force bypasses throttling, not proof that the indexed tree is unchanged.
        if fingerprint and self._code_synced_fingerprint(root) == fingerprint:
            return "unchanged"
        try:
            done = await _run([*cli, "sync", str(Path(root).parent)], timeout=90)
        except Exception as exc:
            return f"failed:{type(exc).__name__}"
        code = getattr(done, "returncode", 1)
        if code != 0:
            return f"failed:exit_{code}"
        if fingerprint:
            self._remember_synced_fingerprint(root, fingerprint)
        return "synced"

    async def _code_inventory(self, cli: list[str], authorized: dict[str, Any]) -> str | int:
        """The indexed file list (stdout), or the CLI exit code on failure.

        Resolving a bare file name cost ~0.7 s per question. The listing is reused only while
        the authorized tree is byte-identical to when it was read and that tree has been
        synced, so a new same-name file still makes the next lookup ambiguous.
        """
        import asyncio

        root = authorized["root"]
        try:
            fingerprint = await asyncio.to_thread(_code_tree_fingerprint, root)
        except Exception:
            fingerprint = ""
        cached = (getattr(self, "_code_inventory_cache", None) or {}).get(root)
        if (fingerprint and cached and cached[0] == fingerprint
                and self._code_synced_fingerprint(root) == fingerprint):
            return cached[1]
        done = await _run([*cli, "files", "--path", root, "-j"])
        if done.returncode != 0:
            return done.returncode
        if fingerprint and self._code_synced_fingerprint(root) == fingerprint:
            self._code_inventory_cache = {**(getattr(self, "_code_inventory_cache", None) or {}),
                                          root: (fingerprint, done.stdout)}
        return done.stdout

    def _code_sync_state_path(self) -> Path | None:
        try:
            return Path(self.data_path("code_sync_state.json"))
        except Exception:
            return None

    def _code_synced_fingerprint(self, root: str) -> str:
        cached = (getattr(self, "_code_synced_fingerprints", None) or {}).get(root)
        if cached:
            return cached
        path = self._code_sync_state_path()
        try:
            data = json.loads(path.read_text(encoding="utf-8")) if path else {}
        except (OSError, ValueError):
            return ""
        return str(data.get(root) or "") if isinstance(data, dict) else ""

    def _remember_synced_fingerprint(self, root: str, fingerprint: str) -> None:
        self._code_synced_fingerprints = {**(getattr(self, "_code_synced_fingerprints", None) or {}),
                                          root: fingerprint}
        path = self._code_sync_state_path()
        if path is None:
            return
        try:
            temporary = path.with_name(path.name + ".tmp")
            temporary.write_text(json.dumps(self._code_synced_fingerprints), encoding="utf-8")
            os.replace(temporary, path)
        except OSError:
            pass  # Only the next launch pays one extra sync.

    async def _code_head(self, root: str) -> str:
        """The repository's current commit, for the one thing `sync` cannot say.

        Sync keeps the index in step with the files; it does not tell us that the team moved
        the branch under us since authorization. Line numbers are commit-scoped - `_confirm`
        sits at 111 in one revision and 113 in the next - so when HEAD has moved, the answer
        has to say which revision its line numbers belong to rather than imply they are
        permanent. Read-only, one subprocess, and never fatal.
        """
        import asyncio

        try:
            done = await _run(["git", "-C", root, "rev-parse", "--short", "HEAD"], timeout=20)
        except Exception:
            return ""
        return done.stdout.strip() if getattr(done, "returncode", 1) == 0 else ""

    @llm_tool(
        name="study_code",
        description=(
            "Answer a question about the learner's OWN project from its real source code, using "
            "the project index the learner authorized. Choose the mode by the SHAPE of the "
            "question: mode='explore' takes a whole sentence and is the one to use for 'where is "
            "X implemented', 'how does the data get from A to B', 'why is it done this way', "
            "'what would break if I changed X'. mode='symbol' and mode='impact' only accept an "
            "exact name the index can match, like 'LocationStorage::save' or '_confirm'; "
            "mode='find' wants a name fragment. mode='structure' takes no question at all and "
            "answers 'what is this project' or 'how is it divided' with the file tree from the "
            "same index - use it before explore when the learner asks about the shape of the "
            "codebase, and remember a tree carries no line numbers to cite. "
            "For any named file or original line, prefer mode='file' over explore/find/symbol, "
            "file='server/routes/weather.js', "
            "offset=1 and limit=40 (at most 120). It uses CodeGraph's existing file reader and "
            "returns only those source rows, avoiding a broad natural-query miss. A filename or "
            "path suffix is also accepted if unique in the authorized index; if ambiguous, choose "
            "the relevant returned candidate instead of guessing. "
            "Sending a sentence to symbol/find returns "
            "nothing - use explore instead. mode='explore' is the default for a reason. The index "
            "is synced before it answers (see index_sync), so code the learner just wrote is "
            "included. The answer must rest on the returned evidence: cite file path and symbol "
            "for anything you state as source fact, call anything not in the evidence an "
            "inference, and say what you could not confirm. The result also lists the exact line "
            "numbers it contains: those are the only lines you have read, so never tell the "
            "learner you had already read something outside that list, and mark any behaviour "
            "you describe from outside it as inference. Costs no model request of its own. If it "
            "reports no authorized project, ask the learner which directory to authorize instead "
            "of guessing."
        ),
        parameters={
            "type": "object",
            "properties": {
                "mode": {"type": "string", "enum": list(_SUBCOMMANDS), "default": "explore"},
                "query": {"type": "string",
                          "default": "", "description": "The question or exact symbol. Omit for structure; structure ignores this field."},
                "file": {"type": "string", "description": "For file mode: authorized root-relative/indexed path, or a unique filename/path suffix. Ambiguous names return candidates without source."},
                "offset": {"type": "integer", "minimum": 1, "default": 1},
                "limit": {"type": "integer", "minimum": 1, "maximum": 120, "default": 60},
            },
            "required": [],
        },
        timeout=180.0,
    )
    async def study_code_tool(self, *, mode: str = "explore", query: str = "", file: str = "",
                              offset: int = 1, limit: int = 60, **_):
        authorized = self._code_authorization()
        if not authorized:
            return {"ok": False, "error": "NO_AUTHORIZED_PROJECT",
                    "next": "Ask the learner which project directory to authorize; "
                            "nothing has been read."}
        cli = self._code_cli()
        if not cli:
            return {"ok": False, "error": "CODEGRAPH_NOT_FOUND",
                    "next": "CodeGraph CLI is not installed or not on PATH; say you cannot "
                            "read the project right now instead of guessing."}
        sub = _SUBCOMMANDS.get(str(mode or "explore").strip().lower())
        text = str(query or "").strip()
        # A file tree is the one question that needs no search terms: "what is in this project"
        # is answered by the index itself. Every other mode still refuses an empty query rather
        # than guessing what the learner meant.
        if not sub or (not text and sub != "files" and not (str(mode).strip().lower() == "file" and file)):
            return {"ok": False, "error": f"unsupported mode {mode!r}" if not sub else "query is empty"}
        index_file = ""
        resolve_file = False
        if str(mode).strip().lower() == "file":
            try:
                index_file = _code_file_request(authorized, file or text, offset, limit)
                text = index_file
            except FileNotFoundError:
                resolve_file = True
            except (ValueError, OSError) as error:
                return {"ok": False, "error": "INVALID_SOURCE_FILE_REQUEST", "detail": str(error)[:200]}
        with phase('index_sync'):
            synced = await self._code_sync(cli, authorized)
        with phase('source_revision'):
            head = await self._code_head(authorized["root"])
        if resolve_file:
            try:
                with phase('file_inventory'):
                    inventory_stdout = await self._code_inventory(cli, authorized)
                if not isinstance(inventory_stdout, str):
                    return {"ok": False, "error": f"CODEGRAPH_EXIT_{inventory_stdout}"}
                with phase('file_candidates'):
                    candidates = _indexed_file_candidates(inventory_stdout, authorized, file or text, offset, limit)
            except Exception as error:
                return {"ok": False, "error": "SOURCE_FILE_LOOKUP_FAILED", "detail": str(error)[:200]}
            if len(candidates) != 1:
                return {"ok": False, "error": "AMBIGUOUS_SOURCE_FILE" if candidates else "SOURCE_FILE_NOT_RESOLVED",
                        "candidates": candidates[:8], "candidate_count": len(candidates),
                        "index_sync": synced, "repo_commit": head or authorized["commit"],
                        "next": "Choose the relevant indexed path if listed. No source was returned; an unresolved name does not prove a file is absent."}
            index_file = text = candidates[0]
        command = ([*cli, sub, "--path", authorized["root"], "-j"]
                   if sub == "files"
                   else [*cli, sub, text, "--path", authorized["root"]])
        if sub == "explore":
            command += ["--max-files", "6"]
        if index_file:
            command = [*cli, "node", "--file", index_file, "--offset", str(offset), "--limit", str(limit), "--path", authorized["root"]]
        try:
            with phase('source_query'):
                done = await _run(command)
        except Exception as exc:
            return {"ok": False, "error": f"CODEGRAPH_FAILED: {type(exc).__name__}: {str(exc)[:180]}"}
        if done.returncode != 0:
            return {"ok": False, "error": f"CODEGRAPH_EXIT_{done.returncode}",
                    "detail": str(done.stderr or "")[:240]}
        raw = done.stdout
        if index_file:
            with phase('source_file_window'):
                raw = _code_file_window(raw, index_file, offset, limit)
            if not raw:
                return {"ok": False, "error": "SOURCE_WINDOW_UNAVAILABLE", "next": "The requested window was not returned by the index. Do not claim the file is absent; verify its indexed path or choose a shown symbol."}
        if sub == "files":
            with phase('source_structure'):
                raw = _structure_lines(done.stdout, authorized["prefix"])
            if not raw:
                return {"ok": False, "error": "STRUCTURE_UNREADABLE",
                        "next": "No usable authorized file entries were returned. Say the structure request failed; "
                                "this does not prove the project or a file is absent. Offer a specific source query."}
        with phase('source_filter'):
            kept, stats = self._code_filter(raw, authorized)
        with phase('source_leak'):
            leak = self._code_leak(kept, authorized)
        log = getattr(self, "logger", None)
        if leak:
            # Boundary 3: if the filter cannot be vouched for, the evidence stops here rather
            # than going out in the next model request.
            if log is not None:
                log.warning(f"study_code refused {sub} query={text[:70]!r} leak={leak[:160]}")
            return {"ok": False, "error": "EVIDENCE_FILTER_UNSURE",
                    "next": "Say that the project index returned evidence the read-only filter "
                            "could not safely keep; nothing was sent. Narrow the question."}
        with phase('source_evidence'):
            evidence = "\n".join(kept).strip()
        with phase('source_shown'):
            shown = _shown(kept, authorized["root"], authorized["prefix"])
            if index_file:
                numbers = sorted({int(hit.group(1)) for line in kept if (hit := _FENCED_LINE.match(line))
                                  and offset <= int(hit.group(1)) < offset + limit})
                shown = [{"file": index_file, "lines": numbers}] if numbers else []
        if sub != "files" and not index_file and not shown and synced in ("throttled", "unchanged"):
            # Measured: a file added seconds before a question stayed invisible behind the
            # throttle, and "not found" then reads like "does not exist". When the throttle is
            # the only thing standing between the question and an empty answer, spend one
            # unthrottled sync and ask once more - one extra second, no retry loop.
            # A file tree never qualifies: it has no line numbers to be missing, so the retry
            # would only burn a second indexer run and replace the folded shape with raw JSON.
            with phase('source_retry_sync'):
                forced = await self._code_sync(cli, authorized, force=True)
            if forced == "synced":
                try:
                    with phase('source_retry_query'):
                        retry = await _run(command)
                except Exception:
                    retry = None
                if retry is not None and retry.returncode == 0:
                    synced = "synced-after-empty"
                    with phase('source_retry_filter'):
                        kept, stats = self._code_filter(retry.stdout, authorized)
                    with phase('source_retry_leak'):
                        retry_leak = self._code_leak(kept, authorized)
                    if not retry_leak:
                        with phase('source_retry_evidence'):
                            evidence = "\n".join(kept).strip()
                        with phase('source_retry_shown'):
                            shown = _shown(kept, authorized["root"], authorized["prefix"])
        with phase('source_record'):
            self._code_receipt(sub, text, authorized, stats, evidence, shown, synced, head)
            await self._code_record(sub, text, authorized, shown, stats, repo_commit=head or authorized["commit"])
        if log is not None:
            # The acceptance has to prove the product asked, so record the call itself.
            log.info(f"study_code mode={sub} query={text[:70]!r} root={authorized['root']} "
                     f"kept={stats['kept_lines']} dropped={stats['dropped_outside_root']} "
                     f"denied={stats['dropped_denied_path']} redacted={stats['redacted']} "
                     f"shown_files={len(shown)} index_sync={synced}")
        if not evidence:
            return {"ok": True, "mode": sub, "index_sync": synced, "evidence": "",
                    "repo_commit": head or authorized["commit"],
                    "note": (f"Nothing inside the authorized project matched this {sub} query. Say "
                             "that plainly; do not describe files you were not shown. If the query "
                             "was a whole sentence, it was the wrong shape for this mode: ask again "
                             "with mode='explore'."),
                    "filtered": stats, "project": authorized["name"], "commit": authorized["commit"]}
        ranges = "; ".join(f"{item['file']} lines {item['lines'][0]}-{item['lines'][-1]}"
                           for item in shown[:6]) or "no numbered source lines"
        if sub == "files":
            # A tree has no line numbers, and pretending otherwise is how invented citations
            # get made. What this answer owes the learner is the shape, then one thread to study.
            barren = (" This is the repository's file tree, not source: it has no line numbers, "
                      "so do not cite any - describe the layout and what each part appears to "
                      "hold. Then take the learner into the material: pick one thread that runs "
                      "between two of these modules (for a Flutter app, how one feature feeds "
                      "another), say which files you would read to explain it, and offer that as "
                      "the next step. The tree shows folders, not calls: never state which module "
                      "calls or feeds which as a fact, only as something to read together. "
                      "Listing names and stopping is not teaching.")
        elif shown:
            barren = ""
        elif synced == "synced-after-empty":
            barren = (" The index was re-synced just for this question and still has nothing that "
                      "matches this query. That is not proof a file or symbol is absent. Say which "
                      "query failed, and narrow it to an exact name from a find result before concluding anything.")
        else:
            barren = (" This query returned no source lines at all - if you asked it "
                      "as a sentence, that shape does not work for this mode: ask "
                      "again with mode='explore'.")
        moved = ("" if not head or head == authorized["commit"] else
                 f" The repository has moved since the learner authorized it "
                 f"({authorized['commit']} -> {head}): these line numbers belong to {head}, "
                 "so mention the revision when you cite a line.")
        if sub == "query":
            barren += (" These are search matches, not function bodies. A returned file path is an indexed "
                       "entry, so do not claim the file is absent. Use an exact returned symbol with symbol/explore "
                       "to read the relevant body before explaining its lines.")
        barren += (" index_sync=throttled or unchanged only means a recent index refresh was reused or no "
                   "authorized file changed since the last one; source queries still run. "
                   "It is not a service limit or a reason to wait for recovery. For missing specific file lines, "
                   "use mode=file with the actual indexed file path and a small offset/limit.")
        with phase('source_surface'):
            surface = await _publish_code_surface(authorized["name"], head or authorized["commit"], evidence)
        return {"ok": True, "mode": sub, "project": authorized["name"], "commit": authorized["commit"],
                "learning_surface": surface,
                "repo_commit": head or authorized["commit"], "evidence": evidence,
                "filtered": stats, "shown": shown, "index_sync": synced,
                "note": (f"Filtered source evidence from the authorized project only. Shown: {ranges}. "
                         "Those line numbers are the whole of what was read for this question - not "
                         "another line of the same file, not another file. Cite path + symbol for source "
                         "facts; if you describe a call site, a widget, a button or a behaviour whose "
                         f"lines are not in that list, say you are inferring it, and never phrase it as "
                         f"something already read ('we saw earlier', 'as shown before').{barren}{moved}")}


async def _publish_code_surface(project, commit, evidence):
    base = os.environ.get("NEKO_LEARNING_SURFACE_URL", "")
    token = os.environ.get("NEKO_LEARNING_SURFACE_TOKEN", "")
    if not base or not token or not re.fullmatch(r"http://127\.0\.0\.1:\d+", base):
        return {"available": False}
    try:
        async with httpx.AsyncClient(timeout=5, trust_env=False) as client:
            response = await client.post(base + "/api/code-evidence", json={"project": project, "repo_commit": commit, "evidence": evidence},
                                         headers={"X-Learning-Surface-Token": token})
        return {"available": response.is_success, **response.json()}
    except (httpx.HTTPError, ValueError):
        return {"available": False, "reason": "learning_surface_unavailable"}


def _code_tree_fingerprint(root: str) -> str:
    import hashlib

    digest = hashlib.sha256()
    for directory, children, files in os.walk(root):
        children[:] = sorted(child for child in children if child not in _FINGERPRINT_SKIP_DIRS)
        for name in sorted(files):
            path = os.path.join(directory, name)
            try:
                stat = os.stat(path)
            except OSError:
                continue
            digest.update(f"{os.path.relpath(path, root)}\0{stat.st_size}\0{stat.st_mtime_ns}\n"
                          .encode("utf-8", "surrogatepass"))
    return digest.hexdigest()


async def _run(command: list[str], timeout: float = _TIMEOUT_SECONDS) -> subprocess.CompletedProcess:
    import asyncio

    return await asyncio.to_thread(
        lambda: subprocess.run(command, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=timeout))
