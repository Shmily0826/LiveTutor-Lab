# 日常学习伙伴阻塞清单

完整执行契约：`docs/daily-companion-contract-2026-10-14.md`。压缩或自动续跑先读 contract、plan、status、blockers；后续明确指令优先。局部项不等于全局阻塞，不能以时间或单项成果标整个 Goal 完成。

| 项目 | 具体状态与证据 | 已尝试 | 恢复条件 / 继续路线 |
| --- | --- | --- | --- |
| 本窗口模型配置 | 工具上下文不提供可确认模型与推理强度 | 已明确说明，不切换 | UI 明确配置确认；当前继续代码/证据接续 |
| Native Realtime 直接看图 | 继承 checkpoint：方向关系误读，免费文字视觉端点 400 | 历史已停止，无重复试探 | 当前复用已通过 Study vision，与角色语音整合 |
| 密集图小字 | 继承 checkpoint：部分小文字/连线误读 | 清晰深色图改善主要关系 | 支持清晰图/局部查看，诚实表达不确定，定向验证 |
| 真人语言/声音/长句与最终体验 | 本轮尚未做 | 夜间不采房间麦克风 | 用户明确“准备好了”后一次 10–20 分钟集中验收；继续固定输入/回环 |

不因以上局部项结束 Goal。新增失败必须记录证据、已试方法、恢复条件；服务失败按要求退避，继续本地工作。

新增局部失败：`daily-companion-20261014-model.json` 首次“two English sentences”输出中文；已修语言检测，修后实际DB输出两句英文（`language-fix-db.json`）。`voice.json/voice2.json` 均为量具启动/就绪缺陷：child未继承UTF8、错误假设/available含plugin ID；改用已有plugin_server_ready并显式UTF8。前两次未CONNECT、不影响额度，第三次单场继续，不做无效服务重连。

续记：voice3是文字触发产品offline handoff，0播放，已停止；voice-fixed改固定WAV+heartbeat，同场真实study_explain与71音频准入/161回环响声，room mic=false。自然停顿分轮仍PARTIAL；日志两段识别93/9字，两个study_explain。恢复条件：统一输入/ASR/tool/audio/playback时基并做停顿专项；不动已验普通打断架构来掩盖问题。观察socket不再接收native输出，逐字语音转述需native DOM/输出文本专项采集或集中真人确认，不能用空观察socketreply认定失败/成功。

Goal objective字段更新工具限制：内置update_goal只支持status；Local Bridge goal get遭schema validation（要求token_budget且剥离action），未重试写入，未改任何Goal预算或状态。完整contract已在现有Goal的plan/status与当前执行上下文明确绑定引用，不重建Goal；此UI字段限制不阻塞开发。

同步补证：native-timing已捕获真实role两句文本和回环，旧“最终reply未采”边界仅适用voice-fixed历史场景。三段75/93/9字识别确认自然停顿过早分轮；没有provider session.updated确认，不臆测silenceDurationMs被代理支持。MANUAL候选默认off；首次support量具在宿主补丁重放锚点冲突时退出（manual-support.json，额度314/33不变），先本地兼容修复再一次有界支持验证，不重复无效服务连接。局部项继续D/E/F工作。

最新MANUAL支持场景已完成（manual-support3.json）：null请求存在；commit前仍三段输入完成与两次工具，没有echo确认，不能交付RNNoise自动end候选。已撤下实验运行时代码，不再同场无效重试。保持局部B问题：下一步可离线设计输入/工具完成协同，或获得代理支持的明确协议；不改供应商、不把普通打断延后、不以这项失败阻塞其他交付。

日常直接Python启动编码失败已修并成功启动/重启；Study SDK将课程拒绝包成INTERNAL前缀，已按实际序列化修前端并专项通过。最新所有量具进程结束；额度330/34/0。仍待任意桌面指示、密集小字、更自然中文长句、真人术语/听感/新能力体验；继续独立本地工作，不作全局阻塞声明。

后续证据更正覆盖上文历史推断：旧英文75/93/9来自三个句子，不能证明句内过早分轮；MANUAL null后两次tools更新未带turn_detection，可能重置的混杂尚未知，不能断言代理不支持。停止重复支持实验，原server_vad保持。

当前真正中文单指令0.9秒句内停顿仍两段ASR，role-point-single工具先ASR的本地scope取消已通过有界ordering修复离线验证；ordering2能够播放真实拒绝句，但role猜CSS/漏ID，指示失败。按原始file/line/symbol映射当前受控证据已实现并过七项守卫，真实角色场景主线一次验证中。省略material ID的source模式指向当前显示版本，不足以绑定旧解释版本；需显式旧ID/版本hint才能拒绝该场景。局部项不挡F隔离失败恢复及其余交付。

最新：真实formatter标题解析缺陷已修并九项守卫过；header4实际role/current source/DOM/device路线通过，指示失败项已局部解除。仍先于整句末尾动作，role误称“光标”；最新relay修正仅离线过，整句准入方案尚待实现。F本地503实际SDK/DB恢复通过，原题/计数保留、共享ledger未变，解除该证据缺口。额度350/40/0，本任务进程全部结束；继续B/D与集中人工验收，不作全局阻塞声明。

B opt-in gate已实现、10离线守卫过，但gated5实际只改善为整句末尾后一次pointer。前片call在已ready ASR之后到达、fresh speech使其误等下一ASR，.4秒释放仍触发proxy提前声音，最终无简短确认。候选日常默认off；下一步先离线修这一实际顺序/有界等待和弃call续答隔离，不重复未改场景或MANUAL。D文字连续源码问答独立推进；source历史旧授权版本已源码修复、方法检查过，实际仓库前进DB仍待原隔离fixture必要时补证。352/42/0，同账本无重置，本场进程结束，非全局阻塞。

## 最新局部状态（覆盖上述历史快照）

- B adjacent6单条source point指令已实际role/DOM/设备通过，compact高亮请求措辞过；并非prefix-after-ASR或paid教学普遍通过。all-Study名称扩展包含readonly/control，日常仍off。picture-gated7五片ASR，三次prefix拒绝，末后并行explain旧参数+最终参数，之后重复两次；无提前provider audio，最终不完整英文/0PCM/0回环。失败原因保留，416/44/0，停止无修改重复场景。
- 最新仅允许call先于预期ASR至多200ms，旧前片不在几秒后升格；14方法、6 ordering、5 lifecycle/replay过。neighbor8一场进行中，复用既有隔离课/图片/固定WAV，不重复paid图片准备，不夜间采房间麦克风。
- 无稳定input item ID，邻接时间只是有界兼容，不保证所有长停顿/persistent control语义。日常不能仅凭point成功或请求变少而打开。prepare-picture现强制新隔离speech acceptance store，防止全局prefs污染正常daily；verify模式只读既有隔离偏好。
- D file mode/实际revision历史/真实结构补证已交付；short-followup4行顺序纠正/漏key→NaN→400有源码模型证据，但『值写反也undefined』错误且各三句。新guidance明确值存在≠缺key、两句不加第三句，此增量未模型验收，不为文案反复paid。继续其他必要能力，不作整个Goal blocked。
- F本地503 SDK/DB恢复已有证据，不重跑；任意桌面、密集小字、真人新能力各保留范围。剩余可自主开发/核证不少，Goal active。最终真人集中10–20分钟等明确“准备好了”。

neighbor8已结束，432/45/0，旧prefix不再升格、无提前audio、实际中文28PCM/72响声；仍三次explain且英文失败，局部B未解除。确认检测漏“用两句英文”，role question丢明确English output；已加一次language参数/count/否定、4 wrapper+SQLite守卫和5失败guard/shape过，最新增量只有离线。较早缺PCM的失败由本场设备路线部分解除，不能称整个paid语音闭环过。下一步离线同一最终ASR重复工具/结果owner分析，必要时再定向完整英文；当前无活动online，本轮候选仍off，继续阶段发布与F日常连续学习。

最新voice9已结束440/46/0：一个actual explain、两句英文主体含原中文模块标签、23PCM/68响声，无提前audio/长期prefs污染。严格全英文检查仍失败；不能因主体英文称纯英文通过。新inflight精确合并7离线过，但这场只有一call没有joined，不声称物理分支已过。全长停顿跨片/persistent control语义仍不普遍保证，候选默认off。下一步是同场语言接续必要验证，不为触发joined重复付费。

Native材料竞态审查两个条件性P1主路径源码已修、9离线过；非空session ensure替换也拒绝。无新版实际事故或换图播放通过声明。短SQL既有lock保留旧identity已提交history，新材料不接纳旧live seed/返回；已经安排event/发送tool结果/排native audio之后的材料变化还未驱动播放取消。下一步研究该材料事件与现有owner/cancel接口的最小关联；不延迟普通真人onset。先完成不依赖这一缺口的连续语言/交付。所有增量未发布，线上前需刷新manifest；不作全局blocked。

continuity10已结束458/47/0：两轮同场正常解释经最新guard、临时英文主体后回中文、各一explain/native25/27/回环75/71、prefs不变。解除这一场语言恢复与实际设备连续性缺口，但严格纯英文/真人尚待。新实际失败：中文把HTML5217/5219『天气未命中 / 百科 HTTPS』的『未』漏掉，关键条件被改。完整WAV/JSON保留raw，不反复跑相同paid图片准备。恢复路线：纠正后重查已授权当前材料、明确引用精确文字或承认看不清；受控HTML定位元数据可提示位置，但不能冒充PNG像素证据或默认将不同材料合并。继续材料cancel/阶段交付，非全局阻塞。

计时量具边界：native500events最终截断第一轮首PCM/scheduled，不能把稍后heartbeat当开始；首次native时间未知不重跑该场。计数25、loopback实际WAV仍可核，按完整WAV重算75/71响声，JSON曲线初60bins不用于错误宣称无播放。下一量具每轮保存首PCM/scheduled，离线修正后继续其他工作。主要延迟已定位工具/代理，不更改普通真人onset。
