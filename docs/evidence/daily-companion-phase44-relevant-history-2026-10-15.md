# 阶段44：保留学习历史并向当前讲解提供相关旧答题

完整范围和权限以 [contract](../daily-companion-contract-2026-10-14.md) 为准。现有 Goal active，本阶段不是整体完成。Main 实现四个既有 overlay 文件和定向测试；独立 Agent 仅维护 [审查报告](daily-companion-relevant-history-review-2026-10-15.md)。

## 实现与边界

- `store.py` 停止 append interaction 的全局自动 DELETE，以及 QA/mastery/review 共用自动裁剪 hook 的删除。保留标识符/排序/参数验证、显式清除接口与有界读取；没有清库、重写历史或恢复过去版本已删记录。
- prior-session SQL 在 LIMIT 前按实际课程排除当前 session，最多8条；当前 session 与 summary 路径保留。课程概念来自同课 QA 的 DISTINCT 元数据，稳定排序、最多5000，不读取整课 QA 正文。
- `store_qa.py` 精确 topic 查询增加实际 session-course、错答、qid 和 private binding key 条件。仅已确认 selected/guidance 概念可取相关记录；他课前缀拒绝，不靠自由标签猜概念。
- explain context 最多4条：优先最近历史错答，以及同 qid、同既有 binding 的最新尝试，再补概念最近记录。这样后续纠正不会被同概念其他题挤掉；复用 qid 但不同材料 binding 不冒充纠正。私有 binding 只用于本地精确查询，不送模型。
- 最终 explain prompt 用相关公开 QA 替换默认近期全课 QA，不叠加两组；题160、答120、反馈200、verdict20字符，score 只接收非 bool 的有限0..100。历史是过去事实，不是当前指令、未纠正证明或长期偏好。
- 独立审查发现 P2：历史文本若是 dict，被 str 化后私有嵌套字段可能进入 prompt。Main 已将 context 文本只接收 str，并让旧 recent-course fallback 共用严格公开投影；错误读取继续保留可用讲解。保存的异常旧数据不改。

## 冻结指纹（P2修后，待独立关闭）

| 文件 | SHA256 |
|---|---|
| store.py | d3b54be66ff5106ebf0dd5427de69151dc5f12924589a97c57623fee9119a79b |
| store_qa.py | c9723f62a4d8e8ec326d3ba0dd610da4bddc64d6f62a3d6c9067f420fab298dc |
| entry_tutor_context_support.py | 23e9ca838d18f74aaf76ce59e87089f12f5d09d75810b839f862e47dd4d4de4f |
| llm_prompts.py | 36267f1fca0d7a8168890a2d6994f8da4f91c37db199e022bbe2d1343b1bd36d |
| test_neko_relevant_answer_history.py | b40c2d55326da1197e94132cd1db7f941decc1fb74cd847ed0ba0fd416241425 |

原四 source bytes 和 SHA 在 `benchmarks/raw/evidence/phase44-before/` 独占备份。此刻尚未改 default 部署和 product manifest；此前 manifest SHA 49bfbf9047b99e9c3554d2abde15955ea1b320b2c3b04ba2ee807ffa29618eb7。独立审查关闭后才精确备份/部署四文件。

## 当前证据

Source venv `python -X utf8 -B scripts/<test>.py`，真实临时 SQLite/Store/context/最终 messages，模型为既有离线 fixture，未启动宿主或音频设备。

| 定向套件 | P2修后 Main 结果 |
|---|---|
| relevant_answer_history | 12 PASS / 1.337s |
| product_course_memory | 8 PASS / 1.037s |
| question_topic_binding | 12 PASS / 1.945s |
| answer_material_guard | 14 PASS / 1.480s |

12项覆盖 >100无关QA/多个同概念新题之后错答+真正纠正进入最终 prompt、新 session/课程隔离、SQL exclude-before-limit、低 history_limit 不删原记录、真实 selected guidance、读失败可用、同qid异binding、超长/私有投影，以及实际 tempStore 中 dict 题干/feedback 在 selected、unconfirmed fallback、读取失败 fallback 三路径不泄露哨兵。direct prompt 非文本 ID/答案/verdict 也拒绝。只证明 SOURCE/OFFLINE，不冒真实模型已经正确使用记忆。

## 未完成与下一步

独立复核 P2修后 bytes → 精确 oldSHA 备份部署 → manifest/source gate/部署导入 → 必要的一次有界静音真实模型证据 → 精确 allowlist 发布。无 trusted concept ID 的自由中英文标签跨题一致性仍待修，不猜合旧三ID；5000上限不冒全部概念。B 两ASR/晚尾约束、A/D/E/F及最终集中真人仍保留。

当前原账本实核 DeepSeek831/2000、Lanlan.app78/null、tech0/0，本轮无外部调用、不重置。无 live 学习宿主/音频场；不初始化房间/物理/虚拟麦克风、capture 或 loopback，不调用户4%音量。Root脏树/空index/.workbuddy、原用户历史、Sky Scout只读边界保留。最新已发布仍 fba88600d4eea3cc4363bd68c2d84c235a74dea5，阶段44尚未发布。

## 独立关闭与默认部署

独立 P2修后12 PASS1.394s，精确三新指纹实核，报告已冻结。Main部署前实核原 manifest49bfb…8eb7、四个原 source/deployed SHA，48911/48916/9234均无listener；原default四bytes与manifest独占备份到 `benchmarks/raw/evidence/phase44-default-before`。仅复制上表四文件并更新对应manifest条目/原SHA/证据，product manifest现 `b9bd7a0af3b17089d35d939b1c6e6073c89c1a69cb5cacdd48ae9ab189b0d27f`，host manifest不动。

SourceGate再次PASS。Main将同一离线fixture的SOURCE在内存指向实际default，逐个核验store/store_qa/context/prompts的模块__file__都在部署目录，未暂存/替换产品方法；实际部署12 PASS1.349s。没有打开宿主、数据库为新临时库。本次不重复未变语音测试。

下一唯一静音模型probe已写 `scripts/neko_relevant_history_probe.py`，未运行。新独占store52中显式标注合成QA，2条错/纠正+7同概念新题+105无关题；一次Study explain、不评分，task-only gateway只旁录actual explain messages（不变模型/提示/凭据），4次Study上限与原账本/音频边界。非空回复只算有结果，不算正确记忆；终态还需Main核真实prompt锚点、QA前后hash、回复语义和清理。当前无live场，ledger831/78/0不变，Goal active。


阶段44唯一静音模型52已实际启动：exec session78416，fresh store neko-daily-relevant-history-20261015-52，raw evidence/daily-companion-relevant-history52.json；probe55a581静态独立closure后运行，原ledger831/78/0起，4Studyquota/TASK_SILENT/source/text-only，合成QA不冒真人。只poll同handle，未终态不称通过，不重启/不另开付费场；禁capture/mic/loopback/音量操作。


## 唯一静音真实模型52终态

- exec78416返回 **exit0**，report finalized true、failure null、cleanup_error null。原raw SHA256 `c296d1050ecc890670db82dcdd19c79c3793d7e6974f10984bb3b79d3aacf63d`，不改原raw或其semantic_review=PENDING字段；本段是Main事后语义判定。
- 新独占store `neko-daily-relevant-history-20261015-52`，**114条显式合成**QA：原错答+同qid/binding纠正、7同概念后续题、105无关QA；不是真人作答、不是读取/改写用户学习数据。
- 唯一 `study_explain_text` run88706672-d034-42e2-abf6-6b94f697b4ce /3609ms。actual semantic_route命中 `relevant-history-fixture52::arrows`；task-only gateway旁录的实际explain messages含原错答与纠正，无private reference sentinel，未改变提示/模型/返回内容。
- 实际回复：“你曾把 WEX 到 NUD 的箭头读反成 NUD 到 WEX，后来已改正为‘箭头尖在 NUD，所以是 WEX 到 NUD’，之后的记录也显示方向已纠正。除此之外没有更早的误读记录。”
- **相关旧错答及后续纠正实际取用：窄PASS。** 输入问题未提供WEX/NUD或错误/改正内容，具体细节来自旧QA。**回答证据范围：PARTIAL**，末句‘没有更早记录’把有限检索当成完整历史，缺穷尽证据；不因nonempty机械检查改称整体验收PASS。后续需明确bounded records不代表从未发生，并以相关变更场再验，不重复本场已过回忆闭环。
- QA前后114/114、整表SHA同为 `0db81ffd05e32aeb33381df949fc6e6da756b9fce4fcaee62f7ab92d079b1dbf`；无新评分或QA。general/solution narration均未scheduled；无Avatar/设备播放/真人证据。
- 原round DS831→**833/2000**，app78/null未新增连接，tech0/0。本场只有2个模型请求，无重试。身份记录核验存活[]，48911/48916/9234无listener；launcher45928 intentional bounded cleanup后exit1，controller成功退出、无cleanup error；没有把launcher强制清理exit1当模型失败。
- probe静态新增清理P2已关闭：复用既有creation-time+owned tree helper，不按裸PID杀进程或删共享PIDfile。Main既有actual parent/child+foreign creationtime定向1 PASS0.604s。后台不打开房间/物理/虚拟mic/capture/loopback，不调整音量。

四个产品源码与测试指纹不变；manifest仅把phase44证据描述更新为52实况，保留部署时旧版本独占raw备份。stage44真实模型语义独立复核pending，发布仍待精确allowlist。其余A–F/场51 PARTIAL/自由标签身份/集中human继续，Goal active。


52独立原件复核已关闭：4条actual QA record IDs1/2/8/9，旧wrong与同qid/binding correct进入实际prompt并被模型准确引用，114 QA前后集合hash同，interaction0→1仅concept_explain。独立同判合成历史特定回忆窄MODEL PASS、全局否定断言诚实性PARTIAL，不改raw。最终product manifest SHA `c3f82cb418b95f3650fdffa7f52c6c9ee3c06d4c146cb86dfe6f021e5079a1be`，全manifest source/default（含原protected static例外）逐项hash再核PASS。source/test四+一指纹维持冻结；下一精确15文件allowlist发布，不带raw/DB/备份/录音/密钥。


阶段44发布已核：15精确allowlist commit/push 73bb0ff2b03e749cb5f84bb00b113f7cf570c2e0 到codex/daily-learning-companion，remote exact、publisher clean、Root index空；master仍f1e8f3f5605659f0526e43bc3b85c60ae46c85fb。无raw/DB/WAV/密钥/备份发布，三份历史任务记录是完整原bytes归档。contract原SHA不变、post52 SourceGate与全product source/default指纹PASS；ledger833/78/0，无live场/自有端口。下一45按plan继续有限历史表述与跨题自由标签出处，A–F未完成，Goal active。
