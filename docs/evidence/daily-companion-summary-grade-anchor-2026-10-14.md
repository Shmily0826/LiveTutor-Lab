# 总结长期评分锚点：源码/离线通过

承接 quality18 的真实接续失败和 quality19 的修复后限定模型证据。`daily-companion-20261014-summary-continuity-quality19.json` finalized=true；真实 backend summary 明确“上一轮”源码、“更早一轮”图题错答、REZ→NUD→WEX 与具体复述下一步；原 interactions/QA 不变。scope 为 Study SDK/backend/SQLite，audio_session/room_microphone/native_window=false；终态581/56/0，不含 Native、设备或真人证明。Main 已清理全部本任务进程。本轮没有新 SDK/model/host/audio/外部调用、预算或进程操作。

## 既有边界与最小增量

previous_course_history 最多8行，能修 quality18/19，却可能被后续老师讲解/总结挤满。既有 `_build_learning_context` 已提供按 Store sessions.course_id 过滤的 course_learning_state.recent_answers；canonical `store_qa.list_qa_records` 返回 ascending，`records[-8:]` 取最新，不需新 SQL/Store/记忆系统。

仅增量修改 canonical `llm_prompts.py` summary 附近，新增 `_summary_previous_answers` 与根 prompt allowlist 字段 `previous_answer_records`：

- 只读取已查询的 recent_answers 最近8条，最多投影3条去重后的实际 graded 记录，保留时间顺序。独立字段，不伪装 interaction、不回填 current history/session_history，也不覆盖当前题。
- parent course_learning_state.course_id 必须与非空当前 course_id 精确一致；当前 session_id 必须明确。排除同当前、空、default/unknown session；拒绝缺失持久 QA id、畸形题文/答案/评分，score 必须为0..100的有限数且不能是布尔。
- Store course-filter 是权威范围。child question.course_family 非空且不匹配时拒绝；缺省仍接受真实已过滤 legacy QA，不因新增字段使旧记录只能保存不能取用。
- 本地使用持久 QA id 和实际 `(question_id, attempt_id)` 去重，同题不同 attempt 保留各自真实结果；不新建或改名 concept。opaque QA/question/attempt/session/topic IDs 不发送模型。
- 仅输出 source_scope=`previous_session_same_course`、公开 question text、user_answer、input_role=`learner_answer`、evaluation_role=`tutor` 和 evaluation 中 verdict/score/feedback/已有 next_action。题文240、答案200、feedback/next_action160内容字符加原明确截断标记；不输出 hidden answer/reference_answer/rubric/material/image等私有字段，不输出整个 course_learning_state。
- 原角色/隐私/当前 filtered-empty 保护保持。调用者直接提供的 previous_answer_records 不被信任，锚点只能由受限已有 QA 投影生成。

Main 仍独占 prompt_templates.py/entry/manifest/host/records/部署。根 allowlist 增加字段仅使上述投影能进入实际 summary prompt；Main 应沿用“此前会话”归因并优先实际答案/评分，不把锚点称作本次完成。

## 离线证据

采用 existing `benchmarks/raw/neko-product-host/.venv/Scripts/python.exe -I -B`，没有 SDK/model/host/audio/provider 调用。

| 检查 | 结果 | 证明范围 |
| --- | --- | --- |
| `scripts/test_neko_summary_interaction_roles.py` | 10 PASS | 原7项投影/接续继续成立；新增实际fresh SQLite/真实 `_build_learning_context`/Store course过滤，legacy QA无course_family，旧graded题被12条后续summary挤出8行interaction仍进入最终prompt，foreign/current QA排除，公开错答/0分/实际反馈/next_action保留，private/opaque字段排除，原QA与当前题不变 |
| 限量/去重/负例 | 纳入上述10项 | 最多3，持久QA id与同qid/attempt重复去重、不同attempt保留；未知parent scope、非list、无当前session、foreign child course、未知prior session、畸形ID/题/答案/评分/建议拒绝，NaN/布尔/负分拒绝；直接伪造anchor不生效 |
| 原 course-memory summary 单项 | 1 PASS | 实际prompt保留早期教学/晚期评分、0/100与原隐私/范围断言，不放宽旧断言、不重跑整批已过教学 |
| targeted diff check | PASS | 任务拥有产品/测试文件无空白差异错误；实际import已覆盖源码语法 |

新增 SQLite 测试最初误要求 `_build_learning_context` 对空会话一定存在 session_history 键；实际该底层方法可省略空键，summary entry 另提供空列表。测试已同时确认实际 history=[] 与 session_history 的有效空值，没有改产品入口或放宽课程/QA保护。

## 证据层级与交接

SOURCE/OFFLINE 通过。quality19 是此前“8条prior互动”版本的真实模型通过，不外推本新增 QA anchor 已被模型/Native/设备/真人正确使用。本轮外部请求0；沿用 Main 已核 581/2000 DeepSeek、56/null app、tech0/0，账本未重读或调整。原用户 DB/history/QA、材料、题身份和不相关脏工作保持。

剩余边界：recent_answers 本身仅来自现有最近8条QA，不能承诺无限历史；新锚点最多3条且已有summary token budget继续生效，长当前材料可能继续被压缩。旧不带可核parent course/current session 的 context 不投影锚点，诚实留空，不借猜测跨课取用。缺省course_family的合法旧QA由真正Store/session course过滤保护，不声称单靠缺省child字段能证明课程。

三个自有文件交付并冻结：llm_prompts.py、test_neko_summary_interaction_roles.py、本报告；未改 prompt_templates/entry/manifest/host/records/额度，不新建Agent。由 Main 后续结合新材料/语言真实场自然补证，无需为锚点重复 quality19 付费。长期 Goal 继续。
