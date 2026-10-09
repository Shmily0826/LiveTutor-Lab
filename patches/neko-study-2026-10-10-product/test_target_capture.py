"""Offline capture safety check: fake window metadata and PIL, no desktop pixels."""
import ast
import asyncio
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

source = Path(__file__).with_name("payload").joinpath("study_companion", "entry_ocr_entries.py").read_text(encoding="utf-8")
tree = ast.parse(source)
names = {"_marker_list", "_markers_matched", "_capture_named_window_image"}
nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
entry = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "_OcrEntriesMixin")
method = next(n for n in entry.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "study_ocr_snapshot")
method.decorator_list = []
nodes.append(ast.ClassDef(name="Entry", bases=[], keywords=[], body=[method], decorator_list=[]))
assert "capture_snapshot" not in ast.unparse(method), "Product entry must not invoke screen-capable pipeline backends"
grabs = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "grab"]
assert grabs and all(any(k.arg == "bbox" for k in call.keywords) for call in grabs)

grabs_seen, ocr_seen = [], []
target = {"title": "Test Lesson", "left": 10, "top": 20, "right": 1010, "bottom": 720}
resolutions = []
foreground = [7]
dpi_active = False

def resolve(title):
    assert dpi_active, "Window measurement must share capture DPI context"
    assert title == "Test Lesson"
    return resolutions.pop(0) if resolutions else (dict(target), "", 7)

def bounded_grab(*args, **kwargs):
    assert not args and kwargs == {"bbox": (10, 20, 1010, 720)}
    assert dpi_active
    grabs_seen.append(kwargs)
    return "fake bounded image"

def dpi(fn):
    global dpi_active
    dpi_active = True
    try:
        return fn()
    finally:
        dpi_active = False

pil = ModuleType("PIL")
pil.ImageGrab = SimpleNamespace(grab=bounded_grab)
backends = ModuleType("offline.study_capture_backends")
backends._run_with_thread_dpi_awareness = dpi
backends._crop_image_to_profile = lambda image, profile: image
pipeline = ModuleType("offline.study_ocr_pipeline")
pipeline.StudyCaptureProfile = lambda **kwargs: kwargs
sys.modules.update({"PIL": pil, "offline.study_capture_backends": backends, "offline.study_ocr_pipeline": pipeline})

env = {"__package__": "offline", "asyncio": asyncio, "_named_window_target": resolve,
       "_foreground_hwnd": lambda: foreground[0], "_window_title": lambda hwnd: "Test Lesson",
       "Err": lambda error: {"error": error.message}, "Ok": lambda data: {"ok": data},
       "SdkError": lambda message, **kwargs: SimpleNamespace(message=message),
       "build_ocr_payload": lambda s: {"status": s.status, "text": s.text}}
exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])), "offline_capture", "exec"), env)
host = env["Entry"]()

def ocr(image):
    ocr_seen.append(image)
    return SimpleNamespace(status="ok", text="ChangeNotifier context.watch", captured_at="now")

async def noop(*args, **kwargs):
    return {}

host._ocr_pipeline = SimpleNamespace(snapshot_from_image=ocr)
host._cfg = SimpleNamespace(ocr_left_inset_ratio=0, ocr_right_inset_ratio=0, ocr_top_ratio=0, ocr_bottom_inset_ratio=0)
host._supervision = None
host._lock = asyncio.Lock()
host._state = SimpleNamespace()
host._update_screen_classification = noop
host._persist_state = noop
args = {"capture_mode": "target_window", "window_title": "Test Lesson", "expected_markers": ["ChangeNotifier", "context.watch"], "min_marker_matches": 2}

async def check():
    for mode in [None, "", "fullscreen", "interactive", "active_window"]:
        kwargs = {} if mode is None else {"capture_mode": mode}
        assert "error" in await host.study_ocr_snapshot(**kwargs)
    assert not grabs_seen and not ocr_seen
    success = await host.study_ocr_snapshot(**args)
    assert success["ok"]["target_window_markers_matched"] == 2
    assert len(grabs_seen) == len(ocr_seen) == 1
    assert success["ok"]["active_window_capture_route"] == "pil_bbox_crop"
    for change in [(None, "target_window_not_foreground", 7), ({**target, "right": 999}, "", 7), (dict(target), "", 9)]:
        resolutions[:] = [(dict(target), "", 7), change]
        assert "error" in await host.study_ocr_snapshot(**args)
    assert len(grabs_seen) == len(ocr_seen) == 1, "Before-grab mismatch must read zero pixels"
    foreground[0] = 8
    assert "error" in await host.study_ocr_snapshot(**args)
    assert len(grabs_seen) == 2 and len(ocr_seen) == 1, "After-grab foreground change must prevent OCR/persistence"
    foreground[0] = 7
    assert host._state.last_ocr_text == "ChangeNotifier context.watch"
    print("PASS: target-only API; all grabs have exact bbox under DPI; changed HWND/rect/focus refused; zero fullscreen/backend capture calls.")

asyncio.run(check())
