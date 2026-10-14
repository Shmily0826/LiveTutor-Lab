# QA<=3 焦点锚点：一次真实模型补证计划

2026-10-14，SOURCE REVIEW / MODEL PLAN，**未执行**。已完整承接四记录、summary-grade-anchor 与 summary-continuity 报告。当前阶段十二07a1fac已发布，Goal active；594/2000、app58、tech0仅引用Main状态，本轮不读或改账本。只新增本报告，无生产/测试/manifest/原报告/数据库修改；没有服务、API、模型、Native、设备、声音或新Agent。

Main已明确本任务自建隔离test-store允许测试追加，原用户daily历史绝不改。本Agent仍只准备计划，不执行追加或模型请求。不需要新材料、图片、录音、题、评分、记忆系统或复制/恢复DB。

## 这一次要证明什么

quality19证明此前八条互动可被真实总结使用；没有证明八条以外的真实QA锚点。新源码已通过fresh SQLite离线：`_build_learning_context` 的course-filtered `recent_answers[-8:]` → `llm_prompts._summary_previous_answers` → `previous_answer_records`最多3题、持久ID本地去重、current/foreign排除。新模型场只证明：**旧真实评分已被后续教师窗口挤出，模型仍通过独立QA锚点聚焦该次错答及已有下一步。** 不重复quality19或已有图片/源码说明。

聚焦更早英文错答可区分两次同类图题：历史QA1为wrong/0，QA2为wrong/10，二者都有已有next_action。模型请求不提供这两个分数、正确方向、实际答案或建议；回答若把较晚10分套给更早英文那次，应判焦点失败，不能仅看出现REZ/NUD/WEX就通过。

## 可复用store及证据状态

唯一匹配该任务前缀的已存在目录为：

`D:/CODE/project/LiveTutor-Lab/benchmarks/raw/neko-daily-speech-acceptance-20261014`

数据库为其 `N.E.K.O/plugins/study_companion/data/study_companion.db`。这是**候选隔离场**，不是原用户daily store。本轮只查看该文件与DB/WAL/SHM的文件元数据，没有打开任何数据库。DB length=4825088、mtime UTC2026-10-13T22:24:30.3605994Z；WAL mtime22:24:36.6944208Z，SHM在2026-10-14T01:12:13.2792957Z有较晚访问。DB文件时间与19结果邻近不等于逻辑内容未变，WAL尤其不能忽略；当前contents/题与状态仍需Main只读预检，不能盲复用历史ID。

既有raw19 `daily-companion-20261014-summary-continuity-quality19.json` metadata：finalized/summary_only=true，course=`daily-speech-constraints-20261014`；before29条interaction、after30条、QA均2条。QA1和QA2关联不同prior session、独立question/attempt；对应grade互动24/26。19后最近八行仍含它们和会复述旧题的teacher summary，因此当时不能直接测新anchor。保存的旧session由raw19.after_database.session_id取；**不可作为新宿主的current session硬编码**。旧raw不含当前`kv.state.current_question`完整独立快照，本报告不猜当前题或其是否为空。

本轮元数据提取以实际schema为准：interactions数组依次id/kind/input/output/metadata/created/session，QA数组id/session/topic/question/user_answer/eval/mode/time/created。不要按QA的列序读interaction，更不能直接打印数组。报告只保留索引、类型、计数和必要历史grade事实，不收录聊天全文、隐式答案、rubric或秘密。

## Main执行前硬前置（无模型调用）

1. 解析绝对store路径，确认它精确为本任务自建隔离目录、DB已存在，不能回退用户daily数据目录。通过已有SQLite helper的`mode=ro`、`PRAGMA query_only=ON`读逻辑状态；不能restore/clear/reset/copy DB，也不能只比较主DB bytes忽略WAL。
2. 与raw19.after_database逐行比较本地旧interactions/QA的原始值及顺序。记录规范JSON的SHA256：所有旧interactions、所有QA、每个QA question/user_answer/eval、以及kv.state.current_question/last_answer_evaluation/learning preferences、课程材料值。完整内容只用于本地比较，不输出文本。若course/QA/题身份不符合该隔离场来源或已有更晚新题/课程，停止这份scene；不要复原成19。若只是更多合法历史，重新计算窗口条件并记录来源，不照猜历史counts。
3. QA1仍真实属于该course，question/attempt与raw19匹配，wrong/0且next_action有效，QA2仍wrong/10；两题应属于runtime current以外的已存session。通过真正Store course-filter读取证明foreign排除，不能靠child course_family单独推断。
4. 拿到明确的当前持久course/session/题hash作为baseline；当前题未知时先核，不为了测试覆盖它。准备窗口夹具后再启动受控SDK-only宿主，启动可能形成新的合法current session，以**启动后**的current/session/question/偏好/材料另存baseline。若启动后混了新课程、改了题的身份或与预期不符，停止，不拿旧session填入请求。

## 最小中性teacher-window夹具

仅在上述预检成功、Main确认无本任务活动宿主写同一库时追加；不付费重复summary填窗口。复用实际`StudyStore.append_interaction`（canonical store.py:586），不调用generate/evaluate/模型，不调用新的SQL记忆系统。

优先计算0..8的最小k：追加后实际同course、排除runtime current的prior8中，不得含目标问题/错答/评分/反馈/next_action，也不得有复述它们的旧teacher summary。已有窗口本身符合可令k=0。当前19旧场的最稳妥方案是**8条**中性记录，使prior8完全是新夹具；仅让grade24退出而旧summary30仍留着不足以证明独立锚点使用。

参数示意（不是本Agent已执行代码）：

```python
fixture_session = verified_existing_prior_session  # 同course，非runtime current
for index in range(k):
    accepted = store.append_interaction(
        kind="concept_explain", input_text="",
        output_text="这是一条离线教师窗口夹具，仅占用历史窗口，不表示学习者完成了任何学习行为。",
        metadata={"test_fixture": "qa_anchor_teacher_window_v1",
                  "fixture_batch": fresh_batch_id, "fixture_index": index + 1,
                  "source_scope": "offline_fixture", "learner_progress": False},
        session_id=fixture_session,
        history_limit=max(before_interaction_count + k + 10, 100),
    )
    if accepted is not True:
        raise RuntimeError("fixture append not confirmed; stop without model")
```

复用raw19确认的既有prior session即可，不造新学习session记录；它必须仍通过sessions.course_id关联且与后续runtime current不同。不能把夹具写入runtime current，否则current-history会污染本次进度，并使prior8不被挤出。record metadata和content都明确offline，不伪称新老师模型回答/真实学习。已经存在同batch记录则只校验，不再次追加；中途失败保留已接受行和数量，停止，不删除回滚原历史或重跑填满。

**保留风险：** Store每10次append会按history_limit trim（store.py:197,629–639），不能沿用默认50盲加。上述limit必须覆盖全部旧行+k及新总结；模型最终append也要核当前隔离cfg.history_limit足够且不触发丢旧行。若无法保证，本场不执行；不要为试验提高或改原用户配置。所有原rows严格前缀相等、所有QA hash相等、kv题/材料/偏好hash相等应在fixture后再次通过。模型前interaction数恰为N+k，无新增question_generate/answer_evaluate/QA；旧prefix不可改变。

## 一次准确SDK调用

沿现有LabClient的真实`POST /runs`→poll→JSON export，不借模型tool调度或Native，不启用narration。public entry为`study_summarize_session`，schema只有可选`focus`（entry_tutor_summary_entries.py:90–106）；不要传course_id/session_id/language/private context伪造当前范围。Main宿主用实际current及cfg课程语言。

```python
result = LabClient().call(
    "study_summarize_session",
    {"focus": "只回顾更早那次我用英文回答左右箭头方向的题：用两句话说明我当时的错答、已有判分和下一步；明确这是此前的记录，忽略较晚那次中文回答及后来的源码讨论，不出新题。"},
    timeout=120,
)
```

入口timeout85s，client120s是观测上限，不是新retry许可。现有`neko_summary_semantics_probe.py --summary-only`会使用固定的泛复盘focus并输出全部response，**不能直接当这个焦点场的runner**；Main需复用其隔离store/原record完整性与owned cleanup办法，改用上述参数及metadata-only输出。provider限流/拒绝/degraded/timeout立即停止，先检查已有run是否终态，不创建第二个run盲重试。预期只一项真实summary模型操作，不生成题/评分/源码解释；实际请求数由Main账本和gateway证据记，不预设修复/structured内部调用一定只有一次。无需新CONNECT。

## 必须记录的只读证明

- source/deployed runtime/llm_prompts/prompt_templates fingerprint。本轮canonical llm_prompts SHA256=`2f0d9a2113032f1c77f3d1d665031d11c6ebf6db116dd149f5297e6efcda2e24`、prompt_templates=`9905fd448ef78a3826bcefce6f3fa1d94af33234d379070603ffbe92c31ca721`；启动现场须再核，不能用历史19指纹。
- 实际builder输入来自Store/course/current；current history有效空、seed不携带旧错答；prior8数/ids/kinds与teacher fixture标记，target旧题/答案/eval/next_action均不在其中。实际**最终发出的prompt投影**previous_answer_records为1..3条，含QA1错答/0分/既有next_action，prior session同课且非current；不能只离线重建理论context而没检查真实调用投影。
- 在本地用持久id/attempt关联目标与QA投影，日志只记counts/roles/scopes与内容hash。prompt中没有opaque QA/question/attempt/session/topic IDs、hidden answer/reference_answer/rubric、图像/hash/private material keys、整个course_learning_state或foreign QA。当前材料不进入这个文字summary的vision输入。
- run_id、entry、真实入参hash、started/completed、终态、degraded/diagnostic、数据字段存在、summary/next_actions哈希，实际DB新增summary row的output与返回summary相等（按实际reply/payload结构核，不能拿单一布尔当语义PASS）。
- 模型后N+k+1条interaction（若没有其它必要合法调用），原N条前缀完全相等，k夹具仍明确保留，QA整表hash/count与题/偏好/材料baseline不变。host正常session生命周期变化单列，不能拿启动的新session与19saved session不等判数据丢失，也不能掩盖summary过程中course/session变化。只清本次owned宿主进程，不触碰别的窗口。

## PASS / FAIL 分层

SOURCE/OFFLINE入参检查通过不等于MODEL语义通过。MODEL窄场PASS应同时满足：正确聚焦更早英文错答和0分（没有借较晚10分）、依据已有QA说明错误并给出其已有next_action、明确此前而非本次刚做；不索要已经保存的题/答案、不称老师解释或夹具为学习者已经掌握、不插入较晚源码课/主动新题。要求两句且summary正文含实际下一步，不能只在next_actions里出现。只出现正确模块顺序或所有结构checks=true仍不充分。

模型返回degraded/unknown、要求补题、混0/10或不同attempt、错误说本次完成/掌握、只复述fixture、漏已有下一步、将所有无关QA一起总结，均记录具体FAIL/PARTIAL，不自动重试。如果prompt实际上没有anchor、prior8仍包含目标证据或state seed泄露目标，则场景无效/准备失败，不能把模型答对当新anchor证明。

这个场最多新增“真实模型读取实际graded QA，在明确离线中性teacher-window夹具下的焦点使用”证据；它不是自然连续学习多轮/human、Native/tool choice、语音或设备证明。19限定历史接续PASS及18失败原样保留。若store漂移前置失败，登记为准备条件未满足并转Main其他C/D工作，不恢复库、不阻塞整个Goal。计划已冻结，执行、预算、宿主与最终语义审阅均由Main负责。
