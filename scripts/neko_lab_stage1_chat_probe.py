"""Stage 1 probe: drive one normal character chat turn and correlate delivery.

Read-only w.r.t. configuration. It:
  1. snapshots /agent/state (48915) before the turn,
  2. types a unique probe message into the character chat input via desktop control,
  3. snapshots state after, and greps the main log tail for callback delivery lines.

It never reads provider credentials and never writes awareness config.
"""
import json
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'benchmarks/raw/evidence'
MAIN_LOG = ROOT / 'benchmarks/raw/neko-store/logs/N.E.K.O_Main_20261008.log'
PY = r'C:\Users\Shmily\.workbuddy\binaries\python\envs\default\Scripts\python.exe'
GUI = r'C:\Users\Shmily\.workbuddy\skills\windows-desktop-control\scripts\gui.py'

PROBE_TEXT = 'STAGE1-PROBE-20261008 请用一句话确认你能看到这条消息。'


def agent_state():
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open('http://127.0.0.1:48915/agent/state', timeout=8) as response:
        return json.load(response).get('snapshot', {})


def log_tail(lines=400):
    if not MAIN_LOG.exists():
        return ''
    text = MAIN_LOG.read_text(encoding='utf-8', errors='replace').splitlines()
    return '\n'.join(text[-lines:])


def gui(*args):
    return subprocess.run([PY, GUI, *args], capture_output=True, text=True,
                          encoding='utf-8', errors='replace')


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    before_state = agent_state()
    before_notification = before_state.get('notification')
    before_log = log_tail()
    result = {'probe_text': PROBE_TEXT,
              'before': {'notification': before_notification,
                         'revision': before_state.get('revision')}}
    print(json.dumps(result['before'], ensure_ascii=False), flush=True)

    # Locate the character window and bring it forward.
    windows = gui('windows')
    try:
        listing = json.loads(windows.stdout)
    except Exception:
        listing = []
    target = None
    for window in listing:
        path = window.get('path') or ''
        title = window.get('title') or ''
        if 'N.E.K.O.exe' in path and window.get('visible') and (
                'Carbon-Based' in title or 'Terminal' in title):
            target = window
            break
    result['window'] = {k: target.get(k) for k in ('hwnd', 'title', 'rect')} if target else None
    print(json.dumps(result['window'], ensure_ascii=False), flush=True)

    if not target:
        result['error'] = 'character window not found'
        (EVIDENCE / 'stage1-chat-probe.json').write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        return

    hwnd = str(target['hwnd'])
    gui('focus', hwnd)
    time.sleep(1.0)
    # Input point calibrated from a 1:1 `crop` of the live screen, NOT from the
    # downscaled shotwin (1472px physical rendered at 1080px => factor ~0.734,
    # using it put the click ~330px off). The handle bar sits at y~498 and the
    # text row at y~540 across the panel's usable width.
    input_x, input_y = 2350, 540
    result['input_point'] = [input_x, input_y]
    # Paste through the clipboard so IME cannot mangle the ASCII probe marker.
    gui('click', str(input_x), str(input_y))
    time.sleep(0.6)
    gui('paste', PROBE_TEXT)
    time.sleep(0.8)
    shot = EVIDENCE / 'stage1-chat-input-filled.png'
    gui('shot', str(shot))
    result['input_shot'] = str(shot)
    gui('key', 'enter')
    time.sleep(6.0)
    after_shot = EVIDENCE / 'stage1-chat-after-enter.png'
    gui('shot', str(after_shot))
    result['after_shot'] = str(after_shot)

    after_state = agent_state()
    result['after'] = {'notification': after_state.get('notification'),
                       'revision': after_state.get('revision')}
    after_log = log_tail()
    new_lines = [line for line in after_log.splitlines()
                 if line not in before_log.splitlines()]
    interesting = [line for line in new_lines
                   if re.search(r'proactive|callback|delivery|trigger_agent|websocket|STAGE1', line, re.I)]
    result['new_log_lines'] = interesting[-40:]
    print(json.dumps({'after': result['after'], 'new_lines': len(new_lines),
                      'interesting': len(interesting)}, ensure_ascii=False), flush=True)
    (EVIDENCE / 'stage1-chat-probe.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
