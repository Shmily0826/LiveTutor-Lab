# 阶段28：明确短答分段修复已部署；真实链通过、教学措辞仍待修

上一轮阶段27为progress：延迟分段代码bf355bc/记录d87a26e已发布，必要场39取得改变下一步的真实FAIL；不是verified wait。继续原Goal和全部A–F，未重建/暂停。原39/旧37–38及其派生均保留。本轮目前没有host、模型或声音会话，账本实核699/2000、app68/null、tech0/0，同bargein-autocheck-20261012不重置；mic/capture/loopback继续禁，必要speaker只用户4%不调。

## 当前候选源码

复用原Core/SDK/SQLite和既有grade claim，不建新记忆/事务系统、不伪造provider utterance或复活owner。

- 原保守answer_intent默认不变；只有Core已验证的首次实际输入receipt及pending pin才开启allow_declared_answer。仅完整“当前题，我的答案是/我的回答为...”声明可省judge；引用/假设/他人/否定/新题/问答案及无内容仍拒。实际39首段可进入原正式entry，原ASR全文保留，不用provider改写答案。
- 实际NativePhraseUplink.flush的现有delivery只新增真实input_sequence。首次_take捕获sealed_phrase要求真实driver/snapshot当前、waiting tuple seq等于frames、完整write/conn匹配。保留driver/delivery对象及epoch。provider response.done可以清waiting，首次origin之后Core仍可在旧owner当前时识别同一本地输入的纯请求；之后waiting若非None仍必须同seq。不能在尾句阶段重新捡一个report当origin。
- ASR completed在任何scope推进之前调用仅Core绑定的同步callback；必须literal True才跳过，async/回调异常False。Core核旧owner、ws/conn/scope/token/activation/socket/frames、没有新pin、原driver/report/epoch、当前数据库四身份、原grade task未取消（含cancelling）/失败、3秒内且仅一次。只吞精确“请评分/点评分/请打分/评分/打分”，不吞改答案/否定/未知文本。原wire trace保留，独立study-grade-tail日志不加进三marker链；诊断日志失败不改变有效scope。
- 新正DSP帧的pin和sequence在首await前改变，所以立即使尾句路径失效；scope按原协议退休旧任务。旧scope从未改写或重生。原成绩/转述仍用原工具、去重、hold和一次受控无PCM重连，新语音优先。

## 已有离线证据与边界

Main27 route tests通过：实际Core/SDK/SQLite/arbiter方法，加实际completed-ASR scope前缀（外层接收/模型/连接/UI替身），实际NativePhraseUplink.note_boundary在两ASR之间清waiting后仍只保留原scope、两provider call一QA/一模型调用、原ASR逐字保存及一次受控relay。新pin-only早return、实际正帧sequence、否定/改答原scope取消、cancelling未done、期限/一次、copied delivery/epoch/foreignwaiting/换题/foreignprovider、callback truthy/async/异常、logger异常均有反例。不能说这是实际网络/设备通过。

Main intent16run：15PASS、1 Windows symlink1314权限skip；现有14项基线加2声明/尾句规则，原question-pin readonly/硬链接/锁/变换不放宽。独立Agent27/16(1skip)/phrase20已过并修闭first-origin和日志异常两个P2，报告short-answer-tail-review；最后的全回放重复bundle清理增量还待最终补审。

旧测试只逐段UPGRADES字符串替换会重复注入旧完整helper，已改为实际canonical patcher在临时文件回放。现有部署manifest所认可的tool_calling.py本来有两个完全相同grade-aware material HELPER bundle，单元旧“只有一份”的假设与当前不符。normalizer仅删除exact重复、保留最后同实现；未知/相似编辑不删。全30临时回放又定位older replay会重新插入exact pre-grade bundle，已补final material normalizer（与现有transport final normalize一致），已知grade bundle存在时去exact plain副本。新增exact duplicate/mixed/idempotence及unknown拒绝测试。原实际runtime尚未写入，旧manifest fingerprints保留。

局限明确：仅有声明首段授权后，未知迟到ASR中的否定/改答案走原退休路径，但若SDK已提交不能倒删成绩；本修复不声称解决所有语义分段或完整意图合并。不擅自拼ASR、设provider协议身份或调低1.2s停顿保护。当前中文窄声明政策不外推所有英文/裸标识符短答。日常AUTO_GRADE仍默认OFF。

## 当前部署门禁与下一步

**尚不可启动新宿主**：Root四个runtime helper源码已改而manifest仍旧SHA；真实两个host完全未改，需先全30文件临时回放/幂等/AST和single-helper计数、独立最终审，再按旧manifest逐文件hash预检后部署新canonical/两个helper副本，更新清单并验实际cwd imports/SourceGate。一次临时回放因manifest包含无patch目标的utils/dev_text_only.py而提前退出，量具已区分静态文件；随后真实发现older replay重插bundle，正在封版，不是线上失败，无原数据改写。

之后必要修后单场复用原6.438秒short WAV/原图；原39题correct不能改pending，若需新题只能正式出题，不重复未修online。修后真实ASR/QA/Native/物理/human继续分层，旧39保持FAIL。源码/部署完成后精确codex分支发布，排除raw/音频/DB/密钥，不动master/Root index/.workbuddy；任何局部问题继续其它A–F。


## 部署已完成；真实场40进行中

最终state迁移P2已补且独立3项通过；Main route28 PASS、intent15PASS/1symlink权限skip、phrase20 PASS。额外ordinary行为18PASS，旧TARGETS数量断言1FAIL：独立git show已确认发布d87a26e也15targets但测试硬编码10，早于本轮，未称全套PASS，未扩大本轮修复。

全manifest实际26文件临时canonical回放/AST/幂等/单helper通过（先前“30”是误计，以实际26为准），只有transport/session_lifecycle/tool_calling三文件改变。candidate与source有8项既有差异及缺source-only utils/dev_text_only.py；不能套source全清单。candidate只核本次三runtime旧SHA与清单相同，余23项明确排除保留。双host三deployed helpers旧SHA全部核过，再保存独占旧bytes备份，更新本次每host三runtime+两个helper，共10文件。manifest同步三runtime和四helper源码SHA，双host实际cwd imports、SourceGate通过。raw部署预检/deployed及backup均在phase28私有证据下，不入Git。

仅Main启动必要修后场40，唯一exec71445；output-only、八API前置、复用原short WAV SHA16cd7764...，不使用mic/capture/loopback、不改用户4%音量。沿用C32原图/原数据，原题correct后通过实际Study_quiz出新题，没有伪造pending。新题问NUD出发箭头（NUD→REZ），原固定输入仍WEX→NUD，因此本场不能预设correct；应诚实评分本次答错并只存一次/读本次成绩。原39FAIL不改。结果未完成，不能称真实修复PASS；进程/最终账本待场终结核对。


## 场40终结与证据分层

唯一exec71445正常exit0、failure无、finalized=true、cleanup_errors=[]；48911/48916/9234已核无listener，没有live host/observer需轮询。原件 `benchmarks/raw/evidence/daily-companion-20261015-native-short40.json` SHA256 `356f05bd564a629a9b0c96ade307f6629d1afe7a8e1c4a82acaef380875c84ab`，不覆写。20项grade_acceptance全部真，result仍为CANDIDATE_GRADE_FLOW_PASS_REQUIRES_SEMANTIC_REVIEW。

实际provider两ASR（1791995791.307 / 5792.888），Core首次accepted5791.311655、同conn1/scope2的一次pure-request-tail consumed，grade_complete5794.259898，没有被尾句退役；relay conn2/scope4 5794.826198。QA5→6，同qid q_c63123a8483b4c54b019d4a9757cd358/aid a_141f81a9a7ed455fb983fd9c23749f56，原五QA row SHA及旧formal投影保持，正式恰一新增；user_answer逐字为“当 前 题 , 我 的 答 案 是 WEX 指 向 NUD 。”，没有使用provider缩写。新wrong0/reference NUD→REZ，topic同course::关系对照图。旧39真实FAIL不追认。

17个正PCM共926280bytes、另1个0byte边界，新token、grade后接收并调度，最终source_ended/activefalse/remaining0。8API guard实际installed/readonly/captureBlocked；room mic/capture/loopback/volume_changed全部false。前后实际preferences/config语言/材料同、provider清理恢复deepseek。没有物理回环，不能称实际可听/真人PASS。

时延：speech end→accepted4.388678s；→NativeASR4.395024s；→seal1.260290s；写9.557ms；写完→accepted3.118832s；grade2.948243s；grade→relay0.566300s；relay→PCM3.048802s；PCM→schedule0.512000s；speech end→PCM10.952024s、→schedule11.464024s。短答和较长场37/38输入长度/题目不同，不能把全部差异归此次修复或承诺稳定10.95秒。未改1.2s自然停顿/ordinary barge-in。

Main重新查看既有forward图：WEX→NUD→REZ；本题NUD出发、固定答WEX→NUD，判wrong及正确答案有据，Native已引用本次结果，没有旧“已经评分”。但反馈开头“你答反了”及misconceptions“方向说反了”不准确：这是答成相邻另一箭头，不是反向。结论为**真实评分/去重/转述链PASS；教学措辞PARTIAL**，不能把20checks全真当完整语义PASS。下一步应从已有评估prompt约束要求只给材料支持的具体错误类型、区别选错连接与方向反转，并保证不固执；无需重跑已过短答链。

账本同bargein-autocheck-20261012，DS699→706/2000（+7，总请求不等于全评分）、app68→70/null（+2初始+受控relay）、tech0/0；无重置/改限/换provider。Goal active，A–F继续、daily AUTO_GRADE默认OFF，未知迟到改答的语义合并未解决、四语言/历史/源码与受控指示范围/集成交付仍按plan推进；human待核心可用后集中一次。阶段28发布待精确allowlist同步，不提交raw/音频/DB/密钥。


阶段28发布确认：14个精确allowlist文件（8脚本/测试、host manifest、5记录）已review/commit/push `7118f5eab9f6ff3ba107e293dde5a4a7c716ad0b` 到codex/daily-learning-companion，remote同SHA、candidate clean、master仍f1e8f3f5605659f0526e43bc3b85c60ae46c85fb。Root index未stage，脏树/.workbuddy/原历史保留；raw/录音/DB/密钥未提交。全契约SHA仍FD518311...84C33。无待轮询进程，账本706/70/0原round。阶段28是实际progress（源码/部署/真实40窄链闭合与准确措辞缺陷证据），不是等待或Goal完成。下一次先读四文件；从现有prompt_templates.py的STUDY answer评估规则及llm_prompts.build_answer_evaluate_messages接续，约束基于真实材料的具体错因、篇幅/语言，再A–F；无需重复40或重建Goal。
