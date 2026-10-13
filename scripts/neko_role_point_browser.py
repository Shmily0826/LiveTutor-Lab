"""Browser observation of a pointer produced by the actual role, not this fixture."""
import json
from pathlib import Path
from neko_learning_surface import SurfaceHandler

CHECK = r'''<script>
(async()=>{const checks=[];const wait=async f=>{for(let i=0;i<100;i++){if(f())return;await new Promise(r=>setTimeout(r,40))}throw Error('role pointer timed out')};try{
const client=window.learningSurface;await wait(()=>client.ready&&client.command);
const frame=document.getElementById('frame');
const target=frame.contentDocument.querySelector(client.command.selector);
checks.push({name:'role chose actual source declaration',pass:!!target&&/^13\s/.test(target.textContent.trim())&&target.textContent.includes('fetchWeather')});
// Learner scroll only. The fixture never submits a pointing command.
target?.scrollIntoView({block:'center',inline:'center',behavior:'instant'});
await wait(()=>client.geometry());client.draw();
checks.push({name:'role pointer is visible after learner scroll',pass:!document.getElementById('marks').hasAttribute('hidden')});
checks.push({name:'visible command matches server role command',pass:client.command.material_id===client.material.id});
}catch(error){checks.push({name:String(error),pass:false})}await fetch('/role-point-result',{method:'POST',body:JSON.stringify(checks)})})();
</script><script defer src="/role-point-done.js"></script>'''


class RolePointHandler(SurfaceHandler):
    def do_GET(self):
        if self.path == '/':
            page=Path(__file__).with_name('neko_learning_surface.html').read_text(encoding='utf-8').replace('__BOOTSTRAP__',json.dumps({'token':self.server.token}))
            self.reply(200,page.replace('</html>',CHECK+'</html>').encode(),'text/html; charset=utf-8')
        elif self.path == '/role-point-done.js':
            self.server.role_point_done.wait(12);self.reply(200,b'/* role point observed */','application/javascript')
        else: super().do_GET()

    def do_POST(self):
        if self.path == '/role-point-result':
            self.server.role_point_checks=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            self.server.role_point_done.set();self.reply(200,{'ok':True})
        else: super().do_POST()
