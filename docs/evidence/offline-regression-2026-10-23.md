# 离线回归 2026-10-23（仓库整理之后）

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

**1. `test_neko_acceptance_preparation` —— 缺模块（已修，非环境问题）**

`ModuleNotFoundError: No module named 'neko_native_avatar_toolchain'`。
该文件只存在于 `master`，`codex/daily-learning-companion` 从来没有带过来，但有 **13 个脚本**
import 它——包括验收指南里那条一键准备课程命令用的 `neko_prepare_acceptance_course.py`。
AST 扫描确认这是**唯一**一个缺失的本地 `neko_*` 模块。
处理：从 master 取回（152 行，只用标准库），`test_neko_acceptance_preparation` 重跑 2 tests OK。提交 `10c24de`。

**2. `test_neko_study_answer_intent` → `test_symlink_outside_refused` —— 沙箱干扰 cleanup**

20 个用例里 19 个通过，唯一错误发生在清理阶段：
`self.db.unlink()` 抛 `FileNotFoundError`，而调用栈里明确经过
`D:\AI\WorkBuddy-2\resources\app.asar.unpacked\cli\vendor\shim\sitecustomize.py`
的 `_safe_remove`。这是 WorkBuddy 注入的 unlink 钩子，不是被测代码。
**判定：环境干扰（INFERRED，未在无钩子环境复跑对照）。**

**3. `test_neko_study_summary_scope` —— 部署树落后于源码**

`AttributeError: 'StudyState' object has no attribute 'study_course_id'`，
抛在**已部署运行树**里：`benchmarks/raw/neko-app/resources/bin/plugins/study_companion/__init__.py:794`。
不是仓库 `patches/.../payload` 里的代码。

## 重大发现：部署树落后 13 天

| 位置 | `__init__.py` | `models.py` 的 `study_course_id` | 最后修改 |
|---|---|---|---|
| 部署树 `benchmarks/raw/neko-app/resources/bin/plugins/study_companion/` | 62540 B | **0 次** | **10-10 15:19** |
| 源码 `patches/neko-study-2026-10-10-product/payload/study_companion/` | 65771 B | 1 次 | 10-23 |

逐文件比对（sha256）：

- PRODUCT 根（`resources/bin/plugins/…`）：相同 1、不同 24、部署树缺 7
- BRIDGE 根（`resources/bin/plugin/plugins/…`）：相同 0、不同 23、部署树缺 9
- 两个 `__init__.py` 的 diff 有 3089 行

`scripts/neko_tutor_start.py` 里**没有任何部署/同步动作**（grep 无 deploy/stage/copy payload），
`Start-Daily-Tutor-Voice.cmd` 也只调它。用户级目录
`%APPDATA%\N.E.K.O`、`%LOCALAPPDATA%\N.E.K.O` 下都没有插件代码。
日常 store `benchmarks/raw/neko-daily-companion/N.E.K.O/plugins/study_companion/` 只有 `config/` 和 `data/`，没有 py。

**推断（INFERRED，未从运行时日志确证）：日常启动加载的是部署树那份 10-10 的代码，
10-15～10-16 的修复不会生效。** 没有跑启动验证——用户当时在图书馆，启动会出声。

这条如果成立，会直接影响定向复测的有效性：复测前必须先把 payload 同步到部署树，
否则测到的是 10-10 的行为，修复项全部判负。

## 没有做的事

- 没有启动 N.E.K.O、没有开麦、没有采集/回环、没有改音量、没有外呼。
  DeepSeek 账本仍是 1825（停止线 1861）。
- 没有同步部署树（会改变运行环境，要用户点头）。
- 没有改宿主补丁，没有动 6 个历史失败夹具。
