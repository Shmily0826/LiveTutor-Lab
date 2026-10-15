# Claude Goal 状态

Goal：[claude-goal-2026-10-15](claude-goal-2026-10-15.md)（用户 2026-10-15 确认，无人值守）。旧 plan/status/blockers 不再逐阶段同步。

## 当前状态（2026-10-15，M1–M5 完成后的 W1–W5 续作，由 Sonnet 5.5 会话完成）

- M1–M5 已完成并复核（报告见 `evidence/claude-m1…m5…`）；本轮不重做。
- **W1**：[报告](evidence/claude-w1-real-verification-2026-10-15.md)。`unchanged` 跳过同步且无重查、文件清单缓存（558→29 ms）、停顿暂扣下三段 WAV 每段 1 条识别（第三段原本 2 条）。
- **W2**：[报告](evidence/claude-w2-source-question-kinds-2026-10-15.md)。5 类题型各拿到真实回答并对照源码；修了 2 个缺陷（结构错嵌套、追问丢前面的文件）。
- **W3**：[报告](evidence/claude-w3-picture-pointing-regression-2026-10-15.md)。材料窗口 DOM 指示/换图 40 项通过；语音换图：旧语音停止、第二段用新图，9 项候选检查通过。角色自主指示未观测到。
- **W4**：[报告](evidence/claude-w4-speakable-numbers-2026-10-15.md)。行号读法改在 payload `_speakable`；听感待用户。
- **W5**：[报告](evidence/claude-w5-acceptance-rehearsal-2026-10-15.md)。发现并修复第 4 步的真实缺陷（语音路径把 `code_requests` 发成字符串，调用被拒）；修复后只有文字端验证。验收说明已更新期望与已知限制。
- 离线：103 个测试模块逐个独立进程运行，96 个通过；7 个未通过都是宿主补丁夹具/就绪检查，与本轮改动无关（见下）。
- 账本 `bargein-autocheck-20261012`：DeepSeek 1116/2000、Lanlan.app 100（本任务起点 968 / 90；上限 +150 / +20；已用 +148 / +10，**DeepSeek 额度用尽**）。
- **结论：可以请用户做集中验收**——见文末结论。需用户说"准备好了"后才开麦克风；本会话没有开过麦克风、采集、回环，没有改系统音量，没有动 `daily-companion-audio-policy.json`。

## 待 Opus 复核

1. **停顿暂扣 × 实验性自动评分链（宿主层，未动手）**。`NEKO_PAUSE_HOLD=1` 与 phrase-input/speech-gate/auto-grade 同时开启时，第二段答案识别后宿主没有触发 `study_answer`（暂扣关则有）；n=1。证据：`benchmarks/raw/evidence/claude-w1-voice-51rerun.json` / `…51nohold.json`，宿主日志 22:56:00 与 23:00:04。日常入口两者都不启用，产品路径（`…product-hold.json`）评分正常，故不阻塞验收；若要把自动评分链并进日常入口，先查 `_take_study_grade_asr` 在暂扣延迟帧下是否错过窗口。风险：触碰 response arbiter/语音传输。
2. **7 个过期的宿主测试夹具**：`test_neko_first_asr_ordering`、`late_asr_tool_patch`、`study_singleflight`、`study_speech_gate`（"unknown edited late-ASR helper"）、`material_audio`（"unknown material patch fixture anchor"）、`tool_result_lifecycle`（替换锚点不唯一）、`autocheck_readiness`（app 预算 `None`）。我没有改宿主；这些夹具对着已叠加了 M2/M3 补丁的宿主文件匹配旧补丁。建议 Opus 判断是更新夹具还是放弃这些旧测试。
3. **模型把 `code_requests` 发成字符串**（payload 层，已修）。我选择"文件名样式的字符串读成文件窗口、自由文本丢弃并回退到刚才读的窗口"，而不是更宽松的解释。请 Opus 复核这个取舍，以及是否还应该把工具说明里 `code_requests` 的示例写得更像对象（改 Native 工具 schema 触碰宿主侧缓存，我没有动）。
4. **`mode=explore` 对中文整句不可靠**（W1）。候选：工具说明要求英文标识符，或后端对含中文的 explore 抽取 ASCII 标识符。没有 Native 证据说明角色会发什么，没做。
5. **provider 在 < 0.4 s 的停顿处仍拆出两条识别事件**（W3 第二场、W5 第 4 步各一次）。这两次都只发出一次工具调用、只有一个回答；但原场 51 的"第二半句识别晚于回答开始"没有再出现，也没有排除。
6. **第 4 步语音端到端修复后未验证**（预算用尽）。这是我最不确定的一项。

## 决定记录

- 路由输入缩短只能省一部分时间；路由已与源码读取并发（M1 之后）。
- W1 的"新建 store"在复制授权文件之外还复制了 m5 store 的 `code_sync_state.json`，否则新 store 的第一次必然是完整同步，测不到 `unchanged`；指纹仍与现有目录比对。
- W4 放在 `_speakable`（角色拿到的副本），不改存库回复，Study 面板引用保持原样。
- 回归口径：每个测试模块一个进程（整套同进程会被隔离守卫串扰）。
- 追问窗口复用：`code_question` 行带本次调用 id，同一次调用的窗口一起取回；旧行保持原行为。

## 历史（追加）

- 2026-10-15：第 4 步语音复核（用户授权约 20 次，实用 15 次）：字符串修复在语音中生效；发现并修正"假设改动当成查找"的教师错误（文字场验证正确）；第二场语音遇 provider 空回合，提示正常。见 [复核报告](evidence/claude-step4-voice-verify-2026-10-15.md)。账本 DeepSeek 1131/2000、Lanlan.app 102。

- 2026-10-15：W1–W5 完成（见上）。发布：W1 df8f5da、W2/W4 02ac085、W3/W5 2827984。
- 2026-10-15：M2/M3 发布 40264ab；M4 完成（宿主 31 文件可从 upstream + diff 重建）。
- 2026-10-15：M1 发布 f252506；M2/M3 实施并实测（撤回了两项无效尝试：提示词确认句、silence_duration_ms）。
- 2026-10-15：Goal 确认，开始 M1。
- 2026-10-15：Codex 收尾：补齐源码过滤与空结果重试计时；空回合自动补发经设计审查风险过高，仅交付说明。见 [收尾报告](evidence/codex-followup-gap-emptyturn-2026-10-15.md)。
- 2026-10-15：Codex 小修复：目录指纹未变时跳过空结果强制同步；离线52项通过，真实场计时由 W1 补上。见 [收尾报告](evidence/codex-resync-skip-2026-10-15.md)。

## 结论：是否可以请用户验收（W1–W5 之后）

**可以请用户做一次集中验收，但请把第 4 步当作重点。**

- **通过了什么**（均不是可听/真人）：停顿暂扣在产品路径下每段一条识别；源码讲解 5 类题型对照源码答对（修了两个缺陷）；`unchanged` 跳过同步与清单缓存有真实计时；出题→答错→纠正→记录在 SQLite 里追加且不丢原错答；换图后旧语音停止、第二段用新图；材料窗口 DOM 指示/换图/重开通过；行号读法已改（听感未验）；32 个 payload/静态文件三方 SHA 一致、SourceGate PASS、宿主补丁全部 patched。
- **还需要用户判断**：听感（语速、"第二十二到二十四行"的读法、停顿暂扣多出的约 0.8 秒是否可接受）；第 4 步停顿追问是否只回答一轮、不再出现"请指定一至三个有界源码范围后再讲解"；角色是否会自己在学习材料窗口里标出某个关系；评分偏严是否可以接受；重启后语音端的接续。
- **待 Opus 复核项**：见上面 6 条（宿主层 2 条没有动手；payload 层的取舍 1 条；未验证 1 条）。
- 本会话的边界：没有开麦克风、没有真人验收；预算用尽后没有再发起真实模型调用。
