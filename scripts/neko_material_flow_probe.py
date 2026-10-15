"""Complete Study link -> actual material controls -> close/reopen; no model/device."""
import argparse
import hashlib
import json
from pathlib import Path
import secrets
import threading
from urllib.parse import parse_qs, quote, urlsplit

import neko_study_ready_probe as study
from neko_learning_surface import LearningSurface, SurfaceHandler, DEFAULT_MATERIALS
from neko_output_only_runtime import protected_html
from neko_source_timing_probe import history_snapshot


MATERIAL_OBSERVER = r'''(async()=>{
const run=__RUN__,checks=[],client=window.learningSurface;
const pause=ms=>new Promise(r=>setTimeout(r,ms));
const check=(name,pass)=>checks.push({name,pass:!!pass});
const wait=async fn=>{for(let n=0;n<120;n++){if(fn())return;await pause(40)}throw Error('material condition timed out')};
const select=async id=>{const el=document.getElementById('materials');el.value=id;el.dispatchEvent(new Event('change'));await wait(()=>client.ready&&client.material?.id===id)};
const visible=()=>!document.getElementById('marks').hasAttribute('hidden');
const aligned=expected=>{client.draw();if(!visible())return false;const m=document.getElementById('marker').getBoundingClientRect();return Math.abs(m.left+m.width/2-expected.x)<2&&Math.abs(m.top+m.height/2-expected.y)<2};
const imagePoint=async()=>{const image=document.getElementById('image'),r=image.getBoundingClientRect();image.dispatchEvent(new MouseEvent('click',{bubbles:true,clientX:r.left+r.width*.3,clientY:r.top+r.height*.3}));await wait(()=>client.command?.kind==='rect');client.draw();return image};
try{
 await wait(()=>client&&document.getElementById('materials').options.length>1);
 check('material capture guard installed',globalThis.__NEKO_OUTPUT_ONLY_CAPTURE_BLOCKED__===true);
 if(run.visit===1){
  await select(run.ids.html);
  const targets=document.getElementById('targets'),option=[...targets.options].find(o=>o.value.startsWith('[data-node-id='));
  if(!option)throw Error('no semantic module option');
  targets.value=option.value;
  const frame=document.getElementById('frame'),target=frame.contentDocument.querySelector(option.value),before=target.outerHTML;
  document.getElementById('point').click();await wait(()=>client.command?.kind==='selector');
  target.scrollIntoView({block:'center',inline:'center',behavior:'instant'});await pause(140);
  let r=target.getBoundingClientRect(),f=frame.getBoundingClientRect();
  check('module pointer aligns after learner scroll',aligned({x:f.left+r.left+r.width/2,y:f.top+r.top+r.height/2}));
  check('pointing leaves material node unchanged',target.outerHTML===before);
  await select(run.ids.image);
  check('HTML to image removes old pointer',!client.command&&!visible());
  const image=await imagePoint();let b=image.getBoundingClientRect(),c=client.command;
  check('image click pointer aligns',aligned({x:b.left+(c.x+c.width/2)*b.width,y:b.top+(c.y+c.height/2)*b.height}));
  const zoom=document.getElementById('zoom');zoom.value='1.5';zoom.dispatchEvent(new Event('change'));await pause(140);
  b=image.getBoundingClientRect();c=client.command;
  check('image zoom keeps pointer aligned',aligned({x:b.left+(c.x+c.width/2)*b.width,y:b.top+(c.y+c.height/2)*b.height}));
  document.getElementById('imageScroll').scrollLeft=50;await pause(140);b=image.getBoundingClientRect();c=client.command;
  check('image scroll keeps pointer aligned',aligned({x:b.left+(c.x+c.width/2)*b.width,y:b.top+(c.y+c.height/2)*b.height}));
  const old=await api('/api/state');
  await select(run.ids.reverse);
  check('replacement image removes old pointer',!client.command&&!visible());
  apply(old);client.draw();
  check('late earlier state cannot restore old material or arrow',client.material.id===run.ids.reverse&&!client.command&&!visible());
  await imagePoint();document.getElementById('clear').click();await wait(()=>!client.command);client.draw();
  check('clear control clears current pointer',!visible());
 }else{
  await wait(()=>client.ready);
  check('reopened material retains actual selection',client.material.id===run.ids.reverse);
  check('reopened page has no retired pointer',!client.command&&!visible());
  await imagePoint();check('reopened material accepts a new pointer',visible());
 }
}catch(error){checks.push({name:'material observer failure',pass:false,detail:String(error).slice(0,200)})}
finally{
 window.close();
 navigator.sendBeacon('/__material_result',JSON.stringify({case:run.case,visit:run.visit,closed:window.closed,checks}));
}
})();'''

STUDY_OBSERVER = r'''(async()=>{
const checks=[],pause=ms=>new Promise(r=>setTimeout(r,ms));let timer;
const check=(name,pass)=>checks.push({name,pass:!!pass});
const state=()=>fetch('/__material_state').then(r=>r.json());
const wait=async fn=>{for(let n=0;n<100;n++){if(await fn())return;await pause(70)}throw Error('material navigation timed out')};
try{
 await Promise.race([globalThis.__phase54Bootstrap,new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('bootstrap deadline')),10000)})]);clearTimeout(timer);
 check('complete Study service ready',studyServiceReady);
 check('Study capture guard installed',globalThis.__NEKO_OUTPUT_ONLY_CAPTURE_BLOCKED__===true);
 const course=String(lastStatusPayload.study_course_id||lastStatusPayload.state?.study_course_id||'');
 await fetch('/__material_begin?width='+innerWidth);
 const link=document.getElementById('learningMaterialLink');
 check('actual Study material entry is visible',link&&!link.hidden&&getComputedStyle(link).display!=='none');
 check('entry opens an independent protected tab',link.target==='_blank'&&link.rel.includes('noopener'));
 link.click();await wait(async()=>{const s=await state();return s.results.length===1&&s.results[0].closed===true});
 link.click();await wait(async()=>{const s=await state();return s.results.length===2&&s.results[1].closed===true});
 const observed=await state();checks.push(...observed.results.flatMap(r=>r.checks));
 check('two actual material documents closed themselves',observed.visits===2&&observed.results.every(r=>r.closed));
 check('material navigation keeps Study course',String(lastStatusPayload.study_course_id||lastStatusPayload.state?.study_course_id||'')===course);
}catch(error){checks.push({name:'complete material flow failure',pass:false,detail:String(error).slice(0,200)})}
finally{clearTimeout(timer);await fetch('/__phase54_result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({width:innerWidth,checks})})}
})();'''


class MaterialHandler(SurfaceHandler):
    def do_GET(self):
        if urlsplit(self.path).path != '/':
            return super().do_GET()
        if not self.allowed():
            return
        with self.server.lock:
            self.server.flow['visits'] += 1
            run = {'case': self.server.flow['case'], 'visit': self.server.flow['visits'], 'ids': self.server.ids}
        page = Path(__file__).with_name('neko_learning_surface.html').read_text(encoding='utf-8')
        page = page.replace('__BOOTSTRAP__', json.dumps({'token': self.server.token}))
        page = protected_html(page, self.server.policy, text_only=True)
        page = page.replace('</html>', '<script>' + MATERIAL_OBSERVER.replace('__RUN__', json.dumps(run)) + '</script></html>')
        self.reply(200, page.encode(), 'text/html; charset=utf-8')

    def do_POST(self):
        if self.path != '/__material_result':
            return super().do_POST()
        length = int(self.headers.get('Content-Length', '0'))
        if not self.allowed() or not 0 < length <= 12000:
            return
        result = json.loads(self.rfile.read(length))
        with self.server.lock:
            if result['case'] == self.server.flow['case']:
                if result['visit'] not in [r['visit'] for r in self.server.flow['results']]:
                    self.server.flow['results'].append(result)
        self.reply(200, {})


def inspect(output):
    database = study.STORE / 'N.E.K.O/plugins/study_companion/data/study_companion.db'
    history = history_snapshot(database)
    materials = [DEFAULT_MATERIALS[i] for i in (1, 2, 3, 4)]
    originals = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in materials}
    surface = LearningSurface(materials, port=0, store=study.STORE)
    surface.RequestHandlerClass = MaterialHandler
    surface.policy = (study.ROOT / 'scripts/neko_capture_policy.js').read_text(encoding='utf-8')
    ids = list(surface.materials)
    surface.ids = {'html': ids[0], 'image': ids[2], 'reverse': ids[3]}
    surface.flow = {'case': '', 'visits': 0, 'results': []}
    url = f'http://127.0.0.1:{surface.server_port}'
    original_relay, original_observer = study.Relay, study.OBSERVER

    class FlowRelay(original_relay):
        def do_GET(self):
            parsed = urlsplit(self.path)
            if parsed.path == study.UI and not parse_qs(parsed.query).get('learning_surface'):
                self.send_response(302)
                self.send_header('Location', study.UI + '?learning_surface=' + quote(url, safe=''))
                self.end_headers()
                return
            if parsed.path in ('/__material_begin', '/__material_state'):
                with surface.lock:
                    if parsed.path.endswith('begin'):
                        surface.flow = {'case': secrets.token_hex(6), 'visits': 0, 'results': []}
                        surface.select(surface.ids['html'])
                    body = json.dumps(surface.flow).encode()
                return self.reply(200, body, 'application/json')
            return super().do_GET()

    thread = threading.Thread(target=surface.serve_forever, daemon=True)
    thread.start()
    study.Relay, study.OBSERVER = FlowRelay, STUDY_OBSERVER
    try:
        study.inspect(output, all_viewports=True)
        report = json.loads(output.read_text(encoding='utf-8'))
        after = history_snapshot(database)
        report['history_before'] = history
        report['history_after'] = after
        report['old_history_unchanged'] = all(after[table].get(key) == value
            for table, rows in history.items() for key, value in rows.items())
        report['original_materials_unchanged'] = all(hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest
                                                    for path, digest in originals.items())
        report['material_surface_port'] = surface.server_port
        report['proof'] = 'real complete Study bootstrap/readonly SDK + actual material page DOM controls and close/reopen; shared headless browser; not trusted physical clicks, OS window movement, autonomous role or human proof'
        if report.get('result'):
            report['result'] = 'PASS: complete Study material navigation, controls, stale state and close/reopen'
        if not report['old_history_unchanged'] or not report['original_materials_unchanged']:
            report['failure'] = 'existing learning history or original material changed'
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        return report
    finally:
        study.Relay, study.OBSERVER = original_relay, original_observer
        surface.shutdown()
        surface.server_close()
        thread.join(timeout=3)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.parent != (study.ROOT / 'benchmarks/raw/evidence').resolve() or output.suffix != '.json':
        raise ValueError('Use a new JSON in the task evidence directory.')
    result = inspect(output)
    print(json.dumps({k: result.get(k) for k in ('result', 'failure', 'cleanup_error', 'tracker_error',
        'old_history_unchanged', 'original_materials_unchanged', 'after')}, ensure_ascii=False))
    raise SystemExit(bool(result.get('failure') or result.get('cleanup_error') or result.get('tracker_error')))
