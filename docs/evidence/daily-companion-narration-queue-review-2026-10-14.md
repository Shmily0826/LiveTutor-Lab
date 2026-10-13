# Phase 6：叙述事件队列与材料来源只读审查

日期：2026-10-14。范围：已部署 base communication/event bus、插件 push bridge、宿主 callback 准入/释放/入模路径。先承接本 Goal contract、plan、status、blockers；仅新增此报告。没有修改生产或测试，没有运行宿主、API、在线模型、音频、账本或浏览器，也没有新增子 Agent。

本报告为 **源码审查**。Phase 6 主线正在进行的 SDK 本地桩验证不属于本报告独立执行的证据；真实模型、设备播放和真人体验均未在本报告验证。communication 默认 OFF 继续保留。

## 确认的断点

### P2：summary emitter 丢弃入口快照，重新混入 live seed

`benchmarks/raw/neko-app/resources/bin/plugins/study_companion/entry_communication_tutor_events.py:164–204` 的 `_emit_session_summarized_event` 在 `await self._lock` 后读取 `self._state.session_summary_seed`，没有使用 Phase 6 summary entry 已传入的 `_material_context` 和 `_session_summary_seed`。生成的 answer count、correct rate、topics 来自这个 live seed；key insight 则来自原 summary payload。换课发生在 helper 等待锁期间，仍可能得到旧总结与新课程统计的组合。入口完成前后校验不能撤回 helper 已经 schedule 的事件。

该 helper 也没有传 `target_lanlan`。不能把“来源是 Study”当作“已绑定当前角色”；没有明确目标的旧事件不得在 drain 时用新默认角色补齐并播放。

最小修法：helper 对带私有 provenance 的 summary 在同一插件锁内核对 captured course/session，仅从 `_session_summary_seed` 深拷贝得到统计，构造固定事件 payload；不读取新 live enrichment。校验失败不 schedule、不修改原 history。summary 语义是 immutable session history，context 只含 course/session；单纯换图不使总结失效。旧调用兼容分支若仍要保留，应明确无材料保护，不能静默声称其具有相同保证。

### P2：插件 queue 到 host 时来源完全丢失

`.../study_companion/_event_bus.py:147–185` 的 `schedule_emit` 保存 `StudyEvent`；dataclass frozen 不会冻结其内部 payload dict。`212–243` 的 worker 在 queue/semaphore 等待后才 emit。`302–345` 的 `_emit_open` 构造 push_message 时只有 visibility/behavior/priority/text/source/target/coalesce，没有传材料 context。首次 entry 校验无法覆盖这些等待窗口。

最小修法：沿用现有队列，在 schedule 时深拷贝必要 payload，给 event bus 注入一个可选的插件材料 validator；构造带保护事件时要求 validator 成立。在 worker 获得槽位后、最终 push 前再次验证。validator 若需要 await，必须在该 await 后重新于插件锁内核对快照再构造固定消息；不能把异步校验结果无限期缓存。stale 是正常 drop，不进入失败重试/worker backoff；已经 reserve 的 throttle/respond bookkeeping 需要走现有 release 路径，不能提交成功计数。queue-full、关闭、取消和旧事件计数保留原语义。

`_FORMATTERS` 的 session formatter `666–676` 仅渲染 duration/questions/rate/insight；私有来源应留在 metadata，不加入 text/parts/key insight。不要新增一个落入 `_format:542–550` 的未知 event 名后依赖 `str(event.payload)`，否则来源字段可能进入模型文本。

### P2：host 的现有过期/领取保护没有材料判据

宿主已有完整 queue；不需要新建队列：

| 现有位置 | 可复用能力与必要补点 |
| --- | --- |
| `main_logic/core/proactive.py:657–718` `filter_deliverable_callbacks` | 当前只识别 TTL/retracted；复用配对 callback/mirror 撤回与 ack=False，加入受信 Study narration 的 stale/unknown 来源判据。 |
| `proactive.py:2138–2205` `submit_proactive_callback` | takeover/hold sink 在 manager.submit 前消费 callback；需要在交给 sink 前校验，或暂不支持此 route。仅 manager release 过滤不能保护它。 |
| `proactive.py:2261+` `_deliver_proactive_batch` | 已调用统一过滤器；继承新增材料过滤，随后 enqueue/trigger 仍保留已有节奏规则。 |
| `proactive.py:3538+` claim、`3637–3754` drain | claim 会过滤，但显式传入的 claimed snapshot 在 drain 不重做过滤，可能跨媒体 staging 的 await；在最终 render 前按当前来源过滤。claim 不能使过期材料合法。 |
| `proactive.py:1064/1133/1309/1733/1773` | 多处 voice/text 最终边界已调用过滤器，可复用，保留原活动/普通打断保护。媒体已落入 Native 而文本被拒时沿用现有 unsafe-session retirement；不能仅丢文字留下孤立图片。 |
| `main_logic/core/lifecycle.py:3304–3450`、`3485–3513` | hot-swap extras 在 3304 过滤后仍可能 await passive media staging，然后 prime 已拼好的字符串。最终 prime 前需要按原 callback 集重新校验并重建文本；不可只过滤队列而继续使用 stale `final_prime_text`。 |

`filter_deliverable_callbacks` 对 claimed/voice-committed 配对项有刻意保留规则。材料失效时必须将当前 snapshot 本体和同 delivery id 的 mirror 一致标记；不能因 claim flag 把旧叙述当“仍 current”，也不能通过宽泛清空抹掉新 owner 的 callback。实际已送入 provider 的内容属于另一层，见下方边界。

## 私有来源可以走现有传输

`plugin/server/messaging/proactive_bridge.py:352–357` 深度之外的 metadata dict 复制和 `497–529` 的 proactive event 都保留 metadata；plugin/channel/source 是 bridge 派生。`app/main_server/character_runtime.py:1492–1599` 将 event metadata 保留为 callback metadata，分别交 passive enqueue 或 proactive submit。无需额外端口、数据库或模型请求。

建议仅为受保护叙述增加一个 bounded 字段，例如：

```json
{"study_narration_origin":{"v":1,"event":"session_summarized","boot_id":"<32 lowercase hex>","change_seq":0,"context":{"course_id":"...","session_id":"..."}}}
```

复用已有材料 binding record 的 v/boot/change_seq/context 校验口径；summary/明确源码文字使用 course/session subset，真正依赖当前图片的解释才携带 material_identity。不要把 summary seed、history、图像内容或系统路径放进 origin。target_lanlan 走现有独立路由字段，必须是生产者已知并注册的明确角色；默认角色或广播不具备安全绑定。

host intake 应仅接受 `source_kind=plugin`、`source_name=study_companion`、`channel=plugin:study_companion` 的一致组合，并校验 marker event/version/field types/长度/目标归属，深拷贝到 host-only callback provenance。别的插件或模型文字不能提交一个 metadata dict 就被认为可信。缺失、畸形、未确认 current 的受保护 Study narration 不进入 LLM/语音队列；其他插件原有 callback 行为保持原契约。

`core/callback_render.py:99–134` 只把 summary/detail 放入文本，`135–270` 按宿主 origin/source 模板渲染，没有把 callback.metadata 全量序列化。保持这个白名单行为，别将私有 marker 添加到 callback detail；内部 origin 仍由宿主派生，不能由 plugin 的新字段替换。

## current 判定不能只靠“没有收到更新”

已部署材料控制准入 `character_runtime.py:903–916` 只接收受信 Study、blind、无 visibility、有具体 lanlan 的控制。Core 现有 `_study_material_controls` 按 producer boot 缓存最多四个 change record；`scripts/neko_material_audio_patch.py:107–138` 的规则可复用：同 boot 且更新 seq 高于 origin、after 在 origin 的相关字段不同，则失效；晚到低 seq 控制不能覆盖新结果。summary subset 与 photo-only 更新兼容。

但该缓存是 **已到达控制的记录**，不是权威当前 snapshot。没有记录、旧 boot 被淘汰、插件重启、目标尚未注册或控制丢失，不能得出 current=True；缓存已有某 boot 也不能证明它仍是当前 producer。仅做这项比较会留下系统性遗漏。

最小适配有两层：插件排队时验证并将明确 target 注册到已有材料通知通道；host 为该角色维持受信的当前 producer boot/context 状态，来自明确的当前状态确认及后续同通道控制。无法确认时 fail closed，不发声；如采用 SDK 当前状态读取，必须无 LLM、有限时间、在等待后重新检查原 callback 和目标所有权，不能自动重放旧叙述。当前控制 payload 若没有重启/最新 boot 确认，则先保留 OFF，源码不能宣称已经解决通知丢失或跨 boot 的权威判定。

## 支持范围及不能顺手扩大之处

建议第一版只支持显式 target 的 session summary 文本、course/session 来源验证以及未注入 provider 的 queue 撤回。general explanation/solution 可以复用同一路径，但其 entry 没有被本次审查赋予材料快照保证；只有实际传入对应 context 后才能纳入。timer/habit/review 等非此类叙述也不能随意继承 summary context。

已有材料音频取消是 **实际工具 batch owner → Native physical connection/token/socket/activation** 的绑定。queued proactive 事件没有该工具 owner，不能直接调用 `_capture_study_material_tool_owner` 或凭最后一次 `_study_material_output_owner` 取消；否则可能取消正在讲的新 owner。若允许 narration 已触发模型后遇到换课，必须在实际 callback 注入/生成处建立自己的准确 output ownership，再复用精确取消；在该分支具备证据前，本报告只提出 queue admission/最终入模保护，不声称已经停止生成中或设备已排音频。prime await 中控制变化也是不可逆窗口，既有 coalescing 注释接受的 residual window 不等于材料安全验收。

TTL、coalesce key、SDK submitted、queue ack 和 prompt rendered 都不等于设备已停声；来源校验不能削弱已通过的普通 onset/barge-in、不能 replay PCM 或重新发旧材料。

## 主线下一步最小离线验收

用真实 helper/event bus/Core 方法及受控 await，分别覆盖：summary 等锁时换课而无事件；原 seed 在 entry commit 后被新课改变仍只用捕获统计；bus 等 semaphore 时换课不 push 且释放 reserve；metadata 原字段经 SDK→bridge→host 完整保留且不出现在 prompt；wrong source/target/boot/unknown current 拒绝；control 比 queue 先到、晚到旧 seq、同课 photo-only subset、目标变更；claimed drain 和 hot-swap media staging await 后旧 callback/mirror/ack 一致撤回；takeover sink 不收到受保护 stale cue；新 owner 的 event 不被旧控制撤回。无需为本轮审查跑在线模型或设备。

文件范围：若主线实现，应在 canonical product 中覆盖 `entry_communication_tutor_events.py`、`_event_bus.py` 及 construction 注入；host 使用现有 patch/部署流程适配 character_runtime、Core proactive 与 lifecycle 最终边界。bridge 与 renderer 已有 metadata/白名单行为，原则上不需改；若 SDK 丢私有 metadata 的实测出现，再改精确序列化边界。不能直接修改 base runtime 当作可复现产品交付。

报告冻结：仅源码审查与适配建议，无本轮运行证据，无部署/发布，无额度或进程操作。communication 默认 OFF；完整受保护 narration 仍待实现与分层验收。
