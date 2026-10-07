import ctypes, ctypes.wintypes as wintypes, os, glob, time, subprocess

print("=== N.E.K.O 相关目录 ===")
cands = []
for base in (os.environ.get("APPDATA"), os.environ.get("LOCALAPPDATA"),
             os.path.expanduser("~"), os.environ.get("TEMP")):
    if not base:
        continue
    for pat in ("*neko*", "*N.E.K.O*", "*Project*N*"):
        cands += glob.glob(os.path.join(base, pat))
for c in sorted(set(cands)):
    try:
        st = os.stat(c)
        isdir = os.path.isdir(c)
        n = len(os.listdir(c)) if isdir else 0
        print("  %-6s %s  %s  entries=%s" % ("DIR" if isdir else "FILE", c, time.strftime("%Y-%m-%d %H:%M", time.localtime(st.st_mtime)), n))
    except Exception as e:
        print("  ERR", c, e)

print("\n=== Documents 目录 ===")
docs = os.path.join(os.path.expanduser("~"), "Documents")
try:
    for d in os.listdir(docs):
        if "neko" in d.lower():
            print("  ", d)
except Exception as e:
    print("  ", e)

print("\n=== Windows 事件日志：最近 10 分钟的 Application Error ===")
ps = r"""
$since=(Get-Date).AddMinutes(-12)
Get-WinEvent -FilterHashtable @{LogName='Application';StartTime=$since} -ErrorAction SilentlyContinue |
  Where-Object { $_.LevelDisplayName -in @('Error','Warning') } |
  Select-Object -First 12 TimeCreated,ProviderName,Id,@{n='Msg';e={($_.Message -split "`n")[0..3] -join ' | '}} |
  Format-List
"""
r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True, timeout=90)
print(r.stdout[:4000] if r.stdout else "(no stdout)")
print("STDERR:", r.stderr[:500])
