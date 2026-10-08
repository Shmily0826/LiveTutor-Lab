# LiveTutor 自主推进第二轮报告 — 多轮教学连续性修复（2026-10-09 夜）

> 自包含。读者不需要读过任何历史对话。
> 上一轮报告：`docs/neko-teaching-validation-2026-10-09.md`（把「单轮能教、连续是假象」定性为 CORE 缺口）。
> 本轮目标：把「连续互动学习」真正做出来，并用真实运行证明改善成立。
> 代码审查附录：`docs/neko-context-reuse-review-2026-10-09.md`（开源复用调研 + 上下文接线逐项审查）。

---

## 0. 一句话结论

**上一轮报告点出的两个最贵缺口——「追问无法复用上一轮材料」（A2/C1）与「出题与当前材料不匹配」（A4/B2）——本轮已修复并通过真实运行复测；会话总结（D2）也从「串味 + 失真」修到「正确区分两科并点名具体错因」。** 累计 6 个插件源文件改动（教学上下文 5 个 + OCR 捕获 1 个，+280/−12 与 +约 120 行），21 项回归（含新增 6 项）全绿，8/8 评分样本达标；另外量化了 Screen Grounding 的真实上限（§6）。**真实桌面 Study 面板** 的完整学习链路**未完成**，原因与缺口在 §7.1 明确列出。**本轮没有新建 Tutor Brain，没有改冻结二进制，没有 commit。**

---

## 1. 起始基线与最终工作树

| 项 | 起始 | 结束 |
|---|---|---|
| git HEAD | `ce79f63` | `ce79f63`（**未 commit / 未 push**） |
| 工作树改动 | 1 项（memory 日志） | 9 项（见 §9 清单；本轮的 docs / patches / scripts 均为新增） |
| 学习 DB | `interactions=45`、`qa_records=8`、`max_id=45` | `interactions=63`、`qa_records=16`、`max_id=68` |
| 历史记录完好性 | — | 关键行 `interactions 24/29/33` 仍在；`qa_records 1–5` 仍在（只读校验） |
| N.E.K.O | 未运行（上一会话结束后 hold 任务已消失） | 运行中（`neko_lab_hold.py` 43200s 常驻托管；48911/48915/48916 全部健康） |
| 插件运行时开关 | 关闭 | 关闭（已还原：`user_plugin_enabled=false`、`set_agent_enabled=false`） |
| 插件临时配置 | — | 已失效还原（`communication` 临时覆盖随插件进程结束而消失；`plugin.toml` 磁盘值从未改动） |

DB 起始值与上一轮报告结尾（45/8）**完全一致**，即本轮起点干净、没有继承未记录的改动。
`interactions` 是**滚动窗口**（`history_limit=50`，每 10 次插入裁剪一次）——`max_id 68` 而 `count 63` 就是裁剪痕迹；
被裁掉的是最早的行，`24/29/33` 等关键样本仍在。**完整学习历史不在 `interactions`，而在 `mastery_snapshots` / `wrong_questions` / `fsrs_cards` / `qa_records`**（本轮实测确认这些表未被裁剪）。

---

## 2. 本轮实际修复（6 个文件）

改动全部位于 `plugin/plugins/study_companion/`，并同步到三个根（LIVE / BRIDGE / goal-isolated），
脚本校验逐字节一致。（`entry_ocr_entries.py` 的 `capture_busy` 补丁是上一轮成果，本轮**未重复修复**。）

### 2.1 `llm_prompts.py` — 会话记忆注入（对应 A2/C1 根因）

- 新增 `build_concept_recent_context(context)`：把 `recent_interactions`（最近 4 条，input/输出各截断）、
  `last_captured_material`（`last_ocr_text`，1200 字符）、`current_practice_question`、
  `last_answer_evaluation`、`recent_learning_events` 组成一个**有界**（实测 ~1.0–3.5k 字符）的 JSON 块。
  只读取具名公开字段，私有字段（`vision_image_base64` 等）结构上不可能进入——新增回归测试断言了这点。
- `build_concept_explain_messages` 把它拼到 user message 的 `{recent_context}` 占位符上。
  **这是本轮唯一让 concept_explain 能看见会话历史的改动**（改前它只渲染 `{text}` + 可选知识图谱块）。
- 新增 `_summarize_context`：渲染前把 `history` 投影掉、改用 `session_history`（每行压缩为 kind/input/output），
  并给 summarize 单独设了行数与字符上限。
- 新增 `_summary_interaction_rows` / `_bounded_text` 等小工具。

### 2.2 `prompt_templates.py` — 提示契约与预算

- `STUDY_CONCEPT_RESPONSE_MODE_SYSTEM_PROMPT`：加入「引用解析」指令——
  当学生说「刚才那道例题」「上一步」「为什么有个 1/2」时，必须从 Recent study context 里解析引用**直接回答**，
  不得要求用户重新粘贴已经在那里的材料；并加了「跨学科只答当前学科」的约束。
- `STUDY_CONCEPT_RESPONSE_MODE_USER_TEMPLATE`：新增 `{recent_context}`。
- `STUDY_QUESTION_GENERATE_REQUIREMENTS` 13/14 条：把「谁决定主题」写成**优先级链**——
  (a) 有 `selected_topic_name/id` 时以自适应目标为主题；(b) 否则以用户材料（`source_text`/`text`，由 `topic_hint` 细化）为主题；
  并明确 `knowledge_question_params`/`knowledge_guidance`/`history`/`last_ocr_text` **只能影响难度与措辞，不得改变主题**。
  （改前第 13 条是误导性的「grounded in screen_classification」——那是屏幕分类，不是学习材料。）
- `STUDY_SUMMARIZE_SESSION_REQUIREMENTS` 7/8 条：以 `session_history` 为**唯一**本会话依据，
  `history` 只用于连续性理解，`screen_classification` 只当弱元数据。
- `STUDY_PROMPT_CONTEXT_MAX_TOKENS["summarize_session"]`：**2000 → 6000**。

### 2.3 `entry_tutor_context_support.py` — 服务端定序与会话作用域

- 知识图谱检索 query 优先级：`topic_hint` 提到 `source_text` 之前（改前用整篇材料当检索 query，命中噪声大）。
- 出题参数接地：当调用方**显式提供学习材料**（`source_text` ≥40 字符且来源不是 `targeted_question`）时，
  置 `material_grounded_question=True`；若 `topic_hint` 解析不到被追踪主题，则剪除
  `target_topic_id`/`target_topic`/`weak_topics`/`due_reviews`/`retry_wrong_question`/`candidate_evidence`
  ——让跨学科的旧弱项无法劫持本次出题主题。
- 会话边界：`recent_learning_events` 上限 16 → 64；summarize 时用事件时间戳求**本会话起点**，
  过滤出 `session_history`（这是 LangGraph「thread-scoped state」的最小可用替代，见审查附录 §1.2/§4）。
- 诊断字段透出：`material_grounded_question` 进入返回载荷。

### 2.4 `entry_tutor_explain_entries.py` — 可观测性

- 讲解载荷新增 `mode` / `active_mode` / `recent_context_chars`。
  改前载荷里**没有任何模式字段**，这正是上一轮报告把「教学模式生效」标为「检查与报告标记不一致」的原因——
  是**报告口径问题**而非产品缺陷；现在两者一致。

### 2.5 `entry_tutor_question_entries.py` — 自适应出题的目标可观测性

- 自适应路径里 `topic` 被强制改写成 `selected_topic_id`（为了让掌握度落到正确主题），
  导致模型自己判断的主题被静默覆盖。新增 `question_topic_label` 保留模型判断，
  于是「选了 A 主题却出了 B 主题的题」变成**可见**——改前实测确实不一致，改后一致（§3.4）。

### 2.6 `entry_ocr_entries.py` — 新增 `active_window` 捕获模式（Objective E，见 §6）

- 新增 `capture_mode="active_window"`：解析前台窗口 → 裁剪到主屏范围 → 优先走管道的 target 捕获，
  失败则退回**同一条 PIL 抓屏路径**并内存裁剪（因为打包运行时缺 `cv2`/`mss`/`pyautogui`，见 §6.1）。
- 新增 `_foreground_window_target()`：解析前台窗口 rect 并裁剪到主屏；遇 N.E.K.O 自身窗口 / 无标题 /
  最小化 / 完全在屏幕外时返回 None（避免把插件自己的 UI 当学习材料）。
- 新增可观测字段：`capture_target_title` / `active_window_capture_route` /
  `active_window_fallback_reason` / `active_window_capture_detail`，全部进入 `llm_result_fields`。
- 默认行为**不变**（`capture_mode` 默认仍是 `fullscreen`），是 opt-in 新模式。

---

## 3. 修复后真实复测（PLUGIN API 级，逐场景 PASS）

全部证据在 `benchmarks/raw/evidence/teach2-*.json`（16 份）。**证据级别：PLUGIN API**
（真实插件进程、真实 LLM、真实 SQLite；不是模拟，但**未经桌面产品 UI**——UI 状态见 §7.1）。

### 3.1 A2 连续追问 → **PASS**（改前 FAIL）

- 第一次 `study_explain_text(text=换元法材料)`，再抛一个**不带材料**的追问：
  「继续刚才的材料：例题 2 里为什么会多出一个系数 1/2？请只针对例题 2 解释。」
- 改前：泛谈幂函数积分公式 + 「如果方便的话，把例题 2 的具体式子发我」。
- 改后（`teach2-r1-followup.json`）：
  > 例题 2 是 ∫ x·e^(x²) dx。系数 1/2 来自换元时的"凑微分"：令 u = x²，则 du = 2x dx。……
  > x dx = (1/2) du …… (1/2)e^(x²) + C。……这也是它和例题 1（∫ 2x·cos(x²) dx，du 正好等于 2x dx，不用补系数）的区别。
- 6/6 检查通过：`fix_is_live`(recent_context_chars=3479) / `mentions_half` / `mentions_example2_math` /
  `names_example2` / `does_not_ask_to_paste` / `explains_du_half`。

### 3.2 C1 跨材料回溯 → **PASS**（改前 FAIL）

- asyncio 材料讲完后问：「回到之前的定积分换元材料：例题 1 的复合关系是什么？正确结果是什么？」
- 改后（`teach2-r2-crossmat.json`）：正确答出 `f(g(x))=cos(x²)`、`g(x)=x²`、`du=2x dx`、结果 `sin(x²)+C`，
  并给出举一反三 `∫2x·e^(x²)dx`。**无 asyncio 串味**（`no_asyncio_pollution=True`），**不要求重贴材料**。
- 同一场景用**真实 OCR 材料**再跑一次（`teach2-r6-ocr-followup.json`）：全屏 OCR 抓取屏幕上的 HTML 材料
  （5/5 关键标记命中，1097 字符），随后不带参数的讲解走 `last_ocr_text` 回退路径，追问同样答对。
  → 说明该修复在「材料来自真实屏幕」的主路径上也成立。

### 3.3 出题材料绑定 → **PASS**（改前 FAIL）

| 场景 | 改前 | 改后（`teach2-r3-binding.json`） |
|---|---|---|
| 换元法材料 出题 | 出 `y=(3x+1)^5` 求导（链式法则，跨学科） | 「在不定积分换元法中，设 u = g(x)，则 ∫f(g(x))g'(x)dx 等于什么？」 |
| asyncio 材料 + `topic="python asyncio"` 出题 | 仍是 `(3x+1)^5` 求导 | 「在 Python asyncio 中，为什么在协程里调用同步的 time.sleep 会阻塞整个事件循环？」 |

两项均 `has_positive_marker=True` / `has_negative_marker=False`。

### 3.4 自适应练习路径的绑定 → **PASS**（本轮新发现的独立缺陷，已修）

- `study_question_context` 选中 `derivative_chain_rule_application`（`selection_reason=due_review`，有明确理由，
  属「有说明地复习旧知识」，合规），但 `study_generate_targeted_question` **改前** 出的却是 asyncio 题
  （`teach2-r9-reuse-prerefix.json`）。
- 修后同一路径出：「对于 y = sin(3x)，根据链式法则求 dy/dx。」（`teach2-r9-reuse.json`），与选中主题一致。

### 3.5 学习状态被真正复用 → **PASS**

`teach2-r9-reuse.json` + 只读 DB：本轮写入的弱项/错题/FSRS 卡确实驱动了自适应选择——
`study_knowledge_map` 报 `weak_topic_count=5`、`wrong_question_count=10`，
`study_question_context` 选中的主题正是本轮评分样本写下的错题主题之一，且给出 `due_review` 理由与
`due/retrievability/stability/difficulty` 明细（FSRS 在跑）。

---

## 4. 评分样本：8 条（用户上限 6–8，本轮用满）

覆盖「同题正误 + 不同材料 + 知识点针对性反馈」。证据：`teach2-r3-binding.json`(1–3)、`teach2-r4-scoring.json`(4–8)。

| # | 题 | 作答 | 判定 | 反馈是否针对具体知识点 |
|---|---|---|---|---|
| 1 | 换元法则 | 「答案是 42」 | wrong / 0 | ✅ 指明「把换元结果当作一个具体数字」的误解 |
| 2 | 同上 | 正确 | correct / 100 | ✅ 仍指出「未显式写出 du = g'(x)dx」 |
| 3 | 同上 | 漏 `du` | partial / 70 | ✅ 精确指出「最终表达式缺少 du」 |
| 4 | asyncio 阻塞题 | 「和 asyncio.sleep 一样都会让出控制权」 | wrong / 0 | ✅ 「正好相反：time.sleep 是同步阻塞调用」 |
| 5 | 同上 | 正确 | correct | ✅ |
| 6 | ∫3x²cos(x³)dx | 完整正确 | correct | ✅ |
| 7 | 同上 | 漏回代（留 `sin(u)+C`） | partial / 80 | ✅ 「没有把 u 回代为 x³」+ 逐步 step_feedback |
| 8 | 为什么 `time.sleep` 卡住其它任务 | 「会启动新线程，线程切换拖慢循环」 | wrong / 20 | ✅ 逐条否定虚构机制并指出应改用 `await asyncio.sleep(3)` |

**第 7、8 条是关键**：学生错在具体知识点（漏回代 / 机制误解），反馈**没有停留在正误分类**，
而是点名错误机制并要求补上正确表述——满足「答案评估真正针对题目与具体错误」的验收项。

---

## 5. 学习状态可靠性（对应 Objective C）

| 检查项 | 结论 | 证据 |
|---|---|---|
| Mastery 是否按有效答题证据更新 | **是**。本轮新增/更新掌握度主题：`topic_edfeb0bc64`(不定积分换元法, n=4, m=0.341)、`python_asyncio`(n=2, m=0.205)、`college_indefinite_integral`(n=1, m=0.347)、`topic_2e11955e1b`(同步阻塞调用, n=1, m=0.0) | `mastery_snapshots`（只读） |
| 错题是否入库并可被利用 | **是**。`wrong_questions` 记录 `error_type`/`verdict`/`status`（`active`/`retrying`）、`retry_count`；本轮的 asyncio、换元法、同步阻塞三主题均落库 | `wrong_questions`、`teach2-r9-reuse.json` |
| FSRS 是否参与 | **是**。新增 4 张 `fsrs_cards`（rating 4/4/2/1），`due_reviews` 返回 retrievability/stability/difficulty | `fsrs_cards`、`teach2-r9-reuse.json` |
| Knowledge Graph 是否参与选择 | **是**。`study_knowledge_map`：200 主题 / 1620 边 / 5 弱项；自适应选择给出 `due_review` + 主题 id | `teach2-r9-reuse.json` |
| Session Summary 是否准确 | **是（修复后）**。改前把上一轮链式法则内容算作本轮学过；修后：「本轮覆盖两个学科：换元法积分与 Python asyncio」，并列出 3 条**具体**弱项（漏回代、误以为 time.sleep 起新线程、未说明不交回事件循环） | `teach2-r8-summary2.json` vs `teach2-r5-summary.json`、`teach2-r8-summary2-precompact.json` |
| 新材料与历史知识是否区分 | **是**。跨材料回溯不再串味；`material_grounded_question` 让「用户材料决定主题」显式化 | §3.2 / §3.3 |

**新发现的独立缺陷（本轮记录未实施）**：`qa_records.session_id` 实际写的是**单次 run_id**，
因此 `sessions` 表 16 行、每行 `question_count=1`、`ended_at` 恒为 NULL——「会话」粒度是错的。
这是本轮只能用时间戳推导会话边界的原因，也是 `interactions` 无法按会话过滤的根源。
方案（需授权，涉及数据语义 + 列迁移）见审查附录 §6.1。

---

## 6. Screen Grounding：新增 opt-in 能力 + 实测上限（Objective E）

> 结论先行：**窗口裁剪这一"低风险小改动"已经实现并跑通，但实测显示它对本场景只带来边际收益**——
> 因为真正污染学习材料的噪声在窗口**内部**（浏览器标签条/书签栏/地址栏、悬浮面板），
> 而消除它需要 DOM/UIA 文本提取或按应用调参，属于架构级改动，本轮只给出量化证据与方案。

### 6.1 先发现一个"已有能力在本构建里是死路"

管道的 target/区域捕获能力**早已存在**（`study_ocr_pipeline.capture_snapshot(target)` +
四个后端 + `StudyCaptureProfile` 裁剪比例），但本轮实测它**不可达**：

| 事实 | 证据 |
|---|---|
| `capture_backend="auto"` 只解析到 dxcam | `study_ocr_pipeline._resolve_capture_backend()` `else: DxcamCaptureBackend()` |
| dxcam 的 `grab(region=...)` 需要 `cv2` | 首次实测 `active_window_capture_detail = "No module named 'cv2'"` |
| 打包运行时**没有** `cv2` / `mss` / `pyautogui` | `resources/bin/` 目录实测：三者均 MISSING，只有 dxcam / PIL / numpy / win32gui |
| 全屏路径之所以能用 | `_capture_fullscreen()` 用的是 PIL `ImageGrab.grab()`，不需要上述依赖 |

即：**四个区域后端在本构建里全部不可用，只有 PIL 全屏可用**。awareness 路径同样走这条 target 通道，
但 `awareness.enabled=false`，所以这个死路一直没被暴露。

### 6.2 已实施的小改动

`active_window` 模式走"同一条能用的 PIL 路径"：一次 PIL 抓屏 → 按窗口 rect 缩放裁剪 →
应用与管道 target 路径**相同**的配置内缩比例 → 送 OCR。实测路由字段 `active_window_capture_route="pil_bbox_crop"`。

### 6.3 实测收益（同一屏、同一材料，`teach2-r10-grounding*.json`）

| 指标 | fullscreen | active_window | 判定 |
|---|---|---|---|
| 模式上报 | fullscreen | **active_window**（`capture_target_title` = 材料窗口标题） | 能力可用 |
| 材料标记保留 | 4/4 | **4/4**（NEKO-LAB 标记 / 换元 / 例题 / 易错） | 不丢内容 |
| 窗口外噪声 | 含 `All Bookmarks`、屏幕顶部的浏览器标签标题 | **已消除** | 收益真实但很小 |
| 窗口内噪声 | `NekoClaw` / `No active tasks` / 书签栏条目（`bilibili`/`扇贝`/`Vercel`） | **仍在** | 主要噪声无法用窗口裁剪去掉 |
| 文本量 | 950 字符 | 967–972 字符 | **几乎没有下降** |

### 6.4 为什么"裁剪到窗口"救不了这个场景

- 学习窗口（Chrome 最大化）几乎等于整屏，窗口裁剪只能去掉**窗口外**的少量内容。
- 书签栏、标签条、地址栏都在窗口**内部**；把窗口裁剪与"顶裁剪"组合起来才有可能去掉它们，
  而本机需要的比例约 **0.13**（≈900px 高度里的 110px）——这是**应用相关**的魔数，
  对 PDF/Word/编辑器窗口会直接切掉正文。
- 想用配置调整顶裁剪比例时又踩到第二个产品问题：**`config/hot-update` 对 `ocr_reader.*` 报成功但不生效**
  （`handler_called: false`；把 `top_ratio` 依次试成 0.06 / 0.13 / 0.4，OCR 文本完全相同），
  要改必须重启插件或改 `plugin.toml`。→ 该"按应用调参"的缓解手段当前**无法在运行时热调**。

### 6.5 方案（证据支持的建议，本轮未实施）

1. **首选仍是 DOM/CDP 与 UIA 文本提取**（与上一轮建议一致，本轮给了新的量化支持）：
   像素裁剪的天花板就在这里——窗口内噪声无法用几何手段去除。
   网页走 CDP `DOM.getDocument`/`Runtime.evaluate`，Windows 应用走 UI Automation，
   RapidOCR 保留为图片/扫描页兜底（本次实测全屏 OCR 耗时 8.1–22.9s，也是选它的另一理由）。
2. 若要短期缓解：给 `active_window` 增加"按目标进程选择内缩 profile"（浏览器 0.13、编辑器 0.03），
   并在 `plugin.toml` 侧提供 profile，而不是让用户手改比值。
3. 顺带修 `config/hot-update` 对 `ocr_reader` 不生效的问题（否则任何调参都不可验证）。

---

## 7. 证据分级：三类证据分别证明了什么

| 级别 | 本轮实际覆盖 | 说明 |
|---|---|---|
| **REAL UI** | **部分**。① 真实屏幕全屏 OCR 抓取到屏幕上渲染的 HTML 材料（5/5 标记，约 1100 字符）——这是产品自己的抓屏+OCR 管道；② 桌面角色窗口（"Carbon-Based Lifeform Terminal"）在 05:03:46/48、05:05:42 显示了由本轮学习数据驱动的消息（窗口截图 + 屏幕 OCR 文本双向确认） | **Study 面板内的完整学习链路未完成**，见 §7.1 |
| **PLUGIN API** | **完整**。§3 全部场景 + §4 全部 8 条评分样本 + §5 全部状态检查 + §6 的 grounding 对照，均在真实插件进程 / 真实 LLM / 真实 SQLite 上完成 | 不能替代 UI 验收 |
| **SIMULATED / SOURCE** | 21 项源码级回归（含新增 6 项）、正则/词表断言、只读 SQLite 查询、源码静态定位 | 仅作支撑 |

### 7.1 Study UI 链路缺口（明确未完成，不标 PASS）

**尝试过什么**：确认桌面存在 "Project N.E.K.O." 与 "Carbon-Based Lifeform Terminal" 两个可见窗口；
枚举了插件服务的全部 100+ 端点（含 `/plugin/{id}/ui/`、`/hosted-ui/*`、`/ui-info`）；
在打包资源里搜索插件 UI 宿主入口（`hosted-ui` / `plugin-manager` / `/plugin/`）。

**阻塞原因（按重要性）**：

1. **看不到 UI**：本会话内 GDI 全屏抓屏返回**全黑**（1440×900 全黑图，已删除临时文件）；
   Electron 的 `PrintWindow` 只能渲染出局部（主窗口仅渲染出 "NekoClaw Tasks" 面板，其余全黑）。
   → 除通过产品自己的 dxcam 管道外，我无法可靠观察 UI 状态。
2. **找不到 Study 面板入口**：桌面端未见学习面板的入口按钮（窗口 OCR 文本里没有任何插件/学习入口）；
   打包资源里找不到能定位到的插件 UI 宿主前端（`bin/frontend/plugin-manager/dist/...` 存在，
   但没有任何静态脚本或 asar 模块引用它，推测由 IPC 在运行时下发）。
3. **安全边界**：在**没有视觉反馈**的前提下对用户正在运行的真实桌面应用做盲点击，
   与本轮「不操作无关页面 / 桌面控制需可交还」的约束冲突，我选择不做。

**因此明确标注**：`Study 面板完整学习链路 = NOT COMPLETED（环境/工具阻塞）`，
而不是 PARTIAL PASS。**可执行的下一步**：见 §11 第 1 条（需要用户在场的 10 分钟）。

---

## 8. 合规与运维（如实记录，含一次真实偏差）

| 约束 | 状态 |
|---|---|
| 不 commit / 不 push | ✅ 遵守。HEAD 仍为 `ce79f63`，未执行任何 git 写操作 |
| 不删除/覆盖历史学习记录与初始 DB 备份 | ✅ 遵守。只读校验 `interactions 24/29/33`、`qa_records 1–5` 均在；未使用任何备份覆盖 |
| 保留新增测试学习记录 | ✅ 新增 18 条 interactions（含 5 条被滚动窗口裁掉）、8 条 qa_records，均在 |
| 评分样本 6–8 条 | ✅ **8 条**（用满上限，不再增加） |
| LLM 调用 ≤50 次 | ✅ 未超。**插件入口调用 25 次**，其中 `study_ocr_snapshot` 为本地 OCR（0 次模型调用）→ 22 次消耗模型的入口调用；concept_explain 每次附带 1 次语义路由（≤8 次），故**模型调用上限 ≈31 次**，评分样本占 8 次。§6 的 grounding 对照又跑了 7 次 OCR，均为**本地 0 次模型调用**，不计入模型预算。（脚本计数器把 OCR 也算作 "LLM entry"，此处按真实调用口径说明，不按脚本口径报数） |
| 夜间静音 | ⚠️ **出现真实偏差，已量化**：`token_usage.json` 记录本轮窗口（04:50–05:33）内 **51 次 `tts:free` + 36 次 `emotion` + 17 次 `proactive` 调用**。来源是「插件学习事件 → proactive bridge → 角色回复 → 应用自身 TTS」；另有启动时的角色问候（04:52）。**我没有启用麦克风、没有调整音量、没有主动开启语音**，但确实存在声学输出的可能。过程：05:11 用 `config/hot-update`(temporary) 关掉 `study_companion.communication` 后 TTS 立即停止（05:05:43 → 05:11 期间为 0）；但之后每次 `/plugin/.../reload` 重载插件（为加载新代码，共 4 次）都会**清掉这个内存级临时覆盖**，TTS 随之恢复（05:22–05:33 又 13 次）。最终关闭插件运行时开关后，TTS 停止（最后一条 05:32:58）；`plugin.toml` 磁盘值从未被改动。**教训：夜间做 Study 验证应在每次 reload 之后重新关闭 communication，或直接改 plugin.toml 临时关闭。** |
| 不读取/输出 API key | ✅ 遵守（仅看到后端日志里出现 `api.deepseek.com` 的主机名，未读取任何凭据） |
| 不操作无关应用 / 不绕过锁屏 | ✅ 全程未锁屏（`OpenInputDesktop` 句柄非 0，实测前台为 Chrome），未做盲点击；只在材料渲染、窗口聚焦、截图/OCR 上操作 |
| 重启前确认进程归属 | ✅ 新增 N.E.K.O 实例数 = 0。DB 起始值与上一轮结尾一致，证明没有继承未记录的进程状态；启动方式沿用已验证的 `neko_lab_hold.py`（唯一一次启动） |
| 桌面控制交还 | ✅ N.E.K.O 仍在运行且健康（48911 `/health` ok），hold 任务继续托管；未残留脚本化输入 |
| 临时开关恢复 | ✅ 插件运行时开关已还原（`user_plugin_enabled=false`）；`communication` 临时覆盖随插件进程结束消失，`plugin.toml` 磁盘值从未改动 |
| 不替换冻结二进制 / 不升级安装包 | ✅ 未触碰 |

**TTS 偏差的处置建议**：夜间做 Study 验证前，先把 `study_companion.communication.enabled` 置 false，
并在**每次插件 reload 之后重新施加**（临时覆盖不跨进程重启）。本轮已验证此法能在 0 成本下完全止住 TTS。

---

## 9. 关键文件与工作树清单

**新增**
- `docs/neko-context-reuse-review-2026-10-09.md`（开源复用调研 + 上下文接线审查）
- `docs/neko-teaching-round2-2026-10-09.md`（本文）
- `patches/neko-study-2026-10-09-round2/{round2-teaching-context.patch,_pre/*.py,README.md}`（本轮精确 diff + 改动前镜像）
- `scripts/neko_lab_teach_round2.py`（本轮复测脚本，证据写 `teach2-*.json`，不覆盖上一轮 `teach-*.json`）
- `scripts/neko_lab_round2_patch.py`（反向重建 → 生成 round-2 diff）
- `scripts/neko_lab_window_shot.py`（PrintWindow 抓窗；GDI 抓屏在本会话返回全黑时的替代）

**修改**
- `benchmarks/raw/neko-app/resources/bin/plugin/plugins/study_companion/` 下 6 个插件源文件（§2）
- 同步到 `benchmarks/raw/neko-app/resources/bin/plugins/study_companion/` 与 `benchmarks/raw/goal-isolated/study_companion/`
- `scripts/test_neko_lab_regressions.py`（15 → 21 项）
- `patches/neko-study-2026-10-08/study.patch`（重新生成，554→971 行，纳入本轮 `llm_prompts.py` 与 `entry_ocr_entries.py` 改动）+ 其 README

**证据**：`benchmarks/raw/evidence/teach2-*.json`（16 份，另有 2 份 grounding 对照留存为 `teach2-r10-grounding-top000.json` / `-top013.json`）。
未保留任何截图（临时 PNG 已删除），未写入任何凭据。

**补丁一致性**：`round2-teaching-context.patch` 已做**正向可应用性验证**——
`_pre/` 镜像先通过 `py_compile`，再 `patch -p1` 应用，结果与 LIVE 部署**逐字节一致**（5/5 MATCH）。
该 patch 覆盖除 `entry_ocr_entries.py` 外的 5 个文件；`entry_ocr_entries.py` 在 `study.patch` 的文件清单内，
由 `study.patch` 覆盖。两个 README 都写明了这个划分。

---

## 10. 相对上一轮的能力提升

| 维度 | 上一轮 | 本轮 |
|---|---|---|
| 多轮追问引用上一轮材料 | ❌ 要求用户重贴 | ✅ 直接答对，并能与相邻例题对比 |
| 跨材料回溯 | ❌ 「当前文本未包含例题 1」 | ✅ 准确回忆并给出完整解 |
| 出题与材料匹配 | ❌ 材料 asyncio → 出链式法则题 | ✅ 材料/主题/自适应目标三者一致 |
| 会话总结 | ❌ 串了上一轮内容 + 漏掉一半学科 | ✅ 两科都在，弱项具体 |
| 答案评估针对性 | ⚠️ 被出题跑题连带削弱 | ✅ 8/8 样本均点名具体知识点 |
| 自适应练习可观测性 | ❌ 主题被静默覆盖，无法发现不一致 | ✅ `question_topic_label` 暴露不一致 |
| 讲解模式可观测性 | ⚠️ 载荷无模式字段，报告口径不一致 | ✅ `mode`/`active_mode` 进入载荷 |
| 回归覆盖 | 15 项 | 21 项（新增会话记忆 / 预算 / 材料接地剪枝 / 会话作用域 / active_window 捕获） |
| 学习状态复用 | ⚠️ 能写不能证 | ✅ 弱项/错题/FSRS 驱动自适应选择，有据可查 |
| Screen Grounding | ⚠️ 全屏 OCR 噪声大、结论停留在建议 | ✅ 新增可用的 `active_window` 窗口裁剪模式；并量化出"窗口裁剪天花板"与"区域后端在本构建不可用"两个事实 |

**仍然存在**：真实 Study 面板链路未验收（§7.1）；`sessions` 会话粒度错误（见 §5 与审查附录 §6.1）；
语音/听感/打断仍未验收（本轮只做了静默前置检查，并发现 TTS 旁路）；无流式输出；
`capture_busy` 后端卡死 bug 未修（插件侧已规避，真实全屏路径不受影响）。

---

## 11. 仍需用户亲自参与的最少工作

1. **10 分钟**：在 N.E.K.O 里帮我指出/打开 Study 面板入口（或告诉我它的入口按钮位置）。
   拿到入口后我可以在无人值守下补完 §7.1 的 UI 链路验收。
2. **5 分钟**：确认「学习会话」的定义（插件运行期 = 一个会话？还是显式开始/结束？），
   以便实施 §5 / 审查附录 §6.1 的 `session_id` 贯通修复。
3. **可选**：真实麦克风/TTS 听感/打断验收（需在场且有声音环境）。

## 12. 下一轮最值得推进的方向（按价值排序）

1. **真实 Study 面板链路验收**（依赖 §11 第 1 条；自动化前置条件已就绪：桌面在跑、OCR 管道可用）。
   这是唯一一个"产品级"证据缺口。
2. **会话粒度修正 + `interactions` 会话化**（把 `session_history` 从时间戳启发式升级为精确查询；
   顺带修 `qa_records.session_id` = run_id 的错误）。这是让「按会话」能力能工作的前置条件。
3. **Screen Grounding：DOM/CDP + UIA 文本通道**（§6.5）。本轮已量化证明像素裁剪的天花板，
   并发现区域捕获后端在本构建不可用——这条路线的收益现在是**被测量出来的**，不是推测。
   低风险第一步：给 `active_window` 增加"按目标进程选择内缩 profile"（浏览器 ~0.13），并在 `plugin.toml` 侧配置化。
4. **修 `config/hot-update` 对 `ocr_reader.*` 不生效**（`handler_called: false`）——否则任何 OCR 参数都无法在运行时验证。
5. **L2/L3 记忆的可审计化**（参考 DeepTutor）：把 `session_summary_seed` 落成 per-surface 摘要文档，
   让「AI 为什么这样判断」可回溯到具体交互。
6. **TTS 旁路的静默开关**（产品侧）：夜间/专注模式下抑制 proactive 投递，避免学习事件触发发声。
