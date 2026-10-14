# 阶段十七：固定输入来源与 Study 页面接续

本阶段继承阶段十六 d0c28db，记录已检查的阶段成果；具体发布标识见项目 status，不等于整个 A–F Goal 完成。完整任务与权限依据 [contract](../daily-companion-contract-2026-10-14.md)，最新人类允许必要约 4% 扬声器，仍禁止麦克风、捕获设备与回环；本阶段无声音。

## 实际本地控制诊断

首次新的 task Native/output-only/offline 场（私有 `daily-phase17-fixed-control.json`）只 begin/end 固定票，不 start_session、不 PCM、WAV、provider 或设备。known root 48911、task debug port 9233，8 捕获 API 保护先于应用安装。core/gen2 之后，同一 wire 出现 none/gen1，随后收到 `invalid_or_stale_control`。原票保持、none/gen3 释放正常。诊断正常退出仅指记录完成，不是准入 PASS。

只读提取本任务 packaged ASAR 的 chat/pet websocket bridge；ELECTRON_RUN_AS_NODE 文件读取，没有启动 Electron 应用或改 ASAR。chat RAW_SEND 经 pet `_activeWs.send(rawData)` 透传，能解释不同页面私有计数共享 wire 的条件；不唯一归因历史 27。trace socket_id 指 wire 对象，不证明 renderer 发送者。

修复仅作用于 captureBlocked 的 `/chat` 和 `/chat_full`：从未发送非 passive 状态的辅助页面持续省略纯 idle 快照，在计数/fingerprint 更新前返回。硬 mute、focus、recovering/timed_out/failed、game 及曾活动后的 release 保留。fixed source API 限 known root pathname，ordinary 输入行为不改。未知源仍通过逆向完整 base SHA 拒绝，不调整 server 准入或伪造 generation。

修后独立 fresh task `daily-phase17-control-postfix.json`：active ticket id1/core/gen2、socket1、start wall1791967848.646；注册观测窗口内所有已记录 reject 和本票 reject 均为空，release=true、cleanup_errors=[]。这是 **实际本地 Native 控制观测通过**，没有正向 provider ACK、session、PCM 或模型，不能证明真实 ASR/TTS/普通真人打断。

两次 ledger bytes 均未变：沿用 bargein-autocheck-20261012，DS610/2000、app58/无固定累计上限、tech0/0。源/Native 子进程清理完成，不凭旧 PID 清进程。

## 源码与离线验证

- 实际完整 capture controller Node21、telemetry8、实际 JS→router/ASR 窄边界4、ASGI/pinned replay6通过。新增 focus/active→release、recovering/timed_out/failed/game 用无设备状态夹具；最初 fixture 误用 waiting，改成源码 recovering 后通过，未改变产品恢复状态。
- Native telemetry 绑定当前 socket/start wall/ticket；send/receive 记录 socket_id，audio correlation 改成每 socket closure，旧 socket 后到 chunk 不污染新 socket binary。仍保留所有旧 reject，不忽略失配。有效本地 receipt 不是服务端 ACK。
- 独立 scope review 未发现 passive 修复具体 P1/P2；pathname 自身不验证完整 proxy/origin，仍依赖 task guard 与已知 root observer。

## Study 页面工作与剩余

三个初始源码问题已修：讲解成功后 status 失败覆盖回答；UI 只能 fresh 开课；真实 plain status 不公开当前 held 题。新增 resume/fresh 明确按钮，公开当前 session/题/state 时复用 existing public projection，隐藏私有答案/cache/owner；同题刷新保 draft，身份变化清旧题/答案。成功后的附带刷新失败保 reply/image，独立 notice，零自动模型重试。

Main初始 UI13/public status3/material14离线通过。独立 review 随后发现另一 P2：评分/出题/总结旧课程 RPC 晚到可覆盖新课程 DOM。现三条请求在首次 await 前绑定课程/session/既有材料 revision，success/catch 在结果写入前核范围；评分额外核 q/attempt。scope/selection 准备也受守卫，合法当前可选 selection 失败保原 literal fallback；不改后端或另建记忆。Main最终实际 UI44通过，含三操作×三个身份×晚成功/失败、题 identity、准备晚响应以及当前错误/成功。独立源码复审确认原 P2 已闭合，degraded 返回早守卫是 SOURCE 覆盖而非独立 degraded 执行 PASS。

新增 existing E2E 的 `--resume-offline` 场：新 fixture store、actual SQLite held checkpoint、actual SDK/runs/export 和真实 DOM。初始 runtime1/2 的单个讲解响应及后续503明确是 synthetic；最终 runtime3 另有明确 synthetic delayed grade，两类结果均不转发模型。不会付费造题、复制 C33 DB 或修改原 daily。先执行用户指定 shared web-inspector 做初态检查；随后维护既有项目 E2E，以真实就绪/操作完成为条件，而不把 HTTP200/DOMContentLoaded 当 Ready。

首场 `daily-phase17-study-runtime.json` 已保留 FAIL：实际 status/session/public 原题成功，但测试未展开现有 Adaptive Practice details，答案框不可见而 fill 超时。只修 harness 通过 summary 点击展开，不强制填隐藏控件、不更改产品。第二 fresh 场 `daily-phase17-study-runtime2.json`/`neko-desktop-study-ui-20261014T085650Z.json` **REAL LOCAL SDK/SQLITE/BROWSER PASS**：真实当前题 q/attempt、私有字段剔除；同题 refresh 保 draft；reload 后可见原题；实际 set_course A→B→A 保原 q/attempt；实际 start_session 后返回不复活旧题。单个明确 synthetic explain→503 场只 submit1/status failure1，保 reply/独立 notice，actual status 恢复清 notice且保 reply。唯一 console503来自注入负例，页面JS异常为空。

两个 bounded 宿主/browser 场均 cleanup_errors=[]、ledger bytes unchanged，无麦克风/捕获/声音/provider，原daily untouched。此时 runtime2 是 late-RPC 修复前版本，保留其范围。

最终 Main source `38cb30d8...` 同步后追加定向 runtime3，新 fresh task、不重写前两场证据。实际 Chromium 中 synthetic grade 的 export 延迟期间，actual SDK set_course B+refresh 更新身份；释放旧结果后 B reply/feedback 未被覆盖，grade请求仅1。这是**真实浏览器迟到结果守卫 PASS + 明确 synthetic 评分**，不是模型评分或 DB grade。随后现有实际刷新、reload、A→B→A、显式fresh与synthetic explain/status故障路径在最终版本通过；`daily-phase17-study-runtime3.json`/`neko-desktop-study-ui-20261014T090103Z.json`，cleanup_errors=[]、ledger bytes不变。唯一console503仍是故障夹具。普通自动出题本场未执行，不用 grade 场冒认已过；其 scope helper 来自 base `static/knowledge-map.js:88/104`，canonical index script在main之前载入，host复制既有资产，没有缺失global的新发现。

真实 provider、当前声音/自然停顿/语言术语、完整连续学习与集中真人体验仍待。局部失败记 blockers 并转其他可做任务；完成只依据实际交付及相应证据。

## 发布检查

managed 功能分支沿用 d0c28db，只准备17个精确代码/manifest/test/证据文件。候选 Node controller21+StudyUI44、public status3、telemetry8共76通过；AST/source hash、密钥模式、diff-check及Root空index检查。候选补充仅4个 ignored 原源码依赖，不复制配置、DB、历史或ASAR；私有运行raw、fixture数据库与音频文件不进入提交。source gate仍精确核实际capture及helpers；原daily新版实际启动待后续，不用任务fixture冒认。
