"""Real shared-browser link/close/reopen check; no plugin, provider, DB or device.

The fixture uses the shipped Study HTML/CSS and exact link initializer, not the
rest of the application bootstrap. The target is the real LearningSurface.
"""
import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import subprocess
import threading
from urllib.parse import urlsplit, parse_qs, quote

from neko_learning_surface import LearningSurface, SurfaceHandler, ROOT, RAW

PRODUCT = ROOT / 'patches/neko-study-2026-10-10-product/static'
BASE = RAW / 'neko-app/resources/bin/plugins/study_companion/static'
IMAGE = RAW / 'evidence/diagram-input-forward.png'


class TargetHandler(SurfaceHandler):
    def do_GET(self):
        if self.path == '/':
            page = Path(__file__).with_name('neko_learning_surface.html').read_text(encoding='utf-8')
            page = page.replace('__BOOTSTRAP__', json.dumps({'token': self.server.token}))
            check = '''<script>(async()=>{for(let i=0;i<100;i++){
              if(window.learningSurface.ready){
                const r=await fetch('/fixture/loaded',{method:'POST'});const n=await r.json();
                if(n.count===1){window.close();navigator.sendBeacon('/fixture/closed',JSON.stringify({closed:window.closed}))}
                break}await new Promise(r=>setTimeout(r,40))}})();</script>'''
            self.reply(200, page.replace('</html>', check + '</html>').encode(), 'text/html; charset=utf-8')
        else:
            super().do_GET()

    def do_POST(self):
        if self.path in ('/fixture/loaded', '/fixture/closed'):
            key = 'loaded' if self.path.endswith('loaded') else 'closed'
            if key == 'loaded':
                self.server.events[key] += 1
            else:
                body = json.loads(self.rfile.read(min(int(self.headers['Content-Length']), 128)))
                if body.get('closed') is True: self.server.events[key] += 1
            self.reply(200, {'count': self.server.events[key]})
        else:
            super().do_POST()


class StudyHandler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def reply(self, body, mime):
        data = body.encode() if isinstance(body, str) else body
        self.send_response(200); self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(data))); self.end_headers(); self.wfile.write(data)

    def do_GET(self):
        route = urlsplit(self.path).path
        if route == '/':
            page = (PRODUCT / 'index.html').read_text(encoding='utf-8')
            page = re.sub(r'<script\b[^>]*>.*?</script>', '', page, flags=re.S | re.I)
            page = page.replace('</body>', '<script src="/fixture/check.js"></script><script defer src="/fixture/done.js"></script></body>')
            self.reply(page, 'text/html; charset=utf-8')
        elif route == '/fixture/check.js':
            source = (PRODUCT / 'main.js').read_text(encoding='utf-8')
            begin = source.index('function configureLearningMaterialLink()')
            end = source.index('async function bootstrap()', begin)
            script = "const $id=id=>document.getElementById(id);\n" + source[begin:end]
            script += '''(async()=>{const checks=[];const link=$id('learningMaterialLink');
              const check=(name,pass)=>checks.push({name,pass:!!pass});
              const wait=async f=>{for(let i=0;i<100;i++){if(await f())return;await new Promise(r=>setTimeout(r,40))}throw Error('link fixture timeout')};
              try{configureLearningMaterialLink();
              const absent=new URLSearchParams(location.search).has('absent');
              check('absent URL stays hidden without a stale href',!absent||(!link.checkVisibility()&&!link.hasAttribute('href')));
              if(!absent){
                check('valid current URL is visible and has no opener',link.checkVisibility()&&link.rel==='noopener'&&link.target==='_blank');
                check('link remains a usable toolbar target',link.getBoundingClientRect().height>=36);
                link.click();
                await wait(async()=>{const s=await(await fetch('/fixture/state')).json();return s.loaded===1&&s.closed===1});
                check('first current picture loaded and its window actually closed',true);
                link.click();
                await wait(async()=>{const s=await(await fetch('/fixture/state')).json();return s.loaded===2});
                check('same link reopens current picture after close',true);
              }
              }catch(error){checks.push({name:String(error),pass:false})}
              document.title=checks.every(c=>c.pass)?'PASS: material reopen':'FAIL: material reopen';
              await fetch('/fixture/result',{method:'POST',body:JSON.stringify(checks)});
            })();'''
            # A deferred same-origin barrier keeps the inspector snapshot after checks.
            self.reply(script, 'application/javascript')
        elif route == '/fixture/state':
            self.reply(json.dumps(self.server.target.events), 'application/json')
        elif route == '/fixture/done.js':
            self.server.done.wait(12); self.reply('/* checked */', 'application/javascript')
        elif route.startswith('/fixture/'):
            self.send_error(404)
        else:
            relative = route.lstrip('/')
            path = BASE / relative
            if '/' in relative or not path.is_file():
                self.send_error(404); return
            self.reply(path.read_bytes(), 'text/css' if path.suffix == '.css' else 'application/octet-stream')

    def do_POST(self):
        if self.path != '/fixture/result':
            self.send_error(404); return
        self.server.checks = json.loads(self.rfile.read(min(int(self.headers['Content-Length']), 8192)))
        self.server.done.set(); self.reply('{}', 'application/json')


def main(output):
    assert output.resolve().parent == (RAW / 'evidence').resolve() and not output.exists()
    original = hashlib.sha256(IMAGE.read_bytes()).hexdigest()
    outcomes = []
    with output.open('x', encoding='utf-8') as f: f.write('{"status":"started"}\n')
    for viewport in ('--desktop', '--mobile'):
        for absent in (False, True):
            target = LearningSurface([IMAGE], 0); target.RequestHandlerClass = TargetHandler
            target.events = {'loaded': 0, 'closed': 0}
            server = ThreadingHTTPServer(('127.0.0.1', 0), StudyHandler)
            server.target, server.checks, server.done = target, None, threading.Event()
            threads = [threading.Thread(target=s.serve_forever, daemon=True) for s in (target, server)]
            for thread in threads: thread.start()
            try:
                url = f'http://127.0.0.1:{server.server_port}/?'
                url += 'absent=1' if absent else 'learning_surface=' + quote(f'http://127.0.0.1:{target.server_port}', safe='')
                run = subprocess.run(['node', 'D:/AI/tools/web-inspector/cli.mjs', url, viewport,
                                      '--screenshot', '--json'], capture_output=True, text=True, encoding='utf-8', timeout=40)
                result = {'viewport': viewport, 'absent': absent, 'checks': server.checks,
                          'target_events': dict(target.events), 'inspector_exit': run.returncode,
                          'inspection': json.loads(run.stdout)}
                outcomes.append(result)
                print(json.dumps({k: v for k, v in result.items() if k != 'inspection'}, ensure_ascii=False), flush=True)
            finally:
                for s in (server, target): s.shutdown(); s.server_close()
                for thread in threads: thread.join()
                output.write_text(json.dumps({'outcomes': outcomes, 'image_sha256': original}, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    assert hashlib.sha256(IMAGE.read_bytes()).hexdigest() == original
    for result in outcomes:
        assert result['inspector_exit'] == 0 and result['checks'] and all(c['pass'] for c in result['checks']), result
        page = result['inspection']['results'][0]
        assert not page['pageErrors'] and not page['consoleErrors'] and not page['horizontalOverflow'], page
    print('PASS: desktop/mobile link visibility, actual material load/close/reopen, absent-link hiding')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    main(parser.parse_args().output)
