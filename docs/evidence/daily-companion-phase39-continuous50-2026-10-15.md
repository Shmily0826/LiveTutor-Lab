# 阶段39：连续场50与反馈边界实证

2026-10-15。上一轮37/38实际开发、审查、部署、发布属于progress，本轮唯一必要场50首次使用新的完整Native观测和反馈digest，不重跑未改的旧基线。完整契约仍为[contract](../daily-companion-contract-2026-10-14.md)，A–F未缩减，Goal保持active。

## 实际结果：PARTIAL，不是完整交付

场50 exec session88098已terminal/exit1，report finalized=true、failure=`RuntimeError: voice session ended abnormally`、cleanup=[]。launcher44128/Native33564已不存在；48911/48916/9234无listener。原round DS785→810/2000、app74→76/null、tech0/0，不重置，计数非金额。没有再次重试或并行在线场。

复用原forwardPNG和47三WAV，fresh任务store `neko-daily-speech-acceptance-20261015-50`，不预先造题；output-only、speech-gate、phrase-input、grade-chain、prepare-picture、verify-picture-state。实际renderer捕获保护为installed/captureBlocked/readonly，8API全阻断；无房间/物理/虚拟mic、capture或loopback，未调整用户已设4%音量。Native AudioContext运行及排程不是物理可听证据；human仍PENDING。

原report `benchmarks/raw/evidence/daily-companion-20261015-continuous50.json` SHA256 `4b6d1d115aa24e4e1e5d84a397a9f7dbf702f7504405e1ccca3149a80b9b7c41`，未回写。47条实际study-text JSON从本场开始至terminal report mtime的日志窗口独占保存为 `daily-companion-20261015-continuous50.study-text.json`，SHA `ee7b49ab9eae3ff9ae5db5f1b19d0ad73cc0b8fdb4acaeda1564eec95b6509f3`；sidecar绑定report和原log bytes/hash，不含正文，不冒称provider ACK。这些raw不入Git。

## 真实模型、SQLite和Native

Native累计sequence完整1..330，25 binary frames中22正/3空，共942880bytes；没有ring丢失或observer异常。按每轮真实时间窗口：

| 轮 | 实际ASR | binary/正帧 | bytes | QA/formal总数 | 实际行为 |
|---|---:|---:|---:|---:|---|
| 出题 | 1 | 7/7 | 252320 | 0/0 | 角色实际study_quiz：从WEX出发的箭头指向谁；未提前公布答案。 |
| 答题 | 1 | 8/7 | 381800 | 1/1 | 完整自然答案WEX指向NUD，唯一正式correct100，同题/attempt，原自然ASR保留。 |
| 追问 | 2 | 10/8 | 308760 | 1/1 | 没有额外grade/新题，但拆成两轮；未实际调用study_explain，直接引入“被调用”的语义，图的方向事实不足以证明调用。 |

第二轮grade检查除run_finished_without_failure外19项成立，native_terminal实际使用完整历史中的source_ended后late empty cancel证据；因第三异常，原结果仍FAIL_OR_PARTIAL。第三两个ASR也不满足当前严格three-completed判据，不能通过新量具修复把本场改成PASS。[独立复核](daily-companion-continuous50-review-2026-10-15.md)已冻结。

## 新增边界证据

正式feedback20字符，hash `28a08a16fd0036f7de6e11e868f864e0c6e67a62d39b5eae9383b9c85c96ae39`，等于actual serialized relay的裸reply20字符hash；整个622bytes wire envelope另hash，不与裸反馈混比。

新conn2、response `resp_1792005894368` 实际六delta有序累计23字符，最后 **stream_sha256** `23a44b785cc36a05c5c9356a78245aae0655ab6da78e713384c5c830c8c1a75f`，与Omni callback、Core entry、queue、WS及Native全部23字符hash相等。正式20与Native23仅增加3空格，去空格精确相等。**本场没有本地答案截断；不能回溯宣称49也是同一原因或已经修好49。** 单chunk的sha256不能当累计stream_sha256比较。

## 真实退出及离线候选机制

第三最后source_ended为1792005960.404，1792005981.493收到真实status `ASR_INPUT_DELIVERY_FAILED`（sequence330）。实际arbiter同cid/gen2于5981.232退出，reason=`native phrase input delivery failed`，距第三整批flush完成5951.1242325约30.108秒。不是observer错误，不能忽略该状态让验收通过。

早先“Core host-turn guard跳过输入boundary”只是候选。进一步核本场第三两响应：arbiter实际为`rejected_no_owner/idle`、terminal=`no_owner_release`，未观察到host-newturn拒绝日志。因此没有实施将boundary移到host guard前的猜测改动。

Main用现有 `test_neko_phrase_input_transport.PhraseTransport` 的actual Core/Omni/queue socket fixture，仅本地固定PCM与假provider事件重放（无网络/设备）：实际profile解析为`lanlan_app_gemini`、announces=false；完整phrase写完后input_sequence16/waiting16。投递合成completed-ASR、带fixture response ID的audio_transcript.delta、completed response.done；无需更改Core host turn，response_input_sequence仍None、waiting16/input_open仍保留。将deadline时钟推进31秒，实际watch记录fatal=true、failure=`phrase_provider_boundary_timeout`。fixture事件不是真实provider/ASR证据。

这证明当前never-announcing自动响应路径存在可复现的等待归属缺口：没有arbiter owner时content不触发_begin_response_lifecycle，响应输入序号未更新，随后terminal无法退役当前waiting。它与50相符，但50未记录该时刻waiting/response-input sequence，仍不冒唯一运行时根因。修复需要明确原生自动响应与实际输入的合法归属设计，不能把旧响应直接绑定到当前input、把本地序号当ASR ID、伪造ACK、延长超时掩盖或取消普通打断保护。

## 本轮另交付：证据自动保留

场50首次新digest仅在宿主日志，probe原final解析未包含此marker，故本场以冻结sidecar保留，原report不改。未来probe已在其真实fresh_log byte slice中保存study_text_trace；新增纯parser拒绝正文字段/未知字段、坏stage/类型/指纹、超大时钟和过深JSON，同时间不同delta保持顺序不去重。Main用实际global log按sidecar原窗口抽取，与冻结47条逐项完全相等；独立亦核相等。

独立发现坏JSON时钟OverflowError及decoder RecursionError可中断finally的P2，已仅在时间转换/decoder对应处安全跳过；后续合法行保留。Main15离线通过（.008s），独立15通过（.009s），[捕获审查](daily-companion-trace-capture-review-2026-10-15.md)已关闭该P2。无生产音频路由修改。

## 接续

下一40先离线处理native automatic response的输入归属缺口与追问取证；无正确归属方案时记录具体条件并推进其他A–F，不能以该局部问题结束Goal。日常AUTO仍OFF；文字入口、概念历史、源码/屏幕与稳定性交付继续，成熟后一次集中真人体验。当前无live场，不要求本人逐句测试。三个当前记录原bytes已独占归档，contract未改。
