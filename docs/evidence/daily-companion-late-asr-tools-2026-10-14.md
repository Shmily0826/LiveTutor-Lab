# Native free 迟到 ASR 与工具 scope：定向离线诊断

日期：2026-10-14。范围只读实际场景、日志和当前源码；新增独立离线复现脚本。本轮没有修改生产源码，没有启动宿主、音频或外部请求，也没有修改额度。这里的通过仅为源码/离线通过。

## 结论与真实事件

确认一个本地竞态：free proxy 没有先行 `speech_started`/输入 item 身份时，工具已经在当前 scope 执行，紧随其后的同一输入 ASR completed 被当作新 turn，取消该工具及 collector。不能通过取消新 turn 隔离来修复它，否则旧工具会泄漏到后续输入。

另一个观察是 function response ID 与 terminal ID 不同；它不能单独定为 batch 挂起缺陷。实际 collector 的 unannounced fallback 在工具完成后正常返回，无需匹配 terminal。没有支持以“仅有一个 batch”为理由关闭任意 response 的证据，不建议 alias。

证据：`benchmarks/raw/evidence/daily-companion-20261014-role-point-single.json`，`benchmarks/raw/neko-desktop-host.log:51101-51143`。时间采用原 wire trace 绝对 wall 秒：

| 事件 | 第一片 | 第二片 |
| --- | --- | --- |
| function arguments done / study_point | 1791900750.191 | 1791900759.180 |
| function response ID | resp_1791900735752 | resp_1791900750262 |
| response.done | 1791900750.244 | 1791900759.187 |
| terminal nested ID | resp_1791900750258 | resp_1791900759254 |
| ASR completed | 1791900750.246 / 27 chars | 1791900759.213 / 76 chars |
| scope retired | 1→2 / 2 tasks | 2→3 / 2 tasks |

第一片工具比 completed 早 55ms，第二片早 33ms。单句刺激实际 speech end 为 1791900757.801862，第一片 ASR 已在整句结束前出现，因此短暂调整派发顺序只修本地竞态，不能宣称修复上游句内分轮。第二片另有 `POST /api/guidance` 409（日志51142附近），不能把最终 0 pointer / 0 audio 的全部原因归于 scope。

## 真实方法复现

新增 `scripts/test_neko_late_asr_tools.py`。AST 加载实际 `_tools.py` 的类、常量和方法，避免初始化桌面组件；仅替换外部工具执行与结果发送。没有复制 ownership/batch 实现。

```powershell
& benchmarks/raw/neko-product-host/.venv/Scripts/python.exe -I -B scripts/test_neko_late_asr_tools.py
```

结果：4/4 通过，0.038秒（首次运行）。检查：

1. 真实 `_start_raw_tool_call` 建立工具与 collector 两个任务后，真实 `note_user_turn_started` 取消两者，没有输出。
2. 真实 `close_raw_tool_batch` 不接受不匹配 response ID，匹配 ID 正常关闭。
3. 当 `_current_response_id=None`，不匹配 terminal 不设置 closed，但真实 `_collect_tool_batch` 在工具完成后按 fallback 封口并正常返回；0.2秒界限内完成。
4. 同 scope 工具正常产生结果；连接 generation/ws 替换后，原 owner 无法重新变为有效。

相关源码：`candidates/N.E.K.O/main_logic/omni_realtime_client/_transport.py:3686` 即时捕获原消息连接 owner 并派发；`:3869-3888` completed 没有先行 scoped 身份时退休工具。`_tools.py:126-170` 保留连接、scope 和实际 provider session；`:414-449` 退休并取消；`:717-774` 派发原工具；`:354-391` 精确关闭与 unannounced 判定；`:576-665` collector 在没有 pending 且 response 不再 open 时可返回。

## 对最小待派发候选的边界审查

当前可支持的是局部、实验性的事件重排：只针对精确 `lanlan_app_gemini` + `_is_free_proxy` + 没有 server-VAD 边界事件，并且有近期本地 speech、当前输入尚未完成 ASR 的原 raw call，在不阻塞 receive 的短有界 pending 区间等待 completed 建立 scope。它不是独立语音架构，也不需要 MANUAL/新 provider。

需要同时满足以下边界，否则不安全：

- 保留 arrival 时的原消息 ws、connection generation、scope、call_id/response_id/arguments。派发时仍核对原 provider session；不能只在 timer 到期后 `_capture_tool_task_owner(self.ws)` 把旧 call 交给新连接。
- pending 区分“未执行的当前候选”和已经执行的旧任务。不能把等待任务直接登记进 `_tool_tasks` 后期待 completed 释放它；`_advance_tool_scope` 会照常取消全部这些任务。pending 必须有独立的有界生命周期、teardown/cancel，旧已执行任务仍正常退休。
- 只允许 expected completed 带来的恰好一次 scope advance；第二次 advance、真正的新 onset/原 native barge-in handoff、输入 owner 替换、新 ws/new connection 都应使候选无效。不能允许旧任务免除 scope fence，也不能复活 retired task。
- completed 先处理 scope retirement 和输入 transcript/host callback，再为仍满足原连接与输入证据的 pending call 生成新 owner，并调用原 `_start_raw_tool_call`。回调有 await，回调之后必须重新检查连接与候选；接收循环不能等待 timer 或外部工具执行。
- timeout 没有 expected ASR 时不能无条件转绑最新 scope。安全的保守处理是丢弃并留下原因；若选择按原 owner 继续，它仍必须经原 scope/connection/session fence，并承认晚 ASR 仍可能取消。设定 pending 数量与等待上限，拒绝无限排队/重连。
- local speech freshness 使用 `_last_local_loud_time` 的 capture wall 时基，与 wall 比较。不要与 monotonic 相减。
- `_voice_handoff_input_sequence` (`_transport.py:159-166`，`:1580`) 每个 speaking PCM frame 都递增，不是稳定 utterance ID。连续后续帧不等于新 onset；反过来也不能靠这一序号把 ASR 和工具认证为同一输入。应复用真正 native handoff/connection ownership 作为硬隔离，frame sequence 至多作为输入活动证据。
- `response.done` 可能在 pending 尚未派发时经过。保留精确 response ID 的原行为即可；当前 unannounced fallback 能完成。没有必要引入 singleton alias 或扩大 terminal 匹配范围。

provider completed 在本场没有 item_id，function 的 item_id 是输出 `fc_*`，不能充当输入 identity；response ID 又不与 terminal 一致。因而仅用时间邻接把下一条 ASR 与 pending call 关联始终是兼容性启发式，不能证明任意迟到 call 属于下一输入。特别是旧响应迟到 + 新语音刚开始场景，近期speech本身不够。主线若无法可靠识别输入替换，应保持保守丢弃并将该边界列为待验证，不放松旧 turn/连接隔离。

## 主线后续验证与状态

最小生产修复由主 Agent 实施；本审查不修改原派发方法。需要定向真实方法离线检查 pending→expected ASR→一次派发、ASR多次/timeout/新onset/handoff/ws替换→不派发、旧已执行工具仍取消，以及同 response sibling 不重复 continuation。再由主 Agent 安排一个受控固定刺激验证工具成功、409原因、完整输入约束和首播放；不要重复 MANUAL 支持 scene。

保留普通真人 barge-in 历史验收，相关代码改变后的最小回归由主线统一安排；本轮不能宣称真人体验或实际播放通过。剩余上游单句分轮、缺输入标识、图片指示409属于不同待解决项目，长期 Goal 继续。

## 主线 ordering-v1 候选定向只读审查

审查对象：`scripts/neko_late_asr_tool_patch.py`、对应 `scripts/test_neko_late_asr_tool_patch.py`、实际应用的 `_tools.py` 和 `_transport.py`。主线报告已有5个候选测试及旧工具/打断回归通过；本审查没有重复运行这些旧批次，没有上线。额外运行的是两个不写文件的定向离线探针。

**确认保留的硬边界**：候选只在精确free app/no server-VAD事件/近期未转录speech路径排队；pending独立于普通 `_tool_tasks`；连接generation和实际provider ws/session固定；foreign scope单独计数；release只接受arrival scope+1；timeout继续原owner，不转绑新scope。native handoff pending或连接替换阻止派发。abandoned使用原 `_close_unanswered_tool_calls`，其connection/session/send_guard保留且不发response.create。capture owner到调用原派发之间没有await，未发现该段存在异步换连接空隙。仍保留上一节列出的缺input item identity启发式限制。

### [P2] ASR已观察、callback未完成时可能丢掉当前工具

来源：`scripts/neko_late_asr_tool_patch.py:48-72` 的timer/released分支和`:94-103` 的finish；transport insertion在 `_deliver_input_transcript` await完成后才调用finish。

实际顺序可以是：当前call入pending→completed推进scope+1→await用户transcript callback→timer先到→record.released仍False而scope已改变→按abandoned关闭call→callback完成时pending已删除。这样旧隔离安全，但这次刚修复的当前工具仍未执行。

定向探针直接加载实际candidate Harness，离线将等待上限缩为.04s，expected scope advance后模拟callback等待.08s，再调用finish：`scope=2, tool_started=False, abandoned=['callback-slow'], pending=0`。这不证明真实callback已经超过.4s；它证明存在与当前helper一致的漏执行条件，而现有成功测试调用completed时没有callback await，没覆盖它。

建议区分“expected ASR已经观察且建立scope”与“host callback已ready”：completed同步阶段标记对应pending的expected transition，callback后标记ready并释放；timer不能把已经观测的expected transition当foreign。若为了有界性仍选择丢弃callback超时call，应明确记录 `transcript_callback_not_ready`，让UI/日志解释本轮失败，并补该定向回归。不要提前在callback未ready时执行，也不要因此移除scope fence或无界延长等待。

### 补丁幂等测试的证明范围

`scripts/test_neko_late_asr_tool_patch.py` 的replay测试再次 `upgrade_targets(voice.TARGETS)`；但 `scripts/neko_voice_host_patch.py:750-751` 已把late-ASR升级纳入TARGETS。builder `_upgrade_targets` 会把包含原scope assignment的已升级hunk再升级。只读探针统计目标替换文本中的 `self._late_raw_foreign_scope =`：现集成TARGETS为1，再次upgrade后为2。

这不是“当前运行源码已经重复升级”的证据：正常单次构建后，应用器先识别完整after并跳过，可保持生产重放幂等。它说明当前候选测试是在二次升级目标上测试parse/after存在，未真正证明二次apply相同字节不变。建议测试直接对最终集成TARGETS做第一/第二次apply，断言源码字节完全相同和唯一marker/foreign计数赋值；若builder也要支持已升级输入，则先识别after避免嵌套相同upgrade。无需为了此测试改运行时ownership。

主线修复与是否上线仍由主Agent决定。本次新增外部请求0、生产源码修改0、新进程0。

## ordering-v1 增量修复核对：前述两点已解决

后续主线新增 `_begin_raw_input_transcript`：scope建立后、await transcript callback之前同步标记 `asr_observed`；callback完成才调用finish设置released/event。原.4秒窗口到期时，如果expected ASR已观察且原连接仍有效，另给有界2秒ready等待。未ready仍有明确timeout日志，随后原scope比较拒绝，不提前执行，也不转绑陌生scope。源码核对确认前述“callback稍长于.4秒即把已观察ASR当成未知scope”条件已修复。超过总有界期限仍可保守丢弃，属于明确timeout范围，不是无界等待。

builder现在发现已集成late-ASR marker直接返回相同TARGETS和空追加replay。新测试使用最终 `voice.TARGETS`，断言重复builder不变、二次apply后的源码字节完全相同；并新增slow-callback readiness场景。主线报告6项候选/工具5/打断19通过；本只读审查读取该增量，不重复跑旧批次。这两项前述审查发现现在标为**源码/离线已解决**，不继续当作上线阻塞。

没有改helper或生产文件，没有外部调用。缺input item身份/时间邻接启发式、上游单句分片、指示409与实际角色播放仍需要各自证据，不能由这一增量修复自动冒称通过。
