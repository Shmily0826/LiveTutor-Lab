# 场50连续学习与反馈边界独立只读复核

2026-10-15。只读本场raw、Native完整历史和global host log中同cid/本场时间窗的结构化study-text诊断；随后核Main提取sidecar。未改raw、源码、DB、共享记录或账本，未启动host/API/模型/音频/设备；只新增本报告。

## 原件与总体结论

原件 `benchmarks/raw/evidence/daily-companion-20261015-continuous50.json` SHA256：**`4b6d1d115aa24e4e1e5d84a397a9f7dbf702f7504405e1ccca3149a80b9b7c41`**。finalized=True，failure=`RuntimeError: voice session ended abnormally`，cleanup_errors=[]、native_observation_error缺省。Main报告唯一exec88098 exit1并自有清理；本审查未代执行进程清理。

**正式出题→同连接自然回答→唯一correct100及完整Native答案成立；整体仍FAIL_OR_PARTIAL。** 第三轮被拆成两个ASR/两个输出，之后实际收到ASR_INPUT_DELIVERY_FAILED。不是环形trace缺失，也不是单纯量具异常。场50没有重现场49答案只到WEX的短文本；不得因此追认49同一根因或已修复。

## 正式grade与完整观测

- 初始健康空pin，QA/formal均0，无预造题。第一轮actual wire study_quiz，保存题干“从 WEX 出发的箭头指向哪个节点？”与Native18字符相等，非空qid/aid、pending。第一和第二phrase delivery均generation1且result=written_waiting_provider_boundary，output==written>0；第二输入未提前更换provider物理连接。
- 第二Native ASR“我 的 答 案 是 WEX 指 向 NUD 。”与QA.user_answer及唯一formal interaction.input_text逐字一致。qid/aid/session/course经held、QA、formal metadata、accepted/complete/relay三marker匹配。after同题同attempt evaluated=True；payload/QA/last_grade均correct100，正确方向WEX→NUD。
- QA恰0→1，formal恰0→1；第三轮后这两个完整数组与第二轮精确相等（QA row_sha256=`10e28159ff40838b1c04593404916c7a05725b8aae366519e24e230516a4022e`）。后续未重评/换题。初始旧QA为空，不能冒称已有历史多行不变得到实测。
- marker accepted wall5890.660514、grade_complete5892.7971385在connection1/scope3，relay_written5893.401036在connection2/scope5；profile均lanlan_app_gemini，受控旧token取消、新tokenPCM及schedule在正式完成之后。第二app CONNECT是实际受控relay，不少计。
- 独立逐项核Native final：eventSequence=330、events长度330、observer_sequence完整1..330；binaryFrames=25等于全部audio_frame数，binaryBytes=942880等于全部bytes和。**25条中22条正PCM、3条空帧**，不是25正帧。初始binaryFrames/eventSequence均0。没有ring淘汰/补造序号。

| 轮次 | snapshot sequence | 本轮帧数/正帧 | bytes | QA/formal |
|---|---:|---:|---:|---:|
| 出题 | 97 | 7/7 | 252320 | 0/0 |
| 回答 | 215 | 8/7 | 381800 | 1/1 |
| 追问 | 330 | 10/8 | 308760 | 1/1 |

## 本场反馈边界：累计SHA正确对齐

raw未嵌入study-text，timing_log内该tag数0。独立从global log按本场cid `32e9b109` 及时间筛出47条结构化诊断，无打印原学习正文/密钥日志。Main随后提取 `daily-companion-20261015-continuous50.study-text.json`，同47records；sidecar SHA256 **`ee7b49ab9eae3ff9ae5db5f1b19d0ad73cc0b8fdb4acaeda1564eec95b6509f3`**，其report_sha256与上面原件一致，声明source-log SHA=`4276ca3b886d3ff02570999b2d9835a7268b155bcf2654780ac5cbe11d34658f`，bytes17901972。sidecar是日志提取，未改原raw，不是新的模型场。

| 边界 | 字符数 | 该完整文本SHA256 |
|---|---:|---|
| 正式feedback、grade_reply | 20 | `28a08a16fd0036f7de6e11e868f864e0c6e67a62d39b5eae9383b9c85c96ae39` |
| 实际relay裸reply写入 | 20 | 同上 |
| provider答案6个delta有序累计 | 23 | `23a44b785cc36a05c5c9356a78245aae0655ab6da78e713384c5c830c8c1a75f` |
| Omni callback、Core entry/queue/WS | 23 | 同上 |
| Native收到的答案文本 | 23 | 同上 |

provider对应generation2/response `resp_1792005894368`，最后记录stream_chunks=6、stream_chars=23、cumulative_available=True；这里用的是 **stream_sha256**，不是末个3字符chunk的sha256。actual relay envelope另有SHA=`fdb5bc5fe4faff32cbfbafce63da8a0e11c976456ec5e83b1d26384c0a03dda8`，它含封装指令，不能拿来和裸feedback比。

正式反馈“正确。WEX 指向 NUD，方向完全对。”，Native“正确。WEX 指向 NUD， 方向 完全 对。”，去掉空白后精确相等。由以上链条，本场差异发生在relay裸文本到provider转写之间，内容仅增加3空格；provider累计到本地callbacks/Core/Native没有丢字。Omni/Core诊断response_id=None，cumulative_available=False，诚实不造其累计身份；第二轮只有一个23字符callback/WS，使用其单次完整hash对齐，不给缺ID流编造provider authority。

此链不证明provider物理ACK/声音逐字等价；没有loopback/human。它也不能用来判定49未知的22→7边界，因为49没有该组诊断。

## 正常结束与最终异常的实际时点

第二轮正常source_ended activeFalse/remaining0 wall**1792005900.640**；后续speech_cancel wall5930.641，晚30.001秒。新checker据完整序列/计数、真实device正常终态及done、无后续输出接受observed_source_ended_before_late_cancel，底层支持该窄量具适配，不能写成cancel截断了第二轮答案。其strict answer receipt 20项中仅run_finished_without_failure=False，其他19项True，原整体失败保持。

第三轮有完整的以下事件，不存在“缺trace所以不知ASR”的解释：

| wall（1792005前缀省略） | 实际事件 |
|---|---|
| 953.720 | 第一ASR：“为什么这道题要看箭头尖端？”（原转写中文字有空格） |
| 953.982–954.375 | Native分块：“箭头 指向 被调用 的那 部分。” |
| 955.350 | 第一system turn end |
| 958.073 | 同token正常source_ended |
| 958.901 | 第二ASR：“短解释，不要重新评分，也不要出新题。” |
| 959.160 | Native“明白。” |
| 959.966 | 第二system turn end |
| 960.405 | 第二正常source_ended |
| **981.493** | **status ASR_INPUT_DELIVERY_FAILED，sequence330** |

异常status晚于最后播放结束约21.088秒、晚于本轮phrase写完成约30.369秒。renderer该status.reason为空；probe正确设置fixed_input_rejected/failed，并在fresh final检查后抛voice session ended abnormally。无native_observation_error，330序列完整，不能说成observer失败或ring overflow。

仅凭raw status code及这些间隔不能唯一认定watchdog/callback/owner哪一条件失败；Main正在提取具体failurecause。本报告不把时间接近30秒直接当根因证实。即使该最终异常另修，第三轮两个ASR仍不满足当前严格单轮ASR判据。

## 教学语义范围

本场正确题与答案语义清楚，第二轮反馈无49的前缀缺失。第三轮没有actual study_explain tool调用，只有Native直接短解释与ack；“被调用”是新增的调用关系含义，而本次题和图的已确认事实是箭头方向。raw不提供该箭头确为调用的证据，不能将它作为真实源码调用事实通过。也未完整回答为何应看尖端，追问教学仍PARTIAL。

## 权限、额度与结论边界

同round原件DS785→810、app74→76、tech无新增；不因余额再跑本场。raw输出专用捕获guard与禁mic/capture/loopback记录继承，实际Native接收/排程有证据；**physical_output=UNVERIFIED_NO_LOOPBACK、human=PENDING**。Main负责进程/端口及发布核查，本次未作服务或设备动作。

原raw不改，整体FAIL_OR_PARTIAL不追认为PASS。确认的新增证据是完整Native观测、正式唯一评分，以及20→23空白变体经provider累计到Native无本地截断；剩余是第三输入分轮、无证据调用语义和真实ASR_INPUT_DELIVERY_FAILED根因。报告冻结；Main若提供新failurecause仅追加精确复核。

## 最后failure线索与guard源码追加核查

Main提供的arbiter连接退出线索已独立在global log结构化记录核到：同cid `32e9b109`、gen2、wall **1792005981.232**，reason=`native phrase input delivery failed`。它距第三phrase实际completed_wall1792005951.1242325约 **30.108秒**，早于renderer status5981.493约0.261秒。该固定reason不含学习正文，未打印其它日志。sidecar47条及reportSHA绑定亦已独立核，无原件回写。

定向实际源码核查：

- `scripts/neko_phrase_input_transport.py:170–182` watchdog每0.1秒检查当前snapshot；waiting存在超过30秒时调用fail(`phrase_provider_boundary_timeout`)。flush成功后才设置waiting=(monotonic,sequence)，note_boundary仅在相同waiting sequence且current snapshot时清waiting。
- actual `_transport._notify_turn_finished` 首先检查connection_still_ours和still_ours，再检查 `_host_turn_is_still_ours`；host turn不同会直接return。其后才在no-server-VAD且step_timeout=None时调用 `_note_voice_handoff_input_boundary(expected_sequence=_voice_handoff_response_input_sequence)`。
- `_host_turn_is_still_ours`有可读的原/current host turn id且不同才False；UI结束/rotate的guard是保护新Core speech id的既有围栏，不能为了退役输入waiting一律去掉。

因此存在明确的源码候选因果路径：同一sealed本地输入被provider分两次ASR，Core speech id推进；实际owned response终结时host-turn guard拒绝整段，连输入boundary也被跳过，waiting继续到30秒后fail。时点与本场高度吻合，**但raw未保存该次terminal的driver.waiting sequence、authority、response-input sequence和host-turn比较结果**，本次也未做Main将执行的actual AST重放；仍不能把候选机制升级成已证唯一根因。

Main拟将“确证当前sealed输入的boundary退役”与“UI双hooks保护新host turn”区分：前者仅same driver/waiting seq、本conn/current authority、actualresponse-input seq匹配时在host-turn guard前完成，后者仍严格守原guard；step_timeout/local fail-open、新PCM、更换conn一律不借此退役。此为待实现/待审设计，本报告未更改代码，未认领修复或实时通过。再次冻结。

## 候选机制更正（后续Main实际离线复现，保留上段调查史）

Main随后用实际native QueueSocket/Core phrase fixture报告更前置机制：无需host-turn改变；lanlan_app_gemini never-announcing response在arbiter idle/no-owner路径，ASR后即便收到有ID transcript和completed response.done，也未调用_begin_response_lifecycle，response_input_sequence=None；driver仍waiting seq16，推进31秒后actual watch报phrase_provider_boundary_timeout。Main同时在50本场实际arbiter记录核到两轮rejected_no_owner/idle与no_owner_release，未见host-newturn日志。

这是Main报告的实际本地fixture证据，本次未独立重跑该fixture。它比上段hostguard候选更精确：没有response-input seq时，即便把原boundary代码前移也无法核对真实输入，反而可能把旧响应冒认为新输入的边界。因此**不实施上段先前提出的hostguard前挪boundary方案**；上段保持为当时未证猜测，不能在当前结论引用成50已确认根因。

下一最小修复必须从实际no-owner协议路径取得足够证据，同时保留新PCM、foreign conn、local fail-open、旧owner的拒绝；不能因收到有ID completed就补造seq或一律清waiting。本报告不预审尚未给出的新实现，不宣称provider能力或设备通过。整体50 FAIL_OR_PARTIAL保持，再次冻结。
