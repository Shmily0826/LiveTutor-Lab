# 阶段34：真实连续出题与评分


阶段33发布已核：ae248a14c23048150294c710fec147f0069c6416 已push codex/daily-learning-companion，10精确allowlist，publisher clean，remote master仍f1e8f3f5605659f0526e43bc3b85c60ae46c85fb，Root index空。阶段34正准备唯一必要真实连续场47：全新task-owned speech-acceptance store，复用原forward PNG；既有C32保留evaluated题，41保留8QA历史（其早期JSON题缺qid/aid，现grade_snapshot保守拒绝），不清空/改造旧题为pending。通过现有Study image/session/preferences setup建立新课，随后Native内实际出题→自己的自然答案→非答题追问；不在Native前preparequiz。新3fixed WAV由Huihui直接exclusive文件流生成，无播放/捕获。

新增grade-chain观测复用原单成绩严格receipt，逐轮保存SQL/Native snapshot；first/third也核ASR/正PCM/turnend/sourceended回执，不以reply/count冒通过，两次实际delivery需完整written/result/同generation。Main preflight9/acceptance25本地过，独立复核进行中，尚未在线，ledger724/70/0，无live进程。检查器发现的弱证据反例写在continuous-grade-probe-review并收紧，不能把fixturePASS冒真实学习。真实场准备命令与结果待阶段34报告。


阶段34场47已启动（exec42404，尚非结果）：独立最终preflight9/acceptance25 PASS、两量具P2关闭；probe16cc4bbc406516e49e2f8591ac0118108ee48b4a8de3742ab41fbb7463f07dbd、acceptance7608015d33cc67048991156e42697426e2e895592a6f0dd906f94b5187e77be1。唯一命令neko_daily_voice_probe.py --store neko-daily-speech-acceptance-20261015-47 --output benchmarks/raw/evidence/daily-companion-20261015-continuous47.json --output-only --phrase-input --speech-gate --grade-chain --prepare-picture --verify-picture-state --teaching-wav [daily-continuous-quiz47/answer47/followup47.wav]。三文件Huihui仅exclusive WaveStream合成，8.476/4.058/9.026秒，SHA b65720996f8f25184e9b776169378502ae5b508e6e580bfa2a8d351f5a0ecf40 / d0d21ac5f74f8e77a499818d8c52fb99eeb7ac91730645f31e969e326a781cbf / 9685bbb3db11102e45e85e6475523cf2a28ee9d9f259b069f8f8e38c811b84ff。
沿用原账本起步724/70/0，SOURCE gate/输出权限预核PASS，必要speaker仅用户已设4%不调整，8API捕获保护在renderer启动先验，mic/设备捕获/loopback禁止。单场hold/每轮deadline+owned cleanup，限流异常终止不无效重连。需等同一exec终结并核raw/SQLite/实际conn/Native排程和cleanup后记录账本，不能并行另开场或按已启动冒PASS。


阶段34真实场47终态：exec42404 exit1（连续验收FAIL，不是服务异常），raw SHA256 4e83c318b0f06cff06abca24b59266db5cf23259205cc2db06ec9e82660d4824，finalized true/failure null/cleanup[]；launcher6000及native51488均已不存在，48911/48916/9234无listener。ledger原round DeepSeek724→746/2000（+22计数非金额）、app70→71/null、tech0/0，不重置；不重跑未修线路。

真实通过窄项：新隔离课/原forward图/8捕获API保护、Native前healthyempty、首轮provider study_quiz请求+实际新pending（问WEX出发指向谁），首轮0QA；第二ASR完整“我 的 答 案 是 WEX 指 向 NUD 。”；第三只解释箭头尖端，0QA/原题未变。三次local phrase写入均connection1完整written，不冒providerACK；provider各有audio.delta接收，但三轮Native PCM均0，无播放回执/物理/human证明，原FAIL保留。

实际未过：第二轮未claim/未正式评分，仅确认答案“对吗”，grade_markers空，第二provider study_answer被受控guard拒；连续check仅健康空题/真实出题/出题不grade/追问不添grade四项true，答案链和完整Native语音失败。同conn结构check因没有accepted marker而false，不能反称三次delivery换连接。

定位中：本场[study-material-audio]实际free=True且tts=True/captured=False。Core读pin/claim前置拒use_tts，因此不能仅归咎empty rearm。现host.apply_free_voice_route在launcher前调用，freshstore当时无characters.json就返回error，首次runtime之后才生成默认卡；外部TTS仍禁止，导致有provider音频但无Native排程。Main下一修fresh startup先复用官方默认角色生成再native voice/角色guidance，保留权限。独立另发现第二前缀零输入触发clear，实际_audio.clear无条件poison旧pin；两项必须分开定向offline复现，不能统统放开clear/replay守卫。尚无修后online证据。
