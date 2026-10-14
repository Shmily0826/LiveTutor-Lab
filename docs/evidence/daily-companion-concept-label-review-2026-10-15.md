# 阶段45：自由概念标签的安全复用设计审查

日期：2026-10-15。已接续四份当前记录与阶段44报告；当前Main记录833/78/0、无live场。本Agent只读answer resolver、已知topic/schema/QA调用点，不运行测试/DB/模型/host/设备，不修改产品/manifest/共享记录或旧历史。本文件只给设计与必要fixture，不是新实现通过。

## 当前问题与可交付方向

现 `entry_tutor_answer_entries.py:325–344` 将held题的 `selected_topic_id`、`topic_id`、**自由topic字符串**统称selected_topic_id。resolver随后把它当explicit ID加course前缀。模型只换了语言/label，也可能使不同题在同课产生不同concept ID；这不是已有同题private binding能全解决的范围。

Main拟移除自由topic→selected ID提升，只保留真正selected/topic ID及显式client路径；新增对**已有catalog完整name/aliases**的唯一匹配，复用canonical scoped ID，而不猜译、不模糊合并、不改历史。该方向适合独立交付：未来新题在确有共同catalog依据时共用concept；无法证明同概念时维持question scope。

## 身份优先级必须保留

1. **已有same-key private binding先于自由label。** 只要binding version/key/course范围仍有效，换label、换回答语言不应改其topic ID，也不应为找“更好名称”重查catalog。原held provenance/material/foreign guard保留。
2. **显式stable ID与已有binding冲突时要明确。** 已有selected ID行为可保持，但不能在同一held question上借自由label或新的model ID静默重绑旧记录。显式用户重新分类若不是本轮授权行为，应拒绝或保留原绑定，不能把它隐藏在自动匹配里。字段名`topic_id`本身不等于known catalog资格；自动复用要实际核存在/来源/course资格，显式client行为另记来源。
3. **同题历史唯一/歧义决定仍有优先级。** 现 `question_topic_candidates` 查全库精确题/参考/binding/material并LIMIT2，不能变为任意最近一条。旧同题有唯一身份就复用，歧义则维持原保守provisional路径；不应借恰好变过的label给旧歧义题挑一个“第一名”。新label fallback放在没有可复用同题依据的分支。
4. **跨题匹配只增加未来引用。** 相同完整name或已存翻译alias可以指向一个现有canonical ID；它不是旧多个ID的等价合并证明。原多个QA/mastery/FSRS身份及原row hash不回写，不能重算过去掌握度来让图看起来统一。

## SQL与catalog资格的最小安全条件

- 先筛course资格：当前前缀ID必须确有本课session所属QA，而不是只看字符串前缀；别课session即使保存了本课前缀topic也不算本课拥有。原有private binding的历史引用与自动新label资格是两件事。
- raw seed必须有实际known `source='seed'` 且course_family为空或本课的既有允许值；明确foreign family排除。不能把其他runtime namespace当全局seed，不能借label相同导入外课记录。
- 只读取topics的name/aliases/source/course_family/id与QA的topic/session元数据。`EXISTS`或去重topic子查询足够，不读QA正文、参考答案或rubric来猜语义，不用全库body扫描或另建翻译/embedding系统。
- “精确”应有明确字符串规则：首尾空白处理可以与现有入口一致，但不要移除中间标点/大小写/下划线去猜代码概念相同，不用substring/LIKE fragments替代完整name/alias等值。若保留ASCII大小写不敏感，须明确这是规则并保护同名区分；不能称无条件逐字精确。
- alias列是JSON文本：核 `json_valid`、JSON array类型，alias元素须text。数值、对象、非法JSON不能str化或当alias；不因一条坏catalog行让正常答题崩溃。SQL标签使用绑定参数，不拼入SQL正文。
- **canonical去重在LIMIT2之前。** raw seed `arrows`与本课mirror `A::arrows`可能同指 `A::arrows`，一个topic多alias也会多行。若先LIMIT2，再Python去重，会吞掉第三行真正不同canonical，错误认唯一。应在资格和exact匹配后映射canonical、DISTINCT canonical，再LIMIT2；0/1/≥2分别未匹配/唯一/歧义。
- canonical映射沿现有course prefix约定，不能double-prefix本课ID；当mirror存在时保持其合法已知元数据，不为自动匹配覆盖name/source/course_family。整个lookup只读。
- 现入口resolve后还有material/current检查及reservation owner守卫。新查询增加await后这些guard必须继续生效；查询期间换课/材料不可把旧catalog结果写新题，不借“只是metadata查询”绕过原检查。

## 必要的最小fixture（本轮未运行）

1. 两道不同qid、同参考概念，label分别精确命中一个现有topic.name与其明确已存英文alias；未来两条正式记录共用同course canonical ID，原记录/FSRS不迁移。换语言不靠模型翻译。
2. held有valid same-key private binding后label改成另一个catalog名称：原ID保持；同题唯一legacy、歧义legacy各维持原行为；相同题干但材料/参考变更不借原binding。
3. 一个raw seed+本课mirror+重复alias只算一个canonical；再加另一个canonical同名/同alias必须ambiguous，不按插入顺序或LIMIT前两行误认唯一。
4. 本课与外课同名、伪本课前缀但仅外课QA、foreign family seed、unknown ID、runtime foreign namespace都不能自动匹配；合法global seed映射只加一次本课prefix。
5. 完整name/alias可用，部分词、未登记中英同义词、弱词（从/连接）、相似代码标识符不猜。无匹配的新题仍保守provisional，不创建以自由label为ID的新concept。
6. invalid alias JSON、非array、object/number alias、不合类型label均不泄露/误选/崩溃；SQL只触QA元数据；查询期间course/material变更不调用模型、不写新scope。
7. metadata公开输出不要携private binding key/材料hash；既有12同题/14材料guard必要回归，不重复无关已验语音链。

这些fixture首先证明SOURCE/OFFLINE身份稳定。真实模型若后续验证，只能证明本次确证alias下的未来跨题归属，不是所有自由概念、翻译或旧库合并通过。

## 场52有限历史断言的独立边界

场52已证明related records进入实际prompt并用于wrong→correct特定回忆，但“除此之外没有更早误读记录”超出四条取回覆盖。Main拟在prompt明确这是bounded片段，未取回不等于不存在；该方向不需要扫描整库或更改历史。

建议actual context/prompt用清晰的覆盖说明：已取回有限同课/同概念记录，非全部历史；没有某记录时说“本次取回片段未见”，不能说“你从未/没有更早”。正常source/question/answer预算与prior/current分隔保持。此修复需源码/离线prompt检查；未经真实模型验证不能把52原件或整体回答追认PASS。

本设计审查未发现需要另建Store/全库翻译系统的理由。是否实现、最终bytes、测试和部署仍由Main负责；本报告初稿冻结，后续仅按明确新任务追加实现审查。

## 阶段45冻结实现独立复审

实际读取指纹均与Main冻结值一致：

| 文件 | SHA256 |
|---|---|
| `entry_tutor_answer_entries.py` | `ac10218159083c75dd9b7410fa5d35f14fdae163cc8330a4699aa173b927226e` |
| `store.py` | `9cbbd1f3edbf16b0adf461ce85d40a28ffcb87737f7f62e4dc3661142bc1d43a` |
| `store_qa.py` | `007bce671e4096414343c23a6d6449b03c2afdc505776fbe3b767ceea78d689d` |
| `llm_prompts.py` | `a661183faadc54838c408e54917c6c555d6299de4f29e6cfee0ef77ca687ad34` |
| `scripts/test_neko_concept_label_identity.py` | `aaa032c1ab643f82707d825c779ec662457fc3bd6aaaf8a7dc3afd7b03bd4925` |
| `scripts/test_neko_question_topic_binding.py` | `8632c6953a0c2e04e6b5e9786fd7ee29cab20ec7ff9756f17af48f88f0a49c75` |
| `scripts/test_neko_relevant_answer_history.py` | `d5ad28a4f10e1a85ccffe31c0568abd9245e29e84115dddd286515e17cc1192e` |

独立使用现有Source venv、`-X utf8 -B`执行：

- 新concept label 10项：PASS，1.228s。
- 既有同题binding 12项：PASS，1.876s。
- 相关history/prompt 13项：PASS，1.524s。

全部使用临时SQLite、实际Store/Tracker与AST entry；模型为double。没有启动应用、API、provider、浏览器或声音设备，没有接触用户DB。Main另报material14通过，本Agent没有重跑其未变套件。

### 身份与SQL边界核对

- held自由 `topic` 已从selected ID选择中移除；保留selected_topic_id/topic_id和显式client路径。已有stable held ID的旧测试现在明确设置selected_topic_id，不再把free text当ID；这使测试符合新的身份契约，不是通过改断言掩盖旧数据被重写。
- valid same-key private binding先于自由label查询；与显式ID规范化后冲突则MaterialContextChanged，不调用评分模型。无private binding时，旧同题unique先复用；旧同题ambiguity不进行label挑选，仍保守provisional。未知新label各题产生不同question-scoped ID，没有借display name自行晋升concept。
- 新 `concept_label_candidates`实际从topics的name/aliases/source/family及QA/session/provenance metadata查询，只返回至多两个ID。runtime candidate必须当前course前缀、确有该course session的QA，且已存binding.scope=concept；原question scope不会仅因label碰巧相等被提升。
- raw seed明确family为空/当前course，且ID无namespace或与subject namespace一致；没有把foreign runtime namespace或foreign family借入。原显式seed选择范围保持独立，不把所有可传ID都称为catalog自动匹配。
- SQLite使用COLLATE BINARY的完整等值，保持代码标识符大小写；aliases须合法array、元素type=text。非法JSON/object/number均不被str化或误选，正常name仍可使用。
- SELECT DISTINCT的是已canonical化的ID，再ORDER BY/LIMIT2；raw seed、本课mirror与重复alias不吞掉另一个canonical的歧义。测试实际覆盖一个canonical去重与两个canonical歧义，无任意first-match。
- 新Store函数实际import并挂在StudyStore，查询期间换课在原material/current guard处拒绝，未reserve新grade或调用model。没有改旧QA/mastery/FSRS，也没有另建schema/记忆系统。

新10项包含两不同题的已登记中英alias、重启及A→B→A、原row保持、共享mastery/review ID、无匹配不合并、别课/伪前缀、旧binding不重标、同题历史优先，以及course await竞态。Main提到最早fixture漏qid/aid触发早期拒绝及测试插入NameError，均已修正；本Agent独立最终35项中未见这些fixture错误，不将其称为产品失败。

### 有限历史表述的证据层

renderer新增 `answer_history_coverage=selected_bounded_records_not_complete_history`，并明确selected records不是全部历史、未取回不能推断未发生、不得说没有其他/更早错误。独立history13的最终prompt检查通过，原隐私类型投影负例仍通过；这只是SOURCE/OFFLINE的表达约束，不证明真实模型以后必守，也不把52原reply的全局否定断言追认为通过。

本次冻结实现窄审未发现新的具体P1/P2。仍不外推未登记翻译、全部自由概念或旧多个ID合并；subject/runtime资格属于已有metadata信任范围。实际默认部署/manifest和新模型场在本复审时尚未更改，由Main后续负责。报告冻结，除本文件外未修改任何源码、共享记录、数据库或原证据。

## 场53量具复用的窄静态复核

新 `scripts/neko_relevant_history_probe.py` SHA实读 `560b0015ebd8b6035755bbd431d2e42518cf3a4f9d78a9e1b64c455cd248f42f`。只读与Main `phase45-before`保留副本的diff，增量仅为封闭scene52/53配置、report scene字段与父子传参；未运行probe或调用API/host。

`configure_scene`将STORE/COURSE/DB/receipt/OUTPUT成组更新，CLI choices只允许52、53，父进程调用worker时明确传同一个scene。默认52仍按原存在检查拒绝，不会覆盖/重跑已完成原件；53具有不同owned store与exclusive输出位置。四call、原round/ledger门禁、TASK_SILENT/source/text-only、actual audit、创建时间ownership cleanup与semantic_review=PENDING未变。

本窄delta未见具体P1/P2。场53计划验证的是新bounded-history prompt与实际语义表述；它没有调用跨题grade，因此不能据53解释成功宣称本阶段alias/shared mastery真实模型链通过。四产品文件精确部署/manifest与唯一模型场仍由Main负责，当前未预判结果，不追认52原PARTIAL。

## 唯一场53原件、实际提示词与回复独立复核

只读原件 `benchmarks/raw/evidence/daily-companion-relevant-history53.json`，SHA256为 `da024ebef9bad31fb41492c42cf834c7471b1bbf0bf4d3e915973c5a55336793`，与Main给定值一致。原件finalized=true、failure=null、cleanup_error=null；五个机械checks为true。本Agent没有运行probe、模型、应用或数据库查询，也未更改原件中保留的semantic_review=PENDING。

实际audit仅有一次concept_explain消息记录。最终发送prompt同时含旧错答“我把WEX到NUD读成NUD到WEX。”及同题纠正“我已改正：箭头尖在NUD，所以是WEX到NUD。”，包含 `selected_bounded_records_not_complete_history`、`not the complete learning history` 与 `Do not claim there were no other or earlier mistakes` 约束，未含PRIVATE_REFERENCE_SENTINEL。实际guidance_source为semantic_route，focus ID是 `relevant-history-fixture53::arrows`；result非degraded。

实际回复为：

> 你确实误读过一步：把 WEX 到 NUD 的箭头读成了 NUD 到 WEX。后来在记录里已纠正，确认箭头尖在 NUD，所以是 WEX 到 NUD。

两句均可由本次取回的旧错答与纠正支持，正确区分旧反向误读与后续改正；没有补充“没有更早/其他误读”的穷尽否定。因此本场合成历史的特定召回、纠正接续及有限历史表述可判实际模型窄PASS。这是本场语义人工读审结论，并非依赖nonempty或五项结构checks；52原件与其全局否定措辞PARTIAL保持不变。

原件before/after快照QA均114条，完整快照hash均为 `0c1e4e49ce11dd18b95c28a2d8f4fa3b0a63b11f993824ccc452fab2e0ebe87d`；interactions从0到1，唯一新增kind=concept_explain，其output与上述reply相同。没有新增正式评分；solution/general narration scheduled均false。原round仍为bargein-autocheck-20261012，DeepSeek上限2000、app无固定累计上限、tech0，观测用量DS833→835、app78不变。以上是原件实际快照复核，不是对当前库另行复查或账本写入。

四产品文件精确部署、manifest `451cdf3b87db02710864e4ebbd072f4961aa255fd740abf52e385fbbbd51bc11`、SourceGate、actual deployed新10+history13共23项PASS（2.650s），以及owned存活为空/三端口无listener，由Main执行和核实；本Agent没有重新执行这些运行操作。原件host_exit=1与Main主动有界停止的说明一致，不将它当服务自然退出成功。

本追加未发现具体P1/P2，复审冻结。53只证明本次有限历史取回后的实际模型回复范围；跨题alias身份复用仍以本阶段SOURCE/OFFLINE证据为准，不能借此宣称跨题评分真实模型、Native、物理播放或真人体验通过。capture/microphone/loopback/avatar/audio路径未运行，本次无新增测试、API、设备、用户DB或共享记录修改。
