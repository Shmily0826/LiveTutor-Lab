# 日常学习伙伴局部阻塞与缺陷（2026-10-15，阶段28）

完整契约：[原文](daily-companion-contract-2026-10-14.md)，169行，SHA256 `FD518311C0B3FAFBE038B2BBD83D8EB0DE8986212BCB4B86FCCAB22464084C33`，未修改。每次上下文压缩或自动续跑先完整读取 contract、plan、status、blockers；后续用户明确指令优先，同步更新记录。Goal `01a13531-0341-7611-afc2-5c472a7ccf50` 当前实查 active，不重建、不局部标完成；完成依据实际交付和证据。局部阻塞记录失败/尝试/恢复条件，转其他任务；限流停止无效重试并退避。

当前权限：必要扬声器仅用户已设约4%，不调整音量；禁止房间/物理/虚拟麦克风、捕获设备初始化和回环。已结束真人场的mic授权不延续。固定WAV只走文件→内存/WS，真实发声必须output-only及8API捕获保护；文字child `NEKO_TASK_SILENT=1`。不夜间要求本人朗读；再次集中真人体验待核心可用及本人明确在场。

账本沿用 `bargein-autocheck-20261012` 不重置/换轮：最新实查 DeepSeek **706/2000**、Lanlan.app **70/null**、Lanlan.tech **0/0**；仅Main调整额度和安排在线。无其他付费供应商；连接有界超时/异常停止/退避，不无限重连，不为耗额度测试。请求计数非账单金额。

允许项目必要修改/隔离依赖、自有测试进程清理；保留Root脏树/.workbuddy/原历史。仅审查过allowlist commit/push `codex/`功能分支，不合并主分支、不强推/覆远端；排除密钥、用户DB、raw音频与无关修改。已有两个子Agent窄范围不冲突，无新增或换模型；Sky Scout源码/索引/已有架构图只读，复用已有两对比图。复用原SQLite和CodeGraph，不另建记忆/索引系统。

源码/离线、真实模型/SQLite、Native接收与播放调度、物理可听、真人体验分别报告；不能用日志/排程冒充可听或本人认可。当前人工不再逐句协助；自动验证到可用后一次约10–20分钟集中体验。

| 当前局部项 | 实际证据/尝试 | 恢复条件与继续方向 |
|---|---|---|
| 短答分段/旧结果优先修 | 39：一整包109782samples仍两ASR；首段声明缺末judge，尾段“点评分”；role两次grade只记一QA，但Native说旧“已经评分”，原真实FAIL | 声明准入与SDK慢await前后的scope/事务归属成套修，actual Core/SQLite回放+新PCM/换题/连接反例，不能仅regex/shield旧task/改owner scope。未修不重复online。 |
| Native纠正量具已闭合 | 场38正式correct100/同题新attempt/QA3→4原wrong保留、topic一致；原FAIL是末0byte frame误判 | 源码核空binary跳过、21tests Main/独立过，另建只读22/22+语义通过；原FAIL保留，physical/human待，未重跑。 |
| Native日常启用 | 显式answer场37、correction38真实子链；默认OFF | 完成输入范围/自然短答/连续课，legacyNone/replay/歧义pin failclosed仍限制，不能只调prompt或跳DB评分。 |
| 响应慢 | 场38说完→PCM17.707s，观察ASR10.602s；phrase封口约1.2s、写32ms、写完→accepted约9.290s | 从既有日志继续拆服务边界，保护自然停顿与ordinary barge-in；必要新证据有针对性单场，勿重复旧PASS。 |
| 题型/篇幅/语言术语 | request透传已source修；真人曾范围丢/超句，英语guard等有局部证据 | 连续真实模型回归中文/英文/临时切换/课程语言，明确偏好才持久，不把临时升级长期。 |
| 材料/指示范围 | 阶段22 currentStudy图真实DOM，受控surface/source既有；旧本人未见图FAIL保留 | 日常入口持续可见/换材料换课定位退役；任意桌面定位受限先controlled，不能宣称任意窗口。 |
| 记忆/源码 | 既有SQLite两QA/重启与26topic保留；CodeGraph已接 | 更宽历史实际引用、长期四偏好/概念，源码版本/引用范围/工具选择继续，不重建系统。 |
| 设备/human | NativePCM/schedule/sourceEnded不等于物理可听；上一场组织FAIL | 自动到核心可用再一次10–20min，当前不要求本人逐句；mic授权不自动续。 |
| 低优先清理/Agent | 六空目录清理automatic approval blocked by policy；learning_memory容量失败 | 保留不绕权限、不换模型，Main及既有另一Agent窄审继续；主动人格后置。 |

Goal active实查，旧paused仅历史；没有全局阻塞/完成依据。某项失败不能结束整个Goal。所有剩余项见plan A–F。场38exec46447已terminal/cleanup[]，无自有host监听；额度691/67/0为当前，旧报告数字仅历史。

精简前blockers全部原bytes独占归档 `docs/evidence/daily-companion-blockers-history-through-phase25-and-phase26-preflight-2026-10-15.md`，SHA256 `baa8d2b1f257330acd0295159e65a143c63f1992ab75553b7a75d9abf31140e5`；之前历史档保留，contract原文不变。

阶段27启动前：既有phrase/grade自动分段诊断已source修及Main/独立12tests，两个诊断P2已闭；preflight8/完成7过。37/38原件不变，v2只读派生确认写完→accepted7.790/9.290s、Core比provider观察仅约3ms，保护1.2s停顿。必要一场短6.438s固定输入39将复用C32原图，因原题correct通过原Study生成新题而不改历史。SourceGate/output-only已过；本轮尚无新host/调用，ledger691/67/0，mic/capture/loopback仍禁、speaker用户4%。详phase27报告；Goal active/all A–F保留。

阶段27场39收尾：exec11085 terminal/exit1/cleanup[]，任务48911/48916/9234无listener，无live场需轮询。原raw39 SHA3199f88767ef1eec3d6e73c04663d6bc71c3d49af400e09bbf1ef726413180e0，实际一个完整109782sample phrase、两个ASR、provider两次study_answer、QA4→5 current correct100及旧四QA hash保留，但没有Core grade markers，Native错误复述旧“已经评分”。新QA来自provider简写，不是完整逐字ASR；helper后续未执行false不等于实际捕获失败，八API实installed/locked且mic/capture/loopback/volumechange全false。真实偏好/语言相同，task provider恢复deepseek。账本699/2000、app68/null、tech0/0同round，+8DS/+1app，不把全DS当评分。

下一轮先四文件，从phase27末段/latency-review的真实分段缺陷续：首段明确“当前题+我的答案是...”的准入和后段scope/事务必须成套，保护新PCM/换题/连接、未知修饰不拼接；单改regex后第二ASR会retire旧task，禁止复活owner。优先离线actual Core/SDK/SQLite回放再必要有界修后场；当前没有新的runtime修复/默认启用，余A–F持续。旧阶段25/26成功及37/38原FAIL/derived都保留，不外推39。

阶段28开发接续（最末为当前）：候选明确当前pending声明+same-local-sealed纯评分尾句已Main27实际方法/SDK/SQLite回放，intent15PASS/1symlink权限skip，独立27/16(1skip)/phrase20；first-origin waiting证明、之后provider terminal清waiting仍可在严格同owner/frames/对象下吞精确一次尾请求、3s、取消/新PCM优先、异常隔离均有反例。不是线上/设备PASS，未知语义分段仍限制。原39仍真实FAIL，未再online，ledger699/68/0，host无运行。

重要部署状态：Root helper/patch源码已改，manifest仍旧SHA，两个actual host未改；现在不得启动。需完成30file临时全canonical回放/幂等/AST/单helper计数、最后normalizer旧replay重插exact bundle增量补审，再旧SHAguard部署/清单/实际cwd imports/SourceGate。详phase28-short-answer报告与short-answer-tail-review。当前未发布phase28，最新远端d87a26e；Goal active/all A–F不缩，先读四文件续，不跑未修39。


阶段28部署更新：最终迁移P2独立3PASS/Main route28，source实际26全预检，candidate仅本次3runtime旧SHA，其他23保留；两host共10runtime/helper已按旧SHAguard部署并备份，manifest/cwdimports/SourceGate过。原“不得启动”已被此部署更新取代；唯一必要修后场40 exec71445进行中，不重复启动。原WAV/图复用，正式新题NUD→REZ，固定答WEX→NUD应由真实SDK诚实评；尚无最终真实结论/新账本，mic/capture/loopback禁、speaker用户4%。详phase28报告。


## 当前阶段28收尾与下一步

阶段28已部署并完成真实场40：同批次纯评分尾句未取消原评分，QA5→6恰一正式成绩、旧五QA保留、原ASR全文写入，20项链路检查通过且Native转述本次wrong0/NUD→REZ；“答反了”措辞不准确，教学语义PARTIAL。日常AUTO_GRADE默认OFF，物理可听/human未验；原39FAIL保留。下一步修具体错误解释与短答风格，继续语言/记忆/源码/指示及全部A–F。

exec71445 exit0/cleanup[]，任务三端口无listener，无待轮询host。ledger706/2000、app70/null、tech0/0同原round；不使用mic/capture/loopback，speaker仅用户4%不调。两host实际10runtime/helper旧SHAguard部署、manifest/cwdimports/SourceGate通过；Main route28、intent15+1权限skip、phrase20，independent迁移3；ordinary18/19的1旧TARGETS断言已独立确认在d87a26e存在。场40原件SHA356f05bd...875c84ab，17正PCM/926280bytes及sourceEnded，speechend→PCM10.952024秒不等于物理可听；short-answer-tail-review及phase28报告详载。

下一步：精确审查/发布本轮allowlist后，修“选错连接被说成反向”的具体错误解释，再沿plan A–F连续推进；不重跑本轮已过链、不擅自开daily AUTO、不改原用户历史。当前仅此教学措辞局部缺陷，无全局阻塞或complete依据。


阶段28发布确认：14个精确allowlist文件（8脚本/测试、host manifest、5记录）已review/commit/push `7118f5eab9f6ff3ba107e293dde5a4a7c716ad0b` 到codex/daily-learning-companion，remote同SHA、candidate clean、master仍f1e8f3f5605659f0526e43bc3b85c60ae46c85fb。Root index未stage，脏树/.workbuddy/原历史保留；raw/录音/DB/密钥未提交。全契约SHA仍FD518311...84C33。无待轮询进程，账本706/70/0原round。阶段28是实际progress（源码/部署/真实40窄链闭合与准确措辞缺陷证据），不是等待或Goal完成。下一次先读四文件；从现有prompt_templates.py的STUDY answer评估规则及llm_prompts.build_answer_evaluate_messages接续，约束基于真实材料的具体错因、篇幅/语言，再A–F；无需重复40或重建Goal。
