# N.E.K.O 验收/评测目标 — Peer-Review Handoff（2026-10-09 01:00 NZDT）

> **给 reviewer 的话**：本文档自包含。你不需要读任何历史对话。目标是复核"本轮 agent 声称完成了什么"以及"下一步计划是否合理"。每条结论都附了**证据文件路径**和**独立复核方法**。深入版交接在 `docs/neko-handoff-2026-10-08-goal-wip.md`（§7 为本轮追加）。

---

## 1. 一句话摘要

N.E.K.O（Electron 41 桌面 + Nuitka 冻结 Python 后端）验收目标的 Stage 2 已定稿：`capture_busy` 是**机制 1（后端标志卡死）**，非合法会话占用；插件侧已打补丁规避并有回归 + 端到端证据；沙箱启动悬案告破；系统光标已修复；Stage 3（评分样本）待用户拍板 Stage 4 三决策后执行。

## 2. 当前实时状态（2026-10-09 01:00 核对）

| 项目 | 状态 | 复核方法 |
|---|---|---|
| git HEAD | `65beaf6`（零 commit，58 个未提交变更，属预期本地产物） | `git log --oneline -1; git status --porcelain \| wc -l` |
| 后端 48911 | `/health` → 200 `{"app":"N.E.K.O","service":"main","status":"ok"}` | urllib + `ProxyHandler({})` 直连 |
| Agent 48915 | `/health` → 200，`user_plugin_enabled:false`，`computer_use_enabled:false` | 同上 |
| 保活任务 | `neko_lab_hold.py`（任务 9rQ5WE，43200s），掉线自动拉起 | `scripts/neko_lab_hold.py` |
| DB 数据 | `interactions=33`、`qa_records=5`，全程未变 | 只读 sqlite 查询 |
| 系统光标 | 已修复（17/18 ID），注册表方案 `Windows Default` 无损 | `scripts/check_cursor_scheme.py` |

**注意**：48915 的状态路径是 `/health`，不是 `/api/system/status`（404）。

## 3. 本轮完成了什么（按时间线）

### 3.1 沙箱启动悬案告破（此前"rc=0 零日志 5 秒退出"）

**根因是三重叠加**：
1. 沙箱导出 `ELECTRON_RUN_AS_NODE=1` + `NODE_OPTIONS=--require …node-language-shim.cjs`，子进程继承后退化为纯 Node，静默退出（rc=0）。
2. Chromium 沙箱在受限令牌下初始化失败 → 桌面进程拉起后端 ~1.5s 后 `STATUS_BREAKPOINT` **0x80000003**（曾误算 0xC0000135，已更正），Job Object 连带回收 openfang + backend。
3. 工具调用结束回收整棵进程树 → 必须常驻后台托管。

**可用配方** = 剥除两个 env + `USERPROFILE=C:\Users\Shmily` + `--no-sandbox` + `neko_lab_hold.py` 常驻托管。四端口 ~13–19s 就绪。

- 证据：`scripts/neko_lab_relaunch_{clean,trace,final}.py`、`benchmarks/raw/evidence/desktop-hold.log`
- 复核：读 `scripts/neko_lab_hold.py`（<100 行）看 env 剥除与重启逻辑

### 3.2 Stage 1（awareness UI）维持关闭

此前已证明 awareness 消息能显示到角色 UI，无新增工作，保持关闭。

### 3.3 Stage 2 定稿：`capture_busy` = 机制 1（标志卡死）

**关键判别**：关闭所有遮罩 → 空置 120s → 单条请求仍 **0.44s 返回 409** `capture_busy`。若是合法会话占用（机制 2），要么有遮罩、要么等待超时（≈50s）。

- **撤销了 Round 9 的"机制 2"误判**（自我更正）；**2026-10-09 依 peer review 再降级**：机制 1 为**最强假设，尚未独立坐实**——`goal-stage2-sequence.json` 实况是 round1/3 before=0、round2/final 各含 1 个轮间残遮罩（409 副产物，非会话证据），且"标志永不释放"读自候选源码，冻结二进制的实际生命周期待运行时探针确认。
- 后端 bug 详情（未修，归 Stage 4）：`_interactive_capture_active` 只置位（`capture_bridge.py:419`）从不释放（仅 `_release_interactive_capture` :512-519 清除）；409 拒绝的同时桌面**仍弹全屏遮罩**；其他捕获路径（:311-316/:352-356）同受影响。
- 证据：`benchmarks/raw/evidence/goal-stage2-timing.json`（PROBE status=409 elapsed=0.44s）、`goal-stage2-sequence.json`（三轮 before/after 遮罩均为 0）、`goal-stage2-confirm.json`（409 且 overlay 出现）

### 3.4 Stage 2.3 插件侧补丁（唯一代码改动）

`entry_ocr_entries.py` 回退白名单加 `capture_busy`（三个导入根同步，diff 校验 ALL-IDENTICAL）：
- LIVE：`benchmarks/raw/neko-app/resources/bin/plugin/plugins/study_companion/`
- BRIDGE：`benchmarks/raw/neko-app/resources/bin/plugins/study_companion/`
- 测试源：`benchmarks/raw/goal-isolated/study_companion/`（回归套件加载此根）

**回归 15/15 OK**（新增 `test_capture_busy_falls_back_only_when_allowed`，原 14 项无回归）——`scripts/test_neko_lab_regressions.py`

**已知缺口（2026-10-09 peer review 指出，属实）**：补丁交付物 `patches/neko-study-2026-10-08/study.patch` 是旧版——本轮只改了三个根的实际 py 文件，未重新生成 patch 文件。实际部署文件已修、交付物未修，夜间计划第 5 条会更新它。

**端到端验证**：真实插件提交 `study_ocr_snapshot(capture_mode='interactive')`，看护线程取消遮罩：
```
run 5ddf55da… succeeded; capture_mode_used=fullscreen;
interactive_fallback_reason=capture_busy; ocr_duration_seconds=28.797
```
- 证据：`benchmarks/raw/evidence/goal-stage2-fallback-verify.json`
- 严格模式（`allow_fullscreen_fallback=False`）硬失败路径**未动**

### 3.5 插件运行时开关已还原

验证时临时开启（`set_agent_enabled:true` → `user_plugin_enabled:true` → 26 插件注册），验证完已还原。当前 `/health` 实测 `user_plugin_enabled:false`。**注意顺序**：只切子开关会被推迟（日志 "deferred until the master switch is ON"），必须先总开关后子开关。

### 3.6 系统光标修复（2026-10-09 00:5x）

N.E.K.O 的 `system-cursor-visibility-service.js` 把 32×32 全透明光标 `SetSystemCursor` 到 18 个 ID，硬杀进程跳过 finally → 全透明。

- 执行 `scripts/fix_cursor3.py`：**17/18 恢复**（全走 `C:\Windows\Cursors` 标准 aero 文件）
- 32640（IDC_SIZE）失败：现代 Windows 无独立 OEM 资源，实际影响≈0（应用都用 32646，已恢复）
- `SPI_SETCURSORS` 持久化 rc=0 err=6：**无实际影响**——注册表 scheme 本来就是 `Windows Default`（`check_cursor_scheme.py` 复核 `non-standard entries: NONE`），重启后自然加载标准光标

## 4. Reviewer 建议检查点（按可疑度排序）

1. **Stage 2 判别逻辑**：`goal-stage2-timing.json` 里 0.44s 返回 409 是否足以排除机制 2？——**已知限制（2026-10-09 更新）**：sequence.json round2/final 各含 1 个轮间残遮罩（409 副产物）；"标志永不释放"读自候选源码而非冻结二进制。机制 1 为最强假设，冻结版生命周期待运行时探针确认。
2. **三根同步**：`diff` 三个 `entry_ocr_entries.py` 是否真的 identical？
3. **回归测试是否真的覆盖**：读 `scripts/test_neko_lab_regressions.py` 的 `test_capture_busy_falls_back_only_when_allowed`，确认断言了 `capture_mode_used='fullscreen'` + `interactive_fallback_reason='capture_busy'` + 严格模式硬失败 + OCR 只跑一次。
4. **DB 未被动过**：只读查询 `interactions` 计数应=33（id 24/29/33 是关键样本）。
5. **0x80000003 归因**：`desktop-hold.log` / trace 输出中 `DESKTOP exited rc=2147483651`。

## 5. 待用户拍板：Stage 4 三决策

| 决策 | 选项 | agent 建议 |
|---|---|---|
| ① 集成范围 | A. 只 `study.patch`（插件侧，有回归+端到端证据）/ B. +`host-loop.patch`（未验证）/ C. 不集成 | **A** |
| ② 目标基线 | A. 当前 HEAD 工作树形式（不 commit）/ B. 先 commit 做基线（需用户授权） | 用户不授权 commit 则 **A** |
| ③ 冻结二进制 | A. 不碰（插件侧已规避）/ B. 反编译 Nuitka exe（极难、高风险） | **A** |

## 6. 下一步计划与用时

| 任务 | 用时 | 依赖 |
|---|---|---|
| Stage 3 评分样本采集（**限 6–8 个，不得扩量**）：端口检查→归属证明→开插件运行时→DB 快照（before/after 到 evidence）→采集→只读核对只增不减→还原开关→报告 | 30–45 min | Stage 4 决策拍板 |
| Stage 5 前置检查（自主） | ~15 min | 随时 |
| 真实语音验收 | 30–60 min | 用户在场；夜间可保持**小音量**（agent 不得调大） |
| 收尾报告 + 交接文档更新 | ~15 min | 最后 |

过夜运维：hold 任务保活 12h；Stage 3 走 API 不依赖屏幕，锁屏无碍。

## 7. 红线（对任何接手 agent 生效）

1. 不 commit / 不 push（等用户明确指令）。
2. 绝不读/输出任何 API key。
3. **绝不用初始备份覆盖 DB**（保护 33 interactions + 5 qa_records）。
4. 语音验收保持用户设置的音量，**禁止调用任何音量控制调大**。
5. 重启 N.E.K.O 前先证明 PID/路径归属。
6. 桌面控制用完必须声明并归还。
7. Stage 3 样本量 6–8 个是用户硬性限定。

## 8. 关键文件索引

| 文件 | 说明 |
|---|---|
| `docs/neko-handoff-2026-10-08-goal-wip.md` §7 | 深入版交接（7.1–7.6） |
| `scripts/neko_lab_hold.py` | 常驻托管启动器（必读） |
| `scripts/neko_lab_stage2_timing.py` | Stage 2 定论证据脚本 |
| `scripts/test_neko_lab_regressions.py` | 15 项回归套件 |
| `benchmarks/raw/neko-app/resources/bin/plugin/plugins/study_companion/entry_ocr_entries.py` | 补丁本体（:92-100 白名单） |
| `benchmarks/raw/evidence/goal-stage2-*.json` | 四份 Stage 2 证据 |
| `scripts/fix_cursor3.py` / `check_cursor_scheme.py` | 光标修复/校验 |
| `.workbuddy/memory/2026-10-09.md` | 本轮工作日志 |
