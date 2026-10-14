# 阶段24首帧题目pin→ASR隔离窄审

2026-10-15。只读实际host stream_audio、native barge buffer/replay、ASR/reset/clear及已冻结fallback设计。Main尚在实现opt-in helper，本文审的是必要条件与现有hook，不是对未读到的新实现宣布bug/PASS。没有tests、服务、provider、音频/mic/capture/loopback或预算操作；没有改Main代码、manifest、共享记录或用户库，唯一新增本报告。

## 方向成立，三项必须收口

输入第一speech frame同步取得当前Study四身份+evaluated，保存一次**包括None**，后续SDK status只核它而不选择最新题，是比ASR后才读题更强的方案。Getter绑真实source session、ASR在现scope advance后捕获message_ws/generation/scope并后台执行正式grade，也符合已有recv与普通barge保护。

实现前必须满足下列P1/P2条件；它们不要求改变ordinary VAD、barge阈值、PCM或新建学习记忆：

1. **P1：重放或受控重连不得重读最新题。** `_native_barge_in_replay=True`的帧仍可带speech_active=True；若统一首True hook或connect reset让它读最新SQLite，则A题语音可在换到B后绑定B。必须携带原frame pin（原None也不变），仅在已证同activation/candidate的barge handoff转交到它所拥有的新connection。普通连接替换不继承；未知/overflow/failure无权威就formal-grade拒绝。原voice包继续原样重放，不新增或改写音频行为。
2. **P1：clear/第二段/迟到ASR不能串一个槽。** 一个“首True capture、任意ASR take后reset”的槽，不足以区分已clear的A ASR与已经开始的B语音。不能clear后重开槽读B，再让迟到A consume B；也不能A ASR消费后仍在B的voiced run中首次重读成更新后的C。需exact item/buffer/candidate归属；无稳定provider ID且第二candidate/clear使归属不明时sticky invalid/fail-closed，不让捕获恢复为“读最新题”。恢复到下一明确新输入或已证连接边界，不按任意terminal/text内容猜。无需新增队列，可仅一个活动record＋ambiguity状态；只有有现有item映射证明时才沿映射取对应record。
3. **P2：legacy None RNNoise路线不能只有RMS hook。** `input_has_speech`在DSP之前由raw RMS生成，但48kHz低RMS语音可以在RNNoise speech_probability>0.4路线被确认。仅在1612读取会漏这些合法语音；若首次在1671才读SQLite，又已越过turn-admission await，可绑定等待期间的新题。应在已有DSP输出之后、进入admission lock之前捕获首次RNNoise-confirmed speech，仍preawait。不把显式speech_active=False强行upgrade成raw_loud或新判定，保持原caller声学契约。

## 现有精确接点

以下文件均相对`benchmarks/raw/neko-product-host/`：

| 符号/位置 | 已存在行为 | 最小pin接法 |
| --- | --- | --- |
| `main_logic/omni_realtime_client/_transport.py` stream_audio `1548–1589` | phrase_driver可能早退；native barge capture可能返回None而未写旧provider。 | opt-in getter应在确认真实首speech且仍属当前input/source之后、1587 buffer之前取pin；不等待网络。phrase_route_changed早退表示未提交新输入，不应留下可供其它输入采纳的pin。 |
| 同方法 `1600–1620` | 先读ingress route，input_has_speech确认后preawait记录活跃。 | Host-scored True可更早；普通RMS确认可在这里取首次pin，但需要后面DSP空/未提交的对应处理。None结果须独立captured flag，不重查。 |
| 同方法 `1630–1646,1652,1671–1682` | 48kHz DSP可返回空，RNNoise确认在lock内使用之前取得的route。 | RNNoise概率在DSP处理后可读，pin应在1652之前确认并保存，不在等待后再取current。 |
| `_transport.py` _capture_native_barge_in_pcm `1357–1396` | generation与bounded buffer、sequence/sample累计；candidate在首voice或quiet gap后更换。 | 原candidate/input记录关联pin；buffer每frame.context只存bool，没有题目pin，不能说它已自动携带题。不要更改context的现有bool用途。 |
| 同文件 _prepare_native_barge_in_replay `1399–1406` | 选candidate及pre-roll cursor。 | 选定同一个candidate的原pin sidecar；pre-roll静音和之后replay True都禁止重读当前题。 |
| `main_logic/core/asr_runtime.py` _recover_native_barge_in `4452–4523` | current()核Core activation/lease/source/socket；close/listener drain→connect→原bounded PCM replay，最后重启recv。 | 把原pin随已有受控handoff固定；只在current()持续成立、candidate未溢出时映射到本次owned新conn，不为其它新连接捐赠。关闭/失败cleanup必须按该record身份收口。 |
| `_transport.py` ASR completed `3918–3943` | no-server-VAD必要scope advance之后deliver，再finish transcript。 | first speech pin必须在Core callback前detach消费，并与本次raw message_ws/gen/scope对应；后台状态getter只复核，不能补读。reset不能清掉callback等待中别的新输入record。 |
| `_audio.py` clear_audio_buffer `228–241` | phrase保护可直接返回False；否则清route marker、await provider clear，drop resampler tail。 | 仅实际clear路径poison相应输入pin，不把返回False的受保护phrase视为已丢弃。不能恢复旧迟到ASR的资格；必须记录unknown/retired输入边界。 |
| `_transport.py` _clear_input_route_identities / _reset_input_route_identity_stream `304–313`、close/_detach_for_close `4559–…` | 普通连接/stream route清理，与受控barge connect复用。 | pin独立、按owner生命周期清理；不能把通用route reset直接等同“允许新的SQL capture”，或让旧finally抹新pin。受控handoff先固定record，普通detach全退役。 |

## 不能误用的计数与返回值

`_note_voice_handoff_input_open:159–166`每次调用都让sequence+1，1612确认的每个语音帧都会调用它；它不是整段utterance固定ID。若pin绑定首帧sequence后要求ASR current sequence精确相等，合法多帧语音必失效；若reset时忽略差异，又可能跨输入。可记录起点/已送frame范围用于证据，但整段身份应使用已有candidate/buffer/本次独立record，不把帧计数偷换成provider turn ID。

`_rollback_voice_handoff_input_open:168–178`会在该帧没有送出时减回sequence；DSP空、resampler空或send false均有相应调用（1637、1780、1798）。pin不能在这些早退后给未来未相关语音保持“真实已提交”资格，也不能简单见None就清：ordinary return None也可能是合法本地buffer、phrase接受或barge retained PCM。以对应入口/candidate/transport receipt区分；无法证明则invalidate正式fallback，不能加一次模型调用碰运气。

_native_barge_in_pending缓冲帧是原输入的一部分，getter必须在pending early return前捕获原首speech；replay时不再次打开capture。Connection generation变化不是天然同输入：只有原_recover中的controlled lineage能承接，真newinput、voice lease/profile/policy变化和外部replacement不能承接。

## SQLite getter与权威边界

第三stdlib helper只能read-only读取本任务actual runtime的既有Study state row，单次一致性JSON投影四非空string和attempt_evaluated；不写DB、不查history/QA/密钥、不把checkpoint当更强current、更不fallback到另一个store或旧SDK状态。path应由当前运行配置/启动关系绑定，非模型给任意文件；source client非当前或权限/lease/activation不符返回None。mode=ro/query_only、显式close、有限busy等待和读失败None，不能在first-frame路径循环等待/重试阻塞ordinary barge。

新第三helper也须加入两实际runtime的exact部署/SourceGate和真实启动cwd import核查；不能让测试scripts sys.path掩盖运行时缺模块，重复阶段20已定位的问题。缺模块/读失败应禁用正式fallback并保ordinary音频路径，不可让首frame额外import异常破坏整个stream_audio。这里只列必要部署边界，没有改manifest或执行import量具。

None与“尚未capture”必须两种状态。第一speech时无题/读取失败/尚未启动后，后续出现新题不能使正在说的这段话获得新题资格。SDK getter后再严格比frame pin，普通评分只pending；显式correction由原retry入口核wrong/partial和新attempt，不从评过字段为true就推测可重评。frame pin是local authority snapshot，不是provider call_id或Native音频来源证明。

ASR callback仍同步登记hold/_create_tool_task返回，不能等待grade/terminal堵recv；raw消息绑定source及pair-exempt只用于此ASR输入，普通ToolTaskOwner pair fence不变。需要重申：第一次frame pin四ID只保证题目开始时归属；实际source/connection/scope/activation和逐send fences仍必须独立存在。

## 必要定向回归（本报告不执行）

1. 首Host-scored True在barge pending return前capture A一次；题随后B、新课/session或SDK status变化，旧ASR不得采用B；首capture None之后新题到来仍不grade。原caller False/RMS/DSP语义与音频送出保持。
2. 48kHz None：低RMS但RNNoise>0.4在pre-admission保存A；admission等待时题变B仍拒。DSP空/resampler空/send false各有正确pin处理，不以None一概当失败或成功。
3. actual controlled native barge A→新conn、pre-roll/replay，getter不重复、原pin只给同candidate；换题期间仍A→SDK B拒。普通外部connect/close、overflow、taskcancel、新lease generation不可捐赠A，旧cleanup不可清新record。
4. input buffer clear→迟到旧ASR，与新speech B同时存在；无映射时拒绝，不consume B。第二candidate在首ASR之前出现/ASR多片时不能reset后在同B声段重读C；合法单输入正常消费后下一明确输入可capture。
5. Frame→rawASR→Core accepted后台任务使用预先pin，原owner/SDK getter/entry保存真实grade且只一次；getter错/缺/过期、status/model等待换题/ABA或newinput→零假新grade/零晚relay，ordinary nonStudy/onset保护不变。
6. 真成绩到声路：hold丢弃自由text/audio/最后buffer；只在可证旧终结或有界一次无PCM controlled isolation后由原受控owner发送合法公开grade文本relay，无伪function_call_output；queue/semaphore阶段失效均不发送，失败诚实且有限，不永久将Goal降为“只有文本”完成。

最后一组必须由Main单独补服务/Native设备证据，源码首帧隔离不能证明声音来自grade。若proxy旧终结无法关联，记录局部protocol blocker、继续受控隔离和其它A–F；不要timeout放音或无限重连，也不要把文字持久化完成冒称Native评分交付完成。

本次仅SOURCE设计审查，无新PASS层；三个必要风险收口后Main再按实际修改做定向量具。报告完成后冻结。
