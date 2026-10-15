# 未改目录跳过空结果强制同步

日期：2026-10-15。背景：[源码计时间隙报告](codex-followup-gap-emptyturn-2026-10-15.md)。

## 改动

`study_code_tools.py::_code_sync` 的成功同步指纹比较不再受 `not force` 限制。`force=True` 仍绕过原有节流判断，但如果当前 `_code_tree_fingerprint(root)` 非空且等于 `_code_synced_fingerprint(root)`，直接返回 `unchanged`，不启动 CodeGraph sync。空结果调用方仅在返回 `synced` 时重查，因此该情形不再出现 `source_retry_query`。

指纹不同、计算异常或没有保存的成功同步状态时仍执行原同步；同步成功后仍保存指纹。新增、删除、改名、编辑等改变已有指纹的操作仍可触发同步。未改过滤、授权、版本校验、节流参数、计时或调用方重试逻辑。

**尚无真实场计时，待下次自然使用验证。** 历史 trace `6365b9e1349b` 的约2.9秒间隙是背景证据，不能当成本次节省时间的实测结果。

## 离线验证

使用 `benchmarks/raw/neko-product-host/.venv/Scripts/python.exe`，设置 `PYTHONIOENCODING=utf-8`，在 `scripts` 目录运行：

```text
python -B -m unittest -v test_neko_code_sync_fingerprint test_neko_code_timing test_neko_code_file_window test_neko_code_structure_request test_neko_source_point test_neko_project_code_teaching test_neko_source_route_memory
```

**52/52 通过，0 失败、0 跳过，15.834秒。** 新增测试覆盖：

- 同一实例及重启后读取已保存状态，目录未改时 `force=True` 返回 `unchanged`，不执行同步。
- 成功同步后新增文件，仍在节流窗口内时 `force=True` 照常同步。
- 无保存状态或指纹计算失败时 `force=True` 照常同步。
- 实际 `_code_sync` 与 `study_code_tool` 联合运行：目录未改、首次状态分别为 `unchanged/throttled` 时，仅有一次查询，无 sync 命令，无 `source_retry_query`；仍记录 `source_retry_sync` 的检查时间。

既有编辑、删除、改名、build忽略、同步失败、节流、文件窗口、过滤与授权等回归保持通过。旧测试中“force无条件同步”的断言由新的精确用例替代。所有同步/查询 IO 使用 mock，测试只操作临时 fixture，没有执行真实 CodeGraph CLI。

部署后在 `scripts` 下调用 `neko_desktop_tutor_host.verify_source_audio_gate()`：**PASS**。该调用仅检查源码指纹和 runtime helper，不启动宿主。

原始证据（不提交）：`benchmarks/raw/evidence/codex-resync-skip-regression-20261015.log`、`codex-resync-skip-sourcegate-20261015.log`。

## 部署、SHA 与发布

开工先核对 payload、product manifest 条目及已部署 `study_code_tools.py` 三方旧 SHA256 均为 `70c4e831331bd239e0a253fc95a1fe45f92ff55d3bed8b91fc4716c7be0d116b`。旧副本与开工文件保存在 `benchmarks/raw/evidence/codex-resync-skip-backup-20261015/`，不提交备份。

部署前再次核对 manifest、已部署副本及开工备份的旧 SHA 一致，再复制新 payload；复制后 payload、manifest 和部署副本三方新 SHA 均为 `9d389504681dd7ca9a869b1cd854df842686780145bbfdcafa06cec0d881c01e`。product manifest 仅更新该条目的 SHA、旧 SHA 与本次简短说明。Native 宿主文件及 host manifest 未变。

| 文件 | SHA256 |
|---|---|
| `patches/neko-study-2026-10-10-product/payload/study_companion/study_code_tools.py` | `9d389504681dd7ca9a869b1cd854df842686780145bbfdcafa06cec0d881c01e` |
| `scripts/test_neko_code_sync_fingerprint.py` | `4080000d32542ac9d8ec9841315f4b057e0111a4153b15785e594d09ec741fb4` |
| `scripts/test_neko_code_timing.py` | `27d87bb33ed7e427c5577e3f5a039ac46b926b9fee65363ea737046dc3507db1` |
| `patches/neko-study-2026-10-10-product/manifest.json` | `585334da9670769846a1cacccf99c2783a1b2e18f0d535757e7cf95df90b88a6` |
| `docs/claude-goal-status.md` | `f4ebc90b8d94c5e05962a16529d0e851ca0e49976f70dd7afecb29ea93d3e31b` |

本报告自身SHA见 [校验清单](codex-resync-skip-2026-10-15.sha256)，清单覆盖以上5项及报告；清单自身由Git提交标识，避免自引用。交付内容为UTF-8/LF。

发布使用 `C:\Users\Shmily\.codex\worktrees\daily-companion\LiveTutor-Lab`，分支 `codex/daily-learning-companion`。本次5个既有文件与发布副本的开工基线一致，父提交为 `72f8ea5b6606f0999d221f13920286ab28fdb5c7`。仅发布代码、两个测试、product manifest、状态追加、本报告与相邻SHA清单，共7个文件；不提交 raw、备份或学习库，不合并主分支、不强推。提交自身作为本报告的发布版本标识。

## 账本与边界

轮次 `bargein-autocheck-20261012`，开工和完成后实核均为 DeepSeek **968**、Lanlan.app **90**，各新增 **0**，预算不变。核对记录保存在上述备份目录的 `preflight.json` 和 `completion.json`，不提交 raw。

仅离线测试及源码/部署指纹检查；不调用模型，不启动宿主或 Native 场，不启动麦克风、虚拟或真实采集、回环；不操作系统音量。不修改 Sky Scout 或其索引，不清理根目录工作树，不修改学习库或用户历史。本次未开展真实模型、output-only Native、设备可听性或真人验收。
