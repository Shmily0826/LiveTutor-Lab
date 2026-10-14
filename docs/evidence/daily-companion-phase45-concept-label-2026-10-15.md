# 阶段45：概念 ID 与显示标签分开、有限历史的表述范围

完整任务以 [contract](../daily-companion-contract-2026-10-14.md) 为准，Goal active。上一44实际部署/模型52/发布是progress；本轮完整读四记录、沿原ledger833/78/0，没有新外部调用。Main拥有必要实现/测试/manifest/部署及共享记录；独立Agent仅 [concept-label review](daily-companion-concept-label-review-2026-10-15.md)，不修改共享源码或用户DB。

## 实际修复

- `entry_tutor_answer_entries.py` 不再把 held question 的自由 `topic` 文本提升为 selected ID。显式 `selected_topic_id` / `topic_id` / client ID 保留原显式入口语义，不把字段名本身当catalog验证。已有同key private binding优先，冲突explicit拒绝；同题unique/ambiguous history先于新label匹配，既有题不因后来新catalog或标签翻译而重绑。
- 仅在没有既有同题决策时，`store_qa.concept_label_candidates` SQL按完整名称或已登记文本别名精确匹配。case-sensitive，不猜译/模糊匹配/改代码标识符大小写；只取metadata，canonical DISTINCT在ORDER/LIMIT2前。两ID即歧义，不任意挑第一项。
- 资格为：实际同course session QA已确证 `scope=concept` 的本课前缀topic，或course-family eligible的raw seed（无namespace或subject namespace）。question-scoped显示名不自动晋升概念，foreign session不能伪借本课前缀。alias必须有效JSON array且元素为text。没有资格的旧自由label保留同题/题级身份，不自动合旧三ID。
- `llm_prompts.py` 明确历史为selected bounded records，缺失不证明从未发生，不断言不存在其他/更早错误。coverage字段同时覆盖confirmed-concept与recent-course fallback。52原始过度断言/PARTIAL不回改；真实模型是否遵循新增措辞仍待一次必要变更场验证。
- 复用既有SQLite/Tracker/mastery/FSRS和binding，没有新记忆库、schema迁移、QA重写或批量merge。

## 冻结源码与测试（待独立实现复核）

| 文件 | SHA256 |
|---|---|
| entry_tutor_answer_entries.py | ac10218159083c75dd9b7410fa5d35f14fdae163cc8330a4699aa173b927226e |
| store.py | 9cbbd1f3edbf16b0adf461ce85d40a28ffcb87737f7f62e4dc3661142bc1d43a |
| store_qa.py | 007bce671e4096414343c23a6d6449b03c2afdc505776fbe3b767ceea78d689d |
| llm_prompts.py | a661183faadc54838c408e54917c6c555d6299de4f29e6cfee0ef77ca687ad34 |
| test_neko_concept_label_identity.py | aaa032c1ab643f82707d825c779ec662457fc3bd6aaaf8a7dc3afd7b03bd4925 |
| test_neko_question_topic_binding.py | 8632c6953a0c2e04e6b5e9786fd7ee29cab20ec7ff9756f17af48f88f0a49c75 |
| test_neko_relevant_answer_history.py | d5ad28a4f10e1a85ccffe31c0568abd9245e29e84115dddd286515e17cc1192e |

原四源码/manifest独占备份 `benchmarks/raw/evidence/phase45-before`；默认部署/manifest尚未改，宿主43源码Gate不变。不能在source/manifest不同步状态盲启动。

## 离线证据

Source venv `python -X utf8 -B scripts/<test>.py`，实际临时SQLite/Store/Tracker/AST grading entry，model double，不是模型/设备验收。

| 套件 | Main当前结果 |
|---|---|
| concept_label_identity | 10 PASS /1.378s |
| question_topic_binding | 12 PASS /1.863s |
| relevant_answer_history | 13 PASS /1.663s |
| answer_material_guard | 14 PASS /1.576s |

新10覆盖已登记CN/EN别名两个不同题、重启/换课返回同QA/mastery/FSRS identity；旧QA前缀原样；未知label不共享concept/question scope不晋升；同课确证concept复用；两canonical歧义；raw seed+mirror先去重；foreign QA/family拒；case与坏JSON/非文本alias拒；samekey private绑定不改、explicit冲突不调model；旧同题历史优先于新catalog；label查询await间换课不评分/不写QA。旧held-authoritative测试明确设置selected_topic_id，避免继续把自由label当ID的错误契约。

新增fixture初版漏qid/aid先触发了既有QUESTION_MISMATCH保护，及插入测试位置导致局部变量NameError，已修正fixture；没有据此放宽产品guard。当前49个离线case全部PASS，不重复不变音频套件。

## 下一步与剩余

独立实现复核 → 精确四文件oldSHA备份部署/manifest → 部署导入定向验证 → 仅一次静音53核新bounded-history措辞（不重跑52） → 独立语义审查/精确allowlist发布。

为复用52量具，仅给 `neko_relevant_history_probe.py` 增加封闭choices52/53与父子同scene参数；原52store/report保留并拒重跑，53独占新store和report。无模型/提示/音频路线改变，仍4Studyquota、原round/ledger、TASK_SILENT/source/text-only、无重试、creation-time owned cleanup；probe新SHA560b0015ebd8b6035755bbd431d2e42518cf3a4f9d78a9e1b64c455cd248f42f，原55a581bytes亦独占备份。尚未运行53，不冒回复语义通过。

无登记翻译别名/无trusted concept来源不能自动断言语义同一；旧数据不猜合。B多ASR/尾约束、A真实日常材料/D源码/E定位/F集成及集中human继续，不以本阶段结束Goal。无live宿主/声/设备；不初始化房间/物理/虚拟mic/capture/loopback，不调4%音量；用户历史/Sky只读/Root脏树/index/.workbuddy保持。


阶段45已审部署：四default文件逐oldSHA备份phase45-default-before/精确新SHA、manifest451cdf3b87db02710864e4ebbd072f4961aa255fd740abf52e385fbbbd51bc11；SourceGate PASS，实际default Store/Tracker/context/grade AST的label10+history13共23 PASS2.650s。独立source35 PASS与probe560b0015静态closure。唯一静音53实际启动exec session51862，fresh store neko-daily-relevant-history-20261015-53，raw evidence/daily-companion-relevant-history53.json；原ledger833/78/0起，4Studyquota/TASK_SILENT/source/text-only/无capture/设备。只poll同handle，未终态不声称通过，不重跑52/另开场。


## 唯一静音53终态 / 新措辞真实模型证据

- exec51862已terminal/controller exit0，finalized true、failure/cleanup_error null。raw SHA256 `da024ebef9bad31fb41492c42cf834c7471b1bbf0bf4d3e915973c5a55336793`，不改原raw的semantic_review=PENDING；本段为Main事后语义判定。
- fresh store53，114显式合成QA。实际semantic_route focus `relevant-history-fixture53::arrows`；task-only旁录的actual explain messages确含coverage与禁止穷尽否定新指令、原wrong/correct，未改模型请求内容或返回值。SDK4156ms，degraded false。
- 实际两句：“你确实误读过一步：把 WEX 到 NUD 的箭头读成了 NUD 到 WEX。后来在记录里已纠正，确认箭头尖在 NUD，所以是 WEX 到 NUD。”
- **本场旧错答/后续纠正与回答范围：MODEL窄PASS。** 没有52末句无更早错误的穷尽断言，无新模块职责猜测/出题。它不是所有回答永不越界的证明，也不替代跨题别名评分真实模型/Native/设备/human验收；52原PARTIAL保留。
- QA前后114/114、整表SHA同 `0c1e4e49ce11dd18b95c28a2d8f4fa3b0a63b11f993824ccc452fab2e0ebe87d`，没有重新评分或QA改写。general/solution narration false/false。
- 原round DS833→**835/2000**、app78/null不变、tech0/0，无重试。Main核owned identities存活[]，48911/48916/9234无listener；launcher14488按creation-time owned tree清理后exit1，controller exit0、cleanup_error null。没有房间/物理/虚拟mic、capture、loopback或音量操作。
- 52量具原55a581副本、原report/store不变；53只因新prompt实际改变而安排一次，不为额度重复已过场。独立原件/语义复核pending。

最终product manifest SHA `bc4f78fa032582cf3e2a590a5274c6a0d7be9b6273cc00f19e025ecb9f043f86`，仅更新phase45证据说明；全source/default含protected static例外逐项再核PASS，四生产源码/测试指纹不变。下一精确allowlist发布45，再转A/E日常材料可见入口核对；其余A–F/51多ASR与最终human继续，Goal active。
