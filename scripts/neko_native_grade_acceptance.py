"""Readonly grading evidence snapshots and conservative report checks.

No services, models, devices or stdout. A passing report is a candidate for
semantic review, never proof of physical output, a provider ACK, or human use.
"""
from contextlib import closing
import hashlib
import json
import math
from pathlib import Path
import sqlite3

_PRIVATE = {'answer', 'accepted_answers', 'key_points', 'rubric', 'solution_steps',
            'internal_private_payload', 'current_question_private', 'answer_evaluation_cache',
            'attempt_evaluation_owner', 'attempt_evaluation_pending'}
_BLOCKED = {'navigator.mediaDevices.' + name for name in ('getUserMedia', 'getDisplayMedia', 'enumerateDevices')}
_BLOCKED |= {'navigator.' + name for name in ('getUserMedia', 'webkitGetUserMedia', 'mozGetUserMedia')}
_BLOCKED |= {'SpeechRecognition', 'webkitSpeechRecognition'}
_ASR = {'user_transcript', 'input_transcript', 'voice_transcript', 'transcript'}
_IDS = ('course_id', 'session_id', 'question_id', 'attempt_id')
_MAX_ROWS = 10000


def _public(value):
    if isinstance(value, dict):
        return {k: _public(v) for k, v in value.items() if k not in _PRIVATE}
    if isinstance(value, list):
        return [_public(v) for v in value]
    return value


def _json_object(value):
    result = json.loads(value) if isinstance(value, str) else value
    if not isinstance(result, dict):
        raise ValueError('expected JSON object')
    return _public(result)


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def _qa_question(value):
    """Actual Store serializes the held question, including private fields.

    Keep only its public prompt and identities. Legacy plain prompts remain
    supported; malformed JSON-looking input must not fall back to a prompt.
    """
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except ValueError:
            if not value.strip() or value.lstrip().startswith(('{', '[', '"')):
                raise ValueError('invalid serialized question') from None
            return value
        value = parsed
    if not isinstance(value, dict) or any(not isinstance(value.get(k), str) or not value[k].strip()
                                          for k in ('question', 'question_id', 'attempt_id')):
        raise ValueError('invalid serialized question identity')
    return {k: value[k] for k in ('question', 'question_id', 'attempt_id')}


def _qa_question_matches(value, current):
    question = _qa_question(value)
    return question == current.get('question') if isinstance(question, str) else all(question[k] == current.get(k) for k in question)


def grade_snapshot(db):
    """Snapshot existing explicit task DB in one readonly transaction; errors fail closed.

    The caller chooses its task DB. Never call on the user's unrelated database
    or publish the returned learner text. All QA rows are hashed, not rewritten.
    """
    try:
        path = Path(db)
        if not path.is_absolute() or path.is_symlink():
            raise ValueError('plain absolute database required')
        path = path.resolve(strict=True)
        if not path.is_file():
            raise ValueError('database missing')
        with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=0)) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute('PRAGMA query_only=ON')
            connection.execute('BEGIN')
            rows = connection.execute("""SELECT json_extract(value,'$.study_course_id') AS course_id,
                json_extract(value,'$.study_session_id') AS session_id,
                json_extract(value,'$.current_question.question_id') AS question_id,
                json_extract(value,'$.current_question.attempt_id') AS attempt_id,
                json_extract(value,'$.current_question.question') AS question,
                json_type(value,'$.current_question.attempt_evaluated') AS evaluated,
                json_extract(value,'$.last_answer_evaluation') AS last_grade
                FROM kv WHERE key='state' LIMIT 2""").fetchall()
            if len(rows) != 1:
                raise ValueError('state missing or ambiguous')
            state = dict(rows[0])
            qa = connection.execute('SELECT id,session_id,topic_id,question,user_answer,eval_result,mode,response_time_ms,created_at FROM qa_records ORDER BY id LIMIT ?', (_MAX_ROWS + 1,)).fetchall()
            interactions = connection.execute("SELECT id,session_id,input_text,metadata FROM interactions WHERE kind='answer_evaluate' ORDER BY id LIMIT ?", (_MAX_ROWS + 1,)).fetchall()
            if len(qa) > _MAX_ROWS or len(interactions) > _MAX_ROWS:
                raise ValueError('snapshot bound exceeded')
            qa_records = []
            for row in qa:
                raw = dict(row)
                qa_records.append({**{k: raw[k] for k in ('id', 'session_id', 'topic_id', 'user_answer')},
                                   'question': _qa_question(raw['question']),
                                   'row_sha256': _digest(raw), 'eval_result': _json_object(raw['eval_result'])})
            history = [{**{k: row[k] for k in ('id', 'session_id', 'input_text')},
                        'metadata': _json_object(row['metadata'])} for row in interactions]
        return {'ok': True, 'course_id': state['course_id'], 'session_id': state['session_id'],
                'question': {'question_id': state['question_id'], 'attempt_id': state['attempt_id'],
                             'question': state['question'], 'attempt_evaluated':
                             True if state['evaluated'] == 'true' else False if state['evaluated'] == 'false' else None},
                'last_answer_evaluation': _json_object(state['last_grade']) if state['last_grade'] is not None else {},
                'qa_records': qa_records, 'grade_interactions': history}
    except (OSError, ValueError, TypeError, sqlite3.Error):
        return {'ok': False, 'error': 'grade_snapshot_unavailable'}


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _wall(value):
    return _number(value) and value > 0


def _integer(value):
    return type(value) is int and value >= 0


def _native_token(value):
    return isinstance(value, str) and value.startswith('native_connection_') and len(value) > len('native_connection_')


def _row_map(rows, *, hashed=False):
    if not isinstance(rows, list):
        raise ValueError('missing rows')
    result = {}
    for row in rows:
        identity = row['id']
        if type(identity) not in (str, int) or identity == '' or (type(identity) is int and identity < 0):
            raise ValueError('missing row ID')
        key = (type(identity).__name__, identity)
        if key in result:
            raise ValueError('ambiguous row ID')
        if hashed and (not isinstance(row.get('row_sha256'), str) or len(row['row_sha256']) != 64
                       or any(c not in '0123456789abcdef' for c in row['row_sha256'])):
            raise ValueError('missing row hash')
        result[key] = row
    return result


def _grade(value):
    return isinstance(value, dict) and value.get('verdict') in ('wrong', 'partial', 'correct') and _number(value.get('score'))


def _same_grade(*values):
    return all(_grade(v) for v in values) and all(v[k] == values[0][k] for v in values for k in ('verdict', 'score'))


def _correction_origin(before, question, qa_rows, history_rows):
    """Join the specific old attempt, allowing its formal session to predate restart."""
    candidates = []
    for history in history_rows.values():
        metadata = history.get('metadata') or {}
        context = metadata.get('material_context') or {}
        payload = metadata.get('payload') or {}
        if (metadata.get('degraded') is not False or context.get('course_id') != before['course_id']
                or any(metadata.get(k) != question.get(k) for k in ('question_id', 'attempt_id'))
                or not isinstance(history.get('session_id'), str) or not history['session_id'].strip()
                or context.get('session_id') != history['session_id']
                or not isinstance(history.get('input_text'), str) or not history['input_text'].strip()
                or not _same_grade(before.get('last_answer_evaluation'), payload)
                or payload.get('verdict') not in ('wrong', 'partial')):
            continue
        for qa in qa_rows.values():
            if (qa.get('session_id') == history['session_id'] and qa.get('user_answer') == history['input_text']
                    and _qa_question_matches(qa.get('question'), question)
                    and _same_grade(qa.get('eval_result'), payload)):
                candidates.append(qa)
    return candidates[0] if len(candidates) == 1 else None


def grade_acceptance(report):
    """Check one ordinary answer or explicit same-question correction turn.

    Native receive/schedule and old-token cancellation are distinct evidence.
    The function never interprets local wire writes as provider acknowledgements.
    """
    names = ('schema_valid', 'pending_four_ids', 'same_question_attempt_evaluated', 'last_grade_consistent',
             'exactly_one_new_qa', 'old_qa_preserved', 'exactly_one_new_formal_interaction',
             'old_grade_interactions_preserved', 'formal_identity_and_asr', 'marker_chain',
             'actual_free_profile', 'old_token_cancel_received', 'old_queue_retired_or_never_received',
             'new_token_pcm_after_grade', 'new_token_playback_scheduled', 'native_text_after_grade',
             'native_terminal', 'output_only_capture_guard', 'run_finished_without_failure')
    intent = report.get('grade_intent', 'answer') if isinstance(report, dict) else None
    correction = intent == 'correction'
    state_check = 'evaluated_wrong_or_partial_four_ids' if correction else 'pending_four_ids'
    result_check = 'same_question_new_attempt_evaluated' if correction else 'same_question_attempt_evaluated'
    if correction:
        names = tuple(state_check if n == 'pending_four_ids' else result_check if n == 'same_question_attempt_evaluated' else n for n in names)
        names += ('correction_origin_formal_lineage', 'same_concept_topic')
    checks = dict.fromkeys(names, False)
    checks['supported_grade_intent'] = intent in ('answer', 'correction')
    retirement_evidence = 'UNVERIFIED'
    try:
        before, after = report['grade_before'], report['grade_after']
        q0, q1 = before['question'], after['question']
        pin = {**{k: before[k] for k in ('course_id', 'session_id')},
               **{k: q0[k] for k in ('question_id', 'attempt_id')}}
        ids_valid = all(isinstance(v, str) and v.strip() for v in pin.values())
        checks[state_check] = (ids_valid and q0.get('attempt_evaluated') is (True if correction else False)
            and (not correction or (_grade(before.get('last_answer_evaluation'))
                 and before['last_answer_evaluation']['verdict'] in ('wrong', 'partial'))))
        result_attempt = q1.get('attempt_id') if correction else pin['attempt_id']
        checks[result_check] = (ids_valid and after['course_id'] == pin['course_id']
            and after['session_id'] == pin['session_id'] and q1.get('question_id') == pin['question_id']
            and isinstance(result_attempt, str) and bool(result_attempt.strip())
            and (result_attempt != pin['attempt_id'] if correction else q1.get('attempt_id') == result_attempt)
            and q1.get('attempt_evaluated') is True
            and isinstance(q0.get('question'), str) and bool(q0['question'].strip()) and q1.get('question') == q0['question'])
        qa0, qa1 = (_row_map(value['qa_records'], hashed=True) for value in (before, after))
        h0, h1 = (_row_map(value['grade_interactions']) for value in (before, after))
        new_qa = [v for k, v in qa1.items() if k not in qa0]
        new_h = [v for k, v in h1.items() if k not in h0]
        checks['old_qa_preserved'] = all(k in qa1 and v['row_sha256'] == qa1[k]['row_sha256'] for k, v in qa0.items())
        checks['exactly_one_new_qa'] = len(new_qa) == 1 and len(qa1) == len(qa0) + 1
        checks['old_grade_interactions_preserved'] = all(h1.get(k) == v for k, v in h0.items())
        checks['exactly_one_new_formal_interaction'] = len(new_h) == 1 and len(h1) == len(h0) + 1
        qa, history = (new_qa[0] if len(new_qa) == 1 else {}), (new_h[0] if len(new_h) == 1 else {})
        if correction:
            origin = _correction_origin(before, q0, qa0, h0)
            checks['correction_origin_formal_lineage'] = origin is not None
            checks['same_concept_topic'] = (origin is not None and isinstance(origin.get('topic_id'), str)
                and bool(origin['topic_id'].strip()) and qa.get('topic_id') == origin['topic_id'])
        metadata = history.get('metadata') or {}
        context, payload = metadata.get('material_context') or {}, metadata.get('payload') or {}
        last, evaluation = after.get('last_answer_evaluation'), qa.get('eval_result')
        checks['last_grade_consistent'] = (_grade(last) and _grade(evaluation) and _grade(payload)
            and all(last[k] == evaluation[k] == payload[k] for k in ('verdict', 'score')))
        turn, = report['turns']
        start, speech_end, end = turn['input_wall'], turn['fixed_speech_end_wall'], turn['observation_end_wall']
        if not all(_wall(w) for w in (start, speech_end, end)) or not start <= speech_end < end:
            raise ValueError('invalid turn window')
        events = report['native_final']['trace']['events']
        if not isinstance(events, list):
            raise ValueError('missing events')
        window = [e for e in events if _wall(e.get('wall')) and start <= e['wall'] <= end]
        asr = [e for e in window if e.get('type') in _ASR and isinstance(e.get('text'), str) and e['text'].strip()]
        original = asr[0]['text'] if len(asr) == 1 else None
        checks['formal_identity_and_asr'] = (isinstance(original, str) and bool(original.strip())
            and asr[0]['wall'] >= speech_end and qa.get('user_answer') == original == history.get('input_text')
            and _qa_question_matches(qa.get('question'), q1) and qa.get('session_id') == pin['session_id']
            and history.get('session_id') == pin['session_id'] and metadata.get('degraded') is False
            and metadata.get('question_id') == pin['question_id'] and metadata.get('attempt_id') == result_attempt
            and all(context.get(k) == pin[k] for k in ('course_id', 'session_id')))
        markers = report['grade_markers']
        if not isinstance(markers, list) or len(markers) != 3:
            raise ValueError('ambiguous grade markers')
        stages = {m['stage']: m for m in markers}
        accepted, completed, relayed = (stages[k] for k in ('accepted', 'grade_complete', 'relay_written'))
        old, new = accepted.get('token'), relayed.get('token')
        complete = completed.get('wall')
        checks['marker_chain'] = (all(_wall(m.get('wall')) for m in markers)
            and speech_end <= accepted['wall'] <= complete <= relayed['wall'] <= end
            and all(all(m.get(k) == pin[k] for k in _IDS) for m in markers)
            and all(_integer(m.get(k)) for m in markers for k in ('connection', 'scope'))
            and accepted['connection'] == completed['connection']
            and accepted['scope'] == completed['scope']
            and relayed['connection'] == accepted['connection'] + 1 and relayed['scope'] > accepted['scope']
            and _native_token(old) and _native_token(new) and new != old
            and completed.get('token') == old and all(m.get('old_token') == old for m in markers)
            and all(m.get('result_attempt_id') == result_attempt for m in (completed, relayed)))
        checks['actual_free_profile'] = report.get('grade_protocol_profile') == 'lanlan_app_gemini' and all(m.get('profile') == 'lanlan_app_gemini' for m in markers)
        cancels = [e for e in window if e.get('type') == 'game_route_speech_cancel' and e.get('correlation_id') == old and _wall(complete) and e['wall'] >= complete]
        stops = [e for e in window if e.get('type') == 'speech_playback_state' and e.get('correlationId') == old
                 and e.get('reason') == 'native_connection_cancel' and e.get('active') is False and _wall(complete) and e['wall'] >= complete]
        checks['old_token_cancel_received'] = bool(cancels)
        frames = [e for e in window if e.get('type') == 'audio_frame']
        # Telemetry counts all binary messages; the player skips empty buffers.
        # Empty messages retain their owner/time guards but cannot prove PCM.
        pcm_frames = [e for e in frames if _integer(e.get('bytes')) and e['bytes'] > 0]
        all_frames = [e for e in events if e.get('type') == 'audio_frame']
        initial = report.get('native_initial') or {}
        initial_trace = initial.get('trace') or {}
        final_trace = report['native_final']['trace']
        native = report.get('native') or {}
        initial_playback = initial.get('playback')
        never_received = (type(initial_trace.get('binaryFrames')) is int and initial_trace['binaryFrames'] == 0
            and type(final_trace.get('binaryFrames')) is int and final_trace['binaryFrames'] == len(all_frames) > 0
            and _wall(initial.get('wall')) and _wall(initial_trace.get('installedAt'))
            and initial_trace['installedAt'] <= initial['wall'] <= start
            and type(native.get('pid')) is int and native['pid'] > 0
            and type(native.get('windows')) is int and native['windows'] > 0 and native.get('fake_silent_input') is False
            and (initial_playback is None or (isinstance(initial_playback, dict) and initial_playback.get('active') is False
                 and _number(initial_playback.get('remainingSeconds')) and initial_playback['remainingSeconds'] == 0))
            and len(frames) == len(all_frames)
            and all(e.get('correlation_id') == new and _wall(e.get('wall')) and _wall(complete)
                    and complete <= e['wall'] <= end for e in all_frames))
        checks['old_queue_retired_or_never_received'] = bool(stops) or never_received
        retirement_evidence = 'NATIVE_STOP_RECEIPT' if stops else 'FRESH_RENDERER_NEVER_RECEIVED_OLD_PCM' if never_received else 'UNVERIFIED'
        checks['new_token_pcm_after_grade'] = (bool(pcm_frames) and bool(cancels) and checks['old_queue_retired_or_never_received']
            and all(e.get('correlation_id') == new and _integer(e.get('bytes'))
                    and e['wall'] >= max(complete, min(c['wall'] for c in cancels), min((s['wall'] for s in stops), default=complete)) for e in frames))
        scheduled = [e for e in window if e.get('type') == 'native_speech_playback_state' and e.get('active') is True
                     and e.get('sdk_speech_correlation_id') == new and _wall(complete) and e['wall'] >= complete]
        checks['new_token_playback_scheduled'] = bool(scheduled) and bool(pcm_frames) and min(e['wall'] for e in scheduled) >= min(e['wall'] for e in pcm_frames)
        replies = [e for e in window if e.get('type') == 'gemini_response' and isinstance(e.get('text'), str) and e['text'].strip()]
        checks['native_text_after_grade'] = bool(replies) and all(_wall(complete) and e['wall'] >= complete for e in replies)
        playback = report['native_final']['playback']
        checks['native_terminal'] = (playback.get('active') is False and _number(playback.get('remainingSeconds'))
            and playback['remainingSeconds'] == 0 and playback.get('reason') == 'source_ended'
            and playback.get('correlationId') == new and _number(playback.get('updatedAt'))
            and bool(frames) and max(e['wall'] for e in frames) <= playback['updatedAt'] / 1000 <= end)
        policy, receipt = report['capture_policy'], report['capture_policy']['receipt']
        checks['output_only_capture_guard'] = (report.get('output_only') is True and report.get('room_microphone') is False
            and report.get('capture_devices') is False and report.get('loopback_enabled') is False and report.get('volume_changed') is False
            and policy.get('flag') is True and policy.get('readonly') is True and receipt.get('status') == 'installed'
            and receipt.get('captureBlocked') is True and isinstance(receipt.get('blocked'), list) and _BLOCKED.issubset(set(receipt['blocked'])))
        checks['run_finished_without_failure'] = (not report.get('failure') and report.get('turn_timeout') is not True
            and turn.get('turn_timeout') is not True and report.get('cleanup_errors') == [])
        checks['schema_valid'] = before.get('ok') is True and after.get('ok') is True
    except (KeyError, ValueError, TypeError, IndexError, AttributeError):
        checks['schema_valid'] = False
    return {'grade_intent': intent, 'checks': checks, 'result': 'CANDIDATE_GRADE_FLOW_PASS_REQUIRES_SEMANTIC_REVIEW' if all(checks.values()) else 'FAIL_OR_PARTIAL',
            'old_output_retirement_evidence': retirement_evidence,
            'physical_output': 'UNVERIFIED_NO_LOOPBACK', 'human': 'PENDING'}


def _completed_native_turn(turn):
    start, speech_end, end = (turn[k] for k in ('input_wall','fixed_speech_end_wall','observation_end_wall'))
    if not all(_wall(w) for w in (start,speech_end,end)) or not start <= speech_end < end:
        return False
    snapshot=turn['native_snapshot'];playback=snapshot['playback'];token=playback.get('correlationId')
    window=[e for e in snapshot['trace']['events'] if _wall(e.get('wall')) and start <= e['wall'] <= end]
    asr=[e for e in window if e.get('type') in _ASR and isinstance(e.get('text'),str) and e['text'].strip()]
    frames=[e for e in window if e.get('type')=='audio_frame']
    positive=[e for e in frames if _integer(e.get('bytes')) and e['bytes']>0]
    replies=[e for e in window if e.get('type')=='gemini_response' and isinstance(e.get('text'),str) and e['text'].strip()]
    ends=[e for e in window if e.get('type')=='system' and e.get('data')=='turn end']
    schedules=[e for e in window if e.get('type')=='native_speech_playback_state' and e.get('active') is True
        and e.get('sdk_speech_correlation_id')==token]
    return bool(not turn.get('turn_timeout') and len(asr)==1 and asr[0]['wall'] >= speech_end
        and _native_token(token) and positive and replies and ends and schedules
        and all(e['wall'] >= speech_end for e in (*frames,*replies,*ends))
        and all(e.get('correlation_id')==token and _integer(e.get('bytes')) for e in frames)
        and min(e['wall'] for e in schedules) >= min(e['wall'] for e in positive)
        and playback.get('active') is False and playback.get('reason')=='source_ended'
        and _number(playback.get('remainingSeconds')) and playback['remainingSeconds']==0
        and _number(playback.get('updatedAt'))
        and max(e['wall'] for e in frames) <= playback['updatedAt']/1000 <= end)


def grade_chain_acceptance(report):
    """Observe request -> generated quiz -> answer -> non-answer follow-up.

    Reuse the one-grade receipt on the answer's own snapshot/window. No writes,
    fabricated pending state, provider ACK inference, or physical-audio verdict.
    """
    checks = dict.fromkeys(('healthy_empty_start', 'quiz_from_actual_role_tool',
        'quiz_did_not_grade', 'same_connection_first_two_inputs', 'answer_grade_flow',
        'followup_did_not_grade_or_replace_question', 'three_completed_native_turns'), False)
    answer_receipt = None
    try:
        first, answer, followup = report['turns']
        before, quiz, graded, after = (report['chain_before'], first['grade_after_turn'],
            answer['grade_after_turn'], followup['grade_after_turn'])
        pin, empty = first['grade_next_input_pin'], report['chain_empty_pin']
        checks['healthy_empty_start'] = (before.get('ok') is True
            and empty.get('_question_empty') is True and report.get('native_grade_chain') is True
            and not report.get('grade_quiz_preparation')
            and all(empty.get(k) == before.get(k) == quiz.get(k) for k in ('course_id','session_id'))
            and all(before['question'].get(k) is None for k in ('question_id','attempt_id','attempt_evaluated')))
        calls = [e for e in report['wire_trace'] if e.get('dir') == 'recv'
            and e.get('type') == 'response.function_call_arguments.done'
            and e.get('name') == 'study_quiz' and _wall(e.get('t'))
            and first['fixed_speech_end_wall'] <= e['t'] <= first['observation_end_wall']]
        checks['quiz_from_actual_role_tool'] = (len(calls) == 1 and quiz.get('ok') is True
            and quiz['question'].get('attempt_evaluated') is False
            and all(isinstance(pin.get(k), str) and pin[k].strip() for k in _IDS)
            and all(pin[k] == quiz.get(k) for k in ('course_id','session_id'))
            and all(pin[k] == quiz['question'].get(k) for k in ('question_id','attempt_id')))
        checks['quiz_did_not_grade'] = (before.get('ok') is True and quiz.get('ok') is True
            and before['qa_records'] == quiz['qa_records']
            and before['grade_interactions'] == quiz['grade_interactions'])
        view = {**report, 'grade_before': quiz, 'grade_after': graded, 'grade_input_pin': pin,
            'turns': [answer], 'native_final': answer['native_snapshot']}
        answer_receipt = grade_acceptance(view)
        checks['answer_grade_flow'] = all(answer_receipt['checks'].values())
        deliveries = [[d for d in report['phrase_deliveries'] if _wall(d.get('started_wall'))
            and turn['input_wall'] <= d['started_wall'] <= turn['observation_end_wall']]
            for turn in (first, answer)]
        accepted = [m for m in report['grade_markers'] if m.get('stage') == 'accepted']
        written = all(len(ds)==1 and ds[0].get('result')=='written_waiting_provider_boundary'
            and ds[0].get('input_timebase')=='arrival_derived_sample_estimate'
            and type(ds[0].get('connection_generation')) is int and ds[0]['connection_generation']>0
            and all(_integer(ds[0].get(k)) and ds[0][k]>0 for k in ('source_samples','output_samples','written_samples'))
            and ds[0]['source_samples'] >= ds[0]['output_samples'] == ds[0]['written_samples']
            and all(_wall(ds[0].get(k)) for k in ('sealed_wall','first_write_wall','completed_wall'))
            and turn['input_wall'] <= ds[0]['sealed_wall'] <= ds[0]['started_wall'] <= ds[0]['first_write_wall']
                <= ds[0]['completed_wall'] <= turn['observation_end_wall']
            for ds,turn in zip(deliveries,(first,answer)))
        checks['same_connection_first_two_inputs'] = (written
            and len(accepted) == 1 and type(accepted[0].get('connection')) is int
            and all(ds[0].get('connection_generation') == accepted[0]['connection'] for ds in deliveries))
        checks['followup_did_not_grade_or_replace_question'] = (graded.get('ok') is True and after.get('ok') is True
            and all(graded.get(k) == after.get(k) for k in ('course_id','session_id','question',
                'qa_records','grade_interactions','last_answer_evaluation')))
        checks['three_completed_native_turns'] = (not report.get('failure') and not report.get('turn_timeout')
            and report.get('cleanup_errors') == []
            and all(_completed_native_turn(t) for t in report['turns'])
            and first['observation_end_wall'] < answer['input_wall']
            and answer['observation_end_wall'] < followup['input_wall'])
    except (KeyError, ValueError, TypeError, IndexError, AttributeError):
        pass
    return {'checks':checks,'answer_receipt':answer_receipt,
        'result':'CANDIDATE_CONTINUOUS_GRADE_PASS_REQUIRES_SEMANTIC_REVIEW' if all(checks.values()) else 'FAIL_OR_PARTIAL',
        'physical_output':'UNVERIFIED_NO_LOOPBACK','human':'PENDING'}
