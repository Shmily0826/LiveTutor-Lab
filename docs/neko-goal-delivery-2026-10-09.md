# N.E.K.O + Study Companion 改进交付记录（2026-10-09）

## 结论与边界

本轮按 `plugin.toml` 的导入链确认 LIVE 配置入口为 `lab_bootstrap_plane -> package.__init__.StudyCompanionPlugin`，并修改 LIVE package `__init__.py`；LIVE `lab_entry.py` 作为兼容入口也纳入检查。BRIDGE `__init__.py` 与 goal-isolated `__init__.py` 同样检查。三个源码根的 12 个共享模块通过 SHA-256 一致性检查，静态验证覆盖这四个入口。源码位于 Git 忽略的 `benchmarks/raw/`，不会出现在普通 `git diff` 中。

没有改动生产/冻结 EXE、当前运行实例的配置或数据库；没有 reload、重启、TTS/provider 调用、麦克风或声音输出，也没有执行真实 Study UI 操作。当前安全限制下，实际 TTS 请求总数无法从运行实例观测，因此不能把静态零调用记录当成 runtime 零 TTS 证明。

## 分级状态

| 子系统 | 状态 | 本轮结果与证据边界 |
| --- | --- | --- |
| 静音闸 | **PARTIAL** | `silent_mode=true` 已写入源码快照的持久 `plugin.toml`，默认配置也 fail-closed。Python fake sink 对 event bus、direct command 及 LIVE configured `__init__`、LIVE `lab_entry`、BRIDGE、goal-isolated 四条 awareness 入口，在两轮重新实例化配置后均观察到 0 次 `push_message`；`silent_mode=false` 的对照验证三条正常消息路径仍能提交。真实 host 的事件、reload、restart 未执行，因此运行时零 TTS 请求仍未证明。 |
| Session 生命周期/回溯 | **PASS（隔离单元） / PARTIAL（实际插件运行）** | Python 用例从 LIVE configured `__init__.py` 抽取并执行 Session 方法：同一活动窗口的 12 个并发请求复用一个新 Session、6 次显式 restart 各自新建、请求 ID 固定；Store QA 方法在临时文件 DB 累加 2 题并结束 Session，重开后 ended_at/count 保留。实际 `_ensure_column` helper 对临时旧 DB 加 nullable 列且旧记录值不变。未访问真实用户 DB。host 运行仍未验。 |
| 主题分类 | **PASS（隔离函数） / PARTIAL（端到端教学）** | Python/asyncio/事件循环归入 `computer_science`，数学词项仍归 `math`，未知主题保持空分类；已有负例通过。没有批量改历史知识图谱，也未在真实插件/API 验证 current topic 到 generated question 的端到端一致性。 |
| 评分与反馈 | **PASS（隔离归一化） / PARTIAL（LLM rubric）** | 独立负例证明“100 分但有 missing_points”被标 partial 且封顶 80；错误核心机制、无 covered_points 的 20 分被封顶 10。测试调用实际评分归一化函数，无 LLM 请求；仍需真实模型输出验证 rubric 与文字反馈语义一致。 |
| Study UI 端到端 | **GAP** | 未打开 UI，也未操作 OCR→讲解→追问→出题/评分→持久记录。按安全要求，需先用隔离 provider/sink 对插件事件、reload、restart 证明零 TTS，再进行 UI 验收。 |

## 实际改动

- 持久静音开关：源码配置 `silent_mode = true`，`CommunicationConfig` 的缺省也是 true；显式配置 false 可恢复常规消息行为。没有依赖临时 communication override。
- 所有已发现的消息出口：事件总线创建受配置控制，`StudyEventBus` 本身默认静音并在 `emit`/`_emit_open` 拦截；awareness 和 N.E.K.O 命令的直接推送也在调用 provider 前返回。
- Session 并发控制：新建 `_study_session_lock` 串行化启动、显式结束和 idle rollover。请求建立 context 时固定 `session_id`，交互写入与答题 QA 追踪使用同一个 ID；答案评估与异步文档分析也在模型工作前捕获 ID。Session 汇总沿用同一 ID 查询历史。
- 历史保护：schema 只通过 `_ensure_column(..., "session_id", "TEXT")` 添加 nullable 列，不回填旧记录。启动时先从已持久化的插件状态读取上次活动 Session ID，清理函数只按这个单一 ID 更新，并要求它严格符合 `study-` + 32 位小写十六进制格式；即使其他未结束行也符合该格式，也不会被扫描或更新。旧 `run_id` 与所有其他 Session 行保持原样。
- 追踪与教学：增加按明确 Session ID 查询会话和交互记录的入口；新观测的编程主题更新知识图谱 subject；评价 prompt 与结果归一化约束评分/缺失点一致性。

## 验证与原始证据

- **SOURCE / 静态**：运行 `node scripts/verify_neko_lab_static_delivery.mjs`，所有 39 项源码检查通过，包括三个根的 12 个共享模块 SHA-256 一致、plugin.toml 到 LIVE package `__init__` 的导入链、四个入口的静音闸、消息出口闸、Session 锁/请求 ID、历史清理范围、分类和评分规则。原始检查结果：[neko-goal-static-source-check.json](../benchmarks/raw/evidence/neko-goal-static-source-check.json)。它记录四份入口源码 SHA，并明确 `runtime_exercised=false`；其中 TTS 计数 0 只表示静态检查未发 provider 请求。
- **ISOLATED SQLITE SQL CONTRACT**：`node scripts/verify_neko_lab_isolated_db.mjs` 在临时 SQLite 文件执行 3/3 SQL 合约断言，覆盖 nullable 迁移形状、两题计数与只按持久 ID 结束。证据：[neko-goal-isolated-sqlite.json](../benchmarks/raw/evidence/neko-goal-isolated-sqlite.json)。这份证据不是 Python Store/runtime 证明。
- **ISOLATED PYTHON UNIT**：使用仓库内 CPython 3.11.15，以 `-I -S` 执行 `scripts/test_neko_lab_regressions.py`：`Ran 38 tests ... OK`。并发 rollover、QA 请求 Session ID、静音出口与恢复路径重点用例各自单独通过。fake sink 覆盖 event bus、direct command 和四份 awareness 入口；Session 并发、idle rollover、显式 restart、交互/QA 请求 ID、主题与评分负例均通过；临时文件 SQLite 上执行 Store 方法、重开 DB 检查 ended_at/question_count；实际 `_ensure_column` helper 迁移旧交互表并保留旧记录。此次追加的两个 cleanup 用例分别模拟 failed-startup 与 shutdown 中 Session 结束抛出普通异常，并验证后续资源清理继续执行。证据：[neko-goal-isolated-python-unit.json](../benchmarks/raw/evidence/neko-goal-isolated-python-unit.json)。这是隔离函数/Store 单元验收，不等价于 N.E.K.O host reload/restart。
- **PORTABLE PATCH / 部分源码**：可复算包位于 [neko-study-2026-10-09-goal](../patches/neko-study-2026-10-09-goal/README.md)，包含 5 个有保留 preimage 的教学上下文文件、pre/post SHA 与拒绝不匹配目标的验证器。`--smoke-apply` 在临时树中 `git apply --check` 并应用，5/5 文本内容与运行源一致。证据：[neko-goal-portable-patch-smoke.json](../benchmarks/raw/evidence/neko-goal-portable-patch-smoke.json)。静音、Session 生命周期/schema 和评分文件仍没有已验证 pristine preimage，不在此部分补丁内。
- **PLUGIN API / 既有基线**：以下为此前轮次留下的 API 证据，不是本轮代码的运行验收：[teach2-r2-crossmat.json](../benchmarks/raw/evidence/teach2-r2-crossmat.json)、[teach2-r9-reuse.json](../benchmarks/raw/evidence/teach2-r9-reuse.json)、[teach2-r4-scoring.json](../benchmarks/raw/evidence/teach2-r4-scoring.json)。它们分别记录跨主题上下文、asyncio 分类错置，以及 100 分但缺 `du`/核心误解仍得 20 分的原始问题。
- **RUNTIME / 只读健康检查**：本轮最后刷新只读 `GET /health`：48911 main、48915 agent、48916 service 均 HTTP 200/status ok；agent health 显示 computer/browser/plugin/OpenClaw/OpenFang flags 均 false。只证明现有服务健康，不证明加载本轮源码。未访问插件 UI/API，也未触发插件事件。

## Git 与 Review 范围

- 未 commit、未 push；checkpoint SHA：无。
- 本轮新增交付：本报告、静态与 SQLite SQL 合约验证脚本、隔离 Python 回归证据、fingerprinted 部分补丁与构建/验证脚本。`scripts/test_neko_lab_regressions.py` 在开始前已是脏文件，本轮只增补 fake-sink、实际入口、Session/并发、SQLite、分类/评分用例，没有覆盖上一轮内容。
- `benchmarks/raw/` 中有本轮源码变更，但其内容受 Git ignore 规则排除，不能由普通 `git diff` 展示。可直接检查 LIVE configured `__init__.py`、LIVE `lab_entry.py`、BRIDGE/goal-isolated `__init__.py`，以及共享 `models.py`、`store_schema.py`、`store.py`、`store_qa.py`、`entry_tutor_context_support.py`、`entry_tutor_summary_entries.py`、`entry_tutor_answer_entries.py`、`entry_document_analysis_jobs.py`、`prompt_templates.py`、`tutor_llm_agent_answer_evaluate.py`、`_event_bus.py`、`entry_neko_commands.py` 与 LIVE `plugin.toml`。
- 当前 workspace 仍没有 mute/session/schema/scoring 全部源码的 pristine preimage，因此完整可移植补丁是 **GAP**。已将有可验证基线的 5 个教学上下文文件做成带 SHA 的部分补丁；其余关键修复仍位于忽略的 `benchmarks/raw/` 源码树，需取得原始源码快照后再安全生成完整差分。
- 保留开始前的其他未提交文件（`.workbuddy/memory/*`、`patches/neko-study-2026-10-08/*`、round2 文档/补丁和脚本）；未对它们执行 reset、stash、覆盖或暂存。
- `git diff --check` 当前报告的 trailing whitespace 位于开始前已修改的 `patches/neko-study-2026-10-08/study.patch`，本轮没有触碰该补丁文件。

## 当前状态与最少后续动作

运行中的 N.E.K.O 服务保持原样且健康；本轮代码尚未加载到它。隔离 Python 与假 sink 现已通过，但仍需安全证明真实插件事件、reload、restart 的 TTS 请求为零后，才可进行任何可能发声的 live 验收；原生 Study UI 的 OCR→讲解→追问→出题/评分→持久记录全链仍未验证。生成完整可移植补丁的最少外部条件是提供 LIVE/BRIDGE/goal-isolated 三份源码根的改动前快照或同版本 source archive。当前未 commit/push，也没有写入运行时 DB 或 reload。
