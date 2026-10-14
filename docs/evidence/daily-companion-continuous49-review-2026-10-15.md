# 场49连续学习独立只读复核

日期2026-10-15。仅核原件 `benchmarks/raw/evidence/daily-companion-20261015-continuous49.json` 及 telemetry ring/实际播放器 cancel 精确 callee，未改实现、raw、数据库、共享记录或账本；未启动服务、在线调用、声音或捕获设备，未重跑场景。

原件 SHA256：`60988217eff6581fa038736e6d6cde71283ca4fb778f808894455c03da3e1148`，独立计算一致。finalized=True、failure=None、cleanup_errors=[]；Main报告 exec30272 exit1、自有进程结束且端口无 listener。本次只读证据，不独立认领进程清理执行。

## 窄结论

**正式连续出题→自然回答→唯一评分成立；整体体验仍 PARTIAL。** 答题 Native 文本只有完整反馈的前缀是真实缺口，不能归 trace 截断。第二轮 strict terminal=False 则存在量具误拒证据：同 token 已真实 source_ended，30秒后被空队列 cleanup cancel 覆盖。第三轮 trace 丢掉 ASR 和回复前半段有明确 ring eviction 证据，不能据最终 snapshot 缺项判成服务端没有 ASR，也不能反过来认领完整第三轮回复验收。

## 从底层记录复核正式链

1. 起始 readonly snapshot ok=True、QA/formal均0；empty pin确有 course/session 且 current_question健康空对象，无预造 pending。
2. 第一轮 wire实际 `study_quiz`（wall1792003509.710）；Native题干“从WEX出发的箭头指向哪里？”与保存题一致。题有非空 qid/aid、evaluated=False；QA/formal仍0。该轮实际5正PCM帧/222440 bytes另1空帧，最终同token source_ended/active=False/remaining0。
3. 第一和第二输入实际 phrase delivery generation均1、result=`written_waiting_provider_boundary`，输出/已写样本分别140610/140610与75264/75264，均在各自窗口。它们证明本地同连接写入，不是 provider ACK。第二 ASR为“我 的 答 案 是 WEX 指 向 NUD 。”，完整保留在正式 interaction.input_text 和 QA.user_answer。
4. 三个实际 marker按 accepted→grade_complete→relay_written，输入四ID完全一致；accepted/complete在connection1/scope3，relay在connection2/scope5，新token不同，profile均实际lanlan_app_gemini。grade_complete wall3562.4322157，旧token cancel wall3562.446，新token正PCM从3565.648开始，其后同token schedule。不能因存在受控第二CONNECT就说第一/二次输入不同连接。
5. QA从0恰增1，formal answer_evaluate从0恰增1；QA question投影的题干/qid/aid与held一致，session一致，formal metadata course/session/qid/aid一致。after同question/attempt evaluated=True，last_grade与QA/formal payload均correct100。反馈“答对了：WEX 是起点，箭头终点是 NUD。”、reference“从WEX出发的箭头指向NUD。”与题和用户答案一致。
6. 第三轮后 QA完整对象（含row_sha256）与第二轮相等，formal完整对象也相等；qid/aid/evaluated/last_grade保持，没有重复grade或换题。这里原QA为0，旧QA保留项是空集条件，不能冒称已验证有历史多行不变。

answer_receipt 20项中19真、仅native_terminal=False，与以上底层事实相符。三个 completed turn总判据为False、整体FAIL_OR_PARTIAL保留；不能用failure=None/正式评分成功代替所有体验通过。

## 问题一：答案短文本与30秒后cancel须分开

第二轮snapshot仅172条，首事件仍为本场安装初期，未达到ring上限。实际唯一 gemini_response（wall3566.306）只有 **“答对了：WEX”**；provider该response只有1条audio_transcript.delta，6条audio.delta，response.done=completed。因此回复短文本不是最终trace丢前缀造成。正式entry反馈完整，Native文本与它不等价；是否实际PCM里有未出现在文本中的词，本场无loopback/human，不能从帧数或文本推断听见了完整反馈。

该轮6正PCM帧合计169320 bytes。更重要的是完整trace记录：

| wall（1792003前缀省略） | 实际事件 |
|---|---|
| 566.301 | Native audio_done，speech_id为本轮 |
| 566.308 | system turn end |
| 568.559 | 同新token playback active=False、reason=source_ended |
| 598.567 | 同token playback active=False、reason=speech_cancel |

最后cancel在已排空source_ended后 **30.008秒**，下一轮输入要到610.737才开始。故不能把它直接写成正在播放的答案被cancel截断；final playback被该后续事件覆盖，才使只看最终reason的native_terminal拒绝。

精确源码：`static/app/app-audio-playback.js:391` 的 STUCK_SPEAKING_FALLBACK_MS=30000；`maybeArmStuckSpeakingFallback` 仅在队列全空而 isPlaying/assistantSpeechActiveTurnId仍粘着时计时，回调重新核空队列后dispatchAssistantSpeechCancel；`neko-assistant-speech-cancel` listener（约1349行）统一发布speech_cancel并清标志。时间与该路径高度吻合，但本raw未记录cancel source或fallback:fire诊断，**尚不能唯一认定这个caller**。亦不能将该cleanup cancel当真人打断或provider主动截断。

最小后续：先复用现有日志定位fallback source；量具可另保留窗口内同token/已实际turn-end后的有效source_ended终态，并将其后的无新PCM空队列cancel单独诊断，不能简单允许任何speech_cancel替代正常结束。短Native文本问题仍须独立修复，即使terminal量具收紧适配，也不能因此把本场整体追认为PASS。

## 问题二：第三轮500条ring丢证据

`scripts/neko_native_telemetry.py:20` 实际上限是 **500**，超过即shift最早一条，并非300。第三snapshot恰500条，最早wall1792003632.110，晚于本轮输入3610.737和两次provider ASR completed **3623.838、3629.026**。wire明确记录两次不同转写观察，不能伪造成单ASR/单provider utterance。

最终ring中198条native_speech_playback_state＋198条speech_playback_state，另有9pong，足以挤掉前面ASR/文本/PCM。保留audio_frame仅34条（33正＋1空），但本轮累计binaryFrames增量45；这是累计计数与截断事件窗口不同层级，不能把保留34条当全部45条。reply拼接只剩“在箭 尾，尖端指向的是接受 方。……”及后段；bubbles=[]，没有另一个完整UI文本来源可补。

第三轮实际存在study_explain调用、provider两个completed输出response及后段Native PCM/排程、最终同tokensource_ended/active=False/remaining0；但凭该snapshot不能独立恢复完整ASR、完整回复或所有帧时序。最小量具方向是保留每轮增量semantic事件/关键收据，限制重复heartbeat/pong挤占，而非仅放大无限ring；仍不改provider owner/工具或runtime。未在本轮实现。

## 权限、额度与验收范围

raw记录output_only=True，8API捕获guard installed/captureBlocked=True；room_microphone/capture_devices/loopback_enabled/volume_changed均False。同round DS757→785、app72→74，tech无新增；第二app连接对应受控relay，不能少计。原件未回写，本审查无额外请求。

确认的真实层：角色出题、同连接自然ASR、本地claim→正式entry/SQLite唯一correct100、后续不添grade、Native接收PCM与排程/结束收据。未确认层：完整答案声音内容、完整第三轮语义及物理输出。**physical_output=UNVERIFIED_NO_LOOPBACK，human=PENDING**。保持原raw总体PARTIAL，不为了关闭量具项重复付费跑原场。

本报告冻结，仅本文件新增。
