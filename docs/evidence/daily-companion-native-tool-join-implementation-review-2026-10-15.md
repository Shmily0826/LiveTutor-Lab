# 阶段42：隔离 Native 工具同槽续接原型审查

日期：2026-10-15。范围：`scripts/neko_native_tool_join_patch.py`、`scripts/test_neko_native_tool_join.py`，以及精确相关 actual `_tools` / `_transport` / arbiter 和阶段40隔离 producer。仅 SOURCE / OFFLINE；未接生产 patch chain、未部署宿主或 manifest，不是上线批准。

## 初次审查结果

独立运行 Source venv：

```text
python -X utf8 -B scripts/test_neko_native_tool_join.py
Ran 4 tests in 1.357s — OK
```

四场确实通过实际 provider handler→raw task→collector→实际发送路径，证明简单工具、并行兄弟、既有 ASR scope 唯一 +1 透传，以及未知/已写 call output 拒绝。工具/Socket 为本地 fixture，未使用模型、provider、服务或音频设备。

发现一个需修 P2；正向四项不覆盖它。Main 正在补负例，本报告尚不批准生产接线。

## P2：缺失真实 wire call_id 仍被合成 ID 接纳为 Native continuation

原型 `capture_native_tool_origin(call_id)` 声称需要 actual bounded call ID，但调用它时只剩 `ToolCall.call_id`。实际 `_transport.py:3865–3870` 在 wire 没有 call_id 时，对这个 raw handler 直接合成 `glm_{response_id}_{output_index}` 或 timestamp ID；不是只在 GLM 分支合成。新 wrapper 未携带“来自原 wire”的资格，因此 LANLAN 缺 ID 事件也能登记、执行工具并把合成 ID 写给 provider。

独立小重放复用当前 `NativeToolJoin` fixture，走实际 handler；事件只有 type/name/response_id/arguments，明确不含 call_id。结果：

```text
wire_call_id_present=False
executed=1
written_outputs=1
synthesized_id_written=True
same_native_slot=True
```

之后喂真实 ID-bearing audio 与 completed terminal，ticket 仍能正常结束。这个终态不能证明那条 synthetic-ID function output 有 provider 归属；本地接受路径已越过接口承诺。

最小修法：在原 provider 事件入口、合成 fallback 前保留真实 call_id 资格，随该次 owner/调用携带，Native join 只接受原 wire 的非空有界字符串 ID；缺失/非法真实 ID 应拒绝此 Native continuation，不执行有副作用的工具。不能按 `glm_` 前缀猜真假，也不能把 response_id 或 terminal ID 当 call_id。其他 provider 原有合成 ID 兼容路径不应被该窄原型无故扩改。

## 已核实现方向与尚待覆盖

- 原型 origin 为原 `_QueuedResponse` 私有对象，`_native_tool_owner` 核原 slot/current/connection/interruption/terminal 与原 admission callback；原 producer callback 联合原 driver epoch、authority snapshot 与 input sequence。它是本地资格，不是 provider ACK。
- ingress capture 后用 dataclass replace 保留 origin；已有 ASR +1 recapture 和 unannounced owner 重建显式透传。entry/collector 检查同 origin、所有 entry owner current、result/entry call ID 集合完整；capture 禁止重复并限制32个 pending+written ID。
- 工具执行前 `wait_native_tool_input` 等原 ticket.sent，等待前后再核 origin；结果不再 enqueue 第二 ticket。实际 sender 检查 send_event literal True，join 原 slot 8秒写预算，每 await 前后重新核 current；失败不会回退重发。以上实现方向对应阶段40互等，但取消/写中退休等负例仍需独立补证。
- 30秒总 start wait 与5秒无工具 announcement 分开；有效 pending 工具可等待总期限，输出完成后恢复短 content-start 等待。producer 本身仍有约30秒边界 watch，两个计时的起点与最终失败行为应实际 fixture 验证，不能只看原型循环推导超慢工具通过。
- `normalize_ordering_helpers` 只接受 exact 原 HELPERS 应用本原型增量后的完整块；否则交回已有 normalizer。当前四例 staged canonical AST/state/二次 apply 检查通过，尚需未知 helper body 拒绝负例，不能据此宣称所有历史迁移可用。
- 旧 parent terminal 不能开始 ticket，function-call ID 不匹配 terminal 的原 capability 未放宽。真实 content 开始后、多 ASR/第二 response/延迟旧工具事件如何无歧义归属，仍超出这四例；同连接时间接近或后来的 current seq 不足以补认。

下一轮定向范围：缺真实 call ID；32/33上限；partial/cancel/new PCM/旧 ws/gen/authority；等待原 ticket.sent 时失败；tool执行超过5秒但未过总期限；8秒 output timeout 与不重放；并行一兄弟失败/abandoned；锁等待与 socket await 内退休；未知 normalizer 内容。它们均可使用实际模块/QueueSocket 和时钟 seams，不需要在线或设备。

## 初次审查指纹

| 文件 | SHA256 |
|---|---|
| `neko_native_tool_join_patch.py` | `82a8510aa176deda9a3f8f28936366ac97fae711f361c351d9270ed97faf37c4` |
| `test_neko_native_tool_join.py` | `35a6b957a8e9819f8ba4e58156c82260ca22a5d425b6464366b8fc2c393ebc3b` |

原始阶段40死锁、原49/50 PARTIAL 与全部运行时/physical/human边界保留；本报告不改变它们。

## 修后复审：24项通过，wire-ID P2关闭；新输入取消等待仍有P2

复审冻结对象：

- patch SHA256 `ce2186431e71284bd99dbbcb9bc79035dc20e550da35c5683aca2132b3f4e122`
- test SHA256 `ee4489aeaa551b3f8a32b0a6c2d768147569a5c6ade2d2fd0a46f3a7c35c443e`

独立运行同一 Source venv 命令：24 tests PASS，21.216s。包括实际 provider handler、并行与唯一+1、完整原PCM写入等待、部分PCM不执行、literal True失败、锁/旧socket、普通无origin路径、32/33上限、并行取消/混origin、实际8秒输出预算、content-start/完成后的迟工具拒绝、exact normalizer拒未知等。Main另报在组合actual模块下原自动20、phrase20、handoff12通过；本次没有重跑这些套件，不把他方执行记为独立执行。

原 P2 已 SOURCE/OFFLINE 关闭：实际 handler 在 `ToolCall.provider_meta["native_wire_call_id"]` 保存原 event 值；capture 要求真实非空≤1000字符字符串与内部 call_id 等值。缺 wire ID 在工具执行前失败关闭，不再把 fallback 合成 ID 当实际身份；合法原 `glm_` 前缀仍可通过。原初稿缺陷与最初4项通过记录保留。Main曾有22项中一个missing-ID测试读取已清除的 `_current` 导致 fixture ERROR，修为保存原owner后24项通过；未因此修改产品资格。

### 新P2：pending工具被新PCM退休后，Native start等待未观察取消，下一整句8秒写失败

新 `_wait_native_audio_started` 只等待 `owner.ticket.started` 与 `native_tools_changed`。它未等待/检查 `owner.interrupt_event`、`owner.interrupted`，也未在循环中主动处理 admission 已失效。工具 pending 时继续按30秒总期限等待。

实际隔离 producer 路径不同于 `cancel_current(..., timeout=3)`：`accept` 收到递增 input sequence 的新 positive PCM 后，清原 waiting 并 cancel response_waiter；其 CancelledError 分支调用 `cancel_response`，该函数调用的是 `arbiter.cancel_ticket(ticket, wait=False)`。实际 arbiter 此时标记 interrupted、置 interrupt_event 并发送精确旧 ticket cancel，但不会等待3秒完成或升级。新 start等待没有被这个 interrupt 唤醒。

独立stdin小重放使用当前 actual-module `NativeToolJoin` fixture，不修改测试文件：第一phrase完整提交，工具 handler 保持等待，喂一帧新的正PCM，随后正常喂完整下一phrase并等其真实 writer。没有注入provider cancel ACK/terminal，没有改超时常数。

```text
after_new_positive:
  old_interrupted=True
  old_still_current=True
  old_ticket_done=False
  cancel_written=1
  pending_tools=1
after_new_phrase:
  wait_seconds=8.0
  fatal=True
  delivery_result=failed_without_retry
  failure=phrase_write_failed
  audio_batches_written=1
```

因此现有 `test_new_pcm_while_tool_runs_cannot_receive_old_result_or_boundary` 只证明40ms短窗内旧结果被抑制、新buffer保留；不能作为下一输入恢复通过。新增pending把原短announcement等待扩为30秒，这个取消缺口现在足以使新整句在原lane后等满其8秒预算，并关闭连接。不能将它描述为已经自动沿用原3秒cancel/escalation。

最小修法方向：让该原slot start等待观察精确旧slot的interrupt，并进入既有有界cancel/升级的安全处理；未知无ID响应不能直接释放lane给新输入，也不能靠假terminal清成功boundary。复用原cancel逻辑而非一律忽略旧owner；补“held工具→新PCM→完整新phrase”实际场，区分正常有ID terminal可安全结束与无归属终态必须及时失败关闭。取消时不能清新buffer、重放PCM或让旧工具输出写新slot。

### 两个30秒计时与批次失败的限界

arbiter30秒 start总预算从原ticket已sent后进入 `_wait_native_audio_started` 起算；producer等待30秒从 flush建立 waiting tuple 起算，两者只隔调度点，并非一个共享deadline。arbiter到期还要走 cancel grace，producer watchdog可能先触发 `phrase_provider_boundary_timeout`。现有缩短总期限测试证明arbiter pending不会无限续命，但不是30秒竞赛双方都已协调的证据；本轮没有人为等待两个完整30秒或冒称精确先后次序。

批次取消/混origin/部分output写入均保持原Native失败而非成功或重试。`reject_native_tool_origin` 在原slot已因新input admission失败时主动不操作它，避免触及新owner；这项保护应保留，但正因如此不能靠它唤醒上述已退休slot的等待。新取消修复须独立处理原slot的等待生命周期，不放宽该身份检查。

当前结论：24项 SOURCE/OFFLINE 通过、原wire-ID P2关闭；取消等待新P2仍未关闭，不建议接生产链。单outstanding本地资格仍不是provider严格因果，多个ASR/第二round未支持；无模型、provider、Native播放、physical或human新增证据。

## 最终取消修复复审：P2 SOURCE/OFFLINE关闭，仍为隔离原型

再次冻结对象：

- patch SHA256 `ceb906653b2fdcd143c3467915d4cd98536512876f163272eab662460167474a`
- test SHA256 `23070f99c386e6f23bd34891f6dedaaaa7fda59f8cf2f9fdb88b464e6fbc32c4`

独立完整运行同一命令：**26 tests PASS，28.074s**。不是只运行两个新增方法；原24项同时通过。未运行宿主、服务、provider、浏览器或设备，没有改生产/manifest/账本。

新 `_wait_native_audio_started` 同时等待精确旧slot的 `interrupt_event`，唤醒后抛 start timeout，交回 `_process` 原 `_cancel_after_timeout` 的 cancel grace / escalation。`automatic_audio && interrupted` 分支在 adoptable-response 之前处理，因此不会为了结束等待采用后来新response，也不把局部cancel当合法终态或直接放开lane。

新增真实完整下一phrase负例不注入provider合法cancelterminal：旧slot仍被准确取消；原3秒grace后升级关闭，测试实际断言 `<4s`、旧slot escalated、原socket closed、写出的PCM仅旧整句、新input仍open且新delivery没有成功。这关闭了此前“旧pending等待30秒、下一整句先等满8秒才失败”的P2。其含义是**及时安全失败关闭**，不是不断连接续或新句已成功上传；无ID/无合法终态时不能声称正常恢复。

Main首次取消修复曾使旧取消grace后的escalation关闭replacement socket，原测试FAIL作为调查历史保留；最终修法在实际工具入口保存原owner的 connection-only callback（generation + provider ws/session），不使用会因正常新input变化的tool scope来决定旧连接cleanup。取消等待入口和 `_cancel_after_timeout` grace/escalation前各核一次该原connection。独立26套件中同时覆盖：output等待期间换ws不写/不关新socket，以及cancel grace期间换ws后旧ticket失败、old.escalated=False、新socket无write且未close。未放宽旧scope、driver、Core authority或结果写回guard。

两个30秒时钟仍是不同起点；此修复通过interrupt提前唤醒取消路径，**不宣称已合并正常慢工具的两个deadline**。普通长等待达到边界时仍可能由producer先失败关闭，未作实时服务或设备测量。8秒output写预算、完整batch验证、原wire-ID资格与unknown normalizer拒绝均未被放松。

最终窄结论：本审发现的两个P2均已按上述冻结bytes SOURCE/OFFLINE关闭，当前增量未发现新的具体P1/P2。仍不预批生产/在线：原型未接生产链，单outstanding本地归属不是provider严格因果；多ASR/第二round/无合法cancelterminal后的用户恢复均保留明确范围，原49/50结论与physical/human待验不变。后续如Main完成其余回归或部署，须由其另记实际层级，不能把本报告26项当模型或播放验收。
