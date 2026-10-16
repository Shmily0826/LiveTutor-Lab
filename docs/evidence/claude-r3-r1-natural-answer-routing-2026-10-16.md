# R1：出题后的自然作答进入评分（离线完成，Native 未验）

> **补验（Native/真实模型）已完成，见 [claude-r3-native-verification](claude-r3-native-verification-2026-10-16.md)：按类 6/6、按场 6/8；下面“Native 未验”“没做”的表述是补验前的状态。**

**证据层级：离线（含真实 wrapper + SQLite + 假评分模型）。没有真实模型调用、没有 Native 场、没有麦克风。** 额度栏位启动时为空，按合同整轮只做离线工作。

## 改了什么
- 新增 `payload/study_companion/study_answer_routing.py`：纯函数 `classify_pending_turn(text)` → `answer / material_correction / other`，`has_pending_question(held)`（有 question_id/attempt_id、`attempt_evaluated is False`、没有评分中/占用）。
- `study_explain_tool` 开头（`material_source != literal_text`）：存在未评分待答题且本句分类为 `answer` 时，**直接转交 `study_answer_tool(answer=<原句>)`**，结果带 `routed_from=study_explain`；`study_answer_tool` 自己仍在锁内复核待答题身份。选的是“直接转交”而不是“返回让角色改调”：后者就是上一轮已证明无效的“靠模型听话”，前者可测、确定。
- 规则：明确的材料纠错（你读错/看错、重新看、再看一遍、图换了、I changed the picture…）→ 走原重读路径；提问/请求/控制语（吗、什么、为什么、请…、再讲、出下一题、等一下…）→ 走原路径；其余陈述、否定、含糊、裸“是/不是”、含标识符的断言 → 作答。
- 识别器输出的汉字间空格（“这 张 图”）被折叠后再分类。
- 语料：`scripts/natural_answer_corpus.json`（**人工拟写**，16 句作答 + 4 句材料纠错负例 + 6 句提问/请求/控制语）。

## 证据（离线）
| 项 | 结果 |
|---|---|
| 语料分类 | 26/26 与期望一致（含汉字间加空格的全部变体） |
| 16 句作答经真实 `study_explain_tool` | 每句恰好 1 次评分调用、QA 记录 +1、`attempt_evaluated=True`、未调用教师 |
| 4 句材料纠错 + 6 句提问等 | 评分调用 0 次，QA 0，待答题仍为未评分 |
| 无待答题 / 已评分 / literal_text | 不转交 |
| 重复同句 | 第二次不再评分（已评分状态） |
| 评分模型抛错 | 不落库、不返回成绩 |
| 回归 | 新模块 13 项；相邻 14 个模块（answer_*、explanation_language、source_*、teaching_failures 等）全过；全量 116 模块仅原 7 个历史失败 |

## 必须说明的限制
- **语料和规则出自同一作者**，26/26 只说明规则自洽，不是独立的泛化率。真实 ASR 文本、模型转述后的 `question` 字段与语料可能不同。
- **Native 每类 ≥1 场的验证没做**（无额度）。通过标准里“≥80% 进入评分并落库”在 Native 层**未验证**。
- 规则偏保守：带问号词（吗/什么/哪）的试探性作答（“是 NUD 吗？”）归为提问，不评分；“好”“嗯”类确认不是作答。
- 待答题是旧课程恢复来的，用户随后发的任何陈述句也会被当作答；这是合同定义的规则。
- 回退：删除 `study_explain_tool` 开头的转交块即可，别处不依赖。
