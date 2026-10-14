"""Shared-browser regression for same-image retry and stale reload responses.

Uses original two PNGs and a local surface only; no model, Study DB or devices.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import threading

from neko_learning_surface import LearningSurface, SurfaceHandler, ROOT, RAW

IMAGES = [RAW / 'evidence' / ('diagram-input-' + name + '.png') for name in ('forward', 'reverse')]
CHECK = r"""
<script>
(async()=>{const checks=[];const c=window.learningSurface;
const wait=async f=>{for(let i=0;i<70;i++){if(f())return;await new Promise(r=>setTimeout(r,40))}throw Error('retry check timeout')};
const check=(name,pass)=>checks.push({name,pass:!!pass});
try{
await wait(()=>document.getElementById('status').textContent.includes('图片未能载入'));
const initial=c.material.id;
check('initial image error is visible and pointing disabled',!c.ready&&c.command===null);
document.getElementById('reload').click();
await wait(()=>!document.getElementById('reload').disabled);
await new Promise(r=>setTimeout(r,450));
check('same image reload really retries and becomes ready',c.ready&&c.material.id===initial&&document.getElementById('image').naturalWidth>0);
if(c.ready){
await c.send({material_id:c.material.id,kind:'rect',x:.2,y:.15,width:.04,height:.04,label:'重试后当前位置'});c.draw();
check('pointing recovers after image retry',!!c.geometry()&&!document.getElementById('marks').hasAttribute('hidden'));
const original=window.fetch;let release;
window.fetch=async(...args)=>{const response=await original(...args);if(args[0]==='/api/reload')return new Promise(resolve=>{release=()=>resolve(response)});return response};
document.getElementById('reload').click();await wait(()=>release);
const menu=document.getElementById('materials');menu.selectedIndex=1;menu.dispatchEvent(new Event('change'));
await wait(()=>c.ready&&c.material.id!==initial);
const newer=c.material.id;
await c.send({material_id:newer,kind:'rect',x:.2,y:.15,width:.04,height:.04,label:'新材料当前位置'});c.draw();
release();await wait(()=>!document.getElementById('reload').disabled);window.fetch=original;
check('late old reload cannot restore the old image',c.material.id===newer);
check('late old reload cannot erase a newer pointer',c.command?.material_id===newer&&c.command?.label==='新材料当前位置'&&!!c.geometry());
}
document.title=checks.every(x=>x.pass)?'PASS: image retry and reload race':'FAIL: same image retry';
}catch(error){checks.push({name:String(error),pass:false});document.title='FAIL: retry fixture'}
await fetch('/fixture/result',{method:'POST',body:JSON.stringify(checks)});
})();
</script><script defer src='/fixture/done.js'></script>
"""


class RetryHandler(SurfaceHandler):
    def do_GET(self):
        if self.path == '/':
            page = Path(__file__).with_name('neko_learning_surface.html').read_text(encoding='utf-8')
            page = page.replace('__BOOTSTRAP__', json.dumps({'token': self.server.token}))
            self.reply(200, page.replace('</html>', CHECK + '</html>').encode(), 'text/html; charset=utf-8')
        elif self.path.startswith('/material/'):
            self.server.image_requests += 1
            if self.server.image_requests == 1:
                self.reply(503, b'temporary test image failure', 'text/plain')
            else:
                super().do_GET()
        elif self.path == '/fixture/done.js':
            self.server.done.wait(12)
            self.reply(200, b'/* checks completed */', 'application/javascript')
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == '/fixture/result':
            self.server.checks = json.loads(self.rfile.read(min(int(self.headers['Content-Length']), 8192)))
            self.server.done.set()
            self.reply(200, {'ok': True})
        else:
            super().do_POST()


def main(output, expect_bug):
    output = output.resolve()
    assert output.parent == (RAW / 'evidence').resolve() and not output.exists()
    image_hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in IMAGES}
    outcomes = []
    with output.open('x', encoding='utf-8') as f:
        f.write('{"status":"started"}\n')
    for viewport in ('--desktop', '--mobile'):
        server = LearningSurface(IMAGES, 0)
        server.RequestHandlerClass = RetryHandler
        server.image_requests, server.checks, server.done = 0, None, threading.Event()
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            run = subprocess.run(['node', 'D:/AI/tools/web-inspector/cli.mjs',
                f'http://127.0.0.1:{server.server_port}/', viewport, '--screenshot', '--json'],
                capture_output=True, text=True, encoding='utf-8', timeout=40)
            inspection = json.loads(run.stdout)
            result = {'viewport': viewport, 'checks': server.checks, 'image_requests': server.image_requests,
                      'inspection': inspection, 'inspector_exit': run.returncode}
            outcomes.append(result)
            print(json.dumps({'viewport': viewport, 'checks': server.checks,
                              'image_requests': server.image_requests}, ensure_ascii=False), flush=True)
        finally:
            server.shutdown(); server.server_close(); thread.join()
            output.write_text(json.dumps({'outcomes': outcomes, 'image_hashes': image_hashes},
                ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    assert image_hashes == {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in IMAGES}
    for outcome in outcomes:
        assert outcome['inspector_exit'] == 0 and outcome['checks'] is not None
        checks = outcome['checks']
        if expect_bug:
            assert checks[0]['pass'] and not checks[1]['pass'] and outcome['image_requests'] == 1
        else:
            assert len(checks) == 5 and all(check['pass'] for check in checks), checks
        page = outcome['inspection']['results'][0]
        assert not page['pageErrors'] and not page['horizontalOverflow']
        assert len(page['consoleErrors']) <= 1
        assert all('503' in error for error in page['consoleErrors'])
    print('Known before-fix bug reproduced' if expect_bug else 'Same-image retry and stale-reload checks PASS')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expect-bug', action='store_true')
    args = parser.parse_args()
    main(args.output, args.expect_bug)
