# 复用调研 + 上下文接线审查（2026-10-09 夜）

> 任务来源：用户要求先调研 `HKUDS/DeepTutor` 等成熟开源实现，并判断哪些能力在 Study Companion 中
> 已经存在、只是接线错误；哪些确实缺失；优先修复已有上下文传递链路而不是重建。
>
> 方法：读参考实现的公开架构说明 → 对 Study Companion 现有代码逐项定位 → 用本轮真实运行结果**逐条证伪或证实**。
> 所有 Study Companion 结论都带代码位置 + 本轮运行证据，不靠推断。

---

## 1. 参考实现的真实机制（不是泛泛而谈）

### 1.1 DeepTutor（HKUDS，Apache-2.0）

| 机制 | 其做法 | 来源 |
|---|---|---|
| 单一运行环路 | Chat / Quiz / Solve / Research / Visualize / Course Study / Mastery Path **共用同一个 agent loop 与 session context**，切换模式不重置上下文 | v1.4.5 release notes；docs「Eight surfaces, one running context」 |
| loop-plugin 框架 | `deeptutor/loop_plugins/`：一个功能向某个 turn 贡献**工具 + 一段 system prompt 块 + 服务端持有的工具参数**，聊天管线里不硬编码 | v1.4.5 release notes |
| 上下文检查点折叠 | 「a tool can collapse a long working context back to a checkpoint plus a summary mid-turn」 | 同上 |
| 掌握度闸门 | 期望答案随题目一起**存在服务端**，「never round-trips through the model」，然后进入间隔复习 | 同上 |
| 三层可审计记忆 | L1 工作区镜像（LIVE，`snapshot/<surface>/`）/ L2 每 surface 摘要（`L2/<surface>.md`，引用 L1 实体）/ L3 跨 surface 综合（`L3/profile\|recent\|scope\|preferences.md`）+ Memory Graph 展示 L3→L2→L1 引用 | docs「Memory」 |
| 追踪森林 | 互动轨迹沉淀为多分辨率图谱 → 动态虚拟学生画像；每个教学结论可回溯到文本证据或错题记录 | 官方发布说明 |

### 1.2 LangGraph 记忆模式（作为「机制命名」参考）

- **短期记忆 = thread-scoped state，由 checkpointer 按 `thread_id` 持久化**；调用开始时读回，每步后快照。
- **长期记忆 = `BaseStore` + `namespaces`**（`store.put/get/search`），跨 thread 存活。
- 两者组合方式：**turn 开始时把长期记忆召回进短期记忆；thread 结束前把短期观察蒸馏回长期记忆**。
- 长上下文管理三件套：`trim_messages`（按 token 预算裁剪副本）/ 滚动摘要（把旧半段压成一条 system message）/ 选择性字段（消息保持短，长寿事实放独立 state key）。
- 明确警告：*「把两种概念混进一张临时表，是 'phantom memory'（幽灵记忆）bug 最常见的成因——上一个会话的信息泄漏进另一个会话，因为 `thread_id` 被复用。」*

> 这条警告与本轮实测到的**会话总结串味**完全同型（见 §3.4），属于同类结构性缺陷，不是我方独有。

---

## 2. Study Companion 的对应机制（改前状态）

| 设计意图 | Study Companion 中的对应物 | 代码位置 |
|---|---|---|
| thread state（短期） | 插件进程内 state：`recent_learning_events`、`session_summary_seed`、`current_question`、`last_answer_evaluation`、`last_ocr_text`、`active_mode` | `entry_tutor_context_support.py` `_record_tutor_result` / `_build_learning_context` |
| checkpointer | state 落盘（`_persist_state`）+ DB `sessions` 表 | 同上 / `store.py` |
| Store + namespace（长期） | `interactions`、`mastery_snapshots`、`wrong_questions`、`fsrs_cards`、`qa_records`、`topics`(824) + 知识图谱边 | `store.py`、`knowledge_tracker.py` |
| 每 turn 注入上下文 | `_build_learning_context(operation, ...)` | `entry_tutor_context_support.py:567+`（改前行号） |
| token 预算 / 裁剪 | `_context_json_for_prompt` + `_compact_prompt_value` + `STUDY_PROMPT_CONTEXT_MAX_TOKENS` | `llm_prompts.py`、`prompt_templates.py` |
| loop-plugin 式的「贡献 prompt 块」 | `knowledge_guidance` 块拼进 concept_explain 的 user message | `llm_prompts.build_concept_explain_messages` |
| 服务端持有参数 | `knowledge_question_params`（服务端算好，模型只读） | `entry_tutor_context_support.py` |
| 答案不外泄 | `internal_private_payload` + `_PROMPT_PRIVATE_FIELDS` + `answer_evaluate` 的必需字段保护 | `llm_prompts.py`、`entry_tutor_question_entries.py` |
| 证据可回溯 | 知识图谱边、`candidate_evidence`、`qa_records`、`_record_answer_knowledge` 把掌握度写回题目 | `knowledge_tracker.py` |

**判断：DeepTutor 缺的那几样能力，Study Companion 基本都已经存在**（掌握度闸门、答案隔离、间隔复习、
知识图谱、可回溯证据）。缺的是**接线**，不是能力。

---

## 3. 关键点：三个教学入口**不是同一个 bug**（逐条用本轮实测定案）

这是本次审查最重要的产出。此前「教学 prompt 不消费 history」是笼统说法，实测后必须拆开：

| 入口 | 上下文注入方式 | 改前是否消费会话/材料 | 改前实测 | 改后实测 |
|---|---|---|---|---|
| **concept_explain** | user message 只渲染 `{text}` + 可选 `knowledge_guidance` 块 | **完全不消费**：`history`/`last_ocr_text`/`current_question` 一个都没进 prompt | 「为什么例题 2 有 1/2」→ 泛谈幂函数公式并要求「把例题 2 发我」（A2 FAIL） | 直接答出 `u=x²`、`x dx=(1/2)du`，并与例题 1 对比（A2 PASS） |
| **question_generate** | `_build_structured_messages` 会渲染整个 allowed context JSON | **消费了，但优先级颠倒**：tracker 的自适应信号（`weak_topics`）盖过用户材料 | asyncio 材料 → 出 `(3x+1)^5` 链式法则题（B2 FAIL） | asyncio 材料 → 出事件循环/`time.sleep` 阻塞题；换元材料 → 出换元题（PASS） |
| **answer_evaluate** | 同上，且有必需字段保护（`question`/`answer`/`expected_answer` 超预算直接 `raise`，不从截断前缀判分） | **消费且正确**，是本轮唯一本来就健康的链路 | 8 条样本判分与反馈具体、知识点针对 | 保持 PASS，未因本轮改动回归 |
| **summarize_session** | 同上 | **消费了，但被两件事压垮**：`summarize_session` 预算只有 **2000 token**，且 `history` 是**跨会话的 50 行滚动窗口** | 把上一轮的链式法则内容当成本轮学过（D2 FAIL），且报「可用交互有限」 | 正确总结两科（换元法 + asyncio）与具体错因，不再引用旧会话内容（PASS） |

结论：**「三个入口有不同根因」已被实测坐实**。同一条「注入历史」的修法只能救 concept_explain；
question_generate 要改优先级、summarize 要改预算与作用域。把它们当成一个 bug 修会修错。

---

## 4. 改前确实存在的「已具备但接线错」清单

1. **会话记忆没有随请求走**（concept_explain 不读 thread state）→ 已修：`build_concept_recent_context` 注入有界会话块，
   并由 `recent_context_chars` 可观测（实测 3479 / 3466 / 3502 字符）。
2. **自适应信号与用户材料争主题**（question_generate）→ 已修：requirements 13/14 定优先级链（自适应目标 > 用户材料 > 其它提示），
   并对显式材料场景剪除跨学科 `weak_topics`/`due_reviews`/`retry_wrong_question`/`candidate_evidence`（`material_grounded_question` 标记）。
3. **知识图谱检索 query 用整篇材料而非显式主题**（`_build_knowledge_guidance_context`）→ 已修：`topic_hint` 优先于 `source_text`。
4. **会话总结的 token 预算与作用域**→ 已修：预算 2000→6000；用 `recent_learning_events` 的时间戳推导**本会话边界**，
   生成 `session_history` 并在渲染前把 `history` 投影掉（LangGraph 的「同一张表混两级记忆 = 幽灵记忆」正是此病）。
5. **自适应出题的目标标签不可见**：`topic` 被强制改写成 `selected_topic_id`，模型自己判断的主题被覆盖，
   于是「选了链式法则却出了 asyncio 题」无人可见 → 已修：新增 `question_topic_label`，改前实测确实不一致，改后一致。

---

## 5. 确实缺失（本轮**没有**建）

1. **单一运行环路**：Study Companion 是「若干独立 operation + 各自手搓 context」，没有 DeepTutor 那种
   一个 loop + 由插件贡献 context 块的接缝。本轮**复用了已有的 `_build_learning_context` 作为接缝**并扩展它，
   没有新建 Tutor Brain / Teaching State Machine。
2. **L2 每 surface 摘要文档 + Memory Graph**：Study Companion 有 `session_summary_seed`（内存版 ≈ L2）
   与 `sessions` 表，但没有按 surface 落盘的 L2 文档，也没有引用图。
3. **上下文检查点折叠**：没有 mid-turn 折叠。
4. **`interactions` 没有 session_id**（见 §6.1）——这是本轮用时间戳推导会话边界的**代偿原因**。
5. Task Board、多引擎 RAG、多 surface 共享工作区：与非目标无关，不在本轮范围。

---

## 6. 本轮新发现的独立缺陷（有证据，未在本轮实施）

### 6.1 「会话」粒度是错的：`qa_records.session_id` 实际存的是**单次 run_id**

- 代码：`entry_tutor_context_support._record_answer_knowledge` 取
  `context.get("session_id") or context.get("run_id") or state.run_id or "default"`；
  `entry_tutor_answer_entries` 传入的 `session_id` 来自 kwargs，恒为空 → 落到 `run_id`。
- 实测：`sessions` 表 16 行，每行 `question_count=1`、`topics_touched` 只有一个主题、`ended_at` 恒为 NULL
  （证据见主报告 §5 的 DB 快照）。
- 影响：任何「按会话」的能力（会话笔记导出、会话时长、按会话的回放/复习）都拿不到真实粒度；
  也是 `interactions` 无法按会话过滤的根源。
- 建议（**需用户授权，涉及数据语义**）：把「学习会话」定义为插件运行期内一段连续学习活动，
  在 state 里维护 `study_session_id`（进程启动时生成 / 显式 `start_session` 时轮换），
  同时写入 `interactions`（需加列）与 `qa_records`。这样 `session_history` 就是精确查询而非时间戳启发式。
  本轮不改：改动数据语义 + 需要列迁移，属于「重大改造只提方案」的范围。

### 6.2 语音旁路：学习事件会经角色的 proactive 通道触发 TTS

- 实测：本轮窗口（04:50–05:33）内 `token_usage.json` 记录 **51 次 `tts:free`**（另 36 次 `emotion`、17 次 `proactive`），
  桌面角色窗口（"Carbon-Based Lifeform Terminal"）在 05:03:46 / 05:03:48 / 05:05:42 显示了由学习数据驱动的消息。
- 05:11:20 我把 `study_companion.communication.enabled` 临时置为 false 后，**TTS 计数立即停止增长**（最后一条停在 05:05:43）；
  但之后每次 `/plugin/{id}/reload`（为加载新代码，共 4 次）都会清掉这个内存级临时覆盖，TTS 随之恢复（05:22–05:33 再 13 次），
  直到最终关闭插件运行时开关才彻底停止（最后 05:32:58）。`plugin.toml` 磁盘值从未改动。
- 判断：这是「插件事件 → proactive bridge → 角色回复 → TTS」的正常产品链路，不是缺陷；
  但对「夜间静音」约束来说是一次真实偏差，必须记录（见主报告 §7 的合规说明）。

---

## 7. Adopt → Adapt → Build 决策

| 决策 | 对象 | 理由 |
|---|---|---|
| **Adopt** | 会话块注入、token 预算裁剪、`trim/summarize/selective keys` 三个思路、thread-scoped state 概念 | 都是已有代码里的机制，直接改参数与作用域即可 |
| **Adapt** | `_build_learning_context`（当作 loop-plugin 的「贡献 context」接缝来用）、`_context_json_for_prompt`（改预算与投影）、`recent_learning_events`（提升为会话边界的权威来源） | 用现成接缝，改动面小、可回归 |
| **Build（拒绝）** | Tutor Brain、Teaching State Machine、独立向量记忆、通用 Agent Framework | 审查显示缺陷是 wiring；DeepTutor 的架构优势在本轮缺口上不提供额外能力，重建会丢掉 4000+ 行已验证的判分/掌握度/FSRS/复习/模式能力 |
| **Defer（需授权）** | 真实 `session_id` 贯通（含 `interactions` 加列）、L2 per-surface 摘要 + 引用图、mid-turn context folding | 数据语义/架构级，按用户「重大架构改造只提证据与方案」的要求不实施 |

## 8. 复用调研的净收益

1. 拿到「三类入口不同根因」的**独立结构性解释**（不是补丁式猜测）。
2. LangGraph 的 phantom-memory 警告**印证**了会话总结串味属于结构性缺陷而非模型偶发——使修复方向从「换提示词」变成「补会话作用域」。
3. DeepTutor 的 loop-plugin / server-owned args 说明「材料与自适应信号谁优先」必须由**服务端定序**，
   不能交给模型自行权衡——这正是 requirements 13/14 的写法依据。
4. 明确列出**不建**的部分，避免把项目扩成通用框架。
