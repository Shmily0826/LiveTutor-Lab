# 阶段42：Native 工具结果同槽续接的只读设计审查

日期：2026-10-15。状态：SOURCE / DESIGN；不是实现批准、部署或模型验收。

已接续 contract / plan / status / blockers 当前记录。阶段40实际工具路径互等仍是未解决的 P2；隔离草稿的40项离线通过不覆盖它。本轮只读实际源与隔离草稿，不改实现、manifest、账本或共享记录，不启动服务、API、Native、浏览器或音频设备，也未新增测试运行。原49/50的 PARTIAL 不变。

## 结论

可以复用现有工具 owner、batch/entry 与 arbiter 单 lane，设计一个**在工具事件入口捕获资格、在原 Native slot 内写回结果**的窄接口；不能在结果完成时重新读取“当前 slot/current seq”来补归属。现有源还没有该接口或不可变 origin 字段。仅沿用 `source="tool_result"` enqueue 会保留阶段40死锁；只提高5秒超时也不解决。

即使完成该接口，能证明的首先是本地唯一输入槽与受保护工具任务之间的归属。当前 LANLAN profile 不保证 function-call ID 与 terminal ID 相同，也没有证明一个 sealed 输入只产生一次 ASR/response。不能把本地 qualification 写成 provider 严格因果 ACK。资格有多个候选或不完整时应拒绝 join，不能回退到任意当前槽。

## 已核实际调用点

实际文件目录均为 `benchmarks/raw/neko-product-host/main_logic/omni_realtime_client/`。

| 位置 | 已确认事实 / 对接要求 |
|---|---|
| `_tools.py:37–47` `_ToolTaskOwner` | frozen，仅 connection generation、scope、捕获的 host/provider turn pair、provider session 与 turn-pair fence；没有 sealed seq、driver/delivery 或 Native slot。 |
| `_tools.py:126–179` capture/current | capture 同步保存身份；current 核 connection/scope/provider session。`turn_pair_fence_applies=False` 只停用不可验证的旧 turn-pair 比较，绝不是新增 Native 归属授权。 |
| `_transport.py:3891–3905` | 原 provider function-call 事件走既有消息保护后，同步 capture owner，再启动工具任务。这是新增 qualification 的候选入口，必须在首个 await 之前捕获。 |
| `_tools.py:730–935` raw admission | 可能等待 speech/ASR gate，记录原 owner；仅既有 `released` 证据允许精确 scope +1 后 capture。新的 origin 必须随这条记录保留，不能在 gate 之后改抓别的 slot。 |
| `_tools.py:956–964` | unannounced response 会重新构造 owner 并设 fence=False。若新增字段只给默认值，这个重建会悄悄丢 origin，必须显式保留。 |
| `_tools.py:51–59, 300, 694–728, 980–986` | entry 保存 owner/task/abandoned，已有 task→entry 映射；batch 按真实 response ID 分组，同一 call_id 不足以唯一标识 entry。无 response ID 不猜兄弟调用。可透传 origin，无需另建 task registry。 |
| `_tools.py:579–673` collector | 等并行兄弟，按 entry 位置收集，排除 abandoned/canceled，结束前有0.5秒 settle grace；注释明确不设总工具预算。不能为 join 让快兄弟提前单独续答。 |
| `_tools.py:1275–1357` | 真实 function_call_output 携原 call_id，经 `tool_result` enqueue 等第二个 ticket；这正是原 Native slot 占 lane 时的互等点。 |
| `_response_arbiter.py:693, 1592–1656, 2824+` | 默认 announcement 等待5秒；item-driven content admission 仍需真实 ID-bearing content 与原 current owner/guard。不能用 function-call event 伪装 audio/text start。 |

另一个写回接口细节：`_tools.py:1326–1335` 的 `_send_owned_event` 目前 await `send_event`，但不返回其 True/False。新 join 不能凭它返回 None / 未抛异常宣布本地成功写入。新专用 sender 必须明确返回底层真实写成功结果，并继续使用原 owner 每次 await 前后的校验；这不要求扩改普通 enqueue 路径。

## 最小新增接口建议（尚不存在）

建议先做资格函数和只读 fixture，再决定是否实现 arbiter 写回。以下是接口契约示意，不声称已有对应 getter。

1. 在已通过原 guard 的 provider tool-event ingress，尝试同步捕获 `NativeToolOrigin | None`。origin 持有**实际 slot/ticket 对象引用**、driver 对象与 epoch、原 sealed delivery 对象与原 input sequence、原 Core authority/owner 快照、provider ws 对象与 generation，以及 capture 时的 tool scope。必须是唯一、未退休、已完整写入的本地 Native 输入；部分写、失败、local fail-open、旧连接或新 PCM 已替换时无资格。若工具事件能在 flush 最后一次 await 返回前到达，先拒绝或实现明确的同一 writer 完成证明，不能只看 live frame count 当写全。
2. owner 的 gate-record、明确的一次 +1 admission、unannounced 重建、entry 和 batch 原样携带该对象。原 capture scope 与经既有规则许可的执行 scope分开保留。scope +1 不是重新捕获 origin 或允许第二次 promote 的理由。collector 必须确认全 batch 的 origin 相同且每 entry 仍可发送；混 origin 不 join。
3. 拟新增 `submit_native_tool_batch(origin, batch, events, sender)` 之类 API：只准精确原 current slot、原 Native 模式/route、同一已提交完整输入，以及 batch 一次性发送。它不 enqueue 第二个响应、不创建第二个 owner，也不额外发送 LANLAN 不需要的 `response.create`。普通工具/SDK/UI/proactive、owner=None、未知 origin 保持原行为；不能借此自动获得 Native join 资格。
4. 该 API 必须与原 slot 的 writer/cancel 共用串行化边界。每个实际 socket await 前后核 slot/driver/epoch/authority/ws/gen/tool owner current；仅底层明确成功的完整结果批次可进入“等待真实内容”状态。中途失败保留诚实 partial/failure，不能重发已写 outputs，也不能释放 lane 后假称没发送。
5. function_call 的 issuing response terminal 只可协助封闭原工具 batch，**不标 Native success、不清 phrase waiting、不把它的 ID 当后续 audio/text ID**。写回后仍由既有严格 content admission 接纳真实 audio/text start，再等其合法 terminal。原 function_call `call_id` 原样用于 output；绝不与 response terminal ID 等同或改写。

第三点只是解决 deadlock 的方向。是否允许无 response ID 的独立单工具 batch join、如何证明旧延迟调用不是前一输入、是否存在同一 slot 的第二轮工具调用，都必须先以实际 event/owner 路径取得资格证据。仅“同一连接且时间很近”不够；资格无法无歧义给出时继续隔离草稿。

## 等待、终态和输入变更

5秒 announcement 是等待实际响应开始，不是所有工具总运行期限。当前 collector 故意允许慢工具；新 origin 不能把真实图理解/并行工具一律变成5秒失败，也不能每个新工具刷新无限期限。

需要显式区分原 slot 的 `awaiting_tools` 与 `awaiting_content`：只有受保护、确属原 slot 的实际工具批次可暂停/替换短 announcement 等待；完整 outputs 真写完才启动下一段真实 content-start 等待。同时保留一个**调用方明确设置的绝对总期限**，与 producer 当前约30秒 provider-boundary watch 的策略一致协调，否则 arbiter 虽等工具，producer 仍会先失败。不能仅静默延长或关闭 producer watch。超限应取消原 ticket/工具资格并报告失败，不借 fail-open 清成功边界。总期限具体数值和超慢工具体验尚未决定，本轮不预批。

新 PCM、输入 scope 变更、连接替换、Core authority 变化、取消或 driver retire，都必须使 origin 失效。不能 shield 整个 join 免于 owner 退休。已写 output 后发生新输入，仍要取消精确旧 slot，禁止清新 owner；等待锁时变更也要在获得锁后重核。原普通 onset/handoff、工具 abandonment、旧 connection cancel guard 保留。

Provider 对同一 sealed 输入可能产生多个 ASR/response。原 slot 首次成功 response 完成后，不允许迟到的第二个工具事件借其旧 origin 复活 slot；它应缺资格并按明确失败/未支持记录。这是当前设计范围限制，不能把一次终态推广为整段输入的全部 provider 事务已结束。

## 下一步最小离线资格场景

- actual `_tools` 的真实 function-call→task→collector→sender；原 Native slot 未内容开始，工具运行超过5秒但在明确总期限内。证明 outputs 真写在原 slot 内、未产生第二 ticket，随后只由真实 audio/text ID 开始。
- 并行快慢工具、迟到兄弟、duplicate/missing call_id、abandoned 与取消：等完整合法 batch，只发一次，不把无资格错误输出作为成功工具继续。
- ingress 到 gate 等待之间的 scope +1、unannounced owner 重建：origin 原对象不丢、不重采；新 PCM/第二 ASR/外部 scope advance 反例都拒。
- socket-write await 内替换 ws/gen/authority、写到一半失败、新输入等待 writer 锁、busy unrelated owner：不续接、不重放、不取消新 owner。
- 旧 parent terminal、idless/unknown/失败 terminal、旧 response ID、terminal 先于完整写回：不能清 phrase waiting；真实新 content 与 terminal 必须满足原 capability。
- 原 slot 已完成后迟到 toolcall、第二工具 round、两个候选 origin：不能用后来 current seq 补认。未知协议归属明确拒绝，默认 OFF/普通 lane 保持原身份与行为。

这些 fixture 可证明本地实现安全性，不能单独证明 LANLAN provider 对 audio/function-call 的严格因果。实际协议仍缺 input-to-tool 的不可歧义标识；若 profile 无此保证，产品报告应明确“单一本地 outstanding input 下的受限 continuation”，而非 strict protocol ownership。

## 审查对象指纹与冻结

| 文件 | SHA256 |
|---|---|
| actual `_tools.py` | `41c50034fbba268f58214df34e5f167fb2f45b906d8d8bd4d854ec4922cc05cc` |
| `scripts/neko_native_audio_dispatch_patch.py`（未接线草稿 patcher） | `c2aaef9d9abde2f7b7620566b08ccb0bc914d62d99a16788919cfb293bf96dd2` |
| `scripts/drafts/neko_phrase_input_transport_phase40.py` | `d247be713381aae91a71608441f9a06d3be0b5ccb868a8b667c9d70f44ce548b` |

本报告冻结为只读设计意见。没有新增运行时、模型、设备或 human 通过结论；阶段40互等仍需实现与独立证据关闭，不能据此直接部署。
