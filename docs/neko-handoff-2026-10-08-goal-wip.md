# N.E.K.O 第二次交接：Study 真实链路与 awareness（2026-10-08）

用户要求收尾，由另一 agent 接手。目标尚未全部完成。本轮改动保留在本机工作树，**没有 commit/push**；GitHub 的 `65beaf6` 不包含本轮成果。先读本文，再读 `neko-goal-progress-2026-10-08.md` 和原 `neko-handoff-2026-10-08-eod.md`。

## 1. 任务与已授权边界

本轮验证真实 Study UI 的屏幕输入、解释、连续追问、出题、评分和记录；复现并修复 awareness 设置、循环与消息平面启动问题。

用户允许修改 Lab 文档、脚本、测试及直接相关的 Study/消息总线源码；有备份的可逆测试部署、配置调整、必要重启，以及操作 N.E.K.O 和本轮测试材料窗口。使用已有模型配置，**不读取、输出或传播 key**。不删除历史或学习记录，不替换整个安装包，不新增付费服务，不 commit/push。本轮静音、不启用现场麦克风；听感、真实语音和打断留给用户回来。

这些权限是当前会话的原指令记录。新 agent 开始前应核对用户是否继续沿用，而不是把文档本身当成新用户指令。

## 2. 已完成与证据边界

| 项目 | 结果 | 仍有的限制 |
| --- | --- | --- |
| 重要产品文档 | 已读教程、睡眠/猫形态、历史与记忆、Study onboarding 和 SDK/版本资料 | 候选源码与实际冻结宿主不能混用 |
| 真实 Study UI | 人工链式法则材料：全屏 OCR → 解释 → 连续追问 → 出题 → 错误/正确反馈 → 记录入库 | 单组材料；不是长期教学质量保证 |
| 连续追问 | 增加显式“沿用上一轮解释”，新样本保留上轮例题并正确求导 | 只附上一轮输入和解释，12k 字符上限；正常角色聊天另判 |
| 评分上下文 | 压力回归确认必要字段可能被压缩丢弃；保护题目、学生答案与参考答案，必要内容超预算拒绝评分 | 原坏分是否完全由此造成未证明；同题大样本未做 |
| Awareness 配置 | 公共设置解析、启动/停止、实际状态回读通过 | 验证后已恢复 disabled |
| 持续后台循环 | 宿主循环取消及跨循环队列问题得到运行证据；临时兼容层后持续 tick/capture | 冻结宿主临时兼容方式，未正式发布集成 |
| 消息平面/订阅 | 实际组件启动、订阅 active、retry false；主动桥接 forwarded 和主程序 delivery 提交有日志 | 最终角色 UI 与这条 awareness 消息的关联未验收 |
| 冷启动 | 完整后台重启后第一 Study 实例持续 12→13 ticks/captures，订阅恢复，结束后原配置恢复 | 分类为 other，不能证明正确识别学习材料 |
| 自动检查 | Python 14 项、两个 Node 检查脚本通过；桌面/移动浏览器控件检查通过 | 不代替实际桌面 UI 或真实语音 |

真实 UI 单次耗时：OCR 6.238s、解释 3.700s、追问 5.684s、出题 6.161s、错答反馈 7.648s、正确反馈 5.617s。数学公式正确；OCR 会混入 N.E.K.O 浮层，部分教学措辞仍不严谨，首轮 OCR 解释未应用知识图谱。

修复前真实 UI 将“答案是 42”判为 correct/100（数据库 id=24），掌握度也受影响。保留该记录。修复后新题错误 id=29 为 wrong/0，正确 id=33 为 correct/100，题目/作答 ID 不同。**不要恢复初始整个数据库**；那会抹掉后续记录。当前数据库含合成测试记录及掌握度影响。

## 3. 还没完成：推荐下一步

1. 核对当前桌面已解锁且可以交互。将正常角色从猫形态恢复；开启一个新 `respond` 样本，记录唯一关联信息，确认新主动消息最终显示到角色聊天 UI，再恢复原 awareness 分支。已有 forwarded 日志不能替代这一步。
2. 排查默认“选择区域”的 `capture_busy`。重启没有解决原现象。显式全屏选项已经取得真实成功样本；最新严格选区不自动全屏回退、模式元数据字段只有组件验证，需补实际 UI。
3. 在固定材料前台验证 awareness 观察分类；冷启动样本的 other 不算材料识别通过。默认 title_first 是轻量观察，ocr_text/both 为可选 OCR 路径；手动全屏 OCR 与 awareness 是不同入口。
4. 扩展同题评分、长上下文、不同材料和多轮追问，检查错误反馈、掌握度污染、知识图谱是否被实际使用。显式 practice scope 的 UI 操作未成功验收；已通过的是自动 Adaptive Practice 出题。
5. 将宿主循环/消息平面修复放入一致的正式源码构建并 review。当前编译包兼容 hook 不应直接视为发布方案。
6. 用户在场后再做麦克风/ASR/TTS、听感、打断和恢复。当前工作可保持静音。

本轮额外角色浏览器客户端出现 Send failed，随后关闭该测试页面，桌面 capture health 恢复。不因此直接判原桌面正常角色聊天失败。此前 47→150 的角色连续性 PASS 是上一 agent 的结果。20:12 的角色数学回复可能是 Study narration，不能当作 19:58 awareness 消息的确认。

最后阶段实际桌面曾不可交互、截图只有壁纸，且同会话观察到 LogonUI；后来一次进程查询未再出现 LogonUI。**当前是否锁屏需重新核对**，不要重复点击、解锁绕过或把激活失败解释成产品故障。

## 4. 版本、当前部署与运行入口

- 工作区：`D:\CODE\project\LiveTutor-Lab`；Lab 基线 `65beaf6b3e4049b6c71c4fa3cbd4353c44e50164`。
- 候选源码 `candidates/N.E.K.O`：`1d814cf32fba8c02b5727d2890710e4e7b8ece24`，最后检查工作树干净。
- 实际桌面包 0.9.0 / Electron 41；Study 与 SDK 0.1.0。
- 实际后台：`benchmarks/raw/neko-app/resources/bin/projectneko_server.exe`，Nuitka Python 3.11 冻结程序。SHA256 `BE32BD8555EFE6450F01191DB4FAB41D4C25B6C14C8C52C44B1F645086AF6288`，未替换。
- 主服务 48911、memory 48912、plugin 48916；材料 HTTP 48930。都是本机测试入口。
- 当前后台最后 PID 3812，桌面 PID 21432。**PID 会变化，重启/停止前重新证明监听者与路径归属**。
- 存储根 `benchmarks/raw/neko-store`；后台启动环境明确指定 NEKO_STORAGE_SELECTED_ROOT、NEKO_STORAGE_ANCHOR_ROOT、NEKO_STORAGE_CLOUDSAVE_ROOT；不要启动到另一个用户数据库。

当前源码入口：

```text
LIVE:   benchmarks/raw/neko-app/resources/bin/plugin/plugins/study_companion
BRIDGE: benchmarks/raw/neko-app/resources/bin/plugins/study_companion
ENTRY:  plugins.study_companion.lab_bootstrap_plane:StudyCompanionPlugin
ORIGINAL ENTRY: plugin.plugins.study_companion:StudyCompanionPlugin
```

冻结默认入口不执行旁置修改，故使用显式源码入口及两个 import 根。`lab_bootstrap_plane.py` 安装 Study 循环兼容层和父进程 delivery 启动 hook；helper 来自 `scripts/neko_lab_runtime_loop.py` 与 `neko_lab_runtime_plane.py`。其他 plugin ID 的调用委托原路径。冷启动时首次导入也安装循环兼容层。

原始 exe 未变；宿主源码 `host-loop.patch` **没有编译进当前 exe**。当前 plane hook 是实验性的补启动路径，不能冒充完整健康重建框架。后续需要正式集成与消息平面断开后的更广运行验证。

收尾状态：Study ready、awareness enabled=false/runtime inactive；communication subscription/worker active，retry=false。保留修复供下一 agent 接手，不主动回滚有效测试部署。后台/桌面/材料服务仍运行；本轮 Chrome `neko-lab` 与 `neko-goal-final` 只含任务页面，不操作用户其他标签。

## 5. 文件、备份与复现

可共享：README、本文、progress 文档、`patches/neko-study-2026-10-08/`、本轮 `scripts/neko_lab_*.py`/测试，以及 `benchmarks/materials/study-chain-rule.html`。全部本地未提交。原始截图、日志、数据、隔离源和安装包在 ignored `benchmarks/raw/`；只克隆 GitHub 不会得到这些文件。

本机隔离 Python：

```powershell
$labPy = 'D:\CODE\project\LiveTutor-Lab\benchmarks\raw\goal-python\cpython-3.11.15-windows-x86_64-none\python.exe'
& $labPy scripts/neko_lab_client.py
& $labPy scripts/test_neko_lab_regressions.py
node scripts/test_neko_lab_followup.js
node scripts/test_neko_lab_ocr_ui.js
& $labPy scripts/neko_lab_verify_records.py
git diff --check
```

缺依赖时先读测试文件及 `benchmarks/raw/goal-source-libs` 的隔离配置；不要读取应用配置找 key。`neko_lab_client.py` 默认只输出筛选后的状态；可调用插件 entry，但不得扩展成凭据读取工具。

真实 UI helper：`neko_lab_ui_step.py`。`ocr --fullscreen` 为明确全屏；`explain --current-input` 使用当前 OCR 输入。必须先核对 Windows 前台固定材料和实际画面；浏览器 bringToFront 不能保证原生窗口前台。对本地 UI 使用共享 `node D:\AI\tools\web-inspector\cli.mjs <target>`；需要浏览器控制用共享 wrapper，不在项目安装 Playwright。桌面原生工具应遵循 computer-use skill 的 @oai/sky API。

可逆 awareness 运行样本：`neko_lab_live_awareness.py` 默认 read，`--mode respond` 会发真实主动消息，finally 恢复原 awareness 分支。已有证据文件可能被重跑覆盖，应先复制到新文件名。`neko_lab_cold_prepare.py`/cold_verify.py 是一次性有顺序的冷启动测试，已完成，不直接重跑旧 prepare。

以下主要是探索脚本，**不要批量执行**：stage、clean_probe、diagnostic_plugin、install_probe、source_entry、sync_probe、plane_probe、awareness_observe。stage 还提供其他脚本 import 的路径常量，不能直接删除。loop_probe 依赖已留下的 clean probe manifest。多个 study_lab_probe* 测试目录/插件仍在 ignored 原始环境中，已停止；清理前核对精确归属和依赖，不删除用户插件。

备份在 `benchmarks/raw/evidence/goal-backups/`：

- `source-deployment/`：原始 Python 文件、plugin.toml 与哈希。
- `ui-followup/`：五个原始 UI/i18n 文件及 original/applied 哈希。
- 根目录：原始配置、初始整个数据库和更早源码备份；数据库仅用于取证，不覆盖恢复。

回滚 UI：`neko_lab_deploy_ui.py --rollback`（校验 applied hash，拒绝覆盖外部修改，随后重载 Study 页）。源码回滚：`neko_lab_deploy_source.py --rollback`，然后重启已确认归属的后台以移除内存 hook，恢复原冻结入口。**源码回滚脚本没有外部修改哈希保护，执行前人工比较当前文件并另备份**。它恢复 LIVE 原文件/manifest；残留 BRIDGE/helpers 不自动删除，先确认原入口加载原代码再考虑清理。两种回滚独立，不修改数据库。

## 6. 原始证据索引（本机，ignored）

所有相对路径基于 `benchmarks/raw/evidence/`：

| 证据 | 用途 |
| --- | --- |
| goal-ui-ocr/explain/followup/question/wrong/correct.txt | 上表实际 UI 的单次结果与耗时 |
| goal-wrong-42-graded-100.png、goal-wrong-evaluation-request.json | 修复前错误答案被判 100 的真实证据 |
| goal-persisted-grading-records.json | 只读核对 id24/29/33 |
| goal-awareness-baseline.json | 原 39 秒 sensor false 的配置复现 |
| goal-background-lifecycle.json | 后台任务约 15ms 被取消 |
| goal-plane-capabilities-40008.json | 冻结宿主没有 message_plane_runner |
| goal-awareness-fixed-read.json / goal-awareness-fixed-respond.json | 修复后的实际观察与主动提交 |
| goal-cold-first-status.json / goal-cold-verification.json | 第一冷启动实例、持续计数与恢复原配置 |
| backend-goal-cold.stdout.log / .stderr.log | 当前后台日志；更多桥接日志在 neko-store/logs |

旧 HTTP `/plugin/messages` 的零数量只标为 legacy_api_message_count，不等于实际消息平面未投递。配置存在、源码存在、submitted/forwarded 和最终用户可见回复分别判定。

接手后优先补最终角色 UI 关联及区域截图；无需先开音量或现场麦克风。用户配合主要是维持电脑开机/解锁，并在后续语音验收时在场。

## 7. 第三次接手补充（2026-10-09 凌晨，自包含）

接手人续跑 Stage 1–2。以下结论覆盖上文对应条目；数据与 git 均未改动（仍是 `65beaf6`，零 commit；DB interactions=33、qa_records=5 与交接时一致）。

### 7.1 Stage 1 已关闭：awareness 消息确认显示到角色 UI

`neko_lab_stage1_correlate.py` 在 `agent_callback_turn` 计数增加的前后各抓一张 1:1 面板帧：`had_input=False agent_callback_turn=True`（排除用户输入驱动）；22:42:14 帧出现选项「切回来了 / 好啦好啦 / 窗口像个小星球」，22:42:35 帧出现「好，我切回来了，正在写 cos·ln x…」。对照组：`goodbye_silent=True` 时 callback_enter/turn 均为 0。证据：`goal-stage1-correlate.json`、`goal-stage1-live-acceptance.json`。

### 7.2 Stage 2 结论更正：机制 1（标志卡住），不是“合法会话占用”

上一轮“屏幕上有真实遮罩所以 409 合理”的判断**是错的**。关键实验（`neko_lab_stage2_timing.py`）：确保 0 个遮罩后空置 120 秒，再发一条交互式截图请求，**0.44 秒**内即返回 409 `capture_busy`。

**结论表述（2026-10-09 依 peer review 降级）**：以上证据（立即拒绝 + 无遮罩 + 长时间空置）使**机制 1（标志置位后不释放）成为最强假设，但尚不足以独立坐实**：
- `goal-stage2-sequence.json` 实况是 round1/round3 before=0 遮罩、round2/final 各含 **1 个轮间残遮罩**（上一轮 409 请求弹出的副产物，非活跃会话证据），并非“三轮均为 0”。
- “标志永不释放”的论断读自**候选源码** `candidates/N.E.K.O/utils/capture_bridge.py`（只在 `request_capture_region` 置 True、仅由 `_release_interactive_capture` 按 token 清除）；实际运行的是**冻结的 projectneko_server.exe**，两者不能划等号——冻结版可能存在候选源码中没有的持有/超时路径。待运行时探针确认冻结版标志生命周期。

插件侧规避补丁（§7.3）不依赖该定性，不受影响。证据：`goal-stage2-timing.json`、`goal-stage2-sequence.json`、`goal-stage2-confirm.json`。

后端侧附带观察（**未修复**，属 Stage 4 正式源码集成范围）：
- 请求被 409 拒绝的同时，桌面端仍会弹出全屏遮罩（多个实验里“409 且 overlay 出现”）；遮罩打开后无人操作会进入 45 秒 retention，叠加新请求使 busy 看起来永久化。
- 逐请求计时显示 409 是“入口即拒”，不是 504 渲染超时；`/api/capture/health` 始终正常。

### 7.3 Stage 2.3 已完成：`capture_busy` 加入全屏回退白名单（三个根同步）

`entry_ocr_entries.py` 的回退白名单由 `{no_renderer, main_server_unavailable, interactive_unavailable}` 扩为**再加 `capture_busy`**。严格模式（`allow_fullscreen_fallback=false`）保持硬失败不变。同步写入三个导入根（已 `diff` 校验一致）：
LIVE `benchmarks/raw/neko-app/resources/bin/plugin/plugins/study_companion`、BRIDGE `.../bin/plugins/study_companion`、测试源 `benchmarks/raw/goal-isolated/study_companion`。

回归：`scripts/test_neko_lab_regressions.py` 新增 `test_capture_busy_falls_back_only_when_allowed`，**15/15 通过**（原 14 项无回归）。

### 7.4 端到端验收：回退分支在真实插件进程内生效

通过 48916 真实提交 `study_ocr_snapshot(capture_mode="interactive")`：run `5ddf55da…` succeeded，`capture_mode_used="fullscreen"`、`interactive_fallback_reason="capture_busy"`、OCR 28.8s。原先该场景直接 Err，现按设计降级。证据：`goal-stage2-fallback-verify.json`。脚本 `neko_lab_stage2_verify.py` 自带遮罩看护线程（每秒轮询并取消 `N.E.K.O Screenshot` 遮罩），不会把用户屏幕留在阻塞状态。

**插件启用前置条件**（本次踩坑记录）：冷启动后 `user_plugin_enabled` 为 False，且仅切换它会被推迟（日志 “UserPlugin enable deferred until the master switch is ON”）。正确顺序：`POST /agent/command {"command":"set_agent_enabled","enabled":true}`（总开关）→ 再 `POST /agent/flags {"user_plugin_enabled":true}`；用完必须还原（本轮已还原为两者 False，`/plugins` 回到 0）。

### 7.5 N.E.K.O 无法从沙箱重启的根因与可复用启动配方（重要运维知识）

此前“桌面 rc=0 退出、零日志”耗掉大量排查，最终是**两个独立原因**，都已复现并解决：
1. 沙箱环境导出 `ELECTRON_RUN_AS_NODE=1` 与 `NODE_OPTIONS=--require …shim.cjs`，子进程继承后 `N.E.K.O.exe` 退化为纯 Node：rc=0、约 5 秒退出、不写任何日志。启动前必须从 env 删除这两个变量（另将 `USERPROFILE` 指回 `C:\Users\Shmily`，沙箱默认污染为 `D:\AI\WB-Profile-B`）。
2. Chromium 沙箱在本沙箱受限令牌下初始化失败，浏览器进程在拉起后端约 1.5 秒后以 `STATUS_BREAKPOINT`（0x80000003）硬崩（注意不是 0xC0000135/DLL），Job Object 连带回收 openfang 与 projectneko_server。加 `--no-sandbox` 后完全正常，四个端口 19 秒内全部就绪。

可复用配方：`scripts/neko_lab_relaunch_final.py`（诊断链）与 `scripts/neko_lab_hold.py`（常驻托管：干净 env + `--no-sandbox` 启动并守护，退出自动重启）。**hold 进程必须以后台任务方式常驻**——普通命令行结束会连带回收整个进程树；ShellExecuteW 方案实测无效（explorer 侧未收到参数）。当前桌面即由 hold 任务托管运行中。

另：进程名过滤注意 `N.E.K.O.exe` 小写含点（`n.e.k.o`），按子串 "neko" 匹配会漏报，需先 `replace('.','')`。沙箱内 `urllib` 默认走代理（会对 127.0.0.1 返回 502），本机请求必须 `ProxyHandler({})`；`opener.open(req, timeout)` 位置参数会被当成 `data`（int body 报错），必须写 `timeout=`。

### 7.6 剩余缺口（更新后的“还没完成”）

1. 后端侧 `_interactive_capture_active` 卡死 + “409 仍开遮罩”未修，需 Stage 4 决策后进正式源码（见 7.2）。
2. Stage 3 评分样本（6–8，用户已限定不扩量）——需在插件运行时开启的状态下采集，快照 DB 前后对比。
3. Stage 4 三项决策：集成范围（study.patch / + host-loop.patch / 不集成）、目标基线、冻结二进制处理。
4. Stage 5 真实语音/听感/打断，需用户在场。
5. commit/push 仍为红线，等待明确指令。

