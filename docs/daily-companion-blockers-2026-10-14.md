# 日常学习伙伴局部阻塞与缺陷（2026-10-15）

| 项 | 证据/尝试 | 恢复条件与继续方向 |
|---|---|---|
| Goal自动续跑 | app get_goal仍paused，状态接口无active；已请求现有Goal UI恢复 | 本轮开发继续；界面恢复后核状态，不重建 |
| Native评分 | 真人口头判错，live/final SQLite仍pending/evaluation空 | 修实际角色工具选择，wrong纠正真实落库回读；并行出题及材料 |
| 题型/篇幅 | role quiz无request字段，后台丢方向二选一；有三句/unasked question | request透传/模型回归，临时不写长期偏好 |
| 图可见 | open_in_codex queued不证明用户看见，用户反馈看不到 | 同当前材料受控可见入口，明确Native直视不可靠 |
| phrase34 | session_started/serverDSP无ASR/reply/PCM；根层缺两个helper已source修复review9过 | 发布SourceGate/实际部署后必要固定输入，非无效旧重跑；无mic/loopback |
| 自然停顿语言术语 | 旧backend/设备局部继承；本场无抢答只有指定试验 | 自动完整链测，再集中human，不扩大已有PASS |
| graded接续及桌面 | pendingC33/受控指示继承；更宽graded/任意桌面待 | 实际连续及受控surface先交付，其他项不因桌面停 |
| human验收 | 前次组织FAIL，wrong纠正/语言/打断没验 | 用户明确再在场后一次10–20min，不当前要求本人继续 |
| 主动人格/narration | defaultOFF，完整authority未交付 | 后置，不挡核心伙伴使用 |

无全局阻塞或complete依据。服务限流/离线停止该线路，继续本地/其他项。历史失败、预算和进程只作历史，最上当前记录为准。

完整契约：docs/daily-companion-contract-2026-10-14.md（原文169行，SHA256 FD518311C0B3FAFBE038B2BBD83D8EB0DE8986212BCB4B86FCCAB22464084C33）。每次上下文压缩或自动续跑先完整读取 contract、plan、status、blockers；后续用户明确指令优先，同步记录。

2026-10-15用户明确恢复全部开发：先自动验证到可用，再安排集中真人验收，不逐句占用本人时间。现有Goal 01a13531-0341-7611-afc2-5c472a7ccf50 不重建；应用最后读取仍paused，已请求界面恢复，当前本轮开发获明确授权。局部阻塞记录失败/证据/尝试/恢复条件并转其他项；全部依据实际证据完成，阶段、小功能、到早晨或额度不构成完成。源码/离线、真实模型、设备播放、真人体验分层。

音频：必要speaker用户已设约4%，不调整音量。已结束真人场的mic授权不延续；禁止room/physical/virtual mic、捕获设备初始化、回环。固定WAV内存/WS允许；仅经核输出专用入口/8API捕获保护可发声，mixed启动仍拒绝。文字开发child NEKO_TASK_SILENT=1。

沿用 bargein-autocheck-20261012，核账本DeepSeek668/2000、Lanlan.app62/null、Lanlan.tech0/0。不重置/换轮/切付费供应商，不为额度耗完测试；Main独占额度/online，限流停无效重试并退避。既有两个子Agent独立窄审，无新Agent，共享代码Main负责。

允许审查后commit/push codex/功能分支，不merge/force/覆远端；保留Root脏树和.workbuddy，Root index不stage。排除密钥、用户DB/history/raw录音/policy。Sky Scout源码/索引/已有架构图只读；复用两对比图，不另建记忆系统、不删除重置原用户历史。

精简前全部原bytes已exclusive归档到 docs/evidence/daily-companion-blockers-history-through-human-test-2026-10-15.md；此前phase18/16/14/12/10/8原档保留。contract未变。
