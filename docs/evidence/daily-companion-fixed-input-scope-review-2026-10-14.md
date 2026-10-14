# 阶段十七fixed input scope关联窄审

日期：2026-10-14。已完整读取contract/plan/status/blockers阶段十六当前记录：Goal active、d0c28db已发布；Main记录账本610/58/0不重置。必要约4%输出不授权任何物理/虚拟mic/capture/loopback。本 Agent只读telemetry/对应test，并为核登记/释放机制精确读取fixture的actual controller路径及begin/state/end同步callee；仅写本报告，不运行测试、服务、API、浏览器、Native、设备或账本，不读用户DB、不新增Agent。

## 新实现的限定支持

INSTALL用WeakMap为同一task root的socket对象分配局部递增id。每个send/receive监听闭包保存socketId，旧socket迟到status仍保留原标签；旧reject没有被删除。refreshSocket在BEGIN前同步运行，新socket不等100ms timer即可绑定。标签只是client调试对象关联，不是server authority ACK、provider utterance id或进程ownership；host48911/known root与本次debug-port的限定继承阶段十六。

BEGIN在actual controller登记前捕获当前socket、局部id和wall time；登记后同步检查socket对象仍相同，否则调用endFixedInput(receipt.id)并拒绝。实际controller begin/state/end片段显示该ticket属于原socket，释放不向已替换的新socket发布none；begin内异常会清本地fixedInputSource。本轮不修改这些controller围栏，也不把登记成功或本地core control send当server准入通过。

Python只接受active/core/capture_started=false、正整数ticket/generation/socket_id及正wall，保存ticket/socket/start scope；snapshot继续保留scope（end后亦保留用于证据），当前发送仍需要registered id且委托controller。未知/旧receipt缺socket标签会拒绝登记，不猜标签或默认当current；现有Fake负例只证明拒绝，不证明任意异常receipt已成功release。已知actual controller产出普通同步对象；本轮未确认可构造的真实缺标签后残留claim，因此不把Fake缺字段直接判成实际泄漏。

## P2：音频correlation跨socket错配

当前INSTALL的binary message分支虽然记录局部socket_id，但从全局trace.lastNativeCorrelation读取correlation_id；各socket的audio_chunk都写这个全局值。可构造顺序：socket1的chunk token c1，socket2的chunk token c2，旧socket1迟到chunk c1，然后socket2收到binary。最后binary事件socket_id=2却correlation_id=c1，误把新socket音频归给旧token。

最小修法：在各socket install闭包内保存last correlation，audio_chunk只更新该局部值，binary只读取同socket的值；若还保留全局诊断值，不能用于音频归属。补两socket迟到旧chunk+新binary负例。这一发现已即时交Main；未修前不能把本版trace作为跨socket音频token归属证明。只控制、无session/WAV的下一offline诊断可以继续，不需要因此paid重连或弱化stop。

## Race、旧trace和证据边界

BEGIN与actual controller登记是同一同步JS执行，无await；socket检查前后对象不同就清原ticket并拒绝。它不采用后出现socket作为新owner。Python IPC lock串行化Runtime.evaluate，但不意味着server状态冻结；真正控制/PCM资格仍依controller当前ticket/socket/readiness。snapshot的currentSocketId可能在下次timer/refresh前落后于真实appState.socket，消费者应依已保存scope与事件标签，不将该字段当即时server授权。

INSTALL遇既有trace会调用refreshSocket；旧版本没有该函数会报错，attach异常关闭CDP，不伪造新的安全状态或未知receipt。在现有task-owned生命周期支持范围内这是failclosed，不保证旧监听可原地升级。旧raw缺socket_id不能当新scope的current事件；按任务既有保守stop继续拒绝，不删旧reject或仅凭wall宣称旧错误不存在。

已读新增actual controller VM用例：先原socket登记/释放，再新socket登记，两个receipt的局部id为1/2、ticket不同；旧/新status分别有1/2标签，core control wall不早于receipt且generation一致，captureCalls=0。Fake缺socket标签拒绝、valid receipt保留scope。Main报告模块 **OFFLINE8通过**，本 Agent仅只读审查，未运行；该用例不覆盖上述binary correlation错配、真实provider、实际声音或human。

结论：输入authority未被本增量放宽；scope基本关联源码可用，但音频correlation P2待Main修复。仅本报告新建，其他文件未改。报告冻结等待精确关闭，不扩扫其他source/capture/host。

## P2精确关闭确认

只读核当前INSTALL：每个socket install闭包单独声明 `let lastNativeCorrelation=null`，该socket的audio_chunk仅更新局部变量，binary仅读取同一局部变量；不再使用trace全局correlation作binary归属。新增actual controller VM顺序为old chunk→new chunk→late old chunk→new binary，明确断言最后binary的socket_id为2且correlation_id为current-correlation，旧/新reject仍各有1/2标签。

该P2 **SOURCE REVIEW CLOSED**；Main报告模块OFFLINE8实际通过，本 Agent未运行。首次VM缺location字段由fixture补齐，属于夹具错误，不冒称产品故障修复。仅修调试关联，未修改播放、server SDK owner或输入准入；socket_id仍非ACK/进程ownership。真实服务、provider、声音及human保持未验证。本轮只追加此报告，最终冻结。

## 明确扩展：Native passive snapshot及共享wire

Main追加本地实际证据：fresh output-only/offline/muted task root的guard及socket1成立，begin receipt为id1/core gen2/active/capture_started false；0.885秒后同Native wire出现none gen1、engaged false并收到invalid_or_stale_control，正常release为none gen3。没有WAV/session/paid调用，Main记录610/58/0逐byte不变且owned cleanup。此为 **Main实际本地控制证据**，本 Agent未运行，不能由此认领provider/设备通过，也不能唯一解释历史27。

按Main明确扩展范围，只读其提取的packaged `chat-websocket-bridge.js` 与 `pet-websocket-bridge.js` 精确发送链。chat的WSProxy.prototype.send在OPEN时仅 `ipcRenderer.send(WS_PROXY_CHANNELS.RAW_SEND,data)`；pet源行299–307的单一RAW_SEND listener核_activeWs OPEN后原样send(rawData)。bridge没有重写voice_input_control的lease_generation；pet bridge自身_wsGeneration/sessionEpoch属于代理生命周期，不是controller voiceLeaseGeneration。

Source controller的IIFE独立保存voiceLeaseGeneration/lastVoiceLeaseFingerprint/voiceLeaseSocket（当前源202–204），各页面open自己的socket对象时reset0并完整sync（382–394）。所以两个renderer各有私有控制计数器，chat代理对象与pet原生对象却可汇入同一条pet_activeWs wire。这支持“pet core2后辅助chat首次passive1”的碰撞条件；client socket_id标1仍不能辨认该wire原始renderer发件人，不能把那条none gen1唯一认定为pet自身状态回退。Main实际时间线与源码机制相容，代理跨IPC路由的其他外围行为未扩扫。

## 最小Source前端适配建议及限制

仅对显式output-only capture guard true、已知task origin/port与 `/chat`、`/chat_full` 辅助页面，在sendVoiceInputControlState发送前跳过可证明被动的初始/重复快照；不修改ASAR、不在server忽略reject、不共享/抬高generation来掩盖counter冲突。普通capture guard false路径完全保持。unknown origin/path/state不冒称pet，不发起fixed ticket；fixed begin只支持已知pet根path `/`，辅助chat拒绝。

“owner none/engaged false”不能单独证明可吞掉任何真实变化。skip须排除hard mute/focus suppression、game route、voice start、recovery/route/readiness阻塞等有意义控制变化，并保留实际active/control发送。如果辅助chat此前曾合法发送active或其他非passive control，后续none释放也是实际变化，不能仅因当前变passive就删除。可以用该页面已发送控制的历史状态限定初始/持续被动skip；不伪造ACK、owner或socket身份。root pet的初始idle、fixed core claim及release完整发送保持，单socketduplicate dedup继承阶段十六，不改 ordinary真实onset。

该段是 **SOURCE机制核对及待实现方案**，不是新修复通过；Main正在实现，尚未审新guard或测试。应以同源actual controller+bridge两renderer VM或下一有界offline本地控制确认chat初始none不入wire、pet1→core2→none3及实际变化仍保留，再决定必要provider场。旧reject仍保留并停止，不为验证方案重放整WAV或付费重连。本轮只追加此scope报告，没有执行服务/API/设备或修改其他文件；报告冻结等待明确下一窄审。

## 当前passive Source修复窄审

明确追加授权后，仅只读 `neko_output_only_patch.py`、`neko_fixed_input_fixture.mjs`、`test_neko_fixed_input.mjs` 并复用上述bridge证据。未运行patch/tests/services。本轮限定实现 **SOURCE REVIEW：未发现新具体P1/P2**。

新增skip位于sendVoiceInputControlState取得完整state/fingerprint之后、实际send与generation递增之前。须capture guard true、path为 `/chat` 或 `/chat_full`、engaged false/owner none/hard_muted false/focus_suppressed false、从未标记发送非被动控制、非game且非recovery pending/failed，才提前返回false。因此guarded辅助chat持续被动初态和重复force/open不发布自己的generation；并非只丢一次第一帧。root `/` 不满足skip，idle→fixed core claim→release原逻辑保持。

voiceLeaseSentNonPassive一旦遇非passive state即保持true：hardmute、focus或engaged控制之后回到none/解除抑制仍可发送，不被当前passive条件吞掉。它是本页面的控制历史限制，不是server ACK，也不在新socket时盲目重置以隐藏之前的真实变化。recovery/game条件退出skip不改server拒绝；后续仍沿原fingerprint去重。普通capture guard false从不进入skip，原generation/open行为保持；新增本地历史变量不赋予ordinary固定输入权限。

fixedInputBlocked增加path不等于 `/` 的拒绝，辅助chat或缺location不能登记fixed输入；原socket/current/OPEN/mute/focus/game/recovery/readiness等围栏仍在。该Source检查是路径边界，**没有额外验证origin/host或Native代理类型**；支持声明仍限capture bootstrap所控制的任务页面，并由telemetry known48911 root准入约束，不能把同名路径当任意来源的authority。

迁移保留完整已知pre-surface helper block，再替换为新增root guard版本；此前异常隔离/最早draft/旧exports和duplicate-open draft仅精确块适配。随后按全部anchor反向移除已知addition，必须匹配CAPTURE_BASE_SHA才允许重放；未知编辑残余不能通过base核。apply_to在写任何目标或复制helper前计算并校验web_app/capture及helper存在/AST，未因新增passive块放宽未知源拒绝。源码能支持这项结论，本轮未执行fresh/replay/idempotence检查。

fixture从实际source capture模块读取，新增location pathname/href便于路径守卫；设备API仍抛错。当前专门新增测试核guarded `/chat` 和 `/chat_full` 初态/refresh/duplicate open零send、begin拒绝；ordinary chat仍gen1；guarded hardmute发送及解除后gen2可见。已有root claim/release、ordinary、revoke、ticket和PCM负例保留。当前文件未见辅助chat focus/recovery及active→release专门执行断言，不能把硬mute用例声称为这些分支实际通过；已通知Main建议补必要定向负例。本 Agent只读，没有为测试缺口启动设备或API。

结论仅为当前Source修复的限定可审阅结果，Main实际本地控制/未来集成须另记。旧phase17 gen1拒绝保留，不推定旧27唯一根因；scope/socket_id继续只是client调试关联。唯一写入仍本报告，最终冻结。

## Main补充passive分支离线执行界限

Main报告补充focus与active→release、recovering/timed_out/failed/game定向用例后 **OFFLINE21通过，ASGI6通过**。初始夹具把状态误命名waiting，按实际Source修为recovering，仅测试修正、没有借改产品状态机来通过。本 Agent未执行；前段“缺专门分支执行”记录属于当时检查点，此处仅按Main已报告的新增证据关闭该范围。没有新provider、PCM播放或human结论。

## 明确追加A/F canonical状态与接续窄审

按Main授权，仅核canonical main.js/index.html/service.py相对managed基线d0c28db的增量、新UI resume与status question测试；为确认公开投影和set_course语义，只读必要models public helper及已有course entry精确callee。不执行服务、模型、测试、设备、DB或账本；唯一写仍本报告。

service增加真实study_session_id、公有current_question及pending/evaluated/none。复用public_current_question_payload的JSON独立副本，剥离答案、rubric、cache、reservation owner/pending等既有private字段；status不从旧history制造held question。新增3测试直接核actual projection、原state不变和options副本独立，Main报告status3通过，本 Agent未运行。保留原last_answer_evaluation/history等既有公开字段，不把该增量解释成全status隐私重构。

syncStatusQuestion只对同course/session、qid/aid、题干及options相同保留草稿/answer image/反馈；身份或题目变化清旧输入/反馈，evaluated标签由真实status提供。index明确选择/返回课程走study_set_course（恢复原题），新开Session走study_start_session（退役原题）；course entry确实restart并resume_course_progress，session变化时清草稿符合当前定义，不能把“同题”外推到换session仍保留未提交草稿。

refreshAfterSuccess只做status/material metadata刷新；失败保留已显示reply并提示无需重复提交，不自动重跑模型。statusRefreshRevision抑制较旧status响应，material metadata另核revision/course/session，成功刷新消除warning。新UI夹具读取actual方法并核restore/原qid aid评分、同题草稿、变更清空、resume/fresh、final refresh失败保留和无重复submit、submit失败诚实及旧status拒覆盖；Main报告UI13及material14通过，本 Agent未执行，非真实DOM/browser/device证明。

### P2：晚到教学结果缺origin守卫

当前evaluateAnswer、generateQuestion、summarizeSession在await callPlugin返回后直接写feedback/currentQuestion/reply，没有像explainText一样捕获提交前material revision/course/session并再次核对。refreshAfterSuccess只在最终refresh失败catch中核它调用时的当前context；它既不能阻止已经写入的旧结果，也没有保存该教学请求原始context。

可构造：A的grade/quiz/summary已在后端正确完成，但SDK result delivery仍pending；角色窗口切到B，B status已到UI；旧A callback随后写DOM。最后refresh B虽会清题/反馈，却不会清已写的A reply，refresh失败还会保留它在B。这是UI迟到回调，不指控后端material guard失效；现有late old STATUS测试没有覆盖late successful TOOL回调。

最小修法：三方法在首次相关await前捕获origin，grade加qid/aid；在成功回复、degraded、错误任何DOM写前核revision/course/session及相应题identity。stale抑制或明确提示并刷新，不重新提交。复用现有explainText guard，补真正deferred RPC、期间新context status、旧success/degraded/error回调负例。已即时交Main。本轮A/F结论 **SOURCE REVIEW P2待修**，不能以UI13/status3覆盖此竞态；其他增量边界保持。报告冻结等待精确修复，不扩扫。

## E2E量具与阶段报告追加窄审

按明确授权，只读 `neko_study_resume_e2e.mjs`、`neko_desktop_study_ui.mjs` 的resume-offline增量及 `daily-companion-phase17-integration-2026-10-14.md`；未执行浏览器/服务/API/设备/DB。未重复审learning_memory尚在修改的RPC guard。限定量具增量 **SOURCE REVIEW：无新具体P1/P2**。

resume-offline分支在已有普通text/model loop之前调用新场并用既有STOP正常退出，继续既有finally关闭context/browser；使用原shared web-inspector的playwright-core依赖，没有新增安装或项目导入包。新场必须匹配明确LOCAL_STAGE17_HELD_QUESTION环境标识及actual public q/attempt/course，等真实studyServiceReady和uiActionInFlight结束，再操作现有DOM。reload、status、resume A→B→A、fresh/start后不复活仍走实际SDK/runs/export；没有调用generate/grade/summary来伪造模型教学验收。

唯一区别明确标为synthetic：route拦截study_explain_text的POST并返回专用synthetic run/status/export，随后拦截一次study_status为503；其余请求continue，恢复后再次真实status，最终course/fresh实际SDK也保留。该用例可证明DOM保reply/notice、不自动重submit和恢复清notice，不能证明真实模型返回、history已保存或服务端503故障行为。步骤名和结果名均包含LABELLED/SYNTHETIC或OFFLINE边界，没有把该回复混成模型证据。

报告保留首场隐藏Adaptive Practice details导致fill超时的FAIL，后仅harness点击summary展开并核可见，不force填隐藏元素或改产品。第二fresh场实际SDK/SQLite/browser结果及postfix Native仅begin/end观测都明确归Main；Native无正向ACK/session/PCM/model/device，旧gen1拒绝不追溯改成PASS。UI也明确不覆盖仍待关闭的晚到RPC P2。

该E2E源码本身不启动/证明宿主offline-egress、不校验ledger bytes或task store所有权；原audio_posture描述不是运行时独立权限证据。cleanup_errors、两场宿主/browser停止、原daily untouched和610/58/0字节不变由Main外层运行记录承担。阶段报告已分别说明这些实际local证明与synthetic、模型、设备边界。本 Agent未读取DB或重跑/独立验证那些外层记录，不能借本审查认领runtime清理或预算复核。

唯一写仍本scope报告，其他文件/记录/账本未动。报告冻结；晚到RPC P2保持待精确独立关闭，不因新E2E通过而消除。

## 晚到RPC P2精确闭环复审

只读当前canonical main与UI resume测试，SHA分别匹配Main冻结的38cb30d8622fdf539b2754911b2a8663b4ff9e9d502672561a3434ff434e6185及32849ae57dee12d34a6128a0ff02c3988ec40e5cfede6a804e8d8d5e17c4f123。三方法在首次await前capture revision/course/session；成功和catch在DOM写入或向bindButton抛错前核origin，grade额外核当前qid/aid。guard位于degraded分支之前，旧degraded也不会写新context；degraded的独立执行负例没有由本 Agent运行。

generate的scope fetch及selection fetch亦有await后origin核；loadQuestionContext的success/catch在变更question context/selection reason前核isCurrent。stale准备不再继续请求quiz，current optional selection失败沿既有literal fallback；当前合法结果/错误仍显示，没有以抑制stale来隐去本context故障。UI44的deferred success/failure矩阵覆盖course/session/material、grade qid/aid、scope/selection、当前成功/错误和无重试；Main报告 **OFFLINE44及material14通过**，本 Agent仅只读断言与源码。

新增scope helper依赖疑点已定向闭合：canonical overlay本身没有所有base资产，实际base `benchmarks/raw/neko-app/resources/bin/plugins/study_companion/static/knowledge-map.js` 源行88定义setPracticeScopeState、104定义loadPracticeScope；index源648在main之前加载该script。Main host既有base static复制后overlay接线提供它，并有既有实际载入证明；不得以canonical目录无同名文件或VM stub存在直接推定生产ReferenceError。本 Agent只读上述精确callee，不重新扫描资产/运行浏览器；本次普通scope生成的Browser执行仍未验，保留OFFLINE层。

原“晚到教学结果缺origin守卫”P2 **SOURCE REVIEW CLOSED**，限定修改未发现新增具体P1/P2。历史发现与修前E2E边界保留，不追溯称已通过。

Main随后报告runtime3 PASS；只读harness新增延迟synthetic grade/export期间实际SDK set_course B并refresh，释放旧grade后明确核B仍当前、reply未变、feedback无旧grade、gradeRequests=1。该场现在有两个显式synthetic结果：旧grade和讲解成功→status503；actual course/status/reload/fresh仍真实SDK。它支持真实DOM拒迟到回调，**没有后端实际评分、DB grade、模型或设备新增证明**。原量具comment/阶段single-synthetic说法须随该增量同步，已通知Main；本报告不省略新增grade double。实际runtime3结果/清理/额度证明归Main，本 Agent没有执行或读取DB。

本轮只追加scope报告，未改生产/测试/共享记录、未运行服务/API/浏览器/设备或账本。报告最终冻结。
