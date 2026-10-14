# 日常学习伙伴局部阻塞与缺陷（2026-10-15，阶段38已部署，无全局阻塞）

完整原任务：[contract](daily-companion-contract-2026-10-14.md)，原169行/SHA256 FD518311C0B3FAFBE038B2BBD83D8EB0DE8986212BCB4B86FCCAB22464084C33，完整A–F/权限预算/发布验收不以摘要替代、不修改。现有Goal 01a13531-0341-7611-afc2-5c472a7ccf50 active，不重建/擅改模型；小阶段、局部失败、时间或额度不是完成依据。

每次压缩/自动续跑先完整读contract、plan、status、blockers，再最新阶段报告，从明确函数继续，不重新大扫；用户后续明确指令优先并同步记录。局部阻塞记失败/尝试/恢复条件，继续其他可行项；限流停止无效重试/退避。仅全部可自主工作完结或所有余项同一外部条件时汇总全局阻塞。

音频：必要speaker仅用户已设约4%不调整；禁房间/物理/虚拟mic、音频捕获初始化、回环，旧真人场授权不延续。固定WAV仅文件/内存/WS，发声必须已审output-only和8API保护；文字child TASK_SILENT+source/text-only。指定学习窗口/受控页面截图按原授权可用，不采其他窗口。用户不刻意逐句验收，核心可用后一次10–20分钟human，再明确在场授权mic；旧human看不到图/80%等Main组织FAIL保留。

沿用bargein-autocheck-20261012，DS累计上限2000，app null（无限额但单场超时/异常停/退避），tech0；不重置/换轮/其他付费商，不为耗额度测，请求计数非金额。49终态已核785/2000、app74/null、tech0/0；原round不重置。只有Main调额度/安排在线，最多原两个Agent：screen_guidance窄审、learning_memory容量失败冻结，不换模型/新增。

授权必要项目代码/隔离依赖/自有测试进程；保留Root原脏master/空index/.workbuddy/用户历史，不reset/clean/stash/清库；仅精确审查allowlist push codex/功能分支，不合master/强推/覆盖历史，排除密钥/DB/raw录音/无关修改。Sky Scout源码/索引/已有HTML只读，原两对比图复用；既有SQLite/CodeGraph，不另建系统。Root无.codegraph；Sky定位先已有CodeGraph。localhost/受控HTML检查用共享D:/AI/tools/web-inspector/cli.mjs，不装项目Playwright/不查个人Chrome。六空目录清理曾自动拒绝，未绕过。

证据分层：SOURCE/OFFLINE、真实模型/SQLite、Native接收排程、物理可听、human分别写；空帧不算正PCM，发送不算provider ACK。未验收不冒PASS，完成须实际全契约交付及证据。

## 具体局部问题与恢复条件

| 项目 | 当前证据/下一可执行动作 |
|---|---|
| 连续出题→正式答题 | 47题有但ttsTrue拒claim/无PCM；35已修fresh与clear，48ttsFalse/Native音频窄证，但误选explain且题空，中止正确。36prompt消除图片解释/出题冲突，49唯一correct100正式grade/同conn已实证，播报截断与量具环形丢证据待修。尚不能启日常AUTO；失败记录不覆盖、不制造pending。 |
| 其他入口 | active Native typed无ASRclaim被guard拒，direct Study SDK入口可用≠Avatar text/UI端到端。legacy/direct speech_activeNone保守拒；当前Core普通Omni会算bool，不把此前None猜测当缺陷。普通设备场当前禁止mic，留后集中human。 |
| 语言/状态/语义 | 32直接English窄修/同课临时finally并发语言P2 SOURCE关闭；其他共享cfg并发未全验。41 partial60、44邻边误称反向FAIL保留，不能因45/46同题正确就冒所有教学正确。 |
| 概念身份/历史 | 同题未来稳定/跨restart窄过，旧三ID不猜合；跨题概念/相关历史当前使用需继续。41早期8QA JSON缺qid/aid，grade_snapshot保守拒，不改旧史来迎合量具；47–49用新taskstore。 |
| 语音/延迟 | 48只1轮4正PCM/排程，不是物理可听或完整话语质量；40短输入到PCM10.952s不外推全延迟。自然停顿/打断、术语数字、实际中英声音/播放/完整日常多轮待验。 |
| 材料/源码/指示 | 原受控表面/22DOM等继承，密集小字、源码版本/引用、窗口/缩放/滚动定位、材料替换退役继续；任意桌面/本人可见性不冒已过，Sky原码与索引只读。 |
| 外部/人工 | 只必要4% speaker，禁mic/capture/loopback；最终集中human待核心可用及明确在场。Agent容量失败冻结/六目录审批拒绝不绕过；局部问题转其余A–F，不因额度或时间称完成。 |

无全局blocked/complete依据。49 exec30272已terminal、cleanup[]/无live场；默认AUTO OFF，36已发布，下一37修复继续，不重试未修线路。

本次精简前全文按原bytes独占归档[历史](evidence/daily-companion-blockers-history-through-phase35-and-phase36-start-2026-10-15.md)，SHA256 e9a058e4b1a3fef51e58bee6946b4d55a06c391a29d63f8eae1dcbbab9928736；通过原归档链保留全部更早报告/权限/失败，contract未变。


阶段36真实49终态：唯一exec30272 exit1，finalized true/failure null/cleanup[]，launcher14952/native已不存在，48911/48916/9234无listener；raw SHA256 60988217eff6581fa038736e6d6cde71283ca4fb778f808894455c03da3e1148。ledger原round DS757→785/2000（+28计数非金额），app72→74/null（含正式relay一次受控重连），tech0/0。停止未修线路的在线重跑。

实际模型/SQLite窄链PASS：healthyempty首输入→role study_quiz实际生成WEX出发指向谁→同connection1不同完整sealed delivery的自然ASR“我 的 答 案 是 WEX 指 向 NUD 。”→accepted/grade_complete/relay_written三身份一致；新增唯一QA+唯一formal、correct100、题/attempt保持，原ASR完整存。第一0QA，第二1，第三追问后仍1且题未换。baseline本场0QA，旧行保持check属空基线，不能冒原八史重启回归。Core accepted→gradecomplete1.782s、complete→relay0.598s，不是完整语音延迟。controlledconn1→2原token实际cancel/stop、新tokenPCM和排程均有。

完整Native仍PARTIAL：第一6audio_frame=5正/1空；第二6正帧，但Native只转述“答对了：WEX”，正式feedback为“答对了：WEX 是起点，箭头终点是 NUD。”，新token终态speech_cancel而非source_ended，严格20grade checks仅native_terminal false。第三34帧=33正/1空、sourceended/题无误但最终snapshot无当轮ASR/只见回复后段，可能trace环形淘汰，需精确分开量具丢证据与实际截断。continuous checks 5true（健康empty/rolequiz/quiz不grade/前两同conn/追问不改grade），answer_flow与three_completed false，不写全链PASS/物理/HumanPASS。

下一优先：在不再在线下，独立continuous49-review核实际raw，Main精确追answer新token的speech_cancel原因；补probe按轮累积流式Native证据，不能裁历史/重置计数伪造fresh。只有具体修后再必要实测；daily AUTO_GRADE仍OFF，Avatar typed/UI与其余A–F继续，不因该局部失败结束Goal。源码/模型/Native/物理/human层分开，原47/48/49失败均保留。


49独立复核完成（continuous49-review）：Native第二轮172events无淘汰，实际文本确实只“答对了：WEX”；但其169320bytes/6正PCM后，1792003568.559已有同新token source_ended inactive/remaining0，1792003598.567才speech_cancel（晚30.008s）。因此final覆盖造成native_terminal false，不能说该late cancel截断了在播音频；源码30000ms sticky empty-queue fallback高度吻合，未凭时长冒唯一caller原因。短反馈独立仍未解，不能借修量具改整体PASS。

第三轮Native trace真实上限500（不是300），最终正好500且首wall3632.110已晚于wire ASR3623.838/3629.026，明确环形淘汰；最后窗口34frames非本轮累计45，不能将其ASR缺失称未识别，也不能按只剩后段做完整语义验收。原raw保持不重算。

下一阶段37先本地：复用neko_native_telemetry的500ring观测，在既有probe观察循环逐轮积累有本地sequence的events，严格身份/容量/缺号拒绝，保留actual earlier sourceended与其后无新同token PCM的回执，将30s后空队列cleanup单独记诊断；不裁历史/重置binary计数来冒fresh、不把本地seq当provider utterance。新量具不改49原FAIL。另精确追正式reply完整feedback→owned relay文本→provider transcript→Core publish的截断边界（当前不能唯一说模型或UI），必要先无内容的len/hash诊断和离线fixture，先不在线重试/不盲改音频协议。daily AUTO OFF，Avatar typed、其他A–F仍继续。当前无live host/exec，账本785/74/0。


阶段36发布核验：11精确allowlist（1host prompt源码、3当前记录、3原bytes归档、35/36证据与独立复审）已commit/push 2fef51ade29f3087463c811eb87aa870eb0ddd5e 到codex/daily-learning-companion，remote同SHA/publisher clean/master仍f1e8f3f5605659f0526e43bc3b85c60ae46c85fb。Root index空/原脏树/.workbuddy/原学习历史保留；无DB/raw/WAV/密钥/备份入Git，contract169行原SHA不变。完整SourceGate再次PASS，ledger785/2000/app74/null/tech0/0，所有47–49 exec已terminal/自有进程已清理，无live场待轮询。

本轮为progress，现有Goal接口再次确认active/all A–F完整，不暂停/重建/标完成。下次压缩/自动续跑先完整四文件和36/49-review，再从明确37观测/完整转述边界接续，不大扫/不重跑未修线路。下一用户真人测试待核心成熟一次集中组织，当前不需本人朗读。


阶段37启动：上一阶段发布7e3c233c204660b6401a20814896cf256ab08acc以及49实际唯一grade/同conn是progress，不是wait。已完整重读contract/plan/status/blockers，源码及ledger785/74/0当前核对，Root index空/publisher clean，无live exec/host。Main仅本地修量具，不重复付费跑49，不使用任何音频设备。

Main观测草稿5文件：NativeTelemetry原500ring增加严格本地observer_sequence和device remainingSeconds/updatedAt；NativeTraceHistory逐快照积累最多12000events，同安装时间/连续seq/重叠内容/总PCM frames+bytes一致，发现漏轮/重载/容量/计数不一致立即拒绝，不补造事件/不重置binary计数。初始、sessionready、observe都接同History，3轮snapshot保留真实累计历史，仍只task renderer/8API保护，不接管用户Chrome。不是provider utterance/ASR authority。

Native terminal判据保留旧final sourceended；只有新增完整seq/counters历史、实际device sourceended/queue0/正确token/done、后无PCM或文字或active状态，才把后来空队列speech_cancel与已正常结束分开记证据，不允许任意cancel冒正常结束。Main telemetry18+grade acceptance27+preflight9离线PASS（JS真实INSTALL在no-device fixture重放750events、gap/改写/counter/overflow拒、latecancel负例）；独立observation-review进行中。未重算原49，真实新采集/物理/human仍未验。

正式反馈短文本根因UNKNOWN：独立feedback-boundary-review实际AST封装/relay表达式/Omni flush/Core handle/send与真实emotionregex '<(.*?)>'均完整保持22chars/hash，未复刻49异步时序；单delta数量不能证明provider原文短。Main下一补既有WIRE_TRACE受控len/hash边界（reply/实际relay/write/providerreceive/callback/Corepublish/Native），不记正文、不新routing，先offline再考虑唯一必要线上。默认AUTO_GRADE仍OFF，其他A–F和本人集中验收继续；账本不重置。


阶段37完成SOURCE/OFFLINE窄修：6源码/测试文件，Main18 telemetry+27 acceptance+13 probe共58 PASS；独立原18/27未变、13新增重验PASS。独立发现末段observer task异常可吞P2并实际AST复现，已同步failed/ended/error再raise，每轮grace后与最后SDK/截图后fresh capture并前后核task，正常cancel/gather/置None后才end_session；独立closure无剩余具体P1/P2。详evidence/daily-companion-phase37-native-observation-2026-10-15.md及native-observation-review。500ring累积12000有严格sequence/counters/identity，不造证据；正常sourceended后的空队列cancel只在完整证据下分开诊断。
原49/raw/PARTIAL不改，正式22chars而Native7chars的根因UNKNOWN。无模型/Native/浏览器/音频设备调用；账本原round实核DS785/2000、app74/null、tech0/0，无live host/exec。现有Goal active，完整A–F不变，不把本阶段当完成。下一38：仅既有WIRE_TRACE受控len/hash边界诊断（正式结果/relay实际write/provider原始delta/Omni callback/Core queue/WS），先离线，再必要线上；本人集中验收待核心成熟，无需逐句配合。


阶段37发布核对：12精确allowlist已push源码/证据commit 62dfc8a025e92030be4498172a20ddaf65bec1ca；remote codex/daily-learning-companion同SHA，publisher clean，remote master仍f1e8f3f5605659f0526e43bc3b85c60ae46c85fb，Root index空。当前SourceGate全指纹/隔离helper导入再次PASS，无host/设备启动。原contract SHA不变，账本785/74/0。本阶段是progress，Goal active，A–F余项及49 PARTIAL保留。
38定向接续：现有scripts/neko_spoken_turn_patch.py已管理_wire_trace.py的spoken诊断（初始化由launcher调用），可优先复用RealtimeWireTrace，避免另增runtime helper/记忆系统；record_recv的first-delta节流前应记录每个真实delta的无正文长度/hash及实际response/物理generation，不能只记录首delta；Core entry/queue/WS以及实际relay payload应分开hash，按真实边界接入且诊断失败不影响路由。当前尚未修改该实现、manifest或host源码，不凭设计冒已交付；先最小离线/独立review再必要线上，不盲重复49。


阶段38草稿开始（未部署/未发布）：Main新增scripts/neko_study_text_trace_patch.py，并在neko_native_grade_patch.upgrade_targets末尾接入，复用既有RealtimeWireTrace对象，不新增runtime helper/服务。4文件actual Source当前版本复制至temp，canonical replay+AST+幂等均过。加入每delta原始转写/既有5个Omni callback/Core entry+queue+WS/grade_reply/实际序列化relay payload成功本地write的无正文chars/UTF8 SHA；累计最多64已绑定generation+response的流，缺identity/容量不冒完整prefix。
重要：当前只是草稿，neko_native_grade_patch helper SHA已变化而manifest尚旧，SourceGate应拒绝启动；尚未改两host或manifest，也没有任何在线/声音/设备调用。下一先专门离线fixture/原grade route回归、独立review，再审阅oldSHA备份/精确部署/manifest同步；不启动旧gate不符的host、不把37先前SourceGate PASS称38已过。账本785/74/0。


阶段38完成SOURCE/OFFLINE+精确部署：Main7诊断+38grade route+5spoken共50PASS，独立7PASS/无新增具体P1/P2。已有RealtimeWireTrace扩展无正文length/UTF8hash，provider每delta节流前/完整done、formal grade reply、actual serialized relay成功write（bare/envelope分开，非ACK）、5Omni callback、Core entry/queue/WS；Core identity首await前冻结；64有身份流累计，缺失/容量不造prefix。logger异常不会改变路由，缺关键记录仍UNKNOWN。
8个两host各自oldSHA核对/exclusive备份→canonical patch/AST/幂等；candidate与Source旧Core turn差异保留。manifest同步4Source+原grade helper+新trace patch helper；SourceGate源码及实际cwd helper导入PASS，草稿hash不符阻塞已关闭。完整证据evidence/daily-companion-phase38-feedback-trace-2026-10-15.md、feedback-trace-review。无host/Native/API/设备调用，原账本DS785/2000、app74/null、tech0/0；原49/raw/PARTIAL不改，短反馈根因仍UNKNOWN。
下一39：仅一场必要的改进观测固定WAV连续场，用新增真实边界区分模型原始短句与转发丢失，沿原对比材料/47WAV、不预造题，先SourceGate/ledger/自有空端口核对，output-only+8API保护、不mic/capture/loopback，speaker仅用户设4%不调整。失败具体记录并转其他A–F，不无效重连。Goal active/完整contract不变；核心成熟再集中human，不要求逐句配合。
