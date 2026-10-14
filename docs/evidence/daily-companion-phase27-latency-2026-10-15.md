# 阶段27：真实语音延迟分段与短答对照

上一轮阶段26是progress：真实同题Native纠正/新成绩/原wrong保留，修量具只读22项及语义通过，代码3016a30、记录8cbfc38已推。Goal active，全部A–F保留，本轮没有全局阻塞。

## 已完成的离线观测增量

复用 `neko_spoken_turn_analysis.py`，新增phrase诊断公开计数/时钟白名单解析与单正式答题分段；没有请求/设备初始化。两个logger的完全相同公开记录合并；不同连接/题/输入窗或多条phrase不任取一个。marker三行核四ID和真实conn/scope/token链；provider ASR重复或多条不生成单条识别指标，即使同timestamp也不视为同一事件。空binary不作PCM，Native chunk_scheduled不是物理可听。估计sample时钟的quiet只用estimated seal减estimated speech end；真实seal与固定WAV结束的wall另计，不混时间基准。

observer仅grade-current场在原acceptance后加诊断，不改变评分/exit/普通输入行为；从本场fresh log解析phrase，缺证据不给指标。不增加整仓扫描、声音测试或依赖。Main/独立12分析测试通过（原5+新7），preflight8、完成判断7 Main/独立过。独立发现连接/scope未核与同t ASR误去重两个诊断P2，均已修并留下原发现及closure，见latency-review报告。

## 既有场37/38只读复算

原raw37/38、原FAIL及之前派生全保留，不重跑模型修量具。读取既有host log，公开计数/时钟与原场输入窗口/conn对齐，另建 `benchmarks/raw/evidence/daily-companion-20261015-latency37-38-v2.json`，SHA256 `d6f3c1139d7d4b40cb13cf7cfbca5753ac8d70bbdc2030a7871cddddd447b98e`。初稿v1仍保留，仅v2为当前分析。原场37/38 SHA仍c8484c5e/c421dc05；没有private答案/PCM写入公开文档。

| 观察段（秒） | 场37，14.005s输入 | 场38，17.014s输入 |
|---|---:|---:|
| fixed speech-end→真实phrase seal | 1.210498 | 1.278321 |
| phrase估计quiet（同sample估计时钟） | 1.223311 | 1.223311 |
| 实际phrase写入wall差 | 0.022669 | 0.027435 |
| 写完→Core accepted ASR | 7.790220 | 9.289721 |
| speech-end→provider ASR观察 | 9.020573 | 10.592305 |
| Core accepted→正式grade | 4.712697 | 4.308187 |
| grade→relay written | 0.610764 | 0.578708 |
| relay written→首Native PCM | 3.207726 | 2.224933 |
| PCM→Native排程 | 0.537000 | 0.527000 |
| speech-end→首Native PCM | 17.554573 | 17.707305 |

Core accepted比provider ASR观察约3/3毫秒，Native用户字幕比provider观察晚约10毫秒。主要未拆清的前段是写完→第一次provider ASR观察，不是UI或Core接收字幕后又等9秒。尚不能把它全部归为服务推理，仍含网络/代理/未观测接收处理；不凭总时长缩短1.2s停顿保护，不绕尚未证实的commit/供应商协议。

## 必要短答对照（启动前）

为检查14–17秒长脚本是否代表日常短答，计划只一场6.438秒固定文件：“当前题，我的答案是WEX指向NUD，请评分。” SAPI Huihui直接exclusive文件流合成，未播放/未采设备，SHA256 `16cd7764152fd9f0aa09bc2bd018bedf642a6083aa6400f7d6f01214f8ddc1c8`，原classifier=answer。复用C32/原图；原题已correct，必须通过原Study正式生成必要新题，不重置/改写为pending；新题若问另一条箭头，按真实题和实际ASR判断评分，不预设固定答案必correct。

新场39 output-only/grade-current/verify-picture-state/prepare-grade-quiz，单固定WAV、无loopback/麦克风/虚拟输入设备。启动前SourceGate及speaker-only policy已过，日常AUTO_GRADE仍默认OFF，产品/runtime未改变。账本实核691/2000、app67/null、tech0/0，原round不重置；单场超时/异常停止，不无限重连。由Main独占在线，其他Agent冻结。speaker只用用户4%不调节。下一步有界39，之后实际证据更新及发布，完整A–F继续。

## 场39实际失败：一整包也能被代理拆成两条ASR

唯一exec11085 terminal/exit1/cleanup_errors=[]，48911/48916/9234实查无listener。新Study题确实仍问WEX出发的起点和终点；pending qid `q_d09b729baa2a49d394c4e6cbffbdc261`，aid `a_ae8513e447f548e78a6fc6fd204c2bac`。原图没重传，未重置历史。

实际只一条phrase写入：109782/109782 samples全写，sealed wall1791993813.969、完成3813.978。provider在3817.421输出第一条ASR“当前题，我的答案是WEX指向NUD。”，3818.948输出第二条“点评分。”；Native观察分别在speech-end后4.729990/6.253990s。这两条都发生在固定输入结束之后，是服务对一个本地整句批次继续分段，不能描述为用户还说话时抢答，也不能以整包发送断言provider单utterance。

首段缺末尾judge短语，当前保守classifier返回None；尾段也None。没有Core显式自动grade accepted/complete/relay markers。角色实际请求两次study_answer，原正式SDK仅新增一条QA/formal，QA4→5，当前题correct100、同attempt；旧四条QA完整hash保持。新QA.user_answer是角色参数“WEX指向NUD”，不是逐字ASR全文，因此不冒充新fallback保存完整原识别文本。最后Native只说“你已经评分过了，刚才‘对，起点WEX、终点NUD，完全正确。’呀。”，沿用前场表达，未正确作为这一题的新成绩反馈。不是量具误判，场39保持真实FAIL。

首Native PCM在speech-end后8.563991s，但它播的是上述错误上下文回复，不能当作已优化且正确的答题闭环。短答较早观察到ASR（4.723s的provider观察 vs 长输入9.021/10.592s）支持继续检查输入长度/分段影响，不证明供应商固定延迟或所有日常短句都快。当前grade_latency因无合法三marker链返回unavailable，正确拒绝套用正式自动grade分段。旧原37/38的pass证据不外推39。

原raw39 SHA256 `3199f88767ef1eec3d6e73c04663d6bc71c3d49af400e09bbf1ef726413180e0`；独占另建 `native-short39-analysis.json` SHA256 `daccc6c99ce3bbe77a53cc5167d6db35a53e0afdb0edeedaaa992d70c4ced768`。原件不覆，未重跑未修场。helper的schema_valid=false来自无marker提前退出，之后capture等未执行checks默认false，不是实际API保护失败：raw receipt实际installed/captureBlocked/readonly，八API全拦，room mic/capture/loopback/volumechange均false；Native麦克风route名不证明设备初始化。Native接收/调度有事件，physical/human仍待。

预算实账691→699 DS(+8，总调用不等于全是评分)、app67→68(+1，本场未controlled reconnect)、tech0；round和上限不变。任务coreApi恢复、配置/偏好具体在最终status核查。没有全局阻塞；停止这条未修路径的重复在线调用，转去修已定位的分段/重复评分上下文及其它A–F。

## 下一项实现必须成套处理

1. 在已有精确pending四ID/首次实际语音owner下，真实首段“当前题+我的答案是...”应能表达答题，不再依赖末尾“请评分”属于同一ASR。拒绝假设/引用/他人/否定/新题/旧答案的条件继续，不把任意“我觉得”或“点评分”自动当答案。
2. 仅扩大regex不足：实际transport对第二个无VAD completed再次note_user_turn_started，旧source tool task和scope会退休，首次pin也已消费。必须先审同一sealed本地输入批次的后续纯评分指令是否能有证据归属，再在scope推进前处理；任何新的有声PCM、answer修饰、换课/换题/activation/socket/connection变更都不能靠旧owner续用。不能shield旧task、伪造provider utterance ID、改owner.scope追最新或无条件拼接ASR。如果没有足够本地批次/新输入证据，使用明确的新Core事务/受控退役设计，而非声称suffix安全。
3. 新方案先用39真实两ASR事件与实际Core/SDK/SQLite和new-input负例离线验证，review/部署清单后才考虑必要修后有界场。当前产品runtime不改，日常AUTO_GRADE仍OFF；不要为了变绿把39量具改成接受错误回复。完整A–F继续，human不逐句占用。

阶段27发布确认：分段观测/测试/真实39失败证据共9 allowlist文件已review/commit/push `bf355bcedbad04d0c958f566560579820a862d92`，remote同SHA/candidate clean/master仍f1e8f3f5605659f0526e43bc3b85c60ae46c85fb；Root index未stage/原脏树保留，raw/录音/DB/密钥未提交。上一轮为progress（源码观测交付及改变下一步的真实短答失败证据），不是无进展等待。Goal active实查；无running exec/自有host待轮询，ledger699/68/0，未修短答不重复online。下轮先四文件，再按phase27末段修真实分段准入与scope/事务；不只regex，不复活owner，新PCM优先，其余A–F持续。
