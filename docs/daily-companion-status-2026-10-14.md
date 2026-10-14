# 日常学习伙伴当前状态（2026-10-15，阶段31收尾）

当前阶段31实际progress：未来同题学习归属12离线+既有31项相关回归通过；真实SDK45两评分/中间重启、旧5QA/mastery/formal/FSRS保持，新增2QA与2mastery使用同一question-scope ID，仅增1张FSRS。两次结果wrong0→correct100，当前反馈正确区分相邻边；旧44跨字段失败仍保留。ledger723/70/0，exec7769终态0、owned launcher10200/8640已不存在/端口无listener；无声音/avatar/mic/capture/loopback。directSDK保存English却回复中文仍未修。Goal active/all A–F保留；发布SHA及独立原件复核见末段。

阶段30实际progress：自动评分/出题指导不再将关系图泛词强配英语从句；离线820seed回归/Main及独立审、真实44静音SDK指导与单次保存链通过。整体仍PARTIAL：44分步反馈错误反向诊断、同题QA已三名字，以及directentry语言应用范围待修；未修改旧成绩。Goal active/all A–F保留。

完整契约：[原文](daily-companion-contract-2026-10-14.md)，169行，SHA256 `FD518311C0B3FAFBE038B2BBD83D8EB0DE8986212BCB4B86FCCAB22464084C33`，未修改。每次上下文压缩或自动续跑先完整读取 contract、plan、status、blockers；后续用户明确指令优先，同步更新记录。Goal `01a13531-0341-7611-afc2-5c472a7ccf50` 当前实查 active，不重建、不局部标完成；完成依据实际交付和证据。局部阻塞记录失败/尝试/恢复条件，转其他任务；限流停止无效重试并退避。

当前权限：必要扬声器仅用户已设约4%，不调整音量；禁止房间/物理/虚拟麦克风、捕获设备初始化和回环。已结束真人场的mic授权不延续。固定WAV只走文件→内存/WS，真实发声必须output-only及8API捕获保护；文字child `NEKO_TASK_SILENT=1`。不夜间要求本人朗读；再次集中真人体验待核心可用及本人明确在场。

账本沿用 `bargein-autocheck-20261012` 不重置/换轮：最新实查 DeepSeek **723/2000**、Lanlan.app **70/null**、Lanlan.tech **0/0**；仅Main调整额度和安排在线。无其他付费供应商；连接有界超时/异常停止/退避，不无限重连，不为耗额度测试。请求计数非账单金额。

允许项目必要修改/隔离依赖、自有测试进程清理；保留Root脏树/.workbuddy/原历史。仅审查过allowlist commit/push `codex/`功能分支，不合并主分支、不强推/覆远端；排除密钥、用户DB、raw音频与无关修改。已有两个子Agent窄范围不冲突，无新增或换模型；Sky Scout源码/索引/已有架构图只读，复用已有两对比图。复用原SQLite和CodeGraph，不另建记忆/索引系统。

源码/离线、真实模型/SQLite、Native接收与播放调度、物理可听、真人体验分别报告；不能用日志/排程冒充可听或本人认可。当前人工不再逐句协助；自动验证到可用后一次约10–20分钟集中体验。

## 历史阶段29实际结果

- 仅canonical prompt新增4b/4c，无固定节点硬编码/输出后处理/篡改分数；avatar复用明确视觉指代保护，时间词不丢弃显式notes；语言解析仅移除明确拒绝保存偏好子句，真以后/always仍交课程语言工具。最终防“不要忘记以后…”肯定reminder的规则只source/offline，没有新增付费复跑。
- Main language6通过；独立最终补审见specific-error-review。此前material guard25 Main/独立通过，涵盖图片替换/旧摘要/身份/排队/拒图/literal边界；最终只语言parser更改，不重跑未变图片保护。发布代码/清单default plugin-code两文件旧SHAguard同步，旧代码私有独占备份，无学习DB修改；host SourceGate和两default代码bytes匹配过。一处inline检查漏scripts导入路径先ModuleNotFound，随后补路径只读检查过，没有因此启动新host。
- 场41原件SHA `f36545263ab5dd4bb726de0264935b79d676566faf56209f6dfebdefd63f3867`：相邻边/真反向都wrong0且区分准确；正确“NUD指向REZ”被partial60，只因没复述起点，原失败保留。英文两句后，临时中文被误visualmissing拒、停止。5个总DS请求，未做后续重启。
- 场42原件SHA `26610cdee7ef9002b8ad35bd981e43d06833b2ba340b7d9f0a772f5f761df218`：同正确答案correct100，原3QA完整hash保留、QA3→4；临时中文不再缺图但仍英文（“不要保存长期偏好”触发旧scope词）；两host重启/返课英文设置及4QA全保留、defaultEnglish两句。exit0只是执行终结，语言语义FAIL保留。
- 场43原件SHA `d26ba02a523033a0d48d82e2ee1bbbd8a10b22ead50ade9990c3624a0af95f77`：相同完整中文请求得到两句中文（NUD→REZ）；下一请求两句英文；courseEnglish/4QA完整hash在前后相同。最终reminder收紧发生在43之后，只离线反例覆盖；43不当作该新增反例实时证据。
- 上述全静音HTTP/SDK文字路径，没有avatar/音频/设备/回环，不能当ASR、Native声音、物理可听或真人PASS。41/42/43均finalized、owned host退出/无cleanup error，无需重试/轮询；任务端口48911/48916/9234无listener。
- 总账本706→720DS（+14是总调用，不等于全评分），app70不变、tech0。请求计数不是账单；无重置/换轮/预算变动/其他付费provider。

## 继承边界与下一步

阶段28真实40单正式grade/旧5QA保留/原ASR/尾句处理/本次角色转述、新17正PCM+调度终结已证；原39FAIL不覆。37/38旧raw checker FAIL及只读派生结论保留。阶段23正式wrong→correct与graded重启、22当前图窗口、19固定入口已有证据；具体历史见本次归档和各phase报告，不从头复验。

当前新增局部问题：41实际knowledge_guidance把关系图匹配英语从句（泛词连接/从）；QA topic却一致为course::有向关系。下一轮先定位既有match_topics/query词和学科证据，不把guidance错误归为QA掌握度已经散裂，不重建系统、不改旧记录。随后继续完整plan A–F日常入口/连续集成、最后一次集中human。

Root dirty master/index空、.workbuddy保留；managed `C:/Users/Shmily/.codex/worktrees/daily-companion/LiveTutor-Lab`，codex/daily-learning-companion。阶段29未完成发布时不冒SHA，末段更新为准。既有screen_guidance窄审，learning_memory容量失败冻结，不换模型/不新增agent。六空目录清理曾automatic approval blocked by policy，未绕过。

精简前status全文独占归档 `docs/evidence/daily-companion-status-history-through-phase28-and-phase29-start-2026-10-15.md` SHA `10e82b662d1f08afc9c12afc4a4a1c1ea00010f8b494af8aafe97dbc36b426b6`，所有旧证据/已验基线/额度历史继续保留。contract未经修改。


阶段29发布确认：12精确allowlist文件（2源码/1测试/1manifest、3当前记录、2证据、3原bytes历史档）已审查commit/push `f9a2e5520e0a9a4fb3db3eb388afad4281caafa9` 到codex/daily-learning-companion，remote同SHA、candidate clean，master仍f1e8f3f5605659f0526e43bc3b85c60ae46c85fb。Root index空/脏树及.workbuddy/原历史保留，raw/录音/DB/密钥未入Git；contract原SHA未变。无live host/exec待轮询，ledger720/70/0不重置。当前轮属于progress：源码/清单/部署/离线及改变下一步的真实41–43证据，非verified wait或完成。Goal active/all A–F继续；下轮先四文件，优先既有knowledge_graph_guidance.match_topics/_query_terms相关性，不重跑已过3评分/42重启/43切换，不建新系统。


阶段30开发：41问句的820seed错配已离线exact复现；两source修主题证据/非explain资格/同ID subgraph，既有+新增topic routing离线过。product manifest/default尚旧，勿启动；独立review后旧SHAguard，再必要一条静音SDK验证。ledger720/70/0无变化、无host；不重复29语言或28声链。详phase30-guidance-relevance。


阶段30新只读证据：41三QA topic原为有向关系，42第4同题语义答转成directed relations，历史hash保持≠概念身份保持。未改旧记录；完成本阶段guide错课修复后，下一优先C同概念跨语言身份复用。先前41topic一致不外推当前四条。详phase30报告。


阶段30部署更新：独立source/offline审查通过，无P1/P2，820seed现有assert suite通过（不是820单独验收）。两default产品代码已oldSHAguard备份同步，29manifest sourcehash与host SourceGate过。此前“勿启动”门禁已满足；唯一必要静音SDK场44 exec57025进行中，复用C41任务/同原41问句，只检查新的评分指导资格和旧4QA保留，不复跑29语言或28音频。未完成前不宣称真实通过/新账本。


## 当前阶段30终结

真实44唯一exec57025已terminal exit0/无cleanup error/host主动终止1，任务端口无listener，无live场待轮询。guide链10结构checks及Main事实核通过，QA4→5/旧4与formal保持，rawSHAf4ec30fc...ecc19ba；教学诊断整体PARTIAL，三topic身份和directentry语言为下一项。ledger721/70/0，原round不重置。阶段30报告含完整SHA与证明范围，独立review封版后精确codex分支发布；不重复29切换或28声音，先读四文件续完整A–F。


独立收尾：guidance-relevance-review已复核44原SHA/10checks及底层notmatched/no payload、QA/formal4→5和旧hash、字段诊断PARTIAL，未改原件/未重试模型。concept-identity-investigation已完成只读源码+既有8断言/纯AST反例：_track_learning无稳定selected/held topic时取模型label，已有::scoped key绕过拼写canonical；同qid/aid但无topic也会分散，非仅匿名SDK。下一步先在原question/topic体系中、模型await前绑定证据支持的稳定selected/held topic，复用既有SQLite；匿名同题只在course/question/expected/material唯一历史身份有据时复用，已有三identity不任挑一个/不改旧成绩。跨题概念翻译不冒同题provenance，完整建议/边界见调查报告。局部失败不结束A–F Goal。当前本轮源码/默认部署/清单/离线/真实44窄链已完成，待精确发布SHA确认。


阶段30发布确认：10精确allowlist文件（2源码/1测试/1manifest、3当前记录、3证据调查）已review/commit/push `f8a21cf1893265cde83d22d63c7d2e33bf46bf53` 到codex/daily-learning-companion，remote同SHA/candidate clean/master仍f1e8f3f5605659f0526e43bc3b85c60ae46c85fb。Root index空/脏树/.workbuddy/原历史保留，raw/录音/DB/密钥未提交；contract原SHA不变。无live场/host待轮询，ledger721/70/0原round。当前轮progress（源码/默认部署/离线/真实44窄链及改变下一步的C/B失败证据），非等待或Goal完成。下轮先四文件，再读concept-identity-investigation接续已有_track_learning/_record_answer_knowledge/held topic选择链，优先稳定后续同题归属；原已三identity不能任挑/合并旧行，不建新系统。所有A–F持续，语言cfg与诊断一致性仍待修；不复跑已过指导/29语言/28声链。


阶段31启动：稳定新评分的同题学习归属，复用question/QA/topic/internal_private_payload，不改旧历史。先固定已有topic/唯一有据历史；无identity或歧义时明确provisional同题归属，不猜跨语概念等价。ledger721/70/0，无host，静音；测试/独立审/旧SHA部署后才必要模型。详phase31-question-topic。


阶段31进展：固定未来同题归属已实现于四既有source，Main新12离线过；既有材料14/身份4/重启3/重试10过。独立审发现known foreign scoped runtime空family被接受，已改仅known seed namespace可带非course前缀，新增正负例过；未动旧数据。明确supplied full材料scope纳入key，普通文本仍不偷读当前图。probe补真实interactions比较及恰+2mastery，不用空all冒PASS。独立终审待完成；default/manifest仍旧，禁止launch。ledger721/70/0，无host/在线。


阶段31部署门禁更新：独立终审关闭known foreign空family P2，最终12/12及此前材料14/14过，无其余具体P1/P2阻断。四reviewed后端文件已逐一oldSHA校验、独占备份到benchmarks/raw/evidence/daily-companion-20261015-phase31-before并同步default；29canonical manifest SHA及期望default指纹/host SourceGate过。首次总核误以static/index.html应等canonical，实际manifest已有protected_html转换/固定protected SHA；未改HTML或绕保护，补量具按既定转换SHA核验，source与deployed分别记录。无host/新模型，ledger721/70/0。probe小门禁补审后仅两实际SDK grade/一次重启，复用原5QA，不制造pending；其余已过链不复跑。


阶段31独立终审：45原件14checks已逐字段复算（非仅读flags），QA/mastery5→6→7、formal10→11→12、FSRS3→4→4，原全row保持；两新QA跨不同session仍同完整key/topic，newscope question，旧三identity不合。wrong0入边误选出边/正确100反馈窄链成立，两回复中文，English仅持久设置保留。四source/default/清单及12新/31既有离线通过；ledger723/70/0，无live场/host。新增--text-only防护只source审，不重复付费/不冒45flag运行证明。下一阶段先B directSDK语言cfg应用，再跨字段诊断/全A–F连续集成；当前待精确codex分支发布，不标Goal complete。


阶段31发布确认：12精确allowlist文件（4产品source/1manifest、2隔离测试脚本、3当前记录、2证据）已review/commit/push `92ec265a3773a4cabf5c7e5c88925e4fbf633302` 到codex/daily-learning-companion，remote同SHA/candidate clean/master仍f1e8f3f5605659f0526e43bc3b85c60ae46c85fb。Root index空/脏树/.workbuddy/原历史保留，raw/录音/DB/密钥未入Git；contract原169行/SHA不变。独立45底层14checks过，旧5QA/旧掌握与复习行保持，实际同题未来归属跨restart稳定；这是progress，不是整体完成。ledger723/2000/app70/null/tech0/0原round，无live exec/host需轮询。下轮先完整四文件，再从study_avatar_tools._study_effective_language和__init__._start_study_session_locked接续B直接入口语言应用，已知savedEnglish/实际Chinese，不大范围重扫或复跑31身份/30指导/29语言/28声音。临时语言仍只单轮，课程/全局回退需防前课语言残留；保存映射与实际prompt/回复分别验证。全A–F继续，任一局部缺陷不结束Goal。
