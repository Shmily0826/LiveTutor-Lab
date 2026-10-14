# 日常学习伙伴当前状态（2026-10-15，阶段27）

当前阶段27取得新观测与真实FAIL证据，Goal active/全A–F未完。复用分析模块自动拆时延，12 Main/独立tests及preflight8/completion7过。必要短答39识别成两ASR，原正式SDK虽新增同题correct100，但无Core claim、角色说旧“已经评分”，真实FAIL保留，不能说日常答题已修完。下一步优先分段/重复请求上下文，不再重复未修在线。日常AUTO_GRADE默认OFF，physical/human待。

完整契约：[原文](daily-companion-contract-2026-10-14.md)，169行，SHA256 `FD518311C0B3FAFBE038B2BBD83D8EB0DE8986212BCB4B86FCCAB22464084C33`，未修改。每次上下文压缩或自动续跑先完整读取 contract、plan、status、blockers；后续用户明确指令优先，同步更新记录。Goal `01a13531-0341-7611-afc2-5c472a7ccf50` 当前实查 active，不重建、不局部标完成；完成依据实际交付和证据。局部阻塞记录失败/尝试/恢复条件，转其他任务；限流停止无效重试并退避。

当前权限：必要扬声器仅用户已设约4%，不调整音量；禁止房间/物理/虚拟麦克风、捕获设备初始化和回环。已结束真人场的mic授权不延续。固定WAV只走文件→内存/WS，真实发声必须output-only及8API捕获保护；文字child `NEKO_TASK_SILENT=1`。不夜间要求本人朗读；再次集中真人体验待核心可用及本人明确在场。

账本沿用 `bargein-autocheck-20261012` 不重置/换轮：最新实查 DeepSeek **699/2000**、Lanlan.app **68/null**、Lanlan.tech **0/0**；仅Main调整额度和安排在线。无其他付费供应商；连接有界超时/异常停止/退避，不无限重连，不为耗额度测试。请求计数非账单金额。

允许项目必要修改/隔离依赖、自有测试进程清理；保留Root脏树/.workbuddy/原历史。仅审查过allowlist commit/push `codex/`功能分支，不合并主分支、不强推/覆远端；排除密钥、用户DB、raw音频与无关修改。已有两个子Agent窄范围不冲突，无新增或换模型；Sky Scout源码/索引/已有架构图只读，复用已有两对比图。复用原SQLite和CodeGraph，不另建记忆/索引系统。

源码/离线、真实模型/SQLite、Native接收与播放调度、物理可听、真人体验分别报告；不能用日志/排程冒充可听或本人认可。当前人工不再逐句协助；自动验证到可用后一次约10–20分钟集中体验。

## 本阶段真实证据

- C32原任务/原forward图/场37原wrong题，未重出题、未提交新图、未动原daily DB。observer新增 `--grade-correction`，必须grade-current/output-only/单固定WAV/已有fresh任务，禁止prepare-grade-quiz；启动前四ID和evaluated=True/last wrong或partial匹配，普通答题仍要求pending。Main及独立8离线测试通过。
- correction量具20离线测试Main/独立通过：原formal历史session可早于当前restart，精确join原qid/aid/session/ASR/成绩；sameqid/题干、新aid/evaluated、恰+1QA/formal、所有原QA完整rowSHA/旧formal投影不变、相同非空topic。Native owner/capture/时序继承，原普通场37只读20项仍过。
- 场38唯一exec46447 terminal exit1/cleanup_errors=[]，48911/48916/9234实查无listener。原raw `benchmarks/raw/evidence/daily-companion-20261015-native-correction38.json` SHA256 `c421dc05ef6fa71018ca1c00a3923a0b312ad005d1f3af20f4f4036b582161f8`；原FAIL_OR_PARTIAL保留，22项仅new_token_pcm_after_grade=False。
- qid `q_f62b68fa3e77408cb26c2bbf3c1eb607` 不变，old aid `a_a71cf8980ca641bf84add105a3f7a055` → new aid `a_826a0e03bcdd4a1eb9fefd5d5c702511`。QA3→4、原wrong0与旧QA全hash/grade公开投影保留；actualASR方向WEX→NUD正确，正式correct100，角色一句“对，起点WEX、终点NUD，完全正确”。原实际submitted图SHA与已有forward图相同、WEX→NUD语义核查继承阶段25，材料前后相同。
- accepted/grade_complete实际conn1/scope2，relay conn2/scope4，新token；原token cancel收到，fresh Native旧PCM0。8帧中7个正PCM累计378480bytes，末事件bytes0；均新token且grade后，source_ended/activefalse/remaining0。空binary本身不作PCM/ACK/终结；修量具仍核全部owner/时序/非负int且至少一正PCM，Main/独立21tests过。只读derived22checks全真，原exit1不追认；派生SHA256 `1f2837ad9f9ffcd44b160f60fd5654d41b9ecafd532b8f30cd3568aa44571cec`。8API locked/output-only、capture_started=false，未用mic/capture/loopback、不改音量。
- speech end→观察ASR10.602s；accepted→grade4.308s；grade→relay0.579s；relay→首PCM2.225s；PCM→schedule0.527s；speech end→PCM17.707s。既有phrase日志：封口wall1791992479.933、首写2479.942、完成2479.960；speech-end estimate2478.724，有意1.2s缓冲，写入32ms，完成写→accepted约9.290s。该后段是服务识别/返回/调度组合，不能全部归单模型或以压停顿阈值修。
- 前后Study preferences公开值、cfg.language和材料相同；比较整个RPC含_seconds会假不同，只比较实际偏好字段。任务coreApi已恢复deepseek。账本685→691 DS(+6，总调用不等于全是评分)、app65→67(+2：初始与受控relay)，tech0，原round/预算不变。

## 继承成果与保留失败

阶段19原Start-Daily-Tutor文字Ready/refresh/原21interaction/820topic/all非kv历史行hash保持，首次seed UPDATE FAIL保留并修4test。阶段20缺phrase helper实际cwd/SourceGate修复，34原FAIL不覆。阶段21 request透传/guard及真实phrase35 ASR→Study→English/24PCM，原timeoutFAIL保留、只读REPLAY修复，不冒充原exit0。阶段22 material窗口/currentimage及同题correction私有四身份、provider恢复Windows保护真实/离线过；六空目录清理被automatic approval blocked by policy，保留且不绕。

阶段23实际HTTP/SDK/DS wrong→correct/同topic/两QA及graded返课/两host重启过，startup丢题原FAIL修3test；只任务四state按真实冻结件恢复，不是用户历史修复。阶段24显式Native正式grade source17本地+actualLANLAN_APP arbiter/30文件幂等/SourceGate及部署、ordinary12/phrase20过；默认OFF，遗留协议输入failclosed。阶段25场37实际ASR→正式wrong0/同aid/QA2→3/同时provider去重、11新PCM/播放终结；原question JSON量具FAIL保留，修13tests只读19全真；材料语义Main核正确。上述physical/human都未外推。

真人第二场已经结束：本人报告无抢答、识别中文/方向纠错可用；但未正式调用评分/图不可见/超句/ASR后13.4s等FAIL，以及本人80%等Main的组织FAIL均保留在 `docs/evidence/daily-companion-human-feedback-2026-10-15.md`。之后修复不冒充再次human认可。

## 发布与下一步

Root dirty master保留、index未stage；managed `C:/Users/Shmily/.codex/worktrees/daily-companion/LiveTutor-Lab`，分支 `codex/daily-learning-companion`。最新代码35abae0edd11e9e5569e3e220113969d8460cace、元数据39f98bac833db95939cfb0bfb7ba181c2f3aaa7d，candidate本阶段前clean；remote master仍f1e8f3f5605659f0526e43bc3b85c60ae46c85fb（发布时再核）。26 observer/validator/证据已review/commit/push `3016a30a8910f6e21efbf63c6b94725f276b87f4`，12 allowlist文件；candidate clean、remote同SHA、master未改。产品Core/runtime此次未变，Root index未stage。

当前没有running场/host需要轮询。既有screen_guidance已完成量具两文件及其review窄审/只读派生后冻结，无provider权限；learning_memory容量失败冻结，不换模型、不新建Agent。本阶段已发布；下一步补已存在phrase日志的自动分段观测，把输入结束→ASR前段定位；随后日常启用范围、语言/自然短答/全A–F继续。无全局阻塞或complete依据。

## 归档

精简前status全部原bytes独占归档 `docs/evidence/daily-companion-status-history-through-phase25-and-phase26-preflight-2026-10-15.md`，SHA256 `a535f58a5df7bcbd02f0c386056c6dc163358c88c8fedbbffdf10f7eadadd3d9`；plan档d8a3694e、blockers档baa8d2b1、此前历史档均保留，contract未改。

阶段27启动前：既有phrase/grade自动分段诊断已source修及Main/独立12tests，两个诊断P2已闭；preflight8/完成7过。37/38原件不变，v2只读派生确认写完→accepted7.790/9.290s、Core比provider观察仅约3ms，保护1.2s停顿。必要一场短6.438s固定输入39将复用C32原图，因原题correct通过原Study生成新题而不改历史。SourceGate/output-only已过；本轮尚无新host/调用，ledger691/67/0，mic/capture/loopback仍禁、speaker用户4%。详phase27报告；Goal active/all A–F保留。

阶段27场39收尾：exec11085 terminal/exit1/cleanup[]，任务48911/48916/9234无listener，无live场需轮询。原raw39 SHA3199f88767ef1eec3d6e73c04663d6bc71c3d49af400e09bbf1ef726413180e0，实际一个完整109782sample phrase、两个ASR、provider两次study_answer、QA4→5 current correct100及旧四QA hash保留，但没有Core grade markers，Native错误复述旧“已经评分”。新QA来自provider简写，不是完整逐字ASR；helper后续未执行false不等于实际捕获失败，八API实installed/locked且mic/capture/loopback/volumechange全false。真实偏好/语言相同，task provider恢复deepseek。账本699/2000、app68/null、tech0/0同round，+8DS/+1app，不把全DS当评分。

下一轮先四文件，从phase27末段/latency-review的真实分段缺陷续：首段明确“当前题+我的答案是...”的准入和后段scope/事务必须成套，保护新PCM/换题/连接、未知修饰不拼接；单改regex后第二ASR会retire旧task，禁止复活owner。优先离线actual Core/SDK/SQLite回放再必要有界修后场；当前没有新的runtime修复/默认启用，余A–F持续。旧阶段25/26成功及37/38原FAIL/derived都保留，不外推39。
