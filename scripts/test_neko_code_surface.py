"""Filtered code evidence view: isolation, escaping, versions and real DOM."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
from urllib.request import Request, build_opener, ProxyHandler
from neko_learning_surface import LearningSurface, SurfaceHandler

ROOT = Path(__file__).resolve().parents[1]
CODE = 'weather_service.dart\n21: Future<Weather> fetchWeather(AppLocation location) async {\n22: final uri = Uri.parse("/api/weather");\n23: return response;\n24: }'

CHECK = r"""<script>
(async()=>{const checks=[];const wait=async fn=>{for(let i=0;i<150;i++){if(fn())return;await new Promise(r=>setTimeout(r,60))}throw Error('code surface timeout')};const check=(name,pass)=>{checks.push({name,pass:!!pass});if(!pass)throw Error(name)};try{
const client=window.learningSurface;await wait(()=>client.ready);
const before=document.getElementById('materials').options.length;
const made=await fetch('/make-code',{method:'POST'}).then(r=>r.json());
await wait(()=>document.getElementById('materials').options.length===before+1);
check('new code evidence enters learner material menu',true);
check('publishing code preserves learner selection',client.material.id!==made.material_id);
const select=document.getElementById('materials');select.value=made.material_id;select.dispatchEvent(new Event('change'));
await wait(()=>client.ready&&client.material.id===made.material_id);
const frame=document.getElementById('frame');check('real returned lines visible',frame.contentDocument.body.innerText.includes('fetchWeather')&&frame.contentDocument.body.innerText.includes('21:'));
const targets=document.getElementById('targets');targets.value='[data-line="evidence-2"]';document.getElementById('point').click();
await wait(()=>client.command&&client.geometry());client.draw();check('code line can be highlighted',!document.getElementById('marks').hasAttribute('hidden'));
const old=client.material.id;await fetch('/make-code',{method:'POST',body:'new'});await wait(()=>client.material.id!==old);check('new evidence version clears old pointer',!client.command&&document.getElementById('marks').hasAttribute('hidden'));
}catch(error){checks.push({name:String(error),pass:false})}await fetch('/browser-result',{method:'POST',body:JSON.stringify(checks)})})()
</script>"""


class TestHandler(SurfaceHandler):
    def do_GET(self):
        if self.path == "/":
            page = Path(ROOT / "scripts/neko_learning_surface.html").read_text(encoding="utf-8").replace('__BOOTSTRAP__', json.dumps({"token": self.server.token}))
            # Keep document load open until real asynchronous UI checks finish.
            # The inspector is a snapshot tool, not a test-script wait runner.
            self.reply(200, (page.replace('</html>', CHECK + '<script defer src="/await-checks"></script></html>')).encode(), "text/html; charset=utf-8")
        elif self.path == "/await-checks":
            self.server.browser_done.wait(12)
            self.reply(200, b"", "application/javascript")
        else: super().do_GET()

    def do_POST(self):
        if self.path == "/make-code":
            data = self.rfile.read(int(self.headers.get('Content-Length',0)))
            self.reply(200, self.server.show_code_evidence({"project": "fixture", "repo_commit": "v2" if data else "v1", "evidence": CODE}))
        elif self.path == "/browser-result":
            self.server.browser_result = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            self.server.browser_done.set()
            self.reply(200, {"ok": True})
        else: super().do_POST()


class CodeSurfaceTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        material = Path(self.temp.name) / "empty.html"; material.write_text('<p>current learner material</p>')
        self.server = LearningSurface([material], port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True); self.thread.start()

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(timeout=3); self.temp.cleanup()

    def test_literal_code_is_escaped_version_bound_and_not_auto_selected(self):
        old = self.server.active_material_id
        made = self.server.show_code_evidence({"project": "project", "repo_commit": "sha1", "evidence": CODE + '\n<script>bad()</script>'})
        self.assertEqual(self.server.active_material_id, old)
        material = self.server.materials[made['material_id']]
        self.assertNotIn(b'<script>bad()', material['content'])
        self.assertIn(b'&lt;script&gt;', material['content'])
        self.assertEqual(material['sha256'], hashlib.sha256(material['content']).hexdigest())
        self.server.select(made['material_id'])
        self.server.guide({"material_id": made['material_id'], "kind": "selector", "selector": '[data-line="evidence-2"]'})
        revision = self.server.revision
        again = self.server.show_code_evidence({"project": "project", "repo_commit": "sha1", "evidence": CODE + '\n<script>bad()</script>'})
        self.assertEqual(again['material_id'], made['material_id'])
        self.assertEqual(self.server.active_material_id, made['material_id'])
        self.assertEqual(self.server.revision, revision)
        self.assertIsNotNone(self.server.command)
        next_version = self.server.show_code_evidence({"project": "project", "repo_commit": "sha2", "evidence": CODE})
        self.assertNotEqual(next_version['material_id'], made['material_id'])
        self.assertNotIn(made['material_id'], self.server.materials)
        self.assertIsNone(self.server.command)
        with self.assertRaises(ValueError): self.server.show_code_evidence({"evidence": "x"*12001})

    @unittest.skipUnless(os.environ.get('NEKO_CODE_SURFACE_BROWSER_CHECK') == '1', 'opt-in shared inspector DOM check')
    def test_browser_menu_and_code_line_pointer(self):
        self.server.RequestHandlerClass = TestHandler
        self.server.browser_result = None
        self.server.browser_done = threading.Event()
        run = subprocess.run(['node', r'D:\AI\tools\web-inspector\cli.mjs', f'http://127.0.0.1:{self.server.server_port}/', '--desktop', '--screenshot', '--json'],capture_output=True,text=True,encoding='utf-8',timeout=45)
        self.assertEqual(run.returncode,0,run.stderr)
        result={'checks':self.server.browser_result,'inspector':json.loads(run.stdout)}
        (ROOT/'benchmarks/raw/evidence/daily-companion-code-surface-browser-20261014.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        self.assertIsNotNone(self.server.browser_result)
        self.assertTrue(all(check['pass'] for check in self.server.browser_result),result)
        self.assertFalse(result['inspector']['results'][0]['pageErrors'])


if __name__ == '__main__': unittest.main(verbosity=2)
