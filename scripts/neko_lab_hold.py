"""Hold N.E.K.O alive: spawn it with a clean env + --no-sandbox, then stay resident.

Why this is needed:
  * The sandbox exports ELECTRON_RUN_AS_NODE=1 / NODE_OPTIONS=... -> without stripping
    them N.E.K.O.exe runs as bare Node and exits rc=0 after ~5s.
  * Chromium's sandbox cannot initialise under the sandbox's token -> browser process
    dies with STATUS_BREAKPOINT (0x80000003) ~1.5s after spawning the backend, and the
    Job Object reaps openfang + projectneko_server with it. --no-sandbox avoids this.
  * A hand-started backend self-terminates when its launcher exits (owner supervision,
    mechanism "parent_handle"), and the sandbox reaps the process tree when a tool call
    ends -- so this holder must stay resident for the app to survive.

Run it as a background task; the desktop lives as long as this process does.
"""
import os
import socket
import subprocess
import sys
import time

APP = r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\neko-app\N.E.K.O.exe"
HOLD = float(sys.argv[1]) if len(sys.argv) > 1 else 7200.0


def ports():
    up = []
    for p in (48911, 48912, 48915, 48916):
        s = socket.socket()
        s.settimeout(0.3)
        try:
            s.connect(("127.0.0.1", p))
            up.append(p)
        except Exception:
            pass
        s.close()
    return up


def main():
    env = os.environ.copy()
    env.pop("ELECTRON_RUN_AS_NODE", None)
    env.pop("NODE_OPTIONS", None)
    env["USERPROFILE"] = r"C:\Users\Shmily"
    env["APPDATA"] = r"C:\Users\Shmily\AppData\Roaming"
    env["LOCALAPPDATA"] = r"C:\Users\Shmily\AppData\Local"

    log = open(r"D:\CODE\project\LiveTutor-Lab\benchmarks\raw\evidence\desktop-hold.log", "wb")
    proc = subprocess.Popen(
        [APP, "--no-sandbox"],
        cwd=os.path.dirname(APP),
        env=env,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        stdout=log,
        stderr=subprocess.STDOUT,
    )
    print("desktop pid %d; holding %.0fs" % (proc.pid, HOLD), flush=True)

    t0 = time.time()
    last = None
    while time.time() - t0 < HOLD:
        time.sleep(5.0)
        up = ports()
        rc = proc.poll()
        if (tuple(up), rc) != last:
            print("  %5ds ports=%r rc=%r" % (int(time.time() - t0), up, rc), flush=True)
            last = (tuple(up), rc)
        if rc is not None:
            print("  desktop exited rc=%r (0x%08X); relaunching"
                  % (rc, rc & 0xFFFFFFFF), flush=True)
            proc = subprocess.Popen(
                [APP, "--no-sandbox"], cwd=os.path.dirname(APP), env=env,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                stdout=log, stderr=subprocess.STDOUT)
            print("  new desktop pid %d" % proc.pid, flush=True)
    log.flush()
    log.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
