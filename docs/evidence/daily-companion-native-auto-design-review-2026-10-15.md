# 阶段40：Native自动响应登记最小设计意见

2026-10-15，仅只读actual Runtime `_response_arbiter.py`、`_transport.py`、关联协议profile及现有 `neko_phrase_input_transport.py`。仅新增本报告，无实现、共享记录、账本、Goal或学习数据修改；未启动应用/网络/模型/声音/设备，未另跑fixture。50实际结果及Main本地复现来源保留，不把设计当修复通过。

## 结论

**可以复用arbiter既有单lane/ticket/owner/seen-ID/quarantine/取消机制，但当前没有一个可直接登记PCM自动响应的公开API。** 不能把audio.append直接塞进当前item_driven队列就认为已覆盖，也不能通过notify_server_vad_response_pending伪造一次VAD来过关。最小正确增量应是现有arbiter的明确automatic-audio模式，绑定真实sealed输入的不可变上下文，不额外发response.create，不在terminal时用currentseq补认旧响应。

首次范围应窄于“所有provider自动响应”：仅已经核实LANLAN_APP capability、非handoff/bypass、真实完整phrase write链。普通stream_audio、旧连接、未知profile仍原样。50一输入两ASR/两response说明响应数不能预设为一；下述多响应限制必须在实施前选定，不能由单response测试冒充全日常可用。

## 现有接口为什么不够

| 现有点 | 实际源码 | 可复用/不能直接做的事 |
|---|---|---|
| `enqueue` | arbiter681–790 | 创建ticket并排入同一队列；response_event默认/None均变response.create，没有“只登记自动PCM”语义 |
| item_driven判断 | arbiter2838起 | 仅responds_to_conversation_items且全部pre-event是user/function-output conversation.item.create才成立；audio.append不属于此类，会走显式create分支 |
| owner先于write安装 | arbiter2928起 | item-driven首个item写前设置terminal/_response_owner/response_send_started，能覆盖同步早响应；可复用该顺序，不可借假item触发 |
| `notify_response_content` | arbiter1592–1656 | capability允许、唯一current owner已开始发送、未interrupted/pending/quarantine、ID真实且未见过时才确认start；无owner就拒绝，正是50路径 |
| server-VAD pending | arbiter1666–1711 | 会夺取/打断显式owner并等待response.created；content fallback明确拒绝server_vad_response_pending，不能用它登记never-announcing PCM |
| `_begin_response_lifecycle` | transport3014起 | 当前从live `_voice_handoff_input_sequence`复制response seq；新增自动路径必须传/取登记时的bound seq，不能迟到才读取live值 |
| phrase flush | helper188–241 | 逐块await成功、检查同epoch/current snapshot、记written样本后才设置waiting与成功report；这是本地write证据，不是provider ACK |

LANLAN_APP profile允许ID-bearing content start、responds_to_conversation_items=True，但function_call_ids_match_terminal=False；function-call事件ID不能借此认作与后续文本/audio同一个response。profile也没有证明“一个PCM phrase只生成一个response”。

## 推荐最小接口与时序（拟新增，不是现有getter）

在现有 `enqueue/_QueuedResponse/_process` 内增加明确可选automatic-audio描述（例如 `native_input_binding`），不要另建queue/DB或伪造conversation item。描述应由真实phrase writer提供：driver/delivery对象身份、driver epoch、完整Core authority snapshot、ws对象、connection_generation、固定input_sequence、expected样本数，以及无await的current检查。名称可由Main适配，关键是物理身份和样本承诺真实存在。

1. **第一byte前预留。** 同一arbiter确认lane可用、无旧server响应/unknown-id quarantine、无其它显式owner、native authority当前，才安装同一ticket/owner。此时记录“预留”，不能记已完整发送或生成provider utterance ID。不要等最后一个await之后才装owner，否则同步到达的真实content仍落no-owner。
2. **只发送原PCM一次。** 用既有worker/send_guard序列化原batch的真实audio.append；不加response.create、不插空白user item、不重放PCM。每次await前后核原ws/generation/epoch/authority与写计数；新PCM、handoff/replay或owner变化使该登记退休，不能改认成新slot。
3. **完整写后commit。** 仅所有原batch样本written==output>0且当前时，自动slot进入可判定“已提交本地输入”的状态。失败/部分写/cancel不得退役waiting为成功；不能因已见输出就忽略剩余未写PCM。若content在完整write之前出现，只可作为同slot候选观察，不能让早terminal完成整批；最小保守做法是明确报告premature/partial并fail-closed，不把丢掉早片段后的残余当完整答案。若要缓冲早content需另作有界设计审查，不能默默加无界输出缓存。
4. **真正ID-bearing start。** 继续用现有profile/seen-ID/quarantine条件，只为该slot接受一个新的实际response ID；transport通过arbiter提供的bound input context开始lifecycle。接口可为 `response_input_context_for(response_id)`，但这是拟新增，只能返回原slot的immutable seq/snapshot，不能实现成“返回当前seq”。
5. **真正terminal与输入退役。** 仅同ID、同conn、原slot仍当前、完整write已commit且非local timeout/fail-open时，允许用bound seq退役对应waiting。UI/tts on_response_done和sid_rotate仍守原host-turn guard；输入完成与UI轮次保护应分开检查，但不移除UI guard。失败response不得伪记正常教学完成。
6. **退休与超时。** 连接close/reconnect、driver.retire、真实新正PCM/inputseq变化、takeover/authority变化、写失败，均明确退休预留与ticket；复用arbiter现有cancel/connection-lost处理。没有owner/完整write资格不安装新slot；未知旧响应不能凭“现在在等待”补认。超时继续有界失败，不无限重连。

`enqueue`当前会等旧response idle；新的PCM自动登记不能因此阻塞/推迟既有真人onset/handoff路径。phase模式只在已经进入phrase collector且原barge-in/bypass保护允许的分支使用；busy情况应交还现有handoff/拒绝策略，不能为等lane继续攒无限输入或关掉普通打断。

## 一份sealed输入多次ASR/response的硬边界

50证明本地输入seq与provider response ID不一一对应。仅新增一个owner覆盖第一response，最多解决“第一owned terminal不再虚假等到30秒”；它**不能自动证明第二个ASR/response是同一语义轮的合法后续**。

可分两档交付，必须明确选范围：

- 最窄首档：只登记/确认第一个真实ID response；第一正常terminal可结束该slot的boundary等待。之后未知新response不继承已消费ticket，更不能把它绑到下一currentseq。若provider继续分轮，记录该protocol分轮/未关联后续范围，不能宣称连续单轮教学全过。这样避免为修timeout把旧response复活，但也不解决自然停顿和所有后续输出归属。
- 若本阶段要完整覆盖50：须让同一个**原sealed输入上下文**可关联多个独立response实例，而不是把它们当同一response ID。仍用现有lane，每个实例有自己的实际ID/terminal，另保留只读input origin资格直到新PCM/conn/authority/有界期限退休。后续实例的资格必须来自本地未变sealed对象和实际ASR/response证据，且不得有其它触发源争用lane；不能仅凭“近期有一个输入”自动收所有新ID。当前profile/事件未提供统一input-item→response链时，存在未消除的归属歧义，应拒绝或保持PARTIAL，不能发明provider utterance ID。

第一response terminal不是“provider永远不会再从该PCM生成输出”的证明。多response策略、episode保留期限/容量、与工具后续response的区分需要单独真实fixture；不建议在无协议证据时直接宽放idle/no-owner content。

## 不建议的替代

- 仅把 `_note_voice_handoff_input_boundary` 搬到host-turn guard前：response_input_sequence为None时没有资格可核，不能修50已复现前置问题。
- 在no-owner content/terminal上 `_begin_response_lifecycle(currentseq)`：可能把旧未见ID或迟到输出归到新PCM，破坏owner保护。
- `notify_server_vad_response_pending()`假装有speech_stopped：改变抢占与created等待语义，且blocked content fallback，与实际缺失协议不符。
- 把PCM换成conversation.item.create/input_audio或补response.create：本地item-driven代码可发送某种item不等于实际free proxy支持该音频输入协议，可能重复触发/改变ASR。没有真实协议/官方实现证据前不能当现成修法，也无需换供应商。

## 最小离线验收矩阵（待Main实现，不在本轮执行）

1. actual QueueSocket/arbiter/phrase：no-created ID content在first-write await内到达与完整write后到达；完整写只有一次，无额外create/PCM replay，bound seq等于登记值。
2. 写失败、部分写、terminal早于整批完成：不能ticket success/清waiting或认作完整输出。
3. first-write等待时新正PCM、connection/socket、authority、epoch变化；迟到旧ID：不能关联新seq；old cleanup不清新slot。
4. seen/server/quarantined ID、idless/仅output_item.added、functioncall与audio ID不匹配、未知strict profile：原拒绝保留。
5. 同sealed输入两ASR/两response：两个实例分别终结，或按首档明确后段未关联；不得“第一个结束=整段语义完整”或第二terminal误关下一输入。
6. 完整owned terminal可退役自己的waiting但host转新sid时UI双hook不动；step_timeout/localfailopen不退役成功；ordinary phrase-OFF与barge-in现有回归保持。

本意见没有设计新记忆系统或放宽Native工具评分授权。等待Main实际接口/fixture结果后再窄审；原50仍PARTIAL，阶段40尚无部署、模型、设备或真人证据。
