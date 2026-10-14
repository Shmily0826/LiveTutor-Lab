# 换课返回原题：阶段十四源码与离线增量

完整contract仍为执行依据，Goal active。阶段十三56c2a07已发布；本报告阶段十四当前是SOURCE/OFFLINE，真实SDK/角色文字续题场尚待执行，不是设备/真人验收。

源码确认原set_course A→B→A会清当前题，历史保存不等于原题恢复。Main复用既有StudyStore SQLite kv，以course_teaching_progress:<course_id>保存原题、attempt旗标/缓存、最近评分及时间；结束旧session保存，set_course恢复目标课。显式study_start_session仍fresh，并写回该课空checkpoint，避免旧题复活。未修改、删除或重建原interaction/QA，未另建数据库/记忆系统。

study_session角色工具新增现有公共题投影和question_state，角色可读取恢复题，而不是凭聊天历史或重新出题。隐私投影去掉答案、rubric、cache及reservation owner/pending；原题私有内容仍供既有不可变题评分，当前图片变化不改旧题。

窄审发现同qid/aid恢复后的旧评分任务可能清新session reservation或stage旧cache。Main每次评分分配不可复用owner，清理只操作自己；reserve/stage/feedback/return锁内复核材料/session/owner。恢复及idle rollover移除旧reservation；成功cleanup/persist之后同步再核context/qid/aid，避免await中新换课后返回旧反馈。review确认两个窗口SOURCE REVIEW CLOSED。

Root真实方法/临时SQLite：course memory8项（新增2）、answer guard13项（新增3 async/锁竞争负例）、受影响language4项、task audit2项均过。包括A→B→A保存身份、B重启、fresh退役、已评分旗标/缓存、foreign checkpoint拒绝、public题不泄露，旧任务迟到不能清新pending、staging锁等待不能写新cache、最终persist换session拒旧回复。未运行无关旧批次。

为真实角色续题场记录action及公开题结果，source CLI只在新continuous-text task store对known canonical avatar单anchor加入私有JSONL观察，AST核后写task code，canonical不审计；unknown拒绝。auditing只写action/目标课程/current course/session/public question/state，不写headers/runtime/私有答案。仅此helper是受控量具，不是新产品数据流；raw/DB/audit不发布。

下一唯一continuous32按continuous-text-plan：fresh task store、已有forward/reverse，A生成恰一pending题→B图→角色切回A原样读原题→同A宿主重启→角色status读原题。零grade/QA/summary，不重跑C31或语音；同bargein-autocheck-20261012，当前595/2000、app58/null、tech0/0，不重置。noNative/noaudio/no捕获/no回环/不调音量，source env NEKO_TASK_SILENT=1。显式失效、网络错误或有界超时停止该场保留，不新quiz凑PASS。

6个payload真实hash已更新manifest，当前source/offline note明确pending真实场；原daily部署尚未启动刷新，不能称它已运行新checkpoint。阶段十四尚未commit/push；原master脏树/.workbuddy/empty index及原用户数据保留。

后续32观测失败保留、33只续未完成步骤：实际role set_course/status恢复原题，宿主重启后实际status及逐字复述通过，qid/attempt/public题不变、3原rows保持、0grade/QA/summary。详见continuous-text-model报告；原daily未刷新，语言前置英文PARTIAL及源码提示修法待必要场，不外推设备/human。当前ledger610/58/0，无活动自有host/Native/声音/捕获。

发布前最后边界：评分reservation改在_ensure_active_study_session之后、相同context验证的state锁内创建，避免空会话恢复题时正确清旧owner却也清掉新评分owner。重新核qid/aid/evaluated/pending，不做owner迁移或绕材料围栏。新增实际空session原题首次grade负例，Root answer现在14通过；33未评分，此增量只有SOURCE/OFFLINE，不重复付费场。
