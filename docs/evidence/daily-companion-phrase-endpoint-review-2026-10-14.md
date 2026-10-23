# B：自然停顿端点方案只读研究

日期：2026-10-14。完整读取 contract、plan、status、blockers，按最后 append 承接已发布3b87b3c、阶段八本地教学投影修复、577/56/0/no online（接续记录事实，未直接读取账本）。仅新建本文。没有生产/测试/manifest/共享记录改动，没有启动host、API、音频、付费或子Agent，也没有制作/修改学习材料。

结论：**免费 raw 路由的可配置 silence/manual endpoint 当前未经证实；可实施的下一步是一个默认 OFF 的本地整段未发送 PCM endpoint 实验，而非继续升格旧 ASR/tool owner。** 先做实际 sender/activation 的离线适配；只有它能保留原真实 onset/cancel、单 writer、收发独立和准确交付状态，才值得安排一个必要场。它不是已经可发布的低延迟解决方案。

## 当前线路与证据

实际 native host 16k PCM 路线为 `main_logic/core/asr_runtime.py:4710–4828` 的 `_voice_session_activation_has_speech` / `_route_microphone_audio_unfiltered` → 当前 session `stream_audio`。host speech verdict 优先有效 RNNoise probability>=0.5，fallback RMS；不是任意另加能量阈值。transport 支持带 captured_at/speech_active 的16k host输入，以及48k浏览器输入经RNNoise/downsample。没有一个 raw `send_audio` 就能切到 Gemini SDK；免费路由实际使用 raw `send_event(input_audio_buffer.append)`。

`omni_realtime_client/_transport.py:1523–1749` 中的原 ingress 身份、activity标记、RNNoise、本地真实 onset/barge-in、静音 clear、native pending 和 provider append 是同一流水。真正发送点为1730附近的 uplink-resample/base64/append；免费路由16k、没有24k resampler。`_client.py:501–515` 将 Lanlan.app/free 标为 `_is_free_proxy=True`、`_has_server_vad=False`：没有 OpenAI speech_started/stopped 边界并不等于远端没有自动 VAD。

### silence / manual 能力不是现成可开启的开关

- `_shared.py:89–92` 只有 SERVER_VAD/MANUAL 枚举；`_protocol_capabilities.py` 只定义response开始证据、multimodal delivery、conversation item和function IDs匹配规则，没有“silence配置生效/支持manual输入边界”的经过验证能力。
- `_transport.py:755–800` free_session只发 `turn_detection={type:server_vad}` 或null。该段“代理会translate disabled-VAD”的注释不是服务实现或回执。其它供应商分支的silence字段不能复制后宣称Lanlan已支持。
- `_gemini_support.py:281–355` 的 `signal_user_activity_end` 在MANUAL下，对raw线路发 `input_audio_buffer.commit`+arbiter `response.create`；直接Gemini才走SDK activity_end。两种协议不可混用。发送成功只证明本地写入，不证明proxy停止自动完成或识别最后一个意图。
- `_client.py:453` 的6秒client VAD grace用于活动/图片/主动回调保护；它不延长provider的VAD。`_audio.py:136–178` 是90秒闲置关闭；`:186–231` 的本地静音clear门限是默认2秒/RNNoise4秒回调。把这些参数增大不会使远端0.9秒停顿不分轮，还会牵动既有缓冲清理。

官方直接 Gemini Live 明确提供 `realtimeInputConfig.automaticActivityDetection.silenceDurationMs`；增大会容纳更长停顿并增加延迟。关闭自动检测需要activityStart/activityEnd；audioStreamEnd是结束/flush信号，不能用来延后已有自动边界。[Google Live API reference](https://ai.google.dev/api/live#AutomaticActivityDetection)、[Google Live VAD guide](https://ai.google.dev/gemini-api/docs/live-api/capabilities#voice-activity-detection-vad)。这支持“上游原协议存在这类能力”，**不支持“Lanlan的Step形状session.update映射它们”**。没有切换供应商或调用直接Google API；不引入SDK依赖或费用。

### 已有实测的精确读法

本次只读原JSON结构及selected wire records，不播放WAV、重跑或写回产物。

| 场景 | 原 wire 的事实 | 能/不能推出什么 |
| --- | --- | --- |
| `daily-companion-20261014-manual-support3.json` | null请求在末非静音前19.610s；随后19.608s及13.535s前又有两条未携turn_detection的tools updates；无session.updated；75/93/9字completed分别在末非静音前6.393s、0.535s、后1.032s；显式commit在后1.217s | 该配置序列未压住自动completed。忽略null、后续更新reset、另一ASR切片仍无法区分；不能断言永久不支持MANUAL。不重复同一无确认场景。 |
| `daily-companion-20261014-picture-neighbor8.json` | 0.9s句内停顿的原复合WAV；五片completed相对末非静音-12.479/-10.353/-6.558/-3.471/+1.276s；工具多次到达，末scope真实explain仍执行三次；first audio+7.977s | 有真正自然停顿及早分片；既有gate是工具准入启发式，不是输入endpoint；no early audio和设备响声不能证明一句一次完整调用。 |

原manual支持WAV是三个独立英文指令，其“75/93/9”不独立证明单长句失败；详见既有 `daily-companion-spoken-turn-analysis-2026-10-14.md`。neighbor8的整体自动结果仍FAIL_OR_PARTIAL，英文及两句形状也失败；不能将新版first-ASR修复借到自然停顿分轮。新观察序号只证明收到事件顺序，不能命名provider utterance。

## 候选比较与选择

| 候选 | 适配点、延迟 | 本次判断 |
| --- | --- | --- |
| 已验证proxy silence参数或manual commit | free session setup + 所有partial update保留配置；speech实时发送、仅endpoint增加quiet等待 | 最优方向，但先需proxy公开映射/明确有效回执或不同配置的有依据验证。当前不够证据，不能盲加字段；不再重复旧MANUAL场。 |
| 实时发送speech、只暂存/压缩silence尾部 | raw append前，通常只增加短hold | 只减少发送的静音sample，不保证proxy在wall-clock无新数据期间不自动结束；不能仅凭离线sample拼接就宣称解决。新语音到来后再把旧quiet压短也无法撤回已完成的ASR/工具。 |
| 所有PCM滚动延迟固定1.2秒 | append前FIFO | 只是平移时间；如果完整静音仍被送出，原0.9秒sample gap还在，仍可分轮。不能把这叫endpoint。 |
| **整phrase尚未发送缓存，内部确认非speech段压缩，确认end后有界flush** | transport原VAD/onset之后、append之前；失去phrase期间流式ASR重叠，增加1.2s本地quiet+upload/ASR等待 | 当前最可做的raw fallback实验：provider在内部停顿时还没收到此phrase前半段，避免它抢先对那个prefix作答；压缩的内部gap减少按sample触发。是否仍按wall/模型语义切片需验证，不保证单ASR/一次工具。 |

## 最小下一实施步骤：先local-only adapter，不开日常开关

1. 仅精确 `lanlan_app_gemini` / free proxy / native16k路径增加一个默认OFF endpointer。优先插在 `_transport.stream_audio` 原DSP、VAD、真实onset、native pending处理之后，uplink append之前。**每capture帧仍立即执行原VAD/onset/cancel**；不缓冲整个stream_audio调用，也不等provider ASR再倒推onset。不将已送到provider的帧加入新缓存，不重新调用stream_audio来drain，避免第二次DSP/onset、旧PCM补发和owner升格。
2. 使用已有 `AudioFrame` 的capture/sample连续性和 `BoundedAudioFrameBuffer` 上限思想，独立拥有“尚未发送的当前phrase”，不创建第二套ASR/学习记忆。初始实验建议end quiet=1.2s、最多20s capture/640,000 bytes（16k mono PCM16），包含pre-roll和tail；这是待测参数，不是最终用户偏好。已有16.978s邻接WAV能在该上限内容纳。无speech、噪声一直活动、输入gap、overflow、设备/权限/route变更应停止该phrase并给可读状态；**不能沿deque淘汰开头后继续发送截断题目**。
3. 内部非speech段只压缩确认低speech的帧区间，保留约80–150ms短呼吸和小量pre/post边缘；不时间拉伸/重采样speech，不用“每帧RMS低”直接删可能的小字音/清辅音。首次flush可用当前已有PCM100ms块（3200bytes，base64约4.3KB），按现有raw写入而不sleep重建旧capture时钟。是否立即burst被proxy接受、是否转成按wall节奏消费，都待实测；不得用synthetic持续speech/noise保持活动。
4. onset和phrase endpoint分成两种边界：打断旧回答仍使用原真实capture证据立即取消；endpoint只是“本地已封存未发送范围”。本地phrase transaction可有日志ID，但明确标local-only，不充当provider input item ID。工具owner/response arbiter保持真实来源，不能给prefix tool重贴当前scope。buffer flush每个await前后核同session/socket/connection generation、native ingress token、activation generation、route/permission/input lease；一个旧flush不能向新connection补音或清新缓存。
5. 协调静音clear和handoff：原 `_should_clear_audio_buffer_on_silence` 不应在本地phrase尚未发送时先reset它的route/handoff来源；仅延后该phrase拥有的clear，不能全局禁clear。`_transport.py:259–304` 的input-open/handoff保护应一直覆盖本地未发送范围；整段flush成功后仍等真实provider边界，不能把quiet当已发生server speech_stop。native barge-in已有replacement/prefix协调器仍独占其帧；新endpointer不得另外replay、读同一cache双发送或借最后的output owner。若无法证明handoff交接一次性，首版应拒绝该状态并保持原日常stream线路。
6. 交付回执必须诚实：activation `OutputCommit.LOCAL_ACCEPTED` 已存在（`activation/contracts.py:41–49`，`controller.py:483–519`将其消费原lease），可表示“新endpointer已经拥有该帧”。`core/asr_runtime.py:4797–4827` 的require_output_commit分支把stream_audio None当LOCAL_ACCEPTED，False当NOT_SENT。普通分支目前可能仍记TRANSPORT_WRITTEN；实现必须连同这个准确状态适配，不能把queued bytes计成provider写入。drain只由一个writer执行；async flush失败/取消后标不可继续，不能触发activation NOT_SENT重试把已经部分写出的整段再次送出。

由源码推导的候选文件范围：`omni_realtime_client/_transport.py`（挂点与owned flush）、`_audio.py`（原clear与pending范围协调）、`_client.py`（默认OFF状态/上限）、`core/asr_runtime.py`（LOCAL_ACCEPTED与真实transport计数）；必要小独立stdlib helper和定向测试。不修改通用onset阈值、response arbiter fail-open、工具scope归属或已验音频cancel。现有activation支持LOCAL_ACCEPTED，但**不等于完整frame batch endpoint已经实现**。

## 延迟、离线验收和停止条件

20秒缓存上界约625KiB原PCM，base64展开另约833KiB；现有固定16.978秒输入不是低内存问题。真正成本是失去流式ASR重叠及对方的接收处理：原neighbor8末非静音到ASR1.276s/首音7.977s，不能直接减1.276再加1.2推算新版首音。新模式末尾延迟下界包含1.2s quiet，之后flush、proxy ASR和模型/工具仍要计；至少分别记录capture last-speech、local seal、first/last transport append、provider ASR、tool/result、firstPCM和device start。不承诺减少响应慢的问题。

最小离线检查使用已有neighbor8同WAV/已有speech verdict或actual DSP fake，禁调用provider：0.9s内部pause不会seal、1.2s外部quiet只seal一次；所有speech sample逐字节一致/发送一次、内部quiet有源range记录；byte/time overflow拒绝、全静音无付费；route/socket/activation/input-owner在锁/DSP/flush await中变化不向新owner写旧PCM；真实onset仍即时发生、未伪server事件；LOCAL_ACCEPTED不算written；partial send/unknown不replay；close取消timer、clear不污染新buffer、handoff input-open直到真实边界。先验证这些，再考虑 **一场** Main组织的原复合WAV实验，重点最后语言/noquiz/nosave约束完整、没有早tool/earlyaudio、没多次paid、端点延迟和原cancel顺序；不重做材料或重复旧MANUAL支持场。

如果proxy会在一次burst内仍拆ASR、按wall停顿/最大包策略抛错，或barge-in prefix不能安全共用，同场失败应停止此候选，保持defaultOFF，记录恢复条件。不能靠重复旧PCM、压制新user onset、降低owner校验或多次CONNECT耗额度制造PASS。更可靠的raw控制仍需proxy endpoint映射；直接Google文档不能替代它。

## 支持和不确定项

确认：当前源码可找出明确append挂点、真实speech/cancel链、capture frame上限/LOCAL_ACCEPTED/owned handoff契约；邻接失败和MANUAL混杂来自现有真实产物。设计复用N.E.K.O现有源码（所读 `_shared.py`、`_audio.py` 保留Apache-2.0项目header），无需安装新依赖；未复制第三方库或改许可证。

未知：Lanlan端点参数映射/局部update合并、wall与sample时间策略、burst输入限速/ASR分片策略；新本地endpoint的ASR准确率、端到端延迟、真实设备和普通真人打断体验。静音不是语言学句界，1.2s只对当前0.9s刺激有望容纳；更长思考停顿、两个确实独立问题和新用户输入不能自动靠时间区分。显式说完/按键的可选入口可能有用，但没有服务manual控制时仍需相同未发送缓存，不能只是发commit。

本文只有源码/既有产物/官方文档研究，**没有新源码或新的离线实现验收、模型、Native、设备或真人PASS**。只读JSON摘取不是新endpoint执行证据。主线可按以上最小adapter与验收表实施；本报告冻结。
