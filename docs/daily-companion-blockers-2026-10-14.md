# 日常学习伙伴局部问题（阶段53后，未全局阻塞）

完整任务以[原始 contract](daily-companion-contract-2026-10-14.md)全文为准，不摘要替代、不修改；169行，SHA256 `FD518311C0B3FAFBE038B2BBD83D8EB0DE8986212BCB4B86FCCAB22464084C33`。Goal `01a13531-0341-7611-afc2-5c472a7ccf50` active，完整A–F不缩范围、不因局部失败结束。沿用户指定模型，不擅自换模型。

每次压缩或自动续跑先完整读取 contract、plan、status、blockers，再读当前阶段报告；后续明确指令优先并同步记录。完成依据实际交付和证据；SOURCE/OFFLINE、真实模型/SQLite、Native接收排程、设备可听、真人体验分别记录，旧FAIL/PARTIAL不追改。

## 当前局部缺陷与恢复条件

| 项目 | 当前证据、已尝试与恢复方向 |
|---|---|
| B 自然停顿/晚尾 | 真实语音场51完整PCM已写仍2ASR；phrase压零不解决代理端分轮，默认phrase/AUTO OFF。旧MANUAL未有完整endpoint关闭ACK，不能冒已支持/永不支持。free registry supports_independent_asr=false；虽有faster_whisper缓存，不翻flag冒接通。停止同输入无效重试；核代理协议或已有适配，期间推进C/D/E/F。 |
| D 源码推理质量 | 59值/键混淆、cap3与DSML失败；50定位/51过滤/52输出分开修。61输出完整但30/100反例错，且无条件泛化“值交换过校验”、偏长/加stars。通用guidance并未解决。53即时Focus+明确材料62数值/拒错窄PASS，不能追改61；风格仍多句/口头禅，下一54修短答并推进UI，不硬编码Sky答案、不重复同数值场。材料范围须在fresh场问题中明确。 |
| A/E 完整UI与指示 | 受控HTML/图/源码指示、材料重开已有窄证；47真实task初始页面仍Refreshing/未证明完整asyncReady和真实task点击。48同任务profile两次无Translate popup不是所有Chrome永久保证。任意桌面定位未证明；继续受控表面和位置更新，不冒全桌面支持。 |
| C 范围与身份 | SDK场52旧真实bounded-history穷尽否定失败保留；SDK场53定向两句召回只补窄证，不追改旧场。登记精确别名/绑定优先已有source/offline，未知自由语义/旧多ID不猜合；跨题模型评分等余证继续，不另建记忆系统。 |
| F 陈旧UI夹具 | 旧product-ui.test.cjs在修改前已缺$id，临时stub又缺studyMaterialRevision；尝试已撤销，不冒整套UI测试PASS。后续维护真实夹具，不能因此停全Goal。 |
| 证据/人工 | 首PCM/Native queued不等于可听或真人；当前没有新设备/真人通过。旧真人麦克风授权不延续，成熟后一次集中10–20分钟，用户重新明确准备好了才采真人输入。speaker必要仅4%，当前静音、禁capture/loopback。 |

## 操作边界

沿原账本bargein-autocheck-20261012，最新868/2000、app78/null、tech0/0，不重置/换轮/换付费供应商。限流退避并停止无效重试；局部失败写清证据、尝试、恢复条件后继续其它任务。没有需要同一外部条件才能推进的全局阻塞，不将困难/待人工/单项失败标全局blocked。六目录删除审批拒绝不绕过，保留用户数据及无关脏改动。

所有本场owned进程和端口已清，无等待中的live handle。下一步可自主做54风格/集成本地工作；完整状态与证据见[status](daily-companion-status-2026-10-14.md)。

精简前完整原bytes历史已独占归档：[through52](evidence/daily-companion-blockers-history-through-phase52-2026-10-15.md)，SHA256 `e58d1570ef6c1c07ef2a904e503f39f9ec50d0571d8c12f01ab2db09387531f2`。历史原件不改；原contract不变。旧档相对链接按原docs位置理解。

阶段53开始：52源码8d9bf21+完整归档/精简metadata808f98a已发布为progress，原账本862/78/0/无live场。61按自身时间窗日志实核两轮regular，question信号分别None/0.3，当前FocusScorer复杂度只读上一轮master reading；不是已经证明唯一质量根因。复用现Focus question信号，对用户当前明确源码解释/影响/校验请求加入即时信号，仍经core全局及focusCognitionEnabled用户开关/滞回/上限，不换模型/provider、不改emotion逻辑；不从屏幕或隐藏prompt打分。先本地正反例/关闭开关检查，部署和协议核对后仅一场必要验证。

阶段53开发冻结：8新离线+4原scorer/question checks PASS，共12不同case，不计重复；actual source scorer SHA185044e52bae217757ee10dd273779eeb94fac820fcc18d94b8e07150f96e1d1、host manifest SHA7804da9efaccc9d255d8256a6be329da898999465975d0bd41db53c81833bd00、SourceGate PASS。当前明确源码推理为既有question信号1.0，仍合并其它信号、受现阈值/情绪/开关/滞回/硬顶，不保证所有语义/所有自定义阈值进入。只支持现中英cue与列举源码扩展名，纯读/无需推理不加此信号。62 fresh场两问显式材料范围、两个数值例子与错误纠正，既有量具仅在本进程替换问题，无源码预取/新图。原862/78/0/同deepseek-flash、text-only/TASK_SILENT、380s与32事件间停止/2000总顶，不mic/声音/capture/loopback；目标均不存在/三端口空，随后启动，未终态不冒模型通过。

阶段53唯一静音真实62已启动exec94567；只poll同handle，不因观察超时重启。尚未终态，不冒实际启用/质量/清理通过；没有Native/浏览器/设备/捕获。

53真实62终态：原raw SHA08212f3ed0442d1f7796493091cee4455a64159d6d4b0f70bea71ed6e7823ce6，terminal另件 SHA80a56f6e4e5a081a6c0d11f6375bc623819a9e9e543510d983074826fbd732f0，原semantics=PENDING保留，Main另件判核心窄PASS/风格PARTIAL。两轮11.572/5.423s，DeepSeek862→868恰6/app78不变，实际CodeGraph commit7aae20f；坐标guard/route/client均有shown，第二轮再次读guard。两个数值例子按原合法输入对调，100超过lat90→400早return，40/30有限且范围合法→调用fetchWeather，未说下游必成功；被用户错误纠正时按实际guard拒绝，不固执维护原错。第二答却“不同意”后追加嗯/喵/重复结论共4句，第一答“后面成不成这两句不管”语气欠耐心；不把句数/基础风格冒通过。

当前场time-window仅提取两条Focus诊断（12:06:38/49）均question1.0、score0.60、charge0.6/0.9、modefocus，各有focus_thinking事件；与source registry/overrides相符，不保存/打印推理链，也不冒完整HTTP body wire capture。问题同时比61增加明确文件范围和数值例子，不能将改善全归因推理开关，也不是性能对照实验。传输无failure/cleanup/tracker错误；controller0，host1是owned forced-stop，全部owned已死/48911、48916、9234无listener，post62 SourceGate PASS；无Native/浏览器/设备/真人新证明。12=新8+原scorer4，同suite重跑不重复计数；offline raw SHA352155f5540dc116b99b273ef85900b35c4c8656f6a1ed7a931c0690d030fb51。

接续边界：53的即时Focus只改实际source离线文字brain路径，不能据此认领free Native Realtime的源码口语同样改善。D语音仍需复用已有Study教师/授权CodeGraph与朗读桥接后验证；不能把文字路径当最终日常语音交付。54先处理角色风格与F UI入口/夹具，随后继续此集成，不因62核心窄PASS收缩A–F。
