# W5：验收彩排（第 2、4、5、6、7 步）

日期 2026-10-15。证据层级分开写：离线 / 真实文字模型 / output-only Native 固定 WAV / 可听性（待用户）/ 真人（待用户）。所有 WAV 都是文件合成（`scripts/make_w5_fixture_wavs.ps1`，System.Speech 直接写文件），不播放、不采集；扬声器为用户预设 4%。本任务账本合计 DeepSeek +148（968→1116，上限 +150）、Lanlan.app +10（90→100，上限 +20），**用尽，不再有真实模型场**。

| 步 | 彩排方式 | 结果 | 层级 |
|---|---|---|---|
| 2 问 weather_service 的非 200 处理 | 沿用 M2/M5 已有的 Native 固定 WAV 场（英文输入）、W1/W2 文字场（中文，指定 file 窗口）。没有为中文原句再合成一场 | 回答都对：22–24 行抛出，26 行解析不会执行；"正在查看源码……"提示 M2 已实测触发；读法见 W4 | 真实文字模型 + Native（M2） |
| 3 打断 | 不在本任务范围（不触碰打断逻辑） | 沿用 M3 离线 + 既有打断测试 | — |
| 4 带停顿追问"改成 500 以上才抛，404 会怎样" | 新合成中文 WAV（两处约 0.9 s 停顿），store `…-m5`，`NEKO_PAUSE_HOLD=1`，两场 | **第一次发现缺陷**：角色把 `code_requests` 发成了 `["…一个字符串…"]`，整个调用被拒，角色念出"请指定一至三个有界源码范围后再讲解"。修复后文字 SDK 用同样形状的请求（`["weather_service.dart"]`）得到正确回答：改成 `>=500` 后 404 不抛，继续走到第 26 行 `Weather.fromJson`，能否解析成功标为推断。**修复后没有再跑 Native 场（预算用尽）**——语音端到端的修复后验证留给集中验收 | 真实文字模型（修复后）；Native（修复前，失败） |
| 5 出题→故意答错→纠正→记录 | 文字 SDK `w5step5`（`claude-w5-step5-2`）；语音端另有 W1 的产品路径场（出题→答错→追问） | 出题（`study_quiz`）；答错被判 `wrong`、`misconception`；纠正用 `correction_of` 创建同一题的新尝试，判 `partial` 70，指出"少了先检查状态码"；数据库 `qa_records` 1→2、`wrong_questions` 2 条（原错答保留）、`mastery_snapshots` 0.0→0.1468。纠正句"非 200 时直接抛出异常，不会解析 body"本身是对的，但被判部分正确——评分偏严 | 真实文字模型 + 本地 SQLite |
| 6 换图并指出关系 | W3 | 新图被使用（REZ → NUD → WEX），旧语音被停止；学习材料窗口的 DOM 指示/换图/清除/重开 40 项通过。**角色自主指示图上某个关系没有被观测到** | DOM + Native（W3） |
| 7 重启后接续 | M5 已有真实文字证据（换课返回、重启、断网、恢复）；本任务未重做。语音端接续在 W5 第 4 步的 m5 store 上间接用到（同一课程的更早会话）：修复前被上面的缺陷挡住 | 文字端通过（M5）；语音端待用户 | 真实文字模型（M5） |

## 本轮发现并修复的问题（payload 层，已部署）

1. **字符串形式的 `code_requests`。** 现象：Native 语音路径下，模型把"目标列表"发成了含一个字符串的列表，校验直接拒绝，用户听到一句与问题无关的"请指定……"。诊断：为被拒请求新增只记类型和键名的日志（`study_explain project_code refused: … shape=list[1]:['str']`），一次 Native 场就确认了形状（不记录任何值）。修复：`coerce_code_requests` 把像文件名/路径（可带 `:行` 或 `:起-止`）的字符串读成有界文件请求；自由文本不指向任何来源，被丢弃，列表为空就等同于"刚才读的那段"；单行引用给上下文窗口。同时 `null`/`[]`/`[{}]`/空字符串视为"省略"。仍然是无效的请求（未知字段、空文件名、整数）照旧被拒绝，三项上限不变。位置 `study_code_teaching.py`；离线 +6 个用例。
2. **（W2 已写）** 结构错嵌套、追问丢前面的文件。

## 没有解决 / 需要用户判断

- 第 4 步语音端到端：修复后没有 Native 场。预期会通过（文字端同形状请求已通过），但这是推断。
- provider 在较短停顿处仍会出两条识别事件（本场：第二处停顿后 "404 会怎样？" 单独成条；暂扣丢弃了 0.70 s 与 0.49 s），但这次只发出一次工具调用、只有一个回答。验收时的体验要看用户的真实停顿。
- 评分偏严（纠正对了仍判部分正确），属模型判分，不改。
- 角色自主指示图上关系：未验证；验收说明已把它写成已知限制。
- 听感（读法、语速）：待用户。

## 离线

每个 `scripts/test_neko_*.py` 模块各用独立进程运行（`claude-w5-offline-all.log`，103 个模块）：**96 个通过**，7 个未通过，都与本轮 payload 改动无关、而且都是宿主补丁夹具/就绪检查：

- `test_neko_autocheck_readiness`（读到 `www.lanlan.app` 预算为 `None` 时的类型错误）、`test_neko_tool_result_lifecycle`（宿主 `_tools.py` 替换锚点不唯一）；
- `test_neko_first_asr_ordering`、`test_neko_late_asr_tool_patch`、`test_neko_study_singleflight`、`test_neko_study_speech_gate`（"unknown edited late-ASR helper"）、`test_neko_material_audio`（"unknown material patch fixture anchor"）：这些夹具拿旧版本补丁去匹配现在已叠加了 M2/M3 补丁的宿主文件。
- 我没有改过任何宿主文件；`neko_voice_host_patch.py --check` 对两棵宿主树全部为 patched。已列入状态文件"待 Opus 复核"。

另：同进程里连续跑整套会被隔离守卫串扰（58 个假错误），所以回归口径是"每模块一个进程"。product 目录下的旧脚本 `test_code_tool_boundaries`、`test_scope_and_window_fallback` 仍因相对导入无法独立运行（M1 报告已记）。

新增：`test_neko_source_question_kinds`（12 个用例）、`test_neko_structure_fold`（4）、`test_neko_speakable_line_refs`（7）；`test_neko_code_history_revision`、`test_neko_code_structure_request`、`test_neko_teaching_failures`、`test_avatar_reply_shape` 各补了断言/名字白名单。

## 部署

payload、product manifest、已部署副本三方 SHA 开工前一致；备份在 `benchmarks/raw/evidence/claude-{w2w4,w2b,w5,w5b}-payload-before/`（不提交）。最终 32 个 manifest 条目与已部署副本逐文件 SHA 一致；SourceGate PASS。
