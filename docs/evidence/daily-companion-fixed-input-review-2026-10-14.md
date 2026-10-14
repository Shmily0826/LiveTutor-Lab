# 阶段十二固定内存输入窄审

日期：2026-10-14。唯一写入为本报告。范围为 `scripts/neko_output_only_patch.py` 的 fixed memory participant/known local draft replay、`neko_native_telemetry.py` delegation/control metadata、`neko_daily_voice_probe.py` begin/send/stop/release；为核对复用的真实controller，仅定向读取已部署 `static/app/app-audio-capture.js` 的 recovery/lease/ordinary-upload 相关片段。没有改源码、manifest、配置或账本，没有运行测试、服务、API、浏览器、声音设备或回环，没有新增Agent。

最新授权仍为必要约4%输出，不调音量，不允许任何物理/虚拟麦克风捕获，不回环。Main 报告实际module Node11、ASGI replay6、Native3与两树gate PASS，本轮不独立运行这些检查，不借它们认领新模型、实际设备/human。phase26的旧timeout仍保留。

## P2：旧probe的非PCM生命周期可以发送到新socket

`NativeTelemetry.send_current` 的audio分支委托 `sendFixedInputFrame(self.fixed_input_id, samples)`，但其他payload每次直接重新读取 `window.appState.socket`，只检查readyState。没有核原fixed ticket/socket，所以旧caller的start_session、end_audio_turn、end_session可落到其await期间接管的新socket。

最明显触发点是 probe `504–506`：先 `await observer.end_fixed_input()` 清ticket并发布release，再另一次CDP eval发送end_session。两次await之间若socket换了，旧probe会结束新owner的会话。即便新socket已有新的fixed来源，旧endFixedInput(id)返回false保护了新来源，下一步无ticket的end_session仍绕过这层保护。current socket存在不能证明旧probe仍有结束权。

最小修法：participant提供按原id/socket核对的受限lifecycle发送，或同一个JS同步closure完成“核确切旧票/current→给该socket发end_session→释放”，不在release后重新查找current来关闭。start_session/end_audio_turn也须绑定确切ticket；ping可单独保留无输入授权语义。owner/ticket/socket失效则拒绝，不向新socket补发，不使用旧ticket重新claim。

必须负例：begin(A)后await中socket替换B，旧A发送start/end均false且B发送记录为空；release A期间已有新票B，A cleanup不释放/结束B。Main只改本场输出专用delegation，不放宽server准入。

## P2：独立readiness拒绝没有使固定票永久失效

实际 `canUploadOrdinaryMicFrame` 在部署module `428` 对 `window.nekoVoiceCaptureReadiness.blocked()` 有独立拒绝。首版 `fixedInputBlocked` 没有该判据。

readiness变为blocked时，`fixedInputState(oldid)`可仍active；sendFixedInputFrame只是因为canUpload返回false而拒绝本帧，未退休fixedInputSource。readiness后来恢复，旧id又可发送。probe正常会在首次发送false时停止，但observer只看active；来源身份不能因readiness恢复自动再次合法。

最小修法：只把既有readiness拒绝条件纳入fixedInputBlocked并退休票。恢复后需显式新begin、新id，旧票保持false；不修改server，不把isRecording设true，不重放之前WAV。

必须负例：readiness.blocked=true时state inactive/sendfalse；readiness恢复后oldid仍false，只有新begin可发。异常readiness判定同样不应把旧票视作有效。

原automatic-recovery疑虑已撤回：Main指出需核完整identity后，本 Agent 精确读取module `19–35`，确认 `matchesAutomaticRecoveryIdentity` 同时要求 `independentAsrActive===true` 与 `isRecording===true`。fixed来源isRecording=false时不能匹配；变true时已有fixedInputBlocked会先永久retire。因此此前假设“fixed来源仍合法且matched automaticRecovery拒绝”的state不可构造，不应添加无身份recovery拒绝或弱化ordinary匹配。本报告只保留实际独立readiness缺口。

## 当前源码已确认的保护

- begin仅在readonly output-only标志成立、current OPEN socket、无physical recording/start、无mute/game/focus-playing/routeblocked或已有recovery拒绝状态时建立 `{id: ++localSequence, socket:S.socket}`。id只标本地participant，不声称provider utterance ID。
- 不设置isRecording，不调用capture/enumerate/SpeechRecognition，也不猜server lease generation；参与原 `resolveMicLeaseOwner/currentVoiceInputControlState/refreshMicLease`。真实controller `339–356` 比较fingerprint并递增已有voiceLeaseGeneration，输出原lease_sync字段与engaged标记。default未启用output-only时begin拒绝，普通录音owner逻辑保持。
- 每帧必须为1–480个int16样本；调用fixedInputState/ordinary-upload检查后，再核fixedInputIsCurrent和原id，核验与向确切source.socket发送之间没有await。socket替换、mute/focus/game等已经纳入的状态会清source，恢复后不会自动重建该票。
- end只接受当前id，旧id不能释放已存在的新id；局部sequence不回退、不由调用方指定。成功后refresh原lease发布owner变化，未通过赋值server字段来借权。
- probe在renderer capture保护确认后begin，再start_session；每480samples前检查failed、每send逐帧委托participant，不继续用旧Python socket上传。状态拒绝/ASR delivery failure/lease resync拒绝使发送停止，无重试；normal和finally均尝试释放。尚需修上述无票non-audio cleanup。
- sanitized outgoing control trace只保留控制/播放字段、inputFrames/inputSamples计数，没有PCM样本；接收lease/ASR拒绝status仅保留有界code/reason。trace仍有既有教学文本用于主线审查，本报告未读取或公开raw history。

## Replay与范围

`patched_capture` 仅把完整已知local draft（state检查/refresh先后顺序及send复核缺失）精确替换为当前helper；随后剥离完整anchors恢复base并要求原known SHA。unknown/重复/edited helper残留会使base hash不符而拒绝，不通过泛化regex删除自定义改动。web_app也要求known base SHA/唯一anchor。两target转换先在内存计算/验证后才写，实际replay/gate通过归Main证据。

上述两P2已分别消息交Main，首版仍标待修。本轮没有发现其他范围内可具体复现的阻断；不扩大narration/全仓/OS权限审查。修复后只精确补关闭确认并保持报告冻结，必要实际场仍复用旧0.9sWAV与既有Sky材料，不回环、不调音量。

证据层：**SOURCE REVIEW，两个P2待修**。Main现有Node11/ASGI6/Native3是其离线结果；新固定输入provider准入、自然停顿、实际输出与human仍待分别验证。未把client send成功或lease generation更新当provider已接受PCM。

## 两项P2关闭确认（精确复核，最新结论）

Main已修复。本 Agent仅再次只读原三个脚本的相关片段：

1. participant `sendFixedInputControl(id,command)`只允许start_session/end_session/end_audio_turn/ping，start仅audio；核fixedInputState、原id和fixedInputIsCurrent后使用原source.socket。end_session提交与endFixedInput释放处于同一同步JS操作。endFixedInput捕获原socket，只有它仍是S.socket且OPEN才refresh，不给接管后的新socket发布none。NativeTelemetry control/PCM均先要求已登记id，原动态读取appState.socket的fallback已移除。probe先发该受保护end_session，由同一次操作释放，已删除先release再另发end的窗口。
2. readiness.blocked已加入fixedInputBlocked，fixedInputIsCurrent据此清source；恢复后旧id没有自动重建入口，只能新begin取得新id。未新增无身份automatic recovery拒绝，原完整identity保护保持。

两项 **SOURCE REVIEW CLOSED**。原发现和当时待修记录保留；当前限定范围无剩余已知具体阻断。Main报告实际module Node新版14（含旧lifecycle、新socket、atomic end/release、readiness恢复旧票拒绝）及Native3通过，明确归Main离线证据，本 Agent未重跑。不扩为provider/设备/human验证。除追加此段外没有改任何文件，没有API/服务/浏览器/设备/账本操作。报告再次冻结。
