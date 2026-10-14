# Phrase adapter：候选宿主时间、授权和交付契约只读追踪

日期：2026-10-14。完整读取 contract、plan、status、blockers 后，仅定向读取 `candidates/N.E.K.O/main_logic/core` 与实际 Omni client 相关源码。该候选树无 `.codegraph`，所以按明确文件用rg定位。Main最新交接：阶段八11文件已发布080d69ad02e0188fa278fcd996ab67ca3f0ed428、候选clean、master不变；这是Main发布事实，本审查未运行git远端/账本核验。

本轮唯一写入是本文；不改源码/测试/manifest/其它报告，不运行host、API、音频、在线、额度或Agent。以下行号均为本次读取的 **candidates/N.E.K.O**，不是旧 `core_parts` 或benchmark拷贝。

Main另补充当前PID48216已复用为conhost，原quality19 launcher是Python；不能以同一PID数字认领进程。本轮未查/清理任何进程，未碰该conhost。端口无listener是Main当前观察，不是本报告独立进程验收。

## 1. 当前 captured_at 不是 collector 的 sample START

| 实际来源/传递位置 | 源码事实 |
| --- | --- |
| `main_logic/core/asr_runtime.py:139–175` `_QueuedMicFrame.from_message` | 默认 received_at=`time.monotonic()`，captured_at=`time.time()`；有帧source_rate/duration_us，但没有用duration反推sample起点。 |
| `asr_runtime.py:3459/3491–3496` `_enqueue_audio_stream_data` | 调用from_message只传message/token/epoch/ingress_sequence，没有传客户端capture timestamp；因此正常这条路径的captured_at是服务器入队/arrival附近wall time。不能称为物理采集首sample时间。 |
| `asr_runtime.py:3599–3605` worker | 原received_at/captured_at透传，不重新取worker wall time。 |
| `asr_runtime.py:3944–3965/4008/4055` DSP后 | processed PCM16不为空后仍取传入captured_at，否则time.time；输出样本数量可能由pipeline处理改变，时间没有变成处理后PCM的sample START。 |
| `asr_runtime.py:4281–4305` activation AudioFrame | `.captured_at`使用received_at/monotonic，用于activation活动/排序；route context另存原captured_at/wall。两个同名字段不能混成一个clock。 |
| `asr_runtime.py:4379–4388 → 4798–4808` 实际 native send | stream_audio收到的是 `context.captured_at` /wall，而非AudioFrame.captured_at/monotonic。 |
| `asr_runtime.py:5005–5027` legacy hot-swap native batch | 最多合并5帧PCM，received_at用第一帧，captured_at明确用 **最后一帧** 的时间。对joined bytes不是第一sample时刻。 |
| `omni_realtime_client/_transport.py:1554–1582` | 将该值当audio_timeline_at，更新last local loud和现有handoff/VAD；不能全局改语义而不影响已验普通打断。 |

collector.feed的captured_at契约是sample START，且自行加 `len(pcm)/32000` 得到end；**不能把上述arrival wall直接传入**，尤其不能拿最后一帧时间给合批音频再加整个batch时长。这样会虚延speech end、制造clock_before_capture_end或影响quiet/max时间。

Main需要一个 **局部的新collector timeline转换**，保留原onset/VAD的audio_timeline_at不变。最小可定位的近似定义是“该已解码PCM chunk以arrival wall为end，start=end−chunk duration”，并显式命名arrival-derived/sample-start estimate；它不是物理麦克风时间保证。单帧的排队/DSP延迟、变长输出和batch timestamp必须分别处理。更稳定的collector样本游标可以用原PCM长度保持连续性，但不能拿它冒充真实wall时钟；tick必须与所定义timeline一致，backlog尚未处理完时不能因worker当前wall较晚提前seal。真实客户端sample timestamp、真实物理capture延迟和跨frame连续性在当前入队代码中没有证据。

首版安全支持范围应显式限正常native16k单帧；legacy hot-swap joined批在没有每frame start元数据/对应verdict之前bypass或拒绝该实验。不能给整个合批套第一帧speech_probability再宣称每一段quiet已确认。

## 2. game route getter 不是 native 麦克风授权

`omni_realtime_client/_client.py:114/161` 的 `get_input_route_identity` 只保存可选callback。`_transport.py:425–438` 只接受三元素tuple并把各元素转str；未知/异常返回None。它不核is_active、socket、Core input lease、硬静音/焦点、权限、activation或connection generation。

两个真实Core构造点：`core/lifecycle.py:2340–2370` 当前new_session、`:2670–2703` pending_session。两者的该参数都指向 `get_active_game_route_generation_identity(self.lanlan_name)`。`utils/game_route_state.py:191–211` 返回 `(game key, game session_id, SDK route instance)`，没有活动game时None。普通native聊天None是正常情况；把None放宽为任何owner或者把这三元组当phrase完整authority都是错误接法。

实际已有native授权证据在Core：

- `core/asr_runtime.py:1339–1348` `_capture_ingress_token/_capture_native_ingress_token` 捕获voice lease connection/generation及microphone route generation。
- `:1468–1474` `_ingress_token_matches` 对这些字段匹配；`:1476–1502` `_voice_input_accepts_pcm` 核preview隔离、builtin/core或game active consumer、lease synchronized、hard mute/focus/内部外部suppressions。
- `:1802–1837` `_capture_voice_session_activation_generation` 捕获session anchor、ingress epoch/audio generation、lease、policy/pipeline，以及microphone/route/profile/permission/input_owner。明确handoff可以保留local anchor，但任意session replacement不能。
- `:4753–4767` native_send_is_current 另外核session引用、physical connection generation、native route、完整native ingress token、Core lease和input接受状态。它不是game getter。

## 3. 新 opt-in authority callback 的真实安装位置

不存在现成 `get_phrase_input_authority` getter。本轮没有创建它；以下是Main需要同时实现的具体接点，不是已实现功能：

1. Omni `_client.py` 可新增独立默认None的phrase-authority callback字段，transport opt-in读取它，unknown/None拒绝。不要替换get_input_route_identity的game语义。
2. 共用Core绑定点是 `core/session_lifecycle.py:346–356` `_bind_owned_output_callbacks(session)`。这里当前已经安装 `session.on_native_barge_in=partial(..., session)` 与 `get_native_barge_in_generation=self._capture_voice_session_activation_generation`，适合给新phrase callback闭包绑定 **该session实参**。不要用稍后变化的self.pending_session作为隐式目标。
3. 该绑定确实被 `core/lifecycle.py:415–422` `_bind_session_lifecycle_callbacks`调用；normal构造后在`:2382`、pending在`:2751`连接前都调用它。pending未安装前必须fail closed；不是仅在某个launcher动态添加一个永远True的getter。
4. `session_lifecycle.py:372–407` 现有async/sync guards检查 `session is self.session` 与connection record未retired；新同步authority callback也需同口径。它还需检查Core active/native route、lease owner=core、`_voice_input_accepts_pcm`、websocket/activation/native ingress、physical connection generation。返回固定immutable快照，在collector/flush每次await后比较；None没有fallback。

可复用 `_connection_record:session_lifecycle.py:171–175` 与上述现有Core方法。具体新增callback的名称/schema由Main实现并在两个真实构造/绑定路径测试后才可称接通；不要把本报告的建议名写成现有API。

## 4. 普通 None 会被计作TRANSPORT_WRITTEN

transport `stream_audio:1523–1546` 明确记录普通路径保持None，即使实际发送有bool结果。最终append `1738–1751` 只在require_output_commit时返回sent；buffer/DSP/resampler无输出时也可能None。

Core `asr_runtime.py:4797–4824` 在require_output_commit=False分支丢弃stream_audio返回并写 `written=None`；只有 `require_output_commit and written is None` 才LOCAL_ACCEPTED，随后调用 `_record_omni_microphone_audio(len(pcm16))`、返回TRANSPORT_WRITTEN。`:4919–4925` 对 `_omni_mic_audio_bytes` 累加。这不是“None证明已经写入”的有效契约。

对新的opt-in collector而言，若仅在transport返回None，会把每个本地queued frame照常累计为transport bytes，甚至还没seal。最小准确接法是 **仅opt-in actual Omni native路径** 使用existing require_output_commit=True，并在Core以 `effective_receipt = original_require_output_commit or verified_phrase_opt_in` 映射False→NOT_SENT、None→LOCAL_ACCEPTED、True→TRANSPORT_WRITTEN；保留owner await后检查和native pending分支，默认旧路径不扩大行为变化。不能只改调用kw却仍用旧原始require_output_commit作后面的条件。

collector实际flush的raw发送量应另由该owned writer在确实send_event成功后记账到原connection；它可能少于原capture bytes（zero压缩），要分别标local accepted/source samples与transport written样本。新的回执若继续是未知，必须UNKNOWN/不可继续，不能fake True。普通计数、ASR记录、provider确认和device播放是不同层；本报告没有测新byte计数。

## 5. native pending/replay 的现有单次PCM责任

`_transport.py:1548–1551` 在native pending时先让 `_capture_native_barge_in_pcm`保留frame，返回None，不向A写；`:1716–1717` 在onset建立pending之后也返回None。Core`:4817–4818` 明确将其LOCAL_ACCEPTED。新的collector不能再把同帧存入第二个buffer并由另一个writer发送。

Core `asr_runtime.py:4432–4449` 原generation/candidate检查、设pending/fatal、启动唯一recovery；`:4488–4520` connect B之后使用native buffer/cursor，逐frame调用 `stream_audio(..., require_output_commit=True, _native_barge_in_replay=True)`，只False失败、cursor单次前进。None已经代表一条合法本地接受路径；若新collector在这里None接管却把整段之后发送两次，会违反原单writer责任。

首adapter可严格 **不支持pending/replay及legacy hot-swap batch**，沿原路径单次交接，并对该正在handoff的输入完整bypass phrase模式；不能把已写B的replay prefix与后续collector suffix当一条“provider此前完全没收到”的phrase。若要支持它，必须真实接上唯一frame-owner/cursor交接并证明LOCAL_ACCEPTED不是触发再次replay，不允许给旧collector升connection或重喂已take batch。连接替换应使旧collector/flush失效；普通真实onset、精确cancel和恢复仍用原逻辑。

## 明确范围

确认的是当前源码：arrival wall→context→stream_audio、activation另有mono时间、legacy batch newest、game getter具体内容、两处真实构造与共用Core callback绑定、None回执误计的具体分支、native pending/replay的独占责任。未确认物理sample START、新authority callback存在/已安装、新LOCAL_ACCEPTED计数、handoff adapter、provider endpoint/ASR/burst、Native/device/human。

本报告为只读接入事实，**没有新实现或运行PASS**。默认OFF保留；Main按具体接点继续实际adapter，不能借collector13离线检查宣称host已接通。报告冻结。
