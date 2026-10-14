# 独立 narration 宿主接入计划：权威状态与最终准入

日期：2026-10-14。只读审查，唯一写入为本报告。读取 contract 原文及 plan/status/blockers 最新阶段九接续段；最新记录为功能分支 `4f42efc0f41474cf3c6c9afa1a795025468a4c92`、Goal active、严格静音、communication 默认 OFF。额度与进程情况仅承接 Main 记录，本轮未查询或调整账本。没有启动服务、浏览器、API、模型、Native、音频设备或回环，没有执行测试或派新 Agent。

源码范围仅 `benchmarks/raw/neko-product-host/` 下的 `main_logic/core/proactive.py`、`main_logic/core/lifecycle.py`、`plugin/server/messaging/proactive_bridge.py`、`app/main_server/character_runtime.py`，及已冻结 narration queue-review/material 两份报告。根目录没有 `.codegraph`，直接定向读取上述文件。下文行号对应此次读取的部署源码；不是修改、部署或运行通过证据。

## 当前结论

现有 callback 队列、delivery id、metadata、claim、ack 和释放路径均可复用，不需要新队列或数据库。**当前限定宿主源码没有一个可直接调用的权威 Study 当前 boot/course/session 获取接口。** 可以先实现默认 OFF 的来源校验与拒绝路径，但不能凭本次计划启用 narration。

首版建议只允许显式 target 的 `session_summarized` 纯文本，来源 context 严格为 course/session subset。单纯换图不使历史总结失效。图片 narration、takeover/hold sink、Native 已生成叙述和 pending-session prime 暂不宣称支持；这些路径须完成各自精确最终准入及输出所有权后再开放。当前严格静音任务只可准备/离线验证文本接法。

## 已确认的来源和路由接点

| 接点 | 当前源码事实 | 最小接法 |
| --- | --- | --- |
| `proactive_bridge.py:356–359,393,496–520` | metadata 浅复制；target 来自独立字段或 metadata；plugin/channel/source 由 bridge 构造并进入 event。没有材料 current 判据。 | 沿用原通道，不将 origin 加入 text/parts。host 接收时深拷贝并限定 marker 类型/长度；不要把 bridge 的浅复制当 immutable provenance。 |
| `character_runtime.py:903–913` | 受信 Study blind/空 visibility/明确角色的 `study_material_control` 被转交该角色 manager；该分支没有建立当前 producer boot 身份。 | 复用明确角色查找和受信控制专用分支，但普通 material change 不能被自动升级为 producer-current 握手。新权威控制要有独立严格契约。 |
| `character_runtime.py:794–799` | `_get_session_manager(name)` 只能确认当前 role 对应的 manager。 | intake 捕获 manager 对象和明确 target，后续所有 await 返回再检查仍为同一 manager。它证明角色归属，不能证明 Study 学习 session。 |
| `character_runtime.py:1146–1155` | 未解析的 proactive target 会在仅一个连接角色时 fallback。 | 受保护 Study narration 必须在此分支之前拒绝 missing/unknown target；不走 fallback，也不补默认角色。 |
| `character_runtime.py:1219–1387,1418+,1546–1595` | 媒体处理/可见渲染在 callback enqueue 之前；最终 callback 保留 event metadata，分别走 passive enqueue/proactive submit。 | 受保护 marker 的 intake 应在 fallback 和所有媒体/可见输出之前；首版拒绝其图片/audio/video/UI action。仅在来源和权威状态确认后创建 host-only provenance 并入现有队列。 |
| `character_runtime.py:560–583` | `_resolve_event_source` 对缺失 source 可按 channel 推断 plugin。 | narration 受信检查使用原 event 明确的 `source_kind=plugin/source_name=study_companion/channel=plugin:study_companion` 三项组合，不依赖推断补齐。此组合是现有 IPC 信任边界，并非本轮证明过的独立签名机制。 |

目标 manager 重建点可见 `character_runtime.py:1914–1942`：新建 Core manager、恢复 websocket、替换 role_state。适合安装新的 app-owned validator 并清空旧权威确认；旧 manager 的缓存不能直接迁移成新 manager 的授权。其他初始构造点未在本次范围核查，Main 实现时须把同一注入接到所有实际构造点，缺注入默认拒绝。

## 权威 current 的必要补点

原 producer/queue 报告已证明插件锁内的实际学习状态能校验 origin；它是材料权威来源。宿主 `self.session`、`pending_session`、`input_mode`、websocket、speech id 是宿主对话/连接身份，不能替代插件的 `context.session_id`。queue metadata 的 boot 是消息自述，不能用首次收到的 narration origin 建立“当前 boot”。旧控制 record 证明已收到的变化，不能证明插件没有重启、控制没有丢失或该 boot 仍在运行。

最小新接口应是 **Main 待实现的独立权威 adapter**，不是假设已有 getter：

1. 由 app 层通过已有受信插件运行时通道，确认 Study producer 的实际运行实例及当前 boot/seq/course/session；不得从模型文本、旧工具 reply 或最后一次 tool owner 获取。若使用 SDK 状态读取，Main 需先核实际只读入口是否返回这些字段，本轮没有读该入口，不虚构它的名称/返回结构。
2. 为明确角色建立有限、host-only 当前确认，至少记录 producer 实例、boot、seq、course/session、target 与 manager 对象。不存在、畸形、断联、超时、重启未重新确认或确认被淘汰时结果为 unknown；unknown 与 stale 均拒绝。该结构是授权状态，不是第二学习记忆/队列/DB。
3. 在现有受信控制通道承接同 producer 更新，低 seq 不覆盖高 seq；新 boot 只经新运行实例确认接管，不接受任意晚到控制自称的新 boot。对于 summary，当前 seq 不得小于 origin seq，相关 course/session 必须相同；photo-only seq 增长允许，不要求 seq 全等。
4. Core 注入同步三态 checker（例如 proposed `study_narration_is_current(origin, target)`，目前源码不存在）。checker 只能使用上述已确认的当前状态；异步 checker 不可直接放进同步 `filter_deliverable_callbacks`。所需异步刷新必须在明确上层边界有界完成，再重新检查原 manager/target/callback，不能把等待前的 True 缓存为永久授权。

**仍缺的重要协议边界：** 一次状态 RPC 的成功回复只证明读取时刻的状态，不能证明回复之后到 provider 真正接收之前插件没有换课；单向异步控制也可能尚在途。启用前 Main 要明确状态变更/控制的顺序与最终发送线性化点，或提供可撤销的材料 lease/受控提交协议，并以实际 await 负例钉住。仅靠“宿主还没有收到新控制”不能声称全过程 current。不可通过拿插件锁跨未知网络等待掩盖问题。本报告不宣称已完成该协议。

## 现有队列的最小保护

| 阶段 | 准确位置与当前行为 | 需要的保护 |
| --- | --- | --- |
| intake/直接 sink | `proactive.py:2138–2205` 在 manager.submit 前可能交 takeover/hold sink；passive 在 `character_runtime.py:1576` 直接 enqueue。 | 两路均先校验 host-only provenance/current。首版受保护 narration 不交未经 guard 的 sink；不能只在 delivery-manager release 做检查。 |
| manager release | `proactive.py:2268` 已调用 filter；`2290–2296` 全部被丢时释放 inflight。 | 复用该空批释放，不为 stale 重试/触发；后续正确事件仍可入队。 |
|统一 filter | `proactive.py:657–715` 只认 TTL/retracted，按 delivery id 清 callback/mirror 并 ack=False。 | 加受保护 narration 的 stale/unknown 判据。其他插件行为保持；不清全队列、不碰不相关新 owner。 |
| claim | `proactive.py:3541–3574` 先 filter 后按预算 claim。 | 复用 checker；claim 只是队列围栏，不是材料授权，后续仍需检查。 |
| claimed drain | `proactive.py:3660–3663` 显式 snapshot 不再 filter；`3676–3681` 仅检查仍在队列/撤回。 | 无论 snapshot 是否显式，都在媒体 await 后/render 前重做材料过滤；失效释放原 claim、ack=False、移除对应 mirror。 |
| text 最终 render | `proactive.py:1773` 最后一次 filter，`1783` 之后仍 await Core lock，`1808` render，`1851` 调 prompt。 | 在最后一次 await 之后、渲染/调用之前再次核本批 current；重建 instruction，不沿用旧字符串。provider 内部真正写前仍需要上述提交契约，外层检查不自动覆盖内部 await。 |

材料失效和一般 coalesce 不是同一件事。现有 filter 在 `686–687,702–703` 刻意保留 voice-committed 或 swap-claimed 配对项；新增材料撤回必须针对本次 origin、同 delivery id 的确切 callback/mirror 一致标记，不能让 claim 保护把旧材料“变回合法”。也不能无差别解除新用户回合/新 owner 的 claim。

## media-final 与 hot-swap 范围

`proactive.py:1064,1133,1309` 的现有过滤覆盖 voice 旋转/媒体等待前后，可复用 checker。真正的媒体发送在 `_stream_cb_media:2317+`，实际 `si` await 在 `2406/2421`；passive staging 的实际 await 在 `2816/2827`。若未来支持依赖图片的 narration，应在每个 callback/image 进入不可逆 provider 写之前及 await 之后核材料与准确 session，不能仅 batch 首次核一次。

已写入 Native 图片但文本被拒时，`proactive.py:1172–1190,1316+` 已有精确 captured `voice_sess` 的 unsafe retirement；应复用其闭包并维持新 session 不受旧 cancel 影响。材料 stale 要走 drop，不能顺着普通 media failure 的重试把旧材料回放。首版纯文本无需主动触碰此音频路径。

hot-swap 有两种冻结字符串，均不能靠清队列撤回：

- `lifecycle.py:3304` 过滤 extras 后，`3354–3359` 拼入 `final_prime_text`，`3371` 才 prime；材料失效要从原 callback snapshot 重新渲染 extras，不能继续送旧 final_prime_text。
- `_render_claimed_passive_callbacks_for_swap_prime:3004–3055` 目前只检查撤回/媒体就绪。在 `3422` 或 `3488` staging await 后重新做材料判据；`3439/3505` 的 unsafe-prefix helper 本身可能 await cleanup，`3448/3513` prime 前还须复核准确 pending session 和原材料，不能使用 await 前拼好的字符串。

claim 后 callback/media 可进入 provider 的窗口，必须拥有 narration 自己的准确 batch/connection/activation 输出绑定，才可对换课后的生成内容进行精确取消。当前 tool batch owner、上一次 `_study_material_output_owner`、观察序号都不能充当 narration owner。本次允许范围没有提供该 binding 的完整实现证据；首版应将未完成 guard 的 pending-prime/Native route fail closed，不能凭 queue admission 声称已停止已生成 PCM。

## Main 的最小下一实施与离线证据

先实现默认 OFF 的 host-only provenance parser、注入 checker 和拒绝路径，沿上述 intake/filter/claim/drain/release 复用队列。没有权威 adapter 时所有 protected summary 都被明确 drop；普通 callback 不受影响。再补真正 producer 实例确认/当前状态控制与失效协议，才允许隔离的纯文本 summary 正向路径。初始先不支持媒体、sink、Native/pending prime，可减少首次开放范围，但需明确记录 route refusal。

用实际部署方法及受控 await 的最小负例即可，不重复已通过的 producer14：未知 boot/来源/target 不 fallback；旧 boot 后到与低 seq 不覆盖；新 manager 不继承旧确认；同课 photo-only 可保留 summary；claim 后换课/drain 拒绝且 paired mirror/ack/claim 一致；全批 drop 释放 inflight且后续当前批正常；最后 lock 或 prime staging 等待期间换课不沿用旧 instruction；private metadata 不进入 text；未支持媒体/sink/Native route 拒绝；确切新 owner 不被旧控制取消。

本轮仅**SOURCE REVIEW / PLAN**。宿主接入实现、真实方法离线验证、SDK→host 当前状态协议、真实模型、Native/device 与真人均尚未由本报告验证。communication 默认 OFF，严格静音不变。报告冻结，除该文件外没有修改任何源码、测试、报告、manifest 或共享接续记录。
