# 阶段25：真实 Native 自动正式评分集成（真实集成证据已取得）

上一轮阶段24为progress：实际源码/部署默认OFF、17离线+12普通handoff+20phrase回归及功能分支发布；不是Goal完成。当前Goal active，无全局阻塞。

本轮已增加accepted/grade_complete/relay_written实际连接与时刻记录，不含答题文本；19本地回归通过。完整两host副本30文件幂等/AST通过。升级最初遇到material normalizer不识别精确阶段24 helper变体，现仅接受已知精确插入，未知改动仍拒绝，新负例通过。实际旧SHA核后部署trace/defaultOFF、SourceGate通过。

现有voice_probe只验explain不覆盖grade；新增grade-current专用场、prepare-grade-quiz显式一次准备，强制output-only/单固定WAV/已有任务及材料、拒mixed/原daily/无provenance；5项实际main AST preflight通过。独立helper grade_snapshot/grade_acceptance及10项正负例已交付待Main复核。独立审发现baseline坏但readpin合法仍开Native的P2，已加baseline.ok及四身份/graded状态全等，不重试。

准备本场仅复用原任务C32及已存材料，必要创建一道正式新题作为本场前置；不修改或重置原用户daily历史，不重新提交图片或制作架构图。既有wrong-WAV的原始ASR全文无法从bounded trace恢复，为新的显式评分意图回归一次离线合成固定文本WAV（SHA 8badfbaee37ccf5f567bce3e71182f6005ca19b9897b987bb80f6ad0eab45276，14.005s）；SAPI文件输出、CreateNew，不播放、不启mic/capture。不是以重建图片替代真实材料。

真实场尚未启动：账本核DeepSeek677/2000、app63/null、tech0/0，round bargein-autocheck-20261012不重置；单场超时/异常停止/no-retry保留。speaker仅用户已设4%必要输出，不改音量，无房间/虚拟mic、捕获设备或loopback。原失败不覆盖；后续真实模型、Native PCM与播放schedule、设备可听、human分层。

下一步：核量具与actual schema/old-token从未接PCM的边界，复审后仅一次真实固定WAV；失败具体记录并转其他工作，完整A–F继续。

场36已terminal/exit1/cleanup_errors=[]，无Native连接/播放。真实quiz已成功保存pending题；observer错误要求rich study_quiz没有的ok字段而提前报FAIL，原raw保留SHA 8ce4ed6f033630c53c3521042c86b965f9e095c224974104554da89b8ad1f048。修为实际tool/非error/非degraded/题干双ID非空、补真实receipt第6前检，Main6PASS。只此新题DS+1至678，app63/tech0不变；旧QA2仍在。下一场37明确不prepare-grade-quiz，复用已保存qid/aid，启动前只读pin同36结果/未评分已核，不重出题、不重置历史，不重复未修服务场。当前无host listener，政策不变。

## 场37真实结果与原失败边界

实际原Native语音ASR→Core accepted claim→原正式SDK/Study/DeepSeek→原SQLite：同course/session/question_id/attempt_id，新增恰1条QA和answer_evaluate，wrong/0；原两QA完整行hash及旧grade interaction公开投影不变，2→3。原ASR全文与QA.user_answer/interaction.input_text逐字相同。输入四ID在首次实际音频固定，actual accepted/grade_complete同connection1/scope2，受控relay为connection2/scope4、真实lanlan_app_gemini。原生模型同时在accepted后0.388s发study_answer调用，仍只有一条正式成绩；实际去重而非重复评分。

正式结果完成后取消原physical token，受控新连接仅一次、无PCM replay。全部11 Native PCM来自新token，存在真实playback schedule与source_ended/active=false/remainingSeconds0。fresh renderer累计frames从0到11，完整trace只有11新token音频，旧token从未收到PCM；这是没有旧queue可播放的证据，不冒充已经停止旧可听声音。8API output-only installed/locked、fixed input capture_started=false，fake input/room mic/capture/loopback/volume change均false。没有物理回环或本人听感证明。

场37原脚本exit1/FAIL_OR_PARTIAL，唯一formal_identity_and_asr失败：量具误把qa_records.question当纯题干，实际Store存储完整held题JSON。不是题目/ASR身份真实不符。已修仅投影question/qid/aid，保留原完整row hash；JSON错ID/非法JSON不能退化成plain绕过，新增真实Store形态测试。Main及Agent13项过，原raw37只读复算19checks全部True。派生文件另建，原FAIL及SHA完整保留，未再请求模型/重启重复场。因此证据为真实子链路+原始记录修量具后的只读复核通过，不追认原进程exit0。

Main语义核查：本任务A课实际submitted_image解码SHA256 057d5bac5ae440dfa0d3269f5138f1188fa182bc0fce81435676c6a4caa65dcc，与已有diagram-input-forward.png逐字节相同。查看该既有图明确WEX→NUD→REZ。题目只问WEX出发的箭头，回答“完全无连接”判wrong0合理；正式反馈和Native两句“起点WEX、终点NUD”正确、无额外出题。未重新制作材料、未修改Sky Scout。Native screenshot可见实际avatar，未据此冒称材料窗口可见性/人类声音验收。

## 时间、额度与收尾

本场speech end→观察ASR 9.031s；accepted→正式grade完成4.713s；grade完成→受控relay written0.611s；relay written→首Native PCM3.208s；首PCM→播放schedule0.537s；speech end→首PCM17.555s。ASR观察比后台accepted晚约7ms属于前后端观察边界，不能硬当服务识别耗时。最大前段包括phrase封口、上传/服务识别及回调，不把9.031s全部归为模型。schedule不是物理扬声器可听时刻。

场36 DS+1已保存必要新题；场37 DS+7/app+2（初始+一次受控relay连接）。阶段总677→685/2000，app63→65/null，tech0/0，round未变。请求数非账单金额。未为了额度或修量具再跑一次相同场；其它额外请求归因尚待，不能声称7次都是评分调用。

场37handle25285 terminal/exit1/cleanup_errors=[]；场36 handle17592 terminal；48911/48916/9234实查无listener。任务coreApi已恢复deepseek，Study偏好及cfg.language前后相同；未接触原daily学习DB/config。所有本轮声音仅output-only允许出口，speaker仍用户4%不调节，mic/capture/loopback未开。原日常默认仍AUTO_GRADE OFF。

原件与派生（只在ignored raw，不发布音频/学习DB/完整题目）：
- daily-companion-20261015-native-grade37.json SHA256 c8484c5ed76bfdca348c43c42dbc605c1020bcdc78814ffca66196a4a81e9035，原FAIL保留。
- daily-companion-20261015-native-grade37-rechecked.json SHA256 709a91cad5cb74a4cdaf1ad234b531694baf4bd8393a091011fc8573cc3073d8，19checks只读复核，全真仍限定Native及SQLite。

## 继续方向

接下来优先同题Native明确纠正：复用此wrong题和原错答，不重新出题；核新attempt/正确成绩/旧wrong行不变，再看默认入口启用范围。当前validator仅普通pending回答，不直接拿它套correction假通过。legacy speech_active=None/PCM replay/歧义input pin仍failclosed；自然短答、连续追问/转课、语言术语/响应前段优化及其余A–F继续。SOURCE/OFFLINE、真实模型/SQLite、Native PCM和schedule分别有以上证据；物理可听、真人体验仍PENDING。Goal active，不局部complete。
