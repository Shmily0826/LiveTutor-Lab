# 日常学习伙伴局部问题（阶段52后，未全局阻塞）

完整任务以[原始 contract](daily-companion-contract-2026-10-14.md)全文为准，不摘要替代、不修改；169行，SHA256 `FD518311C0B3FAFBE038B2BBD83D8EB0DE8986212BCB4B86FCCAB22464084C33`。Goal `01a13531-0341-7611-afc2-5c472a7ccf50` active，完整A–F不缩范围、不因局部失败结束。沿用户指定模型，不擅自换模型。

每次压缩或自动续跑先完整读取 contract、plan、status、blockers，再读当前阶段报告；后续明确指令优先并同步记录。完成依据实际交付和证据；SOURCE/OFFLINE、真实模型/SQLite、Native接收排程、设备可听、真人体验分别记录，旧FAIL/PARTIAL不追改。

## 当前局部缺陷与恢复条件

| 项目 | 当前证据、已尝试与恢复方向 |
|---|---|
| B 自然停顿/晚尾 | 真实语音场51完整PCM已写仍2ASR；phrase压零不解决代理端分轮，默认phrase/AUTO OFF。旧MANUAL未有完整endpoint关闭ACK，不能冒已支持/永不支持。free registry supports_independent_asr=false；虽有faster_whisper缓存，不翻flag冒接通。停止同输入无效重试；核代理协议或已有适配，期间推进C/D/E/F。 |
| D 源码推理质量 | 59值/键混淆、cap3与DSML失败；50定位/51过滤/52输出分开修。61输出完整但30/100反例错，且无条件泛化“值交换过校验”、偏长/加stars。通用guidance并未解决。下一53查现有教学/Focus/校验及实际调用，不硬编码Sky答案，不重复付费场。材料范围须在fresh场问题中明确。 |
| A/E 完整UI与指示 | 受控HTML/图/源码指示、材料重开已有窄证；47真实task初始页面仍Refreshing/未证明完整asyncReady和真实task点击。48同任务profile两次无Translate popup不是所有Chrome永久保证。任意桌面定位未证明；继续受控表面和位置更新，不冒全桌面支持。 |
| C 范围与身份 | SDK场52旧真实bounded-history穷尽否定失败保留；SDK场53定向两句召回只补窄证，不追改旧场。登记精确别名/绑定优先已有source/offline，未知自由语义/旧多ID不猜合；跨题模型评分等余证继续，不另建记忆系统。 |
| F 陈旧UI夹具 | 旧product-ui.test.cjs在修改前已缺$id，临时stub又缺studyMaterialRevision；尝试已撤销，不冒整套UI测试PASS。后续维护真实夹具，不能因此停全Goal。 |
| 证据/人工 | 首PCM/Native queued不等于可听或真人；当前没有新设备/真人通过。旧真人麦克风授权不延续，成熟后一次集中10–20分钟，用户重新明确准备好了才采真人输入。speaker必要仅4%，当前静音、禁capture/loopback。 |

## 操作边界

沿原账本bargein-autocheck-20261012，最新862/2000、app78/null、tech0/0，不重置/换轮/换付费供应商。限流退避并停止无效重试；局部失败写清证据、尝试、恢复条件后继续其它任务。没有需要同一外部条件才能推进的全局阻塞，不将困难/待人工/单项失败标全局blocked。六目录删除审批拒绝不绕过，保留用户数据及无关脏改动。

所有本场owned进程和端口已清，无等待中的live handle。下一步可自主做53本地分析；完整状态与证据见[status](daily-companion-status-2026-10-14.md)。

精简前完整原bytes历史已独占归档：[through52](evidence/daily-companion-blockers-history-through-phase52-2026-10-15.md)，SHA256 `e58d1570ef6c1c07ef2a904e503f39f9ec50d0571d8c12f01ab2db09387531f2`。历史原件不改；原contract不变。旧档相对链接按原docs位置理解。
