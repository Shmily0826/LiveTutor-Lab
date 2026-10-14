"""One bounded actual-role pending-quiz course/host continuation, without devices."""
from __future__ import annotations
import argparse,asyncio,base64,hashlib,json,os,socket,sqlite3,subprocess,time
from pathlib import Path
from urllib.parse import quote
from urllib.request import build_opener,ProxyHandler
import websockets
import neko_desktop_tutor_host as host
from neko_daily_voice_probe import stop_owned_host
from neko_tutor_start import plugin_server_ready
from neko_lab_client import LabClient
from test_neko_product_course_memory import models

ROOT=Path(__file__).resolve().parents[1]
LEDGER=ROOT/'benchmarks/raw/neko-desktop-egress-cap'
def digest(value):return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def snapshot(store):
    db=store/'N.E.K.O/plugins/study_companion/data/study_companion.db'
    with sqlite3.connect(db.as_uri()+'?mode=ro',uri=True) as connection:
        connection.execute('PRAGMA query_only=ON')
        state=json.loads(connection.execute("SELECT value FROM kv WHERE key='state'").fetchone()[0])
        course_id=str(state.get('study_course_id') or 'general')
        material_key='submitted_image:'+hashlib.sha256(course_id.encode()).hexdigest()
        saved=connection.execute('SELECT value FROM kv WHERE key=?',(material_key,)).fetchone()
        image=(json.loads(saved[0]).get('image') or '') if saved else ''
        encoded=image.partition(',')[2] if image.startswith('data:') else image
        question=state.get('current_question') or {}
        rows=connection.execute('SELECT * FROM interactions ORDER BY id').fetchall()
        kinds=[row[0] for row in connection.execute('SELECT kind FROM interactions ORDER BY id').fetchall()]
        qa=connection.execute('SELECT * FROM qa_records ORDER BY id').fetchall()
    return {'course_id':state.get('study_course_id'),'session_id':state.get('study_session_id'),
            'question':models.public_current_question_payload(question),
            'question_state':('evaluated' if question.get('attempt_evaluated') else 'pending') if question else 'none',
            'image_sha256':hashlib.sha256(base64.b64decode(encoded)).hexdigest(),
            'row_hashes':[digest(row) for row in rows],'kinds':kinds,
            'qa_count':len(qa),'qa_sha256':digest(qa)}
def receipts(store):
    path=store/'session-tool-audit.jsonl'
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line] if path.exists() else []

async def main(args):
    output=args.output.resolve();store=(ROOT/'benchmarks/raw'/args.store).resolve()
    if (output.exists() or not output.is_relative_to((ROOT/'benchmarks/raw/evidence').resolve())
            or not args.store.startswith('neko-daily-continuous-text-') or Path(args.store).name!=args.store
            or not store.is_relative_to((ROOT/'benchmarks/raw').resolve()) or (store.exists() and not args.resume_from)):
        raise RuntimeError('fresh owned fixture and unique private evidence only; never restore/copy user history')
    for port in (host.MAIN_PORT,host.PLUGIN_PORT):
        with socket.socket() as check:
            if check.connect_ex(('127.0.0.1',port))==0:raise RuntimeError('existing host owns ports')
    before=json.loads(LEDGER.read_text(encoding='utf-8'))
    if before['round']!='bargein-autocheck-20261012' or before['spent'].get('api.deepseek.com',0)>=2000:
        raise RuntimeError('same-round ledger required; no reset')
    images={name:ROOT/f'benchmarks/raw/evidence/diagram-input-{name}.png' for name in ('forward','reverse')}
    expected={'forward':'057d5bac5ae440dfa0d3269f5138f1188fa182bc0fce81435676c6a4caa65dcc',
              'reverse':'1956a09783dd66b089979eead8729592c9d48cbe8770041badded5ff2347d700'}
    assert all(hashlib.sha256(path.read_bytes()).hexdigest()==expected[name] for name,path in images.items())
    prior=None
    if args.resume_from:
        path=args.resume_from.resolve(strict=True)
        if not path.is_relative_to((ROOT/'benchmarks/raw/evidence').resolve()):raise RuntimeError('private previous scene only')
        prior=json.loads(path.read_text(encoding='utf-8'))
        if (prior.get('store')!=str(store) or not prior.get('finalized') or prior.get('failure')!='AssertionError: '
                or not prior.get('held') or not prior.get('other_course') or prior.get('returned')
                or len(prior.get('turns',[]))!=1 or len(prior.get('steps',[]))!=4
                or not (store/'task-provenance.json').is_file()):
            raise RuntimeError('only finalized image-audit interruption after one quiz and two images may continue')
        actual=snapshot(store)
        assert actual['course_id']==prior['other_course']['course_id'] and not actual['question']
        assert actual['row_hashes']==prior['other_course']['row_hashes'] and actual['qa_count']==0
        assert actual['image_sha256']==expected['reverse']
        with sqlite3.connect((store/'N.E.K.O/plugins/study_companion/data/study_companion.db').as_uri()+'?mode=ro',uri=True) as connection:
            connection.execute('PRAGMA query_only=ON')
            checkpoint=json.loads(connection.execute('SELECT value FROM kv WHERE key=?',('course_teaching_progress:'+prior['courses'][0],)).fetchone()[0])
        assert models.public_current_question_payload(checkpoint['current_question'])==prior['held']['question']
    output.parent.mkdir(parents=True,exist_ok=True)
    if prior is None:store.mkdir(exist_ok=False)
    course_a=args.store+'-a';course_b=args.store+'-b'
    report={'before_ledger':before,'store':str(store),'courses':[course_a,course_b],'hosts':[],
            'steps':[],'turns':[],'native':False,'audio':False,'capture':False,'loopback':False,
            'source_sha256':{name:hashlib.sha256((host.PRODUCT/'payload/study_companion'/name).read_bytes()).hexdigest()
                             for name in ('__init__.py','store.py','entry_tutor_summary_entries.py','entry_tutor_answer_entries.py','models.py','study_avatar_tools.py')}}
    if prior is None:
        (store/'task-provenance.json').write_text(json.dumps({'purpose':'pending quiz cross-course/host continuation','fresh':True,'created':time.time()}),encoding='utf-8')
    else:
        report['resumed_from']=str(args.resume_from.resolve());report['original_held']=prior['held']
        assert report['source_sha256']==prior['source_sha256']
    def save():output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    save();process=None;handle=None;client=LabClient()
    def budget():
        live=json.loads(LEDGER.read_text(encoding='utf-8'))
        if live['round']!=before['round'] or live['spent'].get('api.deepseek.com',0)-before['spent'].get('api.deepseek.com',0)>=25:
            raise RuntimeError('bounded scene spent/round stop; no retry')
    async def boot(number):
        nonlocal process,handle
        budget();handle=output.with_suffix(f'.host{number}.log').open('xb')
        process=subprocess.Popen([str(host.SOURCE_PYTHON),'-X','utf8','-B',str(ROOT/'scripts/neko_desktop_tutor_host.py'),
            '--source','--study-vision','--session-tool-audit','--core-provider','deepseek','--store',args.store,
            '--hold','420' if number==1 else '250','--seconds','100','--api-budget','8',
            '--egress-budget','2000','--allow-host','www.lanlan.app:unlimited','--allow-host','www.lanlan.tech:0',
            '--budget-round','bargein-autocheck-20261012'],cwd=ROOT,
            env={**os.environ,'PYTHONIOENCODING':'utf-8','NEKO_TASK_SILENT':'1'},stdout=handle,stderr=subprocess.STDOUT)
        report['hosts'].append({'number':number,'launcher_pid':process.pid});save()
        ready,reason=await asyncio.to_thread(plugin_server_ready,100,process)
        if not ready:raise RuntimeError('owned host not ready: '+reason)
        deployed=store/'plugin-code/study_companion'
        assert all(hashlib.sha256((deployed/name).read_bytes()).hexdigest()==value for name,value in report['source_sha256'].items() if name!='study_avatar_tools.py')
        report['hosts'][-1]['ready']=True;save()
    async def stop():
        nonlocal process,handle
        if process:
            await asyncio.to_thread(stop_owned_host,process);report['hosts'][-1]['exit']=process.poll();process=None
        if handle:handle.close();handle=None
        save()
    async def sdk(entry,fields):
        budget();result=await asyncio.to_thread(client.call,entry,fields)
        safe={key:value for key,value in fields.items() if key!='image_base64'}
        report['steps'].append({'entry':entry,'arguments':safe,'result':result});save()
        if result['data'].get('degraded'):raise RuntimeError('degraded SDK scene; stop without retry')
        return result['data']
    async def role(question,label):
        budget();audit_before=len(receipts(store));opener=build_opener(ProxyHandler({}))
        with opener.open('http://127.0.0.1:48911/api/characters/current_catgirl',timeout=10) as response:
            character=json.load(response)['current_catgirl']
        turn={'label':label,'question':question,'events':[],'started':time.time()};report['turns'].append(turn);save()
        async with websockets.connect('ws://127.0.0.1:48911/ws/'+quote(character),proxy=None,max_size=2*1024*1024) as ws:
            async def ping():
                while True:await asyncio.sleep(5);await ws.send(json.dumps({'action':'ping'}))
            task=asyncio.create_task(ping())
            try:
                await ws.send(json.dumps({'action':'start_session','input_type':'text','new_session':False,'request_id':label+'-ready'}))
                deadline=time.monotonic()+40
                while time.monotonic()<deadline:
                    frame=await asyncio.wait_for(ws.recv(),max(.1,deadline-time.monotonic()))
                    if isinstance(frame,bytes):raise RuntimeError('unexpected audio')
                    event=json.loads(frame)
                    if event.get('type')=='session_started':break
                    if event.get('type') in ('error','session_failed','session_ended_by_server'):raise RuntimeError('text session failed')
                else:raise TimeoutError('text readiness timeout')
                await ws.send(json.dumps({'action':'stream_data','input_type':'text','data':question,'request_id':label},ensure_ascii=False))
                deadline=time.monotonic()+110
                while time.monotonic()<deadline:
                    frame=await asyncio.wait_for(ws.recv(),max(.1,deadline-time.monotonic()))
                    if isinstance(frame,bytes):raise RuntimeError('unexpected audio')
                    event=json.loads(frame);turn['events'].append(event);save()
                    if event.get('type') in ('error','session_failed','session_ended_by_server'):raise RuntimeError('provider/session error; no retry')
                    if event.get('type')=='system' and event.get('data')=='turn end':break
                else:raise TimeoutError('text turn timeout')
                turn['reply']=''.join(str(event.get('text') or '') for event in turn['events'] if event.get('type') in ('gemini_response','ai_response','text_response'))
                turn['session_receipts']=receipts(store)[audit_before:];turn['after']=snapshot(store);turn['completed']=time.time();save()
                await ws.send(json.dumps({'action':'end_session','reason':'bounded_continuation_turn'}))
            finally:task.cancel();await asyncio.gather(task,return_exceptions=True)
        print('Completed actual text turn:',label,flush=True)
    try:
        await boot(1)
        if prior is None:
            await sdk('study_set_course',{'course_id':course_a})
            await sdk('study_submit_image',{'image_base64':base64.b64encode(images['forward'].read_bytes()).decode(),
                      'text':'用两句话解释当前图片中的箭头，不出题。','expected_course_id':course_a})
            await role('请根据当前图片只出一道中文题，完整说出题目，然后等我回答；不要告诉我答案。','quiz')
            held=snapshot(store);report['held']=held;save()
            assert held['course_id']==course_a and held['question_state']=='pending' and held['question'].get('question_id') and held['kinds'].count('question_generate')==1
            await sdk('study_set_course',{'course_id':course_b})
            await sdk('study_submit_image',{'image_base64':base64.b64encode(images['reverse'].read_bytes()).decode(),
                      'text':'用两句话解释当前图片中的箭头，不出题。','expected_course_id':course_b})
            other=snapshot(store);report['other_course']=other;save()
            assert other['course_id']==course_b and not other['question'] and other['image_sha256']==expected['reverse']
        else:
            held=prior['held'];report['held']=held;report['continued_at']='return-course only; no new quiz or image submission';save()
        await role(f'回到课程 {course_a}，先读取实际学习状态，把刚才尚未回答的题原样复述，继续等我回答，不另出题、评分或透露答案。','return-course')
        returned=snapshot(store);report['returned']=returned;save()
        assert returned['course_id']==course_a and returned['question']==held['question'] and returned['image_sha256']==expected['forward']
        assert any(row['action']=='set_course' and row['requested_course']==course_a and row['current_question']==held['question'] for row in report['turns'][-1]['session_receipts'])
        await stop();await boot(2)
        restarted=snapshot(store);report['restarted']=restarted;save()
        assert restarted['course_id']==course_a and restarted['question']==held['question'] and restarted['image_sha256']==expected['forward']
        await role(f'读取课程 {course_a} 的当前学习状态，把尚未回答的题原样复述，继续等我回答；不要新开学习会话，不另出题、评分或透露答案。','restart-status')
        final=snapshot(store);report['final']=final
        report['checks']={'same_held_question':final['question']==held['question'],'still_pending':final['question_state']=='pending',
            'one_question_only':final['kinds'].count('question_generate')==1,'no_grade_or_summary':not any(kind in final['kinds'] for kind in ('answer_evaluate','summarize_session')),
            'no_qa':final['qa_count']==0,'original_prefix_unchanged':final['row_hashes'][:len(held['row_hashes'])]==held['row_hashes'],
            'status_tool_read_actual_question':any(row['action']=='status' and row['current_question']==held['question'] and row['question_state']=='pending' for row in report['turns'][-1]['session_receipts'])}
        if not all(report['checks'].values()):raise RuntimeError('continuation integrity check failed')
        report['result']='TRANSPORT_DB_COMPLETED_REQUIRES_REPLY_SEMANTIC_REVIEW'
    except Exception as error:
        report['failure']=type(error).__name__+': '+str(error);report['result']='FAIL_OR_PARTIAL'
    finally:
        await stop();report['after_ledger']=json.loads(LEDGER.read_text(encoding='utf-8'));report['finalized']=True;save()
        print(json.dumps({'report':str(output),'result':report['result'],'failure':report.get('failure'),'spent':report['after_ledger']['spent']},ensure_ascii=False),flush=True)
    return 1 if report.get('failure') else 0

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--store',required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--resume-from',type=Path,help='continue only the finalized image-audit interruption; do not repeat accepted preparation')
    raise SystemExit(asyncio.run(main(parser.parse_args())))
