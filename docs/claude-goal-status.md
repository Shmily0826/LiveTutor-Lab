# Claude Goal 状态

Goal：[claude-goal-2026-10-15](claude-goal-2026-10-15.md)（用户 2026-10-15 确认，无人值守）。旧 plan/status/blockers 不再逐阶段同步。

## 当前状态（2026-10-15，M1–M5 完成后的 W1–W5 续作，由 Sonnet 5.5 会话接手）

- M1–M5 已完成并复核（报告见 `evidence/claude-m1…m5…`）；本轮不重做。
- **W1 完成**：[报告](evidence/claude-w1-real-verification-2026-10-15.md)。`index_sync=unchanged` 且无 `source_retry_query`、文件清单缓存（558→29 ms）、停顿暂扣下三段 WAV 每段各 1 条识别（第三段原本 2 条）都有真实证据。
- **W2 完成**：[报告](evidence/claude-w2-source-question-kinds-2026-10-15.md)。5 类题型各拿到真实回答并对照源码；发现并修了 2 个缺陷（结构错嵌套、追问丢前面的文件）。
- **W3**：图片与指示回归——进行中/见下方历史。
- **W4 完成**：[报告](evidence/claude-w4-speakable-numbers-2026-10-15.md)。行号读法改在 payload `_speakable`；听感待用户。
- **W5**：验收彩排——未开始/见下方历史。
- 账本 `bargein-autocheck-20261012`：DeepSeek 1060/2000、Lanlan.app 94（本任务起点 968 / 90；上限 +150 / +20；已用 +92 / +4）。
- 等待用户：集中验收，见 [验收说明](claude-acceptance-guide.md)；需用户说"准备好了"后才开麦克风。

## 待 Opus 复核

1. **停顿暂扣 × 实验性自动评分链（宿主层，未动手）**。问题：`NEKO_PAUSE_HOLD=1` 与 phrase-input/speech-gate/auto-grade 同时开启时，第二段答案识别完成后宿主没有触发 `study_answer`（对照组暂扣关则有）；n=1。证据：`benchmarks/raw/evidence/claude-w1-voice-51rerun.json` 与 `…51nohold.json`，宿主日志 22:56:00 vs 23:00:04。拟议方案：只有在把自动评分链并进日常入口时才需要查；先在宿主里确认 `_take_study_grade_asr` 在暂扣延迟帧下是否错过窗口。风险：触碰 response arbiter/语音传输，故没有动。日常入口只开暂扣，产品路径（`…product-hold.json`）评分正常。
2. **`mode=explore` 对中文整句不可靠**（W1）。不是宿主问题；候选方案是在 `study_code` 工具说明里要求 explore 查询用英文标识符，或后端对含中文的 explore 查询抽取 ASCII 标识符。我没有做，因为角色实际会发什么查询没有 Native 证据，且 `mode=file` 路径不受影响。

## 决定记录

- 路由输入缩短只能省一部分时间；路由已与源码读取并发（M1 之后）。
- W1 的"新建 store"在复制授权文件之外还复制了 m5 store 的 `code_sync_state.json`，否则新 store 的第一次必然是完整同步，测不到 `unchanged`；指纹仍与现有目录比对。
- W4 放在 `_speakable`（角色拿到的副本），不改存库回复。
- 测试按模块独立进程运行；整套放同一进程会被隔离守卫串扰（见 W2 报告）。

## 历史（追加）

- 2026-10-15：W1/W2/W4 完成（见上）。
- 2026-10-15：M2/M3 发布 40264ab；M4 完成（宿主 31 文件可从 upstream + diff 重建）。
- 2026-10-15：M1 发布 f252506；M2/M3 实施并实测（撤回了两项无效尝试：提示词确认句、silence_duration_ms）。
- 2026-10-15：Goal 确认，开始 M1。
- 2026-10-15：Codex 收尾：补齐源码过滤与空结果重试计时；空回合自动补发经设计审查风险过高，仅交付说明。见 [收尾报告](evidence/codex-followup-gap-emptyturn-2026-10-15.md)。
- 2026-10-15：Codex 小修复：目录指纹未变时跳过空结果强制同步；离线52项通过，真实场计时由 W1 补上。见 [收尾报告](evidence/codex-resync-skip-2026-10-15.md)。
