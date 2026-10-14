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

## 阶段十八ready wait关联窄审

Main明确授权后，只读telemetry、相应Native test及daily voice probe的output-only准备分支，不运行宿主/API/设备/DB/账本。NativeRendererPending区分已知root未加载/未ready；foreign HTTP(S) root或多个合法root为普通RuntimeError，未恢复chat fallback。attach_when_ready始终重用同task debug-port，只有ready读取/本地CDP连接，不启动替代Native、不调用begin/start_session或provider连接。daily probe仅output_only采用新等待，ordinary仍原4秒加单attach；output_only成功附着后仍先核capture flag/readonly/installed才登记和发送，权限没有由ready推导。

Main报告Native11 OFFLINE通过，本 Agent只读。新增用例覆盖同port loading/connection refused后ready，identity/install RuntimeError/其他URLError只试一次，.005秒即时mock deadline；既有attach INSTALL异常close和单root/无fallback等保持。它们没有执行真实慢HTTP读取或取消时挂close，因此不能外推严格35秒总上限。

### P2：35秒不是严格总上限，安装超时阶段未区分

attach使用同步opener.open/json.load，底层timeout5但阻塞async event loop。若deadline仅剩0.05秒时进入最后一次HTTP读取，wait_for取消需等同步调用返回，实际可超出35秒。其次wait_for会等待attach取消清理；attach的BaseException路径直接await socket.close，没有本地cleanup deadline，所以close等待也可延长该上限。11项的即时AsyncMock不能覆盖这两个具体边界。

最小修法：本地HTTP读取移出event loop并把I/O timeout限制到remaining，明确取消worker不等于停止底层读取，但它须有真实有界I/O；CDP关闭独立短有界cleanup，同时准确区分ready预算与清理预算，保留关闭尝试，不因timeout留下未知自有连接。新增慢读取/取消与挂close定向负例，无需provider或设备。

另当前except TimeoutError覆盖probe、INSTALL及外层wait_for全部阶段；INSTALL recv超时或进入INSTALL后总等待超时也会被再次attach，不符合“install失败立即拒”的严格含义。若仅允许loading/读取超时重试，应把已ready后的INSTALL失败（包括超时）包装为不可重试类别；不能通过降低身份/capture检查来恢复。这是stage分类问题，不声称当前重试会重连provider。已即时交Main。源码无API/捕获/provider重连路径，但 **ready deadline P2待修/准确限界，install超时待精确分类**。报告冻结等待关闭，既有阶段结果保留。

## 阶段十八等待/cleanup P2精确关闭

只读Main修复及Native测试：HTTP读取通过to_thread执行，底层socket timeout限制到min(5,remaining)，await也限制remaining，不再阻塞event loop。attach为HTTP、DevTools handshake、probe、INSTALL提供剩余预算；INSTALL的TimeoutError（含进入时剩余预算耗尽）转换为RuntimeError，attach_when_ready不再重试安装失败。foreign/ambiguous/其他网络仍拒绝，只有loading/本地连接未ready继续同port polling。

失败连接cleanup通过close_failed_attachment独立wait_for(close,2秒)，异常/超时对已持有transport执行abort。现在准确口径为 **35秒readiness预算加至多最后一次失败CDP close的2秒清理预算**，不是宣称所有同步线程在35秒内瞬间消失。取消HTTP await不能杀worker，其底层有界I/O及task-owned Native停止负责收尾；不把取消async等待冒称已经停止底层读取。原“同步HTTP阻塞/无界close/INSTALL timeout重试”P2 **SOURCE REVIEW CLOSED**。

新增测试直接让HTTP worker sleep .2秒而attach预算.01秒、核caller不被阻塞；INSTALL抛TimeoutError核连接仅一次且close一次；close挂起核2秒后abort。Main报告 **Native14 OFFLINE通过**，本 Agent只读未执行。主动取消的其他分支仍是BaseException清理源码证据，不把这些测试冒称真实Native/provider/设备证明。限定新实现未发现新具体阻断。

daily voice probe仅output-only改为复用阶段十五cleanup_resources：本次host Popen记录PID+creation-time，surface shutdown/close、Native shutdown、owned host stop/wait分别尝试，错误汇总进cleanup_errors；有failure或cleanup_errors退出1，输出log后续仍关闭。独立observer release/close异常保留各自diagnostic字段；不能把这些字段等同成功释放或抹除。ordinary沿原路径，没有为等待改动放宽捕获/回环/provider准入；output-only仍在fixed begin前核capture installed/readonly/flag。

本轮只追加本scope报告，不运行服务/API/浏览器/Native/设备/DB/账本，未启动待准备的voice34。Main安排的必要单场、既有WAV/图片和后续真实结果另记，不能从本审查认领ASR/TTS/PCM播放或human。报告最终冻结。

## Voice34 terminal后的窄输入链诊断

Main已将voice34停止，不在线重试。本 Agent仅解析私有report34的标记/计数，不输出配置、secret或原history；只读runtime router/asr/audio pipeline和其必要streaming/Omni/phrase/ownership精确callee。runtime无CodeGraph由Main确认，本轮不建立索引、不扫描整仓、不运行任何服务/API/设备/DB/账本。

report34标记独立读取：output_only=true，room_microphone/capture_devices/loopback=false，finalized/turn_timeout=true，cleanup_errors为空；fixed ticket id1/core/gen2/socket1/capture_started false。Native trace本地send计数2098 frames、1006953 samples，receive binary0；session_started标native，未见transcript/tool事件，provider wire_trace仅3个send session.update，没有input_audio_buffer.append。**本地socket.send计数不等于服务端已收PCM，更不是ASR/provider通过。** 最初报告没有分层server intake计数，不能仅据空返回推定router丢弃。

Main随后提供对应时间段实际server RNNoise诊断：同pipeline约每2秒201/202 chunks，unavailable_chunks=0、scored_frames与count相符，probability peak1、尾段0、pipeline_max_ms至4.306。此为 **Main提供的实际服务端DSP处理证据**，已跨过本地send-only。它不证明DSP后路由、phrase接收/seal或provider提交；本 Agent未新采现场或重跑。持续DSP也使“全部PCM停在router/queue之前”的解释不成立，后续优先核DSP后门槛。

### 源码实际链及无声return条件

- router音频stream_data源1277–1348：先theater普通音频drop；claim voice connection；外部麦克风route可claim后consume；有序await manager.stream_data。superseded connection分支961–1000依独立voice identity dispatch或在lease已vacated时drop。streaming.py:237–243把audio送_enqueue，不走text缓存。此为链路范围，**不再用它泛称34未到DSP**。
- asr_runtime.py:3459–3508：activation_required但factory缺失、pipeline failed/failure token、lease/registry不接受都会在queue前return。_voice_input_accepts_pcm（1476–1500）要求synchronized、builtin core/game target且accepts input、无mute/focus/suppression/external suppression。worker3584–3599拒stale ingress，activation authority下不重绑旧帧。
- audio_input.py pipeline对48k做RNNoise/resample，对16k保持原PCM；asr_runtime.py:3945完成该DSP后，3959空输出return，3966–3972核 **is_active、audio epoch、lease owner、accepts PCM** 后无声return；随后token/refs/pipeline变化与hot-swap barrier决定丢弃/缓存（3973–4044）。这是当前最优先的断点：DSP持续正常但is_active false等可令所有帧不达native发送。
- _route_microphone_audio（4073起）会consume preview-isolation、activation degraded、required却无factory、factory noise reduction contract不匹配、要求RNNoise但实际不可用；activation runtime create失败或feed决策尚未允许output也不直送provider。没有activation factory/shadow时才走unfiltered；源码中return True表示已在本地处理/consume，**不等于provider写入**。
- native unfiltered（4734–4830）再次核session_closed、same session/connection generation/route/token、owner core、accepts PCM、可调用stream_audio及fatal状态。phrase模式时传真实bool speech_active、单frame标记、require_output_commit；None为LOCAL_ACCEPTED，False为NOT_SENT，不能把collector保存在本地误计provider音频。
- Omni _transport.py:1409/1548–1799：phrase opt-in还须lanlan_app_gemini/free proxy/no server VAD/non-Gemini；pending barge-in/fatal、DSP或resampler空输出、turn-admission lock、phrase collect都可能先不写。实际direct provider事件在1785构造input_audio_buffer.append后send_event；send_event:990–1017仍核send_guard/fatal/Gemini/throttle/ws存在。需要记录实际return层，不能从session.update成功推定audio.append可达。
- NativePhraseUplink的accept/read_snapshot要求actual Core callback、已安装nonretired session、active/native/core、无takeover/closed/fatal、当前Core websocket和provider ws/connection；没有speech true时只保有限preroll，只有buffer sealed后才创建writer。flush逐await核authority，真正send_event成功后才记written_samples。Core authority在session_lifecycle.py:346–384实接，不能用game route getter代替。

### 下一步最小无内容诊断

先新增本地/离线counts-only分层钩子和actual method负例，避免再次盲目paid场。DSP已证实，建议在3966门槛按互斥reason计数，采is_active、epoch_match、owner_match、accepts_pcm、token_match、refs_match、pipeline_match/hot_swap booleans；owner enum/route enum/queue epoch等仅非秘密数值，owner token/PCM/transcript/完整配置不入日志。

随后记录route_enter计数、activation required/factory present/enforce/degraded/noise-contract/current generation匹配、到native_unfiltered/stream_audio的计数；若到phrase，记mode_allowed、bypass reason、speech_true/false计数、authority_current、preroll/buffer样本数、seal/flush/result/written_samples。最后send_event append attempted/true/false与fatal/throttle/ws存在/guard当前等原因。这些字段复用现有Core/controller/provider边界，不更换owner、不伪onset、不重播旧PCM、不创建新队列。

持续约100fps DSP由单audio worker依次await下游；一个长期阻塞turn-admission lock通常会停止后续DSP并形成backlog，所以本场优先无声return/未activation，锁仍仅为待排条件。probability_peak1只有在实际到unfiltered后才推出speech_active true，不能跨过中间门槛直接认领phrase已收语音。

当前报告的timing_log导出只保留固定工具/native timing等marker（probe源564–565），不含voice-rnnoise或native phrase delivery；**缺这些导出日志不证明从未调用**。建议采上述窄计数再明确恢复条件；34保持turn_timeout/未通过，DS610/app59/tech0与cleanup由Main记录，不以本审查改账本或重连。本轮仅追加本scope报告，最终冻结。

## 阶段十九：默认OFF计数helper源码/离线交付

按Main独立开发授权，仅新增 `scripts/neko_native_delivery_diagnostics.py` 和对应test，并追加本报告；未修改实际runtime/host/patchinstaller/manifest或其他记录，未启动服务/API/设备/DB/账本。helper只用stdlib，import不加载N.E.K.O、音频或设备模块，没有新队列/数据库/记忆系统。

交接接口：`install_native_delivery_diagnostics(asr_class, phrase_class=None, transport_class=None, *, enabled=None, logger=None)`。默认仅当 `NEKO_NATIVE_DELIVERY_DIAGNOSTICS == '1'` 才安装；OFF返回None且class/method身份不变，ON幂等并返回DeliveryCounters供Main报告读取snapshot。Main独占把文件部署到actual import路径及安装actual classes，建议传实际AsrRuntimeMixin、NativePhraseUplink、Omni transport mixin；本 Agent不接宿主。纯 `safe_native_snapshot(owner)` 可由Main的actual AST夹具直接调用，输出只含8类bool/None：active、route_native、owner_core、activation_degraded/required、factory_present/enforced、noise_contract_match。

固定7个方法边界：Core process/route/unfiltered、phrase accept/flush、Native stream_audio、provider send_event中的input_audio_buffer.append。其它provider event仍原样调用且不计audio stage；不读取/记录PCM、text、paths、keys或identity token，不打印异常文本/类型内容。包装器原方法恰调用一次、原参数和返回对象不变；async只await原协程一次，不创建task或改变owner/registry/guard。返回True/False/None/other、raised/cancelled只记有限枚举。投影属性异常变unknown；诊断/log错误不能替代业务返回/异常/取消。

所有stage/event/投影字段固定，数值计数饱和到最多1000000，日志最短间隔2秒且仅输出累计计数/安全布尔分布，无timer/worker；每个task runtime安装对象拥有自己的aggregate，不写全局账本。它证明方法入口/出口层级，**不能准确区分一个方法内部哪个return分支，也不是provider ACK或ASR成功**；LOCAL_ACCEPTED/None不能用计数改成TRANSPORT_WRITTEN。必要更窄branch reason仍由Main实际AST fixture/允许的runtime接点另做，不伪造34根因。

执行证据 **SOURCE/纯OFFLINE11 PASS**：`python -B scripts/test_neko_native_delivery_diagnostics.py`（.075秒）。覆盖OFF身份、显式env启用、单次参数/返回身份、ON幂等、非audio event不计、异常及真实Task cancellation透明、同步phrase异常、日志失败不损业务、未知event type不触发不可信比较、无敏感序列化、计数饱和/限频/独立snapshot与安装预验证无部分变更。首次使用module unittest入口因scripts不在module查找路径而ImportError；未改生产，换实际script入口后9通过，再补env与同步异常必要负例得到11通过。不是宿主/actual methods/模型/设备/human验收。

helper与test现冻结，Main后续实际接入、完整pipeline验证及必要场另记；不会为本诊断online重连或重播WAV。

## Main actual-method fixture独立只读复审

Main报告helper11及新增 `test_neko_native_delivery_actual_routes.py` 4项通过。本 Agent只读该测试、冻结helper/test及必要已有native fixture的AST提取/构造精确片段；helper/test SHA未变。本轮不执行测试、服务/API/设备/DB，未接production hook或manifest，唯一追加本报告。

ActualCore的process/route/unfiltered确来自runtime `main_logic/core/asr_runtime.py` AST方法：提取只去decorator/annotation，保业务方法体，在明确隔离namespace运行。OmniRealtimeClient、_TransportMixin、NativePhraseUplink实际方法用于本地QueueSocket，非伪造audio.append记录。positive场46帧对应DSP seam调用46、Core/native/phrase accept entry各46、flush一次，QueueSocket确有input_audio_buffer.append且原mic accounting增加。结合helper原方法单次调用源码及11项纯测试，这支持该fixture的 **stage计数/本地返回透明性与真实方法到本地append路径**，不是外部传输成功。

三个负例运行实际方法的指定分支：required无factory在Core route返回True/consume且不到unfiltered；noise contract不匹配在route停且安全投影false；inactive在DSP seam已调用后process返回None、不进route。未通过修改guard/owner值默认允许来制造这些负例；各case明确设置条件后核原分支仍failclosed。它们支持这些条件可由counts区分到方法层级，不唯一指出34真实原因。

严格边界：DSP是pass-through double并提供.9/.1、rnnoise_available true，没有实际RNNoise/48k处理；preview隔离、ingress/token/lifecycle、registry acceptance与Core construction仍是OfflineManager seam。测试直接调用process，不含router/enqueue/真实lease registry准入；尤其production required无factory可能在enqueue就更早drop，不能把fixture经DSP→route路径说成完整production intake。QueueSocket不连接provider，local audio.append及accounting不代表server ACK、ASR、模型或声音设备。

ConfigManager依赖import前先设置临时NEKO_STORAGE_*和LOCALAPPDATA，按script入口finally恢复env/清临时目录；hook方法在每case后restore，driver/task按fixture退出。只确认该脚本直接执行的隔离设计，不把它泛化为任意test discovery/global runtime生命周期。日志是固定计数/安全布尔，fixture的fake身份和内容未升级成教学证据。

结论 **限定SOURCE REVIEW无新具体P1/P2；Main提供ACTUAL-METHOD OFFLINE4**。production helper import/hook、default-OFF重放、完整原始pipeline及voice34现场定位仍待Main后续，不因这4项标已部署或provider根因已解决。本报告最终冻结，其他文件未动。
