"""Real plugin SDK/HTTP callback with a local model stub, no voice or external calls."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import threading
import time
import ast
import copy
import logging
import sys
import types
import sqlite3
from neko_daily_failure_probe import FailureStub,KIND,launch_plan,file_sha256,GLOBAL_LEDGER
from neko_daily_voice_probe import stop_owned_host
from neko_tutor_start import plugin_server_ready
from neko_native_avatar_toolchain import call
import neko_desktop_tutor_host as host

ROOT=Path(__file__).resolve().parents[1]

def teaching_database_checks(store, quiz, session_id):
    """Read this fresh fixture's committed IDs; avatar replies intentionally omit them."""
    path=(store/'N.E.K.O/plugins/study_companion/data/study_companion.db').resolve(strict=True)
    with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as db:
        db.execute('PRAGMA query_only=ON')
        grades=[(sid,json.loads(metadata)) for sid,metadata in db.execute(
            "SELECT session_id,metadata FROM interactions WHERE kind='answer_evaluate'")]
        summaries=[(sid,json.loads(metadata)) for sid,metadata in db.execute(
            "SELECT session_id,metadata FROM interactions WHERE kind='summarize_session'")]
        qa=[(sid,json.loads(question)) for sid,question in db.execute('SELECT session_id,question FROM qa_records')]
    matches=lambda item: item[0]==session_id and all(item[1].get(key)==quiz.get(key) for key in ('question_id','attempt_id'))
    return {'grade_matches_quiz':len(grades)==1 and matches(grades[0]),
            'quiz_committed_once':len(qa)==1 and matches(qa[0]),
            'summary_session_matches':len(summaries)==1 and summaries[0][0]==session_id and
                summaries[0][1].get('material_context',{}).get('session_id')==session_id}

def core_fixture(report, tool_names=('study_explain',)):
    """Actual registry/envelope/remote-dispatch code, patched core methods, fake output owner.

    The fake provider never opens a connection or plays audio. Only the SDK
    callback and local model stub are real; this is not Native/device evidence.
    """
    from test_neko_material_audio import Harness
    tree=ast.parse((ROOT/'benchmarks/raw/neko-product-host/main_logic/tool_calling.py').read_text(encoding='utf-8'))
    tree.body=[node for node in tree.body if not (
        isinstance(node,ast.ImportFrom) and node.module=='utils.logger_config') and not (
        isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id=='logger' for target in node.targets))]
    module=types.ModuleType('_material_probe_actual_tool_registry');sys.modules[module.__name__]=module
    module.logger=logging.getLogger('material-core-sdk-probe')
    exec(compile(tree,'actual main_logic/tool_calling.py','exec'),module.__dict__)
    import httpx
    client=httpx.AsyncClient(trust_env=False)
    route_tree=ast.parse((ROOT/'benchmarks/raw/neko-product-host/main_routers/tool_router.py').read_text(encoding='utf-8'))
    remote=next(node for node in route_tree.body if getattr(node,'name','')=='_remote_dispatch')
    ns={**module.__dict__, '_get_http_client':lambda:client,
        '_note_dispatch_outcome':lambda *args,**kwargs:None,
        '_is_connection_level_failure':lambda error:False}
    exec(compile(ast.Module(body=[remote],type_ignores=[]),'actual tool_router.py','exec'),ns)
    captured_payloads=[]
    async def dispatch(call_value, metadata):
        result=await ns['_remote_dispatch'](call_value,metadata)
        captured_payloads.append(copy.deepcopy(result.output))
        return result
    core=Harness();core.lanlan_name='MaterialSDKTestRole'
    core.tool_registry=module.ToolRegistry(remote_dispatcher=dispatch)
    for name in tool_names:
        core.tool_registry.register(module.ToolDefinition(name=name,description='local SDK proof only',metadata={
            'source':'plugin:study_companion','callback_url':f'http://127.0.0.1:48916/api/llm-tools/callback/study_companion/{name}',
            'timeout_seconds':20}))
    async def explain(fields, name='study_explain'):
        # Begin without model-supplied recipient; the patched core must supply it.
        original={key:value for key,value in fields.items() if key!='_ctx'}
        value=module.ToolCall(name=name,arguments=original,call_id='local-core-sdk-proof-'+name)
        result=await core._on_tool_call(value,invoking_session=core.session)
        payload=captured_payloads[-1]
        owner=getattr(core,'_study_material_output_owner',None)
        checks={'actual_remote_binding_present':isinstance(payload,dict) and bool(payload.get('_study_material_binding')),
            'core_bound_current_owner':owner is not None and owner.get('tool_name')==name,
            'host_only_binding_stripped':isinstance(result.output,dict) and '_study_material_binding' not in result.output,
            'model_arguments_not_mutated':'_ctx' not in original,
            'spoken_field_present':isinstance(result.output,dict) and bool(result.output.get('question' if name=='study_quiz' else 'reply'))}
        report.setdefault('core_checks_by_tool',{})[name]=checks
        report['core_checks']=checks
        return {'output':result.output,'is_error':result.is_error}
    return explain,client

async def main(args):
    if args.output.exists():raise RuntimeError('preserve previous SDK attempt')
    for port in (host.MAIN_PORT,host.PLUGIN_PORT):
        with socket.socket() as probe:
            if probe.connect_ex(('127.0.0.1',port))==0:raise RuntimeError('leave existing host running')
    store=ROOT/'benchmarks/raw'/args.store
    if not args.store.startswith('neko-failure-material-sdk-') or Path(args.store).name!=args.store:
        raise ValueError('fresh isolated SDK fixture only')
    store.mkdir(exist_ok=False)
    stub=FailureStub(maximum_requests=16 if args.teaching_chain else 8);stub.mode='explain'
    worker=threading.Thread(target=stub.serve_forever,daemon=True);worker.start()
    manifest={'kind':KIND,'nonce':secrets.token_hex(16),'store':str(store.resolve()),
              'stub_url':stub.base_url,'global_ledger_sha256':file_sha256(GLOBAL_LEDGER)}
    plan=launch_plan(manifest,hold=160)
    report={'before_ledger':json.loads(GLOBAL_LEDGER.read_text()),'room_microphone':False,
            'voice_session':False,'supplier':'local pre-existing failure stub only, not real model quality','calls':[]}
    output_handle=args.output.with_suffix('.host.log').open('wb')
    process=subprocess.Popen(plan['argv'],cwd=ROOT,env={**os.environ,'PYTHONIOENCODING':'utf-8'},
                             stdout=output_handle,stderr=subprocess.STDOUT)
    core_explain=core_client=None
    def save():args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    try:
        ready,reason=await asyncio.to_thread(plugin_server_ready,75,process)
        report.update(host_pid=process.pid,host_ready=ready)
        if not ready:raise RuntimeError('SDK host not ready: '+reason)
        print('Local SDK callback host ready; external egress denied, no voice',flush=True)
        if args.through_core or args.teaching_chain:
            names=('study_quiz','study_answer','study_summary') if args.teaching_chain else ('study_explain',)
            core_explain,core_client=core_fixture(report,names)
            report['core_fixture']='patched actual core + real registry/remote callback + fake native owner; no native/provider/device'
        steps=(
            ('study_session',{'action':'set_course','course_id':'material-sdk-local'}),
            ('study_explain',{'question':'Explain this literal source briefly','text':'int count = 1;',
                              '_ctx':{'lanlan_name':'MaterialSDKTestRole'}}),
            ('study_session',{'action':'set_course','course_id':'material-sdk-new'}),
            ('study_material',{}),
        )
        if args.teaching_chain:
            steps=(steps[0],('study_quiz',{'topic':'local-failure-fixture'}),
                   ('study_answer',{'answer':'函数的输入'}),
                   ('study_summary',{'focus':'local protocol test'}),*steps[2:])
        for name,fields in steps:
            if args.teaching_chain and name in names:
                stub.mode={'study_quiz':'question','study_answer':'answer','study_summary':'summary'}[name]
                result=await core_explain(fields,name)
            else:
                result=await core_explain(fields) if core_explain and name=='study_explain' else await asyncio.to_thread(call,name,fields)
            report['calls'].append({'name':name,'result':result});save()
            if result.get('is_error'):raise RuntimeError('SDK callback returned error')
        output=report['calls'][1]['result'].get('output')
        if isinstance(output,str):output=json.loads(output)
        metadata=report['calls'][-1]['result'].get('output',{}).get('material_control_submission',[])
        report['checks']={'native_wrapper_binding_present':report.get('core_checks',{}).get('actual_remote_binding_present',bool(output.get('_study_material_binding'))),
                          'explicit_role_survives_sdk':bool(metadata) and all(item.get('target_lanlan')=='MaterialSDKTestRole' for item in metadata),
                          'sdk_accepted_control':bool(metadata) and all(item.get('status')=='submitted' for item in metadata)}
        if args.teaching_chain:
            quiz,grade,summary=(item['result']['output'] for item in report['calls'][1:4])
            report['checks'].update(quiz_ids_present=bool(quiz.get('question_id') and quiz.get('attempt_id')),
                stub_grade_returned=grade.get('score')==100 and not grade.get('degraded'),
                summary_returned=bool(summary.get('reply')) and not summary.get('degraded'))
            report['checks'].update(teaching_database_checks(store,quiz,report['calls'][0]['result']['output']['session_id']))
        report['result']='PASS_TEACHING_CORE_SDK_LOCAL_STUB_ONLY' if args.teaching_chain else ('PASS_CORE_SDK_LOCAL_STUB_ONLY' if args.through_core else 'PASS_SDK_LOCAL_STUB_ONLY')
        if not all(report['checks'].values()) or any(not all(checks.values()) for checks in report.get('core_checks_by_tool',{}).values()):report['result']='FAIL_OR_PARTIAL'
    except Exception as error:
        report['failure']=type(error).__name__+': '+str(error);report['result']='FAIL_OR_PARTIAL'
    finally:
        if core_client is not None:await core_client.aclose()
        await asyncio.to_thread(stop_owned_host,process);output_handle.close()
        stub.shutdown();stub.server_close();worker.join(timeout=3)
        report['stub_requests']=len(stub.records);report['stub_unexpected_credential']=stub.unexpected_credential
        report['after_ledger']=json.loads(GLOBAL_LEDGER.read_text());report['global_ledger_unchanged']=report['after_ledger']==report['before_ledger']
        if not report['global_ledger_unchanged'] or stub.unexpected_credential:report['result']='FAIL_OR_PARTIAL'
        save();print(json.dumps({k:report.get(k) for k in ('result','failure','checks','stub_requests','global_ledger_unchanged')},ensure_ascii=False),flush=True)
    return 0 if report['result'].startswith('PASS_') else 1

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--store',required=True);parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--through-core',action='store_true')
    parser.add_argument('--teaching-chain',action='store_true',help='quiz/held answer/history summary through actual Core and SDK; no real model/audio')
    raise SystemExit(asyncio.run(main(parser.parse_args())))
