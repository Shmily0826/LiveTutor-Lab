# 源码教学 D / 连续学习 F：定向覆盖审查

2026-10-14。已承接 contract / plan / status / blockers；只读审查现有报告、限定源码和已生成的证据。没有执行测试、启动宿主、调用模型、启动音频、读取原用户学习历史或修改生产文件。本次仅新增本报告。账本和进程状态采用主线状态文件的阶段快照，未重新查询或调整。

结论：函数流程、改动影响、角色自主 CodeGraph 调用、事实/推断区分、索引刷新和引用范围有可继承的真实证据；不能因为旧报告日期较早就重做。当前窄缺口是结构概览的角色实测、日常路线的指定行解释与连续追问，以及版本前进时学习记录的来源版本。源码指示实际已通，但不能代替源码语义教学。

## 覆盖矩阵

| D 要求 | 已有证据 / 证明层 | 当前缺口与处理 |
| --- | --- | --- |
| 项目结构 | `study_code_tools.py` 已有 `structure → files -j`；`_structure_lines` 先按授权前缀筛，再折叠最多40个目录与5个入口。`LIVETUTOR_REAL_MIC_FIX_PLAN.md` §12：真实CLI输出形状核对、离线边界通过，角色验收明确待做 | **源码/离线通过，角色结构讲解缺证据**。树说明没有源码行号；按目录名字推断模块职责应标推断，随后仅针对一条真实模块关系取源码 |
| 函数调用流程 | `neko-code-grounded-tutor-2026-10-11.md` §3：实际原生角色调用 explore/node，解释 `_confirm → AppLocation → LocationStorage.save → Navigator.pushAndRemoveUntil → SkyMapPage`，并说明接收端内部未读 | **继承真实模型通过**。无需重复同一确认按钮流程；新天气流程只需在补连续场景时定向读取缺失节点 |
| 某行含义 | 同报告 §3–4有真实函数体逐步解释与行引用；`teaching-quality-goal-accepted-2026-10-13.md` 有实际 `return`/`None` 纠错，但它是小代码材料，不能替代授权仓库任意行解释。今日 header4 仅指向 `weather_service.dart:13` 声明 | **部分覆盖**。尚未找到当前日常路线中“指定某一行→解释操作→承接语义追问”的承重证据；定位声明不是讲解该行 |
| 改动影响 | 10/11报告 §3第三轮实际角色调用 impact，区分实际返回的定义与未确认调用者/测试；`didUpdateWidget` 是否走到明确标推断 | **继承真实模型通过**。`impact _confirm` 缺同文件按钮回调是已知索引能力边界，不应伪造调用者；需要时用一次精确 explore 取 `build` 来源 |
| 索引更新 | 同报告 §12.2真实新增 fixture 文件，45秒限流内初查缺失，修后一次强制 sync + 重查，16秒后 `synced-after-empty` 找到新符号；§12.3全新索引 init 与授权失败撤旧修复 | **继承真实CLI/模型证据**。不用再修改 Sky Scout、再建索引或重复 canary；相关逻辑未因本轮指示变更重建 |
| 源码版本与引用范围 | 同报告 §4.1、§11：逐回答按自己的 commit 核，不拿当前工作树套旧行号；后续运行5/5引用 `shown=True`。今日 `code-point3.json` / `role-point-header4.json` 实际回调为 `repo_commit=7aae20f`、synced，shown仅两个真实源码块 | 当前工具返回/receipt保留授权commit与repo_commit，但长期 `code_question` 仍写授权commit，见下项源码发现。Git commit也不等于未提交工作树的内容哈希，现有证据不能泛称任意脏树逐字版本认证 |
| 角色自行取证、事实/推断 | 10/11报告：实际角色自主CodeGraph5次；§11针对未展示 `onPressed` 的再次真实回答承认推断；§12.1源码暗号证实工具结果进入模型请求 | **继承角色真实通过**。今天header4的study_code由probe在连接语音前预取，实际角色自主的是study_point；不能升级为当前语音角色自行读源码并解释 |
| 避免整仓 / 无关源码 | 10/11报告 §2：真实4模式过滤、出境18653字、单条最多6532字、无授权外路径/副本/凭据；当前 explore max-files6、证据12000字符上限。今日code-point3实际4226字、9越界行与120源码块行丢弃、3路径遮盖 | **继承边界通过 + 今日实际回调补证**。本地父级索引包含副本不等于发送整仓；未承诺自动缓存或每次完全消除重复查询。继续采用精准问题，而非广读仓库 |

历史首轮“10/10行号真实”属于弱规则，其 shown 尚不存在，不能冒称强范围通过。强范围结论来自后续真实运行。本次也不把历史 `SkyMapPageState` 拼写P3或旧语音失败直接认定为今天的现行回归；若下次必要场景出现该符号，再按实际输出核对逐字名称。

## 可行动的源码发现：长期记录仍可能指向旧授权版本

当前 `patches/neko-study-2026-10-10-product/payload/study_companion/study_code_tools.py:514-515` 将当前 `head` 传给 receipt，却没有传给 `_code_record`。后者在336、339行用 `authorized['commit']` 写问句和metadata，`last_code_commit`同样取授权版本。工具本身返回的 `repo_commit`、本机源码视图却用本次HEAD。

因此，当授权A后仓库前进B，当前证据和receipt可以是B，但课程历史仍标A。它会影响重启后回忆或引用来源版本。**这是源码层确认的条件性缺陷**；今天7aae20f授权与HEAD相同的场景不触发，未声称已经出现实际用户错误。

最小修法建议：给 `_code_record` 增加本次 `repo_commit` 参数，历史/summary seed记录有效读取版本，同时保留原授权commit作为单独metadata。不改表，不重建记忆。先用原真实方法 + fake store做一个A授权/B读取的离线检查，核历史、seed、receipt与返回值一致；再在原隔离更新fixture需要使用时检查一次真实DB，不改 Sky Scout。本审查没有实现或重跑它。

## 下一次最小可执行场景

建议主线在B受影响场景之外，用**同一日常角色文字会话三轮**补语义缺口；不为此再开固定音频或重跑既有图片、索引、过滤批次。量具不得预取study_code结果或把源码正文塞入用户prompt，才能证明角色决策。

1. “Sky Scout 的主要模块怎么分？简短说明，再给一条值得接着学的路径。”检查实际role选择 `study_code(mode='structure', query='')`、只说授权树、目录职责不冒充源码事实、不造行号；下一步是具体线程而非整仓列表。
2. “接着看 weather_service.dart：第17行是什么意思？和第16行有什么关系？先读实际源码，用两句讲。”角色应自行精确explore/symbol取证；现有7aae20f的返回中16行是lat/latitude，17行是lon/longitude，但应按该场实际repo_commit/shown评分。保留真实tool参数、范围、角色全文与DB；不能只查工具200。
3. “如果把这里的查询键改名，哪些地方需要核对？你确认了什么，哪些只是推断？”只有WeatherService本体不足以确定服务端受影响行为；需一次针对路由/消费处的工具证据，或坦白未确认。不得把所有调用者都会坏、无测试、缓存行为等从缺证据升级成事实。可以同时检查前轮语言/简短要求和材料身份是否承接。

这三轮不重复10/11已通过的确认按钮流程，而覆盖结构工具、具体行教学、边界内追加取证和日常追问的组合。通过后只对实际覆盖范围更新结论；若角色没有调用工具、答错或缺范围证据，保留失败并针对原因修复。若B让语音输入暂时不可用，文字场景仍可独立推进。

## F 边界与不再重做的项目

- `teaching-quality-goal-accepted-2026-10-13.md` 已有真实解释→题→错误→纠正→正确→重启续题记录；今日status又有课程图片/偏好实际重启恢复。它们可继承，不因为本次D审查重复整套。
- `daily-companion-failure-recovery-2026-10-14.md` 最末主线补证及 `daily-companion-failure-recovery-sdk-20261014.json` 已是 `PASS_REAL_BACKEND_LOCAL_STUB`：三次503不造题/分数，不消耗原题，恢复同attempt评分一次并能再讲，8个stub请求、sharedledger不变、清理完成。早先“主线待执行”段落已被末段补证覆盖，不能重复安排这项。
- **仍缺**同一日常角色的较长连续材料学习证据：真实源码提问与行追问、图片替换、换课返回、重启恢复，最终当前材料/课程/问题均正确。可以先以以上三轮源码会话作为增量，后续与主线已有图片/重启证据衔接，或集中真人体验时验证操作接续；不是必须重跑每个已经通过的底层工具。
- 当下header4证明actual role point + visible DOM +设备回环，仍在完整话语结束前动作，误称移动光标；最新relay措辞仅源码/离线过。B准入和新措辞由主线推进，本审查不把其当D全局阻塞。任意桌面定位、真实网络断电、真人听感仍分别未验。

支持受控源码/HTML/图片表面；源码的symbol hint是定位字符串，不是CodeGraph身份或像素理解。省略material ID只绑定当前显示源码，旧解释换版本需要显式identity；显式旧ID与材料竞争守卫已有证据，不重复E几何检查。真人新能力集中10–20分钟体验须等用户明确“准备好了”。Goal仍active。

## 本次交接

仅新增本报告；生产、static、surface、账本和原数据均未修改。本次外部请求/在线音频为0，本任务未创建进程。证据层明确为继承实际模型、当前源码核对、已生成DOM/设备产物；没有新增真人或模型验收。

## 增量只读复核：结构、行窗口与修正接续

主线随后执行真实角色文字三轮，保留 `daily-companion-20261014-code-dialogue1.json` 与 `code-dialogue2.json`。本审查没有参与在线调用；限定读取第二场已生成的完整reply和receipt，以及新file branch/三个测试文件。

第二场是现有角色brain的text WebSocket，没有源码预取、音频或房间麦克风。实际receipt有三次自主study_code：files（2846字符）、explore（7619）、explore（3490），全部7aae20f。第一轮说明真实授权目录、模块与数量，并给天气线程下一步，**原矩阵中的结构角色缺口已取得真实模型证据**；不冒称源码模块行为或设备播放。第二轮正确说明17行lon/longitude、16行lat/latitude，却加上“顺序不能调换”——仅调换map条目的书写顺序不等于交换键对应的值，该教学结论错误。第三轮有实际定向explore，部分事实/推断区分，但把throttled误当服务不可用而等恢复，未继续取得消费端具体行；本场不能标完整教学通过。

最新源码修正已经消除旧版本学习记录的问题：`_code_record(..., repo_commit=...)` 以当前读取版本写input、metadata.commit和summary seed，单独保留authorized_commit；调用点传本次HEAD。`test_neko_code_history_revision.py` 用真实方法检查A授权/B读取及空HEAD回退，主线报告1项通过。**上节条件性版本缺陷现为源码/离线已解决**，本审查未重跑或增加真实DB验收。

structure已不把用户自然语言query作为files的路径filter，schema也允许空query。`test_neko_code_structure_request.py`核真实方法argv、授权外目录丢弃、树无shown和current revision记录；主线报告1项通过。最新note明确空结果不证明文件不存在，throttled仅复用最近刷新、源码查询照常执行；其对角色纠错的真实效果仍由下一场必要追问验证。

### 新file branch主路径

源码层检查 `study_code_tools.py` 中 `_code_file_request`、`_code_file_window` 与study_code_tool：

- offset必须为真正int且大于0，limit为1–120的int，拒绝bool；真实路径strict resolve后必须为授权root内的文件。请求路径与resolve后相对路径各做凭据路径检查，校验发生在sync和CLI前；argv没有shell拼接。
- 接受root-relative或既有indexed prefix路径；CLI用固定node --file indexpath --offset --limit --path。单文件请求不走symbol空结果强制sync重查，失败说明窗口不可用，不声称文件不存在。
- 标准化后仍经原filter、凭据内容redact与独立leak检查；shown从过滤后的数字行计算，仅当前index_file。依赖header中的其他路径被去掉，不作为该行窗口事实。
- `test_neko_code_file_window.py`三项由主线报告通过，覆盖argv/行范围/精确shown、外部路径/凭据/非法范围在CLI前拒绝、indexed prefix与不匹配首header拒绝。测试Harness替换了原filter，故这些三项本身不新增凭据内容redact/leak证明；旧实际边界证据仍可继承。symlink解析由源码严格限制，这批测试没有实际symlink夹具。

未发现上述正常请求路径的直接越界或凭据读取绕过；未重新运行CLI或测试。

### 一个窄P2解析边界建议

`_code_file_window`先核raw开头为请求file，随后用raw.splitlines收集整段所有在范围内的数字tab行，并重包为请求file。如果正确首header/源码后出现第二file header或无归属示例的同范围数字行，它们也会归到首file；原filter看不到已经被去掉的第二来源header。现有mismatched-header测试只覆盖**首header不匹配**，不覆盖首块正确、后块错误。

这是源码层确认的条件性解析边界，**没有证据表明目前单文件CLI实际返回了这种多块形状**，不是当前真实越界事故。最小改法是只解析请求file的首源码块/遇后续header停止；加一个正确首块后foreign block同范围行的负例即可，复用已有三项，不做宽范围重验。本审查未修改生产文件。

下一场应直接追问“只交换map两行的书写顺序、键值对应保持不变”和“更换query key”的区别，要求重新检查已有/精确file证据再纠正。不得把角色承认错误、取得server行窗口、业务影响解释、throttled正确说明混作一个transport完成指标。主线安排该场；本审查仅追加报告，外部请求/音频/创建进程仍为0。

### 后续block误归属已修

随后主线将 `_code_file_window` 改为只读首块，在非首行的后续markdown header/fence前停止；原数字tab源码行不会因内容含header字符串而停止。限定源码核对确认上面的foreign后块继承条件已消除；新增 `test_later_file_block_cannot_be_relabelled_as_requested_source` 精确覆盖正确首块 + foreign同line行，主线报告4项file窗口通过。**该P2标为源码/离线已解决**，本审查未重跑旧批次。当前已测CLI形状为header之后裸数字tab源码；若未来formatter改变成另一形状，需要定向适配，不能默认兼容所有输出。

主线提供的B adjacent6结论只用于支持边界记录：单固定WAV point/无提前音频/简短确认已过，但prefix没有实际tool调用，不能据此证明首call在ASR后的裁决分支；paid工具完整约束仍待验、日常开关off。本次没有读取其原始音频或自行验收，也未更新任何额度。D下一必要真实文字纠正场景仍由主线执行。

## 两轮简短追问的限定语义审计

限定读取 `benchmarks/raw/evidence/daily-companion-20261014-code-short-followup4.json` 的两轮实际question/reply及四条code_receipt，并核对最新 `scripts/neko_desktop_tutor_host.py` 的TUTOR_ROLE_GUIDANCE。本次没有在线调用、CodeGraph重查、测试、账本操作、音频或进程操作。该产物明确是实际角色brain的现有text WebSocket、无源码预取，audio_started/room_microphone均false；transport正常结束不等于教学验收。

四条receipt都为7aae20f：客户端file窗口10–23（579字符，synced），路由窗口1–24两次（各864字符，throttled），坐标helper窗口1–18（522字符，throttled）。原始mode记node，因为file branch复用node；query/index路径及小窗口evidence/shown支持精确逐文件取证。角色没有再把throttled当成拒绝读取，第二轮实际继续取得helper，**旧的“等索引恢复才能继续”误解在这两轮已不再出现**。

| 项 | 本场结论 | 依据 / 边界 |
| --- | --- | --- |
| 首轮：只交换map条目位置，键值对应不变 | **真实模型语义正确** | 客户端16–17行分别lat/latitude与lon/longitude，路由8–9行按req.query.lat/lon取值。实际回答说坐标不变，纠正先前“顺序不能调换” |
| 首轮末句：值写反或改键名都读到undefined | **错误，不能标本轮完整通过** | 只交换lat/lon对应值而仍保留两键，消费者读到的是错误坐标字符串，不是undefined。只有缺少它仍读取的原key（例如单方面改名）才会undefined；值交换后能否400取决于坐标范围，合法范围也可能得到错误地点 |
| 第二轮：漏一个key的服务端结果 | **实际模型按源码推导正确** | coordinates.js:5非string/空串→NaN，:12–15要求finite及范围；routes/weather.js:10条件失败，:11–13提前HTTP400及明确error，未走:17服务端fetchWeather。不能把此源码推导冒称真实HTTP请求执行过 |
| 第二轮：客户端与UI影响边界 | **事实 / 未确认分开** | 客户端22–23行已在首轮shown：非200就throw；角色明确UI怎么显示没有读到。未凭空补UI行为，没有把服务端缺键说成500/502 |
| “两句短答，不出题” | **部分遵守：不出题通过，两句短答未过** | 首轮“不会变。”后还有解释句与末句，共3个句号句；第二轮事实段两句、未确认段再一句，也是3句，且含多项行号/判断。两段不能当两句 |
| 纠正接续 | **部分通过** | 当前证据胜过旧自述，行顺序错误已改；但首轮引入新的“值写反→undefined”因果错误，第二轮聚焦漏key，并未明确撤回该错因果。不能把读了helper或正确400解释等同于所有旧错误已纠正 |

最新TUTOR_ROLE_GUIDANCE已经要求默认两句、纠正后重读、区分named map条目排序与key/value配对、throttled继续缩窄读取。本场证明角色能执行小窗口连续读取与部分纠正，但这些提示没有保证精确两句或避免把配对错误与缺键混为一谈。提示里尚未明确“值写反但键存在，不是undefined”；这是可在必要集成时补充的通用语义区分，不需要仅为一句文案再安排付费场景。

可供下一次必要追问/集中体验使用的两句准确表达：

> 只交换两条map记录的书写顺序，键值对应不变，服务端收到的坐标就不变。若交换经纬度对应值，键仍存在但坐标可能错误；若改名或漏掉消费者仍读取的键，则会缺值，本项目按已读校验返回400。

上面的替代表达是本次人工源码审查结论，**不是模型实际已说出的回答**。本场证据升级为真实角色精确行读取与漏key处理解释通过，整体短答/全面纠错仍PARTIAL；没有新增设备播放或真人验收。账本395/43/0仅为主线通知的阶段值，本审查没有重新核对、更新或使用额度。
