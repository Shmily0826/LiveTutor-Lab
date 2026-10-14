# 日常学习伙伴执行计划（2026-10-15恢复开发）

优先级：
1. 阶段20已推ae23b1d，SourceGate/实际两cwd+Main/候选9test过。原voice34失败保持，不重复相同已过检查。现在优先正式评分路由。
2. 修Native口头判错不调用study_answer/无评分记录；明确区分角色选择工具与直接callback。用本次实际句子做回归，核wrong/后续纠正持久化、回读、返课重启。
3. 阶段21出题request透传已交付，真实模型题型/篇幅遵循仍待必要集成验证；临时要求不存长期偏好。
4. 修当前材料可见性与统一课程/图片绑定；拆分Main等待与实际模型/工具/音频延迟。固定输入验证无需本人朗读。
5. 全部A–F继续集成；核心过后一次完整10–20分钟真人脚本，材料日志先就绪、从实际开始计时、整段后反馈。

| contract范围 | 持续剩余工作 |
|---|---|
| A | 日常就绪/失败信息、材料可见、更新/换课正确、可靠Study vision到角色声音；密集小字诚实边界 |
| B | 中文/英文/临时切换/课语言，自然停顿与ordinary打断保护，术语数字代码，完整阶段时延，简短与纠错 |
| C | 同题wrong及纠正/历史实际取用、graded连续返课重启，既有SQLite四偏好和概念身份，不建新库 |
| D | 既有CodeGraph授权Sky结构/调用/行/改动影响；索引版本引用范围、工具选择、事实推断、避免全仓 |
| E | 受控HTML/image/source指示及滚动缩放版本定位；任意桌面fallback明确，开源适配许可证依据继承，学习者操作 |
| F | 多轮/换材料/返课/重启/网络恢复，启动支持问题发布步骤，基础简短耐心风格，集中真人验收 |

完整契约：docs/daily-companion-contract-2026-10-14.md（原文169行，SHA256 FD518311C0B3FAFBE038B2BBD83D8EB0DE8986212BCB4B86FCCAB22464084C33）。每次上下文压缩或自动续跑先完整读取 contract、plan、status、blockers；后续用户明确指令优先，同步记录。

2026-10-15用户明确恢复全部开发：先自动验证到可用，再安排集中真人验收，不逐句占用本人时间。现有Goal 01a13531-0341-7611-afc2-5c472a7ccf50 本轮get_goal已核active，不重建；完整约束以本contract及后续明确指令为准。局部阻塞记录失败/证据/尝试/恢复条件并转其他项；全部依据实际证据完成，阶段、小功能、到早晨或额度不构成完成。源码/离线、真实模型、设备播放、真人体验分层。

音频：必要speaker用户已设约4%，不调整音量。已结束真人场的mic授权不延续；禁止room/physical/virtual mic、捕获设备初始化、回环。固定WAV内存/WS允许；仅经核输出专用入口/8API捕获保护可发声，mixed启动仍拒绝。文字开发child NEKO_TASK_SILENT=1。

沿用 bargein-autocheck-20261012，核账本DeepSeek675/2000、Lanlan.app63/null、Lanlan.tech0/0。不重置/换轮/切付费供应商，不为额度耗完测试；Main独占额度/online，限流停无效重试并退避。既有两个子Agent独立窄审，无新Agent，共享代码Main负责。

允许审查后commit/push codex/功能分支，不merge/force/覆远端；保留Root脏树和.workbuddy，Root index不stage。排除密钥、用户DB/history/raw录音/policy。Sky Scout源码/索引/已有架构图只读；复用两对比图，不另建记忆系统、不删除重置原用户历史。

精简前全部原bytes已exclusive归档到 docs/evidence/daily-companion-plan-history-through-human-test-2026-10-15.md；此前phase18/16/14/12/10/8原档保留。contract未变。

阶段21当前增量：源码/离线出题request透传4、材料12、memory8过；Native语音观察修复7 Main+独立过。必要单场phrase35有真实ASR→study_explain→两句English/24NativePCM、sourceEnded/queue0，无mic/capture/loopback，8APIguard。原raw35因心跳quiet/显式zhCN假设报turn_timeout/exit1/FAIL_PARTIAL，原文件不变；修后既有事件回放59.087s可结束，仅REPLAY通过，不追认整场PASS。speechEnd→ASR11.609s→首PCM21.775s，PCM→播放schedule0.512s，实际可听未验。唯一exec60014已terminal/cleanup_errors=[]，任务ports无listener。账本675/63/0，原round不重置。stage21证据 docs/evidence/daily-companion-phase21-quiz-request-and-voice-probe-2026-10-15.md。

已定位尚未修复：Native显式答当前题可以自由口头判错绕过study_answer，旧qid/attempt仍pending/evaluation空；下一步需权威ASR owner+expected qid/attempt/course/session准入和防重、结果前自由评分抑制/失败诚实，保护ordinary打断。不能只增强prompt或从口头结果倒写DB。然后材料可见/graded多轮及全A–F继续。两个Agent最终窄审冻结，Main已完成stage21 exact发布；应用Goal已active，按contract自动接续。

阶段22接续的具体边界：Core已注册study_answer，Native明确答题仍可零tool自由回复；只改prompt/转换已存在study_explain不覆盖零调用。必须固定真实pending identity与本轮ASR owner，使用原正式entry、防重复/换题；处理自由回复抑制与正式工具结果发声，不能伪造普通打断onset、复活退休scope或直接发虚构function_call_output。已核实际_tools.py要求Free返回真实call_id匹配server function_call，不能把一个local fabricated ToolCall当合法provider调用。Core turn.handle_input_transcript有既有plugin bus/缓存/显示，没有评分fallback；bus事件本身也没有当前完整voice owner，不能只按有pending题就消费每句对不对。先确定实际协议和权威快照/输出路径，再定向离线Core+SQLite测；不在不明时绕权限开mic/循环CONNECT。其它材料可见/记忆源码/受控指示继续，局部阻塞不暂停全部Goal。

阶段22已交付当前Study图片默认跟随/旧指示退役、私有四身份pin、同题wrong/partial更正新attempt保留原错答、Windows保护下日常provider设置恢复。Main/独立离线与真实SDK/SQLite通过；最终原daily入口Ready/refresh/current-image DOM与原27interaction/820topic/QA0/all学习行hash、原pending题和配置偏好均保留，exit0，预算不变。初次coreApi变化失败及恢复初版竞态P2证据保留，最终锁定版7测试及实际入口通过。source/offline不冒称Native自动评分已修；完整A–F继续。证据 docs/evidence/daily-companion-phase22-material-and-correction-2026-10-15.md。scene60427已terminal，48911/48916/9234/55804无listener。六空目录清理automatic approval blocked by policy，保留且不绕。原账本675/63/0不重置，speaker用户4%仅必要output-only可用，禁止mic/capture/loopback。下一步Native真实ASR→原题正式grade→受owner保护的结果输出，再连续集成、剩余A–F和集中human。
