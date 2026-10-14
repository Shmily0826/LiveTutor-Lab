# 日常学习伙伴执行计划（2026-10-15，阶段27）

完整契约：[原文](daily-companion-contract-2026-10-14.md)，169行，SHA256 `FD518311C0B3FAFBE038B2BBD83D8EB0DE8986212BCB4B86FCCAB22464084C33`，未修改。每次上下文压缩或自动续跑先完整读取 contract、plan、status、blockers；后续用户明确指令优先，同步更新记录。Goal `01a13531-0341-7611-afc2-5c472a7ccf50` 当前实查 active，不重建、不局部标完成；完成依据实际交付和证据。局部阻塞记录失败/尝试/恢复条件，转其他任务；限流停止无效重试并退避。

当前权限：必要扬声器仅用户已设约4%，不调整音量；禁止房间/物理/虚拟麦克风、捕获设备初始化和回环。已结束真人场的mic授权不延续。固定WAV只走文件→内存/WS，真实发声必须output-only及8API捕获保护；文字child `NEKO_TASK_SILENT=1`。不夜间要求本人朗读；再次集中真人体验待核心可用及本人明确在场。

账本沿用 `bargein-autocheck-20261012` 不重置/换轮：最新实查 DeepSeek **699/2000**、Lanlan.app **68/null**、Lanlan.tech **0/0**；仅Main调整额度和安排在线。无其他付费供应商；连接有界超时/异常停止/退避，不无限重连，不为耗额度测试。请求计数非账单金额。

允许项目必要修改/隔离依赖、自有测试进程清理；保留Root脏树/.workbuddy/原历史。仅审查过allowlist commit/push `codex/`功能分支，不合并主分支、不强推/覆远端；排除密钥、用户DB、raw音频与无关修改。已有两个子Agent窄范围不冲突，无新增或换模型；Sky Scout源码/索引/已有架构图只读，复用已有两对比图。复用原SQLite和CodeGraph，不另建记忆/索引系统。

源码/离线、真实模型/SQLite、Native接收与播放调度、物理可听、真人体验分别报告；不能用日志/排程冒充可听或本人认可。当前人工不再逐句协助；自动验证到可用后一次约10–20分钟集中体验。

## 当前顺序（阶段27末）

1. 新真实场39短答暴露分段FAIL：provider把同一已完整写入phrase拆成“当前题+我的答案是WEX指向NUD”和“点评分”，没有Core claim，provider两次study_answer只存一QA，但Native说旧“已经评分”。原FAIL保留，不重复未修在线。优先成套修明确声明准入与后续同批次纯请求的scope/事务归属，不能只加regex、shield旧owner或拼接未知内容。
2. 12项/Main独立分段诊断、原37/38只读v2已过；需用39真实事件做离线Core/SDK/SQLite/新有声PCM/换题/连接反例，review/部署清单后才必要修后单场。日常AUTO_GRADE仍OFF。
3. 延迟定位：长输入写完→accepted7.790/9.290s，短输入首ASR约4.723s但场39语义FAIL，不能把8.564s错误回复当优化成功。保护自然停顿1.2s和普通打断，未证实协议不乱发commit。
4. 其它完整A–F继续，局部provider分段不等于全局阻塞。核心可用后一次集中human，不逐句占本人时间。

| 契约范围 | 继续验收及剩余工作 |
|---|---|
| A 日常入口/真实材料 | 固定数据配置/课程、就绪与失败信息；当前图可见、换图换课用正确材料、方便图片/指定窗口入口；可靠Study vision接角色声音、密集小字诚实说明。阶段22 current-image窗口已真实DOM过，本人可见性待最终体验。 |
| B 语音/教学 | 中文/英文/单次切换/课程语言记忆；自然停顿与普通打断；术语数字代码口语；输入结束/ASR/工具/音频/播放分段延迟；默认简短、追问、无证据诚实、纠正后重看材料。 |
| C 对话/长期学习 | 当前题/原错答/更正、返课/重启；历史实际取用、既有SQLite四项明确长期偏好与临时区分、概念topic一致。阶段23真实SDK wrong→correct与graded重启，26 Native纠正；更宽连续与相关历史仍待。 |
| D 源码教学 | 复用授权Sky/既有CodeGraph：结构/调用流程/行含义/改动影响；索引版本、源码引用范围、工具选择和事实/推断，不全仓反复读。Sky只读，源代码定位先CodeGraph。 |
| E 屏幕指示 | 目标窗口代码/模块/关系指点；受控HTML/image/source先交付，滚动缩放/移动后的定位及旧版本退休；开源源码/适配/许可证证据继承；任意桌面范围诚实限定，只指示、学习者操作。 |
| F 集成/交付 | 多轮、换材料/课、重启、网络失败恢复；启动方式、支持/已知问题/发布/体验步骤；简短耐心愿纠错基础风格；复杂人格后置。最终10–20分钟human，未验不冒PASS。 |

阶段25代码已发布35abae0/元数据39f98ba；阶段26代码/量具/证据已精确发布`3016a30a8910f6e21efbf63c6b94725f276b87f4`（12 allowlist文件）。当前正确题在C32任务，下一步只读基于现状态，不能重新造pending/重置历史。详细身份/原件/时延/进程见status和phase26证据。

## 历史承接

精简前plan原bytes独占归档：`docs/evidence/daily-companion-plan-history-through-phase25-and-phase26-preflight-2026-10-15.md`，SHA256 `d8a3694ecaf0e466f3d05a920dd1aa2621215b613ece26d3aeb8e38b0508f210`。此前phase18/16/14/12/10/8及human档保留。旧失败和额度是历史，不能自动当当前；四份最初报告及已过基线不从头重跑。

阶段27启动前：既有phrase/grade自动分段诊断已source修及Main/独立12tests，两个诊断P2已闭；preflight8/完成7过。37/38原件不变，v2只读派生确认写完→accepted7.790/9.290s、Core比provider观察仅约3ms，保护1.2s停顿。必要一场短6.438s固定输入39将复用C32原图，因原题correct通过原Study生成新题而不改历史。SourceGate/output-only已过；本轮尚无新host/调用，ledger691/67/0，mic/capture/loopback仍禁、speaker用户4%。详phase27报告；Goal active/all A–F保留。

阶段27场39收尾：exec11085 terminal/exit1/cleanup[]，任务48911/48916/9234无listener，无live场需轮询。原raw39 SHA3199f88767ef1eec3d6e73c04663d6bc71c3d49af400e09bbf1ef726413180e0，实际一个完整109782sample phrase、两个ASR、provider两次study_answer、QA4→5 current correct100及旧四QA hash保留，但没有Core grade markers，Native错误复述旧“已经评分”。新QA来自provider简写，不是完整逐字ASR；helper后续未执行false不等于实际捕获失败，八API实installed/locked且mic/capture/loopback/volumechange全false。真实偏好/语言相同，task provider恢复deepseek。账本699/2000、app68/null、tech0/0同round，+8DS/+1app，不把全DS当评分。

下一轮先四文件，从phase27末段/latency-review的真实分段缺陷续：首段明确“当前题+我的答案是...”的准入和后段scope/事务必须成套，保护新PCM/换题/连接、未知修饰不拼接；单改regex后第二ASR会retire旧task，禁止复活owner。优先离线actual Core/SDK/SQLite回放再必要有界修后场；当前没有新的runtime修复/默认启用，余A–F持续。旧阶段25/26成功及37/38原FAIL/derived都保留，不外推39。
