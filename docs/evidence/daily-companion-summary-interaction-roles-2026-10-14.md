# 总结交互角色投影：源码及离线通过

承接长期 Goal 的 contract、plan、status、blockers 以及 `daily-companion-phase7-teaching-device-2026-10-14.md`。voice17 当前会话仅有 question_generate、answer_evaluate、summarize_session；模型把出题行 input 中的材料准备请求当成学习者已经完成的讲解，并且总结没有使用实际评分记录已有的下一步。原事故的模型/设备证据保留；本轮没有新模型或设备验证。

## 最小改动

只增量修改 canonical `payload/study_companion/llm_prompts.py` 的 `_summary_interaction_rows` 附近：

- question_generate 行省去 input 与 input_role，只保留原老师出题输出；材料准备请求不再作为会话学习行为送入总结。没有实际 output 的出题行直接省去，不从 private payload 补造题，也不形成虚假出题完成记录。
- 所有 output 明确标记 `output_role="tutor"`。仅 answer_evaluate 的 input 标记 `input_role="learner_answer"`；其他保留输入标记 `request_or_material`。老师既往总结也属于老师输出，不能独立证明学习者掌握。
- 评分 allowlist 增加原 payload 中的 `next_action`，复用既有 160 字符内容截取及明确截断标记，不生成新建议。保留真实 question、verdict、score、feedback、missing_points、misconceptions 等证据。

不改 SQLite 数据、原始交互、题目/作答/attempt 身份、课程或材料 guard；不新增记忆。没有转发 payload 私有材料字段、图片 hash、隐藏答案和 rubric。相邻 `_summarize_context` 保留一个必要范围保护：原 session_history 非空但过滤后为空，仍使用空 session_history，不能误回退到不相关 history；原本没有 session 行时仍沿用原 fallback 行为。

Main 独占 prompt_templates.py 的角色归因、相反关系与省略的区别、口语下一步规则，本轮没有修改该文件。上面角色键值供该规则使用。

## 离线证据

使用既有隔离 Python：`benchmarks/raw/neko-product-host/.venv/Scripts/python.exe -I -B`，未启动宿主、SDK、供应商、音频或麦克风。

| 检查 | 结果 | 证明范围 |
| --- | --- | --- |
| 新 `scripts/test_neko_summary_interaction_roles.py` | 5 PASS | 实际 prompt builder/projection、fresh SQLite；voice17 形状的出题材料省略、真实 wrong/10 与已有下一步保留、teacher/learner/request 角色、0 分不丢、长建议有界、隐私 allowlist、40 行顺序与边界、原数据库历史不变；input-only generation 不制造题目或泄入旧会话，原 empty-session fallback 保留 |
| 原 `scripts/test_neko_summary_material_guard.py` | 14 PASS | 真实 summary entry/context/finalizer/fresh SQLite 配合本地异步桩；初次初始化、换课/换 session、history/context/model/短 SQL/narration 各竞态保护继续成立 |
| 原 course-memory summary 单项 `test_summary_serialization_keeps_late_grades_and_early_lesson` | 1 PASS | 真实总结 prompt 保留早期教学与晚期评分，0/100 分、会话范围及 nested/other-course 排除继续成立；没有重跑整批旧教学 |

新测试直接比较原 SQLite history 与投影前 history，未修改旧历史断言或放宽既有 guard。首轮新测试曾将截断后的总字符串错误限定为 160；既有 compact helper 是 160 字符内容加截断标记。已改为严格验证前 160 字符和精确 `...[truncated 440 chars]` 后缀，生产截断逻辑保持原样。

## 边界与接续

本次只有源码/离线通过。角色标签与省去材料输入能消除该信息混淆入口；不能声称模型已不再误归因，不能称新版实际设备或真人体验通过。旧老师总结的原文字仍保留并明确标为 tutor，不修写原历史；模型必须按 Main 的归因规则谨慎使用它。请求/材料仍不应被解释为完成行为或掌握度，next_action 只提供已记录建议，不保证本次口语一定采用。

只有三个任务文件变更：上述 llm_prompts.py、新投影测试、本报告。既有脏改动保留；本轮未修改生产其他模块、共享 manifest、原 guard 测试、账本或进程。沿用 Main 最新已核状态 577/2000、Lanlan.app 56/null、Lanlan.tech 0/0，本轮外部调用 0；未独立重读或调整账本。文件冻结后由 Main 检查 manifest/部署，再安排有依据的纠错与总结设备验证；长期 Goal 继续。
