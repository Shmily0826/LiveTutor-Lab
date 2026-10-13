# 总结重启接续：quality18 真实失败与离线修复

本轮先完整承接 contract、plan、status、blockers。旧文件中的 577/56/0 和 no-online 快照由 Main 新任务及 quality18 终态覆盖：580/2000 DeepSeek、Lanlan.app 56/null、tech0/0，沿用 bargein-autocheck-20261012；exec46812 已 terminal。本轮不启动宿主、SDK、模型、音频、外部调用或子 Agent，不改账本。

## 已发生的失败

`benchmarks/raw/evidence/daily-companion-20261014-summary-source-quality18.json` finalized=true，scope 明确为真实 Study SDK/backend 和既有 SQLite 历史，没有 Native/device/human 证明；audio_session、room_microphone、native_window 均 false。

第一次真实 `study_summarize_session` 请求“用两句话回顾上一轮题目、我的错答与正确方向，以及下一步。不出新题”。结果非 degraded，却称本次缺少可核对题目/错答，要求补全上一轮题与错答。checks 中 previous_interactions_unchanged、previous_grades_unchanged、same_course、two_real_backend_results 均 true；这些完整性检查通过不能算接续语义通过。第二次源码纠正结果与本次总结接续修复不同，不能替代总结验收。

原 snapshot 有 27 条 interaction 和 2 条 QA；最近 8 行 ID20–27 中，ID25 是实际题目，ID26 是实际 answer_evaluate（wrong/10，有已有 next_action），ID27 是旧老师总结。重启后新 session 无互动；材料/题/QA 保存并未丢失。

源码根因：`entry_tutor_context_support._build_learning_context` 已通过 Store course 过滤取本课历史，排除当前 session 后最多保留 8 行 previous_course_history；但 `llm_prompts._summarize_context` 完全丢弃该字段，只保留当前会话。不是要把旧记录混入 summary entry 的当前 history，也无需新建记忆或重写原 DB。

## 最小修复

只增量修改 canonical `llm_prompts.py` summary context/projection 附近：

- 复用 existing previous_course_history，最多处理原输入前 8 行；仅接受已知 Study LLM operation，再复用已有有界交互投影。
- 保留为独立 previous_course_history，每行加 `source_scope="previous_session_same_course"`。不回填当前 session_history/history，不发 opaque prior session_id，不声称本次刚完成。
- 继承出题 input 省略、无实际 output 的出题行省略、tutor 输出/learner_answer/request_or_material 来源、评分与已有 bounded next_action、private payload/image hash/隐藏答案/rubric 过滤。
- 不加入 course_learning_state 大 payload；不读取整仓库或发送无关源码；当前非空原 session 被过滤为空时仍保持空，不复活未过滤 history。没有 session 行时的原 legacy fallback 保持原行为。

Main 独占 prompt_templates.py 新 scope 语义：本次归因只基于 current；明确要求回顾上一轮或本次无互动时可引用 prior，但须称此前；真实答案/评分优先于旧老师总结，不要求补已有材料。本报告不把这些规则当作新版模型效果。

## 离线验证

使用 existing `benchmarks/raw/neko-product-host/.venv/Scripts/python.exe -I -B`。没有 SDK/model/host/audio/provider 调用。

| 检查 | 结果 | 范围 |
| --- | --- | --- |
| `scripts/test_neko_summary_interaction_roles.py` | 7 PASS | 原 5 个角色/隐私/边界检查；新实际 fresh SQLite、真实 `_build_learning_context`/Store course 路径、两个课程、关闭再打开 Store、新 session 空历史及旧本课题/错答/10分/next_action 入真实 prompt；foreign 课程排除、原 interaction 不变 |
| filtered-empty current 与 prior 分离 | 纳入上述 7 项 PASS | 当前 material-only generation 不形成虚假记录、不回填 current 或复活 unfiltered history；prior 独立最多8行、0分建议保留、course_learning_state 不送模型 |
| 原 course-memory summary 单项 | 1 PASS | 早期教学/晚期评分、0/100、nested/other-course 排除原断言不放宽 |
| quality18 实际 snapshot 最近8行的真实 prompt builder 投影 | PASS | 8行/2条 grade，ID26 的 score10 与 next_action 保留；每行 prior source_scope，出题 input 不出现。仅离线转换原 snapshot，不修改原 DB/JSON，不是再次模型调用 |

最初新测试误把 fixture 实际题目“图中链路起始、中间、结束分别是什么？”断言为包含“三个”；改为精确匹配实际 fixture，生产逻辑未因该错误放宽。

## 交付与剩余

只有 canonical llm_prompts.py、已有 test_neko_summary_interaction_roles.py 和本新报告变更；其他生产/entry/prompt_templates/manifest/records/host/原报告不改，原脏树保留。本轮外部请求0、未动预算或进程。

SOURCE/OFFLINE 通过；quality18 总结真实失败仍保留。需要 Main 整合 manifest/部署并安排一次有依据的真实总结语义复验，确认能称“此前”并使用已有错答/方向/下一步，而非再次索要。新版模型/Native/实际设备/真人均未通过声明。

既有窗口仍为最多 8 行，不能保证任意久远题目在多轮之后仍在窗口；本场 ID25/26/27 确实在最近8行，足以修本次遗漏。不额外扩大 SQL 或引入 course_learning_state 冗余。已有 prompt token budget 继续生效，长历史仍可截断；不承诺所有此前历史完整重放。文件冻结交 Main，长期 Goal 继续其余自主工作。
