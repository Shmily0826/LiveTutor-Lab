# B：连续命令与单长句停顿的离线证据复核

日期：2026-10-14，Pacific/Auckland。按当前 contract/plan/status/blockers 接续 active Goal，不重跑MANUAL支持场景、不调整供应商或额度、不修改生产源码。分析只读已有两个JSON、原SAPI WAV及当前driver；原始证据和输入未变。

## 必须收紧的结论

`native-timing.json` 与 `manual-support3.json` 的原生窗口都记录了三条实际输入文本：

1. `Please use the study material tool to check the image I submitted to study.`
2. `Then use the Study explain tool to explain the weather request path in two Chinese sentences.`
3. `No. Quize`（末尾No quiz被识别为这个文本）。

这份材料是三个独立指令，不是一个有未完成从句的长句。第一条完成在全录音结束前约6.45秒，本身不是“单长句被截断”的充分证据；先检查图片，再讲天气路径，分轮有合理性。当前证实的是三段输入通知、两次重复 `study_explain`、末尾约束短片识别不准确；**真正单长句内部停顿尚未由这份材料测试**。不得沿用此前宽泛描述，把整个三句录音都称为同一句的被截尾片。

原WAV12.272426秒、22050Hz、mono PCM16。raw RMS100/10毫秒窗口得到内部低幅度间隔4.111–4.989（0.878秒）及9.997–10.885（0.888秒），与三条指令之间的停顿相容；这是幅度测量，不是RNNoise/语言学句界。当前文件SHA256 `819a34747cd3ab50d539cf95a92890aa21e1ede95796f880e16b2257f6026466` 与两个场景JSON一致。driver重采样并加1秒前静音、3秒尾静音；MANUAL模式则在最后幅度活动后1.2秒裁尾。未重新合成或播放材料。

| 场景 | provider completed相对末非静音 | 本地commit/clear（说完前） | provider请求工具 |
| --- | --- | --- | --- |
| native-timing | 75字 -6.451秒；93字 -0.490秒；9字 +1.020秒 | 无 | material、explain、explain |
| manual-support3 | 75字 -6.393秒；93字 -0.535秒；9字 +1.032秒 | 无 | material、explain、explain |

完成通知来自provider，不能归因于local quiet清缓存。也不能仅凭 `transcription.completed` 名称当成整个学习者意图已经结束。

## MANUAL实验的精确边界

support3确实发出 `turn_detection:null`，三个completed都在显式end之前；无provider `session.updated`字段确认。它证明**这次配置序列没有压住自动完成通知**，不能证明该代理在任何配置序列下永不支持MANUAL。

尚有可见混杂：wall8263.712的显式null后，8263.714及8269.787又发了两个没有turn_detection的session更新，输入8270.833开始。现有 `_tools.py` 的free工具同步仅发送tools；同文件GLM分支明确有另一供应商漏VAD设置会reset默认的适配注释，但这不是Lanlan会重置的证据。代理是否忽略null、是否在后续局部更新重置、或者另一路ASR仍切句，当前无法区分。没有公开映射源码/回执，故不盲加参数，不再次重复同一支持场景。

## 可以复用什么，以及最小候选的实际范围

已有源码链可复用，不需要新语音架构：

- `core/asr_runtime.py:4710` 的 `_voice_session_activation_has_speech` 优先使用有效RNNoise probability，fallback才用PCM能量；`_send_native_audio_pcm` 将判定送入原session `stream_audio`。
- `omni_realtime_client/_transport.py:1571` 使用该speech verdict，更新 `_last_local_loud_time`。该字段采用capture wall时基，必须和wall比较，不能减monotonic值。
- `_tools.py:409` 的 `_advance_tool_scope` 退休并取消上一scope工具任务；`:446` 的 `note_user_turn_started` 调用它。代理completed在没有先行server onset证据时沿用这个新turn边界。保留它才能保护旧答/旧工具退休。
- `core/tool_calling.py:117` 的 `_on_tool_call` 是工具注册表执行前最小挂点；raw工具通过后台task运行（`_tools.py:_start_raw_tool_call`），等待不会要求阻塞接收循环。现有native free没有可靠的“整个学习者长句完成”本地ASR事件；独立ASR的final/seal属于另一条当前关闭的路线，不能悄悄切过去或换供应商。

**有依据、但仍未实施的最小候选**：仅native/free中有实际近期speech证据时，在 `study_explain/study_quiz/study_answer/study_summary` 的registry.execute之前，读已有最后speech时间，异步等到约1.2秒quiet；等待有总上限，并保留原scope/connection/generation取消。后续fragment照常推进scope，旧call在进入Study付费请求前取消，只让最新仍有效call执行。`study_material`这种只读元数据工具无需等。不要持有音频/取消锁，不缓冲PCM，不改变onset/cancel阈值，不发新的MANUAL配置。

这是**教学工具准入去重/短间隔连续要求协同**，不是代理ASR重新拼句，更不是完整意图判定。它不能保证大于1.2秒的句内停顿、不能修正“No. Quize”、不能阻止provider在工具以外直接说话；最新tool参数是否保留前段问题仍需实际检查。若待执行call已经付费出站，scope取消也不能当成费用撤销。证据中末片约1.02秒晚到，因此直接在最后speech瞬间执行会漏掉末片；quiet候选应先有ASR尾片就绪证据再进入教学，而非只等静音就宣称整句完整。

暂不建议以这三条命令为依据实施全局delay。最有信息量的下一步是主 Agent 明确标为 `single_sentence` 的中文单长句固定刺激：在还未完整的条件/介词从句中放入0.9秒停顿，同一问句末尾包含篇幅/不出题要求；例如“在天气请求从Flutter客户端……经过Express后端再到外部服务的过程中，为什么需要保留后端这一层并用两句中文说明且不要出题？”（省略号位置为控制停顿，不能另加独立命令）。这不是新图片/架构材料，仅为补齐当前未测试的语音输入条件，是否生成及在线运行由主 Agent决定。

该单句若实际没有早工具/回答，则保留原默认，不为优化已通过场景加delay。若有早教学且完整末句未入工具参数，才做上述局部准入候选的单个对比；核对完整问题/末尾约束、Study请求次数、末非静音→首播放，以及受影响普通打断顺序。服务早ASR分段仍如实记为上游行为，不能把延后本地工具冒称已修proxy VAD。

## 可重用离线量具

新增 `scripts/neko_spoken_turn_analysis.py`：只读WAV和场景JSON；输入种类必须依据原刺激声明，默认unknown；分开报告provider完成、原生文本、显式null、后续漏VAD更新及本地commit/clear。不混相对时钟、不从“早完成”自动宣判单长句失败，不写或修改输入文件。

```powershell
& benchmarks/raw/neko-product-host/.venv/Scripts/python.exe -I -B scripts/neko_spoken_turn_analysis.py --scene benchmarks/raw/evidence/daily-companion-20261014-native-timing.json --scene benchmarks/raw/evidence/daily-companion-20261014-manual-support3.json --wav benchmarks/raw/voice-input/daily-study-picture-20261014.wav --input-kind command_sequence
& benchmarks/raw/neko-product-host/.venv/Scripts/python.exe -I -B scripts/test_neko_spoken_turn_analysis.py
```

新离线检查 **5/5通过，0.005秒**：不把多句/未知输入判成单长句失败、null不等于接受且漏VAD后续更新保留、缺绝对时钟拒绝/不混旧历史、声明单句只报告观察且不改原JSON、实际PCM帧率的0.9秒间隔和全静音处理。没有重跑旧批次或MANUAL线上scene。

本阶段新增外部调用0、额度调整0、宿主/音频进程0、生产源码修改0。Goal继续；B单长句及听感待验，其他任务不被这个协议缺口挡住。

## 单中文句实证之后：付费教学工具准入的只读最小方案

主线随后跑了真正单中文句0.9秒内部停顿，证据为 `benchmarks/raw/evidence/daily-companion-20261014-role-point-single.json`。两个ASR completed和两个提前study_point已与晚ASR工具scope竞态分开记录在 `daily-companion-late-asr-tools-2026-10-14.md`。ordering修复改变工具/ASR派发顺序，未改变上游分片。本节只设计可能的 `study_explain/study_quiz/study_answer` 准入，不修改生产、不在线。

### 只等1.2秒静默不够

本场最后speech为wall 1791900757.801862，第二ASR completed是1791900759.213，即最后speech后约1.411秒。第一片工具若只等quiet>=1.2，会在约1791900759.002开始付费，比末片ASR提前约.211秒。末片后scope取消不能撤销已经出站的DeepSeek请求，也不能说完整末尾约束已经进入首请求。

因此最小候选应同时要求：quiet>=约1.2秒、当前候选expected ASR已完成host callback、该ASR的**接收时刻**不早于最新本地speech capture时刻；owner仍是当初这次ready之后固定的scope/connection/session。这个条件能保护本场观察到的“prefix completed在suffix还持续输入”路径，而不是仅对正在说话加sleep。

注意当前 `_finish_raw_input_transcript` (`_tools.py:809`) 保存的是callback完成时time.time。它不是ASR接收时刻，不能直接用来证明ASR覆盖最后speech：慢callback会让旧fragment时间戳看起来比新speech还晚。需要在completed同步阶段、callback之前记录received wall时间与此次scope的关联；继续保留ready标记，两者用途不同。所有capture wall比较与deadline monotonic分别一致。

### 最小挂点及生命周期

优先扩展已经存在的late-ASR pending准入，在 `_start_raw_tool_call_now` (`_tools.py:816`) 之前，仅对精确native free/no-server-VAD的三项付费教学call等待。只读material/source/point不必延迟。不要改变PCM admission、RNNoise/onset/cancel阈值，不重新提交音频，也不扩大供应商路线。

1. 排队和ASR排序沿用当前候选；第一次expected完成并ready后，固定effective owner（例如scope2）。只允许这一完成晋升，quiet等待过程中不能再次capture live owner。
2. await短检查/原可用事件期间持续重读最后speech时间；0.9秒pause内suffix到来则quiet目标后移。不要持有音频/取消/工具发送锁；receive必须保持可读。
3. 第二ASR使scope3。scope2首候选此时只能abandoned，不能升到scope3；原call_id在原连接用已有no-continuation关闭。第二候选ready后再等quiet+最新ASR证据，才能首次进入原执行路径。
4. 设置总体有界等待。超过期限、连接换代、native handoff、foreign scope或输入替换必须丢弃并记录具体原因，不能以“到时间了”为理由硬执行。总上限须覆盖本场首call→末ASR约9秒的观察，具体值由主线选定并验证，不宣称任意长句都受支持。
5. 准入成功后一次调用原now方法。保留原owner检查、单batch continuation及tool-result发送guard；不能手工response.create或清空scope来恢复结果。

若改在原 `_run` (`_tools.py:857`) 中等待，任务与collector都已经登记在 `_tool_tasks`。新ASR退休时 `_advance_tool_scope` (`:414`) 同时cancel两者，而原 `_answer_raw_tool_batch` (`:873`) 没有CancelError/finally释放call；仅依赖普通cancel会有未关闭call风险。需要显式且幂等的no-continuation释放，不能吞掉取消继续执行工具。复用现pending的独立生命周期和abandoned路径修改范围更小，并避免这一新增孤儿路径。

### 能保护什么、不能证明什么

对本场0.9秒pause，只要suffix loud时间正常送达且末ASR接收/ready证据准确，gate可以阻止prefix付费call提前出站，第二scope自然取代它。它无法保证provider的新call arguments含前段问题、没有丢掉“用两句中文/不要出题”等末尾约束；应直接检查最终raw arguments和Study请求内容，不能以只剩一请求就判教学正确。

无input item identity时，“ASR接收晚于最后speech”仍是兼容性启发式；严重迟到的旧fragment也可能晚到。更长句内pause超过quiet阈值、provider在工具之外直接说话、RNNoise漏判speech和缺少最后completed的路径都不由gate解决。不拼装跨scope工具参数、不用临时偏好代替真正问题内容、不自动升级成长期偏好。

最有意义的离线覆盖是：pause<1.2期间新speech推迟准入；quiet已足但最新ASR早于最后speech仍不得出站；末ASR新scope取消首call并只放行新call；旧conn/timeout/handoff不付费且不continuation；parallel sibling正常按原batch返回。主线再安排一个已授权受控固定刺激，核完整问题与末尾约束、付费请求数、末speech→首播放。没有必要重复MANUAL scene或已经通过的旧教学验收。

本节外部请求0、生产修改0、宿主/音频进程0。当前只读设计完成，实施与真实场景验证由主Agent决定。
