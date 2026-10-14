# 日常学习伙伴执行计划（2026-10-15，阶段29收尾）

完整契约：[原文](daily-companion-contract-2026-10-14.md)，169行，SHA256 `FD518311C0B3FAFBE038B2BBD83D8EB0DE8986212BCB4B86FCCAB22464084C33`，未修改。每次上下文压缩或自动续跑先完整读取 contract、plan、status、blockers；后续用户明确指令优先，同步更新记录。Goal `01a13531-0341-7611-afc2-5c472a7ccf50` 当前实查 active，不重建、不局部标完成；完成依据实际交付和证据。局部阻塞记录失败/尝试/恢复条件，转其他任务；限流停止无效重试并退避。

当前权限：必要扬声器仅用户已设约4%，不调整音量；禁止房间/物理/虚拟麦克风、捕获设备初始化和回环。已结束真人场的mic授权不延续。固定WAV只走文件→内存/WS，真实发声必须output-only及8API捕获保护；文字child `NEKO_TASK_SILENT=1`。不夜间要求本人朗读；再次集中真人体验待核心可用及本人明确在场。

账本沿用 `bargein-autocheck-20261012` 不重置/换轮：最新实查 DeepSeek **720/2000**、Lanlan.app **70/null**、Lanlan.tech **0/0**；仅Main调整额度和安排在线。无其他付费供应商；连接有界超时/异常停止/退避，不无限重连，不为耗额度测试。请求计数非账单金额。

允许项目必要修改/隔离依赖、自有测试进程清理；保留Root脏树/.workbuddy/原历史。仅审查过allowlist commit/push `codex/`功能分支，不合并主分支、不强推/覆远端；排除密钥、用户DB、raw音频与无关修改。已有两个子Agent窄范围不冲突，无新增或换模型；Sky Scout源码/索引/已有架构图只读，复用已有两对比图。复用原SQLite和CodeGraph，不另建记忆/索引系统。

源码/离线、真实模型/SQLite、Native接收与播放调度、物理可听、真人体验分别报告；不能用日志/排程冒充可听或本人认可。当前人工不再逐句协助；自动验证到可用后一次约10–20分钟集中体验。

## 当前方向

上一轮阶段28是progress：代码7118f5e/元数据107d76e已发布，真实40单次评分/原ASR/本次转述闭合但教学“答反了”措辞PARTIAL。本轮阶段29继续取得真实失败并修复，未重跑28链；原Goal active，不缩成单项prompt目标。

1. 收尾阶段29：具体错误类型、语义等价短答、时间副词与当前图指代、拒绝保存偏好和持久请求的区别。Main/独立源码及离线验证，真实41/42/43见status；最终肯定reminder收紧仅源码/离线，不能冒充重跑实时。
2. 下一实质阶段优先C/D知识指导相关性：41 relation/arrows材料的knowledge_guidance错配为英语从句；QA topic实际一致为course::有向关系，不能混为掌握度已经散裂。先复用knowledge_graph_guidance.match_topics/_query_terms做离线精确复现，检查泛词“连接/从”及subject证据；证据不足允许不推荐，不推无关课，不重建CodeGraph或记忆库、不改旧成绩。
3. 再完成日常启用范围和连续集成：固定入口/当前材料可见、自然追问/正式成绩、换材料换课与重启、语言/术语/失败恢复。daily AUTO_GRADE仍OFF，严格legacy/no-pin限制有待日常范围策略，不能为demo放松身份或假造pending。
4. 自动验证到核心可用后，再一次10–20分钟集中human。当前不要求本人逐句，不采mic/capture/loopback；必要speaker仅已设4%。局部失败切其他可行任务，不能结束整个Goal。

| 全契约范围 | 剩余要求与证据方向 |
|---|---|
| A 日常入口/材料 | 固定数据配置/课程、初次引导/就绪/失败信息；图片便捷入口与正确替换/换课、Study vision接角色声音、密集小字诚实边界。阶段19固定入口与22当前图DOM已有证据，未改变不重验；本人可见性留最终体验。 |
| B 语音/教学 | 中英/一次切换/课程记忆、自然停顿与普通打断、术语数字代码口语、输入/ASR/工具/音频/播放延迟；简短耐心、承接追问、无证据坦白、纠正后重看。29补静音文字语言，不外推语音中英体验。 |
| C 长期学习 | 原题/错答/更正、返课/重启、相关历史实际取用、既有SQLite四项明确长期偏好与临时区分、概念身份；不建第二套系统。23/26/28已有正式成绩与保留证据，29课语言/4QA重启，指导相关性待修。 |
| D 真实源码 | 既有CodeGraph/授权Sky结构、调用、行、影响；索引和源码版本/引用范围、事实vs推断，不反复整仓；Sky源码/索引只读。Root无.codegraph，Sky定位先现有CodeGraph。 |
| E 屏幕指示 | 受控HTML/图片/源码目标内指点与移动/缩放/滚动过期处理、换材料退役；开源实现/适配/许可记录继承。任意桌面范围诚实限定，只指示、学习者操作。 |
| F 集成交付 | 多轮、换材料/课、重启、网络失败恢复；启动/范围/已知问题/发布记录/体验步骤，默认简短耐心愿纠错；复杂人格后置。实际可听/真人未验不冒PASS。 |

## 交接

阶段29代码/记录正在精确allowlist封版，最终发布SHA见status末段；已发布最新阶段28为7118f5e/107d76e。无running host/exec需轮询，账本720/70/0。Root脏master/index空/.workbuddy/原历史保留，managed codex/daily-learning-companion，master不合并/不强推。

精简前本plan原bytes已独占归档 `docs/evidence/daily-companion-plan-history-through-phase28-and-phase29-start-2026-10-15.md` SHA `6d542e0f7249e1af70ed6f9fecf35234791abae9173b5cbc59021fa9cdc734c8`。所有更早归档和四份最初报告由该历史全文接续保留；旧额度/失败不能自动当当前，不从头重做已验收基线。contract原文169行及SHA不变。


阶段29发布确认：12精确allowlist文件（2源码/1测试/1manifest、3当前记录、2证据、3原bytes历史档）已审查commit/push `f9a2e5520e0a9a4fb3db3eb388afad4281caafa9` 到codex/daily-learning-companion，remote同SHA、candidate clean，master仍f1e8f3f5605659f0526e43bc3b85c60ae46c85fb。Root index空/脏树及.workbuddy/原历史保留，raw/录音/DB/密钥未入Git；contract原SHA未变。无live host/exec待轮询，ledger720/70/0不重置。当前轮属于progress：源码/清单/部署/离线及改变下一步的真实41–43证据，非verified wait或完成。Goal active/all A–F继续；下轮先四文件，优先既有knowledge_graph_guidance.match_topics/_query_terms相关性，不重跑已过3评分/42重启/43切换，不建新系统。
