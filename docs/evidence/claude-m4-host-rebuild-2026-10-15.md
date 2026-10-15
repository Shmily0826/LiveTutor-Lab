# M4：宿主可从干净环境重建（Claude Goal）

日期 2026-10-15。证据层级：本地确定性检查，无外部调用。

## 发现

- 宿主的 31 个改动文件位于被 git 忽略的 `benchmarks/raw/neko-product-host`，仓库里只有 SHA 记录和字符串补丁脚本。
- 用启动链（`apply_voice_host_patch`）对 upstream `1d814cf` 的干净导出重放，**会失败**：`_tools.py` 的 hunk 2 和 hunk 10 都锚定在原始 `_run` 块的不同历史版本上，而 owner-trace 迁移又会提前改写这一段。这些字符串补丁只能"升级"按项目历史一路改过来的树，无法从 upstream 按任何固定顺序重放。启动不受影响，因为现有树已处于打完补丁的状态。
- 另一个隐患：在 Windows 上 `core.autocrlf=true` 会改写导出的行尾，manifest 钉的是 LF 字节。

## 交付

- `scripts/neko_host_rebuild_check.py`：
  - `--write`：只在 live 树与 manifest 全部一致时，生成 `patches/neko-study-2026-10-10-host/rebuild/` 下每个文件一份 unified diff（upstream → 钉住的字节，共 31 份、344 KB，可逐份审查）。
  - 默认模式：`git archive`（强制 LF）导出 upstream → 在 `benchmarks/raw` 下的临时目录 `git apply` 全部 diff → 与 manifest 的 `patched_sha256` 逐文件比较。
- 结果：**31/31 一致**，`git apply` 退出 0；临时目录已删除，项目根目录无写入。
- 处理过的两个坑：
  - git 把 `--no-index` 的目录名写进路径头，已用 `--no-prefix` 解决；
  - 临时树位于本仓库内时，`git apply` 会按外层仓库解析路径并静默跳过，已用 `GIT_CEILING_DIRECTORIES` 隔离。
- 字符串补丁脚本仍是启动时的升级路径；diff 是可复现的重建路径。之后任何宿主补丁改动，都要先 `--write` 再提交（live 不一致时会拒绝）。
- 另外：`test_neko_phrase_patch_replay` 已改为与启动链同序重放本 Goal 的停顿暂扣补丁，并验证与两个宿主树逐字节相同。

## 范围外与前提

- 需要 `candidates/N.E.K.O` 中有 upstream 提交 `1d814cf`（公开的 N.E.K.O 仓库）。
- 宿主的 Python 虚拟环境（`.venv`，依赖安装）不在重建范围内。
- 运行时 helper（`scripts/neko_phrase_input_*.py` 等）本来就在仓库里，由启动时部署并由 SourceGate 按 SHA 核对。
