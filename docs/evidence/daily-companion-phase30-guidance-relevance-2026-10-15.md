# 阶段30：无关自动指导已修复；概念身份与诊断一致性仍待修

先读contract/plan/status/blockers；上一轮29为progress（代码f9a2e55/记录2aa46cc、真实41–43改变下一步），原Goal active，全A–F不缩。账本实核720/2000、app70/null、tech0/0，同bargein-autocheck-20261012不重置；本轮静音本地，未开host/外部模型/声音/设备。Sky只读，不建新知识/记忆/CodeGraph系统，不改旧QA/掌握度。

## 已实复现

实际41问句“已有关系对照图的两条连接是WEX→NUD、NUD→REZ。从NUD出发的那条箭头，起点和终点分别是什么？”在现有820seed中首配english_senior_clause_connection，score28/topic_specific18/matched连接、从，build payload也选英语从句。原因：query拆出孤立从被当明确主题词给18，且非explain路径直接采用未资格过滤的首排名；explain已有specific>=10保护，评分/出题没有。QA本来仍一致course::有向关系，不能冒称已分裂。

## 候选源码与离线

knowledge_graph_guidance仅改匹配证据：长query拆出的单CJK字排除（单字完整query可保留）；完整label/alias须在原query中存在、ASCII有identifier边界，不从拼接ngram伪造名字；topic_specific只完整label/alias/ID或标签/别名内完整Latin词，不把泛词只因独立空格就当完整主题。公共模糊排名仍可供主动搜索；自动指导不因模糊片段强推课。

entry_tutor_context_support的non-explain复用既有specific>=10资格，未匹配直接空guidance/not_matched；已匹配用同一ID生成subgraph，避免payload再次选回weak首项。显式selected topic原路径保持，既有semanticroute/subject限制保持。

最初全收紧导致已有BFS缩写测试FAIL，因seed完整标签是“图的BFS与DFS”且无aliases；补完整Latin token保留BFS而非放回任意中文片段。现有test_knowledge_topic_routing扩展实际方法/820seed：answer/question拒绝41问句与从/连接/泛词，保留真实English标签/BFS/显式选择、alias BFS vs BFSx、单字力 exact vs能力；原Flutter generic同学科噪音、拓扑排序、HTTP alias仍过。Main离线通过，provider_calls0；独立审查待。未造新图或改Sky。

## 门禁与下一步

两source已改、product manifest/default deployed还旧版，不启动直到oldSHAguard同步/独立review。只需一条必要真实SDK文字验证本次non-explain指导上下文移除与原4QA保留，不重跑29语言/28音频链，不借源码/离线称真实PASS。异常停止/记录原run，不无限重试；所有音频/捕获/回环保持关。


## 新增当前证据：概念身份英译分散

部署预检只读实际C41数据库发现：原41三个QA均course::有向关系，但42新增第4条为同course::directed relations。四QA历史hash保持不等于概念身份保持；先前“topic一致”的证据仅限41三条，不能外推42或当前全部。两个名字来自同一题干、预期连接和概念，存在中英切换后身份分散，须按C继续修复。没有合并/改写任何旧QA/掌握度；本阶段先完成guidance相关性后，将此作为下一优先，复用现有question/topic/SQLite身份，不建新翻译或记忆系统。需要后续核实际题目身份/源码归属，不能凭英译词猜全库合并。


阶段30部署更新：独立source/offline审查通过，无P1/P2，820seed现有assert suite通过（不是820单独验收）。两default产品代码已oldSHAguard备份同步，29manifest sourcehash与host SourceGate过。此前“勿启动”门禁已满足；唯一必要静音SDK场44 exec57025进行中，复用C41任务/同原41问句，只检查新的评分指导资格和旧4QA保留，不复跑29语言或28音频。未完成前不宣称真实通过/新账本。


## 场44真实静音SDK终结

唯一exec57025 terminal exit0、probe finalized=true/failure无/cleanup error无，owned host主动终止host_exit=1，不能写全部进程exit0；48911/48916/9234无listener。原件 `benchmarks/raw/evidence/daily-companion-20261015-guidance44.json` SHA `f4ec30fc5bea8926e76809e66658e2c49043e76e0a1a183f3d78cba88ecc19ba`，不覆写。actual部署两SHA与本轮审查相同，SDK /runs调用原41同题/同答案/同预期，实际模型wrong0，给NUD→REZ正确参考。

10项Main readonly检查全部literalTrue：guidance_applied=false/statusnot_matched/emptyfocus/emptyrelated/no public payload，QA4→5单新增/原4全rowhash保留、formal单新增/旧formalhash保持、course和saved语言映射保持。source调用路径只在matched时附加model/public context，离线验证+实际API输出共同证明本轮弱query不再强推英语从句；不能称所有语义相关性或每个seed全通过。公共搜索/显式选题范围保留离线证据，非此单场在线覆盖。

实际反馈“你回答的是WEX→NUD，但题目问NUD出发...NUD→REZ”与misconceptions指出入边误当出边，语义有据；但step_feedback最后仍说“起点和终点正好相反”，相邻两条边不是同端点反转，故**本轮guide资格/保存链PASS，整体教学诊断仍PARTIAL**。原41/42/40的类似失败不追认。本轮不再改prompt反复花额度碰运气；后续B须处理跨字段诊断一致性。

新增QA5 topic为course::有向关系图中的起点与终点，QA1..3为course::有向关系，QA4为course::directed relations；同一题干/同预期，三个同义identity已真实观察。原旧history未改，下一优先C复用既有question/expected-answer/material/course证据稳定新记录归属，不能按中英词盲合全库或删旧成绩。既有Agent正在窄读实际归属路径，是否仅directSDK无heldID或Native同样受影响待核。

同时44实际grade回复是中文，storedcourseEnglish未变，但本场未像42先走study_session.set_course；因此“语言映射保持”只指持久数据，不能当directentry重启自动语言应用已验收。先登记B/C直接entry范围，不能外推用户日常所有入口。43中英切换已过不因该单场读条映射就重测。

账本720→721/2000（+1总DS）、app70/null/tech0/0不变，同round/同上限，不重置/不换provider；无avatar/声音/mic/capture/loopback，非ASR/Native/实际可听/human证据。全29productmanifest sourcehash及host SourceGate通过，default两代码旧SHAguard同步/独占backup；本轮自有进程全部已收尾，Goal active，全A–F继续，局部新失败不结束Goal。


独立收尾：guidance-relevance-review已复核44原SHA/10checks及底层notmatched/no payload、QA/formal4→5和旧hash、字段诊断PARTIAL，未改原件/未重试模型。concept-identity-investigation已完成只读源码+既有8断言/纯AST反例：_track_learning无稳定selected/held topic时取模型label，已有::scoped key绕过拼写canonical；同qid/aid但无topic也会分散，非仅匿名SDK。下一步先在原question/topic体系中、模型await前绑定证据支持的稳定selected/held topic，复用既有SQLite；匿名同题只在course/question/expected/material唯一历史身份有据时复用，已有三identity不任挑一个/不改旧成绩。跨题概念翻译不冒同题provenance，完整建议/边界见调查报告。局部失败不结束A–F Goal。当前本轮源码/默认部署/清单/离线/真实44窄链已完成，待精确发布SHA确认。
