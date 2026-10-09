# N.E.K.O 上游复用与隔离源码宿主（2026-10-10）

## 今晚的决策

继续复用已保存的 Study Companion、原生插件 UI、Store、KnowledgeTracker 和 FSRS。
使用与官方候选提交对应的隔离源码宿主，让文字模式音频阻断可被验证。
不升级整个上游，不重建教学或记忆框架，不把二进制宿主版本字段当作源码身份。

最终已通过隔离源码宿主、原生 Study UI、明确指定的测试窗口与 DeepSeek 完成真实 Flutter 教学验收流程。
启动入口、学习记录、质量结论及剩余限制见[明早交接](neko-v02-morning-handoff-2026-10-10.md)；本文件保留上游核对和局部音频回归的证据边界。

## 当前版本

- 候选 `candidates/N.E.K.O`：官方 `1d814cf32fba8c02b5727d2890710e4e7b8ece24`，2026-10-07；检查时干净。
- [官方 main](https://github.com/Project-N-E-K-O/N.E.K.O)：现场 GitHub API 返回 `3f478bb510059941c2dd62af068ac07c9f411cdd`，2026-10-09，领先候选 22 个提交。
- [最新 GitHub Release](https://github.com/Project-N-E-K-O/N.E.K.O/releases/tag/v0.9.0)：tag `v0.9.0`，2026-08-20 发布，Windows 资产名 `N.E.K.O_v0.9.0.1_win.zip`。
- 本地冻结 `projectneko_server.exe` 的 `1.0.0.0` 字段不能映射到官方提交；没有在本任务中建立该映射。

## Adopt / Adapt

| 能力 | 已有实现 | 今晚用法 |
|---|---|---|
| 指定屏幕源 | 候选 `static/app/app-screen.js` 有 `window.selectScreenSource`、窗口 ID、标题过滤和截图流程 | 复用选择交互思路；泛用分享在源丢失时回退全屏（2302、2443），不得直接开启为受控 Tutor 采集 |
| 区域截图 | `main_routers/system_router/screenshot.py` 的 Windows capture bridge 和 `/screenshot/interactive` | 产品入口已接入明确指定的测试窗口采集；拒绝后无全屏或前台窗口回退，真实捕获证据见下文 |
| 插件原生 UI | `plugin/server/routes/plugin_ui.py`、`frontend/plugin-manager/src/components/plugin/PluginUIFrame.vue`；Study `ui_api.py` 输出 `/plugin/study_companion/ui/` | 使用现成 UI / 插件 action 生命周期，避免新建聊天壳 |
| 教学 | 发布树 `benchmarks/raw/neko-app/resources/bin/plugin/plugins/study_companion` 提供讲解、出题、评分、小结 | 发布实现含本地 overlay 修改；候选未提供同份教学源码，不能声称所有本地改动属于官方 |
| Provider | 主机 `config/providers.py`；Study `study_model_gateway.py` 支持配置的 OpenAI-compatible Provider | 延续 DeepSeek 的已授权路径，限定预算与出口审计；不引入第二 Provider 路由层 |
| 学习记忆 | Study Store/QA/Topics、`knowledge_tracker.py`、`store_fsrs.py` 和 `fsrs_bridge.py`；宿主另有完整持久记忆 | 复用课程/主题和错题记录，完成隔离数据库与真实重启/换课流程；具体结果见交接与记忆运行证据 |
| 音频 | 普通 TTS dummy worker、Native Realtime、ASR 和最终 WebSocket 帧路径均在源码 | 本轮文字产品全部禁用；`DISABLE_TTS` 与插件 silent mode 单独不足以封锁原生路线 |

## 隔离源码宿主

官方入口是 Python 3.11 `launcher.py`。`NEKO_MERGED=1` 可运行同一进程的 Main、Agent、Memory 三个服务；独立入口还有 `python -m app.main_server`、`app.agent_server`、`app.memory_server`。

已用 `git archive` 保留候选精确提交到 `benchmarks/raw/neko-product-host`，未更改候选。
音频局部适配保存于 `patches/neko-study-2026-10-10-host`：

- `NEKO_DEV_TEXT_ONLY=1` 在导入时固定，插件重载不撤销。
- 普通 TTS 在 host selector / Provider selector 之前强制已有 dummy worker；dummy 拒绝并计数文本请求，跳过遥测。
- 原生 Realtime 在 connect 之前将 `_native_audio=False` 并拒绝远程连接；合成原生音频回调也拒绝。
- `send_speech` 以及公共 `_write_audio_frame` 均拒绝并计数，覆盖缓存语音批量发送旁路。
- 可通过 `NEKO_DEV_AUDIO_AUDIT` 保存不含内容的 PID/event/count JSONL。
- 真实启动发现 Agent-LLM 即使 CUA/BrowserUse 默认关闭也执行 Provider ping；局部适配提前返回并计数，隔离 web_search 设置现有 `auto_start=false`。

集中回归为 `PASS_PATCHED_SOURCE_AUDIO_BOUNDARIES`：八个拒绝计数均为 1，Provider/WebSocket/telemetry 假端调用均为 0。此方法级回归实际执行已修改源码与真实 gate，没有向测试注入替代 mute guard；其本身不启动整宿主或经 EventBus 发送插件消息。后续真实源码宿主及 Study UI 教学验收另有完整运行证据，两种证据分别保留。未进行实际声音或麦克风测试。

最终只读核对 `patches/neko-study-2026-10-10-host/manifest.json`：8 个修改后文件 SHA-256 均与当前隔离宿主一致；7 个原文件的基线 SHA-256 均与精确官方提交的 Git blob 一致，新增 gate 的基线为 null。候选 checkout 仍干净。

已有 Python 3.11 为 `benchmarks/raw/goal-python/cpython-3.11.15-windows-x86_64-none/python.exe`。
系统 Python 为 3.14。冻结发布树有 `python311.dll`，没有 Python 可执行入口。
初始 source-libs 和冻结发布目录缺少完整源码依赖。主 Agent 已在 `benchmarks/raw/neko-product-host/.venv` 中按官方 `uv.lock` 安装独立依赖，使用其中的 Python 完成真实源码宿主全流程；未改动正式安装环境。

启动前须重定向 `APPDATA`、`LOCALAPPDATA` 和三个 `NEKO_STORAGE_*_ROOT`。
候选 `config/network.py` 导入时会读取 `APPDATA/N.E.K.O/port_config.json`；仅覆盖端口不能阻止该读取。
不要把任何个人配置、真实数据库或历史误采集文本复制到源码宿主。

现有启动选项 `NEKO_DO_NOT_TRACK=1` 阻止远程遥测，`NEKO_CLOUDSAVE_DISABLED=development_text_only` 禁用云存档。
源码的插件执行目录与状态目录分离：产品将 `PLUGIN_CONFIG_ROOT` 指向 `benchmarks/raw/neko-product-data/plugin-code`，历史 `<store>/plugins` 仅作状态；两者不重合。上游默认执行目录为 `.neko-plugin-installations/plugins`。
启动入口已为隔离数据准备 `<anchor>/state/storage_policy.json` 并设置 `first_run_completed=true`，解决仅环境变量不能完成首次选择的问题。

## 最终产品证据与边界

真实运行已完成源码宿主启动、原生 Study UI、指定测试窗口捕获、DeepSeek 连续教学与跨 Session/换课记忆流程。教学过程中发现并修复的技术错误、知识图误路由和 UI/评分问题，以及剩余质量限制，见[独立教学审查](neko-flutter-independent-review-2026-10-10.md)。完成验收流程不表示每条早期模型回答都正确。

- [真实教学 Transcript](evidence/flutter-product-transcript.md)与[JSON 原始记录](evidence/flutter-product-transcript.json)。
- [桌面 Tutor 可用界面](evidence/tutor-desktop-ready.png)与[授权窗口捕获](evidence/tutor-desktop-authorized-capture.png)。
- [真实重启/换课记忆记录](evidence/flutter-product-memory-runtime.json)。
- [证据目录](evidence/)保存三场 Provider 审计（时间后缀 `T120000Z`、`T123518Z`、`T124909Z`）与宿主运行报告。

最终宿主已退出：48911、48912、48915、48916 端口全部关闭，任务创建的窗口列表为空，浏览器 owner 文件已移除。全轮未进行实际声音或麦克风测试，未把可选语音功能列为已交付能力。最简单的启动方式与用户下一步体验见[明早交接](neko-v02-morning-handoff-2026-10-10.md)。
