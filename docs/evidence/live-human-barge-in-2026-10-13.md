# 真人语音打断验收：FAIL（2026-10-13）

**后续结果：** 本文保留 16:24 场次的 FAIL。18:22–23 的修后真人场次已有实际 handoff/播放反馈及用户听感确认，普通插话与新回复恢复本场 PASS，见 [直接接管验收](native-barge-in-direct-takeover-2026-10-13.md)。不代表本文失败的全部根因均已回溯证明，也不代表跨结束边界或教学质量已通过真人验收。

本次只做一场真人测试，未修改源码、提交或推送；用户要求到此收尾。

## 条件与时间

- Windows 原生 N.E.K.O.，用户端手动启动并进行真实说话、听测。运行命令没有 fake-audio / fake-device 参数；桌面工具也列出了两个 N.E.K.O. 窗口。未创建模拟麦克风或隐藏桌面的验收场景。
- 当前工作树 HEAD `2c54175`，保留既有未提交工作。启动前两个部署根共 20 个补丁目标均为 `patched`，没有已有 Tutor 会话，48911/48916 未监听。
- NZDT：启动日志横幅 **2026-10-13 16:24:06**；原生语音开始 **16:24:38**；本次语音会话关闭 **16:25:29**。停止后守卫确认无遗留会话、日志不再增长；再次核验宿主端口和原生进程均已退出。
- 固定历史账本 `bargein-autocheck-20261012`，DeepSeek 上限 30、Lanlan.app 上限 8、tech 上限 0；Study 单次启动预算 0。没有提高上限、重置 spent 或更换轮次。
- 没有额外录音、回环采集或语音文件上传。正常 Realtime 麦克风上行属于本次用户授权测试。

启动参数：

```text
Start-Tutor.cmd --voice --minutes 5 --budget-round bargein-autocheck-20261012 --egress-budget 30 --api-budget 0 --voice-host www.lanlan.app --voice-connects 8 --code-root keep
```

## 日志顺序（L2）

来源为 `benchmarks/raw/neko-desktop-host.log` 本次横幅起的 688 行，另核对当天应用日志。关键原始行号已保存在 `benchmarks/raw/evidence/live-human-barge-in-20261013-log-excerpt.txt`。

| NZDT | 观察 |
|---|---|
| 16:24:46 | 初始发问阶段 onset declined，尚无音频锚点。该日志的巨大秒数来自未初始化的活动时间，不是等待时长。 |
| 16:24:49 | `voice user_transcript ... len=50`，初始语音有转写事件。 |
| 16:24:50 | Study `concept_explain degraded: this learning run has reached its API budget`，教学工具降级。 |
| 16:24:52 | 首个 `response.audio.delta`，12,584 bytes；随后该回答汇总 `audio_deltas=14`，文本为函数定义。 |
| 16:24:57 / 59 | 真麦输入持续到达：两个 meter 桶各 66 帧，`speaking=16 / 18`，`raw_loud=0 / 0`。说明有宿主语音活动判定，不能证明持续门槛或交接已满足。 |
| 16:25:10 | `local speech onset declined: nothing audible for 17.1s`；owner 仍为 connection=1。日志没有证明此时用户实际听到的播放状态。 |
| 16:25:15 | 第二个 `voice user_transcript ... len=52`；Study 再次因预算降级。 |
| 16:25:17 | 第二段首个音频增量，12,604 bytes；汇总 `audio_deltas=16`，文本是“计算器加法”例子。用户说明只有完全等老师说完后另起一句才被识别，因此这不能算插话的新回答。 |
| 16:25:29 | 会话关闭。`omni_mic_audio_bytes=1523788` 是累计上行计量，不能证明被吞的那句话逐帧到达 provider。 |

本次窗口计数：`handoff complete=0`、`handoff failed=0`、非 declined 的 `local speech onset (...)=0`、`has no attribute 'speech_id'=0`、`Omni native microphone connection closed=0`。当天应用日志也没有本次交接成功或旧 accessor 异常。停止时的正常 WebSocket close 不计作产品异常。

`response.done` 只代表 provider 回答结束，不能当作扬声器已停止。没有声学录音或浏览器播放队列快照来给插话时刻做精确对齐。

## 用户听感（L4）与结论

用户确认插话时老师仍在讲话，并报告：老师继续说完，插话被吞；即便用户的同一句话跨过老师结束，也仍被吞；必须等老师完全说完后重新开一句话才会被识别。

**真人验收 FAIL。** 有真实老师语音和用户报告的实际插话窗口，但旧回答没有停止、插话没有正常处理。第二段正常回答不证明成功打断。离线 mock PASS 不改变这个结论。

## 消耗与清理

| Host | 测试前 | 测试后 | 新增 |
|---|---:|---:|---:|
| DeepSeek | 30/30 | 30/30 | 0 |
| Lanlan.app | 6/8 | 7/8 | 1 CONNECT |
| Lanlan.tech | spent 未列，上限 0 | 同前 | 0 |

这是本地出口账本的连接/请求计量，不是 provider 账单金额。剩 1 条 app CONNECT 不够再做完整初始连接加交接，本次没有重试。

清理守卫输出：`stuck=[]`、`left_over=[]`、`host_log_still_advancing=false`；后续快照 `processes=[]`，48911/48916 和 N.E.K.O./lesson 进程核验也为空。前后快照分别为 `benchmarks/raw/evidence/live-human-barge-in-20261013-before.json` 和 `...-after.json`。

## 后续只读诊断（同日，真人结论仍为 FAIL）

用户随后要求定位并仅修复已证根因，又明确收窄：事件丢失或 owner 不匹配若无法证明，就停止，不做推测性补丁。此次只更新本节；生产源码、补丁脚本、manifest 和两个已部署根均未修改。没有重新启动产品或使用网络、音频设备及额度。

**已证：** 16:25:10 那次进入了 audible 门禁，因此该次持续语音条件已满足；不能把同一结论套给 16:24:57/59 的插话。`_note_local_onset_declined`（`_transport.py:1323–1335`）限流 20 秒，16:24:46 的 declined 会隐藏随后约 20 秒内的拒绝；57/59 秒没有 onset 日志，不等于从未尝试。

**17.1 秒的含义：** `_transport.py:3887` 在音频投递处用 `time.time()` 写 `_ai_recent_activity_time`；`:1436/1444` 用同一时钟相减。首段音频从 16:24:52 开始，14 个 delta 在约 16:24:53–54 的 `response.done` 前投递完；17.1 秒对应最后一次投递距 16:25:10 的年龄，不是首个 delta 的年龄，更不是已静音时长。前端反馈另用后端接收时的 `time.monotonic()`（`asr_runtime.py:4397–4406`），与门禁中的 monotonic 相减，源码没有两种时钟混算；日志不足以排除现场时钟跳变，但不需要该假设就能解释数值。

**反馈与归属：** 前端现有 200 ms heartbeat 在有播放工作时发 `native_speech_playback_state`，携带 `native_connection_*`；后端只接收当前输出 websocket、当前物理连接 token 和布尔 active。门禁优先使用 2 秒内的反馈，否则退回最近投递时间。dispatch/current speech ID 不同可由 `response.done` 轮换解释；该字段差异本身不证明物理连接 token 错误。该场两份日志均没有反馈载荷、接收/拒绝记录或播放器快照，**不能区分反馈未发/丢失、反馈过期、active=false、token 或 websocket 不匹配**。`:1444` 的同一句 declined 在这些分支都可能出现。两个部署根的 transport、ASR 和 playback 源码哈希一致，并匹配修前 manifest；它们不证明当时 Electron 实际加载的 JS 或反馈收包状态。

仅做两项聚焦离线验证：

| 验证 | 结果与边界 |
|---|---|
| 标准库 AST 抽取实际持续语音块、onset 与反馈接收函数；不导入宿主 | 新鲜 owner 播放反馈可在投递已旧 17.1 秒时触发；其他 socket/旧 token 被拒绝。确定性跨结束案例失败：前 8 帧 speech_active=True 时 active=True，后 10 帧仍为同一句 speech，但 owner 发 active=False，满 0.5 秒后没有 handoff。合计 4 项通过、该边界 1 项失败。诊断用临时脚本已删除，没有留下失败套件。 |
| Node VM 执行实际 WebSocket header/blob 分支和 playback 模块，Web Audio 为内存对象 | PASS：owner A 调度后发 active=True；provider 不再送音频、播放仍在继续时 heartbeat 仍发 owner A/True；最后 source ended 发 owner A/False。没有浏览器、真实 Web Audio、麦克风、provider 或配置迁移。 |

**结论：本场精确根因仍未证明，所以没有生产修复。** AST 证明一个与用户描述相符的跨结束资格缺陷：门禁在持续语音达标后才查当前播放，未记住同一句话开始时的播放 owner；但它不证明该场被吞语句实际满足了这个时序，也不证明 57/59 秒主插话为何未交接。不能据此扩大成播放反馈修复，不能调低 VAD/持续阈值或延长无 owner 的计时器。

建议的最小接缝是：先明确现有反馈在该场是否被当前 owner 接收；若确认，再在现有持续语音候选开始时保存新鲜播放 owner，在同一句话跨结束达标时沿用该资格，并在既有 0.15 秒静默重置、物理连接/输入 generation 变化时撤销。继续沿用现有有界 PCM 和 native handoff，不新建架构。此次没有执行此建议。

**真实麦克风未重测；旧语音停止、PCM 交接、新回答及跨结束的同一句话均未通过修后真人验收。** 本场没有进入 handoff，也不能评价其 replay 或旧 accessor 的真人回归。账本保持 DeepSeek 30/30、Lanlan.app 7/8、Lanlan.tech 上限 0；app 剩 1 条不足以覆盖完整初始连接加替换连接，禁止自动追加或改 cap。只有用户另行授权且额度可覆盖时才进行有界真人复验。
