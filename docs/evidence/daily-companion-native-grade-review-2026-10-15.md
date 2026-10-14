# 阶段24 Native 正式评分链独立审查

范围：Main 新 `neko_native_grade_patch.py`、`test_neko_native_grade_route.py`，及为核对真实协议边界所需的既有 `_transport/_tools/_response_arbiter/_protocol_capabilities`、Core `turn/tool_calling/tts_lifecycle` 精确片段。只写本报告；未改共享源码、patch、测试、manifest、四记录或账本，没有服务/API/host/浏览器/音频/设备。另一独立审查者 capacity 失败由本 Agent 接手，没有更换模型或新增 Agent。

结论截至本次源码：发现一个输入 authority P2，Main 已修并增加负例，SOURCE/OFFLINE 关闭；其余限定 relay/hold/dedup 逻辑未发现第二个已证实的 P1/P2。未部署版本不能称 runtime/model/device/human 通过；Main 首次整套候选 patch replay 的 turn.py 冲突仍由 Main 定位，不借方法级测试宣称部署通过。

## 初稿 P2：ASR 时重采控制权，可能认领较早音频

初稿首次 speech pin 只保存 connection/question/last_speech，`_take_study_grade_asr` 到 ASR 才采 owner/token/frames，Core `_make_study_input_handler` 也在 ASR 时采 activation。若首帧与 ASR 之间同一 client/connection 的 activation、websocket 或 tool scope 已换，旧转写可用新 owner 继续；四题目 ID 不变时 status 检查不能拒绝。原10case只覆盖 claim 后新 speech，未覆盖该窗口。

已即时报 Main，Main 确认没有既有真实边界保证先拒，并采纳修复。最小必要做法是首帧固定 Core activation/socket 与 provider/token/scope，ASR 核原绑定；不能通过 ASR 时重新读取“当前 owner”、容忍任意 scope+1 或用观察序号伪造 utterance ID 解决。

## 新版关闭核对

- 首帧增加同步 `get_study_input_authority`（Core activation + websocket）以及 ws/token/scope 保存。SQLite pin 仍只读一次；换题不追新题，replay 与长间隔重叠继续 failclosed。
- ASR 验 provider/connection/token/scope 以及首次 authority 后，才允许 pin；receipt 的 input_authority 只有绑定仍 current 才提供。Core claim 再核 current authority、activation、socket、token、frames 和实际 owner。ASR 回调到 claim 之间出现新帧，不得给旧 ASR 安装新 hold。
- scope 的唯一一次许可只加在两处实际协议分支：`input_audio_buffer.speech_started` 的原 note_user_turn_started 前；无 server VAD 且原 `_raw_transcript_was_already_scoped` 为 false 时，completed 分支的原 note_user_turn_started 前。没有制造 onset 或把 sequence 叫 utterance ID。foreign scope 变化、重复许可均毒化 pin，新的连接才解除歧义；未把合法 provider response host-turn pair 当输入 turn ID。
- 没题但 input authority 仍确认时，可 hold 原物理输出并发“没有评分”状态；pin为空不会读最新问题强行补齐。新 scope 解除该旧 hold。foreign authority 的旧 ASR 不取得该许可。

新增 actual methods tests 覆盖 ASR 前 activation/socket/scope 各变更：pin=None、0 evaluate、0 QA；一次明确协议 scope 许可成立，第二次拒绝；原 owner 下 unknown pin 诚实无评分 hold；ASR 后新 frame 不装旧 hold。初稿 P2 CLOSED / SOURCE+OFFLINE。

## Relay / hold / 正式数据核对

正式执行使用既有注册的 plugin:study_companion study_session/status 与 study_answer，四 ID 来自首次 pin，普通 answer 状态必须 pending 且 attempt 等于原 attempt；correction 必须 evaluated，并由正式 entry 产生新 attempt，不能覆盖原 wrong。原 ASR 全文传入，不截取为伪答案。产生的 local ID 只用于 Core→现有 SDK 调用，没有伪造 provider function_call_output；发给 provider 的是受控新连接上的普通文本消息。

claim task 背景运行，不阻塞 provider receive loop。old physical token 精确 cancel；重连有 swap/frame lock 和 timeout，先 retire 原输出，再 close/listener-drain/一次 connect/listener-start，逐 await 检查 claim。新连接限定 old+1，不认领更高 generation；最终闭包核 provider/token/scope 和 frames/activation/socket。再读取 actual status，核正式结果 qid/new aid/course/session/evaluated 后，才经 existing arbiter 与实际 send_guard 发送。失败没有 PCM replay 或无限重连；history 已提交但不能出声时给诚实状态。新的输入使迟到发送拒绝，并避免关闭已经取得新输入的新连接。

controlled relay 中同一 owner 的 provider study_answer 再调用复用原正式结果；quiz/explain/summary 在该 grading claim 内拒绝。不是从自由口头 verdict 回写 DB。ticket.sent 仅表示本地发送完成，不等于 provider ASR/ACK、Native queue stop 或用户听见。hold 回调与既有 `_tts_output_is_current` 的材料 gate 复用，但首次 ASR **之前**的自由输出时序和真实设备队列仍不由这些方法级测试覆盖，应由主线已有 speech gate/实际场证据单独核验。

## 独立测试与局限

系统 `python -B scripts/test_neko_native_grade_route.py` 首次在导入 SDK 前因缺 ormsgpack/msgpack 失败，非产品失败，未安装依赖。Main 指定既有隔离 Python 后独立运行：

```powershell
.\benchmarks\raw\neko-product-host\.venv\Scripts\python.exe -X utf8 -B scripts/test_neko_native_grade_route.py
```

16 PASS，3.231s。真实 Core admission/tool dispatch 方法、实际 SDK callback/kwargs/serializer、产品 entry 与临时 SQLite、实际 arbiter 类参加；模型是 AsyncMock/本地 harness，Client connect/close/send、listener restart 和 peripheral UI/bus 是 doubles。并非实际 Core 全实例、真实 RNNoise/音频 first-frame 全管线或 provider。更正 case 证明两 QA/新 attempt/旧 wrong 保留；其第二次 relay 因 fixture 复用固定 token 发 RuntimeError warning，测试并未断言第二次 relay_written，所以不能借其 PASS 宣称更正声音已通。

另外 fixture `_ensure_response_arbiter` 直接构造 arbiter，采用默认 STRICT profile；实际 LANLAN_APP `responds_to_conversation_items=True`，会走 item-driven 发送。因此现两 wire event 断言仅证明 strict local profile，不证明 free profile 的具体事件序列。已告知 Main 最小补一个 actual LANLAN_APP capability case，预期 item-driven 仅 conversation.item.create、guard与 sent/hold 行为不变；未据此虚构产品错误。

已知 legacy `speech_active=None` 与 barge-in replay 没有可信 pre-await pin，仍明确 failclosed，不把正常 lane 扩称已经自动评分。实际 provider/Native 发声、ASR首帧authority全管线、ordinary真人打断和最终体验待 Main；主线 Goal 继续，其它工作不因这些边界停下。

本次审查时 SHA256：patch `5da82bfb5debdb1fa0dfa4aeaee80e8643e55fd91238552d696405661f72f9f5`，tests `7e8163ab3a02c4e6a950e9baa8cca52ed358b39fdb1f046181f166a1798caf30`。Main 如继续修复/补测试，以后续精确追加的源码与独立结果为准，不覆盖本段原证据。

## 最终17case与 stable anchor 确认

Main 已补实际 LANLAN_APP capabilities 的 arbiter case；本 Agent 使用相同已有隔离 Python 再独立执行最终整组：17 PASS，3.426s。新 case 核 `relay_written=True`、wire 只有 `conversation.item.create`、hold 已释放、evaluate 恰一次；这关闭上述 free-profile 本地覆盖缺口，仍不是 provider ACK 或 Native PCM/queue/device 证据。

最终 audio hold hook 使用两 host 版本共同存在的 `handle_audio_data` docstring 为精确锚，追加自身 gate；没有把某版本特有的 text-only 三行强加给另一版本，既有 dev_text_only gate 原样保留。input callback 安装在 session_lifecycle 的既有 owner-guard callback loop 之前，后续 loop 包装当前 handler，并未覆盖成旧 handler；native pin reader 和 authority getter 为同步原 session 绑定。

最近 authority/gate/relay 增量未发现新具体 P1/P2；初稿输入 authority P2 已有代码与定向离线负例关闭。Main 自报两真实 host **副本**完整 apply_to 30 文件首次/幂等/AST 通过，本 Agent 未独立运行该迁移，也未写实际 host；当前不能由此称已部署或模型设备通过。最终 patch SHA 仍 `5da82bfb5debdb1fa0dfa4aeaee80e8643e55fd91238552d696405661f72f9f5`，tests SHA 更新为 `60f01ffffcc29821f57c4c7d86b5c35f6696e09dd62a471ef3e91908fd8e3938`。本报告冻结，余下实际链由 Main 继续。

最后 default-OFF 隔离增量精确复核：session_lifecycle 安装两个 getter 和 `on_input_transcript_with_route` 的 if 现同时要求 `hasattr(session, "_capture_tool_task_owner")` 与 `NEKO_STUDY_AUTO_GRADE == "1"`。feature OFF 不会新绑 getter 或替换普通 callback，也不会让旧 handoff fixture 依赖新增 Core 方法。只有该安装条件变化，方法 body 未变，本次按 Main 要求不重复17case。Main 自报重新 temp 30 文件 AST/幂等通过，尚未由本 Agent执行迁移或部署。patch 新 SHA `88486379352e021604e93aa250fb59364363b90172fa6cc01c243e24f8f0565b`，tests 保持上述 SHA。此精确源码确认后再次冻结。
