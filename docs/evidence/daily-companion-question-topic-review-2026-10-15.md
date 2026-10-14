# 阶段31：同题学习身份独立审查

本轮独立审查只读 canonical `entry_tutor_answer_entries.py`、`entry_tutor_context_support.py`、`store_qa.py`、`store.py`、`test_neko_question_topic_binding.py`，随后按 Main 明确授权补读 `neko_question_topic_probe.py`。接续 contract/plan/status/blockers；只写本报告。没有启动应用、服务、浏览器、provider 或音频，没有读用户 DB、变更账本、部署或修改旧成绩。测试使用本任务临时 SQLite 与实际 entry/Store/Tracker，模型为 double。

## 已确认的实现范围

- `study_evaluate_answer` 在模型 await 前解析 binding，并在解析的 await 之后、reservation 之前重新核当前材料/课程/会话和 held qid/aid。held topic/显式 selected 为首选；topicless held 则从不可变原题的 question/reference/qid/material/course 生成 provenance。retry 不纳入 attempt_id，因此新 attempt 保留同题归属。
- supplied 显式 `_material_context` 的 material_identity 已加入 provenance；普通 literal 文本请求没有该字段，当前无关图片变化不会擅自改写文本题身份。held 路径继续用原题 origin，不用新图冒充旧题证据。
- Store 真实绑定了 `question_topic_candidates`。查询只取同课程 sessions 的 QA、同前缀 topic、精确 question/reference，以及相同 binding_key 或受限 legacy origin。`DISTINCT ... LIMIT 2` 用来判定唯一或歧义，没有先截最近100条再决定历史唯一性。歧义生成新的 question scope key，原三个历史身份不任挑、不翻译、不回写。
- `_track_learning` 和 `_record_answer_knowledge` 均优先使用 binding.topic_id；实际 QA、mastery、FSRS 因而不再从本次模型中英文 label 重新选身份。provisional question 标为 question scope，不能据此声称跨题 concept 已统一。label 可用于显示，不能作为跨语义合库证明。
- 成功后才把 binding 写入 held question 的 `internal_private_payload`；失败清 reservation、不保存题绑定。原公共 current_question 投影不暴露该 private binding。课程返回和重启复用既有 kv checkpoint，不新增表/第二套记忆。

## 初稿发现：P2 外课已知 topic 的空 family 不能授权

初稿 `_resolve_learning_topic_binding` 的 selected 分支允许 `known.course_family` 为 `None` 或空字符串的 foreign scoped ID。使用实际临时 Store/entry 复现：

1. 当前 course-A；`ensure_topic(topic_id='course-B::arrows', name='B-only runtime concept', subject='computer_science')`，既有方法默认 family 为空。
2. supplied grade 传 `selected_topic_id='course-B::arrows'`。
3. 结果没有 `course_context_changed`，模型 double 被调用一次，新增 QA topic 是 `course-A::course-B::arrows`。

这不会直接重写 B 成绩，但把外课 selection 当作本课题目归属、形成嵌套身份，违背本轮 scoped selection 的拒绝约定。已向 Main 报告：拒绝 foreign runtime scoped ID；若有 global seed 使用 `::`，应核其明确身份规则，不能把 family 缺失本身当授权。初稿测试只覆盖 unknown foreign，未覆盖已知空 family。此发现保留，修复与关闭状态在后续追加。

## 独立离线执行

使用现有 Source venv，未安装依赖：

```powershell
.\benchmarks\raw\neko-product-host\.venv\Scripts\python.exe -X utf8 -B scripts/test_neko_question_topic_binding.py
.\benchmarks\raw\neko-product-host\.venv\Scripts\python.exe -X utf8 -B scripts/test_neko_answer_material_guard.py
```

本轮实际结果：**11/11** 同题 binding 测试通过（1.551秒）；**14/14** answer material/reservation 回归通过（1.275秒）。另在 Main 增补 explicit-material case 前独立跑过原10项。临时夹具覆盖中英 model labels、held 无 topic、同题 retry、重启及 A→B→A、唯一/多历史 identity、105个无关新记录不能遮旧歧义、question/reference/image/course 改变、失败不保存 binding、lookup await 后 course 变更，以及原 ABA/staging/return 材料守卫。一个 asyncio slow-task 诊断不是测试失败。

这些通过不能消除上面未覆盖的 known-foreign P2，也不能替代实际 provider、日常 Native 语音或真人体验。没有执行新真实 probe。

## 新静音 probe 的窄审意见

量具只针对固定任务 store 的已知5 QA /3 topic checkpoint；output exclusive claim、账本沿用同 round、两次 grade 无盲重试、每次 owned host 结束后才重启，SOURCE gate/部署指纹在请求前检查。固定选择现有题干和参考答案，不制造 pending 题，不修改旧行。这仍是 Main 待执行的量具，不是本审查实际启动或模型证明。

向 Main 提交两个具体判据问题：

- 初稿 `old_qa_and_formal_rows_unchanged` 仅比较 QA 和 mastery_snapshots，没有采 interactions；应改名 QA/mastery，或显式采正式 answer_evaluate 记录再作 formal 声明。
- 初稿 `new_mastery_identity_matches` 对空增量会 `all([])==True`，应先要求本场恰有两条新增 mastery，再核其 topic。现有离线测试确实检查 tracker 表，但不能代替真实 probe 自身非空判据。

上述量具意见不涉及 Native、播放或物理可听；课程语言映射保留也不证明本场回复语言正确。

## 初稿指纹

以下是独立11/14离线批次附近读取的源 bytes（后续修复单独追加，不覆盖历史）：

| 文件 | SHA256 |
|---|---|
| entry_tutor_answer_entries.py | af7a95d3ed11295651bd42e0e63e7be613f2169f15675c5a4d0a891feede64ce |
| entry_tutor_context_support.py | 0848b0574cda5c21f4098bc1355e2456bc50bea4765a4e492820db1c089ff7b7 |
| store_qa.py | 554bd62f3304ee0833ce925b222c0118ae41895eb7ea57f52a795301fa65740f |
| store.py | 4c6a7cb0e87619200f79d5dc7c42d22782eaafac794772b9c16ffc0db5f982a3 |
| test_neko_question_topic_binding.py | facba2b1b7818beac3af5c1eb0cc55728be318d8e8687d2b694719c0e2738c09 |
| neko_question_topic_probe.py | 1f3779aeae15644f7ef75d8f3794ee23cfb0daf03584fdc3f7dd1e29cbe23084 |

本轮结论是 SOURCE/OFFLINE 的未来同题身份保护审查；旧三身份原样保留，跨题概念对应、直接 entry 语言应用、跨字段诊断一致性和整体 A–F Goal 尚未完成。

## 修复复核与冻结

Main 已修复上面的 P2：foreign scoped ID 只在 Store 明确 `source=='seed'` 且 course_family 为无课程或当前课程时允许作为 global seed 加当前课命名空间。已知 legacy runtime 即使 family 为空也被拒绝，不再生成 `course-A::course-B::arrows`。复核实际新增负例（unknown foreign、known runtime empty-family）均在模型前拒绝；global `computer_science::arrows` seed 的正例仍可用。没有依据 label 中英文去合并旧主题。

独立重跑同一命令，最终 **12/12 PASS，1.573秒**；包含 Main 新增的 global scoped seed 正例。此前14项 answer material 回归已经通过；最后 scoped-topic 变化没有修改它们的方法或材料/owner 机制，未无依据重复整批。初稿发现保留为历史，P2 在 SOURCE/OFFLINE 层关闭；本次窄审没有其他需阻断 Main 的具体 P1/P2。

量具两项意见也已精确复核关闭：snapshot 显式采 interactions，分别检查原 QA/mastery 和原 interactions；新增 mastery 要求恰+2后再核相同 ID。Main 进一步增加正式 `answer_evaluate` interaction 恰+2，以及前后 current_question 均为 `{}`，不会把 synthetic pending 当成本场真实题。以上是源码判据审查，没有启动这个 probe。其文字回复语义/语言仍需实际终态审阅，不能由计数判据自动外推。

最终独立读取的 SHA256：

| 文件 | SHA256 |
|---|---|
| entry_tutor_answer_entries.py（含最终 seed 限制） | af7a95d3ed11295651bd42e0e63e7be613f2169f15675c5a4d0a891feede64ce |
| test_neko_question_topic_binding.py（12项） | facba2b1b7818beac3af5c1eb0cc55728be318d8e8687d2b694719c0e2738c09 |
| neko_question_topic_probe.py（含 formal+2 / empty-held） | 3d25479e88711ab7f1ca32ce448971b61a703f60ba61c1df5e6431122b9f5844 |

上表是冻结读取的最终 bytes；前表 source/test 指纹在 Main 并行收口期间读取，不能据此反推缺陷初稿的 bytes。其余三个产品文件未新增变更，指纹沿前表。报告冻结交 Main，部署、真实SDK/模型与发布由 Main 决定；本审查没有新增这些层的证明，也不代表整个 Goal 完成。

Main 后续只读线索（不纳入本阶段修复或本审查独立证明）：startup/resume/session locked 未应用 effective language，应用目前在 avatar mixin；direct SDK grade 绕过 avatar，可能解释44重启后保存 English 但实际中文。该线索仍需下一阶段按实际调用链验证，不能用本次 topic 身份稳定或 language mapping 保留宣称已修语言。

## 静态资源部署门禁补审

按 Main 后续明确授权，仅补核 probe 的路径/已登记保护变换例外及 manifest 对应条目，未运行 probe 或启动宿主。最终 probe SHA256 `ed8a7cc44bebcf766ccbc29ac05edf558ee5213ebb9648b7e2548b7de8c908db`。

`item['path'].removeprefix('payload/study_companion/')` 仅去掉 payload 的固定前缀，`static/index.html` 保留 static 子目录；不再通过 `Path(...).name` 错定位到插件根 index.html。canonical source 仍逐项要求 actual SHA 等于 manifest.sha256。只有 path 恰为 `static/index.html` 且 `protected_deployed_matches is True` 才比较 `protected_deployed_sha256`；其他28项继续比较 canonical SHA，没有接受任意 mismatch 或按文件后缀放宽。

已独立只读核实当前29项 manifest 的这一既有例外：canonical index SHA `cb27a30693e5023dd167781165201712aed79e8662602594f984f2e7e2440928`，`deployed_matches:false`、`protected_deployed_matches:true`，protected SHA `b601a1f408e25f14cf55dfbb4ee1dab85ce76d4a5e791f0cc1d125706eb56239`；注明 exact protected_html + pinned capture policy + text_only=True / Windows newline 变换。probe 分别记录 source_sha256 和 deployed_sha256，不再把两者混称同 bytes。该精确门禁修正没有新 P1/P2；未改 HTML，也未把本次只读核查当作重新执行 transform 或 SourceGate。Main 报告其29项实际 gate 已过，独立本轮未重跑。冻结。

## 实际场45原件独立复核

Main 报告 exec7769 exit0 后，本审查仅只读原件 `benchmarks/raw/evidence/daily-companion-20261015-topic45.json`，独立 SHA256 **`b9f55c58bd357a8eef77afad4e80aef126e95d673c5ead01a0c0400b2ff65fa7`**。没有调用模型、重新启动 host、读取 live DB 或写派生 JSON。原件保留不变。

未依赖 report.checks 的布尔值，直接从 before/每场/after 表重算14项，结果全部成立：

- QA **5→6→7**，mastery **5→6→7**；interactions **10→11→12**，正式 kind=answer_evaluate 恰新增两条。每条正式记录的 input 和 session 均与相应新 QA 对应，两个新 QA 分属两次实际 host 的不同 session。模型结果/QA 中 verdict、score、feedback 一致。
- 原5 QA、5 mastery 和10 interactions 的完整 row 字段保持相等；原3 FSRS row 完整保留，FSRS **3→4→4**，唯一新卡的 topic 恰为两条新 QA 的 binding.topic_id。旧3 topic identity 集合没有被删除、替换或合并。
- 两条新 QA 的题干和参考答案与原题逐字相同。都绑定同一新的 `question_dc0a4746961a77478f26c1f3`，完整 key 同为 `dc0a4746961a77478f26c1f39a5b78d2188c2689faf8b1baf282c096dc98a3cd`，scope=question、source=ambiguous_history。该新 ID 不等于旧三个 topic；两场公开 selected_topic_id 与它一致，两条新 mastery 也同 ID。
- 第一场 snapshot 与第二场 before_restart 完整相等，第二场 snapshot 与最终 after_snapshot 完整相等。course 不变，current_question 前后均 `{}`，没有制造 held/pending quiz 来取得此证明。
- 前后保存的 language_by_course 保持 en-US；这是设置保留证明。两次实际回复均中文，**不能判定 direct entry 输出语言已应用 English**。

语义逐字段复核：第一场答 WEX→NUD，实际 wrong0；reply/feedback 明确这是到达 NUD 的入边，而题目要求 NUD→REZ 的出边，misconceptions 同样指出“把到达误当从此出发”。step_feedback 写入边与题目要求方向不同，没有再断言同端点对调或“起终点正好相反”；本题错误选择和参考答案解释成立。第二场答 NUD→REZ，实际 correct100，reply/feedback/step_feedback 均确认起点 NUD、终点 REZ，没有因为未逐字说“起点/终点”扣分。只认可此两题反馈，不外推所有跨字段诊断一致性。

原件 finalized=True，无 failure 字段；两个 host_exit=1 是 Main 报告的主动 terminate 结果，不能写成 child exit0。账本原件显示 DS **721→723**，Lanlan.app **70→70**，tech 未出现新支出；本审查未改账本。audio/avatar/microphone/capture/loopback 均 False，没有 Native 或设备、人体验证明。

阶段31可补充 **实际静音 SDK/模型/SQLite 的同题身份与重启保存窄链通过**。旧三身份不回写；跨题概念仍未统一，direct entry 语言应用仍未修复，整个 Goal 不因此完成。本报告再次冻结。

### 场45启动边界与后续一行防护

Main 补充45实际命令当时没有 `--text-only`：task static 为 canonical，未启动浏览器或 UI，运行时使用 `--source` / SourceGate / `NEKO_TASK_SILENT=1`，不代表曾有页面端捕获保护的设备实测。default index 的 protected transform 是另外一份部署门禁，不应移作45 task 页面证明。Main 已核两个 launcher PID 不存在、48911/48916/9234 无 listener；本审查未另启动或清理进程。

按授权精确只读核后续 probe Popen 命令新增显式 `--text-only`，与原 `--source`、固定 task store、same round 和 silent env 同时保留；没有增加 Native、voice 或重试分支。该 flag 是未来运行防护，**没有在45执行**，本轮未付费复跑。新 probe SHA256 `86e62dc8a7edd562f399bde465cc6ffb48716dbf10667bf0b5b245bb91caef4d`；45原raw SHA与结果不改。冻结。
