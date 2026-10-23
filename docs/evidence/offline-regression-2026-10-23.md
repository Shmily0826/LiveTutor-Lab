# 离线回归 2026-10-23（仓库整理之后）

> **2026-10-23 19:10 更正**：初版把"骨架树落后 13 天"写成"日常启动跑 10-10 旧代码"，
> 那是错的。骨架树只是**分发源**，`prepare_product_plugin()` 每次启动都会用仓库 payload
> 覆盖它，运行时目录 `store/plugin-code/study_companion/` 与 payload 的 hash 实测完全相同。
> 见文末"更正记录"。

## 口径

- 分支 `codex/daily-learning-companion`。整理后起点 `83369d8`，补模块后 `10c24de`。
- 所有模块用 `benchmarks/raw/neko-product-host/.venv/Scripts/python.exe -B -m unittest <module>`，
  cwd 在 `scripts`，`PYTHONIOENCODING=utf-8`，**每个模块一个独立进程**，单模块 300 秒超时。
  整套放同一进程会被隔离守卫串扰出假错误，这条是 10-15 定下的口径。
- 汇总：`benchmarks/raw/offline-regression-20261023/summary.txt`
- 逐模块原始输出：`benchmarks/raw/offline-regression-20261023/logs/<module>.log`
- 跑批脚本：`benchmarks/raw/run_offline_regression_20261023.sh`

## 结果

| 项 | 数值 |
|---|---|
| 模块数 | 113（`scripts/test_neko_*.py`） |
| 通过 | **104** |
| 失败 | **9** |
| 超时 | 0 |
| 耗时 | 569 秒 |

历史基线（`docs/claude-goal-status.md`，10-16）：116 模块 109 通过、7 个历史失败。
7 个历史失败中 **6 个复现**，`test_neko_autocheck_readiness` 本次通过。

### 复现的 6 个历史失败（已记录在案，非新问题）

`test_neko_first_asr_ordering`、`test_neko_late_asr_tool_patch`、`test_neko_material_audio`、
`test_neko_study_singleflight`、`test_neko_study_speech_gate`、`test_neko_tool_result_lifecycle`。
原因与 10-16 记录一致：这些宿主补丁夹具对着已叠加 M2/M3 补丁的宿主文件匹配旧补丁，
典型报错 `unknown edited late-ASR helper; preserve and inspect`。

### 3 个新失败

**1. `test_neko_acceptance_preparation` —— 缺模块（已修，真缺口）**

`ModuleNotFoundError: No module named 'neko_native_avatar_toolchain'`。
该文件只存在于 `master`，`codex/daily-learning-companion` 从来没有带过来，但有 **13 个脚本**
import 它——包括验收指南里那条一键准备课程命令用的 `neko_prepare_acceptance_course.py`。
AST 扫描确认这是**唯一**一个缺失的本地 `neko_*` 模块。
处理：从 master 取回（152 行，只用标准库），重跑 `test_neko_acceptance_preparation` 2 tests OK。
提交 `10c24de`。

**2. `test_neko_study_answer_intent` → `test_symlink_outside_refused` —— 沙箱干扰 cleanup**

20 个用例里 19 个通过，唯一错误发生在清理阶段：
`self.db.unlink()` 抛 `FileNotFoundError`，调用栈明确经过
`D:\AI\WorkBuddy-2\resources\app.asar.unpacked\cli\vendor\shim\sitecustomize.py`
的 `_safe_remove`。这是 WorkBuddy 注入的 unlink 钩子，不是被测代码。
**判定：环境干扰（INFERRED，未在无钩子环境复跑对照）。**

**3. `test_neko_study_summary_scope` —— 测试读的是分发树，不是运行时树**

`AttributeError: 'StudyState' object has no attribute 'study_course_id'`，
抛在 `benchmarks/raw/neko-app/resources/bin/plugins/study_companion/__init__.py:794`。

那条路径是**骨架分发树**，不是产品运行时加载的代码。`neko_study_plugin_methods_fixture` 第 131 行
把 `RELEASE`（即骨架树）放进 `sys.path` 再 `import plugins.study_companion`，所以测试测的是骨架。
骨架树停在 10-10（`models.py` 无 `study_course_id`），而源码已有该字段 → 测试假红。
**产品不受影响**（见下）。

## 运行时的真实链路（已验证，不是推断）

`neko_desktop_tutor_host.py:274 prepare_product_plugin()`：

1. `source = APP/"plugins/study_companion"` —— 骨架树，只提供文件清单、`plugin.toml`、静态资源
2. `target = store/"plugin-code/study_companion"` —— **真正被加载的目录**
3. 先复制骨架的文件，随后**用 `PRODUCT/"payload/study_companion"` 覆盖全部同名文件**
4. 最后就地改 `plugin.toml`（视觉、communication 关闭、narration 关闭等）
5. 调用点 `neko_desktop_tutor_host.py:1076`，**每次启动宿主都会执行**

实测（日常库 `neko-daily-companion`）：

| 文件 | 运行时 `store/plugin-code/…` | 源码 payload | 一致 |
|---|---|---|---|
| `__init__.py` | `e5b23987d333` | `e5b23987d333` | 是 |
| `models.py` | `bab98d7a7b95` | `bab98d7a7b95` | 是 |

**结论：日常启动加载的是仓库当前 payload，10-15～10-16 的修复会生效。复测前不需要同步骨架树。**

唯一残留的卫生问题：payload 里**没有**的文件会保留骨架的 10-10 版本（先复制骨架、再覆盖），
所以骨架树长期不更新会让"已删除/未纳入 payload 的旧文件"继续存在。不是当前复测的阻塞项。

## 没有做的事

- 没有启动 N.E.K.O、没有开麦、没有采集/回环、没有改音量、没有外呼。
  DeepSeek 账本仍是 1825（停止线 1861）。
- 没有同步骨架树（会让第 3 个测试转绿，但那是改运行环境，要用户点头）。
- 没有改宿主补丁，没有动 6 个历史失败夹具。

## 更正记录

19:10 —— 初版基于"骨架树 = 运行时"的假设，写了"日常启动跑 10-10 旧代码、修复不生效、
复测前必须同步部署树"。读到 `prepare_product_plugin()` 的 payload 覆盖逻辑后，
该推断被推翻：`store/plugin-code/` 与 payload 的 `__init__.py`、`models.py` hash 完全相同，
且部署每次启动都执行。初版结论作废，误差已在本版修正。
