# Output-only 固定输入与 MicLease 准入诊断

日期：2026-10-14。本次唯一写入为该报告。只读实际 source host 的 `main_routers/websocket_router.py`、`main_logic/core/asr_runtime.py` 及 raw phase26 JSON 的元数据/事件类型；不读取或输出学习 history、模型教学内容、秘密或原PCM。不改源码、不运行测试、服务、API、设备、回环或额度。最新授权仍为必要约4%输出、不采任何物理/虚拟麦克风、不回环；Main 记录 DS594/app57/tech0，本轮不直接操作账本。

## 实际证据与确定范围

`benchmarks/raw/evidence/daily-companion-20261014-output-phrase26.json` 已 finalized，output_only=true、capture_devices=false、room_microphone=false、loopback_enabled=false；capture policy receipt.status=installed。一次 turn_timeout=true，Native trace binaryFrames=0。wire_trace 恰有3条 session.update，没有 audio append；Native trace 类型包括一次 session_preparing、一次 session_started、两次 status，但没有 ASR/工具/PCM事件。本轮未输出三类学习状态字段或 reply。

**源码确认：owner=none 足以把所有固定 PCM 在 ASR 入队前拒绝。** 然而该 JSON 的 Native status/session_started trace 只保留 wall/direction/type，没有 status message/detail，也未记录 voice_input_control owner/generation。不能由两条 status 反推出 owner_none，也不能独立断言 phase26 实际 owner=none 或它是唯一原因。现有症状与此路径吻合，下一步应获取定向控制面确认，而不是重复21秒发送或绕过 ingress。

## 为什么 start_session 成功仍可能无输入

1. `websocket_router.py:691–708` 将 voice identity claim 延后到实际 voice engagement，避免仅打开第二窗口就抢录音。`711–749` 首次 claim 调 `_begin_voice_input_connection`，后者在 `asr_runtime.py:5312–5333` 初始化 generation=-1、synchronized=false、owner=none、suppressed=true，并清旧输入同步。
2. audio start_session 在 router `1225–1249` claim 后检查 `_ensure_voice_input_session_authorized`。asr `5488–5489` 如果已经 synchronized 就直接返回 True，**不检查 owner 或 mute/focus**。因此先收到合法同步 owner=none snapshot 后，session可以成功启动，但 PCM仍被禁止。
3. 未收到显式 control 的 legacy 冷启动有特殊兜底：`5490–5509` 只有 control_seen=false 才把 generation=0/owner=core 授权。它是旧客户端兼容行为，不是 output-only 固定输入应依赖的协议；Native renderer 发送过 lease控制后就不能据此假定 core。
4. `_voice_input_accepts_pcm:1476–1500` 要求 synchronized、owner为core/game、registry激活对应 builtin consumer 且 accepts_input=true、无 hard mute/focus/input suppression/external suppression，preview隔离也拒绝。`_apply_voice_lease_state:5189–5201` 把 owner_none 明确加入 suppression。
5. 实际 queue 入口 `3483–3485` 在创建 `_QueuedMicFrame` 前核该判据；不满足时发有界 resync提醒后return，尚未经过DSP/VAD/collector/provider。后续 `4748/4765` 的native发送仍会重查，不能只改最外层一次。

所以会话 ready、WAV sender成功调用send、capture guard已装、session.update wire都有记录，均不能当实际 ingress/transport accepted 证据。

## 合法最小协议与时序

现有控制入口无需启动任何设备。router `1404–1445` 同步处理 `voice_input_control`，因此控制await完成才继续处理该socket之后的PCM。最小形状为：

```javascript
// nextLeaseGeneration must come from this Native socket's real lease controller.
// It is an integer strictly above that controller's previously submitted generation.
const command = {
  action: 'voice_input_control',
  event: 'lease_sync',
  lease_generation: nextLeaseGeneration,
  engaged: true,
  owner: 'core',
  hard_muted: false,
  focus_suppressed: false
};
```

上例的 nextLeaseGeneration 是交给 Main 从实际controller获取的变量，不是已确认存在的getter。generation 必须使用**当前 Native socket 所属的实际 lease controller 单调计数**，传实际整数；不猜0/1、时间戳或一个“足够大”的值，也不搬旧Python controller的generation。asr `5523–5528` 要求generation严格大于当前值；`5540–5551` 要求owner为none/core/game且两个 suppression字段为真实bool。router `1416–1426` 对 never-engaged socket 的 engaged=false idle snapshot直接忽略；声明engaged=true表示这个授权固定输入sender真正承担逻辑输入来源，不表示启动硬件麦克风。

Main 的最小接法是：在已安装capture保护的**实际当前 Native socket**，为已有固定 WAV 内存/WS sender 显式登记逻辑 core 输入来源，沿现有 MicLease 控制器发送其当前完整 snapshot；先控制，再start_session/确认当前owner，最后从同一socket发送PCM。不得从旧controller创建新socket夺权，也不得借过去tool owner或把MicLease/registry guard改为无条件True。

frontend capture仍保持硬拒绝/实际skip；“逻辑固定输入来源已engaged”应与“mic设备started”分离。不要为了让现有refresh逻辑得到core而调用startMicCapture、getUserMedia、SpeechRecognition、虚拟设备或fake capture flag。固定输入结束/取消时，用该controller下一generation发送owner=none的lease_sync或沿现有连接撤销路径释放；不保留永久core授权。

**待 Main 核的实际前端接点：** 当前允许读的两份后端文件没有给出 Native MicLease计数getter/注册固定输入来源的方法；本报告不虚构诸如getMicLeaseState之类接口。Main应定向核现有controller，并防止其仍认为idle而在focus/reconnect等事件重新发布更高generation的owner=none。不能通过无条件忽略这些控制绕过新输入所有者；output-only固定来源应参加同一控制器状态计算，状态不一致就停止输入、恢复显式握手，不无限lease_sync。

## 接受确认与失败停止

当前 control success只返回内部bool；router `1446–1455` 失败发 VOICE_INPUT_CONTROL_REJECTED，没有从这两份源码发现包含owner/generation的正向ack。start_session成功也不足以确认owner。Main可增加默认OFF/output-only局部的有界控制面诊断/ack（不含PCM/history），报告实际当前connection归属、owner、generation、synchronized、suppression与registry accepts；必须在await后重查仍为原socket/manager，不能回发新owner的秘密或给旧socket借权。

PCM因无lease被丢时，asr `3346–3357` 既有status.code=VOICE_INPUT_LEASE_RESYNC_REQUIRED，details.reason为owner_none或lease_unsynchronized。`3369–3394` 对 deliberate hard mute/focus/game/主动revoke抑制该提醒，避免重开本来被禁止的输入。这些拒绝应使固定输入probe立刻终止该发送，不重新设置owner逃避mute/focus/game，也不将无status误当已授权。

已有scope保护必须保持：router `961–1000` 对 superseded/vacated连接仅允许严格voice-owner分支或drop；当前Native/display socket与voice-owner不是可互换身份。若发生新的窗口夺权或连接更换，本轮缓存/PCM应失效，不能重放旧21秒固定输入。成功握手也不能豁免这些条件。

## Main 下一最小验证

先做实际router/asr方法离线负例：同socket synchronized owner=none时start可成功但PCM不入队；按真实单调计数lease_sync core且registry有效时PCM入队；低generation、旧socket、external/game/mute/focus拒绝；idle辅助窗口engaged=false不夺权；固定来源结束释放；await期间替换owner不发旧PCM。再让一次必要场保存 sanitized control ack/drop reason、队列/LOCAL_ACCEPTED/真实wire成功计数，确认第一段输入准入后才完整发送。无需复跑phase26同样无诊断的21秒timeout。

本报告为 **SOURCE DIAGNOSIS + RAW EVENT METADATA REVIEW**。确定none-owner规则与协议字段；phase26实际拒绝原因尚未被该raw payload直接记录。未认领provider自然停顿、实际扬声器或真人体验通过。报告冻结；Main负责实际前端接点、诊断/实现/测试、在线与额度。
