"""Actual Study image DOM flows through the shared web-inspector, offline only."""
from __future__ import annotations

import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path
import subprocess
import threading
import time
import unittest
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / "patches/neko-study-2026-10-10-product/static"
STOCK = ROOT / "benchmarks/raw/neko-app/resources/bin/plugins/study_companion/static"
EVIDENCE = ROOT / "benchmarks/raw/evidence"
IMAGES = [EVIDENCE / name for name in ("diagram-input-forward.png", "diagram-input-reverse.png", "diagram-input-sky-dark.png")]

BROWSER_CHECK = r"""
'use strict';
(async()=>{
const checks=[];const which=new URLSearchParams(location.search).get('case');
const $=id=>document.getElementById(id);
const wait=async(test,label='condition')=>{const end=Date.now()+6000;while(!test()){if(Date.now()>end)throw Error('Timeout: '+label);await new Promise(r=>setTimeout(r,30))}};
const pause=ms=>new Promise(r=>setTimeout(r,ms));
const check=(name,pass)=>checks.push({name,pass:!!pass});
const control=async(value)=>fetch('/fixture/control',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(value)});
const state=async()=> (await fetch('/fixture/state')).json();
const blob=async index=>(await fetch('/fixture/image/'+index)).blob();
async function file(index,name='diagram.png',type='image/png') {return new File([await blob(index)],name,{type})}
function choose(value){const dt=new DataTransfer();dt.items.add(value);$('studyImageFile').files=dt.files;$('studyImageFile').dispatchEvent(new Event('change',{bubbles:true}))}
function paste(value){const dt=new DataTransfer();dt.items.add(value);$('studyInput').dispatchEvent(new ClipboardEvent('paste',{clipboardData:dt,bubbles:true,cancelable:true}))}
async function selected(index){choose(await file(index));await wait(()=>$('studyInputImage').getAttribute('src')&& !$('studyImageChoose').disabled,'file selection');return $('studyInputImage').src}
async function explained(text){$('studyInput').value=text;$('explainBtn').click();await wait(()=>!$('explainBtn').disabled,'explanation completion')}
const requestRefresh=()=>window.dispatchEvent(new MessageEvent('message',{origin:location.origin,data:{type:'neko-study-refresh-summary',plugin_id:'study_companion'}}));
const oldLoad=loadImageFromBlob;let releaseLoad=null;
loadImageFromBlob=async(blob,signal)=>{if(releaseLoad===true)await new Promise(resolve=>releaseLoad=resolve);return oldLoad(blob,signal)};
try{
await wait(()=>$('statusLine').textContent&&!/Starting|启动/.test($('statusLine').textContent),'bootstrap handlers');
await wait(()=>typeof currentPracticeScope!=='undefined');
if(which!=='readiness')await wait(()=>lastStatusPayload.study_course_id==='course-a','initial status');
if(which==='flow'){
  const first=await selected(0);check('actual PNG file produces visible JPEG preview',!$('studyInputImagePreview').hidden&&first.startsWith('data:image/jpeg;base64,'));
  await explained('first picture');let s=await state();let sent=s.calls.filter(c=>c.entry_id==='study_submit_image').at(-1);
  check('file submits correct current image and expected course to Study entry',sent&&sent.args.image_base64===first&&sent.args.text==='first picture'&&sent.args.expected_course_id==='course-a');
  check('successful explanation enables followup',!$('usePreviousExplanation').disabled);
  $('usePreviousExplanation').checked=true;
  const second=await selected(1);check('replacement image differs and clears previous followup',second!==first&&$('usePreviousExplanation').disabled&&!$('usePreviousExplanation').checked);
  await explained('reverse picture');s=await state();sent=s.calls.filter(c=>c.entry_id==='study_submit_image').at(-1);
  check('replacement submits new image without old explanation',sent&&sent.args.image_base64===second&&sent.args.text==='reverse picture');
  const before=second;choose(new File(['bad'],'bad.gif',{type:'image/gif'}));await pause(80);
  check('unsupported file shows error and preserves last valid picture',!$('studyInputPasteError').hidden&&$('studyInputImage').src===before);
  choose(new File([new Uint8Array(21*1024*1024)],'too-big.png',{type:'image/png'}));await pause(80);
  check('oversize file reports 20 MB limit',!$('studyInputPasteError').hidden&&$('studyInputPasteError').textContent.includes('20 MB'));
  choose(new File(['not PNG bytes'],'corrupt.png',{type:'image/png'}));await wait(()=>!$('studyImageChoose').disabled);
  check('unreadable image reports recoverable file error',!$('studyInputPasteError').hidden&&$('studyInputImage').src===before);
  const prior=before;paste(await file(2,'sky.png'));await wait(()=>$('studyInputImage').src!==prior,'actual clipboard image');
  const pasted=$('studyInputImage').src;await explained('pasted Sky Scout');s=await state();sent=s.calls.filter(c=>c.entry_id==='study_submit_image').at(-1);
  check('clipboard image takes same existing submit entry and exact payload',sent&&sent.args.image_base64===pasted&&sent.args.text==='pasted Sky Scout');
  await control({course:'course-b'});$('refreshBtn').click();await wait(()=>!$('refreshBtn').disabled);
  check('role API course switch clears image and followup', $('studyInputImagePreview').hidden&&!$('studyInputImage').hasAttribute('src')&&$('usePreviousExplanation').disabled);
  check('role course change clears stale image error and selected filename', $('studyInputPasteError').hidden&& !$('studyImageStatus').textContent.includes('sky.png'));
  await selected(0);$('studyInputImageRemove').click();check('remove image clears preview and old submitted status', $('studyInputImagePreview').hidden&&!$('studyImageStatus').textContent.includes('图片已交给'));
  $('studyInput').value='text question';await explained('text question');s=await state();check('no image uses normal text entry',s.calls.filter(c=>c.entry_id==='study_explain_text').at(-1)?.args.text==='text question');
}
if(which==='races'){
  await selected(0);releaseLoad=true;choose(await file(1,'delayed-old.png'));await wait(()=>typeof releaseLoad==='function','slow file started');
  await control({course:'course-b'});await refreshStatus();releaseLoad();await pause(160);
  check('course switch cancels late file decoding', $('studyInputImagePreview').hidden&&!$('studyInputImage').hasAttribute('src'));
  await selected(0);releaseLoad=true;paste(await file(1,'delayed-paste.png'));await wait(()=>typeof releaseLoad==='function','slow paste started');
  await control({course:'course-c'});await refreshStatus();releaseLoad();await pause(160);
  check('course switch cancels late paste decoding', $('studyInputImagePreview').hidden&&!$('studyInputImage').hasAttribute('src'));
  await selected(0);releaseLoad=true;choose(await file(1,'late-file.png'));await wait(()=>typeof releaseLoad==='function');const releaseOld=releaseLoad;releaseLoad=null;
  const beforePaste=$('studyInputImage').src;paste(await file(2,'newer-paste.png'));await wait(()=>$('studyInputImage').src!==beforePaste,'newer paste preview');const newer=$('studyInputImage').src;releaseOld();await pause(180);
  check('new paste supersedes older file callback', $('studyInputImage').src===newer);
  const initial=await selected(0);await control({hold_submit:true});$('studyInput').value='stale old explanation';$('explainBtn').click();await wait(()=>$('explainBtn').disabled);
  await wait(async()=>true);await pause(310);const replacement=await selected(1);await control({release_submit:true});await wait(()=>!$('explainBtn').disabled);
  check('late old image reply cannot reenable current followup', $('usePreviousExplanation').disabled&&!$('replyText').textContent.includes('FAKE stale old explanation'));
  check('late old image reply cannot claim new image was submitted', $('studyInputImage').src===replacement&&!$('studyImageStatus').textContent.includes('图片已交给'));
  await control({hold_submit:true});$('studyInput').value='stale old course';$('explainBtn').click();await wait(()=>$('explainBtn').disabled);await pause(310);
  await control({course:'course-d'});await refreshStatus();await control({release_submit:true});await wait(()=>!$('explainBtn').disabled);
  check('late reply from old course cannot overwrite current course', $('selectedStudyCourse').textContent.includes('course-d')&&$('studyInputImagePreview').hidden&&$('usePreviousExplanation').disabled&&!$('replyText').textContent.includes('FAKE stale old course'));
  await control({hold_next_status:true});const oldStatus=refreshStatus();await pause(310);await control({course:'course-e'});await refreshStatus();await control({release_status:true});await oldStatus;
  check('older async status cannot revert newer role course', $('selectedStudyCourse').textContent.includes('course-e'));
}
if(which==='preview'){
  await selected(2);await wait(()=>$('studyInputImage').naturalWidth>0,'preview decoded');
  check('real Sky Scout preview is visible with constrained dimensions', !$('studyInputImagePreview').hidden&&$('studyInputImage').naturalWidth<=2048&&$('studyInputImage').getBoundingClientRect().width>0);
  $('explainPanel').scrollIntoView({block:'start',behavior:'instant'});
}
if(which==='onboarding'){
  check('first launch keeps stage modal closed', !$('learningProfileModal')||$('learningProfileModal').hidden);
  const chooseButton=$('studyImageChoose');chooseButton.scrollIntoView({block:'center',behavior:'instant'});const rect=chooseButton.getBoundingClientRect();
  check('first launch image button is physically reachable',document.elementFromPoint(rect.left+rect.width/2,rect.top+rect.height/2)?.closest('button')===chooseButton);
  $('firstRunStageBtn').click();check('stage dialog opens only on explicit learner click',!!$('learningProfileModal')&&!$('learningProfileModal').hidden);
  $('learningProfileModal').querySelector('button').click();await refreshStatus();
  check('skip remains remembered after status refresh', $('learningProfileModal').hidden&&$('firstRunGuide').hidden);
}
if(which==='course-submit'){
  await selected(0);let s=await state();const before=s.calls.filter(c=>c.entry_id==='study_submit_image').length;
  await control({course:'role-course-before-click'});await explained('old UI picture');s=await state();
  check('preflight rejects old preview after unseen role course change',s.calls.filter(c=>c.entry_id==='study_submit_image').length===before&&$('studyInputImagePreview').hidden&&$('selectedStudyCourse').textContent.includes('role-course-before-click'));
  await selected(1);await control({switch_on_submit:'course-between-status-and-submit'});await explained('atomic course check');s=await state();
  check('submit carries expected course and server rejects intervening switch',s.rejected_submit===true&&!s.stored_courses.includes('course-between-status-and-submit'));
  check('course mismatch refreshes UI and clears invalid preview', $('studyInputImagePreview').hidden&&$('selectedStudyCourse').textContent.includes('course-between-status-and-submit')&&$('usePreviousExplanation').disabled);
}
if(which==='readiness'){
  await wait(()=>/Not ready|未就绪/.test($('statusLine').textContent),'initial unavailable status');await selected(0);$('studyInput').value='offline picture';$('explainBtn').click();await wait(()=>!$('explainBtn').disabled);
  check('not ready gives concrete refresh recovery instruction',/刷新|Refresh/.test($('replyText').textContent));
  await control({offline:false});$('refreshBtn').click();await wait(()=>!$('refreshBtn').disabled&&lastStatusPayload.study_course_id==='course-a');await explained('recovered picture');
  check('service readiness can recover without page reload', $('replyText').textContent.includes('FAKE recovered picture'));
  const previous=$('studyInputImage').src;await control({drop_network:true});await explained('network down');
  check('network failure preserves selected image and explains recovery', $('studyInputImage').src===previous&&/刷新|Refresh/.test($('replyText').textContent));
  await control({drop_network:false});$('refreshBtn').click();await wait(()=>!$('refreshBtn').disabled);await explained('after network recovery');
  check('network restored retries only learner request and reuses same image', $('replyText').textContent.includes('FAKE after network recovery')&&$('studyInputImage').src===previous);
}
}catch(error){checks.push({name:error.stack||error.message,pass:false})}
document.title=(checks.every(c=>c.pass)?'PASS':'FAIL')+': daily image UI '+which;
if(which!=='preview')window.scrollTo(0,0);
await fetch('/fixture/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(checks)});
})();
"""


class FixtureServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self):
        self.reset("flow")
        super().__init__(("127.0.0.1", 0), FixtureHandler)

    def reset(self, case):
        self.case = case
        self.course = "course-a"
        self.offline = case == "readiness"
        self.drop_network = False
        self.switch_on_submit = ''
        self.rejected_submit = False
        self.images_by_course = {}
        self.calls = []
        self.runs = {}
        self.missing = []
        self.result = None
        self.done = threading.Event()
        self.release_submit = threading.Event()
        self.release_submit.set()
        self.hold_next_status = False
        self.release_status = threading.Event()
        self.release_status.set()


class FixtureHandler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def reply(self, body, status=200, mime="application/json"):
        if not isinstance(body, bytes):
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        route = urlsplit(self.path).path
        if route == "/ui/index.html":
            page = (PATCH / "index.html").read_text(encoding="utf-8")
            page = page.replace("</body>", '<script src="/fixture/check.js"></script><script defer src="/fixture/done.js"></script></body>')
            self.reply(page.encode(), mime="text/html; charset=utf-8")
        elif route == "/fixture/check.js":
            self.reply(BROWSER_CHECK.encode(), mime="application/javascript")
        elif route == "/fixture/done.js":
            self.server.done.wait(18)
            self.reply(b"/* test completed */", mime="application/javascript")
        elif route.startswith("/fixture/image/"):
            self.reply(IMAGES[int(route.rsplit("/", 1)[-1])].read_bytes(), mime="image/png")
        elif route == "/fixture/state":
            self.reply({"calls": self.server.calls, "rejected_submit": self.server.rejected_submit, "stored_courses": list(self.server.images_by_course)})
        elif route.startswith("/runs/"):
            run_id = route.split("/")[2]
            record = self.server.runs[run_id]
            if route.endswith("/export"):
                if record["hold"] == "submit":
                    self.server.release_submit.wait(8)
                elif record["hold"] == "status":
                    self.server.release_status.wait(8)
                result = {"success": False, "error": record["error"]} if record.get("error") else {"success": True, "data": record["data"]}
                self.reply({"items": [{"type": "json", "json": result}]})
            else:
                self.reply({"status": "succeeded"})
        elif "/ui-api/i18n/" in route:
            self.reply({})
        elif route.startswith("/ui/"):
            name = route.removeprefix("/ui/")
            patch = PATCH / name
            stock = STOCK / name
            path = patch if patch.is_file() else stock
            if not path.resolve().is_relative_to(STOCK.resolve()) and not path.resolve().is_relative_to(PATCH.resolve()):
                self.reply({}, 404)
            elif path.is_file():
                self.reply(path.read_bytes(), mime=mimetypes.guess_type(path)[0] or "application/octet-stream")
            else:
                self.server.missing.append(route)
                self.reply({"missing": route}, 404)
        else:
            self.server.missing.append(route)
            self.reply({"missing": route}, 404)

    def do_POST(self):
        route = urlsplit(self.path).path
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))) or "{}")
        if route == "/fixture/result":
            self.server.result = body
            self.server.done.set()
            self.reply({"saved": True})
        elif route == "/fixture/control":
            for key in ("course", "offline", "drop_network", "switch_on_submit"):
                if key in body:
                    setattr(self.server, key, body[key])
            if body.get("hold_submit"):
                self.server.release_submit.clear()
            if body.get("release_submit"):
                self.server.release_submit.set()
            if body.get("hold_next_status"):
                self.server.hold_next_status = True
                self.server.release_status.clear()
            if body.get("release_status"):
                self.server.release_status.set()
            self.reply({})
        elif route == "/runs":
            if self.server.drop_network:
                self.connection.close()
                self.close_connection = True
                return
            if self.server.offline:
                self.reply({"error": "test host not ready"}, 503)
                return
            entry = body["entry_id"]
            self.server.calls.append(body)
            data = {}
            error = None
            if entry == "study_status":
                data = {"status": "idle", "mode": "companion", "study_course_id": self.server.course,
                        "state": {"study_course_id": self.server.course}, "config": {"llm_vision_max_image_px": 2048}}
            elif entry in ("study_submit_image", "study_explain_text"):
                data = {"reply": "FAKE " + body["args"].get("text", ""), "degraded": False}
                if entry == "study_submit_image":
                    if self.server.switch_on_submit:
                        self.server.course = self.server.switch_on_submit
                        self.server.switch_on_submit = ''
                    if body["args"].get("expected_course_id") != self.server.course:
                        self.server.rejected_submit = True
                        # Actual SDK run serialization wraps SdkError as INTERNAL.
                        error = {"code": "INTERNAL", "message": "Plugin 'study_companion' entry 'entry study_submit_image' execution failed: 课程已切换，请重新选择当前课程的图片后提交。"}
                    else:
                        self.server.images_by_course[self.server.course] = body["args"]["image_base64"]
            elif entry == "study_question_context":
                data = {"no_data": True}
            elif entry == "study_memory_list_decks":
                data = {"decks": []}
            elif entry == "study_get_settings_config":
                data = {"config": {"llm": {"llm_vision_max_image_px": 2048}}}
            elif entry == "study_start_session":
                self.server.course = body["args"]["course_id"]
                data = {"course_id": self.server.course}
            run_id = str(len(self.server.runs) + 1)
            hold = "submit" if entry in ("study_submit_image", "study_explain_text") and not self.server.release_submit.is_set() else ""
            if entry == "study_status" and self.server.hold_next_status:
                hold = "status"
                self.server.hold_next_status = False
            self.server.runs[run_id] = {"data": data, "hold": hold, "error": error}
            self.reply({"run_id": run_id})
        else:
            self.server.missing.append(route)
            self.reply({}, 404)


class DailyImageUI(unittest.TestCase):
    def test_actual_dom_flows(self):
        original_hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in IMAGES}
        server = FixtureServer()
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        outcomes = []
        try:
            cases = [("flow", "--desktop"), ("races", "--desktop"), ("readiness", "--desktop"), ("flow", "--mobile"), ("preview", "--desktop"), ("preview", "--mobile"), ("onboarding", "--desktop"), ("onboarding", "--mobile"), ("course-submit", "--desktop")]
            selected_cases = os.environ.get("NEKO_IMAGE_UI_CASES", "").split(",")
            if selected_cases != [""]:
                cases = [(case, viewport) for case, viewport in cases if case in selected_cases]
            for case, viewport in cases:
                server.reset(case)
                result = subprocess.run(["node", r"D:\AI\tools\web-inspector\cli.mjs",
                    f"http://127.0.0.1:{server.server_port}/ui/index.html?case={case}", viewport, "--screenshot", "--json"],
                    capture_output=True, text=True, encoding="utf-8", timeout=30)
                inspector = json.loads(result.stdout)
                summary = {"case": case, "viewport": viewport, "checks": server.result,
                           "missing_routes": server.missing, "inspector": inspector,
                           "calls": [{"entry_id": c["entry_id"], "text": c["args"].get("text", ""),
                                      "image_sha256": hashlib.sha256(c["args"].get("image_base64", "").encode()).hexdigest() if c["args"].get("image_base64") else ""} for c in server.calls]}
                attempt = EVIDENCE / f"daily-companion-image-ui-{time.time_ns()}-{case}-{viewport[2:]}.json"
                attempt.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
                print(json.dumps({"evidence": str(attempt), "checks": server.result, "missing_routes": server.missing}, ensure_ascii=True), flush=True)
                outcomes.append(summary)
            self.assertEqual(original_hashes, {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in IMAGES})
            self.assertTrue(all(o["checks"] and all(c["pass"] for c in o["checks"]) for o in outcomes), "Actual DOM failures are preserved in the per-scenario evidence JSON")
            self.assertTrue(all(not o["missing_routes"] for o in outcomes), "Missing static assets/routes")
            final = EVIDENCE / f"daily-companion-image-ui-{time.time_ns()}-passed.json"
            final.write_text(json.dumps({"results": outcomes, "source_image_sha256": original_hashes}, ensure_ascii=False, indent=2), encoding="utf-8")
        finally:
            server.release_submit.set()
            server.release_status.set()
            server.done.set()
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)


if __name__ == "__main__":
    unittest.main()
