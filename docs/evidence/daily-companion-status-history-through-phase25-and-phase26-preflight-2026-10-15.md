# 日常学习伙伴当前状态（2026-10-15）

当前：阶段25真实ASR正式评分及Native子链取得证据，原量具FAIL保留、修后只读19项复核通过；本轮已发布 35abae0edd11e9e5569e3e220113969d8460cace。最新源码/证据均为阶段25；继承阶段24。Root master脏树及index保留，远端master未改；日常自动评分默认仍OFF，物理声音与真人待验。

阶段19实际原Start-Daily-Tutor.cmd文字入口Ready/refresh、课程设置历史保留通过；首次820topic行变FAIL保留，seed相同内容不UPDATE补丁4test及修后原21interaction/820topic/all nonkv rowhash数量不变。原daily当时pending/QA为空，不冒充错题重启证明；C33独立真实模型pending返课重启继承。diag11/actual-method4的localQueueSocket proof不证明provider ACK/full intake。

阶段20：voice34真实log反复No module named neko_phrase_input_transport，已补两exact helper部署到两个host根，实际cwd/import和SourceGate启动前核；9temp/stdlib PASS，最终独立containment审无具体P1/P2。尚未必要修后online，保留voice34 FAIL_NO_ASR_OR_REPLY。唯一新修改是部署安全，不替代声音验收。

真人第二场已finished/ex0，mic/capture策略恢复false，当前无已知自有host/session/listener（启动前再核，不按旧PID清理）。用户无抢答反馈、识别中文和方向纠错可用；A/B/A同pending身份是Main实际SDK证据。口头判错后实际SQLite attempt_evaluated=false/evaluation空；题型范围丢、超两句、识别方框为方案、图不可见、末段ASR后13.4s文本。正式评分追加轮没完整观察，不能伪造失败。真人wrong纠正保存/语言/打断完整体验未验。引导过程用户80%等Main，安排FAIL。详情 docs/evidence/daily-companion-human-feedback-2026-10-15.md。

阶段21 request透传4+quiz guards12+memory8 Main离线过，独立审及空材料P2闭合；原daily仅三个code文件LF/hash部署，无学习data/config/history写入。真实题型遵循仍待。

完整契约：docs/daily-companion-contract-2026-10-14.md（原文169行，SHA256 FD518311C0B3FAFBE038B2BBD83D8EB0DE8986212BCB4B86FCCAB22464084C33）。每次上下文压缩或自动续跑先完整读取 contract、plan、status、blockers；后续用户明确指令优先，同步记录。

2026-10-15用户明确恢复全部开发：先自动验证到可用，再安排集中真人验收，不逐句占用本人时间。现有Goal 01a13531-0341-7611-afc2-5c472a7ccf50 本轮get_goal已核active，不重建；完整约束以本contract及后续明确指令为准。局部阻塞记录失败/证据/尝试/恢复条件并转其他项；全部依据实际证据完成，阶段、小功能、到早晨或额度不构成完成。源码/离线、真实模型、设备播放、真人体验分层。

音频：必要speaker用户已设约4%，不调整音量。已结束真人场的mic授权不延续；禁止room/physical/virtual mic、捕获设备初始化、回环。固定WAV内存/WS允许；仅经核输出专用入口/8API捕获保护可发声，mixed启动仍拒绝。文字开发child NEKO_TASK_SILENT=1。

沿用 bargein-autocheck-20261012，核账本DeepSeek677/2000、Lanlan.app63/null、Lanlan.tech0/0。不重置/换轮/切付费供应商，不为额度耗完测试；Main独占额度/online，限流停无效重试并退避。既有两个子Agent独立窄审，无新Agent，共享代码Main负责。

允许审查后commit/push codex/功能分支，不merge/force/覆远端；保留Root脏树和.workbuddy，Root index不stage。排除密钥、用户DB/history/raw录音/policy。Sky Scout源码/索引/已有架构图只读；复用两对比图，不另建记忆系统、不删除重置原用户历史。

精简前全部原bytes已exclusive归档到 docs/evidence/daily-companion-status-history-through-human-test-2026-10-15.md；此前phase18/16/14/12/10/8原档保留。contract未变。

阶段21当前增量：源码/离线出题request透传4、材料12、memory8过；Native语音观察修复7 Main+独立过。必要单场phrase35有真实ASR→study_explain→两句English/24NativePCM、sourceEnded/queue0，无mic/capture/loopback，8APIguard。原raw35因心跳quiet/显式zhCN假设报turn_timeout/exit1/FAIL_PARTIAL，原文件不变；修后既有事件回放59.087s可结束，仅REPLAY通过，不追认整场PASS。speechEnd→ASR11.609s→首PCM21.775s，PCM→播放schedule0.512s，实际可听未验。唯一exec60014已terminal/cleanup_errors=[]，任务ports无listener。账本675/63/0，原round不重置。stage21证据 docs/evidence/daily-companion-phase21-quiz-request-and-voice-probe-2026-10-15.md。

已定位尚未修复：Native显式答当前题可以自由口头判错绕过study_answer，旧qid/attempt仍pending/evaluation空；下一步需权威ASR owner+expected qid/attempt/course/session准入和防重、结果前自由评分抑制/失败诚实，保护ordinary打断。不能只增强prompt或从口头结果倒写DB。然后材料可见/graded多轮及全A–F继续。两个Agent最终窄审冻结，Main已完成stage21 exact发布；应用Goal已active，按contract自动接续。

阶段22接续的具体边界：Core已注册study_answer，Native明确答题仍可零tool自由回复；只改prompt/转换已存在study_explain不覆盖零调用。必须固定真实pending identity与本轮ASR owner，使用原正式entry、防重复/换题；处理自由回复抑制与正式工具结果发声，不能伪造普通打断onset、复活退休scope或直接发虚构function_call_output。已核实际_tools.py要求Free返回真实call_id匹配server function_call，不能把一个local fabricated ToolCall当合法provider调用。Core turn.handle_input_transcript有既有plugin bus/缓存/显示，没有评分fallback；bus事件本身也没有当前完整voice owner，不能只按有pending题就消费每句对不对。先确定实际协议和权威快照/输出路径，再定向离线Core+SQLite测；不在不明时绕权限开mic/循环CONNECT。其它材料可见/记忆源码/受控指示继续，局部阻塞不暂停全部Goal。

阶段22已交付当前Study图片默认跟随/旧指示退役、私有四身份pin、同题wrong/partial更正新attempt保留原错答、Windows保护下日常provider设置恢复。Main/独立离线与真实SDK/SQLite通过；最终原daily入口Ready/refresh/current-image DOM与原27interaction/820topic/QA0/all学习行hash、原pending题和配置偏好均保留，exit0，预算不变。初次coreApi变化失败及恢复初版竞态P2证据保留，最终锁定版7测试及实际入口通过。source/offline不冒称Native自动评分已修；完整A–F继续。证据 docs/evidence/daily-companion-phase22-material-and-correction-2026-10-15.md。scene60427已terminal，48911/48916/9234/55804无listener。六空目录清理automatic approval blocked by policy，保留且不绕。原账本675/63/0不重置，speaker用户4%仅必要output-only可用，禁止mic/capture/loopback。下一步Native真实ASR→原题正式grade→受owner保护的结果输出，再连续集成、剩余A–F和集中human。

阶段23真实HTTP/SDK/DeepSeek同题wrong→correct两QA、原wrong行保持且同topic_id；+2 DS至677，app63/tech0不变。原ACK量具FAIL及实际graded startup丢题FAIL保持；修startup/idle按最新同课state四字段续接，新3/Main独立、course8/answer14过。只任务C32四字段按真实提交后冻结原件恢复，历史/QA原行不动，非原用户数据恢复；修后完整宿主返课/重启状态与两QA通过，不重复模型评分。scene9824已terminal，两owned host强制exit1/cleanup_errors[]，48911/48916无listener。原daily仅新init bytes受旧SHA防护部署，未再启动或改历史。证据 docs/evidence/daily-companion-phase23-graded-restart-2026-10-15.md。最新已发布代码阶段22 7ffb334be6bba957ab316e677a765dd1fcfc229b，阶段23源码已审查并精确发布 b540837d5f703cbc240d9fd87f175c2594f74e2a，远端同SHA、candidate clean、master不变。下一阶段Native accepted ASR后台正式grade、原题/owner pin、自由输出hold与逐send保护，缺terminal不猜音频归属；详见native-grade-fallback-design。完整A–F持续，不局部标整个完成。

续跑交接：本阶段自主工作未暂停，Goal active。所有当前有界场均terminal、没有需继续轮询的exec，任务host端口无listener。下一轮先完整读四文件，再按phase23末段和native-grade-fallback-design处理零ToolCall评分；在ASR后才取status并不足以证明回答对应输入开始时的题，应固定预先可信held身份/原语音输入scope，后续status+四pin只核它，不能改用换课/换题后的最新题。先完成真实方法/本地SDK/SQLite定向六组回归，再安排必要单场fixed WAV，缺终结不释放Native声音，不重复今日human/旧PASS。无全局阻塞/complete依据。

阶段24开发中：默认关闭Native显式答题自动正式grade。实际Core accepted transcript/route/echo→后台原SDK/SQLite→actual arbiter，本地12项通过，模型/连接/wire/设备替身，非真实Native或播放PASS。四身份首次音频pin、实际ASRowner、换题拒绝、同时provider去重、更正新attempt/原错答保留、一次受控无PCM重连、迟到发送抑制及失败诚实已离线覆盖。尚未runtime部署/发布，host/helper/product manifest待封版；当前不能启动该新版本宿主。legacy None/replay/歧义pin failclosed保留限制，独立审查进行中；learning_memory capacity失败已换给另一个既有Agent审，无新模型/Agent。账本实际677/63/0同round不变，本轮离线进程均terminal、无新增host/audio；不采mic/capture/loopback。详见 docs/evidence/daily-companion-phase24-native-grade-draft-2026-10-15.md。下一步独立审查修复、完整幂等/部署清单，必要有界Native固定WAV，然后其余A–F继续。Goal active，不能局部标complete。

阶段24后续封版：初稿input-time authority P2已修并独立复核；17项Main/独立本地通过，最后defaultOFF绑定一行独立审；actual LANLAN_APP arbiter item驱动分支覆盖，非provider ACK。两host副本30文件回放/幂等/AST通过，原manifest全匹配后实际部署默认OFF；3helper实际cwd import和SourceGate通过。部署后ordinary handoff12/phrase transport20过。product avatar返回qid/attempt，canonical/LF清单及原daily仅code旧SHA保护替换，未动DB/config。仍未发布/真实Native/设备/真人验收；不能说口头绕正式评分已整体交付。账本677/63/0同round，本轮无外部调用/host/音频，Goal active。下一步精确codex分支发布、必要固定WAV真实集成；其它A–F保留继续。详phase24报告末段优先。

阶段24源码已review/commit/push d520252c001f8d95a1f682f9fd15b27084a9d05b，远端codex/daily-learning-companion同SHA且candidate clean，remote master仍f1e8f3f5605659f0526e43bc3b85c60ae46c85fb。17 exact文件，staged LF产品29file及helper全部fingerprint核通过；Root index未stage，原脏树/.workbuddy保留。真实Native自动评分与设备仍待。下一轮先四文件，再准备自动评分专用observer：沿用既有任务材料/固定WAV，无mic/capture/loopback；先核真实任务库pending四身份（不得伪造、重置原历史），必要只创建本场新题，核ASR→QA及迟到音频owner/诚实失败。现有voice_probe默认只验study_explain，不能直接把其结果当grade PASS，先补针对性量具。未开online前先核账本和8API保护，保留单场超时/异常停止，不循环CONNECT。若局部protocol受阻，记录并转其余A–F，不停止全Goal。当前无新增host/音频会话，离线进程已terminal，Goal active。

阶段25进行中（启动真实场前）：trace19本地/30文件回放幂等/AST和实际SourceGate过，defaultOFF。新增grade-current observer及5preflight拒绝测试、只读snapshot/validator正在独立复核。已有任务C32 QA2/grade2可只读取证，拟同已有图创建本场必要新题，再单固定WAV真实ASR正式评分，不碰原daily DB/历史。离线一次合成明确评分意图WAV，未播放、未采设备。当前ledger677/63/0不变、无host在线；先量具正确和baseline/pin一致再开有界单场。报告phase25，Goal active，全A–F持续。

场36已terminal/exit1/cleanup_errors=[]，无Native连接/播放。真实quiz已成功保存pending题；observer错误要求rich study_quiz没有的ok字段而提前报FAIL，原raw保留SHA 8ce4ed6f033630c53c3521042c86b965f9e095c224974104554da89b8ad1f048。修为实际tool/非error/非degraded/题干双ID非空、补真实receipt第6前检，Main6PASS。只此新题DS+1至678，app63/tech0不变；旧QA2仍在。下一场37明确不prepare-grade-quiz，复用已保存qid/aid，启动前只读pin同36结果/未评分已核，不重出题、不重置历史，不重复未修服务场。当前无host listener，政策不变。

阶段25实际集成：36为quiz receipt量具FAIL保留，37原FAIL/exit1仅QA question JSON形态比较假阴性，修13项Main/独立测试后只读复算19checks全True，原raw SHA不变。真实Native ASR→正式wrong0/同题同attempt/QA2→3、旧两QA完整hash保持，原生同时study_answer实际合并一grade；一次无PCM受控重连、新token11PCM/playback schedule/source_ended通过。Main对实际submitted图SHA同已有forward图并视觉核WEX→NUD，正式反馈/Native两句正确。无mic/capture/loopback/volumechange；physical/human待。总DS685/2000、app65/null、tech0/0同round，原Coreprovider恢复deepseek，学习偏好/语言不变；25285 terminal exit1/cleanup[]，48911/48916/9234无listener。AUTO_GRADE日常默认仍OFF。下一步复用本wrong题验证Native明确纠正新attempt/原错答保留，先扩适配correction量具再必要单场；旧short/legacy/replay/自然停顿/全A–F继续。证据phase25及grade-observer-review，Goal active，不整体complete。

阶段25源码/证据已精确review/commit/push 35abae0edd11e9e5569e3e220113969d8460cace，13 allowlist文件，staged helper LF指纹通过；remote同SHA/candidate clean/master f1e8f3f未改，Root index未stage。发布后SourceGate再次通过，账本685/65/0，当前48911/48916/9234无listener，已无running exec需要轮询。现有Goal active。本轮是progress（真实自动正式grade+Native与记录发布）；下一轮仍先完整读contract/plan/status/blockers。C32当前真实wrong题及attempt仍在且evaluated=True已只读核，下一次不可再拿pending-answer脚本或重出题；先加correction模式和对应新attempt/旧wrong保留量具，再必要一次明确纠正固定WAV（无mic/capture/loopback），或转其余A–F。日常AUTO_GRADE默认OFF，不冒称全部交付。

阶段26进行中：复用C32场37真实wrong题/QA3，新增--grade-correction且禁止准备新题，Main8 preflight/baseline测试过；明确WEX→NUD固定纠正WAV一次离线合成，不播放/不捕获。既有Agent只扩correction独立量具，新attempt/原wrong hash及topic一致、旧formal可能跨host session，不虚构lineage字段。现在无host/online，账本685/65/0同round不变、AUTO_GRADE默认OFF。先量具复审，再必要单场纠正；全A–F不缩，Goal active。详phase26报告。
