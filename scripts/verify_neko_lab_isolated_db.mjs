import assert from "node:assert/strict";
import { DatabaseSync } from "node:sqlite";
import { readFileSync, writeFileSync, mkdirSync, rmSync, rmdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const sourceRoot = "benchmarks/raw/goal-isolated/study_companion";
const schemaSource = readFileSync(sourceRoot + "/store_schema.py", "utf8");
const qaSource = readFileSync(sourceRoot + "/store_qa.py", "utf8");
assert.ok(schemaSource.includes('self._ensure_column(conn, "interactions", "session_id", "TEXT")'));
assert.ok(qaSource.includes("question_count = question_count + 1"));
assert.ok(qaSource.includes("WHERE ended_at IS NULL AND id = ?"));

const tempDir = join(tmpdir(), `neko-goal-sqlite-${process.pid}-${Date.now()}`);
mkdirSync(tempDir, { recursive: false });
const dbPath = join(tempDir, "study.sqlite");
const db = new DatabaseSync(dbPath);
const checks = [];
try {
  db.exec(`
    CREATE TABLE sessions (
      id TEXT PRIMARY KEY, mode TEXT NOT NULL,
      started_at TEXT NOT NULL DEFAULT (datetime('now')),
      ended_at TEXT, duration_minutes REAL,
      question_count INTEGER DEFAULT 0,
      topics_touched TEXT NOT NULL DEFAULT '[]', summary_markdown TEXT,
      notes_exported INTEGER DEFAULT 0
    );
    CREATE TABLE interactions (
      id INTEGER PRIMARY KEY, kind TEXT NOT NULL, input_text TEXT NOT NULL,
      output_text TEXT NOT NULL, metadata TEXT NOT NULL, created_at REAL NOT NULL
    );
    CREATE TABLE qa_records (
      id INTEGER PRIMARY KEY, session_id TEXT NOT NULL, topic_id TEXT,
      question TEXT, user_answer TEXT, eval_result TEXT, mode TEXT,
      response_time_ms INTEGER, created_at TEXT
    );
    CREATE TABLE kv (key TEXT PRIMARY KEY, value TEXT NOT NULL);
    INSERT INTO sessions(id,mode) VALUES
      ('legacy-run-123','teaching'),
      ('study-legacy-123','teaching'),
      ('study-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb','teaching');
    INSERT INTO interactions(kind,input_text,output_text,metadata,created_at)
    VALUES('legacy','old question','old answer','{}',1.0);
  `);

  // Same additive, nullable migration as Store._init_db; no history backfill.
  db.exec("ALTER TABLE interactions ADD COLUMN session_id TEXT");
  const legacyInteraction = db.prepare("SELECT * FROM interactions WHERE kind='legacy'").get();
  assert.equal(legacyInteraction.input_text, "old question");
  assert.equal(legacyInteraction.output_text, "old answer");
  assert.equal(legacyInteraction.session_id, null);
  checks.push({ name: "old_schema_migration_preserves_history", pass: true });

  const activeId = "study-" + "a".repeat(32);
  db.prepare("INSERT INTO sessions(id,mode) VALUES(?, 'teaching')").run(activeId);
  const insertQA = db.prepare(`
    INSERT INTO qa_records (
      session_id, topic_id, question, user_answer,
      eval_result, mode, response_time_ms, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
  `);
  const updateQA = db.prepare(`
    UPDATE sessions
    SET question_count = question_count + 1, topics_touched = ?
    WHERE id = ?
  `);
  const updateActiveSession = db.prepare(
    "UPDATE sessions SET ended_at=datetime('now'), duration_minutes=0 WHERE ended_at IS NULL AND id = ?",
  );
  const listQA = db.prepare("SELECT session_id FROM qa_records ORDER BY id");
  const listSession = db.prepare("SELECT * FROM sessions WHERE id = ?");
  const topics = new Set();
  for (const answer of ["A1", "A2"]) {
    insertQA.run(activeId, "python_asyncio", "question", answer, "{}", "teaching", null);
    topics.add("python_asyncio");
    updateQA.run(JSON.stringify([...topics]), activeId);
  }
  const qaRows = listQA.all();
  assert.equal(qaRows.length, 2);
  assert.ok(qaRows.every((row) => row.session_id === activeId));
  assert.equal(listSession.get(activeId).question_count, 2);
  checks.push({ name: "multiple_answers_are_persisted_in_one_session", pass: true });

  // Recovery reads the exact active ID persisted by the plugin; no table scan.
  db.prepare("INSERT INTO kv(key,value) VALUES('state',?)").run(
    JSON.stringify({ study_session_id: activeId }),
  );
  db.close();
  const reopened = new DatabaseSync(dbPath);
  const recoveredState = JSON.parse(
    reopened.prepare("SELECT value FROM kv WHERE key='state'").get().value,
  );
  assert.equal(recoveredState.study_session_id, activeId);
  const recoveredSessionQuery = reopened.prepare("SELECT * FROM sessions WHERE id = ?");
  reopened.prepare(
    "UPDATE sessions SET ended_at=datetime('now'), duration_minutes=0 WHERE ended_at IS NULL AND id = ?",
  ).run(recoveredState.study_session_id);
  assert.ok(recoveredSessionQuery.get(activeId).ended_at);
  for (const historicalId of [
    "legacy-run-123",
    "study-legacy-123",
    "study-" + "b".repeat(32),
  ]) {
    assert.equal(recoveredSessionQuery.get(historicalId).ended_at, null);
  }
  reopened.close();
  checks.push({ name: "restart_closes_only_persisted_session_id", pass: true });

  const evidence = {
    evidence_kind: "ISOLATED_SQLITE_SQL_CONTRACT",
    database: "fresh temporary SQLite file; removed after assertions",
    executed_plugin_python: false,
    checks,
    limitation:
      "Python Store methods could not be invoked because the available uv-managed interpreter path is access-denied; this validates SQLite migration/query semantics, not Python runtime dispatch.",
  };
  writeFileSync(
    "benchmarks/raw/evidence/neko-goal-isolated-sqlite.json",
    JSON.stringify(evidence, null, 2) + "\n",
  );
  console.log(JSON.stringify({ all_pass: checks.every((check) => check.pass), checks }, null, 2));
} finally {
  try { db.close(); } catch {}
  rmSync(dbPath, { force: true });
  rmdirSync(tempDir);
}
