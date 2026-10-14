# 原daily最新版入口：只读准备审查

2026-10-14。完整读取contract与当前plan/status/blockers；最新已发布阶段十八`1bc11f210937dddfe6499b2b6ff6736843d79f46`。voice34虽实际session和server DSP有证据，但无ASR/教学/PCM，保持失败，不能借本次文字入口检查重试声音。此子任务只读源码/源码资产hash，**未打开SQLite、学习history内容或原配置密钥值**，没有服务、浏览器、API、设备、账本、manifest或其他文件写入；唯一新增本报告。

## 已核实的入口与实际范围

`Start-Daily-Tutor.cmd:5`固定`--store neko-daily-companion --budget-round bargein-autocheck-20261012 --egress-budget 2000 --api-budget 80 --text-only --study-ui --learning-surface --code-root keep`。`%*`可追加现有参数。本轮准备的有界离线命令为：

```powershell
Set-Location -LiteralPath 'D:\CODE\project\LiveTutor-Lab'
& '.\Start-Daily-Tutor.cmd' --minutes 5 --offline-egress
```

这是Main执行方案，本文未执行。不要裸调`neko_tutor_start.py`冒充default CMD：其自身store默认是neko-product-data，CMD才明确原daily。不要追加store替换、预算轮次、voice、audio-input、egress-budget0或虚构output-only参数。

launcher `498–508`拒text+voice/audio-input组合并约束store在raw目录；`host_options:235–248`保留text-only与offline-egress、原round，learning-surface只使Study新store默认vision可用，不启动语音provider。`code-root keep`走读取既有授权路径，不弹picker、授权新root或重建索引；当前是否已有有效授权未知，本Agent没有读取它的内容。

Chrome使用该store的`browser/text-profile`并mute；Native用`text-only-userdata`、mute-audio、受保护text-only host预检。捕获API拒绝先于原页面运行；不是全系统禁麦克风声明。offline-egress是现有host relay禁外部模型的边界，不等同全OS/所有浏览器网络离线。Main应以当场relay/no provider receipts和原账本不变补实际证明，不把命令名当已经无调用。

## 启动会改什么：不能要求全store字节不变

| 范围 | 精确caller与预期行为 | 保留判断 |
| --- | --- | --- |
| 代码/资产 | host `prepare_product_plugin:255–294`拷基础.py/.toml/.md与static/surfaces/i18n，再覆盖canonical payload/static；不复制DB/SQLite。manifest改legacy panel及安全默认，text页封装捕获保护。 | plugin-code应升级；学习data不应由部署复制/替换。prepared index因保护封装不会与raw canonical HTML逐字相同。 |
| 宿主Core配置 | host `prepare_store:130–164`读原dict、保unknown字段，强制本项目provider/agent/TTS/proactive/wake等已列字段；坏配置拒绝并留原文件。 | 不是“所有设置完全不变”。Main只记录改动键名和local比较结果，不输出API key/原值；unknown用户字段应保留。 |
| 角色规则/后台循环 | launcher `557/567`调用host `apply_tutor_role_guidance:577–619`及`apply_quiet_brain_config:460–506`。仅空/本项目prefix guidance写入，用户guidance/preset保留；缺省后台review关，自有旧powerful-memory关值可恢复默认，现有true选择保留。 | 允许明确的tutor迁移，不把原Core配置SHA变化叫数据丢失；quiet provenance是既有project记录，本轮不读其私有值。 |
| 首引导/用户默认 | host `prepare_tutor_onboarding:194–232`保存skip而非假completed，保completed和manual intent；`prepare_tutor_conversation_defaults:235–252`只在缺global proactive key时补false，已有choice保留。storage_policy固定同runtime root并更新timestamp。 | 这些state/config文件可变化，不应被误算成学习history改写。初引导已验收，不重跑其整套流程。 |
| Native/profile | `write_surface_config:119–135`使用已保存JSON、只更新apiBaseUrl/chatSurfaceMode/startupDefaultForm/portableUpdateAutoCheck；其他字段保留，坏文件拒绝。持久text userdata/browser profile及owned记录会写入。 | 不清profile，不接管用户Chrome；owner身份以creation-time/本次树为准。 |
| Study设置 | canonical startup `300–307`先manifest config，再`Store.load_config:540–546`让已保存设置覆盖defaults（legacy language字段单独不提升为全局语言；现有明确偏好系统继续复用）。 | manifestdefaults变化不等于覆盖用户的已保存Study配置；Main需实际compare，不能凭source直接PASS。 |
| Study生命周期 | startup `348–380`load原state、close旧open session、清运行reservation/旧error、建立新session；`_start_study_session_locked`加载当前课saved材料，同课未评qid/attempt保留。seed/recent events/last summary及runtime评价快照可清，state+当前course checkpoint写入。shutdown结束新session并保存checkpoint。 | session_id、last_started_at、session rows、状态hash允许变化。未答题若原来存在须同身份/内容保留；已评的当前快照可退役，原QA/错题/历史不能因此删除或重写。 |

`StudyStore.open:224–243`会初始化schema，并执行已有“empty时seed”与knowledge seed逻辑。已有非空学习库不能以“启动都会写DB”为理由放过原interactions/QA丢失；也不能要求整个DB文件或state kv SHA绝对不变。SQLite journal/WAL与session更新本身会改变文件hash。

本轮没有发现启动路径调用fresh `study_start_session` UI按钮；自动startup用`resume_pending_question=True`。因此有待答题时不应通过重出题来补恢复。idle/结束可能增加生命周期记录，Main在快照中按表区分，不混作模型学习产物。

## 原daily源码metadata：目前确实未完整升级

只对`benchmarks/raw/neko-daily-companion/plugin-code/study_companion`的13个指定源码/资产做SHA，未枚举其data或读配置。6项与canonical一致：question entry、explain entry、study_materials、llm_prompts、prompt_templates、learning_preferences。下面7项不同，LF/CRLF归一化后仍不同：

| 相对路径 | 本次actual SHA前缀 |
| --- | --- |
| `__init__.py` | `5c3a35b21c34` |
| `service.py` | `796fc42f5d1a` |
| `study_avatar_tools.py` | `000cb5ba34bc` |
| `entry_tutor_answer_entries.py` | `5c886dedde45` |
| `store.py` | `787c30275f36` |
| `static/main.js` | `c8a8bb5e4a5d` |
| `static/index.html` | `b9b83114fb7b` |

这与阶段十七`deployed_matches=false`一致，不能说原daily已运行新公共题/返课/晚callback修复。它是本次启动前metadata快照，不保证Main之后复制时仍相同。Main应让正常部署升级，不手动copy旧DB/C33 store或重置原历史。prepared index保护层需另核嵌入的canonical页与policy receipt，不能拿raw SHA直接判升级失败。

## Main的一次有界offline实际检查

1. Main先确认本次可拥有的端口/窗口，没有其他daily实例；只用原store、原round。准备私有的before snapshot，记录resolved runtime/data/DB路径（由`self.data_path('study_companion.db')`实际解析，不猜另一个DB）；不复制原学习库，不用restore/reset。公共报告只写hash/计数/比较结果，不写学习全文或密钥。
2. 按上面同CMD＋offline参数启动一次。记录launcher/source gate、actual argv、原daily resolved path、代码部署指纹和text profile路径；未知源/坏配置拒绝就停止，不绕guard。等待真实Study status/runs/export和Native文字composer/保护receipt，不以HTTP200/即时Refreshing或窗口存在算Ready。
3. 只readiness、刷新与只读public状态，不选择新课程、不点fresh/出题/讲解/评分/总结、不触发读取窗口、不发WAV。比较前后public current course、pending题身份/内容hash；若原本没有held题，记NONE保持和“原daily pending特定分支本场无对象”，不要造fixture进原daily。旧task上的C33/pending证明独立继承。
4. 一次手动刷新或页面重新加载足以核当前public题与session同步；不再跑已通过task A/B/A/模型场。Main实际本地读取只做保留比较、不输出original history。到达ready＋保留检查后按Enter正常结束，不等完5分钟来刷状态；失败也只owned cleanup，记录cleanup_errors与实际退出，不按旧PID清人家的进程。
5. after snapshot区分expected配置/session写入与应保留数据。原ledger bytes/余额由Main核，offline场不创建/重置账本；没有paid/provider/audio事件才记录“本场无外部模型/声音”，否则停止调查，不继续在线试题。

推荐的保留快照（Main可在本地内存生成，本文没有读取这些数据）：

- **学习历史/QA：**before已有row ID集合及每row全部持久字段canonical hash；after逐ID同hash、无删除，QA/错题计数稳定。本场不教学，所以新增question_generate/answer_evaluate/summary与QA应为零。仅总rowcount相同不能排除改写；新SDK run日志和session表变化分开。
- **待答题：**before是否pending、qid/attempt/public题内容hash及必要私有产物hash；after同身份/产物，运行reservation移除可单列预期。若已评，current snapshot清除不等于旧QA删除；必须仍核持久QA/history保留。
- **课程/材料/偏好：**selected course相同；各原submitted-image kv、明确长期偏好kv canonical hash相同；课程checkpoint原题/attempt/旗标/cache/评分hash单独比较。当前course checkpoint生命周期写入允许明确解释，foreign课程checkpoint应不变。
- **Study保存设置：**config kv的既有值projection hash保持，legacy语言处理按已有规则；不要将manifest新defaults当“恢复用户设置”。宿主Core配置单列上述已知强制/迁移字段，unknown用户设置hash保持；角色用户guidance/preset与已有proactive choice不得被本轮覆盖。
- **文件metadata：**原DB/config路径、大小/mtime/hash可辅助，不能独立证明学习保留。profile/owner/storage-policy/core attachment配置允许上述变化；代码覆盖目录与data目录必须分开。

whole-DB hash不变若成立是强辅助，但不能成为唯一门槛；正常WAL/session写入时应采用逻辑row/kv hash比较。若Main当前权限/量具无法取这些只读snapshot，则明确“数据保留待完整证明”，不能只凭旧文件还在就通过。本文不要求恢复、拷贝或清空原数据来实现检查。

## 结论与冻结

**SOURCE/METADATA REVIEW：**default text-only、keep、原store/round及可预期改动范围已核。原daily13项当前7个源码/资产仍不同，新版实际入口及原数据保留尚待Main这一次offline运行；不是新的模型、设备或human证明，也不解除voice34局部失败。代码没有新改动，本报告只准备执行与保留判据。

入口SHA：CMD `e6029f0da609cb50be20c02f4a6c03f344027bc4490e83806f7bc478cd422bd0`；launcher `ccd7a692bff07fd2281fd0bac43973c30dc5f372cc778f5d64b8dffdb7da6310`；host `a30de08d711793eb07bb4eed4b9c32ab6c23fe2a61f926689fe3452c123da92d`。这些只是读到的源码版本，Main若修改共享host需按新版本更新其实际证据。

唯一新增本文件；其余代码、manifest、四记录、用户数据、账本、进程均未修改。报告冻结，Main负责实际启动/快照/部署与记录。

## 阶段十九追加：相同 seed 启动写入审查

本段独立审查只读四个指定文件：canonical `store_topics.py`、指定base同名文件、`scripts/test_neko_topic_seed_preservation.py`、私有量具 `benchmarks/raw/evidence/daily-phase19-daily-entry.py`。未执行量具、测试、SQL、服务或浏览器；未打开原用户SQLite、学习history或配置密钥。只追加本报告。

Main本场事实：原CMD的离线文字入口已实际Ready并完成Study刷新；原课程、配置、偏好、history和QA保留检查通过，但820个topics的整行hash均变化，所以**第一次完整保留判定仍为FAIL**。本审查没有旧行完整值，不能将820项变化宣称为“只有updated_at”。源码能确定存在每次seed upsert无条件写updated_at的路径；它是需修的具体原因之一，不是对旧hash变化全部字段的反推证明。旧报告上面的部署metadata和待实际运行结论是其当时快照，不替代Main随后这场实际结果。

### SQL补丁：未见发布阻断

base SHA256核实为 `0069f0cae4dea26b654415e5883744576877dbe3a9163414099428bbad9af2fd`。只读逐文件diff表明canonical相对该base仅新增`upsert_topic:229–232`的WHERE条件；原loader、INSERT参数、全部CASE分支和commit行为保留。

- 冲突id由原ON CONFLICT固定。新增比较包含其余19个持久内容列：name到aliases以及source，排除的只有更新时间。因此只有incoming source为seed且这些内容相同才跳过UPDATE；并未按名称、来源或少量字段误判相同。新id仍正常INSERT。
- row-value `IS NOT`给出NULL-safe比较，不使用会产生unknown的`!=`/`NOT (...=...)`组合。任一对应NULL与非NULL不同仍允许UPDATE；两侧均NULL相等不会误触发。incoming字段沿原参数规范化，source由`str(topic.get('source') or 'runtime')`产生非空值；本次没有新增NULL写入路径。该NULL结论为SOURCE逻辑分析，四项测试并未单列legacy NULL用例。
- incoming非seed满足第一项条件，继续执行原CASE保护：不能覆盖已有seed的权威name/source等，但允许原有空字段enrichment；没有截断正常运行写入。incoming seed任何真实内容变化仍UPDATE，existing非seed升级为seed也因source不同而UPDATE。相同seed的更新时间保持是有意消除重复启动写入。
- JSON比较为原序列化后的SQL存储值比较；已有不同JSON字节/字段内容不会被当作完全相同。补丁没有重定义seed优先级，也没有承诺保存与incoming seed不同的运行enrichment；这些情形仍继承原upsert语义。
- `load_knowledge_seed`仍在原lock内循环、最后commit；返回数是接受的有效seed输入数，不是实际UPDATE数。相同seed返回1同时SQLite total_changes不增加是允许的，不应将该count解释为本次改写1行。

Main报告四项实际方法/临时SQLite检查PASS；本审查只读取其实现，没有重复执行。测试`14–19`抽取真实loader/upsert，SQLite真实执行SQL；`43–66`覆盖完全相同seed所有列及total_changes不变、真实seed修改、非seed权威保护/enrichment、真实loader重复加载。fixture不导入原daily运行实例/库，connection有cleanup。它证明这些离线路径，不证明原库再启动后820行一定全部保持，也不等同真实模型/设备/真人体验。safe_int/float的有效输入stub及简化临时schema不覆盖完整生产迁移和非法输入；该范围并未被本次补丁改变。

### 原daily再检查量具：安全边界与判定范围

当前runner新增`--seed-fix`后缀（`11–12,58`），第二次JSON/console文件与第一次不同；`48`拒覆盖既有结果，console使用`xb`。**第一次FAIL应继续留存**，不删除后重新生成同名结果。runner没有restore、clear、copy DB或写学习SQL；`16–17`使用SQLite mode=ro＋query_only，读取后仅输出原行hash。它确实在本地读取完整行用于hash，不能称“完全不读取history”，但不将原题/错答/隐藏答案全文写进hash报告。Core配置读取仅用于本地比较，报告记录变化键名和相等布尔，不输出值。

启动参数`59`仍为原CMD、原daily store/round、text-only默认、offline-egress；没有以新store绕过原库问题。端口占用先拒绝（`49–51`），正常Enter结束有40秒界限，fallback仅交给既有owned cleanup（`75–80`）；本审查未扩大到该callee或验证其本场执行结果。没有声音/麦克风/回环步骤。report内`audio/devices/model_requests=False`是场景声明，需要Main结合本场guard、运行记录和ledger结果判断，不能仅靠该常量宣布设备或外部调用证明。

量具以下边界应限制最终文字，不影响重复seed旧行hash检查本身：

1. `82–83`逐旧主键核全部row hash相同，覆盖topics和旧history/QA不改不删，但不排除新增row；sessions/kv被显式另行处理。若要宣称本场无新教学记录，另核新增interactions/QA数量，不能由这一个布尔推出。
2. `90`的pending_identity仅核qid/attempt/public题文本/options hash；它不要求after.pending仍为true，也未hash私有答案/rubric/cache。`95`明确记录原pending分支是否有对象。原daily若没有pending，应记本场该分支未覆盖；若有pending，完整“仍待答及私有题产物保留”需要补这些布尔/hash，不把当前指标扩成完整续题证明。
3. Native getter记录composerAvailable但`44–45`没有断言它为true；这只证明text-only/capture guard与not recording。实际Study Ready/刷新由`71–73`已有UI检查承担，不能将该getter单独叫角色文字发送成功。
4. `94`的saved_core_config_preserved仅记录、不参与`101–104`退出条件。runner exit0本身不能推出Core配置完全相同；Main应读该布尔/键名并按前文允许迁移解释。Study config、原课程、偏好、受保护kv及ledger比较则有退出判定。

因此，**SOURCE REVIEW：本次seed WHERE未发现具体阻断；原库是否修复仍以独立seed-fix当场保留比较为准。** 此处不修改第一次实际FAIL，也不把Main四项离线PASS扩大为原daily全数据或学习功能PASS。

本次读到的文件SHA256：canonical topics `30fc4ae177e14c3062f8f68154b203199eb9cc36fae1dff4604ba5861ff085a8`；seed test `8c8accd2e15e1346a5c4d92d7231121e87b5b8e07ca1f7a2996f5260fb2a7ac1`；私有runner `e1c7d242a8956c63c45edb397c3c0bddb64bf1fba8c1023ffcbf3108893d43d3`。后续Main修改量具时这些指纹只是本次源审快照。

本段完成后再次冻结报告；其余文件、用户库、配置、manifest、四记录、进程、设备和账本均未修改。

### 同轮量具收窄复审：三项已修（SOURCE）

Main随后修订上述量具；本审查只读确认，没有运行。最新runner SHA256为`3ba393ddb2009a8fc68bcaa2f355280fbb6f2af27418956d1da154aeada9ecf9`。

- `37`的question_hash新增attempt_evaluated，`90`在原pending时必须after.pending且原题hash相同；不会再因公开题身份相同放过被退为已评。仍不是私有题产物完整hash证明。Main明确本次原daily pending=false，因此这个具体分支本场无对象，不声明实际续题验证。
- `91`对原kv/sessions之外的每张表要求after行数相同，`106`把no_new_learning_rows加入退出条件。结合原`82–83`全部旧行hash保持，可证明这些原表未新增/删除/改写；只按行数判断不能证明保留，但此处两项同时要求，不存在该弱化。
- `95`的saved_core_config_preserved现在由`106`作为成功必要条件，而非仅展示字段；本场exit0不能再忽略实际Core配置变化。原先允许迁移的总体启动说明仍成立，但本次窄scene采用更严格的原配置全相等判据。

前三个旧量具边界在其旧指纹下留存；以上是最新源码闭合结论。Native composerAvailable仍只是记录，不能额外外推文字角色发送。seed补丁没有新发现的具体阻断；Main计划独立`--seed-fix`原入口全行hash场验证旧行与数量，旧FAIL不覆盖。本段不是该场实际结果。报告再次冻结。
