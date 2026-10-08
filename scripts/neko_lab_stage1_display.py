"""Stage 1 display acceptance: awareness proactive message -> character UI bubble.

Two prior runs proved the *bridge* half:
  * with goodbye_silent=True  -> submitted_proactive=2, callback_enter=0, callback_turn=0
  * with the session live     -> submitted_proactive=2, callback_enter=2, callback_turn=2
This script closes the *display* half: it drives a real user turn through the
physical character chat panel (which clears goodbye_silent), then enables
awareness and captures the panel 1:1 so the assistant reply is visible.

Ordering matters: the desktop driving happens first, while the panel is still
guaranteed unobstructed. The awareness window then runs with the desktop left
alone, and the config is restored in a finally block.

It never sends Enter into an app that is not the character window.
"""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import json
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
k32 = ctypes.windll.kernel32

PY = r'C:\Users\Shmily\.workbuddy\binaries\python\envs\default\Scripts\python.exe'
GUI = r'C:\Users\Shmily\.workbuddy\skills\windows-desktop-control\scripts\gui.py'
EVIDENCE = ROOT / 'benchmarks/raw/evidence'

VK_MENU = 0x12
SW_RESTORE = 9
HWND_TOPMOST = -1
SWP_FLAGS = 0x0001 | 0x0002 | 0x0040


def title_of(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    u32.GetWindowTextW(hwnd, buf, 256)
    return buf.value


def find_char_window():
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, _):
        if u32.IsWindowVisible(hwnd) and not u32.IsIconic(hwnd):
            buf = ctypes.create_unicode_buffer(256)
            u32.GetWindowTextW(hwnd, buf, 256)
            title = buf.value
            pid = wintypes.DWORD()
            u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            handle = k32.OpenProcess(0x1000, False, pid.value)
            path = ''
            if handle:
                try:
                    size = wintypes.DWORD(1024)
                    pbuf = ctypes.create_unicode_buffer(1024)
                    if k32.QueryFullProcessImageNameW(handle, 0, pbuf,
                                                      ctypes.byref(size)):
                        path = pbuf.value
                finally:
                    k32.CloseHandle(handle)
            if 'N.E.K.O.exe' in path and ('Terminal' in title or 'Carbon' in title):
                rect = wintypes.RECT()
                u32.GetWindowRect(hwnd, ctypes.byref(rect))
                found.append({'hwnd': int(hwnd), 'title': title,
                              'rect': [rect.left, rect.top, rect.right, rect.bottom]})
        return True

    u32.EnumWindows(cb, 0)
    return found[0] if found else None


def raise_window(hwnd):
    u32.keybd_event(VK_MENU, 0, 0, 0)
    u32.ShowWindow(hwnd, SW_RESTORE)
    u32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_FLAGS)
    u32.SetForegroundWindow(hwnd)
    u32.SetActiveWindow(hwnd)
    u32.keybd_event(VK_MENU, 0, 2, 0)
    time.sleep(0.6)


def gui(*args):
    return subprocess.run([PY, GUI, *args], capture_output=True, text=True,
                          encoding='utf-8', errors='replace')


def drive_turn(text, tag):
    """Click the chat input, paste, verify the foreground, send Enter."""
    report = {'text': text}
    target = find_char_window()
    if not target:
        report['error'] = 'character window not found'
        return report
    report['window'] = target
    hwnd = target['hwnd']
    left, top = target['rect'][0], target['rect'][1]
    x, y = left + 940, top + 540
    report['click_point'] = [x, y]

    raise_window(hwnd)
    fg = u32.GetForegroundWindow()
    report['foreground_after_raise'] = {'hwnd': int(fg), 'title': title_of(fg),
                                        'ok': int(fg) == hwnd}
    if int(fg) != hwnd:
        report['aborted'] = 'character window not foreground before acting'
        return report

    gui('click', str(x), str(y))
    time.sleep(0.5)
    raise_window(hwnd)
    gui('paste', text)
    time.sleep(0.9)

    filled = EVIDENCE / f'{tag}-filled.png'
    gui('crop', '2100', '490', '2800', '600', str(filled))
    report['filled_shot'] = str(filled)

    raise_window(hwnd)
    fg_before = int(u32.GetForegroundWindow())
    report['foreground_before_enter'] = {'hwnd': fg_before, 'title': title_of(fg_before),
                                         'ok': fg_before == hwnd}
    if fg_before != hwnd:
        report['aborted'] = ('character window is not the foreground; '
                             'refusing to send Enter into another app')
        return report

    gui('key', 'enter')
    report['sent'] = True
    time.sleep(11.0)

    after = EVIDENCE / f'{tag}-after.png'
    gui('crop', str(left), '0', str(left + 900), '620', str(after))
    report['after_shot'] = str(after)
    return report


def shot_panel(tag, stamp):
    target = find_char_window()
    if not target:
        return []
    left, top, _, bottom = target['rect']
    paths = []
    for index, offset in enumerate((0, 900)):
        width = 900 if offset == 0 else target['rect'][2] - left - 900
        if width <= 0:
            continue
        path = EVIDENCE / f'{tag}-crop{index}-{stamp}.png'
        gui('crop', str(left + offset), str(top),
            str(left + offset + width), str(bottom), str(path))
        paths.append(str(path))
    return paths


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser()
    parser.add_argument('--seconds', type=int, default=60)
    parser.add_argument('--tag', default='stage1-display')
    parser.add_argument('--text', default='一句话确认你还在：现在继续讲这道题。')
    parser.add_argument('--skip-drive', action='store_true')
    options = parser.parse_args()

    evidence = {'tag': options.tag}
    target_path = EVIDENCE / f'goal-{options.tag}.json'

    try:
        if not options.skip_drive:
            evidence['turn'] = drive_turn(options.text, options.tag)
        evidence['before_agent'] = ctypes.windll.kernel32.GetCurrentProcessId()

        client = LabClient()
        original = status_summary(client.call('study_status'))['awareness']
        evidence['original_awareness'] = original

        # one pre-run sample: who is the character, is the session awake?
        try:
            import urllib.request
            with urllib.request.urlopen('http://127.0.0.1:48915/agent/state',
                                        timeout=5) as response:
                evidence['agent_state_before'] = json.load(response)
        except Exception as error:  # noqa: BLE001
            evidence['agent_state_before'] = {'error': str(error)}

        if options.skip_drive:
            evidence['turn'] = {'skipped': True}

        after_turn = shot_panel(options.tag, 'pretest')
        evidence['panel_before_awareness'] = after_turn

        enabled = {**original, 'enabled': True, 'snapshot_interval_seconds': 1,
                   'push_to_llm_interval_seconds': 30, 'push_to_llm_mode': 'respond'}
        client.call('study_update_settings_config',
                    {'config': {'awareness': enabled}})

        evidence['samples'] = []
        deadline = time.time() + options.seconds
        while time.time() < deadline:
            time.sleep(5)
            state = status_summary(client.call('study_status'))
            sample = {'runtime': state['awareness_runtime'],
                      'push_status': (state['awareness_runtime'] or {}).get('push_status')}
            evidence['samples'].append(sample)
            print(json.dumps(sample, ensure_ascii=False), flush=True)
            target_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2),
                                   encoding='utf-8')

        # capture the panel while awareness is still live
        evidence['panel_during_awareness'] = shot_panel(options.tag, 'live')
    finally:
        try:
            client  # noqa: F821
        except NameError:
            client = LabClient()
        client.call('study_update_settings_config',
                    {'config': {'awareness': evidence.get('original_awareness') or build_default()}})
        restored = status_summary(client.call('study_status'))
        evidence['restored_config'] = restored['awareness'] == evidence.get('original_awareness')
        evidence['restored_runtime'] = restored['awareness_runtime']
        target_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2),
                               encoding='utf-8')
        print('restored:', evidence['restored_config'], flush=True)


def build_default():
    return {'enabled': False, 'snapshot_interval_seconds': 5,
            'context_window_minutes': 5, 'classify_mode': 'title_first',
            'image_max_bytes': 65536, 'push_to_llm_interval_seconds': 300,
            'push_to_llm_mode': 'read', 'os_signals_enabled': True,
            'distraction_detection': True}


if __name__ == '__main__':
    main()
