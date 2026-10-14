# Course checkpoint 保存与恢复窄审

日期：2026-10-14。唯一写入为该报告。只读 canonical `store.py`、`__init__.py`、`entry_tutor_summary_entries.py`、`test_neko_product_course_memory.py`；按Main追加纳入 `study_avatar_tools.py` status投影。为核guard必要callee，定向读取实际 `entry_tutor_answer_entries.py` 的reservation/staging/catch、context finalizer相关引用与models public投影，不扫描全仓。

本轮未修改生产、测试、manifest、数据库或账本，未运行测试、服务、模型、Native、设备或API，没有新增Agent。Main报告8实际方法/临时SQLite通过，不由本审查外推真实模型、Native/device/human。整个Goal不因checkpoint小阶段认领完成。

## P2：恢复同attempt后的旧grading cleanup/staging有ABA窗口

新set_course刻意恢复原question_id/attempt_id，而每次恢复创建新的study_session_id。这是正确的artifact接续，但引入以前“换课会丢题”时很难出现的同id跨session ABA。

必要callee `_clear_attempt_evaluation_reservation`（answer_entries `22–38`）只在plugin lock内比较attempt_id，然后pop `attempt_evaluation_pending`。旧A grading迟到失败/cancel catch（`405–419`）仍按这个旧id清理。可复现顺序：A旧请求已reserved并等model/IO→B→A恢复同AA到新session→新请求对AA设pending→旧A因MaterialContextChanged/cancel进入cleanup。旧cleanup会清**新session的pending**，第三次同AA评分可再进入，破坏单attempt reservation；recover_cached也不能只按同id打新scope的标志。

另有评分成功staging相同窗口：`297` 在等待plugin lock之前检查material context，`343–355` 获得lock后只核attempt_id便写attempt_evaluated/cache。若锁等待期间A→B→A恢复同AA，旧请求可能把旧结果stage到新session，随后material guard才拒绝，已发生state污染。

最小修法：cleanup和staging带原expected course/session/material snapshot或不可复用的reservation ownership，并在**同一state lock内**先核材料/session一致，再改pending/evaluated/cache/recovery；不能仅增加qid比较，因为checkpoint同qid/aid均保留。旧错误可以诚实返回course_context_changed，但不能清新scope的reservation，不能让旧任务回收新attempt占用。不要通过更换已保存qid/aid或删除历史掩盖这个窗口。

受控负例：旧A任务暂停→B→A→新AA reservation→旧A清理，要求新pending/缓存/恢复标志不变；旧A在staging锁前暂停→返A同AA→放行旧锁，要求不stage旧grade且Err；正常同scope失败仍能释放其自身reservation。Main应复用现有实际answer方法及临时SQLite，不需要模型或设备。本P2已即时消息交Main，首版待修。

## 已确认的checkpoint行为

- store `586–603` 复用现有kv，key为course_teaching_progress:<course>；value有version=1及明确course_id。load校验version/course，foreign-course value拒绝。只存current_question、last_answer_evaluation及两个时间字段，不另建记忆/队列表，不改QA/interactions。
- state保存经既有set_raw的store锁与json_copy/JSON落库，不持有外部dict引用。course/session生命周期仍通过已有study_session_lock串行；退出在state锁内保存原课progress，再清session，下一课读取自己的key。
- set_course用resume_course_progress=True，start_session保持显式fresh默认False；fresh启动清held artifact并写回该课空checkpoint，所以之后返课不会复活fresh之前的quiz。无课id/超过80字符拒绝。每次切换生成新session，而artifact qid/aid保留，没有让旧session变成当前session。
- 恢复pending/evaluated题均需要saved question有qid/aid；保留attempt_evaluated和answer_evaluation_cache，恢复时仅去掉departed session的attempt_evaluation_pending。评分已完成的题不会被当新pending重做；未评分题不会以新id重复生成。
- 课程变化清active_practice_scope并递增revision，加载该课已保存material，清旧OCR vision snapshot；仍通过material_changes/submit_material_changes发布旧session失效。没有绕过现有answer/model/history/finalization的材料检查；但上述callee锁内ABA必须补。

checkpoint与state是两个既有kv写，不是跨多个key的原子事务；本轮测试证明顺序正常退出/重启，不外推任何写入间突然进程死亡都已验收。state最新保存的pending在重启时仍由既有resume_pending_question路径恢复，返课时由该课checkpoint选取。

## Status给角色看到的恢复题

Main追加的 `study_avatar_tools.py:671–725` description明确start fresh、set_course resume、status使用held quiz，不让角色因看不到题再次generate。wrapper使用已有public_current_question_payload，并提供question_state=none/pending/evaluated以及current course/session。

models `25–55` 的public投影移除answer/reference_answer/accepted_answers/key_points/rubric/solution_steps/internal_private_payload等，并显式移除answer_evaluation_cache；attempt_evaluated不直接暴露，而用公开question_state表达。状态工具不会把checkpoint私有答案/缓存发给模型。已有avatar answer使用当前snapshot核材料，held来源course不一致拒绝，带held qid/aid进真正grade entry；并未用恢复题的旧session借Native output owner。

status的course数据查询有await，它是一个读取快照而非未来调用永久授权。grade仍需重新核当前context/qid/aid；本轮不宣称status返回后学习者不能换课。任何后续新的并发保证须另有实际guard证据。

## Main测试覆盖和边界

两项新增actual方法/临时SQLite测试覆盖：A→B题不串课、B重启续用、返回A恢复原q/attempt与时间、原interaction list保持、public无答案/rubric、fresh A后再返A不复活；已评分旗标/cache/lastgrade保持、pending reservation不恢复、foreign course checkpoint拒绝、长course id拒绝。Main追加测试还核真正study_session_tool status的qid/aid/question_state及私有字段不泄露。

它们是顺序验证，尚未覆盖上述旧grading与新session同id竞争。本 Agent未执行这8项或读取用户学习DB。旧 interaction/QA不改的源码范围可确认；实际产品重启/换课后角色问答与设备层不凭这8项认领。

最新首版结论：**SOURCE REVIEW，唯一上述ABA P2待修**。其他限定范围暂未发现具体可复现阻断；修复后只精确补关闭确认，不扩大测试或全仓扫描。报告冻结。

## P2关闭确认与最后返回窗口（最新精确复核）

Main已修复原ABA：每次评分reservation分配uuid owner；cleanup在state锁内匹配attempt+owner才清pending/owner或设置recovery标记。reserve/stage/feedback/return锁内重新核expected material/session与准确owner，旧任务即使qid/aid在A→B→A后相同也不能操作新reservation。models公开投影移除pending/owner。实际start恢复分支统一清pending/owner，覆盖course checkpoint、startup及同课idle rollover，不仅saved-course分支。

本 Agent精确阅读新增两项actual answer测试：旧/新两个async任务完整set_course B→A，旧任务迟到失败后新owner/pending保留且新grade正常；staging lock acquire处替换session/owner后旧cache不写、feedback不发，已提交原history保留。Main报告这些与原守卫通过，本 Agent未执行。

复核时另发现success路径清reservation/persist新增await位于最后return guard之后，曾留下旧反馈直接UI返回窗口，已消息交Main。Main同步修复后，本 Agent只读answer entry `418–425`：cleanup/persist结束后同步再核expected context及qid/aid，变更则course_context_changed；核验后没有新的await直到Ok返回。owner已合法移除，最后判断无需要求旧owner，也无需再await一次锁引入新切换点。新增 `test_context_change_during_final_cleanup_persistence_suppresses_old_reply` 在实际persist hook后换session，要求Err且原history仍保留。

原ABA与上述最终返回窗口均 **SOURCE REVIEW CLOSED**。Main最新answer13/course8/language4通过，归Main实际方法/临时SQLite离线证据，未外推模型、Native/device/human。原发现/待修历史不改；当前限定范围无剩余已知具体阻断。仅追加本段，没有源码、测试、数据库、manifest或账本修改，没有服务/API/模型/设备操作。报告再次冻结。

## Continuous32必要量具窄审（执行前SOURCE REVIEW）

本 Agent仅只读新增 `scripts/neko_continuous_text_probe.py`、host新增 `prepare_session_tool_audit/--session-tool-audit` 及 `test_neko_summary_audit.py` 新增方法；仍只追加本报告，不运行/调用。Main manifest6 payload hashes/源更新属于SOURCE/OFFLINE pending，不由本段认领MODEL。

量具限制新 `neko-daily-continuous-text-*` 单层basename store、原目录不得存在、证据输出限定private evidence且不得覆盖；旧round、额度已尽或端口占用拒绝，不恢复/复制用户history。两已有方向PNG核已知SHA，不制新材料。第一次host建立A题，再B材料，再由实际role工具返A，停止该owned host后boot2复用同task store；不创建第二学习数据库、不删历史。

host两次均source、无voice/output-only，env NEKO_TASK_SILENT=1；WS仅text start与text输入，unexpected bytes即fail，不launch Native/meter/capture。每role只发一次，ready40s/turn110s有界，failure/timeout进入finally停当前owned host并保存原场，不新run盲重试。第二次boot是明确验收重启步骤，不是对失败场重试。场景25计数阈值在调用/boot之间检查，不能称逐外部请求的硬25限额；真实共享2000 cap和原round继续由原Sink执行。

session audit helper仅task前缀，target avatar tool bytes需完全等canonical；唯一真实返回前anchor与AST验证后仅写任务plugin-code。记录实际action/requested_course/course_id/session_id/current_question/question_state，既有public_current_question_payload已剥离答案、rubric、缓存和reservation内部标记，不记录headers/runtime/credentials。实际没有单独target_lanlan字段，requested_course就是本次课程目标；不能描述为额外角色路由证明。canonical源码不加入audit。新增测试检查unknown edited target拒绝且bytes保持、非task前缀拒绝及canonical不改，Main报告变为2项通过，本Agent未重跑；测试本身不替代即将发生的真实工具调用。

量具直接读取task DB的公开题及row/QA hashes，用前后prefix、one-question/no-grade/no-summary检查保存边界；同时每role截实际JSONL新receipt，return-course要求真实set_course target及held题，restart要求实际status held/pending。不是从历史kind推断role调用了哪个session action。其他教学模型内容仍留private证据，不发布完整学习记录。

完成标签明确为 `TRANSPORT_DB_COMPLETED_REQUIRES_REPLY_SEMANTIC_REVIEW`：需Main审实际role是否原样复述、等待、没有泄露答案/新出题，再决定MODEL层结论；DB/WS已终态不自动成为教学通过，更不是设备/human。此执行前窄审未见新的具体可复现阻断，不因全Goal其他项尚未完成拦本必要文字场。报告冻结；Main负责唯一real32、预算、进程与结果记录。

## Continuous32/33有限接续与实际回复复审

Main保留32原量具失败：误从state取图hash，而实际submitted_image在course-scoped kv并可能为data URI。32已真实生成恰一pending题且B提交成功，不能因审计错误从头重复出题/提交。当前snapshot改为按course hash取 `submitted_image:<sha256(course)>`，剥data URI头后解base64求hash；未修改学习材料。

新增 `--resume-from` 只接受private evidence中的finalized特定AssertionError断点：same store、有held/other_course、尚无returned、一turn/四SDK steps、任务provenance存在；再只读核实际B、空held、原rows hashes、QA0、reverse图SHA与原A checkpoint公开题一致，并要求6生产sourceSHA等于旧run。只有这些成立才续；branch明确跳过第一次出题和两次图片提交，继续未完成返A及停host/重启/status。不是对provider失败blind retry，也不清原32或改用户DB。这些约束是受控既有任务artifact接续，不宣称防恶意编辑报告的安全沙箱。

本 Agent只读取私有continuous33 JSON中 `held.question`、`turns.reply`、`turns.session_receipts`，没有读取DB/完整history/账本/headers/答案：

- held题为“根据图片，这三个节点之间的箭头表示什么关系？”。return-course回执显示实际set_course再status，均恢复原qid/aid且pending；回复复述同题并等待答案，没有给参考答案、判分或换题。
- restart-status实际status的session已改变，但qid/aid与题文本仍相同、pending；回复明确题没换、复述并等待。不是仅凭history推断角色使用了status。
- 第一轮开头确有 `I'll check the session state first.` 英文工具前置话语，随后中文课程确认与原题；因此本场**课程/题目接续语义通过，语言呈现PARTIAL**，不能说全程纯中文或无前置话语。第二轮中文复述正确。

Main报告33 terminal、7DB检查成立、原3rows/两PNG保持、0grade/QA/summary，DS+6（32准备+9）且无音频；这些DB/额度/进程事实归Main，本 Agent没有重查账本或读取未授权history。上述reply/实际工具回执则为本轮定向原始证据阅读。仅覆盖这道pending题的返课/重启，不外推所有课程、评分或完整A–F。

host新增“工具调用静默、无规划/英文前置句、遵从课程语言”guidance仍以原 `TUTOR_ROLE_GUIDANCE_PREFIX=Study Companion mode:` 标记。apply_tutor_role_guidance仍仅升级该managed前缀，既有persona preset或用户自有其他guidance保持；未移除此前规则。该guidance改动发生在33之后，本轮只确认SOURCE，未再次paid验证，不能借33把英文前置缺陷记为MODEL已解决。

当前窄复核未发现新的具体阻断；不用未完成全Goal或已明确记录LANG PARTIAL否定checkpoint的有限真实接续。报告再次冻结；除本段外无修改，无服务/模型/Native/设备/API/DB/账本操作。raw33与原32不发布，Main18文件候选的manifest/source及发布检查独立负责。

## 发布前空session首次grade边界（SOURCE/OFFLINE）

Main发现并修复自身reservation顺序问题：空session ensure恢复pending会合法清除departed owner，若先reserve就会清掉本次新owner。此次本 Agent只读answer entry `196–222` 与新增actual test，确认ensure先完成，再在原context同一state锁内验证expected course/session（非空原session不能迁移）、重新核qid/aid及evaluated/pending，最后赋新的uuid owner并置reserved。没有迁移旧owner或豁免session guard；ensure失败前尚未reserve。

新增 `test_empty_session_resumes_pending_quiz_before_reserving_its_first_grade` 从实际空session+held题开始，要求首次评分正常、evaluated且owner清除、恰一interaction。Main报告Root answer14全部通过，包括foreign/ensure-failure/ABA/staging/final-return原守卫。本 Agent未执行测试，仅源码精确复核，未发现此移动产生的新具体问题。

该边界 **SOURCE REVIEW CLOSED / Main OFFLINE PASS**。33只验证pending续接、未评分，不能借33认领此首次grade为MODEL通过。仅追加本段，无其他文件/DB/manifest/账本修改，无服务/API/模型/设备操作。报告再次冻结。
