# 教学质量 Goal：完整目标已完成（2026-10-13）

最新结果：用户批准同轮累计300/30/0，保留160/18历史后完成有界验证。真实新客户端接入时旧录音继续、后续回答和实际输出成立；完整宿主重启恢复旧错误及后来正确记录；修正语音/网页响应合同冲突后，不出题和两句话要求通过。最终173/19/0，全部会话已清理，逐项完成审计通过，Goal工具已返回complete。见[最终验收与证明边界](teaching-quality-goal-accepted-2026-10-13.md)。下文全部保留为当时进度和失败历史，不作为当前状态或额外启动授权。

## 21:26 最新状态：Goal BLOCKED，保留完整目标与已验收结果

再次核对：累计160/18/0仍达上限，processes=[]，host log时间未变化；三个本轮源码哈希与已通过回归时相同，19个product文件与两份隔离部署逐项吻合。没有可等待的运行任务。上一轮是有效进展，本轮未通过重复测试或扩大代码范围来掩盖剩余在线证明缺口。

从160授权后的实际语音验证、第一次离线收尾续轮到本次审计，同一额度耗尽条件连续存在三个Goal轮次。必要离线修正/回归已经完成，目前无法在未获新授权的情况下证明最新提示的模型输出及真实客户端切换的语音组合行为。已调用Goal工具登记blocked，原始objective保持完整，未标complete。基础真人教学、后端重启闭环和既有普通真人打断的证据继续保留。

原始审计：`benchmarks/raw/evidence/teaching-quality-20261013-blocked-audit.json`。若以后恢复，应沿用同一budget round/历史账本，先核对新的明确授权，再只做准备好的固定WAV+实际独立WebSocket场景；不需要用户朗读、不采集房间麦克风。不自动增加上限、另建轮次或立即要求真人复测。

## 21:24 离线收尾：完整路由集成通过，去除句数提示冲突

上一轮属于进展：真实固定输入/完整回答/连续心跳的新证据改变了后续动作。本轮不启动宿主或音频，不使用外部provider，累计160/18/0保持不变。

- 新增回归运行两个部署根的**完整、未改动函数体的websocket_endpoint**，经FastAPI/Starlette TestClient建立两个并行ASGI连接；仅模型/manager与telemetry/capture/preview外部边界用夹具替代，不把它称作真实模型或RNNoise测试。旧客户端先实际发送voice_input_control取得voice identity；新显示客户端打开并成为global session后，旧客户端3次ping均收到pong，真实二进制PCM帧经生产解码/dispatch到manager，未cleanup且global session保持新客户端。新客户端实际发送语音接管控制后，旧客户端下一ping得到CHARACTER_SWITCHING_TERMINAL并关闭，新客户端仍收到pong，voice lease保持新owner。两个部署根均通过。原有guard的撤销/旧文字权限/修前断开复现保持通过，共3项测试。
- 观察到的两句话请求同时被追加“先两三句”和“2–4句”，这是可确认的重复数字指令，不能认定它解释全部模型违约。LANGUAGE_DIRECTIVES/PACING_DIRECTIVE改为先讲重点、简短口语，不再附带数字范围；原用户句数、语言、不要出题与代码限制保留。真实avatar请求构造器的中文/英文回归通过；单轮语言不改课程配置。没有截断回答、拼接标点或付费重写。
- avatar reply shape回归、5项课程/历史回归、2项失败/持久题目回归通过。新的生产改动只在study_avatar_tools.py；刷新两份隔离测试部署的代码，19个product文件逐项sha256吻合，未复制/修改学习数据。host与语音onset/PCM/取消代码未改。
- 完成审计仍不通过：教学解释/加法例子/出题/0分误解/针对纠错/100分正确回答/重启接续有真实后端证据；基础真人教学有用户确认；普通打断的既有真人证据保留。最新句数提示改动后的真实模型结果尚无证明；特殊socket抢占目前有完整本地路由集成证明，但付费语音组合场景尚未覆盖。不能将前一版本的真人PASS升级成最新修改后的完整验收。
- 当前唯一在线阻塞是同轮累计160/18/0已耗尽。没有运行中的测试句柄可等待、没有自动重试或新轮次。Goal保持active；下一次应先检查授权/额度是否改变，无改变时不能启动provider或用户麦克风。

本轮完整证据记录：`teaching-quality-20261013-offline-closeout.json`；回归入口为`scripts/test_neko_voice_owner_heartbeat.py`、`patches/neko-study-2026-10-10-product/test_avatar_reply_shape.py`、`scripts/test_neko_product_course_memory.py`和`scripts/test_neko_teaching_failures.py`。

## 21:15 最新：固定长句真实语音连续性 PASS，句数和抢占分支仍未完整通过

用户批准同轮160/18/0，保留已用150/17，只做一场固定WAV输入，允许外放、不采集房间麦克风。首次宿主180秒期限在固定输入开始前到期，角色启动阶段已有4次DeepSeek出站预留；没有Lanlan CONNECT。关闭角色后将同轮宿主等待期限延长到420秒，随后只启动一次实际语音会话。没有清空计数、更换轮次或额外付费重试。

- 13秒原始问题被provider识别为4个语音片段，实际Study只收到一次完整概念解释请求，其中保留了加法函数、两句话和不要出题的指令。Study audit2个完成调用，分别是知识路由和concept_explain；非degraded。
- 原生界面收到完整回答，去空白/Markdown标记后与SQLite工具回答一致。回答正确区分局部计算结果、return交给调用者、无return得到None；无额外测验或代码块。
- **精确句数PARTIAL：** 工具本身返回3句话，角色保留这3句。不能把它描述成两句话限制通过，也不能归因成角色扩写。
- 输入在60秒自动停止，早于77秒WAV循环。连接在约11/12、41/42、71/72秒都收到pong，观察期无close事件。171个播放回执，170个audible=true；WASAPI回环84个响声片段、max_peak=.9901。该结果证明本场真实输入/回答/播放及跨心跳连续性，不替代人耳验收。
- **旧voice owner被新独立socket抢占后的分支仍UNVERIFIED：** 本场pet/chat共享实际连接，没有重现之前的独立socket切换；Electron不支持CDP新建页面，尝试在发送输入后创建额外页面失败且没有增加连接。实际生产guard的离线所有权回归保持通过，但本场在线PASS不能覆盖这个特定分支。
- 19个product文件在两份测试部署中的哈希、17个host manifest文件重新核对通过。未新增生产修改；没有修改打断阈值/PCM handoff/取消逻辑。
- 本场含启动的累计预留150→160，Lanlan.app17→18，tech0。出站预留/CONNECT计数不是账单金额。真实输入已关、角色与宿主已清理，stuck=[]、left_over=[]、log_still_advancing=false。

证据：`benchmarks/raw/evidence/teaching-quality-20261013-continuity-{events,db,loopback,cleanup,audit}.json`，Study audit `neko-product-api-20261013T081054Z.jsonl`。基础教学闭环与本场普通连续性PASS；精确句数和抢占分支保留为剩余证据缺口。没有启动任何图像/声纹工程，不自动追加预算，不让用户立即再测。

## 最新自动收尾：语义改善、心跳边界修复；在线连续性尚待验收

恢复Goal后核对累计额度140/150、app16/18，房间麦克风关闭。增加最小提示要求：同材料的相邻追问保留前面的句数/代码/不出题限制；格式指令碎片不作为新概念提问。5项课程/历史与2项失败回归通过。

用原始13秒长句WAV自动验证，沿用同一budget round。独立fixture只备份前一隔离测试库及3份服务配置，未复制原用户学习数据；Core对话目录为空，保留原测试库不改。测试期已提前告知可能外放，没有让用户朗读或采集房间麦克风。

- 实际Study audit4个成功请求、2次解释（原先3次）。第一输入已合并“接着加法函数，用中文两句话”；第二输入保留“区别是什么，不要出题”。两份数据库回答均为两句、无额外题目和代码块，说明后台格式传递改善。
- WASAPI回环max_peak=.9901、77个响声片段，确有输出；客户端旧socket观察器只有4条事件，遇CHARACTER_SWITCHING_TERMINAL后录音关闭，未形成完整客户端回答记录。不能把后台两句/回环能量升级成完整语音连续性PASS。
- 新日志显示语音socket在20:43:40开始，20:43:42出现新的同角色socket，20:44:09原语音socket关闭。源router在global session变新时保留PCM/voice控制路径，却让旧voice owner的ping走终端切换关闭分支。前端定时ping，时序相符。不能宣称所有终端切换都源于心跳。
- 在仍持有voice lease的旧socket上，只对ping回复pong，保留新的global session与文字输入权限不变。已进入可重放补丁scripts/neko_native_barge_in_patch.py并部署两个根。实际生产guard AST回归：旧代码复现断开；新代码保留有效owner心跳；已失去/撤销voice权限的ping和旧连接文字仍关闭。2项通过；没有靠把整个旧连接重新赋权来规避。
- 20目标补丁检查、host gate fingerprint、19个product文件哈希通过；overlap/迁移与生产JS取消/解码/重连回归通过。没有修改onset阈值、PCM handoff或取消算法。
- 此自动场景计数140→150/150，app16→17/18，tech0。达到上限后已关输入、关闭角色及宿主，stuck=[]、left_over=[]、log_still_advancing=false，无重试场次。

证据：long-pause-setup.json、long-pause-events.json、long-pause-db.json、long-pause-loopback.json，及neko-product-api-20261013T074225Z.jsonl。新心跳修复是离线通过、尚未在线验证；基础真人教学PASS记录保持，完整Goal尚未完成。不再自动追加额度或发起在线请求。后续需要一场合成输入的有界连续性验证，不需要用户朗读。

## 最新本场结果：真人基础教学PASS，边界收尾仍active

用户明确准备后完成本场体验并确认正常。真实quiz/answer、partial55、语音文字与数据库核对通过，计数140/16，进程清理完成。见[本场阶段验收](teaching-quality-accepted-2026-10-13.md)。用户最新安排是不方便朗读时由Agent用固定语音输入，可外放；无需声纹功能。

## 最新授权：累计上限150/18/0，等待用户准备

用户明确批准同一轮累计上限 DeepSeek150 / Lanlan.app18 CONNECT / tech0。账本已原子更新，round与spent120/15逐项核对不变；前后证据为budget-150-before/after.json。当前没有运行中的宿主，本次不启动会话、不打开麦克风，新增调用0。后续物理麦克风必须先说明参与步骤并等用户明确“准备好了”。以下120/16等上限及额度触顶记录均为当时的历史状态。

## 后续离线收尾：启动状态与剩余验收

- 固化 `scripts/test_neko_tutor_start.py` 的真实上游状态/前端选择器回归：未准备的冷状态会选第1天；Tutor持久化跳过后，当天及未来日期均不选自动轮次；重复准备不改文件字节；已完成第1天与显式手动重开第2天仍保留。10项启动回归通过。
- 上述测试的进程清理用例暴露Popen句柄未收尾警告；增加wait/关闭stdout后，实际父子进程清理与引导测试重新通过，无该警告。
- 另发现原生壳 write_surface_config 每次都从打包默认配置重写全部配置。改为首次用默认、后续保留现有设置；只更新Tutor连接/窗口字段。已有配置损坏时停止并保留原文件。新增真实临时文件的重复启动/损坏保护回归通过；这是配置层证明，不宣称所有个性化UI均做了真人验收。
- 本轮0新增出站预留，账本仍DeepSeek120/app15/tech0，没有麦克风或扬声器测试。
- 本地界面宿主按600秒期限结束，guard确认processes=[]；随后关闭本轮角色壳。最终清理快照为 `teaching-quality-20261013-offline-final-cleanup.json`。追加150/18/0仅已提出，尚未获授权、未修改账本。

| Goal要求 | 当前可证明范围 | 剩余 |
|---|---|---|
| 服务失败明确归因、不伪造教学 | 实际CONNECT拒绝/SDK异常链与适配器回归；有额度时真实解释成功 | 修后失败播报的人耳验收 |
| 解释、举例、出题、判错、纠错、判对 | 真实DeepSeek与SQLite闭环结果文件；普通语音解释/扬声器回环 | 角色完整真人教学闭环 |
| 重启续题/续课/错题，课程隔离 | 真实宿主重启续题与具体旧误解回忆；真实回调切课隔离 | 真人语音续课体验 |
| 保留打断 | 前一场用户确认旧声音停止且回答新问题；离线15+4回归 | 新教学版本的最终体验、跨结束/长期场景未新增 |
| 启动可复现，不让引导抢操作 | canonical启动器持久化skip；实际Electron无引导/提示且recording=false；冷启动选择器回归 | 修改后的首次开口需与用户约好后验证 |
| 预算、原历史、脏工作区保护 | 累计120/15，无换轮重置；用户原历史未复制，未提交/推送 | 新付费验收须新的额度授权 |

Goal未完成；在线验证停在已批准额度上限。用户不在场的上一段物理输入只作为环境记录，不能被升级为真人测试或掌握度证据。待授权在线验收时，先约定用户参与的步骤/时长并等“准备好了”，再开麦。

## 19:54 最新状态：引导启动已修，真人教学未验收

用户确认上一场开麦时本人不在电脑旁，指出新手引导会抢占首次操作，并要求先说明何时需要配合。上一场不属于有效真人验收；不会根据环境识别文本推断用户的学习情况。

- 证据显示第1天引导到19:39才记完成，早先录音验证没有等待 tutorial 就绪。首次动画可能干扰首轮；不能把所有识别错误都归因给动画。
- Tutor 启动器 prepare_tutor_onboarding 复用 upstream durable state APIs：保留已完成轮次，将其他自动轮次标为 skipped（不伪造 completed），关闭首次人格提示，保留显式 manual reset/reselect 意图。只有 Tutor 运行目录受影响。真实临时目录验证冷启动、重复调用不改版本/字节、完成轮次与手动重开意图保留，通过。
- 已重开真实 Electron 界面，当前 recording=false、isInTutorial=false、tutorialRunning=false、skipVisible=false、personaOverlayVisible=false、stateReady=true、nextRound=null、toolbar=true。原始证据 tutor-boot.json。此次使用 --api-budget 0、不启用 --voice；麦克风保持关闭，仅做界面验证。ledger启动前后120/15不变。
- 上一场麦克风自动关闭，35条实际播放回执，其中23条audible=true；说明本场输出反馈通道工作，不能替代真人听感。观察器改为包装socket实例send后正常取到回执。
- DeepSeek本地出站预留计数98→120/120、app13→15/16。日志去重器匹配17个成功DeepSeek HTTP；Study audit只有2个请求。其余12个HTTP仍未可靠归因（邻近日志启发式，不能断言全是记忆压缩），另有3个emotion和1个分析分类。账本预扣/连接计数不是账单金额。已保存mic-attribution.json，未发现本窗SDK重试标记。
- 上一在线宿主清理stuck=[]/left_over=[]/log_still_advancing=false。当前只重新打开本地界面，宿主600秒有界；无在线教学复测、无清空计数或增加预算。
- 后续先完成离线/本地工作。需要用户开口或判断声音时，提前说明步骤和预计用时，等待用户明确“准备好了”再开麦；Agent固定输入和扬声器测试也提前说明会发声，默认无人值守阶段不开物理麦克风。
- Goal active，未宣称完成。后端闭环已验证；最终真人体验、长句停顿分轮和在线预算效率仍有待解决。额度已满，未经新授权不再发起付费验证。

## 19:40 进展：角色语音集成与真人验收准备

- 修复 study_session 状态字段不匹配：真实 status 只有 study_course_id，原头像筛选 course_id 后会丢掉身份与跨会话答题记录。现复用 _course_learning_state 返回当前 course/session/recent_answer_records；实际 SQLite 重开与混课程回归通过。真实回调换入数学课程时记录0条，换回 Python 时恢复 wrong/correct 两条记录，未调用模型。
- 长句固定输入 PARTIAL：13.14秒语音带自然停顿被 provider 拆成3次 study_explain，实际教学生成与声音成立，但先答旧题、最后多加追问，未达到原指令要求。保存 native-events、api audit 和 loopback；不把它归为真人测试。
- 短句固定输入：5.259秒中文指令完整识别；角色实际返回两句话，没有出题。语音来自真实 Lanlan，WASAPI Realtek 回环 peak=.99/loud_chunks=28。此次角色直接回答，未调用 study_explain，不能把它当作修后工具转述验收。
- 第一场真实角色确实调用教学工具并将结果交付为音频，但省略了代码，故仅确认语义交付，不宣称逐字转述。受控输入/回环能量仍不能替代人耳听感。观察器筛选错了消息类型，native-events 里的 receipts=[] 是本次观测缺失，不能推断播放反馈没发送。
- 统一默认教学模式与语音 pacing，明确请求篇幅优先、无题优先；语音默认不再加代码块。真实回调同一“中文两句话、不要题不要代码”此前仍有代码，修后返回两句、无代码无追问、非 degraded。保留前后 callback 原始结果。
- 本阶段累计 DeepSeek 73→98/120，app11→13/16；其中第一场6次插件请求，其余包含宿主情绪/分析/记忆调用。无重置、无更换轮次。第一次宿主按900秒期限结束，角色已关闭；当前用相同store/round重新启动，准备一次最终真人体验。
- 最终人耳听感/真人教学验收仍 pending；长句自然停顿导致提前分轮未被解决，跨播放结束真人专项与长期稳定性也仍未新增。

## 已完成的修复

1. **额度拒绝不再伪装成 provider_unavailable。** 本地 Sink 原先对额度耗尽和域名拒绝都回 `403 Forbidden`，HTTP CONNECT 失败被 SDK 包装成没有 HTTP status 的连接异常。现在额度耗尽有专用 `NEKO_EGRESS_BUDGET_EXHAUSTED` reason；Study gateway 检查真实异常链，映射为 `agent_quota_exceeded`，审计也保留 diagnostic/status。未改变放行范围、额度或计数语义。
2. **失败结果不能伪装成教学或评分。** 四个头像教学工具保留 degraded/diagnostic，统一返回明确的暂停说明；失败时去掉题目、分数、verdict 和题目身份，并要求角色只转述失败说明。宿主自己的 Study 人设规则同步说明“服务失败不代表学习者要求的示例无法解释”。原用户自定义人设仍由既有保护逻辑保留。
3. **未答题目可以跨进程重启。** 头像判题从持久化的当前课程题目读取 ID，不再依赖头像临时缓存。Study 启动会给旧会话收尾并创建新会话，但保留同课程尚未评分的题目；切换课程、显式新建学习会话或已评分题目仍清理。进程重启只撤销已经失去执行者的 pending 评分标记，避免旧锁状态堵住答案。
4. **初学者/纠错表达更聚焦。** 现有提示词增加整体篇幅、短段落、纠错只讲一个误解、避免不相关语言和额外测验的要求。真实复述遵守了四句话要求；完整多概念讲解仍有标题与检查问题，不能说所有回答都已达到理想口语长度。

本轮修改的生产源为 `scripts/neko_desktop_tutor_host.py` 和 product payload 中的 `__init__.py`、`study_model_gateway.py`、`study_avatar_tools.py`、`prompt_templates.py`。没有重写教学架构，没有修改语音 onset、PCM 缓冲或播放取消算法。

历史 18:23 的 provider_unavailable 与当时额度触顶、约 10ms 失败相符；旧日志没有保留底层 ProxyError 字符串，因此不能把所有历史失败都回溯认定为额度拒绝。本次用真实 httpx → 实际 Sink 的拒绝复现证明新归因有效，并用有余量的真实请求证明教学路径可正常工作。

## 离线/本地回归

- `scripts/test_neko_teaching_failures.py`：2 项通过。真实 loopback CONNECT 额度拒绝，0 provider/上游连接；实际 SDK 异常包装可正确分类，原网络失败不会归成额度。持久题目 ID、旧课程缓存拒绝、失败判题不显示分数通过。
- `patches/neko-study-2026-10-10-product/test_model_budget.py`：插件 reload 不重授 Study 预算，通过。
- `.../test_avatar_reply_shape.py`：正常回复保持代码标识符/题目 ID；四种失败操作不伪造讲解、题目或评分，通过。
- `scripts/test_neko_product_course_memory.py`：5 项通过。真实临时 SQLite 重开、待答题目保留、课程切换隔离、已评分题目不重开，以及历史/总结序列化。
- 打断回归：15 个 overlap 场景与 4 个迁移/幂等场景，以及生产 JS 播放取消/新回答存活用例，通过。不是新一场真人打断验收。

## 真实集成结果

独立目录：`benchmarks/raw/neko-teaching-quality-20261013`。仅从前一独立测试目录带入角色/服务配置；不复制历史学习数据库。没有头像、麦克风、扬声器或 OCR 截图参与这一组测试。通过已存在的 `LabClient` 和宿主 `/runs` 协议调用真实插件、gateway、DeepSeek 和 SQLite；测试学生答案由 Agent 提供，不能当作用户本人的掌握度。

课程：`python-functions-quality-20261013`，材料为 `add(a, b)`、`total = a + b`、`return total`、`result = add(2, 3)`、`print(result)`。

| 场景 | 结果和证据范围 |
|---|---|
| 解释/计算器例子 | 正常生成代码与讲解，区分参数 a/b、实参 2/3、局部变量 total、return 与 result；打印 5。未拒绝示例 |
| 出题 | 生成“删掉 return total 后 print(result) 输出什么及原因”的真实题目与身份 |
| 宿主完全停止并重启 | 未答题目身份仍有效，随后评分成功；没有手改题目或重新出题来绕过 |
| 已知错误答案 | “自动返回最后算出的数所以输出5”被判 wrong / 0；指出 Python 默认返回 None |
| 针对错误纠正 | 解释计算得到5与返回None的区别，沿用相同代码与误解 |
| 新题与正确答案 | 正确说明内部算出5但没有return，调用结果为None，被判 correct / 100 |
| 学习总结 | 保存主题、错误答案、正确规则、后来纠正及下一步练习 |
| 再次插件停止/部署/启动后回忆 | 未提供旧答案内容，只问“重启前哪一点答错了”；真实模型找回具体题目、误解、None规则和后来答对的记录，以四句话复述 |

原始结果：`benchmarks/raw/evidence/teaching-quality-20261013-results.json`，每一步保留 run_id、参数、完整结果和当时账本。9 个真实教学 entry 均未 degraded；另有 2 个不调用模型的控制 entry。13 次新增本地出站计数与 Study 多调用流程相符；不要把 entry 数当作模型调用数。

19 个 product payload/静态文件已与该独立运行根逐字节核对，当前 product manifest 哈希同步。manifest 的 deployment 明确是这次隔离验收根；不声称此前默认用户目录已被改过。启动器已有的 prepare_product_plugin 会在下一次启动时部署这些 canonical payload，不复制学习数据。

## 可复现入口

下列命令是本轮已执行的形状；必须先看当前账本和运行状态，不应把 prepare/resume 当作自动循环。脚本拒绝重复执行已记录的 paid 阶段。观察超时须检查原 run_id，不能据此重新提交。

```powershell
& 'benchmarks/raw/neko-product-host/.venv/Scripts/python.exe' -X utf8 -u -B scripts/neko_desktop_tutor_host.py --source --core-provider free --store neko-teaching-quality-20261013 --hold 900 --seconds 220 --api-budget 50 --egress-budget 120 --allow-host www.lanlan.app:16 --budget-round bargein-autocheck-20261012
& 'benchmarks/raw/neko-product-host/.venv/Scripts/python.exe' -X utf8 -u -B scripts/neko_teaching_quality_acceptance.py prepare
# 用既有 session guard 完全停止，再以相同 store/round 启动宿主
& 'benchmarks/raw/neko-product-host/.venv/Scripts/python.exe' -X utf8 -u -B scripts/neko_teaching_quality_acceptance.py resume
# 本轮先部署最新 payload，再停止/启动插件，随后执行回忆检查
& 'benchmarks/raw/neko-product-host/.venv/Scripts/python.exe' -X utf8 -u -B scripts/neko_teaching_quality_acceptance.py continuity
```

## 额度、清理和未完成部分

- DeepSeek **60 → 73 / 120**；Lanlan.app **11 → 11 / 16**；tech 上限0。轮次、历史计数和累计上限不变。没有付费自动重试循环。
- 宿主已关闭：guard `stuck=[]`、`left_over=[]`、`host_log_still_advancing=false`。前后快照为 `teaching-quality-20261013-before.json` / `...-after.json`。
- 原始用户学习历史及 `.workbuddy` 改动保留；没有提交或推送。
- **Goal 仍 active：** 实际头像是否准确转述教学工具结果、修后语音交付、完整课程切换的在线场景及最终用户体验尚未完成。backend/model/DB 的通过不能升级成实际声音或人耳的通过。
- 普通打断沿用先前本场真人 PASS；跨播放结束的真人专项和长期稳定性仍未新增验收。
