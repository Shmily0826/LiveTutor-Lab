# 日常连续学习：最小实际角色文字集成计划

日期：2026-10-14。本文件为 SOURCE/计划，不是已执行场景证据。

已完整承接项目 contract、plan、status、blockers，以及 integration、code-coverage、daily-companion-use、summary-anchor-model 报告。主 Agent 最新交接：阶段十三 C31 的限定模型场已通过并发布 `56c2a07`；本计划不重复 C31、源码教学、基础图片理解或旧语音场。部分较早使用文档中“QA anchor 仅离线”的状态已由 C31 更新。本次只读源码与已有材料文件 metadata/hash，没有打开原用户数据库、运行测试、服务、模型、API、Native 或音频设备。

## 本轮实际缺口与最新修复

此前 `_start_study_session_locked` 只有 `resume_pending_question` 且同当前课时保留未答题；换课经 fresh session 路径执行，因此 A→B→A 清空当前题，虽然原 interactions/QA 仍保存。用户 contract C 明确要求保留当前题并验证换课再返回，历史仍在不能代替恢复待答题。该验收应保留。

最新源码已修复这条路径，主 Agent 报告 8 项实际方法/SQLite 离线检查通过。本次只读核对以下接口确已存在：

- `payload/study_companion/store.py:586–603`：既有 Store kv 的 `course_teaching_progress:<course_id>`，version=1、明确 course_id；保存 current_question、last_answer_evaluation 及题/评分时间。没有新增数据库或另建记忆系统。
- `payload/study_companion/__init__.py:_end_study_session_locked`：结束旧 session 前保存当前课 checkpoint。
- `__init__.py:_start_study_session_locked`：`resume_course_progress=True` 时恢复该课题、attempt 标志、last evaluation；剔除运行中 `attempt_evaluation_pending`。启动后保存当前状态，使显式 fresh session 替换 checkpoint，退役旧待答题。
- `entry_tutor_summary_entries.py:50–52`：`study_set_course` 调用 `_restart_study_session(..., resume_course_progress=True)`；显式 `study_start_session` 仍为 fresh 语义，不能用它模拟“返回原课”。
- `study_avatar_tools.py:study_session_tool`：公开 `current_question=public_current_question_payload(held)`，`question_state=pending/evaluated/none`。角色重启后可通过真实 status 工具读取题目，而不依赖旧角色聊天记忆。公开 payload 不包含答案、rubric、evaluation cache。
- `__init__.py` 启动恢复：同课未评 attempt 经 `resume_pending_question=True` 进入新 Study session，session_id 变化本身不代表题目丢失。

上述新 checkpoint/status 增量目前只有 SOURCE/OFFLINE 证据；需要下述真实 SDK＋实际角色文字场才能证明集成。主 Agent 的 8 项结果为交接事实，本子任务没有重跑或升级它的证明层。

## 材料与原题应采用的语义

`study_materials.py` 用既有 Store kv 按课保存最新提交图及文字。`study_submit_image` 在接受材料后更新 image/OCR、材料身份与控制通知，再运行既有 Study explain 路线；没有清空 current_question。因此同课换图目前保留原题。

原题是不可变的教学产物。`entry_tutor_answer_entries.py` 默认按 held question 的原 question/reference/rubric 评分，不自动用新保存图替换原题证据；原 private source_material_context 可记录出处。课/当前题/attempt 的异步 guard 仍约束旧结果。本场不要求“换图后旧题变为新图题”，也不要求以新图为旧题评分。公开题 metadata 不足以重建完整私有题，按课 checkpoint 应保存原产物，不能从历史重新出一题冒充接续。

本轮最小场是跨课材料替换：A 使用 forward，B 使用 reverse，再返回 A 并重启；不增加一次同 A 换图、评分、总结或第三套材料。

## 固定材料与隔离边界

使用本项目已有文件，不制作图片或录音：

| 课程 | 文件 | SHA256 |
| --- | --- | --- |
| A | `benchmarks/raw/evidence/diagram-input-forward.png` | `057d5bac5ae440dfa0d3269f5138f1188fa182bc0fce81435676c6a4caa65dcc` |
| B | `benchmarks/raw/evidence/diagram-input-reverse.png` | `1956a09783dd66b089979eead8729592c9d48cbe8770041badded5ff2347d700` |

Main 创建独立的新 task store，显式传 `--store`，另取不冲突的 A/B course_id。不可沿用 `neko_daily_code_dialogue_probe.py` 的默认 `neko-daily-companion` 或读取用户 daily history；不可恢复、清空、复制旧 C31 store。准备前核验实际 resolved store path、host source fingerprint 与新 store provenance；不符则停止，不用 reset 纠正。

图内容方向已在旧验收覆盖，本轮只验证 material hash/归属和真实 role 取题，不再次把正确箭头关系预先塞进角色 prompt。图片 SDK 提交的 explain 结果不单独升级为“角色重新理解图片”的新证明。

## 一次有界执行顺序

复用现有实际角色文字连接机制，而不是 Native/voice：读取当前角色名，文字 WS `start_session(input_type=text)`，等待真实 `session_started`；每条 `stream_data(input_type=text)` 等到真实 `turn end`。既有 `neko_daily_code_dialogue_probe.py` 的 framing、readiness、bounded timeout 和自有进程清理可复用；不要原样跑其源码问答清单或默认 store。出现 audio bytes、音频会话路径、服务 error 或超时立即停止，保留失败，不重连刷场。

| 步骤 | 操作 | 必须采集的新证明 |
| --- | --- | --- |
| 1 | 真实 SDK `study_set_course(course_id=A)`；`study_submit_image(image_base64=forward,text=既有简短材料描述,expected_course_id=A)`。 | SDK Ok/Err 与 accepted course/session/material；无 UI/用户 DB 代用。 |
| 2 | 实际角色文字：“请根据当前图片只出一道题，等我回答。” | 实际 `study_quiz`/生成 entry，恰一题成功；记录 qid、attempt、公开题文字/选项 hash、pending、private source course；公开结果无隐藏答案。角色确实等待，没有自行评分。 |
| 3 | 切到 B（使用 `study_set_course`，不能 fresh start）；SDK 提交 reverse，带 `expected_course_id=B`。 | A checkpoint 已保存；B material=reverse、current course=B；B 不能暴露 A 为 B 当前待答题。B 不另出题。 |
| 4 | 实际角色文字：“回到课程 A，接着刚才没回答的题，原样复述，不另出题或评分。” | role 实际调用 `study_session(action=set_course,course_id=A)`，随后状态或该返回提供原公开题；qid、attempt、题/选项 hash 与步骤2相同，pending，A material=forward，B reverse 仍保留。不得靠重复 `study_quiz` 替代恢复。 |
| 5 | 优雅结束文字连接并停止本场自有 host；同 store 重新启动，建立新的文字 WS。 | 新 host PID/启动与 resolved store/source fingerprints；新 Study session 合法，原未答题身份未变。不能调用显式 fresh `study_start_session`。 |
| 6 | 实际角色文字：“读取课程 A 当前学习状态，把尚未回答的题原样复述，继续等我回答，不另出题。” | 重启后的实际 `study_session(action=status)` receipt 含原公开题与 pending；最终角色输出覆盖原题完整文字及原选项，不添新题/答案；原 qid/attempt/public hash 和材料 A 保持。 |

步骤3的课切换可通过 SDK 或实际角色 `study_session(set_course)` 执行；记录实际选择。步骤4与6必须有真实角色取用工具证据，仅 SDK 读 state 不足以证明角色接续。若角色实际误调用 fresh start，则场失败，不能补一题后称通过。

SDK `study_submit_image` 会触发现有 explain 请求；按顺序等其 terminal 再切课。这里不是并发 stress，也不追加重复看图验收。实际角色 tool 名、entry 名及 safe args 从 receipt 记录，不能仅凭文字“我记得”断言成功。

## 校验与停止条件

只读核对本场新 task store，不访问原用户库。各阶段保存课程、Study session、material hash、公共题 hash、qid/attempt/pending 标志、本地 checkpoint version/course，以及 interactions/QA rowcount 与已有行 canonical hash；私有 reference/rubric 保留在 store 本地，报告和公共 role payload 不输出。

- 本场恰一次 `question_generate`；`answer_evaluate`、新增 QA、`summarize_session` 应为零。材料 explain 历史和 session 生命周期记录合法，另计，不混为题目重复生成。
- A 的题与尝试不能在返回/重启时再创建、替换、评完；B 状态不能把 A 题说成 B 当前题。
- 新 Study session_id 可以变化；题目源 session_id 保留出处，不强改成新 session 来掩盖来源。
- 旧已提交 interactions/QA 不重写、不删除；如启动已有测试 seed，先明确 baseline 后比较旧行 hash，不强制空库。
- 切回 A 与重启后图必须仍为 A forward。`study_material` 的 material_id 是图片串 hash 的短摘要，内部 material_identity 还包含 OCR，二者按其各自算法比较，不能直接当作相同 hash 字段。
- status 公共题无 answer/reference/rubric/solution/cache。角色自行吐答案、改题、跳过必要 status receipt、触发第二 quiz、课程不匹配、非文本输出、网络失败或有界等待超时均记录 FAIL/PARTIAL 并结束本场；不靠新 quiz、重试或恢复旧 DB 凑 PASS。

费用与 CONNECT 由主 Agent 按真实账本记录。本计划不设新额度、不开调用；网络失败不重做本场已经有证明的步骤。新场只有一次必要 pending 生成，后续以恢复和 status 为主，避免重复旧 quiz/grade/summary 证明。

## 证明范围与交付状态

本计划交付了可执行顺序及真实 contract 缺口定位；最新按课 checkpoint、fresh retire 与公开 status 的 8 项 SOURCE/OFFLINE 证明可继承。真正的 SDK 注册/序列化、实际 role 文字决定、换课返回和重启后的同题复述，仍待 Main 运行这一次有界场。

即使全场通过，也只证明该隔离 task store、该角色文字路径和两课/一题流程；不声明 Native/语音、物理播放、真人体验、所有课程、网络恢复或自然停顿通过。显式 fresh retire 的负例和 immutable held grading 继续引用现有离线 guard，不为此新增付费场。C31 的真实 summary QA 焦点证明独立保留，不外推为本场 pending checkpoint 已通过。

本子任务仅创建本文件；其余代码、测试、manifest、共享记录、进程和账本均未修改。计划冻结，后续执行与证据记录由主 Agent 负责。
