# 源码计时间隙与空回合自动重试收尾

日期：2026-10-15。仅处理本次两个收尾项，不重做 M1–M5。

## 设计结论（实施前）

1. 源码工具：仅用现有 `phase()` 增补过滤、泄密复查、证据整理、编号窗口和 `synced-after-empty` 各步骤计时。保持过滤、授权、版本检查、同步和重试行为不变。历史 trace `6365b9e1349b` 的间隙为 `4657.562 - (338.967 + 1409.953) = 2908.642 ms`；同一调用日志明确为 `mode=explore query='非200状态码分支' shown_files=0 index_sync=synced-after-empty`，因此优先核查强制同步及第二次查询路径。不能由旧 trace 单独分配这 2908.642 ms 到每个步骤。
2. provider 空回合：**风险过高，本次只交付设计，不实施自动重试。** `inject_text_and_request_response` 可用于主动注入，但现有接口本身不提供“原语音问题只补一次且重新开口即作废”的完整保证。保留已有“请再说一遍”提示；不新增开关、宿主补丁或启动链改动。

### 为什么不直接接 inject

- `_transport.py` 的空回答提示只拿最近识别时间、内容计数、完成计数、连接 generation 等做活动判定；它没有把本次 `response.done` 绑定到原始语音输入 item 的唯一身份。已有 M2 证据还显示结束的 response 可能在开口前已创建。静默 3 秒只能作为提示条件，不能证明 provider 之后不会回答。
- `_responses.py::inject_text_and_request_response` 的 WebSocket 路径会创建新的 `role=user` 消息，以 `source='proactive', priority=20` 进入 arbiter，随后 `await shield(ticket.sent)`。它不是对原音频请求的幂等重试，会增加会话条目。
- arbiter 的 `enqueue` 支持 `admission_check`，但 inject 未开放或传入这一参数。调用前检查与真正发出之间可能有队列等待和 await；新用户语音可能在此期间发生。`notify_server_vad_started` 明确不改变 ownership，直到 `speech_stopped` 才处理自动响应归属。单纯调用前检查不足以满足“重新说话即作废”。
- `cancel_ticket` 和取消 inject task 可以撤销待发请求、处理已发请求，但不能撤回 provider 已接受的 user item，也不能单凭“空回合”判定排除原生延迟回复。连接替换已有 arbiter 清理能力，但不能据此推定跨 await 的原问题归属也已覆盖。

若将来实施，需要先形成原语音输入 item + connection generation + 用户 turn epoch 的稳定归属，在所有排队/发送边界复查 admission，跟踪取消 task 与确切 ticket，并证明旧 response 延迟内容与新 inject 不会双播。需覆盖：等待期间及发送 await 内重新开口、排队时晚到 response.created/内容、连接替换、工具执行、取消回合和重复 terminal。该改动会扩展共享 inject/arbiter 的契约，超过本次独立小补丁可安全证明的范围。默认关闭开关和最多两场随机 output-only 测试不能替代这些保证。

## 任务 1：结果与证据

**已完成计时与部署；不改源码工具行为。** 新增固定阶段名：`file_candidates`、`source_file_window`、`source_structure`、`source_filter`、`source_leak`、`source_evidence`、`source_shown`，以及 `source_retry_sync/query/filter/leak/evidence/shown`。沿用 `phase()` 的 name/at_ms/elapsed_ms/outcome 格式，无问题文字、源码内容或动态标签。异常仍交给原来的处理路径，取消继续传播。

历史证据（真实模型 + output-only Native，**本次未重跑**）：`benchmarks/raw/evidence/claude-m5-fresh-voice-1.json` 与 `benchmarks/raw/neko-desktop-host.log` 的 trace `6365b9e1349b`，见上面的 2908.642 ms 计算。同调用日志的 `synced-after-empty` 证明这次执行过强制同步和第二次查询；它们原本都没有 phase。该路径在首次无编号行、最近同步状态为 `throttled/unchanged` 时触发，目的是不把索引暂未返回解释成文件不存在。**间隙落在含该重试的代码段已经确认；旧数据无法证明它全部由同步或全部由第二次查询消耗。**

### 当前只读 CodeGraph（无模型、无宿主、无 sync）

在原授权目录用已有 CLI 执行 `explore 非200状态码分支 --path <授权根> --max-files 6`，然后运行实际 `_code_filter`、`_code_leak`、`_shown`；未强制同步、未修改 Sky Scout 或它的索引。

| 查询 | CLI | 过滤 | 泄密复查 | shown | 结果 |
|---|---:|---:|---:|---:|---|
| 原 explore 查询 | 812.493 ms | 2.769 ms | 1.080 ms | 0.126 ms | kept=56、dropped=19、shown_files=0，与历史统计一致；在 unchanged 状态会触发重试 |
| 正确文件路径，1–29 行 | 688.513 ms | 0.179 ms | 0.595 ms | 0.169 ms | shown_files=1、29 行、无泄漏；窗口截取另计 0.042 ms |

文件路径来自现有 `codegraph files --path <授权根> -j`：`sky_scout/app_sky_scout/lib/data/services/weather_service.dart`。第一次诊断把路径写成少了 `/data` 的版本，CLI 虽 exit=0，实际窗口为空；保留失败记录，核对 inventory 后仅纠正一次。表中采用纠正后的结果。

原始诊断：`benchmarks/raw/evidence/codex-followup-code-query-20261015.json`、`codex-followup-code-query-corrected-20261015.json`；辅助脚本在同目录（不发布）。其日志只保存计数和时长，没有保存源码内容。当前过滤等步骤没有复现秒级开销；本次没有执行会写索引的真实强制 sync，因此也没有声称重现完整的历史 2.9 秒或实现提速。保留现有同步重试保障，待自然使用时新 trace 分配其内部耗时。

### 离线证明

- 新增 `scripts/test_neko_code_timing.py`：4 个用例检查文件窗口与过滤计时、空结果触发一次强制同步和同命令重查、计时无内容、泄密拒绝在记录前退出、重查异常与取消传播。同步和第二次查询分别注入 25 ms 等待，断言它们落在各自 phase，避免间隙再被误认成过滤耗时。
- 对开工备份和新文件执行 AST 对比：去掉 phase 包装，并把为独立计时引入的 `retry_leak` 临时变量内联后，AST 完全一致。这是源码行为范围证明，不是模型或性能验收。

## 任务 2：交付范围

按上述设计结论，仅交付说明。自动重试未实施，既有空回合提示保持原样；本次 output-only Native 场数 **0/最多2**。因此没有“本次两场未触发空回合”或“自动重试成功”的结果。未新增 paid/model 请求或 Lanlan.app 连接。

## 检查、部署与发布

指定解释器：`benchmarks/raw/neko-product-host/.venv/Scripts/python.exe`，全部 Python 命令设置 `PYTHONIOENCODING=utf-8` 并使用 `-B`。

- 指定 16 个回归模块与新增计时模块在 `scripts` 下以 `python -B -m unittest` 一起运行：**264 项，262 通过、2 跳过、0 失败（180.580 s）**。跳过来自已有 `test_known_blocker_tool_result_waits_for_native_owner_that_needs_its_result` 的条件：当前已启用 Native tool join，历史 phase40 死锁断言由 `test_neko_native_tool_join` 的成功路径代替；未删除或改动跳过条件。
- `scripts/neko_voice_host_patch.py --check`：34/34 条目全部 `patched`（两个宿主树各17）。
- 在 `scripts` 目录调用 `neko_desktop_tutor_host.verify_source_audio_gate()`：PASS。
- 先 `scripts/neko_host_rebuild_check.py --write`，再无参数校验：31 diff、31/31 SHA 一致、apply exit=0。
- 本次没有修改 Native 宿主源文件、宿主补丁脚本、启动链或 runtime helper；host manifest 的 `patched_sha256` 已核对，无需改值。重生成的31份宿主 diff 没有内容改动，不加入发布。
- 部署前核对 payload、product manifest 条目、已部署 `study_code_tools.py` 三方旧 SHA 均为 `c3df2774fc0637746bd414dcff7e9adb2e333f4e183c9b8699e891044c2bf035`，随后备份到 `benchmarks/raw/evidence/codex-followup-backup-20261015/`，复制 payload 并再次核对新 SHA。product manifest 只更新此条目及本次说明。
- 开工预检有一个继承的部署差异：`static/index.html`（manifest/source `81ebd4ff60bac5bae29b801345f78b1b54f5f768549626cfc90121e023030ba6`；部署 `548f61fc661687c4e83e8298bf4bc4fc714f525d36b29b0ec4935e7c34ead2b9`）。本次不涉及该文件，未覆盖；不声称整份 product 的32项部署全部匹配。源码工具部署 SHA 单独通过。

证据：`benchmarks/raw/evidence/codex-followup-regression-20261015.log`、`codex-followup-voice-patch-check-20261015.json`、`codex-followup-rebuild-write-20261015.json`、`codex-followup-rebuild-check-20261015.json`；这些 raw 文件和备份均不提交。

回归命令（在 `scripts` 目录、使用上述解释器）：

```text
python -B -m unittest test_neko_project_code_teaching test_neko_source_route_memory test_neko_code_sync_fingerprint test_neko_code_file_window test_neko_source_point test_neko_pause_hold test_neko_empty_turn_notice test_neko_phrase_patch_replay test_neko_native_barge_in test_neko_realtime_barge_in test_neko_native_tool_join test_neko_native_tool_runtime test_neko_native_audio_dispatch test_neko_phrase_input_transport test_neko_native_grade_route test_neko_output_only test_neko_code_timing
```

### 精确文件清单与 SHA256

| 文件 | SHA256 |
|---|---|
| `patches/neko-study-2026-10-10-product/payload/study_companion/study_code_tools.py` | `70c4e831331bd239e0a253fc95a1fe45f92ff55d3bed8b91fc4716c7be0d116b` |
| `patches/neko-study-2026-10-10-product/manifest.json` | `2bcd71e50ae35184b19ade69a9a95d29b55b7214b6f279be04ff7f3555f0227f` |
| `scripts/test_neko_code_timing.py` | `02e36a86aaa0c05174746c1e36754f29f0d3096687f765d3252a31b742bac90f` |
| `docs/claude-goal-status.md` | `e32b51a5e742effcc6888c3fe8c7a9f59ea084acda2944f4f1af9163827b0786` |

本报告 `docs/evidence/codex-followup-gap-emptyturn-2026-10-15.md` 的 SHA 见相邻 [校验清单](codex-followup-gap-emptyturn-2026-10-15.sha256)；清单覆盖上述4项及报告本身。清单自身由 Git commit 标识，避免无限自引用。全部交付文件使用 UTF-8/LF。

发布工作树：`C:\Users\Shmily\.codex\worktrees\daily-companion\LiveTutor-Lab`；目标分支 `codex/daily-learning-companion`，开工本地/远端父提交均为 `bb38bcbd09c10380d68ce9cab265af482fbfce98`。三个已存在交付文件与开工发布副本经换行规范化对比完全一致，根目录其他历史改动不带入。本次精确发布上述4项、本报告与 `.sha256` 清单共6个文件；不包含 raw、学习库、录音、备份、密钥或宿主重建 diff。提交自身标识本次交付版本，不合并主分支、不强推。

### 账本与证据边界

账本始终为 `bargein-autocheck-20261012`，不重置、不提额。开工及完成后实核均为 DeepSeek **968/2000**、Lanlan.app **90/无上限**、Lanlan.tech **0/0**；新增分别为 **0、0、0**，在本任务新增30次 DeepSeek、3次 Lanlan.app 上限内。预检文件：`benchmarks/raw/evidence/codex-followup-preflight-20261015.json`、`codex-followup-completion-20261015.json`。

本次证明层级：**源码/离线 PASS；只读真实 CodeGraph 查询 PASS；新增真实模型场未运行；新增 output-only Native 场未运行；设备可听性与真人验收未运行。** 离线音频测试只处理 fixture 字节及 mock transport，不打开采集设备。没有麦克风、虚拟采集、回环或系统音量操作，没有修改 `benchmarks/raw/daily-companion-audio-policy.json`，没有删除历史、学习库或清理根目录工作树。

剩余不确定性：旧 trace 的 2908.642 ms 无法事后拆分；自然使用时强制同步/重查的实际耗时仍待新 trace。provider 空回合的根因、延迟内容的因果归属和自动补发的防双答条件仍未证明，故不启用自动重试。真人验收继续沿用既有 M1–M5 状态。
