# -*- coding: utf-8 -*-
"""Burst-capture N.E.K.O chat area screenshots. Usage: python neko_burst_shots.py <prefix>"""
import subprocess
import sys
import time

GUI = "C:/Users/Shmily/.workbuddy/skills/windows-desktop-control/scripts/gui.py"
EV = "D:/CODE/project/LiveTutor-Lab/benchmarks/raw/evidence"
CROP = ("1500", "200", "2880", "1100")
DELAYS = (4, 5, 8)  # cumulative t=4, t=9, t=17


def gui(*args):
    r = subprocess.run(
        [sys.executable, GUI, *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    out = (r.stdout or "").strip()
    err = (r.stderr or "").strip()
    return out if out else ("ERR: " + err if err else "ERR: empty")


def main():
    prefix = sys.argv[1]
    elapsed = 0
    for i, d in enumerate(DELAYS, 1):
        time.sleep(d)
        elapsed += d
        out = f"{EV}/{prefix}-t{elapsed}.png"
        print(f"shot{i} t={elapsed}s ->", out)
        print(gui("crop", *CROP, out))


if __name__ == "__main__":
    main()
