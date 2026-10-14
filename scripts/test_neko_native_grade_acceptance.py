"""Small real SQLite and report fixtures; no host/model/provider/device."""
from contextlib import closing
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import neko_native_grade_acceptance as subject

ORIGINAL = '我 回 答 刚 才 的 题，我 的 答 案 是 REZ，请 判 断 对 不 对。'
PIN = {'course_id': 'course-A', 'session_id': 'session-A', 'question_id': 'q-A', 'attempt_id': 'a-A'}
GRADE = {'verdict': 'wrong', 'score': 0, 'reply': '先从 WEX 发起。'}


class Fixture:
    def __init__(self):
        self.temp = tempfile.TemporaryDirectory(prefix='neko-grade-acceptance-')
        self.db = Path(self.temp.name) / 'study.db'
        self.question = {'question_id': PIN['question_id'], 'attempt_id': PIN['attempt_id'],
                         'question': '谁先调用？', 'attempt_evaluated': False,
                         'answer': 'PRIVATE_REFERENCE', 'rubric': 'PRIVATE_RUBRIC'}
        self.state = {'study_course_id': PIN['course_id'], 'study_session_id': PIN['session_id'],
                      'current_question': self.question, 'last_answer_evaluation': {}, 'history': ['PRIVATE_HISTORY']}
        with closing(sqlite3.connect(self.db)) as c, c:
            c.executescript('''CREATE TABLE kv(key TEXT PRIMARY KEY,value TEXT);
                CREATE TABLE qa_records(id TEXT PRIMARY KEY,session_id TEXT,topic_id TEXT,question TEXT,
                user_answer TEXT,eval_result TEXT,mode TEXT,response_time_ms INTEGER,created_at TEXT);
                CREATE TABLE interactions(id INTEGER PRIMARY KEY,kind TEXT,input_text TEXT,output_text TEXT,
                metadata TEXT,created_at TEXT,session_id TEXT);''')
            c.execute('INSERT INTO kv VALUES (?,?)', ('state', json.dumps(self.state)))
            c.execute('INSERT INTO qa_records VALUES (?,?,?,?,?,?,?,?,?)', ('old-qa', 'old-session', 'old-topic', 'old question',
                'old answer', json.dumps({'verdict':'correct','score':1}), 'tutor', 100, 'old-time'))
            c.execute('INSERT INTO interactions VALUES (?,?,?,?,?,?,?)', (1, 'explain', 'PRIVATE_EXPLANATION', 'PRIVATE_OUTPUT', '{}', 'old-time', 'old-session'))

    def before_and_after(self):
        before = subject.grade_snapshot(self.db)
        self.question['attempt_evaluated'] = True
        self.state['last_answer_evaluation'] = GRADE
        metadata = {**{k: PIN[k] for k in ('question_id','attempt_id')},
                    'material_context': {k: PIN[k] for k in ('course_id','session_id')},
                    'degraded':False, 'payload': GRADE, 'rubric':'PRIVATE_RUBRIC'}
        with closing(sqlite3.connect(self.db)) as c, c:
            c.execute('UPDATE kv SET value=? WHERE key=?', (json.dumps(self.state),'state'))
            c.execute('INSERT INTO qa_records VALUES (?,?,?,?,?,?,?,?,?)', ('new-qa',PIN['session_id'],'topic',
                json.dumps(self.question,ensure_ascii=False),ORIGINAL,json.dumps(GRADE),'tutor',800,'new-time'))
            c.execute('INSERT INTO interactions VALUES (?,?,?,?,?,?,?)', (2,'answer_evaluate',ORIGINAL,GRADE['reply'],json.dumps(metadata),'new-time',PIN['session_id']))
        return before, subject.grade_snapshot(self.db)

    def close(self):
        self.temp.cleanup()


def make_report(before, after):
    old, new = 'native_connection_old', 'native_connection_new'
    stages = []
    for stage, wall, connection, scope, token in (('accepted',102,3,5,old),('grade_complete',104,3,5,old),('relay_written',105.5,4,7,new)):
        stages.append({**PIN,'stage':stage,'wall':wall,'connection':connection,'scope':scope,'token':token,
                       'old_token':old,'result_attempt_id':PIN['attempt_id'] if stage!='accepted' else '', 'profile':'lanlan_app_gemini'})
    events = [{'type':'user_transcript','wall':102.1,'text':ORIGINAL},
              {'type':'game_route_speech_cancel','wall':104.2,'correlation_id':old},
              {'type':'speech_playback_state','wall':104.2,'correlationId':old,'active':False,'reason':'native_connection_cancel'},
              {'type':'audio_chunk','wall':105.0,'correlation_id':new},
              {'type':'audio_frame','wall':105.1,'correlation_id':new,'bytes':960},
              {'type':'native_speech_playback_state','wall':105.2,'sdk_speech_correlation_id':new,'active':True},
              {'type':'gemini_response','wall':105.3,'text':GRADE['reply']}]
    return {'grade_before':before,'grade_after':after,'grade_markers':stages,'grade_protocol_profile':'lanlan_app_gemini',
            'turns':[{'input_wall':100,'fixed_speech_end_wall':101,'observation_end_wall':110}],
            'native_final':{'trace':{'events':events,'binaryFrames':1},'playback':{'active':False,'correlationId':new,
                'remainingSeconds':0,'reason':'source_ended','updatedAt':109000}},
            'capture_policy':{'flag':True,'readonly':True,'receipt':{'status':'installed','captureBlocked':True,'blocked':sorted(subject._BLOCKED)}},
            'output_only':True,'room_microphone':False,'capture_devices':False,'loopback_enabled':False,'volume_changed':False,
            'cleanup_errors':[],'failure':None,'timing_log':[],'wire_trace':[]}


def make_correction(fixture, *, partial_origin=False):
    # Actual Store shape: old formal QA belongs to the session before restart.
    fixture.before_and_after()
    if partial_origin:
        partial = {'verdict': 'partial', 'score': 0.5, 'reply': '还需补全。'}
        fixture.state['last_answer_evaluation'] = partial
        with closing(sqlite3.connect(fixture.db)) as c, c:
            metadata = json.loads(c.execute('SELECT metadata FROM interactions WHERE id=2').fetchone()[0])
            metadata['payload'] = partial
            c.execute("UPDATE qa_records SET eval_result=? WHERE id='new-qa'", (json.dumps(partial),))
            c.execute('UPDATE interactions SET metadata=? WHERE id=2', (json.dumps(metadata),))
    fixture.state['study_session_id'] = 'session-after-restart'
    with closing(sqlite3.connect(fixture.db)) as c, c:
        c.execute('UPDATE kv SET value=? WHERE key=?', (json.dumps(fixture.state), 'state'))
    before = subject.grade_snapshot(fixture.db)
    fixture.question['attempt_id'] = 'a-correction'
    grade = {'verdict': 'correct', 'score': 1, 'reply': '这次正确。'}
    fixture.state['last_answer_evaluation'] = grade
    answer = '我更正刚才那道题，答案是 WEX，请重新评分。'
    metadata = {'question_id': PIN['question_id'], 'attempt_id': 'a-correction', 'degraded': False,
                'material_context': {'course_id': PIN['course_id'], 'session_id': 'session-after-restart'},
                'payload': grade}
    with closing(sqlite3.connect(fixture.db)) as c, c:
        c.execute('UPDATE kv SET value=? WHERE key=?', (json.dumps(fixture.state), 'state'))
        c.execute('INSERT INTO qa_records VALUES (?,?,?,?,?,?,?,?,?)', ('corrected-qa', 'session-after-restart', 'topic',
            json.dumps(fixture.question, ensure_ascii=False), answer, json.dumps(grade), 'tutor', 900, 'correction-time'))
        c.execute('INSERT INTO interactions VALUES (?,?,?,?,?,?,?)', (3, 'answer_evaluate', answer, grade['reply'],
            json.dumps(metadata), 'correction-time', 'session-after-restart'))
    report = make_report(before, subject.grade_snapshot(fixture.db))
    report['grade_intent'] = 'correction'
    for marker in report['grade_markers']:
        marker['session_id'] = 'session-after-restart'
        if marker['stage'] != 'accepted': marker['result_attempt_id'] = 'a-correction'
    report['native_final']['trace']['events'][0]['text'] = answer
    return report


class GradeEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.fixture = Fixture()
        self.before, self.after = self.fixture.before_and_after()
        self.report = make_report(self.before,self.after)

    def tearDown(self):
        self.fixture.close()

    def assert_partial(self, report, check=None):
        result = subject.grade_acceptance(report)
        self.assertEqual(result['result'],'FAIL_OR_PARTIAL',result)
        self.assertEqual(result['physical_output'],'UNVERIFIED_NO_LOOPBACK')
        self.assertEqual(result['human'],'PENDING')
        if check: self.assertFalse(result['checks'][check],result)

    def test_success_is_only_candidate_and_fast_pcm_can_precede_relay_written(self):
        original = deepcopy(self.report)
        result = subject.grade_acceptance(self.report)
        self.assertTrue(all(result['checks'].values()),result)
        self.assertEqual(result['result'],'CANDIDATE_GRADE_FLOW_PASS_REQUIRES_SEMANTIC_REVIEW')
        self.assertEqual(result['physical_output'],'UNVERIFIED_NO_LOOPBACK')
        self.assertEqual(result['human'],'PENDING')
        self.assertEqual(self.report,original)

    def test_snapshot_readonly_private_projection_and_full_old_row_hash(self):
        before_bytes = self.fixture.db.read_bytes()
        queries=[]; connect=sqlite3.connect
        def traced(*args,**kwargs):
            self.assertTrue(kwargs['uri']);self.assertEqual(kwargs['timeout'],0);self.assertIn('?mode=ro',args[0])
            connection=connect(*args,**kwargs);connection.set_trace_callback(queries.append);return connection
        with patch.object(subject.sqlite3,'connect',side_effect=traced):
            snap=subject.grade_snapshot(self.fixture.db)
        self.assertEqual(self.fixture.db.read_bytes(),before_bytes)
        self.assertNotIn('PRIVATE',json.dumps(snap))
        self.assertTrue(any('query_only=ON' in q for q in queries))
        self.assertFalse(any('UPDATE' in q or 'INSERT' in q or 'SELECT value' in q or 'output_text' in q for q in queries))
        with closing(sqlite3.connect(self.fixture.db)) as c,c:
            c.execute("UPDATE qa_records SET response_time_ms=101 WHERE id='old-qa'")
        changed=subject.grade_snapshot(self.fixture.db)
        self.assertNotEqual(changed['qa_records'][1]['row_sha256'],snap['qa_records'][1]['row_sha256'])
        self.assert_partial({**self.report,'grade_after':changed},'old_qa_preserved')

    def test_actual_store_serialized_question_and_legacy_plain_question(self):
        projected=next(row for row in self.after['qa_records'] if row['id']=='new-qa')['question']
        self.assertEqual(projected,{**{k:PIN[k] for k in ('question_id','attempt_id')},'question':self.fixture.question['question']})
        self.assertNotIn('PRIVATE',json.dumps(self.after))
        # Older raw reports retain the Store's JSON string; do not rewrite them.
        report=deepcopy(self.report)
        row=next(row for row in report['grade_after']['qa_records'] if row['id']=='new-qa')
        row['question']=json.dumps(self.fixture.question,ensure_ascii=False)
        self.assertTrue(all(subject.grade_acceptance(report)['checks'].values()))
        row['question']=self.fixture.question['question']
        self.assertTrue(all(subject.grade_acceptance(report)['checks'].values()))
        row['question']='different legacy question'
        self.assert_partial(report,'formal_identity_and_asr')

    def test_serialized_question_malformed_or_different_ids_never_falls_back(self):
        for kind in ('question','question_id','attempt_id','missing_id','malformed','array','scalar'):
            report=deepcopy(self.report);question=deepcopy(self.fixture.question)
            if kind in ('question','question_id','attempt_id'):question[kind]='different'
            elif kind=='missing_id':question.pop('attempt_id')
            raw=json.dumps(question,ensure_ascii=False)
            if kind=='malformed':raw='{"question":"谁先调用？",bad'
            elif kind=='array':raw=json.dumps([question])
            elif kind=='scalar':raw='"谁先调用？"'
            row=next(row for row in report['grade_after']['qa_records'] if row['id']=='new-qa')
            row['question']=raw
            self.assert_partial(report)
        with closing(sqlite3.connect(self.fixture.db)) as c,c:
            c.execute("UPDATE qa_records SET question=? WHERE id='new-qa'", ('{"question":"prompt","rubric":"PRIVATE",broken',))
        snapshot=subject.grade_snapshot(self.fixture.db)
        self.assertFalse(snapshot['ok'])
        self.assertNotIn('PRIVATE',json.dumps(snapshot))

    def test_missing_snapshots_markers_or_failure_never_pass(self):
        for key in ('grade_before','grade_after','grade_markers','native_final','capture_policy','grade_protocol_profile','turns'):
            with self.subTest(key=key):
                report=deepcopy(self.report);report.pop(key);self.assert_partial(report)
        for changed in ({'failure':'timeout'},{'turn_timeout':True},{'cleanup_errors':['host not stopped']}):
            self.assert_partial({**self.report,**changed},'run_finished_without_failure')
        self.assert_partial({})

    def test_empty_identity_or_changed_question_attempt_course_is_partial(self):
        for key in PIN:
            report=deepcopy(self.report)
            source=report['grade_before'] if key in ('course_id','session_id') else report['grade_before']['question']
            source[key]=''
            self.assert_partial(report,'pending_four_ids')
        for key in PIN:
            report=deepcopy(self.report)
            source=report['grade_after'] if key in ('course_id','session_id') else report['grade_after']['question']
            source[key]='foreign'
            self.assert_partial(report,'same_question_attempt_evaluated')
        report=deepcopy(self.report);report['grade_after']['question']['attempt_evaluated']=False
        self.assert_partial(report,'same_question_attempt_evaluated')

    def test_extra_qa_deleted_or_mutated_old_row_and_extra_formal_grade_fail(self):
        report=deepcopy(self.report);row=deepcopy(report['grade_after']['qa_records'][0]);row['id']='third-qa';report['grade_after']['qa_records'].append(row)
        self.assert_partial(report,'exactly_one_new_qa')
        report=deepcopy(self.report);report['grade_after']['qa_records']=[r for r in report['grade_after']['qa_records'] if r['id']!='old-qa']
        self.assert_partial(report,'old_qa_preserved')
        report=deepcopy(self.report);old=next(r for r in report['grade_after']['qa_records'] if r['id']=='old-qa');old['row_sha256']='0'*64
        self.assert_partial(report,'old_qa_preserved')
        report=deepcopy(self.report);row=deepcopy(report['grade_after']['grade_interactions'][0]);row['id']=3;report['grade_after']['grade_interactions'].append(row)
        self.assert_partial(report,'exactly_one_new_formal_interaction')

    def test_no_asr_wrong_input_or_formal_identity_not_inferred_from_reply(self):
        for kind in ('missing','different','duplicate'):
            report=deepcopy(self.report);events=report['native_final']['trace']['events']
            if kind=='missing':events.pop(0)
            elif kind=='different':events[0]['text']='another answer'
            else:events.append(deepcopy(events[0]))
            self.assert_partial(report,'formal_identity_and_asr')
        for key in PIN:
            report=deepcopy(self.report);metadata=report['grade_after']['grade_interactions'][0]['metadata']
            (metadata if key in ('question_id','attempt_id') else metadata['material_context'])[key]='foreign'
            self.assert_partial(report,'formal_identity_and_asr')
        report=deepcopy(self.report);report['grade_after']['grade_interactions']=[]
        self.assert_partial(report,'exactly_one_new_formal_interaction')
        report=deepcopy(self.report);report['grade_after']['last_answer_evaluation']['score']=1
        self.assert_partial(report,'last_grade_consistent')

    def test_no_pcm_no_cancel_no_stop_and_old_token_pcm_fail(self):
        for event_type,check in (('audio_frame','new_token_pcm_after_grade'),('game_route_speech_cancel','old_token_cancel_received'),
                                 ('speech_playback_state','old_queue_retired_or_never_received'),('native_speech_playback_state','new_token_playback_scheduled')):
            report=deepcopy(self.report);report['native_final']['trace']['events']=[e for e in report['native_final']['trace']['events'] if e['type']!=event_type]
            self.assert_partial(report,check)
        report=deepcopy(self.report)
        next(e for e in report['native_final']['trace']['events'] if e['type']=='audio_frame')['correlation_id']='native_connection_old'
        self.assert_partial(report,'new_token_pcm_after_grade')

    def test_fresh_renderer_complete_trace_can_prove_no_old_queue_received(self):
        report=deepcopy(self.report)
        report['native_final']['trace']['events']=[e for e in report['native_final']['trace']['events'] if e['type']!='speech_playback_state']
        report['native_initial']={'wall':99,'trace':{'binaryFrames':0,'installedAt':98}}
        report['native']={'pid':1234,'windows':1,'fake_silent_input':False}
        result=subject.grade_acceptance(report)
        self.assertTrue(all(result['checks'].values()),result)
        self.assertEqual(result['old_output_retirement_evidence'],'FRESH_RENDERER_NEVER_RECEIVED_OLD_PCM')
        for kind in ('initial','counter','evicted','outside','missing_native','late_install','already_playing'):
            bad=deepcopy(report)
            if kind=='initial':bad['native_initial']['trace']['binaryFrames']=1
            elif kind in ('counter','evicted'):bad['native_final']['trace']['binaryFrames']=2
            elif kind=='outside':
                bad['native_final']['trace']['events'].append({'type':'audio_frame','wall':99,'correlation_id':'native_connection_new','bytes':100})
                bad['native_final']['trace']['binaryFrames']=2
            elif kind=='missing_native':bad.pop('native')
            elif kind=='late_install':bad['native_initial']['trace']['installedAt']=100.1
            else:bad['native_initial']['playback']={'active':True,'remainingSeconds':1}
            self.assert_partial(bad,'old_queue_retired_or_never_received')

    def test_grade_late_marker_identity_and_time_boundaries(self):
        report=deepcopy(self.report);report['grade_markers'][1]['wall']=105.15
        self.assert_partial(report,'new_token_pcm_after_grade')
        for key,value in (('connection',9),('scope',99),('attempt_id','foreign'),('token','native_connection_foreign')):
            report=deepcopy(self.report);report['grade_markers'][1][key]=value
            self.assert_partial(report,'marker_chain')
        report=deepcopy(self.report);report['grade_markers'][1]['wall']=101
        self.assert_partial(report,'marker_chain')
        report=deepcopy(self.report);report['turns'][0]['observation_end_wall']=104
        self.assert_partial(report)
        report=deepcopy(self.report);report['grade_markers'][1]['wall']=float('nan')
        self.assert_partial(report)

    def test_terminal_capture_and_actual_free_profile_are_required(self):
        for change in ({'active':True},{'remainingSeconds':1},{'reason':'cancelled'},{'correlationId':'native_connection_old'}, {'updatedAt':105000}):
            report=deepcopy(self.report);report['native_final']['playback'].update(change)
            self.assert_partial(report,'native_terminal')
        for key,value in (('room_microphone',True),('capture_devices',True),('loopback_enabled',True),('output_only',False),('volume_changed',True)):
            self.assert_partial({**self.report,key:value},'output_only_capture_guard')
        report=deepcopy(self.report);report['capture_policy']['receipt']['blocked'].pop()
        self.assert_partial(report,'output_only_capture_guard')
        report=deepcopy(self.report);report['grade_protocol_profile']='strict_default'
        self.assert_partial(report,'actual_free_profile')
        report=deepcopy(self.report);report['grade_markers'][2]['profile']='strict_default'
        self.assert_partial(report,'actual_free_profile')

    def late_cancel_report(self):
        report=deepcopy(self.report);snapshot=report['native_final'];events=snapshot['trace']['events']
        events.extend([{'type':'system','data':'turn end','wall':106},
            {'type':'speech_playback_state','direction':'device','wall':109,'updatedAt':109000,
             'correlationId':'native_connection_new','active':False,'remainingSeconds':0,'reason':'source_ended'},
            {'type':'speech_playback_state','direction':'device','wall':109.5,'updatedAt':109500,
             'correlationId':'native_connection_new','active':False,'remainingSeconds':0,'reason':'speech_cancel'}])
        for i,event in enumerate(events,1):event['observer_sequence']=i
        snapshot['trace'].update(eventSequence=len(events),binaryBytes=960,
            collection={'sequence_complete':True,'first_sequence':1,'last_sequence':len(events)})
        snapshot['playback'].update(reason='speech_cancel',updatedAt=109500)
        return report

    def test_observed_normal_end_survives_later_empty_queue_cancel_without_human_pass(self):
        report=self.late_cancel_report();result=subject.grade_acceptance(report)
        self.assertTrue(all(result['checks'].values()),result)
        self.assertEqual(result['native_terminal_evidence'],'observed_source_ended_before_late_cancel')
        self.assertEqual(result['human'],'PENDING');self.assertEqual(result['physical_output'],'UNVERIFIED_NO_LOOPBACK')

    def test_late_cancel_needs_complete_counters_terminal_receipt_and_no_resumed_output(self):
        for kind in ('legacy','gap','counter','byte_counter','missing_zero','bool_zero','foreign','no_end',
                     'early_end','active','more_pcm','more_text'):
            report=self.late_cancel_report();s=report['native_final'];events=s['trace']['events'];receipt=events[-2]
            if kind=='legacy':s['trace'].pop('collection')
            elif kind=='gap':events[1]['observer_sequence']=1
            elif kind=='counter':s['trace']['binaryFrames']=2
            elif kind=='byte_counter':s['trace']['binaryBytes']=True
            elif kind=='missing_zero':receipt.pop('remainingSeconds')
            elif kind=='bool_zero':receipt['remainingSeconds']=False
            elif kind=='foreign':receipt['correlationId']='native_connection_foreign'
            elif kind=='no_end':events[-3]['data']='not an end'
            elif kind=='early_end':receipt.update(wall=105,updatedAt=105000)
            elif kind=='active':s['playback']['active']=True
            else:
                extra={'observer_sequence':len(events)+1,'wall':109.2}
                if kind=='more_pcm':
                    extra.update(type='audio_frame',bytes=0,correlation_id='native_connection_new')
                    s['trace']['binaryFrames']=2
                else:extra.update(type='gemini_response',text='late response')
                events.append(extra);s['trace']['eventSequence']=len(events);s['trace']['collection']['last_sequence']=len(events)
            with self.subTest(kind=kind):self.assert_partial(report,'native_terminal')

    def test_snapshot_missing_invalid_or_locked_fails_without_creation(self):
        missing=Path(self.fixture.temp.name)/'missing.db'
        self.assertFalse(subject.grade_snapshot(missing)['ok']);self.assertFalse(missing.exists())
        with closing(sqlite3.connect(self.fixture.db)) as c:
            c.execute('BEGIN EXCLUSIVE')
            self.assertFalse(subject.grade_snapshot(self.fixture.db)['ok'])
            c.rollback()
        with closing(sqlite3.connect(self.fixture.db)) as c,c:
            c.execute("UPDATE kv SET value='bad JSON' WHERE key='state'")
        self.assertFalse(subject.grade_snapshot(self.fixture.db)['ok'])


class ContinuousGradeEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.fixture=Fixture();self.addCleanup(self.fixture.close)
        before,after=self.fixture.before_and_after();report=make_report(before,after)
        empty=deepcopy(before);empty['question']=dict(question_id=None,attempt_id=None,question=None,attempt_evaluated=None)
        first=dict(input_wall=80,fixed_speech_end_wall=84,observation_end_wall=95,
            grade_after_turn=before,grade_next_input_pin={**PIN,'attempt_evaluated':False},
            native_reply='Which arrow?',native_pcm_frames=1)
        answer={**report['turns'][0],'grade_after_turn':after,'native_snapshot':deepcopy(report['native_final']),
            'native_reply':'Grade feedback','native_pcm_frames':1}
        followup=dict(input_wall=120,fixed_speech_end_wall=123,observation_end_wall=130,
            grade_after_turn=deepcopy(after),native_reply='Explanation only',native_pcm_frames=1)
        report.update(native_grade_chain=True,chain_before=empty,
            chain_empty_pin={k:PIN[k] for k in ('course_id','session_id')},turns=[first,answer,followup],
            wire_trace=[dict(dir='recv',type='response.function_call_arguments.done',name='study_quiz',t=85)],
            phrase_deliveries=[dict(connection_generation=3,started_wall=90),dict(connection_generation=3,started_wall=101.5)])
        report['chain_empty_pin']['_question_empty']=True
        def native_turn(start,token):
            return {'trace':{'events':[
                {'type':'user_transcript','wall':start+4.1,'text':'Synthetic stimulus'},
                {'type':'audio_frame','wall':start+5,'bytes':960,'correlation_id':token},
                {'type':'native_speech_playback_state','wall':start+5.1,'active':True,'sdk_speech_correlation_id':token},
                {'type':'gemini_response','wall':start+5.2,'text':'Synthetic reply'},
                {'type':'system','wall':start+6,'data':'turn end'}]},
                'playback':{'active':False,'remainingSeconds':0,'reason':'source_ended',
                    'correlationId':token,'updatedAt':(start+8)*1000}}
        first['native_snapshot']=native_turn(80,'native_connection_quiz')
        followup['native_snapshot']=native_turn(120,'native_connection_followup')
        answer['native_snapshot']['trace']['events'].append({'type':'system','wall':106,'data':'turn end'})
        for d in report['phrase_deliveries']:
            d.update(source_samples=48000,output_samples=47000,written_samples=47000,
                result='written_waiting_provider_boundary',input_timebase='arrival_derived_sample_estimate',
                sealed_wall=d['started_wall']-.1,first_write_wall=d['started_wall']+.01,completed_wall=d['started_wall']+.02)
        self.report=report

    def test_continuous_candidate_reuses_actual_one_grade_receipt_without_mutation(self):
        before=deepcopy(self.report);result=subject.grade_chain_acceptance(self.report)
        self.assertTrue(all(result['checks'].values()),result)
        self.assertTrue(all(result['answer_receipt']['checks'].values()),result)
        self.assertEqual(result['physical_output'],'UNVERIFIED_NO_LOOPBACK');self.assertEqual(result['human'],'PENDING')
        self.assertEqual(self.report,before)

    def test_prepared_or_nonempty_or_unobserved_quiz_is_not_continuous_proof(self):
        for kind in ('preparation','pending','no_tool','early_tool','no_pin'):
            r=deepcopy(self.report)
            if kind=='preparation':r['grade_quiz_preparation']={'ok':True}
            elif kind=='pending':r['chain_before']['question']['question_id']='already-pending'
            elif kind=='no_tool':r['wire_trace']=[]
            elif kind=='early_tool':r['wire_trace'][0]['t']=82
            else:r['turns'][0].pop('grade_next_input_pin')
            with self.subTest(kind=kind):self.assertFalse(all(subject.grade_chain_acceptance(r)['checks'].values()))

    def test_reconnect_or_duplicate_delivery_or_extra_followup_grade_is_partial(self):
        for kind in ('reconnect','duplicate','extra_grade','changed_question','missing_answer_trace','timeout'):
            r=deepcopy(self.report)
            if kind=='reconnect':r['phrase_deliveries'][1]['connection_generation']=4
            elif kind=='duplicate':r['phrase_deliveries'].append(deepcopy(r['phrase_deliveries'][0]))
            elif kind=='extra_grade':r['turns'][2]['grade_after_turn']['qa_records'].append({'id':'unexpected'})
            elif kind=='changed_question':r['turns'][2]['grade_after_turn']['question']['question_id']='new-question'
            elif kind=='missing_answer_trace':r['turns'][1]['native_snapshot']['trace']['events']=[]
            else:r['turns'][2]['turn_timeout']=True
            with self.subTest(kind=kind):self.assertFalse(all(subject.grade_chain_acceptance(r)['checks'].values()))
        self.assertFalse(all(subject.grade_chain_acceptance({})['checks'].values()))

    def test_failed_partial_or_bool_delivery_and_missing_turn_receipts_fail(self):
        for changes in ({'result':'failed'},{'written_samples':0},{'written_samples':True},
                {'connection_generation':True},{'completed_wall':115}):
            r=deepcopy(self.report);r['phrase_deliveries'][1].update(changes)
            self.assertFalse(subject.grade_chain_acceptance(r)['checks']['same_connection_first_two_inputs'])
        for index in (0,2):
            for kind in ('no_snapshot','no_asr','no_end','no_pcm','bool_pcm','active_playback','wrong_token'):
                r=deepcopy(self.report);t=r['turns'][index]
                if kind=='no_snapshot':t.pop('native_snapshot')
                else:
                    s=t['native_snapshot']
                    if kind=='no_asr':s['trace']['events']=[e for e in s['trace']['events'] if e['type']!='user_transcript']
                    elif kind=='no_end':s['trace']['events']=[e for e in s['trace']['events'] if e['type']!='system']
                    elif kind in ('no_pcm','bool_pcm'):
                        for e in s['trace']['events']:
                            if e['type']=='audio_frame':e['bytes']=0 if kind=='no_pcm' else True
                    elif kind=='active_playback':s['playback']['active']=True
                    else:s['playback']['correlationId']='native_connection_other'
                with self.subTest(index=index,kind=kind):
                    self.assertFalse(subject.grade_chain_acceptance(r)['checks']['three_completed_native_turns'])


class CorrectionEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.fixture = Fixture()
        self.report = make_correction(self.fixture)

    def tearDown(self):
        self.fixture.close()

    def assert_partial(self, report, check):
        result = subject.grade_acceptance(report)
        self.assertEqual(result['result'], 'FAIL_OR_PARTIAL', result)
        self.assertFalse(result['checks'][check], result)

    def test_actual_json_correction_survives_session_restart_and_preserves_wrong_answer(self):
        result = subject.grade_acceptance(self.report)
        self.assertTrue(all(result['checks'].values()), result)
        self.assertEqual(result['grade_intent'], 'correction')
        self.assertEqual(result['physical_output'], 'UNVERIFIED_NO_LOOPBACK')
        self.assertEqual(result['human'], 'PENDING')
        before = self.report['grade_before']
        old = next(r for r in before['qa_records'] if r['id'] == 'new-qa')
        self.assertNotEqual(old['session_id'], before['session_id'])
        self.assertEqual(old['topic_id'], 'topic')
        self.assertNotIn('PRIVATE', json.dumps(self.report))
        # Backward raw-report JSON is accepted, with all three question fields checked.
        for snapshot in ('grade_before', 'grade_after'):
            for row in self.report[snapshot]['qa_records']:
                if isinstance(row['question'], dict): row['question'] = json.dumps(row['question'])
        self.assertTrue(all(subject.grade_acceptance(self.report)['checks'].values()))

    def test_wrong_mode_or_pending_or_correct_origin_rejects(self):
        for mode in ('answer', 'review', '', None):
            report = deepcopy(self.report); report['grade_intent'] = mode
            check = 'pending_four_ids' if mode == 'answer' else 'supported_grade_intent'
            self.assert_partial(report, check)
        report = deepcopy(self.report); report['grade_before']['question']['attempt_evaluated'] = False
        self.assert_partial(report, 'evaluated_wrong_or_partial_four_ids')
        report = deepcopy(self.report); report['grade_before']['last_answer_evaluation'] = {'verdict':'correct', 'score':1}
        self.assert_partial(report, 'evaluated_wrong_or_partial_four_ids')
        report = deepcopy(self.report); report.pop('grade_intent')
        self.assert_partial(report, 'pending_four_ids')

    def test_actual_partial_origin_is_retryable_but_last_grade_alone_is_not_lineage(self):
        fixture = Fixture()
        try:
            report = make_correction(fixture, partial_origin=True)
            self.assertTrue(all(subject.grade_acceptance(report)['checks'].values()))
            report['grade_before']['last_answer_evaluation'] = dict(GRADE)
            self.assert_partial(report, 'correction_origin_formal_lineage')
        finally:
            fixture.close()

    def test_same_attempt_changed_question_course_or_session_rejects(self):
        for key, value in (('attempt_id', PIN['attempt_id']), ('attempt_id', ''), ('question_id', 'foreign'), ('question', 'another prompt')):
            report = deepcopy(self.report); report['grade_after']['question'][key] = value
            self.assert_partial(report, 'same_question_new_attempt_evaluated')
        for key in ('course_id', 'session_id'):
            report = deepcopy(self.report); report['grade_after'][key] = 'foreign'
            self.assert_partial(report, 'same_question_new_attempt_evaluated')

    def test_old_wrong_formal_join_must_be_unique_exact_and_saved(self):
        for kind in ('qa_missing', 'formal_missing', 'old_aid', 'old_qid', 'old_input', 'old_session',
                     'old_course', 'old_grade', 'degraded', 'duplicate_formal', 'duplicate_qa'):
            report = deepcopy(self.report); before = report['grade_before']
            qa = next(r for r in before['qa_records'] if r['id']=='new-qa')
            history = before['grade_interactions'][0]; metadata = history['metadata']
            if kind=='qa_missing':before['qa_records'].remove(qa)
            elif kind=='formal_missing':before['grade_interactions']=[]
            elif kind=='old_aid':qa['question']['attempt_id']='foreign'
            elif kind=='old_qid':qa['question']['question_id']='foreign'
            elif kind=='old_input':qa['user_answer']='different'
            elif kind=='old_session':qa['session_id']='different'
            elif kind=='old_course':metadata['material_context']['course_id']='foreign'
            elif kind=='old_grade':qa['eval_result']['score']=0.5
            elif kind=='degraded':metadata['degraded']=True
            elif kind=='duplicate_formal':
                duplicate=deepcopy(history); duplicate['id']=100; before['grade_interactions'].append(duplicate)
            else:
                duplicate=deepcopy(qa); duplicate['id']='duplicate'; before['qa_records'].append(duplicate)
            with self.subTest(kind=kind): self.assert_partial(report, 'correction_origin_formal_lineage')

    def test_deleted_wrong_old_mutation_extra_grade_and_topic_drift_reject(self):
        for kind, check in (('deleted', 'old_qa_preserved'), ('mutated', 'old_qa_preserved'),
                            ('old_formal_mutated','old_grade_interactions_preserved'),
                            ('extra', 'exactly_one_new_formal_interaction'), ('topic', 'same_concept_topic'),
                            ('missing_topic', 'same_concept_topic'), ('missing_old_topic', 'same_concept_topic')):
            report = deepcopy(self.report); after = report['grade_after']
            old=next(r for r in after['qa_records'] if r['id']=='new-qa')
            new=next(r for r in after['qa_records'] if r['id']=='corrected-qa')
            if kind=='deleted':after['qa_records'].remove(old)
            elif kind=='mutated':old['row_sha256']='0'*64
            elif kind=='old_formal_mutated':after['grade_interactions'][0]['input_text']='changed'
            elif kind=='extra':
                duplicate=deepcopy(after['grade_interactions'][-1]);duplicate['id']=100;after['grade_interactions'].append(duplicate)
            elif kind=='topic':new['topic_id']='different'
            elif kind=='missing_topic':new.pop('topic_id')
            else:next(r for r in report['grade_before']['qa_records'] if r['id']=='new-qa').pop('topic_id')
            with self.subTest(kind=kind):self.assert_partial(report,check)

    def test_new_json_metadata_and_marker_attempt_are_not_original_attempt(self):
        for kind, check in (('qa_aid','formal_identity_and_asr'), ('qa_qid','formal_identity_and_asr'),
                            ('formal_aid','formal_identity_and_asr'), ('marker_pin','marker_chain'),
                            ('marker_result','marker_chain')):
            report=deepcopy(self.report)
            new=next(r for r in report['grade_after']['qa_records'] if r['id']=='corrected-qa')
            if kind=='qa_aid':new['question']['attempt_id']=PIN['attempt_id']
            elif kind=='qa_qid':new['question']['question_id']='foreign'
            elif kind=='formal_aid':report['grade_after']['grade_interactions'][-1]['metadata']['attempt_id']=PIN['attempt_id']
            elif kind=='marker_pin':report['grade_markers'][1]['attempt_id']='a-correction'
            else:report['grade_markers'][1]['result_attempt_id']=PIN['attempt_id']
            with self.subTest(kind=kind):self.assert_partial(report,check)

    def test_empty_binary_frame_is_not_pcm_and_still_requires_exact_owner_and_time(self):
        report=deepcopy(self.report)
        events=report['native_final']['trace']['events']
        empty={'type':'audio_frame','wall':106,'correlation_id':'native_connection_new','bytes':0}
        events.append(empty); report['native_final']['trace']['binaryFrames']=2
        self.assertTrue(all(subject.grade_acceptance(report)['checks'].values()))
        for value in (-1, True, False, float('nan'), float('inf'), 0.5, None, '0'):
            bad=deepcopy(report);bad['native_final']['trace']['events'][-1]['bytes']=value
            with self.subTest(bytes=value):self.assert_partial(bad,'new_token_pcm_after_grade')
        for key,value in (('correlation_id','native_connection_old'),('wall',103)):
            bad=deepcopy(report);bad['native_final']['trace']['events'][-1][key]=value
            self.assert_partial(bad,'new_token_pcm_after_grade')
        bad=deepcopy(report)
        for event in bad['native_final']['trace']['events']:
            if event.get('type')=='audio_frame':event['bytes']=0
        self.assert_partial(bad,'new_token_pcm_after_grade')
        self.assert_partial(bad,'new_token_playback_scheduled')
        # An empty message cannot allow a playback schedule before real PCM.
        bad=deepcopy(report);events=bad['native_final']['trace']['events']
        events[-1]['wall']=104.5
        next(e for e in events if e['type']=='native_speech_playback_state')['wall']=104.6
        self.assert_partial(bad,'new_token_playback_scheduled')


if __name__=='__main__':unittest.main(verbosity=2)
