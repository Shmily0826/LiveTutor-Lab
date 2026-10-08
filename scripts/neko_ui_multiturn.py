# -*- coding: utf-8 -*-
"""N.E.K.O UI multi-turn proxy test: click input, paste message, Enter, burst-capture reply bubbles.

Usage: python neko_ui_multiturn.py "<message>" <shot-prefix>
Screenshots saved to benchmarks/raw/evidence/<prefix>-t6/t11/t19.png
"""
import subprocess
import sys
import time

GUI = "C:/Users/Shmily/.workbuddy/skills/windows-desktop-control/scripts/gui.py"
EV = "D:/CODE/project/LiveTutor-Lab/benchmarks/raw/evidence"
INPUT_X, INPUT_Y = "2460", "677"
CROP = ("1500", "200", "2880", "1100")
DELAYS = (6, 5, 8)  # cumulative t=6, t=11, t=19


def gui(*args):
    r = subprocess.run(
        [sys.executable, GUI, *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    out = (r.stdout or "").strip()
    err = (r.stderr or "").strip()
    return out if out else ("ERR: " + err if err else "ERR: empty")


def main():
    msg = sys.argv[1]
    prefix = sys.argv[2]

    print("click :", gui("click", INPUT_X, INPUT_Y))
    print("paste :", gui("paste", msg))
    print("enter :", gui("key", "enter"))

    elapsed = 0
    for i, d in enumerate(DELAYS, 1):
        time.sleep(d)
        elapsed += d
        out = f"{EV}/{prefix}-t{elapsed}.png"
        print(f"shot{i} t={elapsed}s ->", out)
        print(gui("crop", *CROP, out))


if __name__ == "__main__":
    main()
