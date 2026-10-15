# P5：无模型接续摘要

在现有Store增加只读resume_brief，按课程查询sessions、interactions（code_question/concept_explain/question_generate）和qa_records；不加表、不迁移、不重写旧记录。返回最近同一调用的最多三个源码窗口、最近学习问题/题目、独立的最近评分（保留0）、建议下一步。旧行无call时只取最新窗口，不拼接无关读取；新待答题不会继承旧题分数。

study_session(status)提供该字段，泛问“上次/进度”明确走它，替代recall_memory；详细复盘仍走summary。为防Native压缩掉课程/范围/0分，增加根据这些实际字段本地格式化的spoken_recap，中英文输出，不调用教师、不硬编码学习答案。提示角色完整转述；空历史明确告知没有可供接续的记录。

## 离线与部署

先红后绿：新增7项覆盖多课程/多会话、无call旧行、0分、空历史、旧题成绩与新待答题隔离、异常旧metadata、完整口头事实格式。课程8/重启3/语言6/角色指导2/summary scope1/interaction roles10均独立进程通过。

修改前32项旧SHA三方一致，分阶段保存代码/manifest，再部署到授权代码目录；新32/32、SourceGate和补丁check通过。未修改宿主、仲裁、打断或传输，没有新增记忆系统。

## 真实文字与 Native

| 场 | 账本前→后 DeepSeek/app | 证据 |
|---|---|---|
| SDK首次新库 | 1406/121→1408/121 | 源码讲解成功；默认target_weak出题因新库无跟踪数据被NO_TARGETED_QUESTION_DATA拒绝，保留失败，不伪造历史 |
| 唯一SDK调整复核 | 1408/121→1420/121 | 显式指定刚学的源码主题出题→错答0分→关闭宿主→重启→泛问调用session status→404追问调用explain重新读取源码；原QA哈希保持 |
| Native a，实际SDK库一致性快照、未复制角色聊天 | 1420/121→1435/122 | 泛问取得工具数据，复述文件与0分，漏课程/范围；同会话404追问有新教师/源码读取与音频，条件判断正确，但Native把throw所在行说成22，实际throw在23，行号质量仍有风险 |
| 本地事实措辞后Native唯一复核 b | 1435/122→1441/123 | 一次session工具调用，复述课程r2-resume-source、weather_service.dart第18至29行、上次题目、0分、复习错答后再作答；收到2413640 bytes PCM |

SDK直接status读取0新增模型调用（场内逐工具账本保存）；真实角色泛问仍需要角色模型本身，不能把整个语音回合说成免费。SDK泛问2.741s、追问6.592s；Native等待以raw时间戳为准，数字不等于真人听感。

Native a/b使用现有实际测试学习库的SQLite只读一致性快照和原源码授权；没有复制角色对话，避免用旧答案冒充读取学习记录。6项初版加完整措辞第7项通过；本阶段两场Native上限已到，不继续重复。

结论：数据派生、真实文字重启链与完整Native泛问事实通过；404端到端控制流通过但一次Native语句行号有误，仍需真人判断解释准确性。可听性/真人待用户。本项新增DeepSeek35、app2。原始场次均在raw/evidence/codex-r2-p5-*。
