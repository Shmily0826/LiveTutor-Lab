# 日常学习伙伴局部阻塞与缺陷（2026-10-15，阶段29收尾）

完整契约：[原文](daily-companion-contract-2026-10-14.md)，169行，SHA256 `FD518311C0B3FAFBE038B2BBD83D8EB0DE8986212BCB4B86FCCAB22464084C33`，未修改。每次上下文压缩或自动续跑先完整读取 contract、plan、status、blockers；后续用户明确指令优先，同步更新记录。Goal `01a13531-0341-7611-afc2-5c472a7ccf50` 当前实查 active，不重建、不局部标完成；完成依据实际交付和证据。局部阻塞记录失败/尝试/恢复条件，转其他任务；限流停止无效重试并退避。

当前权限：必要扬声器仅用户已设约4%，不调整音量；禁止房间/物理/虚拟麦克风、捕获设备初始化和回环。已结束真人场的mic授权不延续。固定WAV只走文件→内存/WS，真实发声必须output-only及8API捕获保护；文字child `NEKO_TASK_SILENT=1`。不夜间要求本人朗读；再次集中真人体验待核心可用及本人明确在场。

账本沿用 `bargein-autocheck-20261012` 不重置/换轮：最新实查 DeepSeek **720/2000**、Lanlan.app **70/null**、Lanlan.tech **0/0**；仅Main调整额度和安排在线。无其他付费供应商；连接有界超时/异常停止/退避，不无限重连，不为耗额度测试。请求计数非账单金额。

允许项目必要修改/隔离依赖、自有测试进程清理；保留Root脏树/.workbuddy/原历史。仅审查过allowlist commit/push `codex/`功能分支，不合并主分支、不强推/覆远端；排除密钥、用户DB、raw音频与无关修改。已有两个子Agent窄范围不冲突，无新增或换模型；Sky Scout源码/索引/已有架构图只读，复用已有两对比图。复用原SQLite和CodeGraph，不另建记忆/索引系统。

源码/离线、真实模型/SQLite、Native接收与播放调度、物理可听、真人体验分别报告；不能用日志/排程冒充可听或本人认可。当前人工不再逐句协助；自动验证到可用后一次约10–20分钟集中体验。

| 当前项 | 权威证据与行动 |
|---|---|
| 指导主题不相关（下一优先） | 41有向关系材料的knowledge_guidance为英语从句，匹配连接/从；QA topic原本一致course::有向关系。复用knowledge_graph_guidance.match_topics/_query_terms定位generic词/subject证据，允许证据不足不推荐，不改旧掌握度/不重建系统。 |
| 日常自动评分范围 | 窄显式中文37/38/40有正式成绩+转述，daily AUTO默认OFF、legacy/no-pin受限；29仅文字语义/语言，不代表日常全面启用或自然所有问法。结合身份和材料，继续连续集成，不能只放松regex/所有消息自动打分。 |
| 真实长响应 | 40短6.438s输入speechend→PCM10.952s（37/38较长约17.6s），题目长度/输入不同，不归因全部源码优化；保留1.2s自然停顿/ordinary barge-in，未证实协议不乱commit，必要时针对新证据优化。 |
| 教学语义/临时语言 | 41/42失败原件保留；修后42正确100/重启，43中文→英文+4QA保持。最终肯定reminder反例source/offline而非新实时。更多题型/术语/数字/语言语音、无证据/纠正后重看仍按全plan，不泛称完结。 |
| 当前材料/屏幕指示 | 22受控当前图DOM已有；29明确视觉指代保护25离线过，真实43仅literal notes不当vision。任意桌面定位支持范围诚实，受控HTML/图片/source指点、滚动缩放和换材料退役继续集成；旧本人看不到图FAIL留human。 |
| 学习历史/源码 | 既有SQLite题/错答/更正/多次重启有局部真实证据，长期四偏好与相关取用/概念一致/CodeGraph结构调用行影响/源码版本引用仍完整范围，不因小项PASS标全Goal。 |
| 设备与human | 未用mic/capture/loopback；29纯文字，28 Native PCM/排程不等于物理可听；旧human80%等Main的组织FAIL保留。核心可用再集中10–20min，mic授权只本人明确在场那次，不自动续。 |
| 旧测试/清理/Agent | ordinary19中18行为过、1旧TARGETS断言在发布d87a26e已失效，不能说19全过；六空目录删除auto approval blocked不绕；learning_memory容量失败冻结，不换模型/新增agent，Main及既有另一窄审继续。 |

无全局阻塞或complete依据；41/42/43均terminal/无cleanup error，任务端口无listener；账本720/70/0。某项目阻塞转其他独立工作，限流停止无效重试。当前已过短答/相邻反向/成绩重启不重复付费测试。

精简前blockers全文独占归档 `docs/evidence/daily-companion-blockers-history-through-phase28-and-phase29-start-2026-10-15.md` SHA `3e15d2650f3398ff39b0bc89cec2c2bc953f553de5e122eecac1a9917b019c26`；更早历史/失败/恢复条件都在归档链保留。原contract169行/SHA不变，不以摘要替代原始任务。


阶段29发布确认：12精确allowlist文件（2源码/1测试/1manifest、3当前记录、2证据、3原bytes历史档）已审查commit/push `f9a2e5520e0a9a4fb3db3eb388afad4281caafa9` 到codex/daily-learning-companion，remote同SHA、candidate clean，master仍f1e8f3f5605659f0526e43bc3b85c60ae46c85fb。Root index空/脏树及.workbuddy/原历史保留，raw/录音/DB/密钥未入Git；contract原SHA未变。无live host/exec待轮询，ledger720/70/0不重置。当前轮属于progress：源码/清单/部署/离线及改变下一步的真实41–43证据，非verified wait或完成。Goal active/all A–F继续；下轮先四文件，优先既有knowledge_graph_guidance.match_topics/_query_terms相关性，不重跑已过3评分/42重启/43切换，不建新系统。
