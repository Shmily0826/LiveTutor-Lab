# 阶段23：真实同题更正与已评分题重启接续

2026-10-15，原Goal active，完整contract及后续音频指令不变。阶段22源码已发布7ffb334；本阶段只用既有任务课程 `neko-daily-continuous-text-20261014-32`，有fresh task-provenance；复用C32/C33真实模型原题及既有对比图，未生成新题/图片、未打开原用户daily数据库、未采集或播放音频/使用设备。source子进程 `NEKO_TASK_SILENT=1`、text-only。原round不重置，DeepSeek675→677/2000，Lanlan.app63不变，tech0/0；计数不是账单金额。

## 实际通过与两个保留失败

通过真实HTTP plugin llm-tool callback→SDK→既有Study入口→DeepSeek→SQLite：明确错误方向得到wrong；带原双ID及四身份pin的更正得到correct。question_id及题干不变，attempt_id更新；两个QA，同topic_id，第一条wrong行hash完整保留。评分入口返回的反馈/100分及状态一致。此处是直接callback验证正式工具，不冒称Native模型自动选工具。

第一次场在已完成两个评分及A→B→A之后，量具直接索引set_course ACK不存在的last_answer_evaluation，报KeyError，原FAIL_OR_PARTIAL不改。set_course ACK已有evaluated公共题，但完整last grade应从status读取。只接续未做status/restart，无重评/新题/模型请求。

接续场发现**真实产品缺陷**：startup仅resume_pending_question，已评分题及反馈被清空，空checkpoint写回；两条QA仍保留，recent_answer_records仍有2。旧pending C33通过不能覆盖这个graded分支。第二个FAIL_OR_PARTIAL保留，不归为量具错误。

## 源码修复与可复核范围

startup及空/idle Study会话使用resume_current_progress；现有state中当前课最新四字段（current_question、last_answer_evaluation及两个时间）优先于旧checkpoint。空state同样权威，避免明确fresh开始后复活旧题。换课仍使用该课既有checkpoint，显式新会话仍fresh；旧reservation字段清除。复用原SQLite，不新增表、队列或记忆系统。

Main course8、answer14及新graded-restart3通过；新3独立通过。新用例采用实际startup AST参数、实际wrapper/lifecycle方法与临时SQLite，覆盖wrong/correct重启、stale checkpoint、empty/idle runtime、reservation去除及fresh不复活。测试初稿误用SDK方法名on_start而非实际startup，修量具后通过；这不是产品失败。独立review见同日graded-restart-review；不能由AST/临时库冒称完整宿主通过或掉电原子性。

为不重复两个已成功付费评分，Main在**唯一任务C32库**中，按冻结的真实评分后state与两QA完整hash恢复被旧startup清掉的四个checkpoint字段（state与course_teaching_progress同事务）；其它state字段、所有interaction及QA原行不动。任务恢复清单和失败基准hash本地保留。原用户daily库没有恢复/复制/清空；不声称产品会自动修复已损坏历史。此项是明确fixture恢复准备，不能算未经中断的连续学习证明。

修后实际source宿主采用canonical __init__逐字相同部署：原题、新更正attempt、evaluated及last grade correct读回；B无A题，返回A原题/grade一致；再次完整停止/启动同库，状态和两QA仍一致。原interaction行hash全部保留、question_generate仍恰1、answer_evaluate恰2、Study config不变。两个宿主由自有清理强制退出（进程exit1、cleanup_errors=[]），不是自然正常退出0证明。最终scene9824已terminal，48911/48916无listener。

私有原件只本地：

| 报告 | SHA256 / 范围 |
|---|---|
| daily-phase23-correction-model.json | c8e9a6e27b7d4e81e60208624dbd181024a10393cb8178faaa44a57e0a759650；真实wrong/correct，ACK量具失败 |
| daily-phase23-correction-continuation.json | ca2ad8dbbe87c700ff363d6654fa6c054d3613d8c8aa9e1b33cfe78698cade48；实际graded重启丢题失败 |
| daily-phase23-task-checkpoint-recovery.json | 687abbe52075011bfc1202b6f2acf48abe1e5560ba19fc0e2f6aefb04194e4fb；仅任务四字段准备 |
| daily-phase23-correction-fixed.json | 80455018f05fa38f42586f6417d3a077f61fc465090154296f49397c75f28ad6；修后完整宿主状态/返课/重启通过 |

## 剩余

SOURCE/OFFLINE、HTTP真实模型正式工具评分、修后本地完整宿主/SQLite通过；Native自动ASR评分、正式成绩语音转述、实际可听、真人仍待验。启动与checkpoint/state依然不是所有掉电窗口的原子协议，不外推未测边界。

Native fallback设计已窄审：ASR recv不能等网络评分，须固定真实connection/scope/lease owner后后台任务；先固定权威原题，四身份pin防status后换题；同轮输出hold和已有arbiter逐send守owner，不能伪造provider function_call_output。未宣布响应/缺终结时不能timeout放行下一段音频；material取消永久退physical token、ordinary barge-in带PCM replay，均不能直接挪用。先实现并验证正式评分和诚实回执；可听闭环需要有证据的旧终结或有界无PCM连接隔离。详见native-grade-fallback-design同日报告。局部协议边界不暂停全部Goal，完整A–F继续，集中真人体验仍后置。
