"""
THE decisive experiment: can an EXTERNAL brain service register tools into
N.E.K.O and receive callbacks, without forking N.E.K.O?

LiveTutor Brain is a stdlib ThreadingHTTPServer. This stands up a server with
the same shape on loopback and registers it through the product's own public
API. Schema discovered empirically: registration is PER-TOOL, flat fields
{name, callback_url, ...}, plus a `source` discriminator on clear().
"""
import json, threading, time, urllib.request, urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE = "http://127.0.0.1:48911"
CALLBACK_PORT = 48977
received = []
srv = None


class Brain(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self._send({"ok": True, "role": "livetutor-brain-stub", "path": self.path})

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(n) if n else b"{}"
        try:
            body = json.loads(raw)
        except Exception:
            body = {"_unparsed": raw.decode("utf8", "replace")}
        received.append({"path": self.path, "body": body})
        print(f"  [BRAIN CALLBACK] POST {self.path}")
        print(f"                   payload keys = {sorted(body.keys())}")
        print(f"                   payload = {json.dumps(body, ensure_ascii=False)[:400]}")
        if "screen" in self.path:
            self._send({"ok": True, "observation": "a button labelled Submit",
                        "text": "Submit  Cancel", "elements": 2})
        else:
            self._send({"ok": True, "verdict": "grounded", "result": "stub-reply"})


def call(path, meth="GET", payload=None, timeout=60):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=meth)
    req.add_header("Content-Type", "application/json")
    t = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw, st = r.read(), r.status
    except urllib.error.HTTPError as e:
        raw, st = e.read(), e.code
    ms = (time.perf_counter() - t) * 1000
    try:
        js = json.loads(raw)
    except Exception:
        js = raw.decode("utf8", "replace")[:400]
    return st, js, ms


srv = ThreadingHTTPServer(("127.0.0.1", CALLBACK_PORT), Brain)
threading.Thread(target=srv.serve_forever, daemon=True).start()
CB = f"http://127.0.0.1:{CALLBACK_PORT}"
print(f"external brain stand-in listening on {CB}\n")

print("=== 1. baseline: product's own tools ===")
st, js, _ = call("/api/tools")
print(f"  GET /api/tools -> {st}")
for role, tools in (js.get("tools_by_role") or {}).items():
    names = [t.get("name") if isinstance(t, dict) else t for t in tools] \
        if isinstance(tools, list) else list(tools)
    print(f"    role {role}: {names}")

TOOLS = [
    ("livetutor_read_screen", "Read the learner's current screen and return "
     "grounded visual facts. Use before describing anything on screen.",
     {"type": "object",
      "properties": {"focus": {"type": "string", "description": "optional UI region hint"}},
      "required": []},
     "/livetutor-brain/read_screen"),
    ("livetutor_ground_claim", "Check whether a statement the tutor is about to "
     "make is actually grounded in what is on screen.",
     {"type": "object", "properties": {"claim": {"type": "string"}},
      "required": ["claim"]},
     "/livetutor-brain/ground_claim"),
]

print("\n=== 2. register each tool (per-tool, flat schema) ===")
for name, desc, params, path in TOOLS:
    st, js, ms = call("/api/tools/register", "POST", {
        "name": name, "description": desc, "parameters": params,
        "callback_url": CB + path, "source": "livetutor_brain",
    })
    print(f"  register {name:<26} -> {st} in {ms:.0f}ms  {json.dumps(js, ensure_ascii=False)[:220]}")

print("\n=== 3. do they show up in the tool list? ===")
st, js, _ = call("/api/tools")
for role, tools in (js.get("tools_by_role") or {}).items():
    names = [t.get("name") if isinstance(t, dict) else t for t in tools] \
        if isinstance(tools, list) else list(tools)
    hit = [n for n in names if n and n.startswith("livetutor_")]
    print(f"    role {role}: {names}")
    if hit:
        print(f"      ^^^ EXTERNAL BRAIN TOOLS VISIBLE: {hit}")
print(f"  raw keys: {list(js.keys())}")
print(f"  full: {json.dumps(js, ensure_ascii=False)[:1200]}")

print("\n=== 4. SSRF posture: is callback_url forced to loopback? ===")
for label, bad in [("public host", "http://example.com/hook"),
                   ("cloud metadata", "http://169.254.169.254/latest/meta-data/"),
                   ("loopback", f"{CB}/ok")]:
    st, js, _ = call("/api/tools/register", "POST", {
        "name": "probe_ping_zzz", "description": "probe",
        "parameters": {"type": "object", "properties": {}},
        "callback_url": bad, "source": "livetutor_brain"})
    print(f"  {label:<16} {bad:<42} -> {st} "
          f"{'ACCEPTED' if st == 200 else 'rejected'} {json.dumps(js)[:120]}")
    if st == 200:
        call("/api/tools/unregister", "POST", {"name": "probe_ping_zzz",
                                              "source": "livetutor_brain"})

print("\n=== 5. is the callback reachable + does the product know how to call it? ===")
# (a) direct reachability of the callback URL we registered
try:
    with urllib.request.urlopen(CB + "/livetutor-brain/read_screen", data=b'{}',
                                timeout=10) as r:
        print(f"  direct GET callback -> {r.status} {r.read()[:120].decode()}")
except urllib.error.HTTPError as e:
    print(f"  direct GET callback -> {e.code}")
# (b) product-driven invocation needs a configured LLM provider
for p in ["/api/system/status"]:
    st, js, _ = call(p)
    if isinstance(js, dict):
        print(f"  {p}: status={js.get('status')} ready={js.get('ready')}")
        for k, v in js.items():
            if any(t in k.lower() for t in ("llm", "provider", "model", "chat", "agent")):
                print(f"    {k} = {json.dumps(v, ensure_ascii=False)[:300]}")

print(f"\n  callbacks received so far: {len(received)}")

print("\n=== 6. unregister ===")
for name, *_ in TOOLS:
    st, js, _ = call("/api/tools/unregister", "POST",
                     {"name": name, "source": "livetutor_brain"})
    print(f"  unregister {name:<26} -> {st} {json.dumps(js)[:160]}")
st, js, _ = call("/api/tools/clear", "POST", {"source": "livetutor_brain"})
print(f"  clear source=livetutor_brain -> {st} {json.dumps(js)[:160]}")
st, js, _ = call("/api/tools")
print(f"  final tool list: {json.dumps(js, ensure_ascii=False)[:300]}")

srv.shutdown()
print("\n=== DONE ===")
