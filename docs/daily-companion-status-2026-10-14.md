# 日常学习伙伴当前状态（2026-10-15，阶段29收尾）

本轮实际progress：修具体错因和语义等价短答；解决时间副词误选图片、拒绝保存被误作长期语言。真实43中文→默认英文、42正确短答100及重启/4QA保持取得证据。原40措辞PARTIAL、41原FAIL/partial60、42临时语言FAIL均保留，不追认。Goal active，全部A–F未完成。

完整契约：[原文](daily-companion-contract-2026-10-14.md)，169行，SHA256 `FD518311C0B3FAFBE038B2BBD83D8EB0DE8986212BCB4B86FCCAB22464084C33`，未修改。每次上下文压缩或自动续跑先完整读取 contract、plan、status、blockers；后续用户明确指令优先，同步更新记录。Goal `01a13531-0341-7611-afc2-5c472a7ccf50` 当前实查 active，不重建、不局部标完成；完成依据实际交付和证据。局部阻塞记录失败/尝试/恢复条件，转其他任务；限流停止无效重试并退避。

当前权限：必要扬声器仅用户已设约4%，不调整音量；禁止房间/物理/虚拟麦克风、捕获设备初始化和回环。已结束真人场的mic授权不延续。固定WAV只走文件→内存/WS，真实发声必须output-only及8API捕获保护；文字child `NEKO_TASK_SILENT=1`。不夜间要求本人朗读；再次集中真人体验待核心可用及本人明确在场。

账本沿用 `bargein-autocheck-20261012` 不重置/换轮：最新实查 DeepSeek **720/2000**、Lanlan.app **70/null**、Lanlan.tech **0/0**；仅Main调整额度和安排在线。无其他付费供应商；连接有界超时/异常停止/退避，不无限重连，不为耗额度测试。请求计数非账单金额。

允许项目必要修改/隔离依赖、自有测试进程清理；保留Root脏树/.workbuddy/原历史。仅审查过allowlist commit/push `codex/`功能分支，不合并主分支、不强推/覆远端；排除密钥、用户DB、raw音频与无关修改。已有两个子Agent窄范围不冲突，无新增或换模型；Sky Scout源码/索引/已有架构图只读，复用已有两对比图。复用原SQLite和CodeGraph，不另建记忆/索引系统。

源码/离线、真实模型/SQLite、Native接收与播放调度、物理可听、真人体验分别报告；不能用日志/排程冒充可听或本人认可。当前人工不再逐句协助；自动验证到可用后一次约10–20分钟集中体验。

## 阶段29实际结果

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
