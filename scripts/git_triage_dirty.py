"""Classify every dirty/untracked path: is the on-disk content already in a branch?

Read-only. Prints counts only; writes nothing to the repo.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REF = sys.argv[1] if len(sys.argv) > 1 else "codex/daily-learning-companion"


def git(*args, **kw):
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True,
        encoding="utf-8", errors="surrogateescape", **kw
    )


# path -> blob hash for the reference branch
tree = {}
out = git("ls-tree", "-r", "-z", REF).stdout
for rec in out.split("\0"):
    if not rec:
        continue
    meta, _, path = rec.partition("\t")
    parts = meta.split()
    if len(parts) >= 3 and parts[1] == "blob":
        tree[path.replace("\\", "/")] = parts[2]

# every dirty or untracked path
status = git("status", "--porcelain", "-z", "--untracked-files=all").stdout
entries = []
for rec in status.split("\0"):
    if len(rec) < 4:
        continue
    code, path = rec[:2], rec[3:]
    entries.append((code, path.replace("\\", "/")))

# hash working-tree content in bulk
paths = [p for _, p in entries if (ROOT / p).is_file()]
proc = subprocess.run(
    ["git", "hash-object", "--stdin-paths"], cwd=ROOT,
    input="\n".join(paths), capture_output=True, text=True,
    encoding="utf-8", errors="surrogateescape",
)
hashes = proc.stdout.split("\n")
disk = dict(zip(paths, hashes))

same, diff, gone = [], [], []
for code, path in entries:
    if path not in disk:
        gone.append((code, path))
        continue
    ref_hash = tree.get(path)
    if ref_hash and ref_hash == disk[path]:
        same.append((code, path))
    else:
        diff.append((code, path, ref_hash is None))

if "--paths" in sys.argv:
    for code, path, absent in sorted(diff, key=lambda x: x[1]):
        print(path)
    sys.exit(0)

print(f"参考分支: {REF}")
print(f"脏/未跟踪总数: {len(entries)}")
print(f"  已存在于该分支且内容相同: {len(same)}")
print(f"  内容不同 / 该分支没有:    {len(diff)}")
print(f"  路径不存在(已删除):        {len(gone)}")
print()
print("=== 内容真的不同或不存在于该分支的文件 ===")
for code, path, absent in sorted(diff, key=lambda x: x[1]):
    tag = "新增" if absent else "不同"
    print(f"  [{code.strip() or '??'}] {tag}  {path}")
if gone:
    print("=== 已删除路径 ===")
    for code, path in gone[:20]:
        print(f"  [{code.strip()}] {path}")
