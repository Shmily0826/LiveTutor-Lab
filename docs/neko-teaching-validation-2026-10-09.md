# N.E.K.O + Study Companion 真实教学体验验证报告（2026-10-09 夜间）

> 目标：判断 N.E.K.O + Study Companion 能否成为真正可用的 LiveTutor 底座。
> 方法：以代表性材料（数学换元法 + Python asyncio，非预设样例）走完整教学回路，
> 覆盖内容理解 / 多轮上下文 / 错误纠正 / 出题判分 / 学习状态复用 / 上下文污染六个维度。
> **证据级别标记**：[UI+OCR]=真实桌面屏幕捕获链路；[API]=插件 entry 调用（同一插件进程、同一 TutorLLMAgent、同一 DB）；[DB]=只读 SQLite；[SRC]=源码静态分析。
> 全部原始证据：`benchmarks/raw/evidence/teach-*.json`（14 份）。

---

## 1. 一句话结论

**能用来带学的骨架已经真实存在且单轮质量高，但"连续互动"是假象——跨轮上下文断裂是当前最大的 CORE 级缺口**。出题/判分/学习状态/模式切换全部真实可用；只要补上"把最近学习历史注入教学 prompt"这一个 PLUGIN 级修复点，教学体验会有台阶式提升。**建议：继续 N.E.K.O 底座 + 小幅扩展，不保留独立原 LiveTutor 底座。**

## 2. 带学能力逐场景判定

### PASS（8 项）

| 场景 | 结果 | 证据级别 | 证据 |
|---|---|---|---|
| 屏幕内容理解忠实度 | 材料渲染前台→全屏 OCR（10-16s）抓到标记/定义/两道例题/易错警示全部关键内容；解释完全忠于材料（sin(x²)+C、½系数、∫x·cosx 需分部积分全对） | [UI+OCR] | teach-ocr.json, teach-phase-a.json (A1) |
| 概念解释质量 | 换元法解释结构完整、准确、有教学语气（"凑微分时系数要除回去，这是最容易丢分的地方"） | [API] | teach-phase-a.json |
| 错误暴露→纠正 | 学生演示"令 u=x 换元 ∫x·cosx dx"的错误：明确否定 + 指出恒等换元无意义 + 给出分部积分正确解 x·sin(x)+cos(x)+C | [API] | teach-phase-a.json (A3，三项检查全中) |
| 错答判分 | "答案是 42" → verdict=wrong, score=0，反馈具体，next_action 给出复习方向 | [API] | teach-phase-a2-scoring.json (A5) |
| 对答判分 | 提供标准换元题 ∫3x²cos(x³)dx + 完整推导 → verdict=correct, score 高分 | [API] | 同上 (A6) |
| 教学模式 | set_mode(teaching) 生效；回复为分步教学并以检查题收尾（∫₀²x(x²+1)³dx 换限小测）；已还原 companion | [API] | teach-phase-c.json (C2) |
| 编程材料解释 | asyncio 事件循环/协程/gather/阻塞陷阱解释全部正确 | [API] | teach-phase-b.json (B1) |
| 学习状态持久化 | interactions 33→45、qa_records 5→8，mastery/主题记录真实入库，只增不减 | [DB] | teach-phase-d.json, teach-restore.json |

### FAIL / 缺口（4 项）

| 场景 | 结果 | 级别 | 证据 |
|---|---|---|---|
| **多轮追问上下文** | 追问"例题 2 为什么有½"，回复泛谈幂函数公式并要求"把例题 2 发我"——上轮 OCR 材料/解释完全丢失 | **CORE GAP** | teach-phase-a.json (A2) |
| **跨材料回溯** | asyncio 之后问"回到定积分材料例题 1"，回复承认"当前学习文本中未包含例题 1"（好消息：无学科串味，no_asyncio_pollution=True） | 同上（同根因） | teach-phase-c.json (C1) |
| **出题主题绑定** | 换元法材料出了链式法则题；asyncio 材料 + topic="python asyncio" 仍出 (3x+1)^5 求导题——知识图谱无 asyncio 种子时回退 weak_topics，输入材料/topic_hint 权重不足 | PLUGIN | teach-phase-a.json (A4), teach-phase-b.json (B2), [SRC] entry_tutor_question_entries.py:461+ |
| **会话总结失真** | summarize 输出"会话聚焦 calculus/differentiation（5x^4 外层因子）"——既不是换元法也不是 asyncio，还把屏幕分类当学习内容 | PLUGIN | teach-phase-d.json |

另：B3 判分 verdict=wrong 但理由是"答非所问"（因 B2 出题跑题），未指出 time.sleep 阻塞事件循环——判分机制本身正常，但被出题跑题连带削弱教学价值。

## 3. CONFIG / PLUGIN / CORE GAP 分类

- **CONFIG 可解决**（改配置即好，无需改码）：
  - 视觉模型通道（llm_vision_enabled=false）可开——但成本高，非必需（见 §5）。
  - 出题主题跑题的部分场景：先 `study_set_practice_scope` 限定主题范围再出题（插件已有此机制，今晚未启用）。
- **PLUGIN 级可修**（改插件源码，改动面小、收益大）：
  1. **教学 prompt 注入最近历史**：`_build_learning_context` 已收集 `history`(5-12条)/`last_ocr_text`/`current_question`，但 **concept_explain / question_generate / evaluate_answer 的 prompt 组装不消费这些字段**（只有 summarize_session 用）[SRC: entry_tutor_context_support.py:567-602, tutor_llm_agent.py 无 history 引用]。这是 A2/C1/A4/B2/D2 四个缺口的共同根源。修法：prompt 组装时注入最近 N 条交互摘要 + last_ocr_text 截断文本。
  2. 出题 topic_hint 权重：材料/topic_hint 应优先于 weak_topics 回退（或至少并行提示）。
  3. session summary 的 history 消费已有，但需要把当晚 explain 类交互纳入摘要权重。
  4. knowledge_guidance 返回空（需查参数契约，小问题）。
- **CORE GAP**（冻结后端/宿主层面，插件侧无法修复）：
  - `capture_busy` 标志卡死 + "409 仍弹遮罩"（Stage 2 已定性，未修；今晚 fullscreen 路径绕开，无实际影响）。
  - 无流式输出（TutorLLMAgent 是 ainvoke 一次性返回）——影响长解释的等待体验，非阻断。
  - 插件进程无法注册 ExternalRoute 抢占主聊天轮——若将来要"教学对话完全接管角色"，需要宿主小改；当前 Study UI 独立面板模式下不需要。

## 4. 今晚修复与真实运行证据

1. **study.patch 已修正**（patches/neko-study-2026-10-08/study.patch）：旧版缺 `capture_busy` 白名单。重建官方基线（反向应用法）→ 生成 entry_ocr_entries.py 新 diff 段（39→49 行）→ **正向应用验证与 LIVE 部署文件逐字节一致**。回归 15/15 OK。三个导入根 diff 校验一致。
2. **教学验证基础设施**：`scripts/neko_lab_teach_night.py`（9 个 phase：snapshot/prepare/ocr/phase-a/a2/b/c/d/restore），材料 2 份（benchmarks/materials/study-substitution-20261009.html、study-asyncio-20261009.md）。
3. **N.E.K.O 冷启动→完整教学会话**：02:06 hold 任务拉起四端口 → 02:22-02:45 完成 8 场景验证 → 开关还原 → DB 只增不减。LLM 调用 14 次（限 50），评分样本 3 条（限 6-8）。
4. **长稳观察（38 分钟窗）**：后端 RSS 稳定（777MB/533MB 双进程，零增长）；渲染进程 901→930MB（+30MB/10min，桌宠持续渲染 CPU ~60% 单核，属特性非泄漏）；无 run 积压、无重复消息、无状态失真（DB 计数全程一致）。

## 5. Screen Context 路线评估（OCR 局限实测）

今晚实测暴露的 OCR 通道真实限制 [UI+OCR]：
1. **视口外不可见**：材料折线下半页（例题 2/警示）首次 OCR 完全缺失，需人工缩放/单屏适配才能采全。
2. **噪声混入**：Chrome 书签栏、N.E.K.O 桌宠对话浮层、任务栏时间全部进入 OCR 文本（570 字符里噪声约占 1/3）。
3. **延迟**：全屏捕获+RapidOCR 10-16s，不支撑"实时感"。
4. 浮层干扰是双向的：桌宠 UI 会遮挡并污染教学材料画面。

**最小改动推荐**（今晚不实现）：
- **首选：Windows UIA 文本提取作为主通道**——对浏览器/VSCode/PDF 阅读器等学习场景可直接拿到结构化文本（零噪声、亚秒级、视口无关），OCR 降为兜底（图片/PDF 扫描页）。插件已有 `screen_classification` 的窗口标题通道，UIA 是其自然延伸。
- 次选（纯 CONFIG 级缓解）：OCR 提交前按目标窗口 rect 裁剪（插件进程内可做），或教学时引导用户最大化学习窗口。
- **VLM（视觉模型）暂缓**：对纯文本类学习材料无增益（UIA/OCR 已够），仅在图表/几何图/手写公式场景有真实价值，且当前 llm_vision_enabled=false、成本高。

## 6. Study Companion 能否承担 Tutor Brain 大部分功能？

**能，且证据充分**（与 docs/neko-study-companion-audit.md 的静态审计结论互相印证，今晚补齐了动态运行证据）：
- 已真实工作：结构化出题、判分+反馈+next_action、掌握度/错题/FSRS 持久化、模式系统、OCR 输入、（静态审计确认的）复习调度/记忆卡/番茄钟/文档分析。
- 单轮教学质量高：解释、纠错、反馈的具体性和准确性今晚全部达标。
- **不够的部分**（审计"STILL MISSING"今晚全部实测坐实）：连续对话状态（prompt 不消费历史）、Socratic 多轮控制、新材料即时出题绑定、校准的掌握度估计。
- 判断：这些缺口全部位于**插件 prompt/上下文组装层**，不触及 N.E.K.O 宿主核心。**不需要新建 Tutor Brain**。

## 7. 底座选型建议

| 选项 | 判定 |
|---|---|
| 继续 N.E.K.O + 小幅扩展 | **✅ 推荐**。核心回路已验证可用；缺口集中且 PLUGIN 级可修；省下全部已验证资产（判分/状态/复习/模式/语音/桌宠）。 |
| 保留原 LiveTutor 独立底座 | ❌ 不值得。需要重造出题/判分/掌握度/复习调度/语音全部已验证能力，投入远超收益。 |
| 外挂独立 Tutor Brain 服务 | ❌ 当前无必要。缺口不是"策略/状态机"级别，是"prompt 没读历史"级别。 |

## 8. 运维状态（截至 02:45）

- N.E.K.O 运行中，本会话 hold 任务（12h）托管，重启配方已验证。
- 插件运行时开关已还原（user_plugin_enabled=false, plugins=0）；模式已还原 companion。
- DB：interactions=45（+12）、qa_records=8（+3，全部为今晚评分样本），历史记录未动。
- 夜间全程静音（无麦克风/无发声/未动音量）；未 commit/push；工作树改动相对基线 dcbf479。
- 屏幕上的材料 A Chrome 窗口为验证遗留，可关闭。

## 9. 明日建议（按价值排序）

1. **修教学 prompt 历史注入**（PLUGIN，约 1-2 处改动）→ 用同样场景复测 A2/C1/A4——这是"能不能连续带学"的分水岭。
2. practice_scope + topic_hint 出题绑定复测（CONFIG+PLUGIN 混合）。
3. UIA 文本通道 PoC（半天级）：拿"当前窗口文本"替代一次 OCR，对比噪声/延迟。
4. 用户在场时：真实语音链路验收（今晚保持静默）。
5. Stage 3 评分样本（6-8 上限）今晚已用 3 条，剩余额度留给修复后复测。
