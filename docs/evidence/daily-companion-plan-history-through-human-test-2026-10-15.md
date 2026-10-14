# 日常学习伙伴 plan（阶段十九已发布，Goal持续）

2026-10-15用户停止真人测试并反馈引导过慢：约80%时间等Main，20分钟计时包含准备/反馈且自动结束，流程安排FAIL。已核第二场finished/ex0、audio policy恢复mic/capture=false；Goal实际paused。语音识别/回复、方向纠错和用户无抢答反馈可用；评分只有口头评价，live及最终SQLite无评分，题型/篇幅约束、识别与图可见性有缺陷。语言/打断/纠正保存未验，不新开场补。详情 docs/evidence/daily-companion-human-feedback-2026-10-15.md。账本668/2000、app62/null、tech0/0沿用。后续明确恢复再优先评分真实落库/回读、题型简短和材料显示；离线/固定输入过后才整段8–10分钟人工，避免逐句等Main。

2026-10-15用户重新开始真人测试：上一场已确认finished/ex0、20分钟到期且原audio policy已恢复，用户未做，不记humanPASS。新场实际Ready：runner82639与Native observer94904，麦克风按钮存在、isRecording=false，未自动录音；按已授权mic/speaker准备，20分钟上限，结束恢复原禁止mic策略，Goal保持paused。原合成A图/test-course继续可用，学习表面已选forward，无重复图片模型提交；本场独立private报告和日志不覆盖旧场。

真人测试准备已完成：Goal实际paused；用户明确本次mic/speaker授权。原daily测试课human-picture-a-20261014提交既有合成forward图（真实Study确认WEX→NUD→REZ、非degraded），受控窗口已选同PNG；不要求用户真实案例。Native可见窗口/麦克风按钮Ready、isRecording=false；human runner30716与只观察Native的94396实际live，等用户第一句，不自动替用户开始mic。当前账本DS617/2000、app59/null、tech0/0；准备模型调用+7，原round不重置。计划/markers/private日志均在ignored raw；用户反馈前无humanPASS。结束恢复原mic禁止策略与原selected course，Goal仍paused等明确继续。

用户要求安全收尾后暂停自动开发、先真人体验：阶段20具体phrase缺失部署已修，Main9临时检查及实际两树部署/SourceGate/launcher-cwd import通过；未起应用/设备/provider，未commit/push。安全检查点 docs/evidence/daily-companion-phase20-safe-checkpoint-2026-10-14.md。独立审8项race闭合，最后root containment/第9项恢复后再核。账本610/59/0无变化，无自有运行场。当前用户明确允许本次在场真人测试使用mic/speaker，不调约4%音量、不loopback；结束恢复原禁止mic开发边界，不自动恢复Goal。完整A–F/contract/原账本/局部阻塞继续/实际证据完成要求均保留。

阶段二十进行中：阶段19实质进展继承。Main核实际宿主22:20:10..30重复 No module named neko_phrase_input_transport，且launcher cwd的importlib.find_spec对两个phrase helper均false；这给出34具体发送失败原因，不回写34或冒称修后声音成功。发现本地tests的scripts路径掩盖缺失部署；改为两个exact helper部署到两个host根、source/deployed指纹+实际cwd child import启动前检查。新增六temp离线部署/import/拒绝/idempotence检查已过，独立审查及实际SourceGate尚待。根据新明确原因调整原counts-hook优先级，先闭合具体部署缺陷；helper诊断生产hook仍未做，不为计数而扩大改动。账本仍610/59/0，尚未安排新online/音频场；mic/capture/loopback禁止，必要speaker4%不调音量。

1. B下一实际动作：接入现default-OFF counts-only helper到actual Core/phrase/transport，更新精确host replay/manifest/SourceGate，独立审查/本地真实方法回归后再安排必要诊断场。不同方法独立aggregate不能误称同一个整体计数；不可从return=true推断发送。保guard/ordinary打断，不因计数已有而猜34根因或无效CONNECT。
2. A/F原daily文字入口已实跑，新版部署/Ready/refresh和原21interactions/820topics等逐row保留通过；相同seed重复UPDATE已源码修复、实际复验。原daily无pending/QA/错题对象，不造题充验收；C33同题返课/重启model证据独立继承。无需再跑相同已过入口，除非相关代码改或回归。
3. 继续C更宽graded跨课连续、D源码工具/口语与版本证据、E受控图片/source角色指示、F多材料连续及网络恢复。human集中10–20分钟尚待；docs/daily-companion-human-experience已更新真实原入口范围，键盘/无mic。主动narration defaultOFF后置。

阶段十九当前没有运行中的自有host/Native/browser/online场；exec1561（首次topics保留FAIL）及21312（修后PASS）均terminal，两个场均正常Enter结束、cleanup_errors=[]，48911/48916/9234无listener。没有声音或设备，没有线上模型调用，账本bytes未变。下一轮先读四记录，再继续实际hook，不自动重跑19入口或旧voice34。

完整契约：D:/CODE/project/LiveTutor-Lab/docs/daily-companion-contract-2026-10-14.md；169行，SHA256 FD518311C0B3FAFBE038B2BBD83D8EB0DE8986212BCB4B86FCCAB22464084C33。原文不摘要替代。每次上下文压缩或自动续跑先完整读 contract、plan、status、blockers；用户后续明确指令优先并同步记录。

现有 Goal 01a13531-0341-7611-afc2-5c472a7ccf50 ACTIVE，不重建。局部阻塞记录证据/尝试/恢复条件并转其他项；只有实际完整交付才 complete，阶段结束、到早晨、额度或单项失败均不能代替完成证据。源码/离线、真实模型、设备播放、真人体验分别记录。

最新用户重申：必要时使用用户设置约4%的扬声器，不调整音量；仍禁止房间/物理/虚拟麦克风、捕获设备初始化和回环。固定WAV内存/WS授权保留；输出专用先安装8 API捕获保护，旧mixed入口继续拒绝。文字场使用 NEKO_TASK_SILENT=1。真人麦克风仍须用户明确准备好了且重新明确许可。

沿用 bargein-autocheck-20261012，不重置换轮；当前账本 DS610/2000、Lanlan.app59/null、Lanlan.tech0/0。Main独占额度/在线场安排，不切付费供应商，不为用完额度重复测试。限流停无效重试并退避。两个既有子Agent冻结，无新Agent。

允许审查后 commit/push codex/分支；不merge主分支、不force、不覆盖远端历史；保留Root原脏树/.workbuddy及空index，排除密钥、用户DB/history、raw/测试录音/local policy。Sky Scout源码/索引/已有图只读，不重建材料，不另建记忆系统，不清原用户历史。

最新阶段19已review/commit/push：0cb1045147abf163aba8f35ba527c083c986ab19；12 exact文件，parent1bc11f210937dddfe6499b2b6ff6736843d79f46。managed/远端codex/daily-learning-companion同SHA且clean；29个product canonical指纹全部核实，28个原daily部署raw匹配，index额外exact保护封装/Windows换行字节比较通过，manifest不假称index raw相同。Main seed4/diag11/actual-method4过，候选seed4/diag11及两个JS语法检查过；actual-method4是Main runtime，候选不带ignored host依赖，未冒称候选执行这4项。index文本/LF payloadSHA/AST/密钥模式/diff-check过；无private数据发布。阶段18已发布1bc11f2证据继承。Root HEAD2c541755344eb8bcf35e310f871c513ea809e1a5；remote master f1e8f3f5605659f0526e43bc3b85c60ae46c85fb 未动。阶段17 eadc692、16 d0c28db、15 e34c2f9、14 605deff、13 56c2a07 及全部详细证据继承。

阶段18关键失败：唯一voice34 real session_started + server RNNoise DSP约20.13s；无observed append/ASR/tool/reply/Native PCM，turn_timeout=true，FAIL_NO_ASR_OR_REPLY。旧raw exit0/failure=null只是观察程序结束，不能算验收。所有此场自有进程已退出/cleanup_errors=[]，不再online重试。Native同task就绪等待修复14离线检查通过，不能当语音成功。

精简前 plan/status/blockers 原始bytes分别归档到 docs/evidence/daily-companion-*-history-through-phase18-2026-10-14.md（exclusive创建并hash复核）；更早phase16/14/12/10/8原档保留。contract不动；旧档历史预算/进程/下一步不自动作为当前状态。
