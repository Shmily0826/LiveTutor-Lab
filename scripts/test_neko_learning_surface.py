"""Offline safety/revision guards. Browser geometry is checked separately."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from neko_learning_surface import LearningSurface, SurfaceHandler, DEFAULT_MATERIALS, PointingTargets


class PointingMetadataTest(unittest.TestCase):
    def test_locators_are_bounded_and_escaped(self):
        parser = PointingTargets()
        parser.feed('<div data-node-id="entry" data-node-label="StartupPage"></div>'
                    '<path data-edge-id="map-access" data-edge-from="entry" data-edge-to="maps" data-edge-label="HTTPS"/>'
                    + ''.join(f'<div data-line="{i}"/>' for i in range(100)))
        self.assertEqual(len(parser.targets), 80)
        self.assertEqual(parser.targets[0]["selector"], '[data-node-id="entry"]')
        self.assertEqual(parser.targets[0]["label"], 'StartupPage')
        self.assertIn('entry → maps', parser.targets[1]["label"])

BROWSER_CHECK = r"""
<script>
(async()=>{
const checks=[];
const wait=async(test)=>{const end=Date.now()+12000;while(!test()){if(Date.now()>end)throw Error('browser condition timeout');await new Promise(r=>setTimeout(r,60))}};
const check=(name,condition)=>{checks.push({name,pass:!!condition});if(!condition)throw Error(name)};
const client=window.learningSurface;
try{
await wait(()=>client.ready);
const select=document.getElementById('targets');
check('Sky Scout semantic targets discovered',select.options.length>10);
select.value='[data-node-id="entry"]';
document.getElementById('point').click();
await wait(()=>client.command&&client.geometry());client.draw();
let r=client.geometry();let marker=document.getElementById('marker');
check('HTML marker matches measured target',Math.abs(Number(marker.getAttribute('x'))-(r.x-4))<1);
check('parent overlay visible',!document.getElementById('marks').hasAttribute('hidden'));
const frame=document.getElementById('frame');
const target=frame.contentDocument.querySelector('[data-node-id="entry"]');
const original=target.outerHTML;
target.scrollIntoView({block:'start',behavior:'instant'});
await new Promise(resolve=>setTimeout(resolve,140));client.draw();
r=client.geometry();if(r)check('scroll measured from live DOM',Math.abs(Number(marker.getAttribute('y'))-(r.y-4))<1);
check('material DOM unchanged by guidance',target.outerHTML===original);
const zoomTarget=frame.contentDocument.querySelector('[data-node-id="pages"]');
await client.send({material_id:client.material.id,kind:'selector',selector:'[data-node-id="pages"]',label:'观测页面'});
zoomTarget.scrollIntoView({block:'center',inline:'center',behavior:'instant'});
const beforeZoom=zoomTarget.getBoundingClientRect().width;
frame.contentWindow.Archify.view.zoomIn();
await new Promise(resolve=>setTimeout(resolve,140));zoomTarget.scrollIntoView({block:'center',inline:'center',behavior:'instant'});client.draw();
check('HTML zoom action recomputes or safely hides pointer',(frame.contentWindow.innerWidth<=720||zoomTarget.getBoundingClientRect().width>beforeZoom)&&(client.geometry()?Math.abs(Number(marker.getAttribute('width'))-(client.geometry().width+8))<1:document.getElementById('marks').hasAttribute('hidden')));
frame.contentWindow.Archify.view.reset();
await new Promise(resolve=>setTimeout(resolve,140));
await client.send({material_id:client.material.id,kind:'selector',selector:'[data-edge-id="map-access"]',label:'定位页面到地图服务'});
frame.contentDocument.querySelector('[data-edge-id="map-access"]').scrollIntoView({block:'center',inline:'center',behavior:'instant'});client.draw();
check('original SVG relation can be indicated',!!client.geometry());
await client.send({material_id:client.material.id,kind:'selector',selector:'[data-node-id="entry"]',label:'entry'});
frame.contentWindow.scrollTo(0,100000);
await new Promise(resolve=>setTimeout(resolve,140));client.draw();
check('offscreen target hidden',client.geometry()===null&&document.getElementById('marks').hasAttribute('hidden'));
await client.send({material_id:client.material.id,kind:'selector',selector:'[data-node-id="not-present"]',label:'missing'});client.draw();
check('missing target hidden',client.geometry()===null);
const materials=document.getElementById('materials');
materials.selectedIndex=3;materials.dispatchEvent(new Event('change'));
await wait(()=>client.ready&&client.material.kind==='image');
check('material switch clears old pointer',client.command===null);
await client.send({material_id:client.material.id,kind:'rect',x:.25,y:.25,width:.05,height:.05,label:'image region'});client.draw();
const initial=client.geometry();check('image region visible',!!initial);
const zoom=document.getElementById('zoom');zoom.value='2';zoom.dispatchEvent(new Event('change'));
await new Promise(resolve=>setTimeout(resolve,140));client.draw();const enlarged=client.geometry();
check('normalized image target scales to 200 percent',enlarged&&Math.abs(enlarged.width-initial.width*2)<1);
const scroller=document.getElementById('imageScroll');scroller.scrollTo(100,80);
await new Promise(resolve=>setTimeout(resolve,140));client.draw();const scrolled=client.geometry();
check('image scroll keeps target aligned',scrolled&&Math.abs(scrolled.x-(enlarged.x-scroller.scrollLeft))<1&&Math.abs(scrolled.y-(enlarged.y-scroller.scrollTop))<1);
materials.selectedIndex=4;materials.dispatchEvent(new Event('change'));
await wait(()=>client.ready&&client.material.id.startsWith('4-'));
check('reverse image clears previous pointer',client.command===null);
// Leave a useful actual pointer in the final screenshot.
await client.send({material_id:client.material.id,kind:'rect',x:.45,y:.3,width:.1,height:.15,label:'浏览器验收：反向对比图指定区域'});client.draw();
document.title='PASS: '+checks.length+' browser geometry checks';
}catch(error){checks.push({name:error.message,pass:false});document.title='FAIL: browser geometry checks'}
let summary=document.createElement('pre');summary.id='browser-check-result';summary.hidden=true;summary.textContent=JSON.stringify(checks);document.body.prepend(summary);
await fetch('/browser-check-result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(checks)});
})();
</script><script defer src="/browser-check-done.js"></script>
"""


class BrowserCheckHandler(SurfaceHandler):
    def do_GET(self):
        if self.path == "/":
            page = Path(__file__).with_name("neko_learning_surface.html").read_text(encoding="utf-8")
            page = page.replace("__BOOTSTRAP__", json.dumps({"token": self.server.token}))
            self.reply(200, (page.replace("</html>", BROWSER_CHECK + "</html>")).encode(), "text/html; charset=utf-8")
        elif self.path == "/browser-check-done.js":
            self.server.browser_done.wait(35)
            self.reply(200, b"/* browser check complete */", "application/javascript")
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == "/browser-check-result":
            length = int(self.headers.get("Content-Length", "0"))
            self.server.browser_result = json.loads(self.rfile.read(min(length, 16384)))
            self.server.browser_done.set()
            self.reply(200, {"saved": True})
        else:
            super().do_POST()


class LearningSurfaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "lesson.html"
        self.path.write_text('<html><b data-node-id="one">original lesson</b></html>', encoding="utf-8")
        self.image = Path(self.temp.name) / "diagram.png"
        self.image.write_bytes(b"test bytes")
        self.server = LearningSurface([self.path, self.image], 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def request(self, route, payload=None, auth=True):
        headers = {"X-Learning-Surface-Token": self.server.token} if auth else {}
        data = json.dumps(payload).encode() if payload is not None else None
        with urlopen(Request(self.url + route, data=data, headers=headers), timeout=3) as response:
            return response.status, response.read(), response.headers

    def test_no_filesystem_traversal_or_unauthorized_api(self):
        for route in ("/api/state", "/material/../../lesson.html", "/material/unknown"):
            with self.assertRaises(HTTPError) as error:
                self.request(route, auth=False)
            self.assertIn(error.exception.code, (403, 404))
        with self.assertRaises(HTTPError) as error:
            self.request("/api/guidance", {"kind": "clear"}, auth=False)
        self.assertEqual(error.exception.code, 403)

    def test_read_only_snapshot_and_revision_invalidation(self):
        before = self.path.read_bytes()
        material = self.server.state()["materials"][0]
        self.server.guide({"material_id": material["id"], "kind": "selector", "selector": '[data-node-id="one"]'})
        self.assertEqual(self.request(material["url"])[1], before)
        self.assertEqual(hashlib.sha256(self.path.read_bytes()).hexdigest(), material["sha256"])
        self.path.write_text("updated lesson", encoding="utf-8")
        self.server.reload_materials()
        self.assertIsNone(self.server.command)
        with self.assertRaises(LookupError):
            self.server.guide({"material_id": material["id"], "kind": "selector", "selector": "b"})
        with self.assertRaises(HTTPError) as error:
            self.request(material["url"])
        self.assertEqual(error.exception.code, 404)

    def test_image_bounds_types_and_wrong_material_kind(self):
        html, image = self.server.state()["materials"]
        good = {"material_id": image["id"], "kind": "rect", "x": .5, "y": .1, "width": .2, "height": .3}
        with self.assertRaises(LookupError):
            self.server.guide(good)
        self.server.select(image["id"])
        self.server.guide(good)
        for field, value in (("x", float("nan")), ("x", True), ("width", -.1), ("width", .6), ("height", 0)):
            with self.assertRaises(ValueError):
                self.server.guide({**good, field: value})
        with self.assertRaises(ValueError):
            self.server.select(html["id"])
            self.server.guide({**good, "material_id": html["id"]})
        with self.assertRaises(ValueError):
            self.server.select(image["id"])
            self.server.guide({"material_id": image["id"], "kind": "selector", "selector": "img"})

    def test_request_validation_and_material_csp(self):
        material = self.server.state()["materials"][0]
        status, body, headers = self.request(material["url"])
        self.assertEqual(status, 200)
        self.assertIn("connect-src 'self'", headers["Content-Security-Policy"])
        self.assertIn("form-action 'none'", headers["Content-Security-Policy"])
        with self.assertRaises(HTTPError) as error:
            self.request("/api/guidance", [])
        self.assertEqual(error.exception.code, 400)
        _, body, _ = self.request("/api/reload", {})
        self.assertIsNone(json.loads(body)["command"])


@unittest.skipUnless(os.environ.get("NEKO_SURFACE_BROWSER_CHECK") == "1", "opt-in shared web-inspector browser verification")
class BrowserGeometryTests(unittest.TestCase):
    def test_real_materials_in_shared_inspector(self):
        before = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in DEFAULT_MATERIALS}
        server = LearningSurface(DEFAULT_MATERIALS, 0)
        server.RequestHandlerClass = BrowserCheckHandler
        server.browser_done = threading.Event()
        server.browser_result = None
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        results = []
        try:
            for viewport in ("--desktop", "--mobile"):
                server.select(server.state()["materials"][0]["id"])
                server.browser_done.clear()
                server.browser_result = None
                run = subprocess.run(["node", r"D:\AI\tools\web-inspector\cli.mjs", f"http://127.0.0.1:{server.server_port}/", viewport, "--screenshot", "--json"], capture_output=True, text=True, encoding="utf-8", timeout=55)
                print(json.dumps(json.loads(run.stdout), ensure_ascii=True), flush=True)
                evidence_dir = Path(__file__).resolve().parents[1] / "benchmarks/raw/evidence"
                attempt = evidence_dir / f"daily-companion-guidance-browser-{time.time_ns()}-{viewport[2:]}.json"
                attempt.write_text(json.dumps({"checks": server.browser_result, "inspector": json.loads(run.stdout)}, ensure_ascii=False, indent=2), encoding="utf-8")
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertIsNotNone(server.browser_result, run.stdout)
                self.assertTrue(all(check["pass"] for check in server.browser_result), server.browser_result)
                inspection = json.loads(run.stdout)["results"][0]
                self.assertFalse(inspection["horizontalOverflow"])
                self.assertFalse(inspection["pageErrors"])
                self.assertFalse(inspection["consoleErrors"])
                results.append({"viewport": viewport, "checks": server.browser_result, "inspector": json.loads(run.stdout)})
            after = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in DEFAULT_MATERIALS}
            self.assertEqual(before, after)
            evidence = Path(__file__).resolve().parents[1] / "benchmarks/raw/evidence/daily-companion-guidance-browser-20261014.json"
            evidence.write_text(json.dumps({"results": results, "unchanged_material_sha256": after}, ensure_ascii=False, indent=2), encoding="utf-8")
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == "__main__":
    unittest.main()
