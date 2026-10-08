# MEMORY.md — LiveTutor-Lab / N.E.K.O Lab 长期要点

## N.E.K.O 沙箱启动配方（最重要，可复用）
- 从沙箱启动 `benchmarks/raw/neko-app/N.E.K.O.exe` 必须同时做三件事：剥除 `ELECTRON_RUN_AS_NODE`/`NODE_OPTIONS`、`USERPROFILE=C:\Users\Shmily`、加 `--no-sandbox`（否则 STATUS_BREAKPOINT 0x80000003，Job Object 连带杀 openfang+backend）。
- 必须用**常驻后台任务**托管：`scripts/neko_lab_hold.py`（干净 env + --no-sandbox + 退出自动重启）。普通命令行结束会回收整个进程树；ShellExecuteW 方案无效。
- 手动起的后端会被 owner_supervision（parent_handle）在启动器退出后带走；桌面端拉起的后端不受影响。
- 判定进程用 `name.lower().replace('.','')` 再匹配 "neko"（`N.E.K.O.exe` 含点）。
- 本机 HTTP 必须 `ProxyHandler({})`（沙箱代理会对 127.0.0.1 回 502）；`opener.open(req, timeout=…)` 必须关键字传参。
- 完整诊断链：`scripts/neko_lab_relaunch_{clean,trace,final}.py`；详细说明在 `docs/neko-handoff-2026-10-08-goal-wip.md` §7.5。

## Study 插件运行时启用顺序（冷启动后默认全关）
- 仅切 `user_plugin_enabled` 会被推迟（"deferred until the master switch is ON"）。
- 正确顺序：`POST 48915/agent/command {"command":"set_agent_enabled","enabled":true}` → `POST /agent/flags {"user_plugin_enabled":true}` → 48916 `/plugins` 出现 26 个插件。
- **用完必须还原**为两者 False（交接时状态）。

## Stage 2 结论（2026-10-09 定稿，覆盖早前误判）
- `capture_busy` 是**机制 1：标志卡住**，不是合法会话占用。证据：0 遮罩空置 120s 后请求仍 0.44s 返回 409（`goal-stage2-timing.json`）。
- 后端 bug 未修：409 同时桌面仍弹全屏遮罩；`_interactive_capture_active` 只置位不释放。属 Stage 4 正式源码集成范围。
- 插件侧已修（Stage 2.3）：`entry_ocr_entries.py` 回退白名单加 `capture_busy`，三个根同步（LIVE/BRIDGE/goal-isolated）；严格模式仍硬失败；回归 15/15；端到端 run `5ddf55da…` 验证降级生效。

## 红线（长期有效）
- 不 commit/push；不读/输出任何 API key；绝不用初始备份覆盖 DB（保护 33 interactions + 5 qa_records，id 24/29/33 在 `interactions` 表）；语音验收保持静音；重启前先证明 PID/路径归属。
- 用户限定 Stage 3 评分样本 6–8 个，不得扩量。
