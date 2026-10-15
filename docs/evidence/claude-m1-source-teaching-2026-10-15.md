# M1：源码回答更快且能接续（Claude Goal）

日期 2026-10-15。Goal：[claude-goal-2026-10-15](../claude-goal-2026-10-15.md)。证据层级：源码/离线 + 真实文字模型。没有 Native、设备或真人证据。

## 改了什么

| 改动 | 位置 | 保护 |
|---|---|---|
| 语义路由只看"学习者问题 + 请求的文件/符号名"，讲解模型仍拿完整证据 | `study_code_teaching.py` `_route_text`；`entry_tutor_explain_entries.py`（内部键 `semantic_route_text`）；`entry_tutor_context_support.py` 查询优先级 | 只有 project_code 设置该键；其它入口查询不变（离线断言）；路由流程、置信度、topic 匹配、配额预留、response_mode 逻辑未改；该键不在提示词白名单里 |
| 追问省略 `code_requests` 时，重读本会话最近一次 `code_question` 的源码窗口（当前版本） | `study_code_teaching.py` `last_source_requests` | 只取同一会话、同一授权项目；最多 3 个窗口、每窗不超过 120 行；版本移动时提示"首次读取于 X、现在是 Y"；没有可复用记录时拒绝，照旧要求指定文件 |
| 讲解记录和事件只存"问题 + 来源（项目@版本 文件:行）"，不存代码 | `_finalize_tutor_call`、`_record_tutor_result` 使用 `history_input_text` | 旧记录不改；非源码讲解照旧存原文 |
| 教师上下文增加最近 3 次源码读取的来源（不含代码） | `llm_prompts.py` `_recent_source_reads` | 明确标注只是来源，事实仍须来自本次证据 |
| 索引同步按改动跳过：授权目录的路径、大小、mtime 指纹与上次成功同步相同时，返回 `unchanged`，不跑约 2–3 秒的 sync | `study_code_tools.py` `_code_sync`、`_code_tree_fingerprint` | 任何新增、删除、改名、编辑都会同步；同步失败不记指纹；force 和空结果重试照旧；指纹存于插件数据目录 `code_sync_state.json`，重启后仍生效 |

## 离线

- 31 个相关模块共 236 个测试通过，另有 `test_knowledge_topic_routing` 脚本通过。
- 新增 9 个 case：`test_neko_project_code_teaching` +3，`test_neko_source_route_memory` 3，`test_neko_code_sync_fingerprint` 3。
- 修了两个旧夹具：`test_neko_teaching_failures` 的 exec 命名空间缺 `__name__`；路由测试缺 `phase`。
- 仍失败且早于本次改动：`test_code_tool_boundaries`、`test_scope_and_window_fallback`（relative import）；`test_language_pin_safety`、`test_turn_language_request`（比对的是旧的 neko-product-data 副本）。

## 真实文字场 `claude-m1-followup3-1`

复用 task store 69 和用户已授权的 Sky Scout（7aae20f），静音、text-only，无 Native、麦克风或采集。

| 轮 | 问题 | 结果 | 回调 | 主要分段 |
|---|---|---|---|---|
| 1 | 解释非 200 处理（指定 file 1–29） | 正确：22–24 行抛异常，不解析 body，上层不推断 | 6.98 s | 首次 sync 3.00 s，inventory 0.53 s，路由 1.86 s，讲解 0.69 s |
| 2 | 改成 `>= 500` 后 404 会怎样（不带 code_requests） | 正确：不再抛出，走到 26 行解析；"很可能失败"标为推断 | 2.89 s | sync throttled，路由 1.00 s，讲解 1.11 s |
| 3 | 错误说法"非 200 会先调用 fromJson" | 正确拒绝，引用 22–24 与 26 行 | 2.56 s | 路由 0.83 s，讲解 0.97 s |

- 路由输入 389–403 token；阶段57 的 70 场同类请求是 1,368 token。路由耗时与 token 数关系不大：历史上约 400 token 的路由也要 1.9–2.3 秒。所以这项改动不能解释 73 场的 12 秒超时。
- 新记录约 165 字符，只含问题和来源。
- DeepSeek 890→896，恰好 6 次；旧 6 条记录 SHA 不变；清理无错（owned host exit 1 为受控停止）。
- 不足：第 3 轮在口语里念出了完整路径。指纹同步是在这场之后加的，尚无真实场证据，会在 M2 的场次里一并观察。

## 下一步候选（不在 M1 内实施）

路由已不依赖证据，可以与源码读取并发，按本场数字可省约 0.7–1.2 秒。需要处理取消、预留归属和失败丢弃，等 M2 测出 Native 侧开销后再决定。
