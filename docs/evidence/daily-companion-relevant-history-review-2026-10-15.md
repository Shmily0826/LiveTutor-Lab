# 阶段44：相关旧历史与跨题身份的只读设计审查

日期：2026-10-15。已接续当前contract/plan/status/blockers；Main记录831/78/0、无live场。本Agent只读canonical源码与必要callee/test名称，没有运行测试、服务、模型、设备或用户DB，没有改产品、manifest、共享记录或账本。本文件是最小实施建议，不是新检索已交付的证据。

## 结论

应先复用现有SQLite的**同课、确证题/概念ID定向QA查询**，把有据的旧错答与后续尝试作为独立、总量有界的model context。不能只扩大最近history窗口，不能把检索弱词排名当稳定concept ID，也不能依据中英标签猜合旧记录。现有question binding已解决同题未来身份稳定的一部分，不能外推为跨题同概念全部解决。

最小可交付范围：已有trusted selected topic / held binding可定向找到的旧成绩，不受最近30 interaction或100 QA窗口遮蔽；在实际prompt中看到有限公开证据；模型能正确提及先前错误/后续纠正，且不声称发生于当前session。不另建memory库、不更新旧QA/掌握度、不推断长期偏好。

## 当前源码的具体缺口

| 源码 | 确认事实及影响 |
|---|---|
| `entry_tutor_context_support.py:649–659` | 当前session取15–30条（summary100）；同课先取最近30，再在Python排除当前session取8。当前session已有≥30条时，旧session行被LIMIT先挤掉，结果可全空；应在SQL中先排除session再LIMIT。 |
| 同文件 `290–299` | `_course_learning_state`只从最近100 QA建立topic_ids，再用这组ID取weak/review；近100之外的概念不只失去原答，连候选集合也可能消失。recent_answers8不是相关检索。 |
| `store.py:1337–1369` | `list_interactions`只有session/course + ID倒序LIMIT，没有题/概念检索；session优先于course参数，不能通过同时传两者得到交集。 |
| `store.py:605–658` | 旧interaction未必仍存在：append每累计10次触发按传入history_limit的全局DELETE。这里是已存在源码行为，不是本轮新改动；未读实际DB，不能断言某用户已丢行，但不能承诺找回已删history。正式QA应是相关已评分历史的主来源。停止自动删除是否需修由Main按原“保留历史”契约处理，不能为检索测试删旧数据。 |
| `store_qa.py:168–196` | 已有按精确topic_id的有界QA查询，可复用思路和索引；当前没有course/session join过滤，且`SELECT *`会读完整question/answer/private payload。它不宜直接原样注入prompt。 |
| `store_qa.py:199–228` | `question_topic_candidates`查全库范围内的精确题/参考/binding及course/material，LIMIT2是证明身份歧义，不是教学历史检索。不能改为“最新一条即正确身份”。 |
| `llm_prompts.py:323–347` | explain会用recent_interactions、prior course和recent_answers，但只是窗口内公开投影；不存在按当前题/概念补找更早记录。新增context字段若不接prompt allowlist/renderer会被丢掉。 |
| 同文件 `200–257` | 模型context有token预算及多档压缩，最终可变成截断excerpt；即使context对象含相关旧行，也不证明实际发给模型时还存在。需验证最终messages，不只断言Store返回。 |

旧interaction若已物理trim，不能复原“用户当时的全部追问/临时要求”；现有QA中仍可有正式答案、成绩与反馈，这两种证据须区分。当前不是全局阻塞，可先完成QA有据子集。

## 身份链：已有稳定路径与保留范围

`entry_tutor_answer_entries.py:325–344`优先held question的selected_topic_id/topic_id/**topic自由标签**，再取client selected。`_resolve_learning_topic_binding:23–77`把传入selected作为explicit course-scoped身份；若无selected，才用private binding或精确同题历史唯一candidate，歧义/无历史生成question hash ID。

因此：

- 已有真正stable selected ID可跨题保持。`entry_tutor_question_entries.py:630–635`会把context中的selected ID留在新题，后续记录沿用；`_track_learning:1044–1054`、`_record_answer_knowledge:1120–1139`优先binding/selected ID并加course scope。
- 没有trusted ID的同题provisional binding只证明同题/同参考/同材料身份。question或held qid改变，不能推断还是同概念；这是保守正确的边界，不应为合并掌握度删除provenance。
- held自由topic标签也会进入selected路径；标签可能是模型产生的中英文名称，跨题仍可能分成不同ID。不能把这个路径一律称为知识库已确认concept。
- `knowledge_tracker._resolve_topic_id:1386–1400`遇到`::`直接保留，后面的name canonical lookup不会再替它合并。检索不应偷偷改此行为或回写历史。
- `knowledge_graph_guidance.match_topics:395+`保留公共模糊rank；specific_score与完整name/alias/Latin词资格是指导相关性证据，不是任意旧标签之间的翻译等价证明。rank第一名≠唯一稳定身份。

最小身份政策：确证held binding / learner-selected existing ID优先；没有它时只对**同课允许范围内、唯一已知的完整name/alias匹配**考虑未来绑定，含明确source与scope。弱词、多候选、未见过的翻译标签或foreign runtime ID拒绝自动合并，保留question scope。global seed需沿现有known-source/course-family保护映射为本课ID；绝不把别课runtime概念借过来。

这轮可先只交付确证ID相关历史；若另修未来跨题绑定，单独验新题确实共用已有concept ID，而非只在返回label上相同。原有多个历史ID不迁移、不猜合、不重算旧成绩。

## 最小SQLite/上下文对接方案（待Main实施）

1. **捕获请求身份。** 使用入口已捕获的expected course/session/material和held binding/qid，不在多次await后改读live当前课。选择最多1个exact held qid及至多几个确证topic ID；没有资格返回空相关集，不能取全库最新行兜底。
2. **只读有界查询。** 在现有Store增加/扩展一个有界QA读取方法，`qa_records JOIN sessions ON session_id`并精确course；topic使用等值/有限IN，qid可由已有JSON字段严格提取。SQL先过滤再LIMIT，固定小上限（例如总6条），不拉5000全库再Python模糊找。已有`idx_qa_topic_created(topic_id, created_at DESC, id DESC)`可复用；必要索引/性能测量是Main后续实现事项，无需新DB或嵌入模型。
3. **错误与纠正一起呈现。** 优先当前held题的旧formal记录，再同concept相关旧题。不能只取最新correct而抹掉wrong，也不能只取陈旧wrong而忽略后来正确；可为同qid保留一条旧wrong/partial和最新合法attempt，按时间呈现，余量给其他确证同concept题。retry源码只返回previous_attempt_id、保存同qid和新attempt，并非完整持久化纠正边；无显式lineage时只能说“同题后一次尝试”，不编造某次纠正引用关系。
4. **公开DTO，不传原JSON。** 仅record id、source scope/时间、topic ID/label、qid/attempt、公开题干、learner answer、verdict/score、有限feedback/misconception/next-step；每项有字符上限、总条数/总字数上限。排除rubric、private reference、internal_private_payload、图片base64、origin/hash/keys/路径/保留字段。SQL内部可以核private provenance，但不能因此把它送进教学文本或UI。
5. **单独命名证据范围。** 例如context中的`relevant_previous_answers`（仅建议名，当前不存在），每行明确current/previous-session。同课旧图/旧源码问题即使concept相同，也只是旧学习证据，不能当当前材料事实。已换材料的事实解释仍以本次材料工具为准；不可用旧正确答案覆盖新材料。
6. **接入最终prompt。** 新字段需进入现有allowlist、explain recent-context renderer及相关structured操作的预算管理；放在必要当前source/question/answer之后、无关course概览之前，避免只在context存了却因压缩消失。保留grade required三元组与summary immutable current-session界线，旧证据不得冒充新进度。最终message内保留具体公开证据，而不是仅`retrieved_count=6`。
7. **不升级偏好。** 历史只作学习事实。不能从旧answer/input里的“这次中文/别出题”等推断长期language、brief或proactive偏好。当前显式偏好仍由现有load_preferences/turn override路径决定；历史文本是数据，不是新的系统指令。
8. **每await后保持原guard。** 取topic/QA/构建context期间换课、换session或需材料identity的入口变更，沿既有MaterialContextChanged/finalizer拒绝，不能让旧检索写新课程seed。检索本身不append interaction、不改QA/mastery/FSRS/偏好，也不把用户历史搬进第二套Store。

`list_qa_records_for_topic`当前不核course，建议扩为上述安全方法或由严格callee确保scope并在SQL交叉核course；仅ID有本课前缀不足以证明一条历史row确实来自本课session。无需全文LIKE或以模型生成词扫描整库。

## 最小证据场景（本轮未运行）

- 在临时SQLite先存确证concept的一次wrong及同qid后续correct，再放>100条无关QA和>30条当前session interaction。查询仍定向返回旧wrong+correct，旧session过滤在LIMIT前生效，模型prompt保留两条完整公开事实。
- 同课不同题共用真实selected concept ID；换输出语言不新建concept。自由中英标签、同名不同课、两个candidate、弱词（如连接/从）不猜合，不重写旧三identity。
- 只有同题provisional scope时不把另一题硬绑；相同qid但reference/material provenance不符不能凭旧反馈宣布当前正确。已重启不同session的同题可按确证qid/binding取旧attempt，明确prior活动。
- 恶意/异常元数据（跨课session配本课topic前缀、非法JSON、重复/缺attempt、过长反馈）、private rubric/base64/key sentinel都不越界或泄漏。原Store行hash、QA/mastery/FSRS/偏好前后不变。
- 查询或prompt组装await期间换课/换材料，模型不收到新旧混合context；summary仍区分immutable current history与related prior事实。
- 最终messages under token budget仍有相关旧错答及最新尝试，当前题/答案/材料不被历史挤掉；旧“这次语言”不改变显式偏好。仅Store返回/计数测试不足。
- 离线满足后，Main若安排最小真实模型场，应审实际prompt中的锚点和真实回复是否承接旧错误/纠正；不重新评分、不增加QA来制造“使用过历史”的证据。SOURCE/OFFLINE、模型、Native/physical/human分别记。

## 只读审查基线

| canonical文件 | 本轮初读SHA256 |
|---|---|
| `entry_tutor_context_support.py` | `0848b0574cda5c21f4098bc1355e2456bc50bea4765a4e492820db1c089ff7b7` |
| `entry_tutor_answer_entries.py` | `af7a95d3ed11295651bd42e0e63e7be613f2169f15675c5a4d0a891feede64ce` |
| `store_qa.py` | `554bd62f3304ee0833ce925b222c0118ae41895eb7ea57f52a795301fa65740f` |
| `knowledge_graph_guidance.py` | `31b103c512eca8c5ac2eeea8d50db6c63cb213ab74e81bf0ae43421192420f89` |
| `llm_prompts.py` | `2f0d9a2113032f1c77f3d1d665031d11c6ebf6db116dd149f5297e6efcda2e24` |
| `knowledge_tracker.py` | `15a5ff73d9bae24a220bc89e01204115fef8b30fba2a07af9eb3f327afbae970` |

既有question binding测试覆盖同题重启/歧义/材料/课隔离等，不能作为新增“更早相关历史已进入模型”的证据。本报告冻结为设计意见，没有新功能通过或全Goal完成结论。

## Main阶段44收窄方案的追加设计意见（未实现验收）

Main决定本轮先修保留与相关读取：取消学习历史自动trim；prior查询在SQL LIMIT前排除当前session；课程topic_ids来自同课QA元数据distinct、上限5000；explain只用现有confirmed selected/guidance ID与同课eligible映射读取最多4条公开QA，替换默认recent answers而非叠加。无trusted ID的跨题别名/语言身份不本轮猜修，属于明确后续范围。此收窄能独立交付有据子集，不等于相关记忆或跨题身份全解决。

需在实现/定向证据中守住四处：

1. **旧错答必须有后续状态边界。** “最新wrong1 + concept最新3”仍可能丢纠正：旧qid A错后已正确，但同concept B/C/D等新题把A的correct挤出最新3，最终只保留A的wrong。最小为选中的wrong按同qid/确证binding补最新attempt（占总4条预算），否则只能明确叫historical曾错，不得推断尚未纠正。优先实际wrong→later-correct证据对，而非一概旧wrong置顶后丢其闭环。
2. **总4行仍需字符/字段限额。** 题、user_answer、feedback均可能极长；应在公开DTO投影后按行/总量限额，不原样送question/eval_result JSON字符串。最终prompt确实替换默认5条recent answers、不同时叠加两组；private字段与临时偏好不因旧数据检索进prompt。
3. **5000是界限。** distinct取ID需确定顺序与SQL course过滤；不得因上限声称“全部旧概念都可见”。已明确selected的精确ID仍可单独做course/source资格核验，不能因为未在前5000就任意取他课/全库latest兜底。读全课QA正文或Python加载全历史再distinct不符合元数据/有界目标。
4. **当前session与保留语义不回退。** exclude只对prior查询使用，summary immutable current-session路径仍沿原guard；自动learning retention停止不意味着清空旧行重建，也不授权调用显式purge。QA/mastery/review保留变更应限这些自动hook，避免误改其他资源清理接口。旧数据已被历史版本删掉的部分仍无法凭此恢复。

现阶段仍只有SOURCE/DESIGN审查，没有执行测试、DB或模型。Main冻结后才能复核实现与实际prompt证据。

## 实现初次冻结复审：10项通过；公开投影新增P2

Main冻结的四overlay与测试指纹实读一致：

| 文件 | SHA256 |
|---|---|
| `store.py` | `d3b54be66ff5106ebf0dd5427de69151dc5f12924589a97c57623fee9119a79b` |
| `store_qa.py` | `c9723f62a4d8e8ec326d3ba0dd610da4bddc64d6f62a3d6c9067f420fab298dc` |
| `entry_tutor_context_support.py` | `ff426b5fd9918be23fc2c8ed79a61a986c2629bc993c700999030a7c2c196d8c` |
| `llm_prompts.py` | `5f5c1457664fab9fa66b7252dc99eb5b5d1d68ac2343c8c07715c448133c0e27` |
| `scripts/test_neko_relevant_answer_history.py` | `0f7a2fcfc45901d9c5c8ad81068bf9a30540552fb5995d69ff99256b11bcd646` |

独立运行Source venv `python -X utf8 -B scripts/test_neko_relevant_answer_history.py`：**10 tests PASS，1.338s**。只用新临时SQLite/实际Store、context与最终messages，没有模型、服务、设备或用户DB。Main另报course8/binding12/answer material14通过，本Agent未重复这些套件。

本版已把SQL exclude放在LIMIT前，自动interaction DELETE删除；append-only hook只保留标识符/order/参数验证；同课topic distinct稳定排序且最多5000。相关历史优先最新wrong、同qid且同private binding key的最新attempt，之后填concept最近记录，按id去重≤4；同qid异binding过滤。10项实际证明旧wrong及其correct不会被>100无关QA或同concept其他题挤掉、foreign session不能借本课topic前缀进来、原history_limit=2也不自动清interaction/QA，以及实际prompt包含所选公开锚点。

### P2：将非字符串历史字段str化，绕过私有字段过滤

`_relevant_answer_records` 的 `bounded(value, limit)` 使用 `str(value or "")`。SQLite历史JSON字段未保证question.question/feedback为字符串，若其为dict，helper会把嵌套字段值转成普通文本。后续 `_relevant_answer_items` 看到已是字符串便允许，递归private-key sanitizer也无法再识别内部键。

独立stdin负例复用本次实际临时SQLite/context/prompt fixture：

- 保存一条同课同topic合法QA外壳，但question.question为 `{"answer":"PRIVATE_NESTED_QUESTION"}`。
- evaluation.feedback为 `{"api_key":"PRIVATE_NESTED_FEEDBACK"}`。
- 实际调用context和最终 `build_concept_explain_messages`。

结果：`nested_question_stringified_into_prompt=True`、`nested_feedback_stringified_into_prompt=True`，相关行数1。哨兵是本任务合成常量，不是读取真实密钥；没有改任何源码/测试文件或真实DB。

最小修法：文本公开字段只接收str，否则置空/跳过异常行；数值score维持严格int/float非bool及0..100规则。不要把dict/list转成repr。需同时留意fallback：相关读失败/空集合时renderer仍用旧5条recent_course，旧fallback也有题干str化/feedback对象透传，不能通过“异常就返回[]”把同一畸形字段绕回旧路径。宜统一复用安全公开投影，再保留lesson可用，不需要扩大为全库数据清理或改旧QA。

目前这个P2尚未关闭；10项并不证明畸形历史不会泄露私有字段。实际课程/材料await guard、无法恢复已删历史、自由标签跨题与5000上限范围继续保留；尚未部署/模型验证。

## P2修后精确关闭复审

实读修后指纹：

- context support：`23e9ca838d18f74aaf76ce59e87089f12f5d09d75810b839f862e47dd4d4de4f`
- prompts：`36267f1fca0d7a8168890a2d6994f8da4f91c37db199e022bbe2d1343b1bd36d`
- relevant history test：`b40c2d55326da1197e94132cd1db7f941decc1fb74cd847ed0ba0fd416241425`

store/store_qa维持前述冻结版本，此轮只核公开投影P2与必要新测试，不重复未变语音/评分套件。

独立完整运行相同新history套件：**12 tests PASS，1.394s**。新负例用实际临时Store存入dict题干/feedback哨兵，分别经过confirmed selected、unconfirmed fallback、相关读取失败fallback的最终messages，私有哨兵均未出现；合法learner answer与数值score42保留。另覆盖直接prompt非文本qid/topic/answer/verdict以及bool/NaN score。

修法与证据一致：context的bounded仅接受str；renderer相关与旧recent_course fallback共用 `_relevant_answer_items`，同时支持公开evaluation及旧eval_result输入，但只投影明确文本字段；非文本变空、strict数值score保留。没有把私有结构转成repr，也没有靠返回空集合再绕到旧不安全投影。

本P2在SOURCE/OFFLINE范围关闭，本次精确增量未发现其他具体阻断。原发现及10项不足的记录保留。尚未部署/真实模型，不据12项宣称用户日常已利用长期历史；5000界限、既有历史已删部分不可恢复、无trusted ID跨题别名和相关记录实际被模型用于回答仍分别保留后续证据要求。报告冻结；未修改产品、共享记录、DB或原场51。

## 部署后静音场52量具初次只读审查

Main报告已备份并精确部署四文件，product manifest SHA `b9bd7a0af3b17089d35d939b1c6e6073c89c1a69cb5cacdd48ae9ab189b0d27f`，SourceGate通过；将new12测试源码仅在内存改指default后、实读四模块__file__确认再执行12 PASS(1.349s)。这些部署/测试是Main执行，本Agent本段没有另读用户库或运行probe/API/host/设备。

只读 `scripts/neko_relevant_history_probe.py` 初稿及精确audit/cleanup/LabClient callee，确认：

- 固定NEW owned store52、输出exclusive创建、存在即拒；合成2旧wrong/correct+7同概念+105noise，有明确synthetic标记，不冒真人学习史。snapshot只读该固定task库。
- 启动前核原round/2000、app null、tech0与余量、占用端口及SourceGate/product源hash；worker TASK_SILENT、source/text-only，无浏览器/Native/声音路径，单次entry、观察既有run不重发POST。
- audit只改launcher创建的task plugin gateway副本：先exact canonical bytes、单anchor、AST，再在concept_explain的已有messages构建后/原transport调用前记录。现有gateway已有Path/json import。没有改prompt、endpoint、credential或默认部署模块。
- 检查actual explain messages里wrong/correct两条锚点和private reference sentinel不出现；QA全raw hash保持，未通过新增grade伪造记忆使用。

### 量具P2：cleanup只凭数字PID重新取得owner

初稿 `stop_owned` 先poll，再 `psutil.Process(process.pid)` 采children并terminate，没有保存/核验Popen启动creationtime。原root在poll与重新取Process之间退出且PID复用，会把新foreign进程及其children当作本次owner；pidfile也仅以数字PID集合匹配unlink。poll若已结束还直接return，不能据此证明无本次遗留child。

这与本Goal阶段15已建立的process ownership约定不一致。最小修法是复用现有 `process_creation_time(pid)` / `stop_owned_tree(record)`（记录包含pid与created_at）或等价same-owner验证；不把共享pidfile或PID数字当控制权。新量具本轮未运行，不能拿旧probe运行成功覆盖这个cleanup实现。

另需明确判据范围：`nonempty_reply`和prompt锚点/hash是结构候选检查；它们不证明模型真的指出“过去把WEX→NUD读成NUD→WEX，后来已纠正”。建议report显式semantic_review=PENDING，实际终态后由Main/独立读语义判定，不能exit0就标recall PASS，也不需用关键词凑成假人工验收。

当前量具仍待上述ownership P2关闭；本段只静态审查，没有运行probe、服务或模型。

## 静音probe cleanup / 语义标识的精确closure

修后 `scripts/neko_relevant_history_probe.py` 实读SHA：`55a5819db5d4854a0629d42e823ad413d5a217cff3ed2c374b134b4107db6bcc`。

只读增量与既有callee确认：已删除新写的 `stop_owned` 和数字PID文件unlink；Popen后立即保存kernel creationtime，无身份则失败保留证据。ready之后只在原root仍属已记录实例时补充其已观察child身份。finally对完整ownership记录复用既有 `stop_owned_tree`，其中每个pid按记录creationtime核准，不咨询共享PID文件；因此即使root先退出，已登记的child仍分别校验/清理。没有扩大为全系统同名进程扫描。

原发现是静态owner-contract风险，本Agent未执行真实PID复用触发；不把它写成已发生误杀。Main另执行既有真实parent/child+foreign创建时间保护定向1项PASS(0.604s)，属Main执行，本Agent本轮没有再启动进程测试。

report新增 `semantic_review="PENDING; nonempty reply and prompt checks are structural evidence only"`。脚本exit仅表达机械判据，实际回复是否准确使用wrong→correction需终态后读语义，不能据nonempty或exit0认领recall/human PASS。之前单场、隔离库、四call配额、原round不重置、silent/text-only、audit只改task gateway的界线未变。

该精确增量未见残留具体阻断；ownership P2在SOURCE/既有helper证据范围关闭。probe仍未由本Agent运行，不预判其真实模型结果，也不扩展为所有崩溃/orphan情形已验。报告本段冻结，不修改代码、账本、共享记录或用户数据。

## 唯一静音场52：原件与实际模型语义独立复核

Main执行唯一场exec78416 terminal/exit0。本Agent只读原 `benchmarks/raw/evidence/daily-companion-relevant-history52.json`，实读SHA为 `c296d1050ecc890670db82dcdd19c79c3793d7e6974f10984bb3b79d3aacf63d`，与Main提供一致；没有重跑probe/API/模型/host、没有读实际DB或改原JSON。

### 实际输入与数据库保持

原件明确fixture为synthetic saved QA、真实模型回复，**不是人类旧答题史**。before/after snapshot均114 QA，同raw-row集合SHA：

`0db81ffd05e32aeb33381df949fc6e6da756b9fce4fcaee62f7ab92d079b1dbf`

这两项是已审量具对实际task SQLite读取后记录的值，本Agent在本轮不另连DB重算。interactions从0到1；新增唯一行为为concept_explain，input_text为本次询问，output_text等于模型实际reply。没有新增评分或QA来凑回忆证据。

result非degraded、semantic_status=available，knowledge_guidance_source=semantic_route，focus为 `relevant-history-fixture52::arrows`。实际copied gateway audit记录恰一个concept_explain messages对象，system/user角色齐全；不是仅返回的context计数。

### 实发prompt真的保留旧错误与后续尝试

独立读取actual_messages中的公开history段：`answer_history_source=confirmed_concept`，只有4个record，ID为1、2、8、9，topic均为本课arrows。

- record1，qid `original-arrow`：`我把WEX到NUD读成NUD到WEX。`，wrong/0。
- record2，同qid：`我已改正：箭头尖在NUD，所以是WEX到NUD。`，correct/100。
- record8/9为后来同concept其他题，correct/100。

实际prompt包含前两条原文，没有末尾无关变量练习105条中的最新marker，没有 `PRIVATE_REFERENCE_SENTINEL` 或binding私有对象。由于该prompt公开投影不包含private key，本轮“相同binding”取回资格由先前实际Store离线测试与当前源码查询提供；本次模型audit独立确认的是同qid公开闭环和最终实际供给，不能从公开prompt反推出隐藏private key内容。

### 人工读语义：特定回忆窄通过，覆盖范围诚实性仍PARTIAL

真实reply为：

> 你曾把 WEX 到 NUD 的箭头读反成 NUD 到 WEX，后来已改正为“箭头尖在 NUD，所以是 WEX 到 NUD”，之后的记录也显示方向已纠正。除此之外没有更早的误读记录。

前句准确区分旧wrong与后来correct，方向、节点、时间关系都有实际prompt证据；不是nonempty就通过。两句中文、未出题、未杜撰模块调用职责，特定synthetic历史取回→模型使用→纠正接续窄链可记真实模型PASS。

末句“除此之外没有更早的误读记录”是对更大历史范围的否定断言。模型只收到4条有限、定向取回证据；即使这次合成fixture碰巧没有另一条wrong，也不能由此声称全部历史已检查、没有更早错误。应表述“本次取回记录中只看到上述误读”或保留未知；当前整体回答诚实范围仍PARTIAL。原raw的semantic_review=PENDING不回写；本段是独立后续语义判断，不把机械exit0升级成全功能/human验收。

未来最小方向是让模型明确知道related-history只是有界片段，禁止从未取到推断不存在；这不是要求扩大SQL到整库或付费重跑当前原场。本轮不实施、不修改prompt。

### 额度、清理与分层

原件同round/原budget保持，DeepSeek831→833（+2），app78不变、tech预算0；audio/capture/microphone/loopback/avatar均False。finalized=True，failure与cleanup_error缺省即无记录异常，host_exit=1与Main主动停止相符，不把exit1当模型运行失败。

Main另核5条ownership记录对应存活集合为空、48911/48916/9234无listener；这是Main进程/端口检查，本Agent本轮没有执行live进程检查。四生产源码无后续更改由Main持有部署记录。

最终本场分层：**有界相关历史实际进入模型并被用于特定错误/纠正回忆：真实模型窄PASS；全历史不存在断言：PARTIAL；真人日常历史、语音/Native、physical与human：未由本场验证。** 原件不改、不另发请求；跨题自由别名、5000范围与已删历史不可恢复等其余C工作仍保留。
