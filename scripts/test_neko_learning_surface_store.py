"""Synthetic SQLite + opt-in real DOM tests; no plugin, provider, or devices."""
import base64
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from neko_learning_surface import LearningSurface, StudyPictureSnapshot, SurfaceHandler, ROOT, RAW

IMAGES = [ROOT / 'benchmarks/raw/evidence' / ('diagram-input-' + n + '.png')
          for n in ('forward', 'reverse', 'sky-dark')]


class StoreFixture:
    def __init__(self):
        self.temp = tempfile.TemporaryDirectory(prefix='neko-surface-fixture-', dir=RAW)
        self.store = Path(self.temp.name)
        self.db = self.store / 'N.E.K.O/plugins/study_companion/data/study_companion.db'
        self.db.parent.mkdir(parents=True)
        with closing(sqlite3.connect(self.db)) as db, db:
            db.execute('CREATE TABLE kv (key TEXT PRIMARY KEY, value TEXT)')
            db.execute('CREATE TABLE interactions (text TEXT)')
            db.execute("INSERT INTO interactions VALUES ('synthetic-private-history-do-not-read')")
        self.set('A', 0)

    def set(self, course, image=None, session=None, invalid=None):
        state = {'study_course_id': course, 'study_session_id': session or 'session-' + course,
                 'recent_learning_events': ['synthetic-private-history-do-not-read']}
        key = 'submitted_image:' + hashlib.sha256(course.encode()).hexdigest()
        with closing(sqlite3.connect(self.db)) as db, db:
            db.execute('INSERT OR REPLACE INTO kv VALUES (?,?)', ('state', json.dumps(state)))
            if image is not None or invalid is not None:
                value = {'course_id': course, 'image': 'data:image/png;base64,' + base64.b64encode(IMAGES[image].read_bytes()).decode() if image is not None else invalid, 'text': ''}
                db.execute('INSERT OR REPLACE INTO kv VALUES (?,?)', (key, json.dumps(value)))
            else:
                db.execute('DELETE FROM kv WHERE key=?', (key,))

    def close(self):
        self.temp.cleanup()


class StudySurfaceTests(unittest.TestCase):
    def test_replaced_selected_code_evidence_stays_on_new_code_version(self):
        first = self.server.show_code_evidence({'project': 'fixture', 'repo_commit': 'old-version', 'evidence': 'source line: old code'})
        self.server.select(first['material_id'])
        self.assertFalse(self.server.state()['study']['following'])
        second = self.server.show_code_evidence({'project': 'fixture', 'repo_commit': 'new-version', 'evidence': 'source line: new code'})
        state = self.server.state()
        self.assertEqual(state['active_material_id'], second['material_id'])
        self.assertNotIn(first['material_id'], self.server.materials)
        self.assertIsNone(state['command'])
        self.assertFalse(state['study']['following'])

    def test_existing_store_attaches_after_fresh_launcher_database_creation(self):
        server = LearningSurface([IMAGES[2]], 0)
        try:
            self.assertIsNone(server.state()['study'])
            server.attach_study_store(self.fixture.store)
            state = server.state()
            self.assertTrue(state['study']['following'])
            self.assertEqual(state['study']['course_id'], 'A')
            self.assertEqual(state['active_material_id'], state['study']['material_id'])
            self.assertEqual(state['study']['image_sha256'], hashlib.sha256(IMAGES[0].read_bytes()).hexdigest())
        finally:
            server.server_close()

    def setUp(self):
        self.fixture = StoreFixture()
        self.server = LearningSurface([IMAGES[2]], 0, store=self.fixture.store)

    def tearDown(self):
        self.server.server_close()
        self.fixture.close()

    def test_current_picture_not_default_reference_and_readonly_projection(self):
        before = self.fixture.db.read_bytes()
        state = self.server.state()
        image = self.server.materials[state['active_material_id']]
        self.assertEqual(image['content'], IMAGES[0].read_bytes())
        self.assertEqual(state['study']['course_id'], 'A')
        self.assertTrue(state['study']['following'])
        self.assertNotIn('synthetic-private', json.dumps(state))
        self.assertNotIn('base64', json.dumps(state))
        self.assertEqual(self.fixture.db.read_bytes(), before)
        queries = []
        original = sqlite3.connect
        def traced(*args, **kwargs):
            connection = original(*args, **kwargs)
            connection.set_trace_callback(queries.append)
            return connection
        with patch('neko_learning_surface.sqlite3.connect', side_effect=traced):
            self.server.state()
        self.assertFalse(any('interactions' in q or 'SELECT value' in q for q in queries))
        self.assertTrue(any('query_only=ON' in q for q in queries))

    def test_replace_course_session_and_old_pointer_invalid(self):
        a = self.server.state()['active_material_id']
        command = {'material_id': a, 'kind': 'rect', 'x': .2, 'y': .2, 'width': .1, 'height': .1}
        self.server.guide(command)
        self.fixture.set('A', 1)
        replacement = self.server.state()
        self.assertNotEqual(replacement['active_material_id'], a)
        self.assertIsNone(replacement['command'])
        self.assertNotIn(a, self.server.materials)
        with self.assertRaises(LookupError):
            self.server.guide(command)
        replaced = replacement['active_material_id']
        self.fixture.set('A', 1, session='new-A-session')
        self.assertNotEqual(self.server.state()['active_material_id'], replaced)
        self.fixture.set('B', 2)
        self.assertEqual(self.server.state()['study']['course_id'], 'B')
        self.fixture.set('A', 1)
        self.assertEqual(self.server.state()['study']['image_sha256'], hashlib.sha256(IMAGES[1].read_bytes()).hexdigest())

    def test_empty_invalid_failure_and_recovery_never_fallback(self):
        self.fixture.set('B')
        state = self.server.state()
        self.assertIsNone(state['active_material_id'])
        self.assertEqual(state['study']['status'], 'empty')
        self.fixture.set('B', invalid='data:image/png;base64,not!base64')
        self.assertEqual(self.server.state()['study']['status'], 'unavailable')
        with patch.object(self.server.study_reader, 'read', side_effect=sqlite3.OperationalError('secret path')):
            failed = self.server.state()
        self.assertIsNone(failed['active_material_id'])
        self.assertNotIn('secret', json.dumps(failed))
        self.fixture.set('B', 2)
        self.assertEqual(self.server.state()['study']['status'], 'ready')

    def test_reference_selection_explicit_and_reload_follow(self):
        reference = next(m['id'] for m in self.server.state()['materials'] if not m.get('source'))
        self.server.select(reference)
        self.fixture.set('B', 1)
        state = self.server.state()
        self.assertEqual(state['active_material_id'], reference)
        self.assertFalse(state['study']['following'])
        self.server.select('@study')
        self.server.reload_materials()
        state = self.server.state()
        self.assertIn(state['active_material_id'], self.server.materials)
        self.assertTrue(state['study']['following'])

    def test_wal_dirty_uncommitted_snapshot_and_no_write(self):
        writer = sqlite3.connect(self.fixture.db)
        try:
            writer.execute('PRAGMA journal_mode=WAL')
            self.fixture.set('A', 1)
            writer.execute('BEGIN IMMEDIATE')
            writer.execute("UPDATE kv SET value='invalid-uncommitted' WHERE key='state'")
            paths = [self.fixture.db, Path(str(self.fixture.db) + '-wal')]
            before = {p: p.read_bytes() for p in paths}
            self.assertEqual(self.server.state()['study']['image_sha256'], hashlib.sha256(IMAGES[1].read_bytes()).hexdigest())
            self.assertEqual({p: p.read_bytes() for p in paths}, before)
        finally:
            writer.rollback()
            writer.close()

    def test_missing_or_outside_store_rejected_and_no_store_unchanged(self):
        with tempfile.TemporaryDirectory() as outside:
            with self.assertRaises((OSError, ValueError)):
                StudyPictureSnapshot(outside)
        with self.assertRaises(OSError):
            StudyPictureSnapshot(self.fixture.store / 'missing')
        no_store = LearningSurface([IMAGES[0]], 0)
        try:
            state = no_store.state()
            self.assertIsNone(state['study'])
            self.assertEqual(state['active_material_id'], state['materials'][0]['id'])
        finally:
            no_store.server_close()


BROWSER_SCRIPT = r"""
<script>
(async()=>{
const checks=[],c=window.learningSurface;
const wait=async(fn)=>{const end=Date.now()+10000;while(!fn()){if(Date.now()>end)throw Error('DOM wait timeout');await new Promise(r=>setTimeout(r,40))}};
const check=(name,ok)=>{checks.push({name,pass:!!ok});if(!ok)throw Error(name)};
const change=async(course,image,invalid=null)=>{await fetch('/fixture/change',{method:'POST',headers:{'X-Learning-Surface-Token':BOOT.token},body:JSON.stringify({course,image,invalid})})};
try{
await wait(()=>c.ready&&c.material?.course_id==='A');
check('initial current Study A shown, not Sky',c.material.source==='study_store_snapshot'&&document.getElementById('materials').value==='@study');
const old=c.material.id;
await c.send({material_id:old,kind:'rect',x:.3,y:.3,width:.05,height:.05,label:'当前图的位置'});
await wait(()=>c.command);c.draw();check('current image can be pointed',!!c.geometry());
await change('A',1);await wait(()=>c.ready&&c.material?.id!==old);
check('replacement clears old pointer',!c.command&&document.getElementById('marks').hasAttribute('hidden'));
// Fetch old version without provoking a deliberate 404 console error.
const invalid=await fetch('/fixture/old-check',{method:'POST',body:JSON.stringify({id:old})}).then(r=>r.json());
check('old material retired server-side',invalid.retired);
await change('B',null);await wait(()=>!c.material&&!document.getElementById('empty').hidden);
check('course B no image never falls back to Sky',document.getElementById('imageScroll').hidden&&!c.ready&&document.getElementById('studyContext').textContent.includes('B'));
await change('B',null,'data:image/png;base64,invalid!');await wait(()=>document.getElementById('empty').textContent.includes('无法读取'));
check('invalid picture hides old pixels and gives recovery state',!c.material&&!c.ready&&document.getElementById('imageScroll').hidden);
await change('B',2);await wait(()=>c.ready&&c.material?.course_id==='B');
check('course B image automatically shown',!document.getElementById('imageScroll').hidden);
await change('A',1);await wait(()=>c.ready&&c.material?.course_id==='A');
check('return A uses saved replacement',c.material.sha256===EXPECTED_REVERSE);
// Delay one real earlier state response; a newer reload must win.
const originalFetch=window.fetch;let held=false,release;const hold=new Promise(r=>release=r);
window.fetch=async(route,...args)=>{const response=await originalFetch(route,...args);if(route==='/api/state'&&!held){held=true;await hold}return response};
await wait(()=>held);const prior=c.material.id;await change('A',0);document.getElementById('reload').click();await wait(()=>c.ready&&c.material?.id!==prior);
const latest=c.material.id;release();await new Promise(r=>setTimeout(r,100));window.fetch=originalFetch;
check('late older state cannot restore previous image',c.material.id===latest);
await change('A',1);await wait(()=>c.ready&&c.material?.sha256===EXPECTED_REVERSE);
const select=document.getElementById('materials');select.value=[...select.options].find(o=>o.textContent.startsWith('参考')).value;select.dispatchEvent(new Event('change'));
await wait(()=>c.ready&&!c.material?.source);
check('reference requires explicit selection and is labelled',document.getElementById('studyContext').textContent.startsWith('查看参考材料'));
select.value='@study';select.dispatchEvent(new Event('change'));await wait(()=>c.ready&&c.material?.course_id==='A');
check('follow current Study selectable',select.value==='@study');
document.getElementById('reload').click();await wait(()=>!document.getElementById('reload').disabled&&c.ready);
check('reload retains current Study image',c.material.course_id==='A');
await c.send({material_id:c.material.id,kind:'rect',x:.2,y:.2,width:.05,height:.05,label:'当前 Study 课程 A · 反向图'});c.draw();
check('current pointer after resume',!!c.geometry());
document.title='PASS: current Study image '+checks.length+' checks';
}catch(error){checks.push({name:error.message,pass:false});document.title='FAIL: current Study image'}
await fetch('/fixture/result',{method:'POST',body:JSON.stringify(checks)});
})();
</script><script defer src='/fixture/done.js'></script>
"""


class FixtureHandler(SurfaceHandler):
    def do_GET(self):
        if self.path == '/':
            page = Path(__file__).with_name('neko_learning_surface.html').read_text(encoding='utf-8')
            page = page.replace('__BOOTSTRAP__', json.dumps({'token': self.server.token}))
            script = BROWSER_SCRIPT.replace('EXPECTED_REVERSE', json.dumps(hashlib.sha256(IMAGES[1].read_bytes()).hexdigest()))
            self.reply(200, page.replace('</html>', script + '</html>').encode(), 'text/html; charset=utf-8')
        elif self.path == '/fixture/done.js':
            self.server.done.wait(35)
            self.reply(200, b'/* DOM checks completed */', 'application/javascript')
        else:
            super().do_GET()

    def do_POST(self):
        if self.path.startswith('/fixture/'):
            payload = json.loads(self.rfile.read(min(int(self.headers.get('Content-Length', '0')), 16384)))
            if self.path == '/fixture/change':
                if not self.allowed(auth=True): return
                self.server.fixture.set(payload['course'], payload.get('image'), invalid=payload.get('invalid'))
                self.reply(200, {'ok': True})
            elif self.path == '/fixture/old-check':
                self.reply(200, {'retired': payload['id'] not in self.server.materials})
            else:
                self.server.result = payload
                self.server.done.set()
                self.reply(200, {'ok': True})
        else:
            super().do_POST()


@unittest.skipUnless(os.environ.get('NEKO_SURFACE_STORE_BROWSER_CHECK') == '1', 'opt-in global web-inspector')
class BrowserStudySurfaceTests(unittest.TestCase):
    def test_real_dom_current_material_desktop_mobile(self):
        fixture = StoreFixture()
        server = LearningSurface([IMAGES[2]], 0, store=fixture.store)
        server.RequestHandlerClass = FixtureHandler
        server.fixture, server.done, server.result = fixture, threading.Event(), None
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in IMAGES}
        outcomes = []
        try:
            for viewport in ('--desktop', '--mobile'):
                fixture.set('A', 0)
                server.select('@study')
                server.done.clear(); server.result = None
                run = subprocess.run(['node', 'D:/AI/tools/web-inspector/cli.mjs', f'http://127.0.0.1:{server.server_port}/', viewport, '--screenshot', '--json'], capture_output=True, text=True, encoding='utf-8', timeout=55)
                inspection = json.loads(run.stdout)
                outcomes.append({'viewport': viewport, 'checks': server.result, 'inspector': inspection})
                print(json.dumps(outcomes[-1], ensure_ascii=True), flush=True)
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertIsNotNone(server.result)
                self.assertTrue(all(c['pass'] for c in server.result), server.result)
                result = inspection['results'][0]
                self.assertFalse(result['pageErrors'])
                self.assertFalse(result['consoleErrors'])
                self.assertFalse(result['horizontalOverflow'])
            self.assertEqual(hashes, {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in IMAGES})
        finally:
            (RAW / 'evidence/daily-phase22-surface-browser.json').write_text(json.dumps({'outcomes': outcomes, 'unchanged_image_sha256': hashes}, ensure_ascii=False, indent=2), encoding='utf-8')
            server.shutdown(); server.server_close(); thread.join(); fixture.close()


if __name__ == '__main__':
    unittest.main()
