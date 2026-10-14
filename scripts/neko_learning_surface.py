"""Read-only learning materials and guidance on a loopback-only controlled surface.

Only explicit files are exposed; HTML must be trusted developer-owned standalone
material. No audio, provider requests, desktop capture, or source writes.
"""
from __future__ import annotations

import argparse
import base64
import binascii
from contextlib import closing
import hashlib
import html
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import re
from pathlib import Path
import secrets
import sqlite3
import threading
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MATERIALS = [
    Path(r"D:\UoA\S2\COMPSCI 734\project\Sky Scout\sky_scout\.archify\architecture-sky-scout-20261003-192623\sky-scout.html"),
    ROOT / ".archify/architecture-relations-20261013-230748/forward/forward.html",
    ROOT / ".archify/architecture-relations-20261013-230748/reverse/reverse.html",
    ROOT / "benchmarks/raw/evidence/diagram-input-forward.png",
    ROOT / "benchmarks/raw/evidence/diagram-input-reverse.png",
    ROOT / "benchmarks/raw/evidence/diagram-input-sky-dark.png",
]
TYPES = {".html": "text/html; charset=utf-8", ".htm": "text/html; charset=utf-8",
         ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
RAW = ROOT / "benchmarks/raw"
STUDY_SELECTION = "@study"


class StudyPictureSnapshot:
    """Only persisted course/session and that course's one submitted image.

    Never instantiate StudyStore (its constructor can write/migrate). This is a
    coherent SQLite read transaction, not the plugin's live/boot authority.
    """
    def __init__(self, store):
        self.store = Path(store).resolve(strict=True)
        self.db = self.store / "N.E.K.O/plugins/study_companion/data/study_companion.db"
        self.checked_db()

    def checked_db(self):
        raw = RAW.resolve(strict=True)
        path = self.db.resolve(strict=True)
        if not raw.is_relative_to(ROOT.resolve()) or not self.store.is_dir() or not self.store.is_relative_to(raw) or not path.is_relative_to(self.store) or not path.is_file():
            raise ValueError("Study store 必须是项目 benchmarks/raw 内已存在的任务目录")
        return path

    def read(self):
        path = self.checked_db()
        # Do not use immutable=1: an active writer's WAL contains current data.
        with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=.25)) as db:
            db.execute("PRAGMA query_only=ON")
            db.execute("BEGIN")
            row = db.execute("SELECT json_extract(value,'$.study_course_id'), json_extract(value,'$.study_session_id') FROM kv WHERE key='state'").fetchone()
            if not row or not isinstance(row[0], str) or not row[0].strip() or len(row[0]) > 1000 or (row[1] is not None and not isinstance(row[1], str)):
                raise ValueError("没有有效的已保存课程状态")
            course, session = row[0], row[1] or ""
            key = "submitted_image:" + hashlib.sha256(course.encode()).hexdigest()
            # Bound the fetched value, and project only material fields, not history.
            saved = db.execute("SELECT CASE WHEN length(value)<=16020000 THEN json_extract(value,'$.course_id') END, CASE WHEN length(value)<=16020000 THEN json_extract(value,'$.image') END, CASE WHEN length(value)<=16020000 THEN json_extract(value,'$.text') END FROM kv WHERE key=?", (key,)).fetchone()
        context = {"course_id": course, "session_id": session}
        if saved is None:
            return {**context, "status": "empty", "message": "当前课程尚未提交图片。请在 Study 中提交后再来看。"}, None
        image, text = saved[1], saved[2] or ""
        if saved[0] != course or not isinstance(image, str) or not image or len(image) > 16_000_000 or not isinstance(text, str) or len(text) > 12000:
            raise ValueError("当前课程的图片记录无效")
        # Keep the exact stored string in the identity calculation, as Study does.
        identity = hashlib.sha256((image + "\0" + text).encode()).hexdigest()
        mime = None
        if image.startswith("data:"):
            match = re.match(r"^data:(image/(?:png|jpeg));base64,", image)
            if not match:
                raise ValueError("当前图片格式不受支持；请使用 PNG 或 JPEG")
            mime = match.group(1)
            image = image[match.end():]
        try:
            content = base64.b64decode(image, validate=True)
        except (ValueError, binascii.Error):
            raise ValueError("当前图片内容无效") from None
        actual_mime = "image/png" if content.startswith(b"\x89PNG\r\n\x1a\n") else "image/jpeg" if content.startswith(b"\xff\xd8\xff") else None
        if not actual_mime or (mime and mime != actual_mime):
            raise ValueError("当前图片内容与格式不匹配")
        digest = hashlib.sha256(content).hexdigest()
        scope = hashlib.sha256(json.dumps([course, session, identity], ensure_ascii=False).encode()).hexdigest()
        material_id = "study-" + scope[:24]
        material = {"id": material_id, "name": "当前 Study 图片 · " + course[:100],
                    "kind": "image", "source": "study_store_snapshot", "sha256": digest,
                    "course_id": course, "session_id": session, "material_identity": identity,
                    "url": "/material/" + material_id, "content": content, "mime": actual_mime}
        return {**context, "status": "ready", "message": "已显示当前课程的已保存图片。",
                "material_id": material_id, "image_sha256": digest, "material_identity": identity}, material


class PointingTargets(HTMLParser):
    """Locator metadata only; never use this as evidence of image relationships."""
    def __init__(self):
        super().__init__()
        self.targets = []

    def handle_starttag(self, tag, attributes):
        if len(self.targets) >= 80:
            return
        attrs = dict(attributes)
        for name in ("data-node-id", "data-edge-id", "data-line"):
            value = attrs.get(name)
            if not isinstance(value, str) or not value or len(value) > 100:
                continue
            escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\a ").replace("\r", "\\d ")
            label = attrs.get("data-node-label") or attrs.get("data-edge-label") or value
            if name == "data-edge-id":
                label = f"{attrs.get('data-edge-from', '')} → {attrs.get('data-edge-to', '')} · {label}"
            self.targets.append({"selector": f'[{name}="{escaped}"]', "label": str(label)[:160],
                                 "type": name, "id": value})
            break


class LearningSurface(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, materials, port=48918, *, store=None):
        self.paths = [Path(p).resolve(strict=True) for p in materials]
        if not self.paths and store is None:
            raise ValueError("请指定至少一份 HTML、PNG 或 JPEG 学习材料")
        self.token = secrets.token_urlsafe(32)
        self.lock = threading.RLock()
        self.materials = {}
        self.command = None
        self.active_material_id = None
        self.revision = 0
        self.study_reader = StudyPictureSnapshot(store) if store is not None else None
        self.follow_study = self.study_reader is not None
        self.study = None
        self.reload_materials()
        super().__init__(("127.0.0.1", port), SurfaceHandler)

    def reload_materials(self):
        # Read fully before publishing so a failed reload preserves the old view.
        materials = {}
        for index, path in enumerate(self.paths):
            if path.suffix.lower() not in TYPES or path.stat().st_size > 32 * 1024 * 1024:
                raise ValueError("材料必须是独立 HTML、PNG 或 JPEG，且不超过 32 MB")
            content = path.read_bytes()
            digest = hashlib.sha256(content).hexdigest()
            material_id = f"{index}-{digest[:24]}"
            materials[material_id] = {"id": material_id, "name": path.name,
                "sha256": digest, "kind": "html" if path.suffix.lower() in (".html", ".htm") else "image",
                "url": f"/material/{material_id}", "content": content,
                "mime": TYPES[path.suffix.lower()]}
            if path.suffix.lower() in (".html", ".htm"):
                parser = PointingTargets()
                parser.feed(content.decode("utf-8", errors="replace"))
                materials[material_id]["targets_for_pointing"] = parser.targets
        with self.lock:
            self.materials = materials
            if self.active_material_id not in materials:
                self.active_material_id = next(iter(materials), None)
            self.command = None
            self.revision += 1
            if self.study_reader is not None:
                self.study = None  # reload replaced the dynamic entry as well
            self.refresh_study()

    def refresh_study(self):
        if self.study_reader is None:
            return
        with self.lock:
            try:
                status, material = self.study_reader.read()
            except (ValueError, OSError, sqlite3.Error):
                # No raw exception/path/data leakage; stale images fail closed.
                status, material = {"status": "unavailable", "message": "无法读取当前课程图片。请确认 Study 已保存，恢复后会自动更新。"}, None
            if status == self.study:
                return
            self.study = status
            stale = [key for key, item in self.materials.items() if item.get("source") == "study_store_snapshot"]
            for key in stale:
                self.materials.pop(key)
            if material:
                self.materials[material["id"]] = material
            if self.follow_study:
                self.active_material_id = material["id"] if material else None
            elif self.active_material_id in stale:
                self.active_material_id = None
            self.command = None
            self.revision += 1

    def attach_study_store(self, store):
        # A fresh launch creates its database after this local server starts.
        reader = StudyPictureSnapshot(store)
        with self.lock:
            self.study_reader = reader
            self.follow_study = True
            self.study = None
            self.refresh_study()

    def state(self):
        with self.lock:
            self.refresh_study()
            return {"materials": [{k: v for k, v in m.items() if k not in ("content", "mime")}
                                  for m in self.materials.values()],
                    "revision": self.revision, "active_material_id": self.active_material_id, "command": self.command,
                    "study": {**self.study, "following": self.follow_study} if self.study else None}

    def show_code_evidence(self, payload):
        evidence = payload.get("evidence")
        if not isinstance(evidence, str) or not evidence.strip() or len(evidence) > 12000:
            raise ValueError("源码证据必须非空，且不超过12000字符")
        project = str(payload.get("project") or "authorized project")[:100]
        commit = str(payload.get("repo_commit") or "unversioned")[:80]
        digest = hashlib.sha256((project + "@" + commit + "\n" + evidence).encode()).hexdigest()
        material_id = "code-" + digest[:24]
        lines, source_targets = [], []
        source_file, in_source = "", False
        for index, line in enumerate(evidence.splitlines(), 1):
            target = f"evidence-{index}"
            lines.append(f'<div data-line="{target}" data-node-label="{html.escape(line[:120], quote=True)}">{html.escape(line)}</div>')
            header = re.fullmatch(r'\*\*`([^`]+)`\*\*(?:\s+—\s+.*)?', line.strip())
            if header:
                source_file = header.group(1)
            if line.strip().startswith('```'):
                if in_source:
                    in_source, source_file = False, ""
                else:
                    in_source = bool(source_file)
            number = re.match(r'^(\d+)\t', line) if in_source and source_file else None
            if number:
                source_targets.append({"selector": f'[data-line="{target}"]', "label": line[:160],
                                       "type": "data-line", "id": target,
                                       "source_file": source_file, "source_line": int(number.group(1))})
        content = ('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
                   '<title>当前源码证据</title><style>body{margin:24px;background:#101a1a;color:#edf4f1;font:16px/1.7 system-ui}h1{font-size:22px}p{color:#b3c7c0}pre{font:14px/1.8 Consolas,monospace;white-space:pre-wrap;overflow-wrap:anywhere}pre div{min-height:1.8em}::selection{background:#007f68;color:white}</style>'
                   f'<h1>{html.escape(project)} · {html.escape(commit)}</h1>'
                   '<p>仅显示本次工具返回的授权源码证据。下列原始行号属于该版本；没有展示的部分仍是未知或推断。</p><pre>'
                   + "\n".join(lines) + '</pre></html>').encode()
        parser = PointingTargets(); parser.feed(content.decode())
        material = {"id": material_id, "name": f"当前源码证据 · {project}@{commit[:12]}",
                    "sha256": hashlib.sha256(content).hexdigest(), "kind": "html", "source": "filtered_codegraph_evidence",
                    "url": f"/material/{material_id}", "content": content, "mime": TYPES[".html"],
                    "targets_for_pointing": source_targets[:80] if source_targets else parser.targets}
        with self.lock:
            if material_id in self.materials:
                return {"material_id": material_id, "sha256": material["sha256"],
                        "next": "这份源码证据已在学习窗口中；保留当前选择和指示。"}
            stale = [key for key, item in self.materials.items() if item.get("source") == "filtered_codegraph_evidence"]
            for key in stale: self.materials.pop(key)
            self.materials[material_id] = material
            if self.active_material_id in stale:
                self.active_material_id = material_id
                self.command = None
            self.revision += 1
        return {"material_id": material_id, "sha256": material["sha256"],
                "next": "学习者在学习窗口选择这份源码证据后，可用study_point指向其中已展示的代码行。"}

    def select(self, material_id):
        with self.lock:
            self.refresh_study()
            if material_id == STUDY_SELECTION and self.study_reader is not None:
                self.follow_study = True
                self.active_material_id = self.study.get("material_id")
                self.command = None
                self.revision += 1
                return self.state()
            if material_id not in self.materials:
                raise LookupError("材料版本已更新，请重新选择")
            self.active_material_id = material_id
            if self.study_reader is not None:
                self.follow_study = self.materials[material_id].get("source") == "study_store_snapshot"
            self.command = None
            self.revision += 1
            return self.state()

    def guide(self, command):
        with self.lock:
            self.refresh_study()
            material = self.materials.get(command.get("material_id"))
            if material is None:
                raise LookupError("材料已更换，请重新选择当前材料")
            if material["id"] != self.active_material_id:
                raise LookupError("这不是当前显示的材料，请先由学习者切换材料")
            kind = command.get("kind")
            clean = {"material_id": material["id"], "kind": kind,
                     "label": str(command.get("label", "正在解释这里"))[:160]}
            if kind == "selector" and material["kind"] == "html":
                selector = command.get("selector")
                if not isinstance(selector, str) or not selector.strip() or len(selector) > 300:
                    raise ValueError("请提供有效的 HTML 目标选择器")
                clean["selector"] = selector
            elif kind == "rect" and material["kind"] == "image":
                values = [command.get(k) for k in ("x", "y", "width", "height")]
                if any(type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 1 for v in values):
                    raise ValueError("图片区域必须使用 0 到 1 的归一化坐标")
                x, y, width, height = values
                if width <= 0 or height <= 0 or x + width > 1 or y + height > 1:
                    raise ValueError("图片区域不能为空或超出图片")
                clean.update(zip(("x", "y", "width", "height"), values))
            elif kind != "clear":
                raise ValueError("HTML 使用 selector；图片使用 rect；清除使用 clear")
            self.command = clean if kind != "clear" else None
            self.revision += 1
            return self.state()


class SurfaceHandler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def reply(self, status, body, mime="application/json; charset=utf-8", material=False):
        if not isinstance(body, bytes):
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self' data: blob:; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'self'" + ("; form-action 'none'" if material else ""))
        self.end_headers()
        self.wfile.write(body)

    def allowed(self, auth=False):
        expected = f"127.0.0.1:{self.server.server_port}"
        if self.headers.get("Host") != expected:
            self.reply(403, {"error": "只允许使用本机 127.0.0.1 地址"})
            return False
        if auth and not secrets.compare_digest(self.headers.get("X-Learning-Surface-Token", ""), self.server.token):
            self.reply(403, {"error": "此学习窗口的授权标识无效，请重新打开"})
            return False
        return True

    def do_GET(self):
        if not self.allowed():
            return
        route = urlsplit(self.path).path
        if route == "/":
            page = Path(__file__).with_suffix(".html").read_text(encoding="utf-8")
            bootstrap = json.dumps({"token": self.server.token}, ensure_ascii=False).replace("<", "\\u003c")
            self.reply(200, page.replace("__BOOTSTRAP__", bootstrap).encode("utf-8"), "text/html; charset=utf-8")
        elif route == "/api/state":
            if self.allowed(auth=True):
                self.reply(200, self.server.state())
        elif route.startswith("/material/"):
            with self.server.lock:
                self.server.refresh_study()
                material = self.server.materials.get(route.removeprefix("/material/"))
            if material:
                self.reply(200, material["content"], material["mime"], material=True)
            else:
                self.reply(404, {"error": "材料版本已更新，请重新载入"})
        else:
            self.reply(404, {"error": "没有这个学习页面"})

    def do_POST(self):
        if not self.allowed(auth=True):
            return
        try:
            route = urlsplit(self.path).path
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= (65536 if route == "/api/code-evidence" else 4096):
                raise ValueError("指示请求为空或过长")
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError("指示请求必须是对象")
            if route == "/api/guidance":
                result = self.server.guide(payload)
            elif route == "/api/reload":
                self.server.reload_materials()
                result = self.server.state()
            elif route == "/api/select":
                result = self.server.select(payload.get("material_id"))
            elif route == "/api/code-evidence":
                result = self.server.show_code_evidence(payload)
            else:
                self.reply(404, {"error": "没有这个操作"})
                return
            self.reply(200, result)
        except LookupError as exc:
            self.reply(409, {"error": str(exc)})
        except (ValueError, TypeError, OSError) as exc:
            self.reply(400, {"error": str(exc)})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--material", action="append", type=Path, help="explicit trusted standalone HTML or PNG/JPEG; repeatable")
    parser.add_argument("--port", type=int, default=48918)
    parser.add_argument("--store", type=Path, help="existing task store under project benchmarks/raw; readonly current Study image")
    args = parser.parse_args()
    server = LearningSurface(args.material or DEFAULT_MATERIALS, args.port, store=args.store)
    print(f"Learning surface: http://127.0.0.1:{server.server_port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
