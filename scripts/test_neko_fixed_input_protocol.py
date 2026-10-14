"""Actual JS frames -> isolated actual current-router branch -> actual ASR queue.

No app startup, listener, model, capture device, WAV or playback. The router's
outer display/old-connection guard is outside this fixture's proof scope.
"""
import ast,atexit,json,os,subprocess,tempfile,types,unittest
from pathlib import Path
from unittest.mock import AsyncMock
# Registry dependencies load ConfigManager even though Core is AST-isolated.
# Give that initialization a disposable store before importing the fixture.
runtime_store=tempfile.TemporaryDirectory(prefix='neko-protocol-')
atexit.register(runtime_store.cleanup)
for key in ('NEKO_STORAGE_SELECTED_ROOT','NEKO_STORAGE_ANCHOR_ROOT','NEKO_STORAGE_CLOUDSAVE_ROOT'):
    os.environ[key]=runtime_store.name
import test_neko_fixed_input_authority as authority

ROOT=Path(__file__).resolve().parents[1]
tree=ast.parse((authority.HOST/'main_routers/websocket_router.py').read_text(encoding='utf-8'))
claims=[n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='_claim_voice_input_connection']
assert len(claims)==1,'router voice claim shape changed'
claim=claims[0]
def is_control(n):
    return isinstance(n,ast.If) and isinstance(n.test,ast.Compare) and isinstance(n.test.left,ast.Name) and n.test.left.id=='action' and any(isinstance(v,ast.Constant) and v.value=='voice_input_control' for v in n.test.comparators)
branches=[n for n in ast.walk(tree) if is_control(n)]
assert len(branches)==1,'router current-control branch shape changed'
branch=branches[0]
wrapper=ast.parse('''def make_dispatch(manager, connection_id, websocket):
    lanlan_name=manager.lanlan_name
    session_manager={lanlan_name:manager}
    this_session_id=connection_id
    voice_input_claimed=False
    _voice_connection_sockets={}
    async def dispatch(messages):
        for message in messages:
            pass
    return dispatch
''')
outer=wrapper.body[0]
outer.body.insert(-2,claim)
dispatch=next(n for n in outer.body if isinstance(n,ast.AsyncFunctionDef))
dispatch.body[0].body=branch.body
env={'json':json}
exec(compile(ast.fix_missing_locations(wrapper),'<actual-router-control-branch>','exec'),env)

class FixedInputProtocol(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.base=authority.FixedInputAuthority(methodName='runTest')
        await self.base.asyncSetUp()
        self.manager=self.base.manager
        self.dispatchers={}
    async def asyncTearDown(self):await self.base.asyncTearDown()
    def sequence(self,mode):
        result=json.loads(subprocess.check_output(['node',str(ROOT/'scripts/neko_fixed_input_sequence.mjs'),mode],timeout=10))
        self.assertEqual(result['captureCalls'],0)
        return result['rows']
    async def apply(self,row):
        name=row['connection'];message=row['message']
        if name not in self.dispatchers:
            self.dispatchers[name]=env['make_dispatch'](self.manager,name,types.SimpleNamespace(send_text=AsyncMock()))
        if message['action']=='voice_input_control':await self.dispatchers[name]([message])
        else:
            self.assertTrue(await self.manager._ensure_voice_input_session_authorized(name))
            await self.manager._enqueue_audio_stream_data(message)
    async def test_normal_actual_idle_core_pcm_release_sequence(self):
        rows=self.sequence('normal')
        self.assertEqual([r['message'].get('lease_generation') for r in rows if r['message']['action']=='voice_input_control'],[1,2,3])
        await self.apply(rows[0]);self.assertEqual(self.manager._voice_lease_generation,-1)
        await self.apply(rows[1]);self.assertEqual(self.manager._voice_lease_connection_id,'pet')
        self.assertEqual(self.manager._voice_lease_generation,2);self.assertTrue(self.manager._voice_input_accepts_pcm())
        await self.apply(rows[2]);self.assertEqual(self.manager._audio_stream_queue.qsize(),1)
        await self.apply(rows[3]);self.assertFalse(self.manager._voice_input_accepts_pcm())
        self.assertTrue(self.manager._audio_stream_queue.empty());self.manager.send_status.assert_not_awaited()
    async def test_duplicate_same_socket_open_preserves_inflight_pcm_and_scope(self):
        rows=self.sequence('same-socket-reset')
        for row in rows:await self.apply(row)
        self.assertEqual(self.manager._voice_lease_generation,2)
        self.assertEqual(len([r for r in rows if r['message']['action']=='voice_input_control']),2)
        self.assertEqual(self.manager._audio_stream_queue.qsize(),1)
        # One abort belongs to the initial core claim; duplicate open adds none.
        self.assertEqual(self.manager._asr_runtime.abort.await_count,1)
        self.manager.send_status.assert_not_awaited()
    async def test_replayed_old_control_remains_rejected_by_actual_server(self):
        rows=self.sequence('normal')
        for row in rows[:2]:await self.apply(row)
        await self.apply(rows[1])
        self.assertEqual(self.manager._voice_lease_generation,2)
        status=json.loads(self.manager.send_status.await_args.args[0])
        self.assertEqual(status['details']['reason'],'invalid_or_stale_control')
    async def test_genuine_new_socket_restarts_scope_without_old_ticket(self):
        rows=self.sequence('new-socket-reset')
        for row in rows:await self.apply(row)
        self.assertEqual(self.manager._voice_lease_connection_id,'pet-new')
        self.assertEqual(self.manager._voice_lease_generation,2)
        self.assertEqual(self.manager._audio_stream_queue.qsize(),1)
        self.manager.send_status.assert_not_awaited()

if __name__=='__main__':unittest.main(verbosity=2)
