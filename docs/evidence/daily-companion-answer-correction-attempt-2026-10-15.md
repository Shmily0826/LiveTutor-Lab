# 同一道错题显式重试与纠正记录

2026-10-15。接续既有Goal/current contract与执行记录；Main独占online、额度、共享代码/部署。本阶段只修改canonical `entry_tutor_answer_entries.py`，新建`test_neko_answer_correction_attempt.py`及本报告。没有修改Store、models、service、avatar、manifest、四记录或原用户DB；没有服务/provider/设备/mic/capture/loopback。原Native直接口头评分未落库的缺陷不由本入口单独关闭。

## 已交付

新增显式SDK `study_retry_question`，不是题目生成，也不调用模型：

```python
await plugin.study_retry_question(
    question_id=old_question_id,
    attempt_id=old_attempt_id,
    course_id=current_course_id,
    session_id=current_session_id,
)
```

四个字段均为SDK必填非空string，精确匹配当前持久held题及当前course/session，包含当前运行中的_session_id；不自动初始化会话、转课或挑另一题。只有原attempt_evaluated为真实bool True、同qid/attempt的cache verdict为wrong或partial、非degraded/错误结果、无pending/owner reservation时允许。未知/正确/未评/不完整cache、外课origin拒绝。cache来自既有正式grade staging，无新增评级或从口头判断倒填。

成功生成一个新的`a_<uuid>`，原question_id、题干、topic/selected_topic、私有答案/rubric和source origin逐字段保持。新attempt移除旧cache/reservation/recovery、置未评分，原QA/错答/history完全不改不删。last_answer_evaluation保留为此前实际已发生的成绩，而非给新attempt套旧cache；后续正常grade会更新它。无需重生成题或新概念ID。

成功SDK返回`retried=True`、`question_state='pending'`、原qid、新attempt、previous_attempt_id、current course/session及现有public_current_question_payload；不返回隐藏答案/rubric/private origin。旧attempt参数重复调用会拒绝，普通study_answer重放原已评attempt仍按原ATTEMPT_ALREADY_EVALUATED拒绝。

拒绝码：QUESTION_CONTEXT_CHANGED、ATTEMPT_IN_PROGRESS、ATTEMPT_NOT_RETRYABLE；保存失败为RETRY_PERSIST_FAILED。拒绝控制操作不调用模型，不增加评分/QA记录。入口不要求_agent存在，因此网络/模型不可用仍可准备一个已明确请求的新attempt；实际答案评分继续由原grade入口负责。

## 持久化与并发

查过既有Store.get_retry_wrong_question：它读取错题供练习选择，并不更新当前held attempt；没有等效显式重试入口。未另造wrong-question/history系统。

既有Store.save_state与save_course_progress通过set_raw分别commit，直接连续调用会在第二次失败时留下半更新。新私有`_save_retry_question_checkpoint`持原Store.answer_write_lock、复用原连接和kv表，在一个BEGIN IMMEDIATE事务更新现有`state`与`course_teaching_progress:<course>`两key；按原version1 course progress投影写四个既有字段。没有新表/长期队列。连接已有未提交transaction时拒绝，不rollback别人的事务。模型、网络或SDK推送不在该锁内。

state lock内先核原身份，copy候选并交给短本地SQLite worker；**提交前不改live current_question**。失败rollback，两key和live都保持原attempt；没有“失败后重新覆盖旧snapshot”的路径，因此不会把随后新课/新题还原。其他标准setter必须继续沿现有state lock协调，这沿用现有插件约定。

任务取消时不能放走仍可能commit的to_thread：在原state lock内shield/drain这段SQLite事务。若已经完成commit，同步live新attempt后传播CancelledError，DB/live保持一致；这意味着caller取消/回执丢失可能已建立新attempt，应先read status再决定重试，不盲重放旧ID。这个恢复边界不宣称取消必然零写入，不清已有历史。进程崩溃两kv由SQLite同事务保障；完整断电/磁盘故障设备验收未做。

## 离线证据

```powershell
& benchmarks/raw/neko-product-host/.venv/Scripts/python.exe -X utf8 -B scripts/test_neko_answer_correction_attempt.py
& benchmarks/raw/neko-product-host/.venv/Scripts/python.exe -X utf8 -B scripts/test_neko_answer_material_guard.py
```

新10 tests PASS，1.143秒；受影响原14 tests PASS，1.256秒，均exit0。实际entry/wrapper/context/finalizer/Store/Tracker，fresh临时SQLite，本地async model；没有SDK服务/真实模型/音频。早期fixture有两处调用形状错误（旧error已flatten、fixture导出locked lifecycle方法），已按实际接口修正，不放宽产品断言；真实staging测试改为等到实际attempt_evaluated阶段才阻塞getter，未手造成功reservation。

- 实际wrong→retry→A/B/A返回→新实例重启→correct：两QA、同topic/qid、两个不同attempt；原QA整行dict仍完全一致，重试时旧interaction不增加/删除。checkpoint和state真实保存新attempt，正确评分更新latest evaluation。
- partial可重试，正式correct不可；普通已评grade与重复旧retry ID仍拒，模型只评一次原attempt。
- 14种false/unknown/foreign/busy条件拒，held及SQLite total_changes保持；没有用伪cache造成功路径。
- 两个同pin并发retry只有一个新attempt；真实grade已staged但reservation owner尚未清理时拒，清理后允许。
- _agent=None也可准备retry，QA数保持，不隐式模型生成。
- 真实SQLite TEMP trigger让第二kv写入失败：第一个state写入也rollback，live/state/course progress保持。
- 保存worker失败且随后course switch执行：course-B和新空题保持，旧课QA不删，不将旧题覆盖回新课。
- worker等待中取消：锁保留到事务结束，完成后live/state/checkpoint一致，旧QA保持。

原14 guard保留ordinary grade的材料、reservation、课变更、晚题/commit、cleanup及旧task隔离。图片验证/event push/UI缓存及本地model仍是fixture double；“重启”是actual Store.load_state＋实际session lifecycle的新实例，未启动桌面宿主。SDK注册/真实远端参数解析、Native选择重试工具、模型正确判分与设备/真人纠正体验尚待Main集成。

## Main接入约定与剩余

Main拥有avatar/ASR路由，只有学习者明确重新回答/纠正同一道已错或partial题时调用retry；普通“解释为什么错”不应创建attempt。调用前固定真实status四字段；成功后用返回的新attempt构造_expected_question，再将完整原纠正答案交原study_answer。任何retry Err须停止该次评分，不改用最新任意题。retry回执丢失时先读状态，不因仍有原qid就重放旧attempt。

SDK返回public当前题只是身份/可见内容；不能声称新答案已评分。旧评分继续由QA/history记忆取用，correct后应真实回读新attempt/evaluation。只恢复成绩数据控制入口，不新增人格/主动测验、不把临时纠正要求变长期偏好。未知Native forced-tool协议、owner/自由音频抑制、真实错答纠正的模型/设备证明仍由Main完成。

本阶段SOURCE/OFFLINE交付；不冒Native/model/device/human PASS。以上三个文件完成后冻结供Main集成；无commit/push/deploy或其他文件写入。
