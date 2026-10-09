# LiveTutor v0.2 第五轮：安全真实屏幕 + 可用桌面文字 Tutor（2026-10-09）

范围：闸门搬进产品、原生 UI 走通并给出最简本地使用路径、先本地确认捕获来源再做少量真实调用、安全收尾。
前四轮见 `neko-real-strong-tutor-2026-10-09.md`、`neko-real-tutor-ui-2026-10-09.md`、
`neko-desktop-tutor-2026-10-09.md`、`neko-host-tts-gate-plan-2026-10-09.md`。
源码改动与重建：`patches/neko-study-2026-10-09-target-window/README.md`。

## 结论先说

现在**真的**能做：

1. 一条命令启动一次性宿主（`DISABLE_TTS=true` + 代理 sink），宿主自带的 Study UI 在浏览器里可用；
2. 点名窗口采集在产品内部有 fail-closed 闸门，五种不符一律拒绝，不回退全屏、不回传文本；
3. 采集来源可以在**零像素、零调用**的情况下先被验证，然后才允许真实模型调用；
4. 真实 DeepSeek 连续文字教学（讲解→追问→出题→判分→针对错处重讲→会话总结）在宿主里跑通，无 degraded。

还**不能**说：桌面产品已经可用。三个缺口：Study UI 上那个采集按钮仍然只走 `interactive`
（用户手选区域），`target_window` 目前只能由入口/脚本调用，用户点不到；宿主音频出口仍然只有
配置级禁用，没有二进制级 fail-closed 闸门（阻塞项，标准见 gate-plan）；宿主路径每轮时延是隔离夹具的 3–5 倍，原因未定位。

## 一、真实屏幕采集：闸门在插件里，不在脚本里

`study_ocr_snapshot` 新增 `capture_mode="target_window"`，与 `window_title` / `expected_markers` /
`min_marker_matches` 配合。规则按“任何一点不符就拒绝”实现：

| 情况 | 结果 | 是否读像素 |
|---|---|---|
| 没给 `window_title` 或没给 `expected_markers` | `TARGET_WINDOW_REFUSED: expected_markers are required` | 否 |
| 标题找不到窗口 / 标题不是精确相等 | `TARGET_WINDOW_REFUSED: target_window_not_found` | 否 |
| 窗口存在但被别的窗口压住 | `TARGET_WINDOW_REFUSED: target_window_not_foreground` | 否 |
| 窗口几何不可用（含 `N.E.K.O` 自身界面） | `TARGET_WINDOW_REFUSED: target_window_geometry_unusable` | 否 |
| 抓帧后前台已经不是目标窗口 | `TARGET_WINDOW_REFUSED: target_lost_foreground` | 是，但文本不外传 |
| 抓到的内容没有预期文本 | `TARGET_WINDOW_CONTENT_MISMATCH: content_mismatch (0 of 3 …)` | 是，文本被丢弃 |
| 全部相符 | 成功，回传文本 + `capture_target_title` + `route` + `markers_matched` | 是 |

要点：`allow_fullscreen_fallback` 在本模式被强制 `False`，所以**不存在**“截不到就退成全桌面”这条路；
拒绝发生在 `build_ocr_payload` 与状态写入之前，因此既不会把文本回传，也不会污染 `last_ocr_text`
（离线用例显式断言了这两点）。上一轮那种“调用方自己过滤 foreign markers”的事后做法不再是唯一防线
——它保留为第二意见，但权威判定在产品代码里。

宿主是编译产物，只能用它的 `/runs` 协议验。真实结果（`model_calls: 0`）：
`PASS_HOST_TARGET_WINDOW_GATE` 4/4，见 `benchmarks/raw/evidence/neko-target-window-host-gate-20261009T100716Z.json`。
成功那一路：`capture_mode_used=target_window`、`capture_target_title="Synthetic Lesson Fixture (LiveTutor test)"`、
`route=pil_bbox_crop`、`markers_matched=5`、课文 5/5 行被识别、foreign markers 为空、176 字符。
三条拒绝路径 `carried_text` 全为 false，最快 31 ms 返回（还没截就已经拒了）。

另有一层不依赖宿主的验证：`scripts/neko_target_window_guard_check.py` 用真实 tkinter 窗口跑真实 Win32
解析函数，`PASS_TARGET_WINDOW_GUARD` 10/10，`pixels_captured: 0`——包括“另一个窗口压在上面时必须拒”
“前缀标题不算身份”“N.E.K.O 自己的界面不可为目标”“裁剪区域是主屏的真子集（90,70,583,371 ⊂ 1440×900）”。

离线回归：`python -I -S -B scripts/test_neko_lab_regressions.py` → 39/39 OK（含本轮新增用例）。
`-I -S` 是刻意的：这样 PIL 不可导入，测试进程不可能真的抓屏。

## 二、原生 UI 与最简本地路径

本轮修掉了 UI 驱动的一个竞态，并暴露出真实的首次运行体验：`#learningProfileModal`（选学段）在 load 之后
才被创建，旧驱动在它出现之前就判断“没有弹窗”，于是点击被覆盖层挡住而超时。新逻辑等它出现、按
`[data-stage="college"]` 选择、再按 computed style 判定关闭，同时兜住 `#memoryDeckDialog`
（“Skip and use default” / “Create and save”）。这属于产品自带的 onboarding，不是 bug；但用户第一次打开时
确实要先过这两层，文档按事实写在这里。

本地路径（PowerShell，仓库根目录）：

```powershell
# 1) 一次性宿主：禁用 TTS/voice/proactive，出口只允许 api.deepseek.com
python scripts/neko_desktop_tutor_host.py --hold 900 --seconds 200

# 2) 零调用冒烟：宿主 UI 能开、首次运行弹窗能过、Teaching 能选中
node scripts/neko_desktop_study_ui.mjs --up-to-mode

# 3) 真实文字闭环（3 次调用）：粘贴课文 → Explain → 追问 → 会话总结
node scripts/neko_desktop_study_ui.mjs

# 4) 只验采集来源（0 次调用），再跑完整目标窗口会话（约 10 次调用）
python scripts/neko_desktop_tutor_session.py --window --capture-only
python scripts/neko_desktop_tutor_session.py --window

# 5) 收尾
python scripts/neko_desktop_tutor_host.py --stop
```

手工使用路径就是第 1、3 步之间那段：打开宿主 → 浏览器进 `http://127.0.0.1:48916/plugin/study_companion/ui/`
→ 首次运行选学段（或 Skip）→ Teaching → 粘贴课本文本或点 OCR 手选区域 → Explain → 追问 → 展开面板做总结。

本轮实测时延（同一宿主、`thinking: disabled`、DeepSeek flash）：UI 首答 9.7 s / 追问 11.7 s / 总结 11.6 s；
目标窗口完整会话 6 次讲解 14.6–19.1 s、出题 5.2 s、判分 15.5 s、总结 13.5 s。比隔离夹具慢 3–5 倍，
原因未定位（宿主多一跳 HTTP 协议、插件锁、状态持久化都在嫌疑名单里）。UI 侧仍未做流式输出。

## 三、最小真实验收：顺序与账目

要求是“先本地确认捕获来源，再允许必要的少量真实 API 调用”。顺序照办了，但账目要如实记：

- 本地确认阶段：guard check 10/10（0 像素、0 调用）+ 宿主闸门 probe 4/4（0 调用）+
  修复后的 `--window --capture-only`（`neko-desktop-tutor-session-20261009T101632Z.json`：
  `model_calls: 0`、`capture_mode_used=target_window`、5/5 课文行、`plugin_gate_active_in_loaded_build: true`）。
- 真实调用：**13 次**。其中 10 次是我自己的 bug 造成的提前消费——`--capture-only` 的提前退出条件
  写反了（`stop_after_capture = not lesson`，采集成功时反而继续跑完整教学），完整会话在采集已经
  被判定可信之后照跑不误。修好之后重跑同一条命令，确实在采集处停止且 0 次调用（上面那个 artifact）。
  另外 3 次是 UI 文字闭环。
- 这 10 次跑出的东西本身是有效的验收证据（`neko-desktop-tutor-session-20261009T100026Z.json`）：
  采集闸门在 loaded build 里生效（`plugin_gate_active_in_loaded_build: true`，`markers_matched: 5`），
  课文 → 讲解 → 两次追问 → 出题 → 判一个典型错误答案（“你把 du 误写成 dx，漏掉了内层导数 2”）→
  结合错处重讲 → 中文小结（含“薄弱点：du=dx 漏掉内层导数 2”）→ 6 条互动落库，degraded 为空。
  那份报告由出 bug 的旧版本写出，里面 `"capture_only": true` 与 10 次调用同时出现，标签不可信，
  以本节的说明和 T101632Z 那份为准。

教学质量按案例本身判：u-substitution 的系数 1/2、`du=2dx`、错因定位都正确且没有硬编码；
总结仍会自造“例题”细节（上一轮已记为遗留），不构成本轮的通过条件。

## 四、安全收尾

- **监听进程**：`--stop` 之后 48911/48912/48915/48916 无 LISTENING（只剩系统侧 TIME_WAIT 残留），
  `Get-Process` 里没有任何 `projectneko` / `N.E.K.O` 进程。
- **旧 pid 文件**：`benchmarks/raw/neko-backend.pid`(40040)、`neko-shell.pid`(12700)、`neko.pid`(30492)
  指向的进程都已不存在，是更早几轮的残留；本轮没有产生的 `neko-desktop-host.pid` 已由 `--stop` 清掉。
  这三个文件不是我这次建的，所以只报告、不删除。
- **一次性数据**：`benchmarks/raw/neko-appdata`（gitignored，9.5 MB）里
  `N.E.K.O/config/core_config.json` 写有明文 DeepSeek key。要删随时可以，但我没有替你删——
  它同时是本轮宿主验收的可复现夹具。
- **个人配置未被改动**：真实 `%LOCALAPPDATA%\N.E.K.O\config\core_config.json`
  mtime 仍是 `2026-08-20T07:23:42Z`，只有 2 个键，`assistApi=free`，没有 `DISABLE_TTS`、
  没有 `agentModel*` 字段、没有任何 key 字段。宿主是靠重定向 `LOCALAPPDATA/APPDATA` 到一次性树里跑的
  （`NEKO_STORAGE_*` 三个变量并不能搬动 ConfigManager）。
- **网络边界**：两次宿主审计都是 `sink_allowed_hosts=["api.deepseek.com"]`、`sink_denied_hosts=[]`、
  `observed_external_connections=[]`（`neko-desktop-host-20261009T100617Z.json`、`…T101343Z.json`）。
  本轮没有再出现上一轮那些被拒的主机名，这只说明这次没观测到，不等于宿主永远不会试。
- **音频边界**：`DISABLE_TTS=true`、`ttsProvider=""`、`proactive=false`、`voice_wake_word=false`；
  浏览器 headless 且 `--mute-audio`；UI 驱动从未点击截屏/语音相关按钮；本轮没有启动麦克风、TTS、
  Native Realtime 或 Proactive。**但**二进制级 fail-closed 音频闸门仍然不存在，正式安装版宿主依旧不可
  用于 Study UI E2E，判定标准沿用 `neko-host-tts-gate-plan-2026-10-09.md`。
- **误采集的个人内容**：本轮没有读取、打印、上传或以任何形式再次使用此前误采集的文本；
  证据文件里对拒绝掉的采集只记 hash/字符数，不记原文。历史处置见第四轮文档。
- 没有 commit、没有 push、没有 reset；`patches/`、`scripts/`、`docs/` 的改动都留在工作区待你审。

## 五、下一步（按价值排序）

1. 把 `target_window` 接到 Study UI 的采集入口（capture-mode 选择 + 标题输入 + 预期文本来源），
   让闸门是**用户点得到**的，而不是脚本才有的。
2. 宿主音频出口的构建级 fail-closed 闸门（gate-plan 的 4 步），在那之前正式宿主继续 BLOCKED。
3. 定位宿主路径 3–5 倍时延，并给讲解加流式或“正在思考”的 UI 状态。
4. 总结仍会补造例题细节、session 跨重启累积不清理——都属于可用性而非安全性缺口。
5. UI 加载时控制台仍有一条 404 资源记录（不影响文字闭环，本轮未定位；空闲加载复现不到）。

## 六、最终复核（Final Review，同日）

### 源码与版本控制

`scripts/neko_plugin_source_coverage_check.py` → `PASS_SOURCE_COVERAGE`：

- 两个部署树（宿主真正 import 的 `plugins/study_companion/` 与回归套件读取的
  `plugin/plugins/study_companion/`）逐字节一致；每个模块都能 parse，且
  `entry_ocr_entries.py` 的类体存在（就是为上一轮那次误截断准备的检法）。
- 5 个被改过的模块（`entry_ocr_entries` / `entry_tutor_context_support` / `llm_prompts` /
  `prompt_templates` / `tutor_llm_agent_concept_explain`）全部能由
  「v02 快照 + `study.patch` → `goal-context.patch` → `ui-real-tutor.patch` →
  `target-window-capture.patch`」**逐字节重建**；`modified_uncovered = 0`，`rebuild_failed = 0`。
  顺带纠正 `neko-study-2026-10-09-ui/README.md` 里“`entry_tutor_context_support.py` 无法重建当前快照”
  的旧说法：按 goal-context → ui 的顺序可以重建。
- 另有 81 个模块是随冻结 app bundle 交付的、从未被补丁改过，也**不在 Git 内容里**（仓库不存 531 MB
  宿主与整份 bundle）。这类“没人看过但被覆盖/截断”的风险现在由
  `patches/neko-study-2026-10-09-final/plugin-tree-inventory.json`（104 + 103 个模块的字节数与 SHA-256）
  钉住：`python -I -S -B scripts/neko_plugin_source_coverage_check.py` 会立刻报漂移。

### 采集路径收紧（并说明证据边界）

窗口目标路线原来会“整屏抓一帧再裁”，现在改成只向 PIL 请求目标矩形
（`ImageGrab.grab(bbox=…)`）；打包运行时若拿不到 `ImageGrab.ScreenSize` 才退回原路线。
离线用例把这条性质钉住了（`grabs` 只能有 1 个且必须带 bbox）。39/39 离线回归仍全过。

宿主内的复验结果要如实分开讲：

- 两条**拒绝**路径依旧即时生效（31–47 ms，无文本外传）。
- “点名窗口 + 预期文本”的成功路径这次**没能**在宿主里重跑：桌面前台当时被用户自己的
  Chrome 窗口占着（探针把 `foreground_title` 记进了证据），闸门因此正确地拒绝了采集——
  这是设计要求的行为，我没有去抢用户焦点。所以成功路径的宿主级证据仍是本轮改动之前的
  `neko-target-window-host-gate-20261009T100716Z.json`（4/4，5/5 课文行）与
  `neko-desktop-tutor-session-20261009T101632Z.json`（capture-only，`model_calls: 0`）。
  bbox 改动后的成功路径，请按快速开始里的命令在前台属于那个窗口时自行复验一次。

### capture-only 的零调用约束

从“分支顺序碰巧正确”改成入口即成立：`--capture-only` 必须与 `--window` 同时给
（否则 argparse 直接报错），并且 `call()` 站点加了白名单——只允许
`study_status` 与 `study_ocr_snapshot`，任何其它入口在 capture-only 运行里会立刻抛错。
以后改动代码顺序也不可能再出现“本想零调用却跑了 10 次”的那种事故。

### 交付

- 一条命令：`python scripts/neko_tutor_start.py`（启动 → 打开 Study UI → 按 Enter 关闭并打印出口审计）。
- 使用说明：`docs/neko-tutor-quick-start.md`；仓库 README 顶部加了 Quick start 段落。
- 复核后状态：宿主内无残留监听（48911/48912/48915/48916 均无 LISTENING，无 neko 进程），
  用户真实配置仍未被写入（mtime 2026-08-20、2 个键、`assistApi: free`）。
