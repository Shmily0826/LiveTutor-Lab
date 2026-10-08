"""Stage 1 correlation: watch for a specific awareness reply to land in the UI.

Sequence (all in one process, one timeline):
  1. note the Main log offset and snapshot the character panel,
  2. enable awareness (push_to_llm_mode=respond),
  3. poll the Main log every 5s for `trigger_agent_callbacks enter` +
     `agent_callback_turn=True` (the host finishing a proactive turn),
  4. the moment the turn completes, grab the panel full-frame 1:1,
  5. keep grabbing on a short cadence for a few seconds,
  6. always restore the awareness config.

The UI grab is a single full-panel crop read at 1:1 (1472px wide, accepted by
the viewer), which is what makes the correlation visual instead of log-only.
"""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import json
import re
import subprocess
import sys
import time
from pathlib import Path

from neko_lab_client import LabClient, status_summary
from neko_lab_stage import ROOT

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()

u32 = ctypes.windll.user32

PY = r'C:\Users\Shmily\.workbuddy\binaries\python\envs\default\Scripts\python.exe'
GUI = r'C:\Users\Shmily\.workbuddy\skills\windows-desktop-control\scripts\gui.py'
EVIDENCE = ROOT / 'benchmarks/raw/evidence'
MAIN_LOG = ROOT / 'benchmarks/raw/neko-store/logs/N.E.K.O_Main_20261008.log'
CHAR_TITLE = 'Carbon-Based Lifeform Terminal'


def find_char_window():
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, _):
        if u32.IsWindowVisible(hwnd) and not u32.IsIconic(hwnd):
            buf = ctypes.create_unicode_buffer(256)
            u32.GetWindowTextW(hwnd, buf, 256)
            if CHAR_TITLE in buf.value:
                rect = wintypes.RECT()
                u32.GetWindowRect(hwnd, ctypes.byref(rect))
                found.append([rect.left, rect.top, rect.right, rect.bottom])
        return True

    u32.EnumWindows(cb, 0)
    return found[0] if found else None


def grab(rect, path):
    subprocess.run([PY, GUI, 'crop', str(rect[0]), str(rect[1]),
                    str(rect[2]), str(rect[3]), str(path)],
                   capture_output=True, text=True, encoding='utf-8')
    return str(path)


def read_log():
    return MAIN_LOG.read_text(encoding='utf-8', errors='replace') if MAIN_LOG.exists() else ''


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser()
    parser.add_argument('--seconds', type=int, default=120)
    parser.add_argument('--tag', default='stage1-correlate')
    options = parser.parse_args()

    client = LabClient()
    original = status_summary(client.call('study_status'))['awareness']
    before_text = read_log()
    before_turns = len(re.findall(r'agent_callback_turn=True', before_text))

    evidence = {'tag': options.tag, 'original_awareness': original,
                'before_callback_turns': before_turns, 'frames': []}
    target = EVIDENCE / f'goal-{options.tag}.json'
    rect = find_char_window()
    evidence['char_rect'] = rect
    if not rect:
        print(json.dumps({'error': 'character window not visible'}, ensure_ascii=False))
        return

    try:
        enabled = {**original, 'enabled': True, 'snapshot_interval_seconds': 1,
                   'push_to_llm_interval_seconds': 30, 'push_to_llm_mode': 'respond'}
        client.call('study_update_settings_config', {'config': {'awareness': enabled}})
        print('awareness enabled', flush=True)

        stamp = time.strftime('%H%M%S')
        first = EVIDENCE / f'{options.tag}-t0-{stamp}.png'
        grab(rect, first)
        evidence['frames'].append({'at': time.strftime('%H:%M:%S'), 'phase': 'enabled',
                                   'path': str(first),
                                   'turns': len(re.findall(r'agent_callback_turn=True', read_log()))})

        deadline = time.time() + options.seconds
        fired = False
        while time.time() < deadline:
            time.sleep(5)
            text = read_log()
            turns = len(re.findall(r'agent_callback_turn=True', text))
            state = status_summary(client.call('study_status'))
            print(json.dumps({'turns': turns, 'ticks': (state['awareness_runtime'] or {}).get('completed_ticks'),
                              'push': (state['awareness_runtime'] or {}).get('push_status')},
                             ensure_ascii=False), flush=True)
            if turns > before_turns and not fired:
                fired = True
                # the turn just landed: capture immediately, then twice more
                for index, delay in enumerate((0.0, 4.0, 9.0)):
                    if delay:
                        time.sleep(delay)
                    shot = EVIDENCE / f'{options.tag}-hit{index}-{stamp}.png'
                    grab(rect, shot)
                    evidence['frames'].append({
                        'at': time.strftime('%H:%M:%S'),
                        'phase': f'post-turn-{index}',
                        'path': str(shot), 'turns': turns})
                    print('captured', shot, flush=True)
                new_lines = text[len(before_text):].splitlines()
                evidence['turn_log'] = [line for line in new_lines
                                        if re.search(r'proactive|callback|agent_notification|'
                                                     r'rerouted|goodbye_silent', line, re.I)][-30:]
    finally:
        client.call('study_update_settings_config', {'config': {'awareness': original}})
        restored = status_summary(client.call('study_status'))
        evidence['restored_config'] = restored['awareness'] == original
        evidence['restored_runtime'] = restored['awareness_runtime']
        target.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding='utf-8')
        print('restored:', evidence['restored_config'], 'fired:', 'turn_log' in evidence, flush=True)


if __name__ == '__main__':
    main()
