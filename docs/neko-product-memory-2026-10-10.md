# LiveTutor v0.2 课程记忆局部修复

已完成源码、隔离数据库回归与真实 Study UI 的宿主重启、换课、返课验收。原始答题和课程隔离通过；同概念自动标签的 Mastery/FSRS 归并仍为 PARTIAL。

## 原问题与修复

- 现有对话查询只取当前 Session，新 Session 无法带入上一课的上下文。现加入 `sessions.course_id`、持久化 `study_course_id`，查询同课前序 Session 的历史与答题记录。
- 全局弱项、FSRS 和自适应出题可能混入其他课程。复用现有 Store、KnowledgeTracker、Mastery、FSRS、PracticeScope 过滤器，按当前课程的 QA 记录限定主题；主题身份采用 `课程::主题`，显示名称仍为原主题。
- Flutter、Dart、Widget、Provider 缺少学科标识，运行时主题可能被默认写为 math。现识别为 computer_science。
- 总结入口未传 Session 上下文到保存函数，导致总结不落入 interactions。现传入真实请求上下文；总结读取至多 100 条当前 Session 记录。
- Store 的 history 是倒序，最近上下文却从数组尾取值，可能选中较旧记录。现在按记录 ID 排序，再提取最新内容。

## 用户入口契约

`study_start_session({course_id: "flutter-provider"})` 开始该课程的新 Session，返回 `session_id`、`started_at`、`course_id`。`study_set_course` 要求非空课程 ID，调用同一入口。课程 ID 最长 80 字符，界面应保持其稳定；省略时沿用当前课程，初始值 general。

重开宿主仍保留所选课程，Session ID 更新。切换课程会清除当前练习题、OCR 文本和旧练习范围。既有未标记课程的数据库记录不自动归入新课，避免错误认领历史材料。既有模式与全局配置继续复用，没有新增记忆架构；尚未发现独立通用教学偏好字段/提取链路，不能声称跨课程偏好完整验收。

## 隔离验收

命令：`benchmarks/raw/neko-product-host/.venv/Scripts/python.exe -I -B scripts/test_neko_product_course_memory.py`。

结果：最终 4 个测试通过，0.470 秒。测试只打开新建临时 SQLite，直接执行产品 Store、Tracker、学习上下文和现有 Session 生命周期方法；未启动宿主、浏览器、OCR、模型、麦克风或音频。新增提示序列化检查确保 15 条总结记录/末尾评分保留，以及长/短当前出题材料和格式要求完整保留。

验证包括：

- Flutter Session A 写入错误与正确答案，创建 Mastery 和 FSRS。
- 关闭数据库后重开，所选课程恢复；新 Session B 的模型提示包含同课旧解释、错误答案与正确答案。
- 切换积分课程后，Flutter 对话、答案、薄弱主题、错题和同课历史查询不混入。
- 15 条本次互动的总结上下文保留第一条；实际 `study_summarize_session` 入口将总结保存到本 Session。
- 倒序历史输入最终提取的确实是最新互动。

## 真实宿主/UI 证据

本轮 [真实 Transcript](evidence/flutter-product-transcript.md) / [原始 JSON](evidence/flutter-product-transcript.json) 中的 session_B_memory 正确找回三次评分（两错一对）、错误 C 的 read 误解、错误 A 的 watch 自动监视误解及最后正确 C 的进步。course_isolation_math 只讲交集 A∩B={2}，明确离散数学无历史记录。course_return_flutter 仍恢复同样的两错一对，数学讨论未混入 Flutter 事实。memory_plain_language_retest 用学生语言准确总结，没有暴露内部 mastery/confidence 字段；仍额外加小检查，严格长度 PARTIAL。持久化补充证据：[真实运行](evidence/flutter-product-memory-runtime.json) / [最终快照](evidence/flutter-product-memory-final.json)。

这些额外真实教学的模型链路时长分别为 5.066 s、3.509 s、6.204 s、3.182 s（前置语义路由 started 至讲解 completed）。UI 记录保存等待只是观察上界，不是服务延迟。

## 已证实的概念级追踪缺口

只读实际本轮隔离 DB（SQLite mode=ro），证据保存于 [topic 标签快照](evidence/neko-product-topic-label-review.json)：QA1 的 Provider read/watch/notifyListeners 机制 wrong0、Mastery0；QA2 的 Provider notifyListeners 与重建 wrong0、Mastery0；QA3 的 Provider read/watch 与 notifyListeners correct100、Mastery0.6189。三个标签各只有一次答题，分别有三张 FSRS 卡。

QA2/QA3 实际考查同一删除通知后的行为，但自动题目标签不同，纠正没有更新原标签的 Mastery/FSRS。这证明原始保存和回忆可用，也说明概念级进步尚未稳定归并；本轮保留证据，不改库、不建立新框架。已保存一条真实 Session 总结，与最后两题一错一对一致。

全局统计/课程浏览 API 仍可展示总体学习数据；教学上下文已按课程过滤。下一步应优先复用现有 targeted-question/已选 topic 身份稳定同主题练习，避免继续让自由文本标签决定全部量化追踪。
