from __future__ import annotations

from .store_common import (
    Any,
    uuid,
    _DEFAULT_APPEND_ONLY_HISTORY_LIMIT,
    safe_float,
    safe_int,
)


def concept_label_candidates(self, *, course_id: str, label: str) -> list[str]:
    """At most two canonical IDs, from exact known names/aliases with provenance.

    A question-scoped identity must not become a concept just because its display
    label happens to match. No fuzzy translation or whole QA bodies are read.
    """
    if not isinstance(label, str) or not label.strip() or not course_id:
        return []
    course = str(course_id).strip()
    prefix = course + "::"
    rows = self._require_read_conn().execute(
        """
        SELECT DISTINCT CASE WHEN substr(t.id, 1, length(?)) = ?
                             THEN t.id ELSE ? || t.id END AS topic_id
        FROM topics t
        WHERE (t.name = ? COLLATE BINARY OR EXISTS (
            SELECT 1 FROM json_each(CASE WHEN json_valid(t.aliases)
                THEN CASE WHEN json_type(t.aliases) = 'array' THEN t.aliases ELSE '[]' END
                ELSE '[]' END) a WHERE a.type = 'text' AND a.value = ? COLLATE BINARY
        )) AND (
            (substr(t.id, 1, length(?)) = ? AND EXISTS (
                SELECT 1 FROM qa_records q JOIN sessions s ON s.id = q.session_id
                WHERE q.topic_id = t.id AND s.course_id = ?
                AND json_extract(CASE WHEN json_valid(q.question) THEN q.question ELSE '{}' END,
                    '$.internal_private_payload.learning_topic_binding.scope') = 'concept'
            )) OR (t.source = 'seed' AND COALESCE(t.course_family, '') IN ('', ?)
                AND (instr(t.id, '::') = 0
                     OR substr(t.id, 1, length(t.subject || '::')) = t.subject || '::'))
        ) ORDER BY topic_id LIMIT 2
        """,
        (prefix, prefix, prefix, label.strip(), label.strip(), prefix, prefix, course, course),
    ).fetchall()
    return [str(row['topic_id']) for row in rows]


def ensure_session(self, *, session_id: str, mode: str, course_id: str = "") -> None:
    session_key = str(session_id or "default")
    with self._lock:
        self._require_conn().execute(
            """
            INSERT INTO sessions (id, mode, started_at, topics_touched, course_id)
            VALUES (?, ?, datetime('now'), '[]', ?)
            ON CONFLICT(id) DO NOTHING
            """,
            (session_key, str(mode or "companion"), str(course_id or "").strip()),
        )
        self._require_conn().commit()


def end_session(self, *, session_id: str, summary: str = "") -> None:
    session_key = str(session_id or "").strip()
    if not session_key:
        return
    with self._lock:
        conn = self._require_conn()
        conn.execute(
            "UPDATE sessions SET ended_at = COALESCE(ended_at, datetime('now')), "
            "duration_minutes = MAX(0, (julianday(COALESCE(ended_at, datetime('now'))) - julianday(started_at)) * 1440), "
            "summary_markdown = COALESCE(NULLIF(?, ''), summary_markdown) WHERE id = ?",
            (str(summary or "").strip(), session_key),
        )
        conn.commit()


def close_open_sessions(self, session_id: str) -> None:
    session_key = str(session_id or "").strip()
    if (
        len(session_key) != 38
        or not session_key.startswith("study-")
        or any(char not in "0123456789abcdef" for char in session_key[6:])
    ):
        return
    with self._lock:
        self._require_conn().execute(
            "UPDATE sessions SET ended_at = datetime('now'), "
            "duration_minutes = MAX(0, (julianday('now') - julianday(started_at)) * 1440) "
            "WHERE ended_at IS NULL AND id = ?",
            (session_key,),
        )
        self._require_conn().commit()


def list_sessions(self, limit: int = 100) -> list[dict[str, Any]]:
    rows = (
        self._require_read_conn()
        .execute(
            """
            SELECT *
            FROM sessions
            ORDER BY started_at DESC, id DESC
            LIMIT ?
            """,
            (max(1, int(limit)),),
        )
        .fetchall()
    )
    return [
        {
            "id": str(row["id"]),
            "mode": str(row["mode"] or ""),
            "course_id": str(row["course_id"] or ""),
            "started_at": str(row["started_at"] or ""),
            "ended_at": str(row["ended_at"] or ""),
            "duration_minutes": safe_float(row["duration_minutes"], 0.0),
            "question_count": safe_int(row["question_count"], 0),
            "topics_touched": self._json_loads(row["topics_touched"], []),
            "summary_markdown": str(row["summary_markdown"] or ""),
            "notes_exported": bool(row["notes_exported"]),
        }
        for row in rows
    ]


def add_qa_record(
    self,
    *,
    session_id: str,
    topic_id: str,
    question: dict[str, Any],
    user_answer: str,
    eval_result: dict[str, Any],
    mode: str,
    response_time_ms: int | None = None,
    history_limit: int = _DEFAULT_APPEND_ONLY_HISTORY_LIMIT,
) -> None:
    session_key = str(session_id or "default")
    topic_key = str(topic_id or "").strip()
    db_topic_key = topic_key or None
    with self._lock:
        conn = self._require_conn()
        conn.execute(
            """
            INSERT INTO qa_records (
                session_id, topic_id, question, user_answer,
                eval_result, mode, response_time_ms, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """,
            (
                session_key,
                db_topic_key,
                self._json_dumps(question or {}),
                str(user_answer or ""),
                self._json_dumps(eval_result or {}),
                str(mode or "companion"),
                int(response_time_ms) if response_time_ms is not None else None,
            ),
        )
        row = conn.execute(
            "SELECT topics_touched FROM sessions WHERE id = ?", (session_key,)
        ).fetchone()
        touched = self._json_loads(row["topics_touched"], []) if row is not None else []
        if topic_key and topic_key not in touched:
            touched.append(topic_key)
        conn.execute(
            """
            UPDATE sessions
            SET question_count = question_count + 1, topics_touched = ?
            WHERE id = ?
            """,
            (self._json_dumps(touched), session_key),
        )
        self._trim_append_only_rows(
            conn,
            table="qa_records",
            group_column="topic_id",
            group_value=db_topic_key,
            history_limit=history_limit,
        )
        conn.commit()


def list_qa_records(self, limit: int = 100, *, course_id: str = "") -> list[dict[str, Any]]:
    course_key = str(course_id or "").strip()
    where = " WHERE session_id IN (SELECT id FROM sessions WHERE course_id = ?)" if course_key else ""
    params = (course_key, max(1, int(limit))) if course_key else (max(1, int(limit)),)
    rows = (
        self._require_read_conn()
        .execute(
            "SELECT * FROM qa_records" + where + " ORDER BY id DESC LIMIT ?",
            params,
        )
        .fetchall()
    )
    return [
        item
        for item in (self._qa_record_from_row(row) for row in reversed(rows))
        if item is not None
    ]


def list_qa_topic_ids(self, *, course_id: str) -> list[str]:
    rows = self._require_read_conn().execute(
        """SELECT DISTINCT topic_id FROM qa_records
           WHERE session_id IN (SELECT id FROM sessions WHERE course_id = ?)
             AND topic_id IS NOT NULL AND topic_id <> '' ORDER BY topic_id LIMIT 5000""",
        (str(course_id or "").strip(),),
    ).fetchall()
    return [str(row[0]) for row in rows]


def list_qa_records_for_topic(
    self, topic_id: str, limit: int = 10, *, course_id: str = "", mistakes_only: bool = False,
    question_id: str = "", binding_key: str = "",
) -> list[dict[str, Any]]:
    topic_key = str(topic_id or "").strip()
    safe_limit = max(1, int(limit))
    if topic_key:
        query = """
            SELECT *
            FROM qa_records
            WHERE topic_id = ?
            ORDER BY id DESC
            LIMIT ?
            """
        params: tuple[Any, ...] = (topic_key, safe_limit)
    else:
        query = """
            SELECT *
            FROM qa_records
            WHERE topic_id IS NULL
            ORDER BY id DESC
            LIMIT ?
            """
        params = (safe_limit,)
    conditions, extra = [], []
    if str(course_id or "").strip():
        conditions.append("session_id IN (SELECT id FROM sessions WHERE course_id = ?)")
        extra.append(str(course_id).strip())
    if mistakes_only:
        conditions.append("json_extract(CASE WHEN json_valid(eval_result) THEN eval_result ELSE '{}' END, '$.verdict') IN ('wrong', 'partial', 'dont_know')")
    for key, value in (("question_id", question_id),
                       ("internal_private_payload.learning_topic_binding.key", binding_key)):
        if value:
            conditions.append("json_extract(CASE WHEN json_valid(question) THEN question ELSE '{}' END, '$." + key + "') = ?")
            extra.append(str(value))
    if conditions:
        query = query.replace("ORDER BY id DESC", "AND " + " AND ".join(conditions) + " ORDER BY id DESC")
        params = (*params[:-1], *extra, params[-1])
    rows = self._require_read_conn().execute(query, params).fetchall()
    return [
        item
        for item in (self._qa_record_from_row(row) for row in reversed(rows))
        if item is not None
    ]


def question_topic_candidates(
    self, *, course_id: str, question: str, expected_answer: str,
    question_id: str = "", material_identity: str = "", binding_key: str = "",
    allow_legacy: bool = False,
) -> list[str]:
    """At most two distinct identities: two proves ambiguity, not recency preference."""
    prefix = course_id + "::"
    rows = self._require_read_conn().execute(
        """WITH candidates AS (
            SELECT topic_id, CASE WHEN json_valid(question) THEN question ELSE '{}' END AS artifact
            FROM qa_records WHERE session_id IN (SELECT id FROM sessions WHERE course_id = ?)
        ) SELECT DISTINCT topic_id FROM candidates
        WHERE substr(topic_id, 1, length(?)) = ?
          AND json_extract(artifact, '$.question') = ?
          AND COALESCE(json_extract(artifact, '$.answer'), '') = ?
          AND (json_extract(artifact, '$.internal_private_payload.learning_topic_binding.key') = ?
               OR (? AND json_extract(artifact, '$.internal_private_payload.learning_topic_binding') IS NULL
                   AND COALESCE(json_extract(artifact, '$.question_id'), '') = ?
                   AND COALESCE(json_extract(artifact, '$.internal_private_payload.source_material_context.course_id'), ?) = ?
                   AND COALESCE(json_extract(artifact, '$.internal_private_payload.source_material_context.material_identity'), '') = ?))
        LIMIT 2""",
        (course_id, prefix, prefix, question, expected_answer, binding_key,
         int(allow_legacy), question_id, course_id, course_id, material_identity),
    ).fetchall()
    return [str(row[0]) for row in rows]


def add_wrong_question(
    self,
    *,
    topic_id: str,
    question: dict[str, Any],
    user_answer: str,
    expected_answer: str,
    error_type: str,
    verdict: str,
) -> str:
    question_id = str(uuid.uuid4())
    with self._lock:
        self._require_conn().execute(
            """
            INSERT INTO wrong_questions (
                id, topic_id, question, user_answer, expected_answer,
                error_type, verdict, status, retry_count, consecutive_correct,
                max_correct_difficulty, last_error_at, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 'active', 0, 0, 0, datetime('now'), datetime('now'), datetime('now'))
            """,
            (
                question_id,
                str(topic_id or ""),
                self._json_dumps(question or {}),
                str(user_answer or ""),
                str(expected_answer or ""),
                str(error_type or "unknown"),
                str(verdict or "wrong"),
            ),
        )
        self._require_conn().commit()
    return question_id


def get_retry_wrong_question(self, topic_id: str) -> dict[str, Any] | None:
    rows = self.list_wrong_questions(
        limit=1, topic_id=topic_id, statuses=("active", "retrying")
    )
    return rows[0] if rows else None


def list_wrong_questions(
    self,
    *,
    limit: int = 20,
    topic_id: str | None = None,
    topic_ids: list[str] | set[str] | tuple[str, ...] | None = None,
    statuses: tuple[str, ...] = ("active", "retrying", "resolved"),
) -> list[dict[str, Any]]:
    status_values = tuple(str(item) for item in statuses if str(item))
    if not status_values:
        status_values = ("active", "retrying", "resolved")
    status_json = self._json_dumps(list(status_values))
    safe_limit = max(1, int(limit))
    topic_key = str(topic_id or "").strip()
    topic_keys = list(
        dict.fromkeys(str(item or "").strip() for item in (topic_ids or ()))
    )
    topic_keys = [item for item in topic_keys if item]
    if topic_ids is not None and not topic_key and not topic_keys:
        return []
    if topic_key:
        query = """
            SELECT *
            FROM wrong_questions
            WHERE status IN (SELECT value FROM json_each(?))
                AND topic_id = ?
            ORDER BY
                CASE WHEN status = 'retrying' THEN 1 ELSE 0 END DESC,
                last_retry_at DESC,
                created_at DESC,
                id DESC
            LIMIT ?
            """
        params: tuple[Any, ...] = (status_json, topic_key, safe_limit)
    elif topic_ids is not None:
        query = """
            SELECT *
            FROM wrong_questions
            WHERE status IN (SELECT value FROM json_each(?))
                AND topic_id IN (SELECT value FROM json_each(?))
            ORDER BY
                CASE WHEN status = 'retrying' THEN 1 ELSE 0 END DESC,
                last_retry_at DESC,
                created_at DESC,
                id DESC
            LIMIT ?
            """
        params = (
            status_json,
            self._json_dumps(topic_keys),
            safe_limit,
        )
    else:
        query = """
            SELECT *
            FROM wrong_questions
            WHERE status IN (SELECT value FROM json_each(?))
            ORDER BY
                CASE WHEN status = 'retrying' THEN 1 ELSE 0 END DESC,
                last_retry_at DESC,
                created_at DESC,
                id DESC
            LIMIT ?
            """
        params = (status_json, safe_limit)
    rows = self._require_read_conn().execute(query, params).fetchall()
    return [self._wrong_question_from_row(row) for row in rows]


def mark_wrong_question_resolved(self, question_id: str) -> None:
    with self._lock:
        self._require_conn().execute(
            """
            UPDATE wrong_questions
            SET status = 'resolved', resolved_at = datetime('now'), updated_at = datetime('now')
            WHERE id = ?
            """,
            (str(question_id or ""),),
        )
        self._require_conn().commit()


def record_wrong_question_correct(
    self, *, topic_id: str, error_type: str, difficulty: int
) -> None:
    with self._lock:
        rows = (
            self._require_conn()
            .execute(
                """
            SELECT *
            FROM wrong_questions
            WHERE topic_id = ? AND status IN ('active', 'retrying')
            ORDER BY
                CASE WHEN status = 'retrying' THEN 0 ELSE 1 END,
                last_retry_at DESC,
                created_at DESC,
                id DESC
            LIMIT 5
            """,
                (str(topic_id or ""),),
            )
            .fetchall()
        )
        matched_generic_correct = False
        current_error_type = str(error_type or "none").strip()
        processed_error_types: set[str] = set()
        for row in rows:
            if current_error_type in {"", "none"}:
                if matched_generic_correct:
                    continue
                matched_generic_correct = True
                row_error_type = str(row["error_type"] or "")
            else:
                row_error_type = str(row["error_type"] or "")
                if current_error_type != row_error_type:
                    continue
            if row_error_type in processed_error_types:
                continue
            consecutive = int(row["consecutive_correct"] or 0) + 1
            max_difficulty = max(
                int(row["max_correct_difficulty"] or 0), int(difficulty or 0)
            )
            old_enough = bool(
                self._require_conn()
                .execute(
                    "SELECT (julianday('now') - julianday(?)) >= 1.0 AS ok",
                    (str(row["last_error_at"] or ""),),
                )
                .fetchone()["ok"]
            )
            status = "retrying"
            if consecutive >= 3 and max_difficulty >= 3 and old_enough:
                status = "resolved"
            if status == "resolved":
                self._require_conn().execute(
                    """
                    UPDATE wrong_questions
                    SET status = 'resolved',
                        retry_count = retry_count + 1,
                        consecutive_correct = ?,
                        max_correct_difficulty = ?,
                        last_retry_at = datetime('now'),
                        resolved_at = datetime('now'),
                        updated_at = datetime('now')
                    WHERE id = ?
                    """,
                    (consecutive, max_difficulty, str(row["id"])),
                )
            else:
                self._require_conn().execute(
                    """
                    UPDATE wrong_questions
                    SET status = ?,
                        retry_count = retry_count + 1,
                        consecutive_correct = ?,
                        max_correct_difficulty = ?,
                        last_retry_at = datetime('now'),
                        updated_at = datetime('now')
                    WHERE id = ?
                    """,
                    (status, consecutive, max_difficulty, str(row["id"])),
                )
            processed_error_types.add(row_error_type)
        self._require_conn().commit()
