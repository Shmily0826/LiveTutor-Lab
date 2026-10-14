# 阶段24：显式答题意图与只读题目 pin helper

状态：SOURCE / OFFLINE；新增 helper 和临时 SQLite 定向测试已完成冻结。没有接入实际 ASR/Core、正式评分、SDK、provider、音频、设备或真人验收。不替代长期 Goal 的剩余工作。

本子任务只新增 `scripts/neko_study_answer_intent.py`、`scripts/test_neko_study_answer_intent.py` 和本报告；没有改共享 patch、host、部署 helper manifest、四记录、账本或用户数据。使用标准库，无依赖安装/新系统，按 ponytail 最小完整实现。接续既有四份记录与 Main 阶段24授权；本轮禁止 mic/capture/loopback，未执行任何声音或服务。

## 接口及严格边界

`answer_intent(text) -> "answer" | "correction" | None`。

只在用于匹配的副本中消除相邻中文字之间的空白，再 casefold/collapse whitespace；输入原字符串没有改写或截取，函数也不生成替代答案。Main 应把原 ASR 全文原样送正式 entry，而不是把副本或分类标签当答案。引用片段从匹配副本移除，引用中的评分指令不能授权；原代码/答案里的引号内容仍完整留在原文中。

中文目标为明确当前/刚才/刚刚/上一题；英文目标为 current/last/previous/just-asked question 或 question you just asked。普通答题需自身答案/选择表达及明确请求判断/评分；更正需自身同题的更正表达。中英拒绝模糊代词/无题目目标、仅图对不对、解释旧答案、他人话语/引用、假设、不要评分、出题、纠正老师答案或更改课程/发音的误命中。测试包含本场常见中文字间空白、代码标识符、数字与完整引用答案。

这是保守规则，不是通用语义模型：部分口语省略、陌生同义表达会返回 None；否定/假设/他人或多个意图出现时优先拒绝。裸 `if` 等代码条件词、无明确“当前/刚才题”的简短答案也可能被拒，不能为了命中提升为隐式自动评分。分类仅表示显式意图，不能证明答案有效、材料正确、实际函数调用或评分已经发生。

`read_question_pin(runtime_root) -> {course_id, session_id, question_id, attempt_id, attempt_evaluated} | None`。

参数是实际 host 的 `NEKO_STORAGE_SELECTED_ROOT` 指向的 **N.E.K.O runtime 根**，不是其外层 task store。唯一 DB 路径为 `runtime_root/plugins/study_companion/data/study_companion.db`。要求绝对已存在的 plain root，DB 与内部目录不为 symlink/reparse，解析后仍在 root 内，单文件 hardlink 也拒绝；返回前 recheck path/file identity，检测到替换则拒绝。没有创建目录/DB或实例化可迁移的 StudyStore。

sqlite 使用 `mode=ro`、`query_only=ON`、`timeout=0`、`contextlib.closing`。仅一次 SELECT 从 kv/state 投影 `study_course_id/study_session_id/current_question.question_id/current_question.attempt_id/current_question.attempt_evaluated`；用 json_type 核 bool 必须是 JSON true/false，LIMIT2 拒非唯一 state，四 ID 必须是非空字符串（不截取返回），不会抓取完整 state/history/题干/answer/rubric/config/keys。锁、缺字段、坏 JSON/未知 schema、非法路径返回 None，不输出 exception/路径/学习数据。没有重试或 immutable=1 绕 WAL。

返回 evaluated=True 仍是有效身份快照，由 Main 决定普通答题/更正是否准入；未评分题不能把缺失或整数 0 自动视作布尔 false。首次 speech frame 前调用一次并固定副本，**不得每 frame 重读或追新题**。Main 仍需用实际 boot/connection/Core owner/输入 scope 与该 pin 绑定，在正式提交、await 后及发声前核当前身份、防重、换题/换课拒绝；这个已落库快照没有提供 live authority、provider call_id 或 utterance ID。它也不是恶意并发路径交换的系统级 file-handle admission，返回前检查只拒绝实际检测到的替换；部署及调用路径由 Main 控制。

## 离线证据

`python -B scripts/test_neko_study_answer_intent.py`：14 cases，13 PASS、1 SKIP（0.318s）。语言 cases 内含多个中英正负 subtests；真正 SQLite 创建、只读连接、trace query 数量、DB bytes 保持、连接关闭后立即 rename、bool及四 ID、缺库不创建、exclusive writer 锁 timeout0、hardlink拒绝、未知 schema、读后检测文件替换均通过。没有服务/音频/model。

唯一 SKIP 是 Windows 真 symlink→外部 DB 创建，系统 `WinError1314` 缺权限；没有要求系统权限、提升权限或伪称通过。源码包含链接/包含关系拒绝，真实 hardlink 负例已过；真实 symlink 案例待有既定权限的环境执行。之前首版把 symlink 创建失败与 hardlink 合在一 case 不够透明，最终已拆成明确 SKIP，不借 hardlink PASS 当 symlink proof。

所有测试 DB 是 stdlib TemporaryDirectory 的 synthetic state，清理正常，未触碰用户/任务真实 DB。外部模型/服务请求为0，未启动 host/Native/browser/设备，账本不读不写；未尝试之前被拒的六空目录清理。

冻结 SHA256：

- helper：`515fab3f66ba7c33fc72871ff399644d820c92eccba776dc35d1582ae537083c`
- tests：`664086e478b1c0a6536649091096337a27e77a26e1f27eb430fcac425b833cb4`

下一步由 Main 独占：作为第三 helper 安全部署与实际 cwd import gate；把首次输入 pin 和原 ASR 全文接入真实受权评分链，定向验证 old/new question、纠正、停止/失败、不重复正式 attempt 及答案播出。当前未做上述集成，不宣称 Native 原来零 tool 自由判错的问题已解决。
